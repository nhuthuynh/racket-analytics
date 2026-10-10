"""S3-DoD-P11 footage bucket measurement (FIX-03-1d; sprint-03 §9.1; BLK-GOLD-01; PO P12 (b)).

Naming the provider of the private footage bucket is the PO's decision (P11); no agent can or
may supply it. The row's status is therefore measured: from the PO's recorded P11 answer and
from a probe of the bucket (does it exist, and does an anonymous reader get refused). The
sprint plan must say the same.

Negative cases first: an anonymous 403 alone never proves the bucket exists (SeaweedFS answers
403 for a missing bucket too), a readable bucket is never met, and an unclear P11 row is no
answer (fail closed, ADR 0014).
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR
from footage_bucket_fixtures import po_record, sprint_plan

SCRIPT = SCRIPTS_DIR / "measure" / "footage_bucket.py"
PLAN = REPO_ROOT / "docs" / "sprints" / "sprint-03.md"
PO = REPO_ROOT / "docs" / "requirements" / "po-input-2026-10-05.md"
WAITING = "not met: waiting on P11"


@pytest.fixture(scope="module")
def m():
    spec = importlib.util.spec_from_file_location("footage_bucket", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["footage_bucket"] = module
    spec.loader.exec_module(module)
    return module


# --- negative cases first -------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("status", [301, 400, 500, 503])
def test_an_unexpected_anonymous_answer_is_refused(m, status: int) -> None:
    with pytest.raises(ValueError, match=r"anonymous read"):
        m.bucket_state(True, status)


@pytest.mark.unit
@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_anonymous_read_on_a_missing_bucket_is_absent_not_private(m, status) -> None:
    assert m.bucket_state(False, status) == "absent"


@pytest.mark.unit
@pytest.mark.parametrize(
    "decision",
    ["Relayed to the PO on 2026-10-06; still open.", "", "Provider:", "We will decide later"],
)
def test_a_p11_row_without_a_named_provider_is_no_answer(m, decision: str) -> None:
    assert m.po_provider(po_record(decision)) is None


@pytest.mark.unit
def test_the_p12_row_that_mentions_p11_is_not_a_p11_answer(m) -> None:
    assert m.po_provider(po_record()) is None


@pytest.mark.unit
@pytest.mark.parametrize("state", [None, "absent", "public", "private"])
def test_without_a_provider_every_bucket_state_is_waiting_on_p11(m, state) -> None:
    result = m.measure(None, state)
    assert result["status"] == WAITING
    assert result["met"] is False


@pytest.mark.unit
def test_a_readable_bucket_is_not_met(m) -> None:
    result = m.measure("Example Cloud", "public")
    assert result["met"] is False
    assert result["status"] == "not met: footage bucket is readable without credentials"


@pytest.mark.unit
@pytest.mark.parametrize("state", [None, "absent"])
def test_a_provider_without_a_bucket_is_not_met(m, state) -> None:
    result = m.measure("Example Cloud", state)
    assert result["met"] is False
    assert result["status"] == "not met: P11 answered, footage bucket not built (C3-08)"


@pytest.mark.unit
def test_a_plan_without_the_row_is_refused(m) -> None:
    with pytest.raises(ValueError, match="S3-DoD-P11"):
        m.dod_status("# sprint plan\n\n| DoD row | Status |\n|---|---|\n")


# --- positive cases -------------------------------------------------------------------------


@pytest.mark.unit
def test_a_provider_and_a_private_bucket_are_met(m) -> None:
    assert m.bucket_state(True, 403) == "private"
    provider = m.po_provider(po_record("**Provider: Example Cloud, eu-west.** Bucket per ADR 0006"))
    assert provider == "Example Cloud, eu-west"
    result = m.measure(provider, "private")
    assert result["met"] is True
    assert result["status"] == "met (provider: Example Cloud, eu-west; anonymous read refused)"


@pytest.mark.unit
def test_the_plan_verdict_ignores_emphasis_and_the_dated_note(m) -> None:
    plan = sprint_plan("**not met: waiting on P11** (no footage of people stored, 2026-10-07)")
    assert m.dod_verdict(m.dod_status(plan)) == WAITING
    assert m.dod_verdict("met (provider: X; anonymous read refused)") == "met"


# --- the repository itself ------------------------------------------------------------------


@pytest.mark.unit
def test_the_repository_po_record_and_sprint_plan_agree_on_s3_dod_p11(m) -> None:
    """Offline drift guard (runs in CI): while the PO record names no provider, the plan must
    say "not met: waiting on P11"; it may never say met before a provider is named."""
    verdict = m.dod_verdict(m.dod_status(PLAN.read_text(encoding="utf-8")))
    if m.po_provider(PO.read_text(encoding="utf-8")) is None:
        assert verdict == WAITING
    else:
        assert verdict != WAITING


# --- live, on the local object store (SeaweedFS) --------------------------------------------


@pytest.fixture(scope="module")
def s3_env(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, str]]:
    if os.environ.get("S3_ENDPOINT_URL"):
        yield {k: v for k, v in os.environ.items() if k.startswith("S3_")}
        return
    env = {**os.environ, "RA_DEV_STATE": str(tmp_path_factory.mktemp("objstore"))}
    script = str(SCRIPTS_DIR / "dev-objectstore.sh")
    res = subprocess.run(["bash", script, "start"], capture_output=True, text=True, env=env,
                         timeout=180, check=False)
    assert res.returncode == 0, res.stderr
    try:
        yield dict(re.findall(r"^export (S3_[A-Z_]+)=(\S+)$", res.stdout, re.M))
    finally:
        subprocess.run(["bash", script, "stop"], env=env, timeout=60, check=False)


def _live(s3_env: dict[str, str], bucket: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **s3_env}
    cmd = [sys.executable, str(SCRIPT), "--po", str(PO), "--dod", str(PLAN),
           "--endpoint", s3_env["S3_ENDPOINT_URL"], "--bucket", bucket]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)


@pytest.mark.integration
def test_live_a_missing_bucket_is_absent_although_anonymous_reads_get_403(s3_env) -> None:
    out = _live(s3_env, "racket-footage-does-not-exist")
    assert out.returncode == 1, out.stdout + out.stderr
    result = json.loads(out.stdout)
    assert (result["bucket"], result["anonymous_status"]) == ("absent", 403)
    assert result["status"] == WAITING  # the real PO record names no provider


@pytest.mark.integration
def test_live_an_existing_private_bucket_is_private_and_the_plan_agrees(s3_env) -> None:
    out = _live(s3_env, s3_env["S3_BUCKET_MEDIA"])
    assert out.returncode in (0, 1), out.stdout + out.stderr  # 3 = plan disagrees
    assert json.loads(out.stdout)["bucket"] == "private"
