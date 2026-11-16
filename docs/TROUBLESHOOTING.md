# Troubleshooting

Preserve the first failed command and relevant error. Separate a proven bottleneck from a hypothesis, and change only the affected layer.

| Symptom | What to inspect | Next bounded step |
| --- | --- | --- |
| NumPy cannot install in quickstart | Python version and wheel compatibility | Use Python 3.8–3.11 for NumPy 1.24.3; keep the full runtime separate |
| Offline report already exists | Chosen output filename | Use a new `.local/` report name |
| Private configuration missing/invalid | Example schema, required paths, model field | Edit `.local/runtime.json`; no key value belongs in it |
| Published hash mismatch | Exact named file, source pin and applied patch | Compare against the supplied pin/patch; preserve local edits, do not bypass the check |
| Wrong Python environment | `sys.prefix` versus `paths.interpose_python` | Invoke the configured parent interpreter directly |
| Scene/model/checkpoint missing or LFS pointer | Real bytes, filenames, layout and authorized downloads | Complete the specific asset; do not treat a small pointer as a model |
| Checkpoint loads but config fails | Matching `config.yaml`, its relative paths and source version | Keep the checkpoint's training configuration beside it or at the supported parent-parent location |
| `isaacgym` import or native library failure | SDK path, simulator Python, import order, driver and runtime library paths | Test the SDK alone, importing it before Torch; avoid changing the system CUDA without evidence |
| Extension build is slow/fails | Compiler, Torch/CUDA compatibility, build log and cache disk space | Time the build separately; correct the named compiler/dependency problem |
| Planner proposal limit reached | Preserved `planner/attempt_*` responses and rejection reasons | No generation was dispatched if dispatch count is zero; fix the contract/input and use a fresh run |
| API failure | Reported HTTP status/class, project funding and model access | Fix access outside public logs; API errors are not retried as invalid plans |
| Run already exists | Existing manifest and partial outputs | Preserve it and select a new run name |
| Program finishes but task looks wrong | Body drift, object contact, penetration and synchronization | Record a quality/physical failure even when artifact checks pass |
| ResMimic cannot read an NPY | Actual target loader schema and robot definition | Use a verified converter; changing the extension is not conversion |

## Inspect a live failure

Read `trial_01/runs/<name>/manifest.json` first. It records the status, error type and dispatch count. Planner errors are under `planner/`; simulator conversion/evaluation logs and `execution_evidence.json` are beneath `output/<episode>/maskedmimic_res/task_0/`.

A converter can catch a per-file exception and still exit zero. The bridge therefore also checks for its expected nonempty output and conversion evidence. A zero process exit is only one piece of the result.

The runtime is headless by design. A missing visible window does not itself imply failure. Conversely, a nice preview does not establish physical task completion. Compare reference trajectories, raw recorder evidence and the actual task outcome.

## Logs and secrets

The launcher redacts known API-key patterns and strips API credentials from child environments. Treat logs as private until reviewed: they can still contain machine paths, scene content, prompt text and asset names. Never publish a raw key or ask someone to paste it into an issue.
