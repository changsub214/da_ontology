"""D5 incident sinks (IncidentSinkPort).

Now      : LogIncidentSink — structured log line (Cloud Logging when deployed).
Later    : PubSubIncidentSink — topic → BigQuery subscription (direct write) →
           scheduled batch job → notify the owning team. Selected via
           STARLIGHT_INCIDENT_SINK=pubsub; no service/callback code changes needed.
"""

from __future__ import annotations

import dataclasses
import json
import logging

from app.domain.models import GovernanceIncident

_log = logging.getLogger("starlight.governance.incident")


class LogIncidentSink:
    def emit(self, incident: GovernanceIncident) -> None:
        try:
            _log.warning("GOVERNANCE_INCIDENT %s", json.dumps(dataclasses.asdict(incident), ensure_ascii=False))
        except Exception:  # never break the user turn
            _log.exception("incident sink failed")


class PubSubIncidentSink:  # future (not in prototype scope)
    def __init__(self, topic_path: str) -> None:
        self._topic_path = topic_path

    def emit(self, incident: GovernanceIncident) -> None:
        raise NotImplementedError("Future: google-cloud-pubsub publish; BQ subscription schema = GovernanceIncident")
