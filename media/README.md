# Preview provenance

## Trial 01: actual saved-result preview

[`trial_01/preview_trial_01.mp4`](trial_01/preview_trial_01.mp4) and its PNG show the actual saved human joint positions and object-center trajectory from the completed `lift_hold_001` run. They contain 383 frames at 30 FPS, about 12.77 seconds. Source basename and SHA256 are recorded in [`trial_01/preview_trial_01.metadata.json`](trial_01/preview_trial_01.metadata.json); the source NPY itself is not redistributed.

The blue skeleton is drawn directly from saved joints. The orange diamond is the saved floorlamp center, not a lamp mesh. This adaptation removes body/object meshes and room geometry; it applies no retiming, new motion generation or simulation. The saved object trajectory is interpolated by the original interaction pipeline. Physical grasp/release and exact body/object synchronization remain unverified.

**SMPL-X Body credit: Max Planck Institute for Intelligent Systems.** The body representation is used under the [SMPL-X Body license](https://smpl-x.is.tue.mpg.de/bodylicense.html), [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). Changes: a mesh-free skeletal drawing of saved joints, with a geometric marker in place of the object mesh. Retain this credit, license link and change description when sharing the body visualization. The root code license does not replace these media terms. This does not grant redistribution rights to the separately downloaded models or source dataset.

Regenerate this style for a trusted output using `scripts/render_trial_result.py --motion FILE.npy --output-dir NEW_DIRECTORY --trusted-input`. Only the CPU media dependencies in `requirements-media.txt` are needed for rendering. The script refuses existing preview files.

## Synthetic offline example

`offline_waypoints.mp4` and `offline_waypoints.png` visualize original synthetic box coordinates. Regenerate them using `scripts/make_demo_video.py` and optional `requirements-media.txt`. The animation linearly interpolates validated waypoints; it is a schematic, with no SMPL-X mesh, learned motion, LLM or physics. Its 0.2 m lift differs from the historical floorlamp experiment's 0.15 m lift.

## Original mesh-based preview

The original `preview_lift_hold_001.mp4` remains private under `.local/review_assets/` on the preparation machine. It is excluded from Git because exact rendered object-asset terms and required credits still need resolution. This does not imply all SMPL-X media is prohibited: the [Body license](https://smpl-x.is.tue.mpg.de/bodylicense.html) and [Model license](https://smpl-x.is.tue.mpg.de/modellicense.html) have different scope. Do not copy licensed models or dataset meshes into a public repository to make a preview work.
