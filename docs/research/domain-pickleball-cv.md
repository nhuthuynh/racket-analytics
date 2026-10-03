# Research: Pickleball Domain (Rules, Coaching, Competitors) and Sports Computer Vision

- **Date:** 2026-10-03
- **Author role:** Senior research analyst (domain: pickleball rules and coaching; sports computer-vision state of the art)
- **Product:** racket-analytics (see `docs/specs/2026-10-02-racket-analytics-design.md`)
- **Scope:** The source base for (a) the pickleball rules and scoring engine, (b) coaching content and the shot taxonomy, (c) the competitive context, and (d) the CV pipeline: ball tracking, player detection and tracking, pose, court homography, audio hit detection, datasets and evaluation metrics.
- **Out of scope:** Engineering process (see `engineering-process.md`). Security, NFRs, operations and LLM-agent design (see `architecture-quality-security.md`).

## How verification was done

Every URL in the register was requested with WebFetch on 2026-10-03. A source is marked **verified = yes** only when the fetch succeeded and the returned content contained the guidance this file attributes to it. WebFetch returns a model-produced summary of the page, so star counts and quoted phrases are as that summary reported them on 2026-10-03. Re-open the URL before you quote one externally.

**Major limitation:** The sandbox egress proxy blocked **every primary pickleball-rules and coaching domain we tried**: usapickleball.org (rules summary and the 2026 Official Rulebook PDF), pickleballcanada.org, globalpickleballfederation.org, ifpickleball.org, pickleball.com, pickleballteachers.com (PPR), betterpickleball.com, selkirk.com, en.wikipedia.org and several rules-explainer sites. It also blocked the competitor sites pb.vision, swing.vision and apps.apple.com, and the paper hosts arxiv.org, dl.acm.org, paperswithcode.com, librosa.org and docs.opencv.org. GitHub did work, so the CV material is well verified. Where a publisher keeps its canonical docs in its own GitHub repo (OpenCV, Ultralytics, librosa), we fetched that copy instead. **No pickleball rule is verified in this file.** The rules material below comes from search-engine snippets only and is marked UNVERIFIED. It must be checked against the official rulebook before the rules engine is finalised (see Gaps).

## Source register

### Pickleball domain (rules, coaching, products)

| ID | Title | Publisher / author | URL | Type | Credibility signal | Verified |
|---|---|---|---|---|---|---|
| DOMAIN-01 | 2026 Official Rulebook | USA Pickleball | https://usapickleball.org/docs/rules/USAP-Official-Rulebook.pdf | standard | National governing body (US) | **no**: egress blocked. Exists per WebSearch results (title "2026 OFFICIAL RULEBOOK") |
| DOMAIN-02 | 2026 USA Pickleball Rulebook Change Document | USA Pickleball | https://usapickleball.org/docs/rules/USAP-Rulebook-Change-Document.pdf | standard (change log) | Governing body | **no**: egress blocked. Exists per WebSearch results |
| DOMAIN-03 | Basic Rules Summary | USA Pickleball | https://usapickleball.org/docs/rules/USAP-Rules-Summary.pdf | official doc | Governing body | **no**: egress blocked |
| DOMAIN-04 | 2026 Official Rulebook (Pickleball Canada edition) | Pickleball Canada | https://pickleballcanada.org/wp-content/uploads/2026/03/2026-Official-Rulebook-EN.pdf | standard | National governing body (Canada) | **no**: egress blocked |
| DOMAIN-05 | 2026 Rulebook Change Document (GPF) | Global Pickleball Federation | https://globalpickleballfederation.org/docs/GPF-Rulebook-Change-Document-2026-edition.pdf | standard (change log) | International federation | **no**: egress blocked |
| DOMAIN-06 | PB Vision: Video Analysis & Ratings | PB Vision | https://pb.vision/ | product site (competitor) | Direct pickleball competitor | **no**: egress blocked. Search snippets only (see DOMAIN-07) |
| DOMAIN-07 | PB Vision launch coverage | Ministry of Sport | https://ministryofsport.com/ai-now-assisting-pickleball-players-improve-their-game-with-the-launch-of-pb-vision/ | news | Trade press | **no**: not fetched. Search snippet only |
| DOMAIN-08 | SwingVision: AI Stats for Tennis & Pickleball | SwingVision | https://swing.vision/guides/set-up-your-recording | product docs (competitor) | Direct competitor | **no**: egress blocked |
| DOMAIN-09 | Top "pickleball" repositories by stars | GitHub search | https://github.com/search?q=pickleball&type=repositories&s=stars&o=desc | repo index | Live star counts | yes. The top repo has 38 stars, so there is no mature open-source pickleball CV project |
| DOMAIN-10 | TrackNet-Pickleball | Andrew Dettor | https://github.com/AndrewDettor/TrackNet-Pickleball | repo | 34 stars, 13 forks. Most-starred pickleball ball-tracking repo | yes. TrackNetV2 transfer learning with manual frame labelling. No metrics in the README. No licence stated |
| DOMAIN-11 | PBLineCaller | clssmitty | https://github.com/clssmitty/PBLineCaller | repo | 20 stars | yes. YOLO via Roboflow plus a Colab notebook. Self-described as "just the beginning", with no accuracy data |

