"""IT-03-07 (ST-050; NFR-066 b, ADR 0006): job <-> store <-> DB, a store failure mid-purge.

The object store refuses one delete during the first purge pass. Whatever order PE-3 chooses,
the pass must not leave an orphan: if a stored object of the match is still there, the database
still knows it (a later pass can find it); rows are never gone while their objects remain.
The next pass completes (no row, no object), and a third pass is a no-op.

Written red first (QA-ACC-3): ``red_until`` ST-050.
"""

from __future__ import annotations

import contextlib
from typing import Any

import pytest

from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.red_until(story="ST-050")]


def _purge_tolerating_failure() -> None:
    # the injected failure may surface as an exception or an exit code; the state is checked
    with contextlib.suppress(Exception):
        st.PURGE_MAIN.load()(["--once"])


def test_it_03_07_a_store_failure_leaves_no_orphan_and_the_next_pass_completes(
    api: ApiDriver, committed_db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    match_id = st.tagged_example(api, "ivy", "IT-03-07")
    keys = st.object_keys_of(committed_db, match_id)
    assert keys
    assert st.delete_match(api, "ivy", match_id).status_code in st.statscontract.DELETE_OK

    store_cls = st.OBJECT_STORE.load()
    real_delete = store_cls.delete
    failures = {"n": 0}

    def failing_delete(self: Any, key: str) -> None:
        if failures["n"] == 0:
            failures["n"] += 1
            raise ConnectionError("injected store failure (IT-03-07)")
        real_delete(self, key)

    monkeypatch.setattr(store_cls, "delete", failing_delete)
    _purge_tolerating_failure()
    assert failures["n"] == 1, "the purge never deleted an object, so no failure was injected"

    still_stored = st.keys_still_stored(keys)
    known = st.object_keys_of(committed_db, match_id)
    orphans = sorted(set(still_stored) - set(known))
    rows = {k: n for k, n in st.rows_holding(committed_db, [match_id]).items() if n}
    assert orphans == [], f"objects left that no row points to: {orphans}"
    assert still_stored == [] or rows, "rows gone while an object of the match remains"

    monkeypatch.setattr(store_cls, "delete", real_delete)
    st.run_purge_once()
    assert {k: n for k, n in st.rows_holding(committed_db, [match_id]).items() if n} == {}
    assert st.keys_still_stored(keys) == []

    before = st.rows_holding(committed_db, [match_id])
    st.run_purge_once()  # no-op
    assert st.rows_holding(committed_db, [match_id]) == before


def test_it_03_07_two_passes_at_once_both_succeed_and_leave_nothing(
    api: ApiDriver, committed_db: Any
) -> None:
    """QA-FUZZ-3 concurrency case for the purge (NFR-058): parallel runs do not fail or
    double-delete into an error."""
    import concurrent.futures

    match_ids = [st.tagged_example(api, "ivy", f"IT-03-07 parallel {i}") for i in range(3)]
    keys = [k for m in match_ids for k in st.object_keys_of(committed_db, m)]
    for m in match_ids:
        assert st.delete_match(api, "ivy", m).status_code in st.statscontract.DELETE_OK
    main = st.PURGE_MAIN.load()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda _: main(["--once"]), range(2)))
    assert codes == [0, 0]
    assert {k: n for k, n in st.rows_holding(committed_db, match_ids).items() if n} == {}
    assert st.keys_still_stored(keys) == []
