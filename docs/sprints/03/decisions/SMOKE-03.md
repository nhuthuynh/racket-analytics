# SMOKE-03 decisions

Small decisions of ticket SMOKE-03 (sprint-close integration smoke of `main` at `1842e96`; SRE-SMOKE-3), one dated row each (who, decision, evidence, reasoning). Append only. One file per ticket (PO rule 2026-10-07); the DOCS/RETRO ticket folds these rows into the sprint's decision log.

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-10-10 | sre-devops-engineer | **Prune build cache and dangling images only (disk-and-prune.md steps 1-3); leave the other rounds' app images** | `docker ps -q \| wc -l` → 0; `df -h /` 11G → `docker builder prune -af` (3.631 GB) + `docker image prune -f` (0 B) → 14G | The run started at the 10 GB floor; build cache is safe to drop with no build running; images of other rounds are not this round's to remove (disk-and-prune.md) |
| 2026-10-10 | sre-devops-engineer | **No Compose image build; Compose for the pulled services, the app services as local processes behind the committed Caddyfile** | 13.07 GiB free < `RA_UP_MIN_FREE_GB` 16; a fresh build takes about 6 GB (disk-and-prune.md) | Lowering the build floor would risk the 10 GB run floor for every lane; the same topology as the pre-review and round-2 smokes keeps the results comparable. Container hardening and IT-00-10 stay covered by `infra/tests/test_compose_*.py` and CI's Compose E2E job |
| 2026-10-10 | senior-qa-engineer | **Run Playwright with CI's gated filter (`--grep-invert "@red-until-"`) and no separate red-until step** | `grep -rn "@red-until-" web/e2e` → nothing | With no tagged test left, the gated run is every journey; a listed step would select 0 tests |
