# Isaac Gym backend adaptation

Source: NVIDIA [ProtoMotions](https://github.com/NVlabs/ProtoMotions), commit
`9062f0ae139767d9ac05cebf2253583e2652a56a`, files
`protomotions/simulator/isaacgym/{config.py,simulator.py}`.
The source is covered by the NVIDIA License in the checkout root `LICENSE`.
Retain that complete license when distributing the adapted backend.

Input SHA256:
- simulator.py: `655506279098f2bd31fd66d57435ca02af492aa3e45ff11aa4ba8972e7f472d0`
- config.py: `c232bf1b7a13a8c4c0f951948494f304ff15464ae7c7f778f7c44048c8065ed6`

Target: ProtoMotion_for_InterPose commit
`ad70a3785bf162c89a8df91eb79568770416f1d8`.

Focused changes from upstream:

- Use the fork's `_actions` and controller outputs in simulator DOF order;
  remove the second DOF permutation from PD and torque submission.
- Keep compute and graphics device IDs separate so headless `cuda` does not
  accidentally select compute device -1. CPU requests disable GPU PhysX and
  tensor pipeline; CPU fetch uses `device.type` and occurs once per substep.
- Initialize pending-reset bookkeeping, normalize reset `env_ids=None` to all
  environments, and preserve unspecified optional RobotState fields. Cache the
  resulting complete supported state for the immediate SDK refresh. SDK state
  does not expose `local_rot`; that optional reference-motion field stays absent.
- Provide plain nested dictionaries to the SDK config parser.
- Load marker URDFs only when requested. Preserve dictionary construction order
  for marker actor creation and tensor updates.
- Exclude marker bodies from object contact forces; empty scenes return an empty
  tensor `(num_envs, 0, 3)` instead of calling `.clone()` on None. Scene objects
  must have no articulated DOFs, matching the robot-only DOF tensor layout;
  unsupported articulated objects now fail explicitly.
- Clone every populated default-state tensor before returning it. The fork's
  public getter normalizes root height in-place while body-order conversion
  copies body positions; returning the cached state directly caused repeated
  getter calls to accumulate a root-height offset. The pre-fix harness captured
  environment 1 root z changing from 0 to -1 on the second public getter call.
- Zero SDK stiffness and damping for effort mode (TORQUE/software PROPORTIONAL),
  following Isaac Gym Preview 4 `docs/programming/physics.html` effort-mode setup
  and official `python/examples/dof_controls.py` lines 142-144. The asset's
  inherited stiffness was observed as float32 max; nonzero submitted torque
  produced essentially zero movement. Disabling the implicit drive is the
  isolated corrective experiment; software PD gains remain unchanged. Physical
  causation is subject to the before/after runtime comparison in harness logs.
- Raise RuntimeError on failed simulator creation instead of exiting successfully.

`config.py` otherwise retains upstream defaults and serialization classes;
`__init__.py` deliberately avoids importing the SDK to preserve import ordering.
Built-in PD targets retain upstream semantics: no extra default-position bias.

Validation scope: source syntax and abstract/protected base-interface checks
were performed by the adaptation worker. GPU physics, DOF-order, reset/state,
config roundtrip and GUI checks are recorded separately by the execution harness.
Static checks do not prove runtime correctness. Scene/model-specific HOI behavior,
articulated scene objects, and checkpoint loading remain outside this adaptation.
