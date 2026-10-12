"""Session-state keys. One place, so callbacks/tools never drift on key names.

ADK prefixes: `app:` shared across users, `user:` per user, `temp:` current invocation only.
"""

SCHEMA_CARD = "app:schema_card"            # KC ontology-class-anchors → prompt block
ALIAS_ROWS = "app:alias_rows"              # cached ont_entity_aliases rows
RESOLVED_ENTITIES = "temp:resolved_entities"  # D3 pre-grounding output for this turn
TOOL_CALLS_USED = "temp:tool_calls_used"   # 12-call budget counter
KC_VERDICTS = "temp:kc_verdicts"           # {kc_entry_id: verdict} — governance gate input
EVIDENCE = "temp:evidence"                 # list[EvidenceItem as dict]
BLOCKED = "temp:blocked"                   # list of blocked verdicts → D5 notice + incident
