# 0015. CV licence posture: MIT/Apache code by default, pretrained weights judged by their training data, no AGPL

- **Status:** Proposed. The human product owner decides OQ-12. Need-by date: Sprint 1 review (sprint-00 §10).
- **Date:** 2026-10-03
- **Deciders:** human product owner (OQ-12); principal-engineer (licence choice, R/A); senior-ml-cv-engineer (author, SPIKE-01)
- **Consulted / required reviewers:** principal-engineer, security-privacy-engineer (sprint-00 §3, SPIKE-01 row). **Neither review has happened yet.** This draft is not approved.
- **Related:** SPIKE-01; OQ-12; NFR-062, NFR-065; FR-083; ADR 0008 (stack, CV deferred to this ADR), ADR 0014 (SBOM-based licence gate); RISK-01, RISK-10, RISK-11 (`brainstorm-engineering.md` §7); roadmap RM-09

## Context and problem statement

The R2 vision pipeline needs ball tracking, person detection and tracking, pose, court homography, audio onsets, and evaluation tooling (ENG §1.2). Our research names candidate code, pretrained weights and datasets for each stage [DOM/CV-01..CV-19, DOMAIN-10, DOMAIN-11]. NFR-062 says no AGPL or non-commercial component, **weights or dataset** may be used in the product without an ADR. The product is a closed-source SaaS (spec §3). OQ-12 asks the PO to choose between "MIT/Apache only" and "buy an Ultralytics Enterprise licence".

SPIKE-01 re-checked every candidate's licence at its source on 2026-10-03. It also asked a question the research had not asked: **what data were the pretrained weights trained on, and does that data's licence allow commercial use?** A permissive code licence says nothing about the weights the repo links to.

## Decision drivers

- NFR-062: 0 AGPL or non-commercial components, weights or datasets in the shipped graph without an ADR. The CI licence gate fails closed (ADR 0014).
- A closed-source SaaS cannot meet AGPL-3.0's terms without releasing its source (AGPL §13 network clause; judgment, not legal advice).
- Accuracy and cost targets CV-T01..T12 (ENG §5.4) must stay reachable. A posture that leaves a stage with no usable model is a product risk, not only a legal one.
- Privacy: no face recognition, and re-identification only within a match (NFR-065). We therefore do **not** need cross-video person re-identification (ReID) weights.
- Start simple, avoid vendor lock-in, and keep inference behind interfaces so models can be swapped [EP/ENG-25; EP/ENG-17].

## Method (SPIKE-01)

