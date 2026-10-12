"""D4: read OKF provision text through BigQuery ObjectRef (graph node → signed URL → GCS).

Path: Provision node `gcs_obj_ref` → OBJ.GET_ACCESS_URL(ref,'r') (authorizer = BQ
connection SA) → HTTP GET → split YAML frontmatter / verbatim body → sha256 check.
The agent's own identity needs no storage.objects.get — access is mediated by the graph.
"""

from __future__ import annotations

import hashlib
from typing import Any
import yaml

from app.domain.models import ProvisionText
from app.ports import ObjectRefPort


def _split_frontmatter_and_body(markdown_text: str) -> tuple[dict[str, Any], str]:
    """Split `---\\n...\\n---\\n<body>` into (frontmatter_dict, body_str)."""
    txt = markdown_text.lstrip("\ufeff")
    if not txt.startswith("---"):
        return {}, txt.strip()
    parts = txt.split("---", 2)
    if len(parts) < 3:
        return {}, txt.strip()
    fm_raw, body = parts[1], parts[2]
    try:
        fm = yaml.safe_load(fm_raw) or {}
        if not isinstance(fm, dict):
            fm = {}
    except Exception:
        fm = {}
    return fm, body.strip()


def _verify_sha256(body: str, fm: dict[str, Any], full_text: str) -> bool | None:
    expected = str(fm.get("sha256") or fm.get("digest") or "").strip().lower()
    if expected.startswith("sha256:"):
        expected = expected.split(":", 1)[1].strip()
    if not expected:
        return True
    body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest().lower()
    full_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest().lower()
    return expected in (body_hash, full_hash)


class ProvisionReader:
    def __init__(self, objectref: ObjectRefPort) -> None:
        self._objectref = objectref

    def read(self, provision_slot_id: str) -> ProvisionText:
        meta = self._objectref.signed_read_url(provision_slot_id)
        read_url = str(meta.get("read_url") or "")
        raw_md = self._objectref.fetch(read_url) if read_url else str(meta.get("raw_markdown") or "")
        fm, body = _split_frontmatter_and_body(raw_md)

        doc_id = str(meta.get("doc_id") or fm.get("doc_id") or fm.get("source_doc") or "")
        if "_" in doc_id and doc_id[:2].isdigit():
            doc_id = doc_id[:2]
        section_number = str(meta.get("section_number") or fm.get("section_number") or fm.get("locator") or "") or None
        raw_page = meta.get("source_page") or fm.get("source_page") or fm.get("page")
        source_page = int(raw_page) if raw_page is not None and str(raw_page).isdigit() else None
        kc_entry_id = str(meta.get("kc_entry_id") or fm.get("kc_entry_id") or fm.get("id") or provision_slot_id)
        gcs_uri = str(meta.get("gcs_uri") or fm.get("gcs_uri") or "")

        return ProvisionText(
            provision_slot_id=provision_slot_id,
            kc_entry_id=kc_entry_id,
            doc_id=doc_id,
            section_number=section_number,
            source_page=source_page,
            verbatim_body=body,
            frontmatter=fm,
            gcs_uri=gcs_uri,
            sha256_ok=_verify_sha256(body, fm, raw_md),
        )
