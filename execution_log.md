# GitHub package execution record

Date: 2026-11-16. Target: `badriawan/interpose-experiments`, public.

## Status

- Local package preparation: **PASS**.
- Live GPU/API reproduction of the new portable adapter: **NOT RUN**.
- Public GitHub publication: **BLOCKED** by unavailable authenticated publishing access and absent target repository.

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

**Observed:** GitHub authentication/repository creation blocks publication. Full GPU/API execution and clean-machine installation remain unverified. **Unresolved:** redistribution terms/credits for the original rendered object assets. No download/build/CPU/GPU throughput bottleneck was measured during packaging; source preparation uses local test fixtures rather than a full remote download.

All changes are confined to this isolated repository. Removing or archiving it reverses the packaging work; ignored private assets/config/cache remain outside any public Git export. No original source/environment/data repair is needed. The source helper operates only when explicitly invoked with `--fetch`; it never resets incompatible existing checkouts.

Next: complete local Git publication prerequisites using `docs/PUBLISHING.md`, push without force, then verify the public README/video and remote commit. Validate the new full research runtime separately before claiming fresh GPU reproduction or policy readiness.
