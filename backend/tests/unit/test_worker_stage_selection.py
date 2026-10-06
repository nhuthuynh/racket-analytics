"""``WORKER_STAGES`` selects the stages one worker process runs (ST-013; ADR 0027)."""

from __future__ import annotations

import pytest

from racket.worker.stages import STAGES, selected


def test_an_unknown_stage_name_is_refused() -> None:
    with pytest.raises(ValueError, match="nope"):
        selected(STAGES, ("probe", "nope"))


def test_no_names_means_every_stage() -> None:
    assert set(selected(STAGES, ())) == {"probe", "send_sign_in_link"}


def test_the_sandbox_worker_can_run_probe_only() -> None:
    assert list(selected(STAGES, ("probe",))) == ["probe"]
