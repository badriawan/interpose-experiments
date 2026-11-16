# Licensing and asset publication

This repository combines original experiment utilities with adapted upstream code and separately licensed components. The root license does not override the terms of a third-party patch, SDK, model, dataset, or generated asset.

| Material | Public release treatment |
| --- | --- |
| Adapted InterPose code and patch | Upstream MIT notice retained in `third_party/InterPose-LICENSE.txt` |
| Isaac Gym backend patch | NVIDIA license and provenance retained separately; check its research/evaluation restrictions |
| Isaac Gym SDK | Not redistributed; obtain under NVIDIA's terms |
| SMPL/SMPL-X model files and shape data | Not redistributed; obtain and accept the relevant model license |
| Processed scene data, object meshes, checkpoints | Not included; obtain from authorized sources and verify their own terms |
| Synthetic waypoint demo/video | Uses our own box coordinates; no body model or source scene geometry |
| Original floorlamp motion/video | Kept outside public Git pending asset-specific rights and attribution review |

See the [InterPose MIT notice](../third_party/InterPose-LICENSE.txt), [NVIDIA notice](../third_party/ProtoMotion-NVIDIA-LICENSE.txt), and [backend provenance](../third_party/isaacgym_backend_PROVENANCE.md). The source helper fetches vendor repositories; it does not relicense them.

## Body models and rendered media are different

The [SMPL-X Model license](https://smpl-x.is.tue.mpg.de/modellicense.html) and [SMPL-X Body license](https://smpl-x.is.tue.mpg.de/bodylicense.html) address different material. The Body terms provide a path for sharing certain body representations and media under their attribution conditions, including MPI for Intelligent Systems credit; this does not grant redistribution of all model files, shape components, tools, or unrelated scene assets. Confirm which material a proposed upload contains and supply the required credit/citation.

Likewise, the [OMOMO repository](https://github.com/lijiaman/omomo_release) has an MIT code license, but that fact alone does not establish permission to redistribute every downloadable dataset asset. Trace the actual object mesh's origin. A scene name alone does not prove a particular dataset license applies to that mesh.

## Before publishing a dataset or real preview

Record the source and license for the body representation, object geometry, scene, checkpoint, and any input video. Check whether redistribution and the proposed use are permitted. Retain required attribution and notices. Review binary files and Git history as well as visible documentation. Keeping a file out of the working tree after it was committed does not remove it from history.

The original floorlamp preview is preserved locally under `.local/review_assets/`, which is ignored. The public synthetic video is explicitly labeled so users do not mistake a cleared illustrative asset for successful human/robot motion generation. This document records publication decisions for this release; it is not a substitute for the relevant licenses.
