# Racket Sports Match Analytics — Design Spec

**Status:** Draft for product-owner review
**Date:** 2026-10-02

## 1. Problem & product vision

Amateur racket-sport players record their matches on phones but get almost nothing out of the
footage. Coaching is expensive, and the existing analysis tools are either tennis-only or need
special hardware. This app turns an ordinary match video into four things:

1. **A score sheet.** The rally-by-rally score, worked out automatically and correctable by the player.
2. **Pattern analysis.** What each player does, where, and what wins or loses them points.
3. **Opponent scouting.** The tendencies of a specific opponent, built from every match the
   player has uploaded against them.
4. **Training plans.** Sessions built for general weaknesses and for beating a specific opponent.

The engine is sport-agnostic. Each sport is a plug-in that supplies court geometry, a rules and
scoring state machine, a shot taxonomy and a drill library.

## 2. Locked decisions

| Decision | Choice | Why |
|---|---|---|
| Target user (v1) | Amateur and club players, self-serve | Biggest audience. The player films themselves, so consent and capture are simple. |
| First sport | Pickleball (doubles first, singles supported) | Fast-growing with few tools. The ball is slower and larger than in tennis, so it is easier to track. Its side-out scoring is a real test of the rules engine. |
| First milestone | Upload a recorded match, get stats and a training plan | It proves the whole value chain. Live streaming reuses the same pipeline later. |
| Capture setup | One phone on a tripod behind a baseline, elevated if possible, 1080p at 60 fps or better | A fixed camera makes court calibration a one-time step per video. 60 fps resolves the ball. |
| Accuracy posture | Human-in-the-loop: every automatic call shows a confidence, and the player can correct it | One phone camera cannot make line calls that are good enough to referee from. Every correction becomes training data. |
| Coaching AI | An LLM (Claude) reasons over structured stats and **chooses drills from a curated library**. It does not invent drills. | Every recommendation can be traced back to a stat and a vetted drill. |

## 3. Architecture

```
Client (mobile PWA / web)
  ├─ capture & upload (resumable, chunked)
  ├─ court calibration UI (confirm 4 corners)
  ├─ review timeline (rallies, shots, score: correct anything)
  └─ dashboards, scouting reports, training plans
        │
API service ──── Postgres (matches, rallies, shots, players, plans)
        │   └─── Object storage (raw video, clips, thumbnails)
        ▼
Job queue ──► GPU analysis workers (Python)
               1. Court detection → homography (image → court coordinates)
               2. Player detection + tracking + identity (YOLO + ByteTrack, plus re-id)
               3. Pose estimation (RTMPose) → swing/stance features
               4. Ball tracking (TrackNet-style heatmap model, fine-tuned on pickleball)
               5. Event detection: hits (trajectory inflection + player proximity
                  + audio "pop" onset) and bounces (vertical inflection near ground)
               6. Rally segmentation (dead-ball gaps, serve detection)
               7. Shot classification (serve, return, drive, drop, dink, lob,
                  volley, speed-up, reset, erne, ATP)
               8. Rules engine → score per rally (sport plug-in)
          ──► Analytics jobs (pure SQL/Python over the event tables)
          ──► Coaching service (LLM + drill library) → plans
```

**Why audio matters for pickleball:** the paddle "pop" is loud and distinctive, so audio onset
detection gives a cheap, high-precision signal for hit timing. Hit timing is the hardest event to
get from video alone.

### Sport plug-in interface

```
SportPlugin {
  courtModel        // line geometry, zones (e.g. kitchen/NVZ), net position
  rules             // state machine: serve order, faults, scoring, game/match end
  shotTaxonomy      // shot types and the features used to classify them
  metrics           // sport-specific KPIs (e.g. third-shot drop success)
  drillLibrary      // tagged drills: skill, level, duration, players, equipment
}
```

Pickleball ships first. Tennis, badminton and table tennis are later plug-ins. Table tennis will
need 120 fps or more and a different camera position.

### Stack (recommended)

- **Workers:** Python (PyTorch, OpenCV, Ultralytics, FFmpeg). There is no realistic way around
  Python for computer vision.
- **API:** Python FastAPI, which keeps the backend to one language and shares the domain models
  with the workers. A Go API, matching the knowledge-base-builder pattern, is possible but would
  add a second backend language before product-market fit.
- **Client:** Next.js PWA first, with camera upload from the phone browser. A native app
  (Expo/React Native) waits until live capture needs it.
- **Data:** Postgres plus S3-compatible storage, with Redis or a Postgres-backed queue for jobs.
- **GPU:** serverless GPU (e.g. Modal or RunPod) so the app pays per processed minute, not for
  idle GPUs.

## 4. Data model (core)

