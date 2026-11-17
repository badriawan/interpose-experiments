# GitHub package execution record

Date: 2026-11-16. Target: `badriawan/interpose-experiments`, public.

## Status

- Local package preparation: **PASS**.
- Live GPU/API reproduction of the new portable adapter: **NOT RUN**.
- Public GitHub publication: **PASS** on 2026-11-17; public `main` verified after push.

## Completed work

Created this independent companion repository without changing the original InterPose datasets, environments, simulator sources, drivers or system CUDA. Ported the experiment's launcher/configuration into relative package paths, retained the adapted official executor, supplied exact source pins and two reviewable patches, and separated the parent/simulator interpreters. Added English usage, setup, development, schema, troubleshooting, licensing and publishing documentation.

Included a synthetic CPU example and a clearly labeled original box/height-curve MP4 and PNG. Preserved the real floorlamp preview privately under ignored `.local/review_assets/`; publication rights for all rendered assets remain unresolved. No original model, SDK, weight, initial NPY, dense mesh, generated trajectory, API response or credential is in the public file set.

## Commands and evidence

Commands were run from the package root unless stated otherwise. `PARENT_PYTHON` below denotes the existing isolated InterPose Python 3.8.20 interpreter; no environment was installed or upgraded.

| Command/check | Result | Private evidence |
| --- | --- | --- |
| `PARENT_PYTHON -I -B -m unittest discover -s tests -v` | 21 tests PASS | `.local/audit/cpu_tests_final.log` |
| `PARENT_PYTHON -I -B scripts/offline_demo.py` | Synthetic validation PASS; no generated motion | `.local/offline_demo.json` |
| `PARENT_PYTHON -I -B scripts/make_demo_video.py` | MP4 and poster generated; poster visually inspected | `media/offline_waypoints.{mp4,png}` |
| `git archive` pinned base paths; `git apply --check`; apply and compare hashes | Both patches PASS; 16 source hashes matched | `.local/audit/patch_closure.json` |
| `PARENT_PYTHON -I -B scripts/update_package_manifest.py --write` then verification | Reviewed package code recorded; verification PASS | `.local/audit/package_manifest_final.log` |
| `PARENT_PYTHON -I -B scripts/configure_runtime.py` | Config and published code/checkpoint/config hashes PASS; no key read | `.local/runtime_manifest.json` |
| `PARENT_PYTHON -I -B trial_01/launch_trial.py --preflight` | PASS against existing read-only assets | `.local/audit/preflight_final.log` |
| `PARENT_PYTHON -I -B trial_01/launch_trial.py --dry-run` | PASS; no API/model construction | `.local/audit/dry_run_final.log` |
| Staged names/bytes, credential-pattern, private-path and excluded-artifact audit | PASS; matched values never emitted | `.local/audit/staged_audit.json` |

The combined final CPU suite took about 0.58 s; preflight about 0.19 s and dry-run about 0.32 s on the preparation machine. Command-level timings are in `.local/audit/final_checks.json`. Total wall time and peak RAM/VRAM were not comprehensively measured. GPU generation and API calls were not used for packaging.

## First failures and limited fixes

Review found the source helper rejected its own patch-added files on repeated preparation. It now recognizes only the exact expected additions, verifies their bytes/modes, and rejects tampering and unrelated files; three regression tests cover these cases. This changed packaging code only. No package version was changed.

The first remote availability probe, `git ls-remote` against the intended HTTPS target, returned `Repository not found`. GitHub CLI/token/helper access was unavailable. A read-only SSH probe stopped at host-key verification; no host key or authentication setting was changed. Browser inventory reported its access host unavailable. No remote repository was created or pushed.

## Bottlenecks and rollback

**Observed during initial preparation:** GitHub authentication/repository availability blocked publication; this was resolved for the successful push on 2026-11-17. Full GPU/API execution and clean-machine installation remain unverified. **Unresolved:** redistribution terms/credits for the original rendered object assets. No download/build/CPU/GPU throughput bottleneck was measured during packaging; source preparation uses local test fixtures rather than a full remote download.

All changes are confined to this isolated repository. Removing or archiving it reverses the packaging work; ignored private assets/config/cache remain outside any public Git export. No original source/environment/data repair is needed. The source helper operates only when explicitly invoked with `--fetch`; it never resets incompatible existing checkouts.

## Publication follow-up — 2026-11-17

After the destination became accessible, `git fetch origin main` found the GitHub initialization commit `5079f50`, containing only a title-only README. `git merge --allow-unrelated-histories -X ours origin/main` retained that remote history and the full prepared README. The resulting tree was identical to the audited package tree.

`GIT_TERMINAL_PROMPT=0 git push -u origin main` succeeded without force and published merge commit `f8ae53e`. `git ls-remote origin refs/heads/main` matched the local commit. The public GitHub repository API confirmed `private=false` and `default_branch=main`. These documentation updates record the resolved publication status; they do not change runtime code or validation claims.

Next: validate the new full research runtime separately before claiming fresh GPU reproduction or policy readiness. Follow `docs/PUBLISHING.md` for routine reviewed updates.

## Trial 01 README and saved-result video — 2026-11-17

Rewrote the root README in simple English around the completed `lift_hold_001` experiment: original instruction, required external setup, private input preparation, configuration, preflight/dry-run, one generation command, exact NPY/JSON output locations, inspection and preview commands. The report explicitly distinguishes the historical failed planner launch and later successful saved-plan resume from a fresh direct execution. It preserves the observed body drift and incomplete hand withdrawal instead of claiming physical success.

Added `scripts/render_trial_result.py` and six focused tests. The renderer reads trusted saved positions, draws a skeleton and an object-center marker, and refuses to overwrite previews. Public `media/trial_01/preview_trial_01.{mp4,png,metadata.json}` was generated from the historical NPY whose SHA256 is `3e8d0512cf95360a801855b5ada17c97b6c9f8104cfbdff056ba9f23bae21930`. It contains 383 frames at 30 FPS, 1120×700 resolution, about 12.77 seconds. All frames decoded successfully and the poster was visually inspected. No meshes, models, API or simulator were loaded; the source hash stayed unchanged. Media credits record MPI, the SMPL-X Body CC BY 4.0 terms and the mesh-free adaptation. The earlier mesh-based preview remains private.

The actual render took 10.842 s with measured process max RSS 445.914 MiB. Peak VRAM was not measured; this was CPU rendering. No new package installations or version changes occurred. The combined suite passed 27 tests, including the tiny video roundtrip; existing dependencies emitted deprecation/resource warnings, without test failures. The new package manifest covers 20 code files, and the private runtime was reconfigured against it.

README examples were checked for shell/Python syntax. The input-copy block was run in a private sandbox against the existing trusted original assets; preflight of that copied scene passed. The output-inspection block read the actual completed clip and confirmed the documented shapes. Evidence is under `.local/audit/readme_input_smoke.log`, `readme_input_preflight.log`, and `readme_output_inspection.log`.

One draft-writing command failed with `SyntaxError: unterminated triple-quoted string literal` because its outer shell heredoc delimiter collided with an embedded README example. The document was subsequently written through a structured patch. The only incidental artifact was a new empty log and its new empty directory outside the package; their creation times and emptiness were verified before removing them. No experiment, environment or original data file was changed.

Rollback: revert this documentation/renderer commit to remove the new guide and public preview. The original experiment and its saved outputs require no restoration. This update records and visualizes existing results; it does not establish a fresh end-to-end GPU run on another computer.