1. For every GitHub repo, `curl` fetched `https://raw.githubusercontent.com/<owner>/<repo>/HEAD/<file>` for `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `LICENCE`, `COPYING` and `license`. A 404 for all six is recorded as "no licence file". The sha256 of each LICENSE file fetched is in the Evidence table, so a later change can be detected.
2. READMEs were fetched the same way, and grepped for licence statements, the sources of the weights, and the training datasets.
3. Pages outside GitHub (cocodataset.org, crowdhuman.org, motchallenge.net, ultralytics.com, docs.ultralytics.com, hackmd.io, huggingface.co, ai.meta.com) returned `EGRESS_BLOCKED` from WebFetch and HTTP `000` from curl. For COCO, CrowdHuman, MOT17, AI Challenger and the Ultralytics licence page we only have **web search summaries**. They are marked "search, unverified". The security-privacy-engineer must confirm them from an unrestricted network before this ADR is Accepted (logged in `docs/sprints/00/blockers.md`).
4. `gh api repos/<r>/license` returned HTTP 403 ("GitHub access to this repository is not enabled for this session"), so the raw-file method was used instead.

Tiers used in the table:

- **U = usable in product.** A permissive licence (MIT, Apache-2.0, BSD, ISC) was fetched. For weights, the licensor grants the weights a permissive licence or the training data allows commercial use.
- **E = eval only.** Non-commercial terms. Allowed for internal measurement. It never reaches a training run whose output ships, and never reaches the product.
- **A = needs ADR.** AGPL, no licence at all (default copyright: all rights reserved), or weights whose training data has non-commercial or unclear terms. It may not ship until an accepted ADR, with legal sign-off where noted, says otherwise.

## Licence table (fetched 2026-10-03)

### Code

| # | Component (source) | Licence found | Tier | Notes |
|---|---|---|---|---|
| C1 | TrackNetV3 code [DOM/CV-01] | MIT (LICENSE fetched) | **U** | Baseline ball tracker (ENG §1.2 stage 7) |
| C2 | yastrebksv/TrackNet [DOM/CV-02] | **No licence file** (6 names → 404) | **A** | Read for ideas only; do not copy code. Superseded by C1 |
| C3 | wolfyeva/TrackNetV2 [DOM/CV-03] | **No licence file** | **A** | Do not use |
| C4 | ByteTrack, ifzhang [DOM/CV-04] | MIT (LICENSE fetched) | **U** | The association algorithm needs no weights; only the detector does (W4) |
| C5 | roboflow/trackers (SORT, ByteTrack, OC-SORT, BoT-SORT… "clean-room" implementations) | Apache-2.0 (LICENSE fetched) | **U** | **New candidate**, not in DOM. supervision no longer contains a tracker module (`supervision/tracker/byte_tracker/core.py` → 404), and this package now provides the trackers. Preferred pip-installable ByteTrack (judgment) |
| C6 | supervision [DOM/CV-16] | MIT (LICENSE.md fetched) | **U** | Depends on `av` (PyAV, BSD-3, fetched). PyAV wheels bundle FFmpeg ("Binary wheels … with FFmpeg bundled", README). Whether that FFmpeg build is LGPL or GPL was **not verified**, so it joins the open FFmpeg blocker (worker image) |
| C7 | Ultralytics YOLO [DOM/CV-05] | **AGPL-3.0** (LICENSE fetched), or the paid "Ultralytics Enterprise License" (README §License) | **A** | The README says the Enterprise licence covers "integration of Ultralytics software **and AI models** into business products and services". Price not available (licence page blocked) |
| C8 | BoxMOT [DOM/CV-07] | **AGPL-3.0** (LICENSE fetched) | **A** | Its README examples use `--detector yolo26n` (Ultralytics) and `--reid lmbn_n_duke` (DukeMTMC ReID weights). NFR-065 means we need no cross-video ReID |
| C9 | TrackEval [DOM/CV-08] | MIT (LICENSE fetched) | **U** | Eval tooling; not shipped anyway |
| C10 | MMPose / RTMPose project [DOM/CV-10, DOM/CV-11] | Apache-2.0 (LICENSE fetched; README "released under the Apache 2.0 license") | **U** | Maintenance risk: last release 2024-01-04 [DOM/CV-11]. Export to ONNX (RISK-10) |
| C11 | MMCV, MMEngine, MMDetection (RTMDet), dependencies of C10 | Apache-2.0 (LICENSE files fetched) | **U** | Training/export-time dependencies. The runtime should be ONNX Runtime (C17) so these are not shipped (judgment) |
| C12 | YOLOX (Megvii) | Apache-2.0 (LICENSE fetched) | **U** | ByteTrack's detector. Code only, see W5 |
| C13 | OpenCV [DOM/CV-12] | Apache-2.0 (LICENSE fetched) | **U** | Homography (`findHomography`, RANSAC) |
| C14 | librosa [DOM/CV-13, DOM/CV-14] | ISC (LICENSE.md fetched) | **U** | Audio onsets |
| C15 | roboflow/sports [DOM/CV-15] | MIT (LICENSE fetched) | **U** for the `sports` package; **A** for its examples | `setup.py` `install_requires` has no ultralytics. But `examples/soccer/requirements.txt` = `ultralytics`, `gdown`, and that README says its YOLOv8 models are "distributed under the AGPL-3.0 license". Do not copy example code or models |
| C16 | SAM 2 code [DOM/CV-17] | Apache-2.0 (LICENSE fetched); optional `cc_torch` post-processing BSD-3 (LICENSE_cctorch fetched) | **U** | Demo fonts are OFL-1.1; the demo is not shipped |
| C17 | PyTorch (BSD-style, LICENSE fetched), ONNX Runtime (MIT, fetched), CatBoost (Apache-2.0, fetched) | permissive | **U** | Inference/training runtime; CatBoost for a learned bounce step [DOM/CV-19] |
| C18 | CoachAI-Projects code [DOM/CV-18] | MIT (LICENSE fetched) | **U** | Schema reference only (ShuttleSet, ShuttleNet); we do not plan to ship its code |
| C19 | TennisProject [DOM/CV-19] and the linked TennisCourtDetector | **No licence file** in either repo | **A** | Ideas only (CatBoost bounce step, 14-point court keypoints). Do not copy code or weights |
| C20 | TrackNet-Pickleball [DOMAIN-10] | **No licence file** | **A** | Its weights derive from TrackNetV2. Do not use |
| C21 | PBLineCaller [DOMAIN-11] | MIT (LICENSE fetched) | **U** for code; model **A** | Its README says it uses "a YOLO model trained and hosted on Roboflow"; that model's licence is unknown |
| C22 | deep-person-reid / torchreid (BoxMOT's ReID backend family) | MIT (LICENSE fetched) | **U** for code, not needed | ReID weights are trained on person-ReID datasets whose terms we did not check. NFR-065 means no need: **do not adopt** |
| C23 | TensorRT | not fetched (NVIDIA proprietary SDK licence; judgment) | **A** | Decide in SPIKE-03 only if ONNX Runtime GPU misses the cost target |

### Pretrained weights

| # | Weights (source) | Trained on (source) | Tier | Reasoning |
|---|---|---|---|---|
| W1 | TrackNetV3 checkpoints [DOM/CV-01] | Shuttlecock Trajectory Dataset (badminton; README links hackmd pages, blocked) | **U, with a provenance caveat** | The README says: "This project, including both the codebase and the pretrained model checkpoints (e.g., weights hosted on Google Drive), is released under the MIT License." The licensor grants MIT explicitly. The dataset's own terms are unverified (hackmd blocked). We fine-tune on our own pickleball frames (SPIKE-02). If the PO wants zero provenance risk, we train from scratch on our own data (cost: more labelled frames; judgment) |
| W2 | yastrebksv/TrackNet tennis weights [DOM/CV-02] | TrackNet tennis dataset, 19,835 broadcast frames (README) | **A** | No licence on the repo; broadcast-video source |
| W3 | ByteTrack model zoo (`bytetrack_x/l/m/s/nano/tiny_mot17`, ablation) [DOM/CV-04] | CrowdHuman + MOT17 (+ Cityperson, ETHZ for the test models) (README "Model zoo") | **E** | MOT17: CC BY-NC-SA 3.0 (search, unverified). CrowdHuman: non-commercial research and education only, no redistribution (search, unverified). Allowed for internal eval only |
| W4 | Any off-the-shelf person detector pretrained on **COCO** (YOLOX, RTMDet, Ultralytics YOLO26, …) | COCO | **A (legal sign-off)** | COCO annotations are CC BY 4.0, but "the COCO Consortium does not own the copyright of the images" and images follow Flickr terms, with a different licence per image (cocoapi issue #551 fetched; COCO terms page blocked, search summary). This is a **training-data** question that buying a code licence does not obviously settle (judgment) |
| W5 | RTMDet person detectors used by RTMPose (`…coco-obj365-person…`) | COCO + Objects365 (file names in the RTMPose README) | **A** | As W4. Objects365 terms not checked |
| W6 | RTMPose `aic-coco` checkpoints (incl. RTMPose-m 75.8 AP) [DOM/CV-10] | AI Challenger + COCO (file names `…simcc-aic-coco…`) | **E** | AI Challenger is "only for non-commercial scientific research or academic teaching" (search, unverified) |
| W7 | RTMPose `body7` checkpoints (marked `*`) | AI Challenger, COCO, CrowdPose, MPII, sub-JHMDB, Halpe, PoseTrack18 (RTMPose README "Body8") | **E** | Includes AI Challenger (as W6). The other six were not checked; one non-commercial source is enough |
| W8 | Ultralytics YOLO26 detect/pose weights [DOM/CV-05] | COCO (README: "YOLO26 models pretrained on COCO") | **A** | AGPL-3.0 unless Enterprise (C7), **plus** the COCO question (W4) |
| W9 | BoxMOT ReID weights (e.g. `lmbn_n_duke`) [DOM/CV-07] | DukeMTMC (name), not checked | **A, not needed** | AGPL tooling and NFR-065 rule them out |
| W10 | SAM 2 checkpoints [DOM/CV-17] | SA-V (+ SA-1B; paper, not fetched) | **U** | README: "The SAM 2 model checkpoints … are licensed under Apache 2.0". `sav_dataset/README.md`: "The videos and annotations in SA-V Dataset are released under CC BY 4.0" |
| W11 | TennisProject CatBoost bounce model, TennisCourtDetector weights [DOM/CV-19] | Not stated | **A** | No licence |
| W12 | TrackNet-Pickleball weights [DOMAIN-10] | Own frames + TrackNetV2 3-in-3-out weights | **A** | No licence |

### Datasets

| # | Dataset | Licence found | Tier | Use |
|---|---|---|---|---|
| D1 | SportsMOT [DOM/CV-09] | CC BY-NC 4.0 (README fetched: "SportsMOT is licensed under a Creative Commons Attribution-NonCommercial 4.0 International License"; no LICENSE file) | **E** | Player-tracking evaluation research only. Whether internal evaluation inside a commercial company counts as "NonCommercial" is a legal call (security-privacy-engineer) |
| D2 | ShuttleSet / ShuttleSet22 [DOM/CV-18] | Repo LICENSE is MIT; the dataset README has no separate licence (fetched). The data are annotations of broadcast matches; the videos are not included (judgment) | **U as a schema reference** | We copy field ideas, not data |
| D3 | Shuttlecock Trajectory Dataset (TrackNetV2/V3 training data) | Not verified (hackmd blocked) | **A** | Not needed if W1 is used as an initialisation only |
| D4 | TrackNet tennis dataset [DOM/CV-02] | Not stated in README | **A** | Not needed |
| D5 | COCO | Annotations CC BY 4.0; images per-image Flickr terms (cocoapi #551 fetched; terms page search only) | **A (legal)** | Drives W4, W5, W8 |
| D6 | MOT17 | CC BY-NC-SA 3.0 (search, unverified) | **E** | Eval only |
| D7 | CrowdHuman | Non-commercial research and education; no redistribution (search, unverified) | **E** | Eval only |
| D8 | AI Challenger keypoints | Non-commercial research or teaching (search, unverified) | **E** | Eval only |
| D9 | SA-V | CC BY 4.0 (fetched) | **U** | Possible permissive source for segmentation pretraining (judgment) |
| D10 | Our own labelled pickleball footage (ENG §5.2.3) | Ours, subject to recording consent (OQ-06) | **U once consent exists** | The only data with no third-party licence risk. Licence and consent are recorded per set in the manifest (QD §8, ST-011) |

**Finding.** For **code**, every pipeline stage has a usable (U) permissive option: TrackNetV3, ByteTrack or roboflow/trackers, MMPose/RTMPose, OpenCV, librosa, SAM 2, TrackEval. The gap is in **weights**. Apart from TrackNetV3 (W1) and SAM 2 (W10), every off-the-shelf person-detector and pose checkpoint we found is trained on COCO (image terms unclear) or on explicitly non-commercial data (AI Challenger, CrowdHuman, MOT17). Ultralytics Enterprise fixes the AGPL problem for Ultralytics code and models. It does not obviously fix the COCO training-data question (judgment; the Enterprise terms could not be fetched).

## Considered options

1. **MIT/Apache code only, with weights tiered by training data (proposed).** Ship only U code and weights. Use E weights to bootstrap internal measurement only. Raise one follow-up ADR, with legal sign-off, on COCO-pretrained person detector and pose weights (W4/W5) before R2 ships. Fall back to training on our own data plus permissive data.
2. **Buy an Ultralytics Enterprise licence.** Use YOLO26 for detection, pose and tracking in one library [DOM/CV-05, DOM/CV-06].
3. **Use AGPL components as-is** (Ultralytics and BoxMOT under AGPL-3.0).
4. **Do nothing.** Leave OQ-12 open and decide per story.

## Decision outcome

Proposed: **Option 1.** The PO decides through OQ-12.

1. **Allow-list (U).** Product code may use the U rows: C1, C4, C5, C6, C9 (dev), C10–C14, C15 package only, C16, C17, C18 (reference), and W1, W10, D9, D10.
2. **Eval-only boundary (E).** W3, W6, W7, D1, D6, D7 and D8 may be downloaded only into eval workspaces. They never enter `workers/src/`, a container image, a training run whose output ships, or the gold sets. A model trained or fine-tuned **from** an E checkpoint is itself E (judgment).
3. **No AGPL.** C7, C8, W8 and W9 are not adopted. Option 2 is reopened only if SPIKE-02/SPIKE-03 or the FR-083 eval shows a **measured** accuracy or cost gap against CV-T03/CV-T05/CV-T12 that a U stack cannot close. That would need its own ADR with the Enterprise price and terms (OQ-12 recommendation).
4. **Person detector and pose weights need a follow-up ADR before FR-083 (Sprint 6) is Ready.** That ADR picks one of: (a) accept COCO-pretrained Apache code weights (YOLOX or RTMDet) on recorded legal advice; (b) train or fine-tune the detector and pose model on D10 plus permissively licensed data only; (c) Option 2, if (a) and (b) both fail. Until then, internal spikes may use W4/W5 to measure. The security-privacy-engineer owns the legal question.
5. **No-licence repos (A)** are reference reading only. No code or weights are copied from them.
6. **Every model artefact we ship** records the licence of its code, its weights and **each** training dataset in its eval report (`docs/evals/`), and in the model card (ML DoD "Licences of models, weights and datasets recorded").

## Pros and cons of the options

### Option 1: MIT/Apache code, weights by training data
- Good: meets NFR-062 without spending money; no vendor lock-in; every stage has a usable code path (table above).
- Good: it is the only option that addresses the **weights' training data**, which is where the real gap is.
- Bad: we may need to train our own person detector and pose model, which takes labelling and GPU time (RISK-11). The size of that cost is unmeasured until SPIKE-02/03 (judgment).
- Bad: RTMPose's best published checkpoints (75.8 AP [DOM/CV-10]) are E. A COCO-only or self-trained model may score lower. Unmeasured.

### Option 2: Ultralytics Enterprise
- Good: one library for detection, pose and tracking, with a large community [DOM/CV-05]; the fastest start (judgment).
- Bad: cost unknown (licence page blocked); recurring vendor dependency.
- Bad: YOLO26 weights are COCO-pretrained (README). Whether the Enterprise terms cover training-data claims is unverified, so W4's question may remain.
- Bad: the default tracker can change between releases [DOM/CV-06] and must be pinned (ENG §5.2.5).

### Option 3: AGPL as-is
- Good: free, and fastest.
- Bad: AGPL §13 would require offering the service's source to its users (judgment). This conflicts with a closed-source SaaS and fails the NFR-062 gate. Rejected.

### Option 4: Do nothing
- Bad: every CV story re-litigates licences. The CI gate (ADR 0014) catches packages but not weights downloaded at runtime, so E weights could slip into production unnoticed (judgment). Rejected.

## Consequences

- Good: a clear allow-list for R2. The CI gate (ADR 0014) covers Python packages, and the weights rule closes the gap the package scanner cannot see.
- Trade-offs accepted: possible extra labelling and training for person detection and pose; possibly lower pose accuracy than the published RTMPose numbers.
- Follow-up work:
  - security-privacy-engineer: confirm the "search, unverified" rows (COCO, CrowdHuman, MOT17, AI Challenger, Ultralytics Enterprise terms) from an unrestricted network; give the legal reading of "NonCommercial" for internal evaluation (D1, D6–D8) and of COCO-pretrained weights (W4).
  - senior-ml-cv-engineer: add a **weights manifest** check: every file under the model registry carries `{code_licence, weights_licence, training_datasets[], tier}`, and CI fails on tier E or A outside eval paths. Proposed as a Sprint 1+ story, because it is a CI change and needs the SRE.
  - senior-ml-cv-engineer: SPIKE-02 starts from W1 (TrackNetV3, U).
  - principal-engineer: the follow-up ADR on person detector and pose weights before FR-083 is Ready (Sprint 6).
  - FFmpeg inside PyAV wheels (C6) joins the open FFmpeg licence blocker.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| TrackNetV3 code MIT | `curl https://raw.githubusercontent.com/qaz812345/TrackNetV3/HEAD/LICENSE` → 200, "MIT License, Copyright (c) 2024 qaz812345", sha256 `1eeb31683deba741bce99f5f33bb813293a23b4e6c8302d6f056a587a30cd497` | fetched 2026-10-03 |