### Sports computer vision

| ID | Title | Publisher / author | URL | Type | Credibility signal | Verified |
|---|---|---|---|---|---|---|
| CV-01 | TrackNetV3 (official code) | qaz812345 (NYCU authors). Paper in ACM proceedings, doi 10.1145/3595916.3626370 | https://github.com/qaz812345/TrackNetV3 | repo + paper ref | 311 stars. Peer-reviewed (ACM MM Asia 2023 per DOI prefix; venue name is judgment) | yes (repo). Paper page blocked |
| CV-02 | TrackNet (unofficial PyTorch implementation) | yastrebksv | https://github.com/yastrebksv/TrackNet | repo | 248 stars. Implements Huang et al. 2019 (arXiv 1907.03698) | yes (repo). arXiv blocked |
| CV-03 | TrackNetV2 (improved) | wolfyeva | https://github.com/wolfyeva/TrackNetV2 | repo | 22 stars (low) | yes, but thin: README gives no metrics |
| CV-04 | ByteTrack | Yifu Zhang et al. (ifzhang) | https://github.com/ifzhang/ByteTrack | repo + paper (ECCV 2022) | 6.7k stars. Peer-reviewed. MIT | yes |
| CV-05 | Ultralytics YOLO | Ultralytics | https://github.com/ultralytics/ultralytics | repo | 62.2k stars. YOLO26 is the current family. **AGPL-3.0 or commercial Enterprise licence** | yes |
| CV-06 | Ultralytics docs: Multi-object tracking (track mode) | Ultralytics | https://github.com/ultralytics/ultralytics/blob/main/docs/en/modes/track.md | official doc (repo source) | Vendor docs | yes |
| CV-07 | BoxMOT | Mikel Broström | https://github.com/mikel-brostrom/boxmot | repo | 8.3k stars, 1.9k forks. **AGPL-3.0**. Benchmarks on MOT17 and SportsMOT | yes |
| CV-08 | TrackEval (official HOTA implementation) | J. Luiten et al. | https://github.com/JonathonLuiten/TrackEval | repo + paper (IJCV, HOTA) | 1.3k stars. MIT. Reference implementation of HOTA | yes |
| CV-09 | SportsMOT | MCG-NJU | https://github.com/MCG-NJU/SportsMOT | dataset + paper (ICCV 2023) | 231 stars. Peer-reviewed. **CC BY-NC 4.0** | yes |
| CV-10 | RTMPose (MMPose project page) | OpenMMLab | https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose | repo / official doc | OpenMMLab | yes |
| CV-11 | MMPose | OpenMMLab | https://github.com/open-mmlab/mmpose | repo | 7.9k stars. Apache-2.0. **Latest release v1.3.0 (2024-01-04)** | yes |
| CV-12 | OpenCV tutorial: Basic concepts of the homography explained with code | OpenCV | https://github.com/opencv/opencv/blob/4.x/doc/tutorials/features2d/homography/homography.markdown | official doc (repo source of docs.opencv.org) | OpenCV project | yes (docs.opencv.org blocked, so we fetched the canonical source) |
| CV-13 | librosa | librosa team | https://github.com/librosa/librosa | repo | 8.6k stars. ISC licence | yes |
| CV-14 | librosa `onset.py` (onset_detect / onset_strength docstrings) | librosa team | https://github.com/librosa/librosa/blob/main/librosa/onset.py | official API doc (source) | as CV-13 | yes (librosa.org blocked) |
| CV-15 | roboflow/sports | Roboflow | https://github.com/roboflow/sports | repo | 5.4k stars. MIT | yes |
| CV-16 | supervision | Roboflow | https://github.com/roboflow/supervision | repo | 51.1k stars as reported by the fetch (judgment: re-check, this looks high). MIT. 4.9k forks | yes |
| CV-17 | SAM 2 | Meta AI (facebookresearch) | https://github.com/facebookresearch/sam2 | repo (FAANG research) | ~20k stars. Apache-2.0 / BSD-3 | yes |
| CV-18 | CoachAI-Projects (ShuttleSet, ShuttleSet22, ShuttleNet…) | wywyWang / NYCU ADSL (Prof. Wen-Chih Peng) | https://github.com/wywyWang/CoachAI-Projects | repo + datasets (KDD 2023, IJCAI 2024) | 282 stars. MIT. Peer-reviewed | yes (repo). ACM paper page not fetched |
| CV-19 | TennisProject | yastrebksv | https://github.com/yastrebksv/TennisProject | repo | 235 stars | yes |
| CV-20 | Building effective agents | Anthropic | https://www.anthropic.com/engineering/building-effective-agents | engineering blog | Anthropic. Same source as ENG-25 in `engineering-process.md` | yes (re-fetched) |

