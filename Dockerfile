FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    STARLIGHT_STUDIO_ROOT=/app \
    STARLIGHT_AGENT_MODE=remote \
    STARLIGHT_ALLOW_PUBLISH=true \
    STARLIGHT_GCP_PROJECT=finance-ontology-changseop \
    STARLIGHT_GCP_PROJECT_NUMBER=567090080191 \
    STARLIGHT_GCP_LOCATION=us-central1 \
    STARLIGHT_OKF_BUCKET=finance_okf \
    STARLIGHT_OKF_PREFIX=okf \
    STARLIGHT_KC_ENTRY_GROUP=finance-okf \
    STARLIGHT_KC_ENTRY_TYPE=okf-bundle \
    STARLIGHT_AGENT_RESOURCE=projects/567090080191/locations/us-central1/reasoningEngines/8299777321720610816 \
    STARLIGHT_RAG_AGENT_RESOURCE=projects/567090080191/locations/us-central1/reasoningEngines/817539122053775360 \
    KMARKET_AGENT_RESOURCE=projects/567090080191/locations/us-central1/reasoningEngines/1848235340704251904 \
    KMARKET_RAG_AGENT_RESOURCE=projects/567090080191/locations/us-central1/reasoningEngines/7928094837654421504

WORKDIR /app

RUN pip install --no-cache-dir \
    "google-auth>=2.35.0" \
    "requests>=2.32.0" \
    "pyyaml>=6.0.0"

COPY okf_veri_web /app/okf_veri_web
COPY finance/okf /app/finance/okf
COPY finance/data/un_data /app/finance/data/un_data
COPY finance/ontology/cq /app/finance/ontology/cq
COPY finance/agents/starlight-graphrag/deployment_metadata.json /app/finance/agents/starlight-graphrag/deployment_metadata.json
COPY finance/agents/starlight-graphrag/app/orchestrator/questions.py /app/finance/agents/starlight-graphrag/app/orchestrator/questions.py
COPY finance/agents/starlight-rag-agent/deployment_metadata.json /app/finance/agents/starlight-rag-agent/deployment_metadata.json
COPY ecommerce /app/ecommerce
COPY tools/studio_server.py \
     tools/agent_chat_engine.py \
     tools/agent_remote_client.py \
     tools/rag_remote_client.py \
     tools/ecommerce_agent_handler.py \
     tools/kc_registry_state.json \
     /app/tools/

EXPOSE 8080

CMD ["python", "tools/studio_server.py"]