| TrackNetV3 checkpoints MIT | TrackNetV3 README line 231: "This project, including both the codebase and the pretrained model checkpoints (e.g., weights hosted on Google Drive), is released under the MIT License." | fetched |
| TrackNetV3 trained on the Shuttlecock Trajectory Dataset | README lines 14, 82, 227 (hackmd links) | fetched; dataset terms blocked |
| No licence: yastrebksv/TrackNet, wolfyeva/TrackNetV2, yastrebksv/TennisProject, yastrebksv/TennisCourtDetector, AndrewDettor/TrackNet-Pickleball | 404 for `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `LICENCE`, `COPYING`, `license` (TennisCourtDetector: `LICENSE`, `LICENSE.md`) at `HEAD` | fetched |
| ByteTrack MIT | LICENSE 200, "MIT License, Copyright (c) 2021 Yifu Zhang", sha256 `e9d83751678cbaba6dfba902ea39215c423d93425e58f8450d6001f7261696f9` | fetched |
| ByteTrack weights trained on CrowdHuman + MOT17 (+ Cityperson, ETHZ) | ByteTrack README "Model zoo": "Train on CrowdHuman and MOT17 half train…", "Train on CrowdHuman, MOT17, Cityperson and ETHZ…" | fetched |
| roboflow/trackers Apache-2.0, ByteTrack included | LICENSE 200 (Apache 2.0, sha256 `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`); README: "clean-room, benchmarked implementations of SORT, ByteTrack, OC-SORT, BoT-SORT, C-BIoU, and McByte" | fetched |
| supervision MIT; no tracker module now | LICENSE.md 200 (sha256 `72bb009f9633af978da6c49f3a927a83d04ddf8ed992492f6f2a62122de95227`); `supervision/tracker/byte_tracker/core.py` → 404; `pyproject.toml` dependencies include `av>=14.2` | fetched |
| PyAV BSD; wheels bundle FFmpeg | PyAV `LICENSE.txt` 200 (BSD 3-clause text); README: "Binary wheels are provided on PyPI … with FFmpeg bundled" | fetched |
| Ultralytics AGPL-3.0 or Enterprise; Enterprise covers "software and AI models" | LICENSE 200 "GNU AFFERO GENERAL PUBLIC LICENSE Version 3" (sha256 `0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0`); README §License lines 278–281 | fetched |
| YOLO26 weights pretrained on COCO | Ultralytics README line 127 | fetched |
| Enterprise required for SaaS and custom-trained models | web search summary of ultralytics.com/license (page `EGRESS_BLOCKED`) | search, unverified |
| BoxMOT AGPL-3.0; examples use Ultralytics and DukeMTMC ReID | LICENSE 200, AGPL v3 (same sha256 as Ultralytics' LICENSE, i.e. the verbatim GNU text); README lines 243, 253–254 | fetched |
| TrackEval MIT | LICENSE 200 (sha256 `f7e548c5729e464d878dd4abf691e323bbea028a756d08395d88b83e43dd2d86`) | fetched |
| SportsMOT CC BY-NC 4.0 | README line 218 | fetched; no LICENSE file |
| MMPose, MMCV, MMEngine, MMDetection Apache-2.0 | LICENSE files 200 (sha256 `aa2c6f3408169b96e5547c875deb481c91502514c1885fa0acb4b596c8909cb9`, `866d999d3ca92d2c5dc9b0afc941c5fac6529e2d180fc638274f91f7fce161d7`, `874b8b2e6f12306a1ff7812c068a0dbf880418b8ac1f7190382bd6c6da9f23a1` ×2) | fetched |
| RTMPose checkpoints trained on AIC+COCO and Body7 (AIC, COCO, CrowdPose, MPII, sub-JHMDB, Halpe, PoseTrack18); RTMDet person detectors on COCO+Objects365 | `projects/rtmpose/README.md` lines 155–213 (checkpoint names `…aic-coco…`, `…body7…`, `…coco-obj365-person…`) | fetched |
| AI Challenger non-commercial | web search summary (challenger.ai terms) | search, unverified |
| COCO: annotations CC BY 4.0, images under Flickr terms per image | `https://github.com/cocodataset/cocoapi/issues/551` (WebFetch); cocodataset.org `EGRESS_BLOCKED`; search summary agrees | fetched (issue) + search |
| CrowdHuman non-commercial, no redistribution | web search summary (crowdhuman.org blocked) | search, unverified |
| MOT17 CC BY-NC-SA 3.0 | web search summary (motchallenge.net blocked) | search, unverified |
| YOLOX Apache-2.0 | LICENSE 200 (sha256 `0ec3668d3274bcf29e8a29e9576d5a2cd96fc78d3c5bec4387355a796e5d9088`) | fetched |
| OpenCV Apache-2.0; librosa ISC | LICENSE 200 (sha256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`); LICENSE.md 200 "ISC License" (sha256 `79aa4a8086d51ac89f9a7322f546670cdef73e758c67f04587b7af8afafd6df8`) | fetched |
| roboflow/sports MIT; examples need ultralytics (AGPL) | LICENSE 200 (sha256 `9b643489f635eb955b4be522cf73d6eea50b65e33aaa5ece18e804676469c20d`); `setup.py` install_requires has no ultralytics; `examples/soccer/requirements.txt` = `ultralytics`, `gdown`; example README "© license" section | fetched |
| SAM 2 code and checkpoints Apache-2.0; cc_torch BSD-3; SA-V CC BY 4.0 | LICENSE 200 (sha256 `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`); README line 198; `LICENSE_cctorch` 200 "BSD 3-Clause"; `sav_dataset/README.md` line 162 | fetched |
| CoachAI-Projects MIT; ShuttleSet README states no separate licence | LICENSE 200 (sha256 `2ff939aee5c1dbce2051c009933dc0ca17f75e75b26c844b73780f2498b33164`); `ShuttleSet/README.md` grep for licen/commercial → only the citation line | fetched |
| PBLineCaller MIT; uses a Roboflow-hosted YOLO model | LICENSE 200 (sha256 `65a804b45f5f3b06c59ab028a4e805bc294a960e493ce527ce36dfa2994a3d24`); README | fetched |
| PyTorch BSD-style; ONNX Runtime MIT; CatBoost Apache-2.0; torchreid MIT | LICENSE files 200 (sha256 `bd018feef8825e88181c84eb7e3aa4eafb8f08a20d9fd6ef948569610c4a3e43`, `2f07c72751aed99790b8a4869cf2311df85a860b22ded05fa22803587a48922c`, `a2574dd20dd0af8e0bd25b34b38c1bb11912ff319ee4f41436395df0b1d19309`, `3ac8ce2a83d170cb1c7c84152e0c1faca1f187794303514383960d2441716247`) | fetched |
| GitHub API not usable here | `gh api repos/qaz812345/TrackNetV3/license` → HTTP 403 "GitHub access to this repository is not enabled for this session" | test result |
| AGPL §13 incompatible with a closed SaaS | (judgment, not legal advice) | judgment |
| A model trained from an E checkpoint is E | (judgment; conservative reading) | judgment |

Note: the sha256 values are of the LICENSE files as fetched on 2026-10-03; re-run the curl in the Method section and `sha256sum` the file to detect a change. Note that MIT/Apache LICENSE files are mostly boilerplate, so equal hashes across repos (Ultralytics = BoxMOT, SAM 2 = roboflow/trackers, MMDetection = MMEngine) are expected and are not an error.

## Confirmation

- The PO answers OQ-12 at the Sprint 1 review. The answer is appended here as a dated note and the status changes.
- The security-privacy-engineer confirms or corrects every "search, unverified" row before acceptance.
- The NFR-062 CI licence gate (ADR 0014) stays red on any AGPL or non-commercial package. From Sprint 1, the weights-manifest check (follow-up) does the same for model files.
- Every eval report in `docs/evals/` lists code, weights and dataset licences with their tier.

## Notes

- 2026-10-03, senior-ml-cv-engineer: drafted in SPIKE-01. Principal-engineer and security-privacy-engineer reviews are **pending**. No review approval is claimed.
