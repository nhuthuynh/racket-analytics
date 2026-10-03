# Bounded Context Canvases

One canvas per context, in the DDD Crew Bounded Context Canvas layout [EP/ENG-12]. The relationships are in [`../context-map.md`](../context-map.md) and the events in [`../eventstorming.md`](../eventstorming.md).

| Canvas | Classification | Code module | First sprint with code |
|---|---|---|---|
| [identity-players.md](identity-players.md) | Generic | `racket.players` | S0 (dev identity) |
| [capture-media.md](capture-media.md) | Supporting | `racket.video_ingest` | S0 |
| [vision-analysis.md](vision-analysis.md) | Core | `racket.analysis_jobs`, `racket.worker`, vision stages | S0 (job runtime) |
| [match-scoring.md](match-scoring.md) | Core | `racket.matches`, `racket.scoring` | S0 (minimal `Match`) |
| [sport-plugin-pickleball.md](sport-plugin-pickleball.md) | Core (Published Language) | `racket.sports.pickleball` | S1 |
| [analytics.md](analytics.md) | Core | `racket.analytics` | S2+ |
| [coaching.md](coaching.md) | Core | `racket.coaching` (+ `coaching/drills`, C1) | R1 later sprints |
| [dataset-labelling.md](dataset-labelling.md) | Supporting | `racket.dataset` | S0 (ManifestCheck) |

The classifications and roles are (judgment) unless cited. A canvas changes in the same PR as the code that changes the context's model (principal-engineer DoD).
