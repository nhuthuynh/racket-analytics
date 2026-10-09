"""`scripts/measure/statscontract.py` mirrors `docs/architecture/api-sprint-03.md` (PE-DESIGN-3;
PE-1, PE-R1S3-02, PE-R2S3-04; ADR 0033 rule 2: a contract change changes the harness in the same
commit). Each test reads the contract text and the harness constant and fails when they differ,
so neither can move alone. Negative cases first: a 204 on DELETE /me is a contract break (the
contract narrowed `DELETE_OK` from (202, 204) to (202,)), and the parsers refuse a section they
cannot find instead of comparing nothing.
"""

from __future__ import annotations

import importlib.util
import re
import sys

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit

MEASURE = SCRIPTS_DIR / "measure"
CONTRACT = SCRIPTS_DIR.parent / "docs" / "architecture" / "api-sprint-03.md"
if str(MEASURE) not in sys.path:
    sys.path.insert(0, str(MEASURE))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, MEASURE / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def section(text: str, heading: str) -> str:
    """The body of the markdown section whose heading starts with `heading` (### or ##)."""
    m = re.search(rf"^(#+) {re.escape(heading)}[^\n]*\n(.*?)(?=^#{{1,3}} |\Z)", text, re.M | re.S)
    if not m:
        raise ValueError(f"api-sprint-03 has no section {heading!r}")
    return m[2]


def success_statuses(text: str, heading: str) -> set[int]:
    found = {int(s) for s in re.findall(r"\*\*Success: (\d{3})\b", section(text, heading))}
    if not found:
        raise ValueError(f"{heading!r} names no success status")
    return found


def label_routes(text: str) -> set[tuple[str, str]]:
    rows = re.findall(r"^\| `(GET|POST) (/label/[^`]+)` \|", section(text, "5.2 Routes"), re.M)
    if not rows:
        raise ValueError("api-sprint-03 §5.2 lists no label route")
    return set(rows)


@pytest.fixture(scope="module")
def doc() -> str:
    return CONTRACT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sk():
    return _load("statscontract")


# ------------------------------------------------------------------------------ negative first
def test_a_delete_me_answered_204_is_a_contract_break() -> None:
    live = _load("live_stats")
    step = live.judge_account_deletion(
        deleted_id="acc-1",
        status=204,
        old_session=401,
        back=True,
        items=[],
        again_me={"id": "acc-2"},
    )
    assert step["ok"] is False
    assert step["problems"] == ["DELETE /me status 204"]


def test_a_missing_section_is_refused_not_compared() -> None:
    with pytest.raises(ValueError, match=r"4\.1"):
        success_statuses("## 3. Evidence\nnothing\n", "4.1 `DELETE /matches/{match_id}`")
    with pytest.raises(ValueError, match="no success status"):
        success_statuses("### 4.2 `DELETE /me`\n- body only\n", "4.2 `DELETE /me`")
    with pytest.raises(ValueError, match="no label route"):
        label_routes("### 5.2 Routes\n| Route |\n")


# ------------------------------------------------------------------------------ contract = harness
@pytest.mark.parametrize("heading", ["4.1 `DELETE /matches/{match_id}`", "4.2 `DELETE /me`"])
def test_delete_ok_is_exactly_the_contract_success_status(doc: str, sk, heading: str) -> None:
    assert set(sk.DELETE_OK) == success_statuses(doc, heading) == {202}


def test_the_purge_command_and_service_are_the_contract_ones(doc: str, sk) -> None:
    body = section(doc, "4.4 Purge job contract")
    assert f"**`{sk.PURGE_ONCE}`**" in body
    assert f"the **`{sk.PURGE_SERVICE}`** Compose service" in body
    assert f"`{sk.PURGE_SCHEDULE_VAR}`, default 86400" in body


def test_the_label_routes_are_the_contract_ones(doc: str, sk) -> None:
    assert set(sk.LABEL_ROUTES.values()) == label_routes(doc)


def test_the_labeller_admin_cli_is_the_contract_one(doc: str, sk) -> None:
    assert f"`{sk.LABELLER_ADMIN}`" in section(doc, "5.5 Labeller administration")


def test_the_confirmation_body_is_the_contract_one(doc: str, sk) -> None:
    assert sk.CONFIRM_BODY == {"confirm": "delete"}
    assert '**Body (required):** `{"confirm": "delete"}`' in section(doc, "4.1 `DELETE")


def test_the_an06_per_game_key_is_a_contract_field(doc: str, sk) -> None:
    rows = [ln for ln in section(doc, "2.1 `GET").splitlines() if ln.startswith("| AN-06 |")]
    assert len(rows) == 1
    assert f"`{sk.AN06_PER_GAME_KEY}`" in rows[0]