**Verified sources: 22.** That is DOMAIN-09, -10 and -11 plus CV-01 to CV-20, with CV-03 only thinly verified. **Unverified: 8** (DOMAIN-01 to DOMAIN-08).

## Guidelines

### G1. Pickleball rules and scoring: PROVISIONAL, NOT VERIFIED

None of the items below could be fetched from a governing body. They are recorded so the BA and domain coach know exactly what to check. They must not be coded as acceptance criteria until someone confirms each one against DOMAIN-01 (2026 edition) and records the rule number.

- R1 (UNVERIFIED, search snippet citing DOMAIN-01/02): The 2026 USA Pickleball rulebook exists, along with a separate 2026 change document. Pin the rules engine to an explicit **rulebook edition** (`rules_version = "USAP-2026"`).
- R2 (UNVERIFIED, search snippet): Side-out (traditional) scoring: only the serving side scores, and games go to 11, win by 2.
- R3 (UNVERIFIED, search snippet citing Rule 14.A): **Rally scoring stays a provisional rule in 2026.** It is an option that tournament directors may use, with exclusions for some events (snippet: double-elimination doubles, Golden Ticket and National Championship events). Under the 2026 change, the game-winning point is no longer limited to the serving team.
- R4 (UNVERIFIED, search snippet): Two-bounce rule. The serve must bounce before the receiver returns it, and the return must bounce before the serving team plays it. After that, volleys are allowed.
- R5 (UNVERIFIED, search snippet): The non-volley zone (NVZ, "kitchen") extends 7 ft from the net on each side. A player may not volley while standing in the NVZ or on its line.
- R6 (judgment / background knowledge, UNVERIFIED): In doubles, the score is called as three numbers (serving score, receiving score, server number 1 or 2). The game starts at "0-0-2", so only one server serves on the first service turn. Serving starts from the right-hand court when the serving team's score is even. Volleying momentum that carries a player into the NVZ is a fault. A ball touching a line is in, except that a serve landing on the NVZ line is a fault. **All of these need rule numbers from DOMAIN-01.**

### G2. Coaching and shot taxonomy: UNVERIFIED

