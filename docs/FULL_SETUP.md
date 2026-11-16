# Full research setup

This path targets Linux, an NVIDIA GPU, and Isaac Gym Preview 4. It requires substantial external software and separately licensed data. The release provides code, fixed source pins, and observed environment snapshots; it is not a one-command installation or a clean-machine reproduction claim.

## 1. Inspect the machine first

Record OS, GPU/VRAM, driver, available RAM/disk, compiler, network access, and GUI/headless requirements. Keep existing environments. Do not change the system driver or CUDA to match a guessed package version. Validate the CUDA runtime shipped with the chosen PyTorch environment using a small GPU tensor operation.

The CPU quickstart has its own environment. The historical full experiment used two isolated environments:

| Component | InterPose parent | MaskedMimic simulator |
| --- | --- | --- |
| Python | 3.8.20 | 3.8.20 |
| NumPy | 1.24.3 | 1.23.5 |
| PyTorch | 2.0.0 | 2.2.0 |
| PyTorch CUDA runtime | 11.7 | 11.8 |
| OpenAI / AutoGen | 2.2.0 / 0.2.40 | Not used by simulator child |

[Parent snapshot](../environments/interpose-observed.yml) and [simulator snapshot](../environments/simulator-observed.yml) record the working machine's packages. They are references, not platform-independent lockfiles. Editable repositories and proprietary SDKs still need their own setup. Preserve the separate PyTorch/NumPy versions: they reflect observed compatibility with different parts of the pipeline, not arbitrary upgrades.

## 2. Inspect and prepare pinned sources

```bash
python scripts/prepare_sources.py
```

The default only lists source URLs and commits. To clone into new ignored `external/` directories and apply the supplied patches:

```bash
python scripts/prepare_sources.py --fetch
```

This command downloads source and declared submodules, with Git LFS smudging disabled. It does not install packages or download SDKs, model weights, or licensed data. Missing LFS assets must be resolved separately through authorized sources. Existing incompatible, staged, or unrelated modified checkouts are preserved and rejected rather than reset.

The key bases are:

| Source | Pinned commit |
| --- | --- |
| InterPose | `5ee373310a75fa15719959b2808f8d399f27ae16` |
| ProtoMotion_for_InterPose | `ad70a3785bf162c89a8df91eb79568770416f1d8` |
| SMPLSim | `b5c08720503ad5fff64050c4d289c42d947fcf8d` |
| SMPL-X code fork | `a5b8e4ac14f79f3f33fd2cf2a16e6f507146b813` |
| human_body_prior | `4c246d8a83ce16d3cff9c79dcf04d81fa440a6bc` |
| bps_torch | `00fcac3dffd294211d4ea0363eaf6c2ca4e068dc` |
| chamfer_distance | `f86f6f7cadd3aca642704573d1626c67ca2e2846` |

The pinned ProtoMotion fork lacks the needed Isaac Gym backend. The supplied patch adapts NVIDIA ProtoMotions source from commit `9062f0ae139767d9ac05cebf2253583e2652a56a`. Read its [provenance](../third_party/isaacgym_backend_PROVENANCE.md); the patch is not evidence that an unmodified fork runs this experiment.

## 3. Build environments one component at a time

