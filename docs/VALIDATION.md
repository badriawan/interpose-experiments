# Validation status and limits

The release separates the tests of the portable package from results produced earlier in the original research workspace.

## Current package checks

The independent CPU path has been exercised using the actual waypoint validator and the trusted executor's extracted `adjust_frames` method. The combined CPU suite contains the original 21 tests plus six saved-result renderer checks. They cover valid and invalid plans, malformed/nonincreasing timing, isolation from heavy imports/API/key access, relocation to a copied path, package/dependency tamper rejection, and safe source preparation. Source-preparation tests use local fixture repositories to exercise pins, safe patching, patch-added-file idempotence, and preservation of incompatible checkouts without network access. Runtime wiring tests check interpreter selection, credential-environment removal, the private converter XML path, finite headless settings, and refusal of foreign bootstrap scripts. Renderer checks cover trusted-input requirements, skeleton/array validation, source preservation, output preservation, and a tiny H264 decode; the rendering smoke test is skipped if optional media packages are absent. The supplied patches were also applied against clean pinned base trees, and the resulting 16 dependency-file hashes matched their published expectations.

Local logs and audit artifacts live under ignored `.local/audit/`. Consult the release's execution record for the exact commands and final check counts. A passing offline suite does not test the LLM, body assets, checkpoint loading, GPU physics, or a clean installation of the full dependency stack.

The portable full runtime has not been rerun end to end on a fresh machine for this release. Local full preflight and `--dry-run` passed using the original, read-only licensed assets. Those checks read no API credential and constructed no model. They do not replace a full GPU run. No API credit is spent by the offline example or configuration helper.

## Historical lift/hold result

The original `lift_hold_001` produced a 383-frame clip at 30 Hz for a 0.15 m floorlamp lift and a five-second planned hold. The body pelvis drifted by approximately 0.207 m. Planned stationary pelvis constraints therefore did not establish actual body stationarity. The output contains simulated human motion and a generated object trajectory, but physical object lifting was not established.

The README's saved-result video was rendered directly from that historical NPY using a skeleton and object-center marker. It has 383 fully decoded frames at 30 FPS, 1120×700 resolution. Rendering neither alters the source nor reruns the API, body model or simulator. The original mesh-based preview stays private; the public result video is a different view of the same stored trajectory.

A later ResMimic reference conversion/tuning produced 1,525 frames at 120 Hz with 29 DOFs and 38 links. That smoother reference was tested with a robot-only policy: the maximum root-XY tracking error was approximately 0.884 m and the relevant threshold failed. The physical object task was not successfully completed. These are historical observations, not a promise that this repository reproduces them by running the CPU example.

## Meaning of a pass

| Observation | What it establishes |
| --- | --- |
| Synthetic validation passes | The tested planning contract and frame-adjustment checks accepted the fixture |
| Preflight passes | Configured inputs, selected assets, environment identity and code expectations passed CPU checks |
| Simulator evidence passes | Checkpoint/policy/recorder/clock observations passed their recorded checks |
| Artifacts verified | The expected fresh output files and bounded array/metadata checks passed |
| Animation looks plausible | A visual review result, which must be recorded separately |
| Physical task succeeds | Requires explicit contact/dynamics/task criteria; not established by the preceding rows |
| Robot policy tracks a reference | Requires its own policy test; smooth reference motion alone is insufficient |

## Next validation required

Before using clips as policy-training references, run the configured full pipeline in an isolated prepared environment, inspect body/object synchronization and contact, validate downstream retargeting against the correct loader, replay it, and measure policy tracking and physical task completion. Do not start long training merely because a file loads.
