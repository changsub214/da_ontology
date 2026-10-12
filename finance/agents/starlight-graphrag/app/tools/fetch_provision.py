"""fetch_provision — LLM-facing wrapper. Logic lives in services/provision_reader (ObjectRef path)."""

from __future__ import annotations

from typing import Any

from google.adk.tools import ToolContext

from app.runtime import get_runtime


def fetch_provision(provision_slot_id: str, tool_context: ToolContext) -> dict[str, Any]:
    """Read the verbatim text of a provision through its graph ObjectRef.

    Only allowed after kc_lookup returned ALLOW or SUPERSEDED_RESOLVED for the same
    provision (enforced by the governance gate).

    Args:
        provision_slot_id: `provision_slot_id` of a Provision node from graph_query.

    Returns:
        {"status": "ok", "doc_id": "01", "section_number": "제29조", "source_page": 20,
         "verbatim_body": "...", "sha256_ok": true, "gcs_uri": "gs://..."}
    """
    rt = get_runtime()
    try:
        prov = rt.provision_reader.read(provision_slot_id)
    except Exception as exc:
        return {
            "status": "error",
            "provision_slot_id": provision_slot_id,
            "error": str(exc),
        }
    return {
        "status": "ok",
        "provision_slot_id": prov.provision_slot_id,
        "kc_entry_id": prov.kc_entry_id,
        "doc_id": prov.doc_id,
        "section_number": prov.section_number,
        "source_page": prov.source_page,
        "verbatim_body": prov.verbatim_body,
        "sha256_ok": prov.sha256_ok,
        "gcs_uri": prov.gcs_uri,
    }
