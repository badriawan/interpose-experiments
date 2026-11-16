# Getting started

The quickest runnable example checks a synthetic lift plan on the CPU. It is independent of the original project directory and uses no paid services.

## 1. Create a small environment

From the repository root:

```bash
python3.10 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-offline.txt
```

Python 3.8–3.11 and NumPy 1.24.3 are the supported range for this example. Do not install the full simulator stack into this environment. If you already have an appropriate NumPy environment, you can use its Python directly.

## 2. Validate a plan

```bash
python -I -B scripts/offline_demo.py
```

Expected terminal status: `SYNTHETIC_VALIDATION_PASS`. The script saves `.local/offline_demo.json` and reports that no motion was generated. It checks malformed arguments, the 30 Hz waypoint timeline, a five-second plateau, and the executor's frame adjustment against the same lift/hold validator.

The fixture raises a synthetic box by 0.20 m, holds for five seconds, and returns it. These are invented coordinates for testing; they are not the historical floorlamp scene. A passing result establishes valid planning data, not reachable grasps or contact physics.

Existing reports are preserved. To run again:

```bash
python -I -B scripts/offline_demo.py --output .local/offline_demo_002.json
```

## 3. Run the checks and watch the preview

```bash
python -I -B -m unittest discover -s tests -v
```

Open [the synthetic waypoint video](../media/offline_waypoints.mp4). Its moving box and height curve illustrate the plan only. There is no human-body model or robot policy in this video.

## 4. Move to actual generation

Read [full setup](FULL_SETUP.md) before using `trial_01/launch_trial.py`. Its `--preflight` and `--dry-run` modes require the prepared research runtime and trusted scene inputs. They are different from this independent offline demo. Only `--execute` makes the real planner request and dispatches generation.

All `.local/` reports, private configuration, external checkouts, and `trial_01/runs/` outputs are excluded from Git. Review files explicitly before publishing any new dataset or video.
