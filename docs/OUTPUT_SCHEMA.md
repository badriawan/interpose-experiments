# Output files and interpretation

A real run is allocated under `trial_01/runs/<run-name>/`. Input snapshots, planner responses, the accepted plan, status manifests, and execution artifacts are kept together. These files are ignored by Git because they may contain licensed data or private scene content.

Typical output structure:

```text
trial_01/runs/<run-name>/
  manifest.json
  inputs/<scene>/{environment_state,motion_data}/...
  planner/attempt_*.json
  accepted_plan.json
  runtime_dispatch_started.json
  output/<episode>/
    <sequence>_pidx_<index>_task_0.npy
    <sequence>_pidx_<index>_task_0.json
    objs_mesh/*.ply
    maskedmimic_res/task_0/
      trajectory_pose_aa_0_0.npz
      stage10_raw_trajectory.npz
      execution_evidence.json
      stage10_*_attempt_*.log
```

The default episode name follows `frl_apartment_4_sub17_floorlamp_001_0`. Paths are recorded in each run's manifest; inspect those records instead of assuming a file from another run is equivalent.

## Main `.npy` dictionary

The main NPY contains a Python dictionary saved by NumPy. Loading it requires `allow_pickle=True`: only load files you trust. NPY is a container, not a guarantee about schema, units, or safety.

For the bounded single-person output, let `B=1` and `T` be the saved frame count:

| Field | Expected shape | Meaning |
| --- | --- | --- |
| `human.joint_xyz` | `[1,T,24,3]` | Joint positions in meters |
| `human.pose_aa` | `[1,T,22,3]` | Axis-angle rotations in radians |
| `human.orientation` | `[1,T,1,4]` | Root quaternion, `wxyz` |
| `object.<name>.xyz` | `[1,T,3]` | Saved object center trajectory |
| `object.<name>.rotation` | `[1,T,4]` | Object quaternion, `wxyz` |
| `object.<name>.object_point` | `[1,N,4]` | Saved actual object positions at integer annotation frames |
| `object.<name>.planned_object_point` | `[1,N,4]` | Retimed planned annotations, retained separately |
| `metadata` | Dictionary | Schema, frame rate, model, units, task and verification flags |

Numeric arrays must be finite. The runtime checks array shapes and quaternion norms; dtype is inherited from the producer and must be inspected for each export rather than assumed to be uniformly float32.

The metadata writer uses schema `interpose-hoi-project/1.1`, 30 FPS, scene-normalized Z-up coordinates, nominal floor `z=0`, and SMPL-X v1.1 with the recorded gender and 16 betas. Root pose rotation is global; the remaining 21 pose rotations are parent-local. The 24 positional joints use SMPL-X indices `0..21,28,43`: the last two are `left_middle1` and `right_middle1`. They are not extra axis-angle joints. Exact names and parents are embedded in metadata.

Five seconds means **150 intervals** at 30 Hz; count endpoints carefully. The planned object hold, actual body motion, and simulator recording clocks are separate observations. `phase_sync_verified=false` and `physical_success_verified=false` remain explicit. The writer does not silently shift or synchronize dense trajectories.

## Other artifacts

| File | Purpose and limit |
| --- | --- |
| Task `.json` | Terminal environment state plus task fields; not the full motion |
| `trajectory_pose_aa_0_0.npz` | Official simulator pose/trans output used by the executor |
| `stage10_raw_trajectory.npz` | Raw official recorder buffers, actions, timestep, and observed clocks |
| `execution_evidence.json` | Checkpoint/policy/clock observations, process status and resource evidence |
| `objs_mesh/*.ply` | Reconstructed human/object mesh frames; expensive and subject to asset terms |
| `manifest.json` | Run state, dispatch count, inputs, verification and output hashes |

`ARTIFACTS_VERIFIED` means the expected fresh files and recorded bridge evidence passed the bounded checks. It does not certify fixed body position, grasp success, absence of penetration, or robot-policy tracking.

## ResMimic is a separate conversion

The NPY is a source clip, not a ready ResMimic policy input. Keep its metadata, source hashes, and relevant evidence alongside conversion outputs. A downstream adapter must read the actual target loader, map joint order and coordinate conventions, retarget to the robot, resample rotations appropriately, tune/smooth, then validate replay and physical policy tracking. `.pkl` and `.npz` are serialization formats; their required keys depend on that loader.

No ResMimic exporter or converted motion is shipped in this release. The historical tuned reference had 1,525 frames at 120 Hz, 29 DOFs, and 38 links. A robot-only policy test still failed its root-XY threshold (maximum error about 0.884 m); object lifting was not physically achieved. Smooth reference animation does not resolve this failure.
