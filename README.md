# racket-analytics

Video-based match analytics, scoring and tailored training plans for racket sports — pickleball first.

## Run it locally

Everything runs in Docker Compose on your machine; nothing is deployed.

**You need:** Docker with Compose v2 (`docker compose version`), GNU `make`, Python 3 (for
`make demo`), about 16 GB of free disk, and these local ports free: 3000 (app), 8000 (API),
5432 (Postgres), 8025 and 1025 (Mailpit), 8333 (object store), 16686 (tracing).

```bash
make up      # build and start the stack; waits until every service is healthy
make demo    # optional: load a sample match with 12 tagged rallies and stats
```

The first `make up` builds the images, which takes several minutes on a cold machine (about
2 minutes with a warm Docker build cache). It creates `infra/.env` from `infra/env.example`
(dev-only values) the first time.

1. Open **https://localhost:3000**. The stack uses its own local certificate authority, so the
   browser warns about the certificate: click through (Advanced, then Proceed to localhost), or
   trust the dev root once `make demo` has copied it to `.local/demo/root.crt`.
2. Sign in with a **Sign in as Ivy** button (also Carlos and Dana; dev stack only), or enter an
   email address and open the sign-in link in Mailpit at **http://localhost:8025**.
3. Explore: create a match with the new-match wizard, upload an MP4 or MOV video (H.264 or
   HEVC), tag rallies on the score sheet, read the stats with their uncertainty, use
   "Show me" to jump to the rallies behind a number, correct a rally (stats update), and
   delete a match. `make demo` prints the link to the sample match's stats page.

### Try the prototype

The whole R1 journey on the demo data, in about five minutes:

1. `make up`, then `make demo`. The demo signs in as Ivy, seeds a tagged sample match and
   generates her 2-week plan; running it again adds nothing.
2. Open the stats URL that `make demo` prints (`https://localhost:3000/matches/<id>/stats`)
   and sign in with **Sign in as Ivy**: the stats with their uncertainty.
3. Open the plan URL it prints, **https://localhost:3000/plan**: the weaknesses ranked by
   rallies lost per game and two weeks of sessions, each starting with a warm-up.
4. On a drill, read its **Why** (the metric, its value and n) and press **Show me** to see
   the rallies behind it.
5. Press **Mark done** on a session. It also works offline ("Saved on this device, will
   sync") and syncs once you are back online; **Undo** takes it back.
6. Press **Not for me** on a drill, optionally say why, then **Swap drill**: you get another
   drill for the same weakness that still fits the session.
7. `make down` when you are finished (it deletes the stack's volumes, so the demo data too).

### Troubleshooting

- Docker Hub `toomanyrequests` (pull rate limit): use a mirror,
  `DOCKERHUB_REGISTRY=mirror.gcr.io make up` (or set it in `infra/.env`).
- Image build fails with `CERTIFICATE_VERIFY_FAILED` or `SELF_SIGNED_CERT_IN_CHAIN` behind a
  TLS-intercepting proxy: pass the proxy's CA bundle (PEM) to the builds,
  `EXTRA_CA_FILE=/path/to/ca.crt make up` (absolute path; off by default). It is a BuildKit
  secret, used only while building and never stored in an image.
- `make ps` shows each service's health; `make logs` follows the logs (Ctrl-C to stop).
- `port is already allocated`: stop whatever uses that port (often a local Postgres on 5432).
- `make down` stops the stack **and deletes its volumes** (database, videos, certificates).
- `make help` lists every target.

## Documentation

- Design spec: `docs/specs/`
- Research (verified sources): `docs/research/`
- Requirements (FR/NFR): `docs/requirements/`
- Sprint plans, test scenarios: `docs/sprints/`
- Decision log (ADRs with evidence): `docs/decisions/`
- Retrospectives: `docs/retros/`
- Agent team definitions: `.claude/agents/`
