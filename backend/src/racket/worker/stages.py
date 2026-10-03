"""Stage registry of the job runtime (ADR 0012 seam ``STAGES``; context map R7).

Each stage's code belongs to the context whose model it writes; this module only registers it.
"""

from __future__ import annotations

from collections.abc import Mapping

from racket.analysis_jobs.stage import Stage
from racket.video_ingest.probe import ProbeStage

STAGES: Mapping[str, Stage] = {ProbeStage.name: ProbeStage()}
