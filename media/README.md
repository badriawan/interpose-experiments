# Preview provenance

`offline_waypoints.mp4` and `offline_waypoints.png` visualize original synthetic box coordinates. Regenerate them using `scripts/make_demo_video.py` and optional `requirements-media.txt`. The animation linearly interpolates validated waypoints; it is a schematic, with no SMPL-X mesh, learned motion, LLM or physics. Its 0.2 m lift differs from the historical floorlamp experiment's 0.15 m lift.

The original `preview_lift_hold_001.mp4` remains private under `.local/review_assets/` on the preparation machine. It is excluded from Git because exact rendered object-asset terms and required credits still need resolution. This does not imply all SMPL-X media is prohibited: the [Body license](https://smpl-x.is.tue.mpg.de/bodylicense.html) and [Model license](https://smpl-x.is.tue.mpg.de/modellicense.html) have different scope. Do not copy licensed models or dataset meshes into a public repository to make a preview work.
