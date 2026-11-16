# Development guide

Start with the independent offline demo and learn the contract before adding model calls. Keep changes in this companion repository; leave the original project, environments, and successful run directories intact.

## Code map

| Component | Responsibility |
| --- | --- |
| `trial_01/launch_trial.py` | CLI modes and one-run entry point |
| `trial_01/launcher/core.py` | Preflight, API messages, strict proposal parsing, validation, run manifests |
| `trial_01/launcher/settings.py` | Private path config and published integrity expectations |
| `trial_01/launcher/runtime.py` | Deferred heavy imports, one dispatch, artifact checks |
| `trial_01/launcher/recovery.py` | Narrow saved-plan recovery with preserved evidence |
| `trial_01/executor_code/waypoint_validation.py` | CPU argument and lift/hold validation |
| `trial_01/executor_code/protomotios_generate_multi_object.py` | Adapted InterPose interaction executor |
| `runtime/` | Simulator subprocess setup, official entry points, evidence hooks |
| `patches/` | Changes applied to the pinned external repositories |

## Make a second dataset example

1. Copy trusted scene inputs into a new private scene directory. Preserve the scene name used by the floor-height metadata. Save the source provenance and SHA256 values.
2. Keep the existing object for the first change. Add a new `custom_instruction` and matching `custom_goal` in the environment-state JSON. Do not alter only the text while leaving an incompatible numeric goal.
3. Use a fresh run name. Run full preflight and dry-run, inspect planned waypoints, and only then explicitly execute one interaction.
4. Review the resulting body and object trajectories, clock evidence, contact/penetration behavior, and task outcome. Keep success claims separate from valid serialization.
5. Record the configuration, commit, asset hashes, prompt, accepted plan, first failed command if any, and validation result. Publish only cleared files.

Use [the goal example](../configs/lift_hold_goal.example.json) as a field reference. A goal has this structure; replace the center with the actual initial object center from trusted input, rather than copying invented coordinates:

```json
{
  "action": "lift_hold_return_release",
  "object": "floorlamp",
  "center_xyz_m": [0.0, 0.0, 0.0],
  "lift_height_m": 0.15,
  "hold_duration_s": 5.0,
  "release_after_placement": true,
  "settle_duration_s": 1.0,
  "hand_withdraw_duration_s": 1.0,
  "hand_withdraw_distance_m": 0.1
}
```

This is an illustrative **schema**, not runnable floorlamp scene coordinates. For example, the instruction can request: “Lift the floorlamp 15 cm, hold it for five seconds, return it to its original position, then release it.” The supported action returns the object before release; it is not a free-drop implementation.

The scenario basename must match `<sequence>_pidx_<index>`, and the sequence's object token, JSON object name, goal object, and initial NPY object key must agree. The initial dictionary must contain the expected human joint/pose/quaternion fields and one object with center and quaternion. Preflight is deliberately strict about this identity.

## Change an object or behavior

Changing an object requires compatible rest geometry, scene metadata, a trusted initial state/pose, naming, orientation, contact targets, and enough reachability/clearance. A new noun in the prompt is insufficient. Begin with an object already supported by the prepared InterPose assets; validate its geometry and contact behavior before increasing task complexity.

Changing the action requires coordinated changes to goal schema, prompt, tool contract if needed, validators, executor timing/contact behavior, metadata, artifact checks, and tests. The current protocol permits one object, fixed planned pelvis and object X/Y, one rise/hold/return, and a maximum 900-frame planning budget. These restrictions belong to this exercise, not to every InterPose capability.

## Check changes in increasing cost order

```bash
python -I -B -m unittest discover -s tests -v
python -I -B scripts/offline_demo.py --output .local/changed_plan_check.json
```

Then validate configured inputs without API, test the simulator separately if its code changed, and run one small explicit live example only when those checks pass. Keep download, extension build, model load, inference, and export timings separate. Preserve the first error and fix the smallest relevant component; do not change unrelated package versions to make an error disappear.

Published code hashes intentionally detect edits. Verify the package manifest with:

```bash
python scripts/update_package_manifest.py
```

After reviewing an intentional change to this repository's code, explicitly regenerate its package manifest:

```bash
python scripts/update_package_manifest.py --write
```

This does not accept arbitrary external dependency changes. External expected hashes require a separately reviewed update, the corresponding pin/patch and provenance, and dependency tests. Finally, regenerate the private runtime manifest using `configure_runtime.py`. Do not edit that private manifest to bypass a mismatch.

## Recovery and publication

A failed run remains evidence. A reused name is rejected rather than overwritten. The CLI exposes `--prepare-recovery --run-name NAME` and `--resume-saved-plan --run-name NAME` for the narrow supported saved-plan case; inspect their checks before use. Never repeatedly resume a partially dispatched simulator as if it had not run.

Keep `.local/`, `external/`, environments, credentials, generated runs, licensed body/scene data and dense meshes out of public commits. Check staged files, paths, output sizes, attribution and history before a public push. The supplied `.gitignore` helps but does not establish redistribution rights.