Follow the pinned [InterPose instructions](https://github.com/Mael-zys/InterPose/tree/5ee373310a75fa15719959b2808f8d399f27ae16) and the pinned simulator source, using the snapshots to explain required versions. Work in new Conda prefixes. Install and test PyTorch first, then PyTorch3D, human_body_prior, BPS and its native dependencies, and the remaining imports. Use the pinned vendor code rather than a moving branch. Record each command, version rationale, download/build/test duration, and first failure.

Install or reuse Isaac Gym Preview 4 under its own terms; its SDK is not in this repository. Import Isaac Gym before Torch in its environment. Verify one basic SDK simulation before trying the HOI task. The packaged evaluation is explicitly headless. The executor uses `save_obj_only=True`, so it does not call Blender rendering; Blender GUI is not required for this path. Its visualization-module imports can still require Python dependencies. Optional rendered previews have separate dependencies.

Do not run an upstream installer blindly: it may assume older paths, compiler availability, or different package versions. The source helper is deliberately separate from installation so failures can be isolated.

## 4. Acquire and arrange assets

Obtain assets through the official links and any required account/license acceptance. Do not use another person's credentials or commit downloaded models. Required layout includes:

- [Pinned InterPose prerequisites](https://github.com/Mael-zys/InterPose/blob/5ee373310a75fa15719959b2808f8d399f27ae16/README.md#prerequisites): follow its processed-data and SMPL-X download links. Preserve the complete processed-data layout.
- [Pinned ProtoMotion SMPL instructions](https://github.com/Mael-zys/ProtoMotion_for_InterPose/blob/ad70a3785bf162c89a8df91eb79568770416f1d8/README.md#download-smpl-parameters): obtain SMPL v1.1.0 and follow the documented filename mapping.
- [Pinned ProtoMotion checkpoint instructions](https://github.com/Mael-zys/ProtoMotion_for_InterPose/blob/ad70a3785bf162c89a8df91eb79568770416f1d8/README.md#download-pretrained-models): download the paired pretrained model and configuration. A cloud link may require access; this package supplies no replacement credentials or unlicensed mirror.

```text
InterPose/
  data/smpl_all_models/smplx/SMPLX_MALE.npz
  data/smpl_all_models/smplx/SMPLX_FEMALE.npz
  processed_data/rest_object_geo/floorlamp.ply
  processed_data/replica_processed/scene_floor_height.json
ProtoMotion_for_InterPose/
  data/smpl/SMPL_NEUTRAL.pkl
checkpoint_directory/
  last.ckpt
  config.yaml
prepared_scene/frl_apartment_4/
  environment_state/sub17_floorlamp_001_pidx_0.json
  motion_data/sub17_floorlamp_001_pidx_0.npy
```

The official evaluator also searches the checkpoint's parent-parent for `config.yaml`. Keep the matching configuration; a checkpoint by itself is insufficient. Other processed-scene files and object metadata required by the upstream executor must also be present. The initial NPY is a trusted dictionary, not arbitrary downloaded code.

`smplx_root` must identify the same resolved model directory the executor uses at `InterPose/data/smpl_all_models/smplx`; preflight enforces this equality and checks the simulator SMPL model. If you keep models elsewhere, arrange an explicit local link without replacing existing files. `data_root` points to the prepared scene directory containing both subfolders. The required scene JSON must contain a matching `custom_instruction` and `custom_goal`; see [development](DEVELOPMENT.md). Original licensed scene inputs are not bundled.

For the first real example, select the original pair at `processed_data/replica_new/frl_apartment_4/{environment_state,motion_data}/sub17_floorlamp_001_pidx_0.{json,npy}`. The JSON belongs in `environment_state/`, and NPY in `motion_data/`. Copy only that pair into a new private scene folder, preserving its basename and the scene name `frl_apartment_4`. For a fresh destination, from this repository root:

```bash
mkdir -p .local/prepared_inputs/frl_apartment_4/environment_state
mkdir -p .local/prepared_inputs/frl_apartment_4/motion_data
cp -n external/InterPose/processed_data/replica_new/frl_apartment_4/environment_state/sub17_floorlamp_001_pidx_0.json .local/prepared_inputs/frl_apartment_4/environment_state/
cp -n external/InterPose/processed_data/replica_new/frl_apartment_4/motion_data/sub17_floorlamp_001_pidx_0.npy .local/prepared_inputs/frl_apartment_4/motion_data/
```

Inspect the trusted initial dictionary locally to obtain `object.floorlamp.xyz`. In the **copied** JSON, retain the original scene/human/object fields and add `custom_instruction` plus `custom_goal` using [the example fields](../configs/lift_hold_goal.example.json). Set `object` to `floorlamp`, center to that actual initial XYZ, lift to `0.15`, hold to `5.0`, and action to `lift_hold_return_release`. The example's synthetic box coordinates must not be copied as real scene coordinates. Set `data_root` to the absolute path of this new private `frl_apartment_4` directory. Preflight will reject mismatched centers, naming, or initial fields.

## 5. Configure local paths

```bash
mkdir -p .local
cp configs/runtime.example.json .local/runtime.json
```

Edit the copied JSON with your actual paths. `interpose_root` and `protomotions_root` must refer to the pinned, patched checkouts. `interpose_python` and `simulator_python` are the full paths to the two environment Python executables. `smplsim_root` points to pinned SMPLSim source; `isaacgym_python_root` points to the SDK's `python/` folder. Optional `paths.cxx` and `paths.vulkan_icd` select an existing compiler or Vulkan ICD without changing the system.

```bash
python scripts/configure_runtime.py --config .local/runtime.json
```

This checks the configured paths and published code hashes, including the expected checkpoint/configuration, then writes `.local/runtime_manifest.json`. It does not read the API key or run the models. Configure again only after reviewing an intentional configuration change. For a custom config location, set `INTERPOSE_LAB_CONFIG` for later commands as well.

## 6. Check inputs without spending API credit

Use the configured **parent** environment's Python in place of `/path/to/interpose-env/bin/python`:

```bash
/path/to/interpose-env/bin/python -I -B trial_01/launch_trial.py --preflight
/path/to/interpose-env/bin/python -I -B trial_01/launch_trial.py --dry-run
```

Preflight checks prepared inputs, required assets, environment prefix and integrity. Dry-run feeds a synthetic proposal through the planner validation path using those local inputs. Neither proves simulator compatibility or motion quality. Stop at the first failure and preserve its output.

## 7. Prepare API access and execute one run

The current bounded planner expects `gpt-4o`, the OpenAI Python SDK, and a funded API project. Store the key in the file named by `paths.key_file`, outside version control, owned by your user and readable only by that user (`chmod 600`). Do not paste the key into chat, commands, public logs, or scene JSON. The launcher reads it only during explicit live execution. API billing is separate from a ChatGPT subscription.

```bash
/path/to/interpose-env/bin/python -I -B trial_01/launch_trial.py   --execute --run-name lift_hold_001
```

Choose a new run name each time. There are at most three proposal attempts and one generation dispatch. Simulator children receive scrubbed API environment variables and block external Python socket connections; localhost is retained for distributed runtime communication. Logs and partial artifacts are preserved on failure. Do not mistake `ARTIFACTS_VERIFIED` for physical task success; inspect [outputs](OUTPUT_SCHEMA.md) and [validation limits](VALIDATION.md).