- `Player`: an app user, or an opponent profile the user creates and links across matches
- `Match`: sport, format (singles/doubles), scoring system (side-out/rally), video, calibration
- `Rally`: start and end time, server, score before and after, winner, how it ended
  (winner/error/fault)
- `Shot`: rally, hitter, time, type, court position of the hitter and of the ball's landing
  spot, height over the net if known, outcome, confidence, `corrected_by_user`
- `Event`: the raw hits and bounces the vision pipeline detected (kept for re-processing)
- `MetricSnapshot`: computed per player per match, so trends over time stay cheap to query
- `TrainingPlan` → `Session` → `DrillAssignment` (drill id, reps or duration, the reason it was
  chosen, linked to a metric)

## 5. Analytics (pickleball v1)

- **Score and flow:** score progression, runs, side-outs, serve/return points won
- **Serve and return:** depth heatmaps, return depth and how it affects the next rally
- **Third shot:** drop vs drive mix, success rate (did the team reach the kitchen?)
- **Transition:** time and shots needed to get to the NVZ line, and points lost in transition
- **Dink battles:** length, cross-court vs straight, who speeds up first, and how speed-ups end
- **Errors:** unforced errors by shot type and court zone
- **Patterns:** shot-sequence n-grams (e.g. *deep return → drop → dink cross → speed-up
  middle*) ranked by how often they win or lose the point
- **Positioning:** player heatmaps and partner spacing (how often the middle is left open)
- **Opponent scouting** (merged across matches against the same opponent): their favourite
  patterns, their weakest shot under pressure, their serve tendencies, which side they cover
  poorly

Each metric comes with a sample size. When a sample is too small to mean much, the app marks the
metric that way instead of hiding it.

## 6. Training plans

Input: the player's metric trends, their self-reported level and goals, the time they have
available, and optionally an opponent's scouting report.

1. A rules layer ranks weaknesses by **points lost per match** attributable to each one.
2. The LLM gets the top weaknesses, the evidence behind them (stats and links to clips) and the
   drill library. It picks drills, orders them into sessions, and writes a short "why" for each
   drill that links back to the evidence.
3. **General plan:** a 2–4 week block that targets the biggest point leaks.
   **Opponent plan:** 1–3 sessions before a known match that drill the specific counter, e.g.
   "they speed up from the backhand on high dinks, so drill keeping dinks low to their backhand
   and reset blocks".
4. After the next match is uploaded, the plan is scored: did the targeted metrics move?

Clips matter: every insight links to the video moments behind it. Players trust what they can
see.

## 7. Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | Skeleton: upload, storage, job queue, match/rally/shot schema, **manual tagging UI**, and the pickleball rules engine with tests | A user can tag a match by hand and get a correct score sheet |
| M1 | Court calibration (automatic, with a 4-corner fallback) plus player tracking and identity | Player heatmaps on real footage |
| M2 | Ball tracking plus hit/bounce detection (video + audio), and rally segmentation | ≥90% of rallies segmented correctly on the test set |
| M3 | Shot classification plus automatic scoring, with the review/correction flow | A match is scored automatically with ≤1 correction per game on average |
| M4 | Analytics dashboards plus clip linking | All §5 metrics except scouting |
| M5 | Training plans (general) plus the drill library (~80 drills) | Plan generated, traceable to stats |
| M6 | Opponent profiles, scouting reports, opponent-specific plans | Scouting merged across ≥2 matches |
| M7 | Live mode: stream ingest (WebRTC/RTMP), windowed pipeline, live score and in-match tips | Live score lag under 5 s |

M0 deliberately includes manual tagging. Analytics, coaching and the review UI can then be built
and tested on real data while the vision models are still being trained, and the manual tags
become the labelled dataset.

## 8. Risks

- **Training data:** there are very few public pickleball datasets. Mitigation: label about
  50 matches through the M0 tagging tool, and start from TrackNet weights trained on
  tennis and badminton.
- **Amateur footage quality:** bad camera angles, backlight and fences. Mitigation: a capture
  guide shown in the app, a quality check on upload, and graceful degradation (score only, no
  shot detail).
- **Doubles identity swaps:** players cross paths and the tracker swaps their identities.
  Mitigation: use team side plus clothing colour for re-id, and let the user fix identities once
  per match.
- **Privacy:** videos show third parties, possibly minors. Mitigation: videos are private by
  default, sharing is explicit, retention controls exist, and there is no face recognition
  (identity is per match and assigned by the user).
- **GPU cost:** keep it to around 1–2 GPU-minutes per match-minute. Track this from M2 onwards.

## 9. Open questions

- Product name and repo name
- Monetisation: freemium (a few analysed matches per month) or subscription
- Whether coaches get a multi-player view in v1.x