- C1 (UNVERIFIED, search snippets from coaching blogs, none fetched): The third shot drop is a soft, arcing shot meant to land in the opponent's NVZ. It neutralises the serving team's positional disadvantage, because the returning team is already at the kitchen line. Players move forward through the "transition zone" with a drop, a step forward, another drop, and so on. A dink is a soft shot from at or near the kitchen line that lands in the opponent's NVZ.
- C2 (judgment): The spec's shot taxonomy (serve, return, drive, drop, dink, lob, volley, speed-up, reset, erne, ATP) matches what the competitor PB Vision is reported to analyse ("all 3rd shots whether drop, hybrid, drive or lob"; search snippet, DOMAIN-06/07 unverified). A "hybrid" third shot may be worth adding as a class.

### G3. Ball tracking

- B1 Use a **multi-frame heatmap model** (TrackNet family), not a per-frame detector, for the ball. TrackNet takes several consecutive frames and outputs a Gaussian heatmap centred on the ball. That design targets balls that are "small, blurry, and sometimes even invisible" [CV-02].
- B2 Start from **TrackNetV3**. It adds a trajectory-rectification module that uses inpainting to repair occluded segments, plus a background estimate and mixup augmentation. It takes 8-frame windows for tracking and 16-frame windows for rectification, and outputs `Frame, Visibility, X, Y` per frame. On its badminton test set it reports accuracy 97.51%, precision 97.79%, recall 99.33%, F1 98.56% at 25.11 FPS. Licence: MIT [CV-01].
- B3 Expect to **fine-tune on our own labelled pickleball frames**. The only public pickleball adaptation does TrackNetV2 transfer learning with manual frame labelling and publishes no metrics or licence [DOMAIN-10]. The original TrackNet dataset is broadcast tennis: 19,835 frames from 10 videos at 1280×720, 30 fps [CV-02]. That is a different domain from an amateur phone on a tripod (judgment).
- B4 Make **visibility a first-class output**. An occluded ball is "not visible", not a guessed position [CV-01].
- B5 Treat bounce detection as a separate learned step on the trajectory. TennisProject uses a CatBoost regressor over ball-tracking output to predict bounces, and a 14-keypoint court detector feeds its homography [CV-19].

### G4. Player detection, tracking and identity

- P1 Detect people with Ultralytics YOLO. The current family is YOLO26, and the library supports detection, pose and tracking [CV-05]. **Its licence is AGPL-3.0, or a paid Enterprise licence for business products** [CV-05]. BoxMOT is AGPL-3.0 too [CV-07]. A closed-source SaaS has to budget for a licence or choose MIT/Apache alternatives: ByteTrack (MIT) [CV-04], supervision (MIT) [CV-16], MMPose (Apache-2.0) [CV-11].
- P2 ByteTrack associates **every** detection box, low-confidence ones included, matching low-score boxes to existing tracklets so occluded objects are recovered. It reports MOT17 test MOTA 80.3, IDF1 77.3, HOTA 63.1 at 29.6 FPS on a V100 [CV-04].
- P3 Ultralytics track mode ships BoT-SORT, ByteTrack, OC-SORT, Deep OC-SORT, FastTracker and TrackTrack, and **TrackTrack is the default**. Pass `persist=True` only for sequential frames from one video. ReID is off by default and can be enabled with `with_reid: True` on BoT-SORT, Deep OC-SORT and TrackTrack [CV-06]. Pin the tracker explicitly in config so a library upgrade cannot change it silently (judgment).
- P4 Expect identity switches. Sports footage has fast motion, deformation and players who look alike [CV-09], and keeping IDs through occlusions and exits or re-entries is a known open challenge [CV-15]. With 4 players in doubles, add a **constrained identity step**: exactly 2 per side, with user confirmation (judgment).
- P5 SAM 2 offers promptable video segmentation and tracking from clicks or boxes. Model sizes run from 38.9M to 224.4M parameters at 39.5 to 91.2 FPS on an A100 [CV-17]. It is a candidate for a "user taps each player once" identity UX or for auto-labelling (judgment).

### G5. Pose estimation

