# Trial 02: official HOI-Agent baseline plan

**Status: planned, not executed in this release.**

The intended next comparison uses the floorlamp task supplied by the pinned InterPose project through its official HOI-Agent flow. The goal is to establish one small baseline before comparing the bounded structured planner in `trial_01`.

Proposed sequence:

1. Inspect the pinned official input JSON, prompt construction, tool definitions and executor entry point.
2. Confirm the exact built-in task and required scene assets; preserve a source snapshot and hashes.
3. Reuse verified isolated environments and checkpoint, then run CPU preflight and a simulator smoke test.
4. Explicitly authorize one paid planner run and one scenario, preserving prompts, API usage, commands and outputs.
5. Compare output schema, reference timing, body/object quality and physical outcome with `trial_01`.

No completed motion, video, or success claim belongs to this folder yet. Avoid interpreting its presence as evidence that the unmodified official loop was executed by the public quickstart.
