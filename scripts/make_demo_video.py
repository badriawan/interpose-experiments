#!/usr/bin/env python3
"""Render own synthetic waypoint data; this is not a generated motion clip."""
import argparse
import importlib.util
from pathlib import Path
import sys

import imageio.v2 as imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'media')
    args = parser.parse_args()
    directory = args.output_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    movie = directory/'offline_waypoints.mp4'
    poster = directory/'offline_waypoints.png'
    if movie.exists() or poster.exists():
        parser.error('Preview exists; select a fresh --output-dir.')
    spec = importlib.util.spec_from_file_location('offline_demo', str(ROOT/'scripts/offline_demo.py'))
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    goal, plan = demo.fixture()
    result = demo.validate(plan, goal)
    waypoints = np.asarray(result['retimed_waypoints'][0], dtype=float)
    frames = np.arange(int(waypoints[-1,0])+1)
    seconds = frames/30.
    height = np.interp(frames, waypoints[:,0], waypoints[:,3])
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':'#e8edf5',
                         'axes.labelcolor':'#c7d2e5','xtick.color':'#c7d2e5','ytick.color':'#c7d2e5'})
    fig, (scene, timeline) = plt.subplots(1, 2, figsize=(11.2,6.3), dpi=100,
        gridspec_kw={'width_ratios':[1,2]})
    fig.patch.set_facecolor('#101827')
    fig.subplots_adjust(left=.06,right=.97,bottom=.21,top=.75,wspace=.28)
    fig.text(.06,.9,'InterPose experiments / Offline quickstart',fontsize=21,weight='bold')
    fig.text(.06,.83,'SYNTHETIC WAYPOINT PREVIEW  •  no LLM, model or physics',fontsize=13,color='#65d6b3')
    for ax in (scene,timeline):
        ax.set_facecolor('#172337')
        for spine in ax.spines.values():spine.set_color('#3a4c67')
    scene.set(xlim=(-.5,.5),ylim=(.35,.95),ylabel='Object center Z (m)',xticks=[])
    scene.axhline(.4,color='#8798ad',lw=2)
    box=Rectangle((-.13,height[0]-.1),.26,.2,facecolor='#63b6ff',edgecolor='white')
    scene.add_patch(box);scene.set_title('Own synthetic box',color='#e8edf5',pad=15)
    timeline.plot(seconds,height,color='#65d6b3',lw=3)
    timeline.scatter(waypoints[:,0]/30.,waypoints[:,3],color='#e8edf5',s=32,zorder=3)
    timeline.set(xlim=(0,seconds[-1]),ylim=(.45,.78),xlabel='Time (s)',ylabel='Object center Z (m)')
    timeline.set_title('Lift → hold 5 seconds → return',color='#e8edf5',pad=15)
    cursor=timeline.axvline(0,color='#ffcd75',lw=2)
    dot,=timeline.plot([0],[height[0]],'o',color='#ffcd75',ms=8)
    stamp=fig.text(.06,.13,'',fontsize=14)
    fig.text(.06,.075,'Linear schematic interpolation; not SMPL-X or a MaskedMimic result.',fontsize=11,color='#a4b3c9')
    with imageio.get_writer(str(movie),fps=30,codec='libx264',quality=8,macro_block_size=2) as writer:
        for frame,t,z in zip(frames,seconds,height):
            box.set_y(z-.1);cursor.set_xdata([t,t]);dot.set_data([t],[z])
            stamp.set_text('t = {:.2f} s   |   Z = {:.3f} m'.format(t,z))
            fig.canvas.draw()
            rgb=np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy()
            writer.append_data(rgb)
            if frame==int(waypoints[1,0]):imageio.imwrite(str(poster),rgb)
    plt.close(fig)
    print('Synthetic preview: '+str(movie))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