- PO1 RTMPose-m reports **75.8% AP on COCO at 90+ FPS on an i7-11700 CPU and 430+ FPS on a GTX 1660 Ti**. It supports 17-keypoint COCO body, 26-keypoint Halpe and 133-keypoint WholeBody sets, and deploys via ONNX Runtime, TensorRT, ncnn and OpenVINO [CV-10].
- PO2 MMPose is Apache-2.0, but its **latest release is v1.3.0 from 2024-01-04** [CV-11]. Pin versions, export to ONNX and treat the training toolkit as a maintenance risk (judgment).
- PO3 Ultralytics also provides pose models, and its default tracker keeps keypoints aligned with detections [CV-06]. That makes it a single-library alternative if the licence is acceptable.

### G6. Court calibration and homography

- H1 A homography is a 3×3 matrix with **8 degrees of freedom** (it is defined only up to scale) relating two planes. Estimate it with `findHomography()` from point correspondences, and apply it with `warpPerspective()` [CV-12]. It is valid **only for points on the plane**, here the court surface [CV-12]. So player foot points and ball bounce points map correctly, but an airborne ball does not (judgment drawn from the planar assumption).
- H2 Four correspondences are the minimum, and more points with robust estimation (RANSAC) handle outliers [CV-12, partially: the summary infers these rather than quoting them]. Use all detectable line intersections, not just 4 corners. Keep the "confirm 4 corners" UI as a fallback and a validation step (judgment).
- H3 Prior art uses a court-keypoint detector (14 points in TennisProject [CV-19]; pitch and court keypoints in roboflow/sports [CV-15]) feeding a view transformer. Camera calibration is listed as a key challenge [CV-15].

### G7. Audio hit detection

- A1 Use `librosa.onset.onset_detect` on an onset-strength envelope. `onset_strength` computes **spectral flux**, the mean positive frame-to-frame difference across (by default Mel) frequency bins. Peak picking uses defaults found by hyperparameter search: `pre_max` 30 ms, `post_max` 0 ms, `delta` 0.07, `wait` 30 ms. Set `units="time"` to get timestamps, and `backtrack` to roll back to the nearest energy minimum [CV-14]. librosa is ISC-licensed, 8.6k stars [CV-13].
- A2 The 30 ms `wait` default sets the minimum spacing between onsets [CV-14]. Real paddle contacts in a fast hands battle are rarely closer than that (judgment, needs measuring), but tune it on labelled pickleball audio rather than trusting defaults (judgment).

### G8. Datasets and evaluation metrics

- E1 Report tracking quality with **HOTA** (and its DetA and AssA parts), plus MOTA and IDF1, using the TrackEval reference implementation (MIT). TrackEval calls HOTA its "recommended tracking metric" [CV-08].
- E2 SportsMOT (240 clips of basketball, football and volleyball at 720p and 25 fps; ICCV 2023) is a useful benchmark for player tracking under sports motion. It is **CC BY-NC 4.0, so non-commercial only**: use it for evaluation research, never to train a commercial model without permission [CV-09].
- E3 ShuttleSet (KDD 2023) and ShuttleSet22 (IJCAI 2024) are the reference for **stroke-level tactical annotation** in a turn-based racket sport. The same group also published stroke forecasting (ShuttleNet), movement forecasting and shot influence models (MIT) [CV-18]. Model our rally, shot and stroke schema on them (judgment).
- E4 Ball-tracking metrics follow TrackNetV3's accuracy, precision, recall, F1 and FPS [CV-01]. Define "correct" with a pixel-distance threshold that we document (judgment).

### G9. Coaching AI (LLM)

- L1 Use the simplest design that works. Prefer a **workflow** (predefined code path) over an autonomous agent for plan generation. Ground each step in tool results. Invest in tool and interface design [CV-20].

## Implications for racket-analytics

