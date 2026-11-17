#!/usr/bin/env python3
"""Preview a trusted saved motion NPY on CPU, without models or dataset meshes."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np

NAMES = ('preview_trial_01.mp4', 'preview_trial_01.png', 'preview_trial_01.metadata.json')
BODY_LICENSE = 'https://smpl-x.is.tue.mpg.de/bodylicense.html'
CREDIT = 'SMPL-X Body: Max Planck Institute for Intelligent Systems'


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024*1024), b''):
            result.update(chunk)
    return result.hexdigest()


def validate_motion(data):
    """Validate the saved single-person schema before drawing any output."""
    if not isinstance(data, dict):
        raise ValueError('Motion must be a saved dictionary.')
    try:
        joints = np.asarray(data['human']['joint_xyz'])
        objects = data['object']
        metadata = data['metadata']
        fps = metadata['fps']
        parents = metadata['position_joint_parent_indices']
    except (KeyError, TypeError):
        raise ValueError('Missing human joints, object, FPS or skeleton metadata.') from None
    if joints.ndim != 4 or joints.shape[0] != 1 or joints.shape[2:] != (24, 3) or joints.shape[1] < 2:
        raise ValueError('human.joint_xyz must have shape [1,T,24,3], T >= 2.')
    if joints.dtype.kind not in 'iuf' or not np.isfinite(joints).all():
        raise ValueError('Human joints must be finite numeric values.')
    if not isinstance(objects, dict) or len(objects) != 1:
        raise ValueError('This preview requires exactly one saved object.')
    object_name = next(iter(objects))
    if not isinstance(object_name, str) or not object_name:
        raise ValueError('Object name must be a nonempty string.')
    try:
        centers = np.asarray(objects[object_name]['xyz'])
    except (KeyError, TypeError):
        raise ValueError('Saved object center xyz is required.') from None
    if centers.shape != (1, joints.shape[1], 3) or centers.dtype.kind not in 'iuf' or not np.isfinite(centers).all():
        raise ValueError('Object xyz must be finite and have shape [1,T,3].')
    if isinstance(fps, (bool, np.bool_)) or not isinstance(fps, (int, float, np.integer, np.floating)) or not np.isfinite(fps) or fps <= 0:
        raise ValueError('FPS must be a positive finite number.')
    if not isinstance(parents, (list, tuple)) or len(parents) != 24:
        raise ValueError('Skeleton metadata must contain 24 parent indices.')
    if any(isinstance(parent, (bool, np.bool_)) or not isinstance(parent, (int, np.integer)) for parent in parents):
        raise ValueError('Skeleton parents must be integers.')
    if parents[0] != -1 or any(parent < 0 or parent >= 24 for parent in parents[1:]):
        raise ValueError('Skeleton requires root 0 with parent -1 and valid other parents.')
    for index in range(1, 24):
        seen = set()
        current = index
        while current != 0:
            if current in seen:
                raise ValueError('Skeleton parents contain a cycle.')
            seen.add(current)
            current = parents[current]
    return {'joints':joints[0].astype(float, copy=True),
            'centers':centers[0].astype(float, copy=True), 'fps':float(fps),
            'parents':list(parents), 'object_name':object_name, 'metadata':metadata}


def load_motion(path, trusted_input=False):
    if not trusted_input:
        raise ValueError('NPY dictionaries use pickle. Pass --trusted-input only for an output you trust.')
    source = Path(path)
    if source.suffix.lower() != '.npy':
        raise ValueError('Expected a trusted generated .npy file.')
    value = np.load(str(source), allow_pickle=True)
    if not isinstance(value, np.ndarray) or value.shape != ():
        raise ValueError('Expected a scalar NPY dictionary.')
    return validate_motion(value.item())


def check_destination(directory):
    directory = Path(directory)
    for name in NAMES:
        if (directory/name).exists() or (directory/name).is_symlink():
            raise ValueError('Preview output already exists; choose a fresh --output-dir.')
    return tuple(directory/name for name in NAMES)


def render(motion_path, output_dir, trusted_input=False):
    """Draw saved positions directly: no retiming, interpolation or model calls."""
    start = time.monotonic()
    movie, poster, report_path = check_destination(output_dir)
    source = Path(motion_path)
    original_hash = digest(source)
    motion = load_motion(source, trusted_input)
    # Keep the optional media stack out of import-time/offline NumPy tests.
    import imageio.v2 as imageio
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Line3DCollection

    joints, centers = motion['joints'], motion['centers']
    count, fps = len(joints), motion['fps']
    times = np.arange(count)/fps
    height = centers[:,2]-centers[0,2]
    metadata = motion['metadata']
    goal = metadata.get('custom_goal', {})
    plan = metadata.get('planned_lift_validation', {}).get('retimed_plan', {})
    hold_start, hold_end = plan.get('hold_start_frame'), plan.get('hold_end_frame')
    hold_valid = all(isinstance(value, int) and not isinstance(value, bool) for value in (hold_start, hold_end))
    hold_valid = hold_valid and 0 <= hold_start < hold_end < count
    selected_poster = hold_end if hold_valid else count//2
    edges = [(motion['parents'][index], index) for index in range(1,24)]
    all_points = np.concatenate((joints.reshape(-1,3),centers),axis=0)
    low, high = all_points.min(0), all_points.max(0)
    middle = (low+high)/2
    half = max(float(np.max(high[:2]-low[:2]))/2+.2, .55)
    zlow, zhigh = min(-.05,float(low[2])-.05), max(1.,float(high[2])+.12)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig = plt.figure(figsize=(11.2,7),dpi=100,facecolor='#f4f7fb')
    scene = fig.add_axes([.04,.21,.49,.60],projection='3d',facecolor='#f4f7fb')
    timeline = fig.add_axes([.63,.29,.32,.39],facecolor='white')
    fig.text(.05,.93,'Trial 01 | saved motion result',fontsize=22,weight='bold',color='#14253d')
    fig.text(.05,.875,'Actual saved human joints and object path; CPU playback only',fontsize=12,color='#41556e')
    scene.set(xlim=(middle[0]-half,middle[0]+half),ylim=(middle[1]-half,middle[1]+half),
              zlim=(zlow,zhigh),xlabel='X (m)',ylabel='Y (m)',zlabel='Z (m)')
    scene.set_box_aspect((2*half,2*half,zhigh-zlow))
    scene.view_init(elev=19,azim=-57)
    scene.tick_params(labelsize=8)
    scene.set_title('Blue: body joints    Orange: object center',fontsize=11,pad=12)
    xx, yy = np.meshgrid(scene.get_xlim(),scene.get_ylim())
    scene.plot_surface(xx,yy,np.zeros((2,2)),color='#d9e4ef',alpha=.23,shade=False)
    bones = Line3DCollection([],colors='#2869ad',linewidths=2.5)
    scene.add_collection3d(bones)
    markers = scene.scatter([],[],[],s=15,color='#2869ad',depthshade=False)
    hands = scene.scatter([],[],[],s=35,color='#c74d72',depthshade=False)
    object_marker = scene.scatter([],[],[],s=95,marker='D',color='#df8b20',edgecolor='#92530d',depthshade=False)
    timeline.plot(times,height,color='#df8b20',lw=2.5,label='Saved object center')
    if hold_valid:
        timeline.axvspan(hold_start/fps,hold_end/fps,color='#65b58d',alpha=.2,
                        label='Planned hold ({:.1f} s)'.format((hold_end-hold_start)/fps))
    timeline.axhline(0,color='#bdc8d4',lw=1)
    cursor = timeline.axvline(0,color='#2869ad',lw=1.5)
    point, = timeline.plot([0],[height[0]],'o',color='#92530d',ms=6)
    ymin, ymax = min(-.01,float(height.min())-.015), max(.03,float(height.max())+.025)
    timeline.set(xlim=(0,times[-1]),ylim=(ymin,ymax),xlabel='Saved frame time (s)',ylabel='Object lift from initial Z (m)')
    timeline.set_title('Object height in the saved output',pad=12,fontsize=11)
    timeline.grid(alpha=.18)
    timeline.legend(loc='upper right',fontsize=8)
    stamp = fig.text(.63,.77,'',fontsize=12,color='#14253d')
    goal_description = ''
    if isinstance(goal,dict) and isinstance(goal.get('lift_height_m'),(int,float)) and isinstance(goal.get('hold_duration_s'),(int,float)):
        goal_description = 'Requested: {:.2f} m lift / {:.1f} s hold'.format(goal['lift_height_m'],goal['hold_duration_s'])
    fig.text(.63,.20,goal_description,fontsize=11,color='#41556e')
    fig.text(.05,.115,'Skeleton and marker view only. No dataset meshes. Physical grasp/release is not verified.',fontsize=10,color='#41556e')
    fig.text(.05,.075,CREDIT,fontsize=9,color='#41556e')
    fig.text(.05,.043,'Adaptation: mesh-free skeletal visualization. Body media terms: CC BY 4.0 (see accompanying credits).',fontsize=8,color='#64748b')
    try:
        with imageio.get_writer(str(movie),fps=fps,codec='libx264',quality=8,
                                pixelformat='yuv420p',macro_block_size=2) as writer:
            for index in range(count):
                bones.set_segments([[joints[index,a],joints[index,b]] for a,b in edges])
                markers._offsets3d = joints[index].T
                hands._offsets3d = joints[index,22:24].T
                object_marker._offsets3d = centers[index:index+1].T
                cursor.set_xdata([times[index],times[index]])
                point.set_data([times[index]],[height[index]])
                stamp.set_text('Frame {:03d}/{:03d}\nTime {:.2f} s  |  {} FPS'.format(index,count-1,times[index],'{:g}'.format(fps)))
                fig.canvas.draw()
                pixels = np.asarray(fig.canvas.buffer_rgba())[...,:3].copy()
                writer.append_data(pixels)
                if index == selected_poster:
                    imageio.imwrite(str(poster),pixels)
                if index % 90 == 0:
                    print('Rendered {}/{} saved frames'.format(index+1,count),flush=True)
    finally:
        plt.close(fig)
    if digest(source) != original_hash:
        raise RuntimeError('Source motion changed during rendering; inspect preserved outputs.')
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report = {'status':'RENDERED_SAVED_RESULT','source_file':source.name,'source_sha256':original_hash,
              'video':movie.name,'poster':poster.name,'frames':count,'fps':fps,
              'playback_duration_s':count/fps,'source_span_s':(count-1)/fps,
              'resolution':[1120,700],'object_name':motion['object_name'],
              'trajectory_kind':'saved human joint positions and saved interpolated object trajectory',
              'render_style':'mesh-free skeleton and diamond marker for object center; no invented geometry',
              'coordinate_frame':str(metadata.get('coordinate_frame','see source metadata')),
              'retiming_applied':False,'new_simulation_run':False,'API_calls':0,'models_loaded':False,
              'physical_success_verified':False,'phase_sync_verified':False,
              'body_credit':CREDIT,'body_license_url':BODY_LICENSE,
              'body_media_license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/',
              'changes':'Saved joint positions drawn as a skeleton; body/object meshes and scene geometry omitted.',
              'render_elapsed_s':round(time.monotonic()-start,3),
              'render_max_rss_mib':round(rss/(1024*1024 if sys.platform=='darwin' else 1024),3),
              'source_unchanged':True}
    with report_path.open('x') as target:
        json.dump(report,target,indent=2,allow_nan=False);target.write('\n')
    print('Saved-result preview: '+str(movie))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motion',type=Path,required=True,help='Trusted generated NPY dictionary.')
    parser.add_argument('--output-dir',type=Path,required=True,help='Fresh preview destination.')
    parser.add_argument('--trusted-input',action='store_true',help='Acknowledge that loading this trusted NPY dictionary uses pickle.')
    args = parser.parse_args(argv)
    if not args.trusted_input:
        parser.error('Loading an NPY dictionary uses pickle; --trusted-input is required for trusted outputs only.')
    try:
        render(args.motion,args.output_dir,args.trusted_input)
    except (ValueError,OSError,KeyError,TypeError) as error:
        parser.exit(1,'PreviewError: '+str(error)+'\n')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
