"""Stage registry of the job runtime (ADR 0012 seam ``STAGES``; context map R7).

Each stage's code belongs to the context whose model it writes; this module only registers it.
"""

from __future__ import annotations

from collections.abc import Mapping

from racket.analysis_jobs.stage import Stage
from racket.players.stages import SendSignInLinkStage
from racket.video_ingest.probe import ProbeStage

STAGES: Mapping[str, Stage] = {
    ProbeStage.name: ProbeStage(),
    SendSignInLinkStage.name: SendSignInLinkStage(),
}


def selected(stages: Mapping[str, Stage], names: tuple[str, ...]) -> Mapping[str, Stage]:
    """The stages one worker process runs (``WORKER_STAGES``; empty means all). The media
    sandbox worker runs ``probe`` only; a worker with SMTP access runs ``send_sign_in_link``."""
    if not names:
        return stages
    unknown = sorted(set(names) - set(stages))
    if unknown:
        raise ValueError(f"unknown stage(s) in WORKER_STAGES: {', '.join(unknown)}")
    return {name: stages[name] for name in names}