| Theme | Implication |
|---|---|
| Rules (G1) | **Blocking:** before any rules-engine story is "Ready", the domain coach or BA must get the 2026 USAP rulebook (outside this sandbox), record rule numbers for R2–R6, and update this file. Make the rules engine a pure, versioned state machine (`rules_version`) supporting side-out **and** rally scoring (because rally scoring is provisional and allowed by tournament option). Write property-based and table-driven unit tests per rule (e.g. 0-0-2 start, server 1→2→side-out, win-by-2 at 10-10, rally-scoring game point by receiving team). |
| Coaching (G2) | Add the drill library and taxonomy only with sources a coach has verified. Consider adding a "hybrid" third-shot class. Coaching statements in the UI must trace to a stat and a vetted drill, as the spec already requires. |
| Ball tracking (G3) | Architecture: TrackNetV3 (MIT) as the baseline, fine-tuned on our own labelled pickleball frames. **Sprint scope:** a labelling tool plus a small gold set (judgment: a few thousand frames across courts and lighting) comes before model work. NFR: report visibility-aware precision, recall and F1 per test video, and gate merges on no regression. |
| Tracking and identity (G4) | **Licence decision (ADR needed):** AGPL-3.0 Ultralytics and BoxMOT against a commercial licence or MIT/Apache components. Doubles identity constraints (2 per side) plus a user-confirmation UI. Pin the tracker in config. Integration tests should run on short fixture clips with a known number of ID switches. |
| Pose (G5) | RTMPose via ONNX Runtime so we don't depend on an unmaintained training stack at runtime. CPU numbers suggest pose may not need GPUs, which is a cost lever to benchmark. |
| Homography (G6) | Map only ground-plane points: feet and bounces. Use ball height or trajectory in image space for hit and bounce logic. Calibration acceptance test: reprojection error of known court lines below a threshold we document. Keep the manual corner confirmation. |
| Audio (G7) | An audio onset stream as an independent hit-timing signal fused with visual inflection. Unit tests on synthetic click tracks. Integration tests on labelled real audio. Expose `delta` and `wait` as tuned config, not hard-coded defaults. |
| Evaluation (G8) | A "model quality" test layer separate from unit and integration tests: HOTA, IDF1, ball F1 and hit-timing error in ms on a frozen gold set, run in CI on demand and every sprint. Respect dataset licences: SportsMOT for evaluation only. |
| Competitors (DOMAIN-06/08/09) | PB Vision and SwingVision reportedly already offer pickleball stats from one phone (unverified snippets). Open-source pickleball CV is immature (≤38 stars). The PM should verify competitor features first-hand and position on **correctable score sheets plus opponent scouting plus traceable drills** (judgment). |
| Coaching LLM (G9) | Plan generation as a deterministic workflow: stats → candidate weaknesses → drill retrieval → LLM selection and rationale. Evaluate with a rubric against coach-labelled cases. |

## Gaps / unverified

1. **All pickleball rules (G1)**: usapickleball.org, pickleballcanada.org, globalpickleballfederation.org, ifpickleball.org, pickleball.com and en.wikipedia.org were egress-blocked. Rally-scoring details (Rule 14.A, the event exclusions, and the game-winning point change) come from search snippets only. The 0-0-2 start, server-number calling, NVZ momentum and line-call rules are background knowledge only.
2. **Coaching sources (G2)**: PPR (pickleballteachers.com), betterpickleball.com, selkirk.com and thedinkpickleball.com were not fetched or were blocked. No verified coaching standard exists yet.
3. **Competitors**: pb.vision, swing.vision and the Apple App Store were blocked. Features, capture requirements ("camera at least four feet above the ground" for PB Vision) and download and rating figures come from search snippets only.
4. **Papers**: arXiv (TrackNet 1907.03698, ByteTrack 2110.06864, ShuttleSet 2306.04948), ACM DL (TrackNetV3, ShuttleSet) and paperswithcode were blocked. Only the papers' official or unofficial repos were verified. TrackNet paper metrics (P/R/F1 99.7/97.3/98.5) come from a search snippet and are unverified.
5. **OpenCV homography details**: the 4-point minimum and RANSAC were inferred by the fetch summariser rather than quoted. Confirm them in `findHomography` API docs (docs.opencv.org blocked).
6. **Star-count anomaly**: supervision reported at 51.1k stars. Re-check.
7. **TrackNetV2 official repo** not found. CV-03 is a 22-star fork-style repo with no metrics.
8. **Pickleball audio "pop" characteristics** (frequency band, minimum inter-hit interval): no source found. This needs our own measurement.
