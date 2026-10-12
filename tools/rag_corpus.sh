#!/usr/bin/env bash
# RAG Engine corpus for the RAG arm of the RAG-vs-GraphRAG comparison (ADR 0011 evaluation-only exception).
# REST only (no vertexai SDK). Read-only by default; mutating subcommands must be named explicitly.
#
#   tools/rag_corpus.sh create            # create corpus starlight-rag-pdfs (fails if one with that name exists)
#   tools/rag_corpus.sh upload <corpus>   # upload data/un_data/*.pdf (filenames kept: first 2 chars = doc id)
#   tools/rag_corpus.sh verify [<corpus>] # gate R1-G1: 10/10 files present, display names == local filenames
#
# Settings are fixed in agents/design/rag_agent_v0.yaml (v0.2.0).
set -euo pipefail

PROJECT="${STARLIGHT_PROJECT_ID:-finance-ontology-changseop}"
REGION="${STARLIGHT_RAG_REGION:-us-central1}"
NAME="${STARLIGHT_RAG_CORPUS_NAME:-starlight-rag-pdfs}"
EMBED="text-multilingual-embedding-002"
CHUNK=512
OVERLAP=100
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${STARLIGHT_RAG_SRC_DIR:-$ROOT/finance/data/un_data}"
API="https://${REGION}-aiplatform.googleapis.com"
BASE="projects/${PROJECT}/locations/${REGION}"

PY="${STARLIGHT_PYTHON:-$ROOT/finance/agents/starlight-graphrag/.venv/bin/python}"
tok() { "$PY" -c "import sys; sys.path.insert(0, '$ROOT/tools'); from agent_remote_client import _access_token; print(_access_token())"; }

list_corpora() {
  curl -sS -H "Authorization: Bearer $(tok)" "$API/v1/$BASE/ragCorpora"
}

wait_op() {  # $1 = operation name
  local op="$1" i
  for i in $(seq 1 60); do
    local r; r=$(curl -sS -H "Authorization: Bearer $(tok)" "$API/v1/$op")
    if echo "$r" | python3 -c "import json,sys; sys.exit(0 if json.load(sys.stdin).get('done') else 1)"; then
      echo "$r"; return 0
    fi
    sleep 5
  done
  echo "timeout waiting for $op" >&2; return 1
}

cmd_create() {
  if list_corpora | python3 -c "import json,sys; sys.exit(0 if any(c.get('displayName')=='$NAME' for c in json.load(sys.stdin).get('ragCorpora',[])) else 1)"; then
    echo "corpus '$NAME' already exists in $REGION — refusing to create a duplicate" >&2; exit 1
  fi
  local body
  body=$(cat <<JSON
{"displayName":"$NAME",
 "description":"Starlight RAG arm: 10 PDFs from data/un_data (ADR 0011, evaluation only)",
 "vectorDbConfig":{
   "ragEmbeddingModelConfig":{"vertexPredictionEndpoint":{"endpoint":"$BASE/publishers/google/models/$EMBED"}}}}
JSON
)
  local r; r=$(curl -sS -X POST -H "Authorization: Bearer $(tok)" -H "Content-Type: application/json" \
    "$API/v1/$BASE/ragCorpora" -d "$body")
  local op; op=$(echo "$r" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('name') or '')")
  [ -n "$op" ] || { echo "create failed: $r" >&2; exit 1; }
  wait_op "$op" | python3 -c "import json,sys; d=json.load(sys.stdin); e=d.get('error'); r=d.get('response',{}); print('ERROR', e) if e else print(r.get('name'))"
}

cmd_upload() {
  local corpus="$1" f n=0 fail=0
  for f in "$SRC"/*.pdf; do
    local fn; fn=$(basename "$f")
    local meta
    meta=$(python3 -c "import json,sys; print(json.dumps({'rag_file':{'display_name':sys.argv[1]},'upload_rag_file_config':{'rag_file_transformation_config':{'rag_file_chunking_config':{'fixed_length_chunking':{'chunk_size':$CHUNK,'chunk_overlap':$OVERLAP}}}}}, ensure_ascii=False))" "$fn")
    local r; r=$(curl -sS -X POST -H "Authorization: Bearer $(tok)" -H "X-Goog-Upload-Protocol: multipart" \
      -F "metadata=$meta;type=application/json" -F "file=@$f;type=application/pdf" \
      "$API/upload/v1/$corpus/ragFiles:upload")
    if echo "$r" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('ragFile',{}).get('name') else 1)"; then
      n=$((n+1)); echo "ok   $fn"
    else
      fail=$((fail+1)); echo "FAIL $fn :: $r" >&2
    fi
  done
  echo "uploaded $n, failed $fail"
  [ "$fail" -eq 0 ]
}

cmd_verify() {
  local corpus="${1:-}"
  if [ -z "$corpus" ]; then
    corpus=$(list_corpora | python3 -c "import json,sys; c=[x['name'] for x in json.load(sys.stdin).get('ragCorpora',[]) if x.get('displayName')=='$NAME']; print(c[0] if len(c)==1 else '')")
    [ -n "$corpus" ] || { echo "FAIL: expected exactly one corpus named $NAME" >&2; exit 1; }
  fi
  local local_list; local_list=$(cd "$SRC" && ls -1 *.pdf)
  curl -sS -H "Authorization: Bearer $(tok)" "$API/v1/$corpus/ragFiles?pageSize=100" | LOCAL="$local_list" CORPUS="$corpus" python3 -c "
import json, os, sys
d = json.load(sys.stdin)
files = d.get('ragFiles', [])
remote = sorted(f.get('displayName', '') for f in files)
local = sorted(x for x in os.environ['LOCAL'].splitlines() if x)
states = {f.get('displayName'): (f.get('fileStatus') or {}).get('state', '?') for f in files}
print('corpus', os.environ['CORPUS'])
for n in remote: print(' ', states[n], n)
ok = remote == local and all(s == 'ACTIVE' for s in states.values())
print('R1-G1', 'PASS' if ok else 'FAIL', f'{len(remote)}/{len(local)}', 'missing=', sorted(set(local)-set(remote)), 'extra=', sorted(set(remote)-set(local)))
sys.exit(0 if ok else 1)
"
}

case "${1:-verify}" in
  create) cmd_create ;;
  upload) cmd_upload "${2:?corpus resource name required}" ;;
  verify) cmd_verify "${2:-}" ;;
  *) echo "usage: $0 {create|upload <corpus>|verify [<corpus>]}" >&2; exit 2 ;;
esac
