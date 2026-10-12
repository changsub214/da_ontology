#!/bin/bash

# ==============================================================================
# GCP 관리자 사전 환경 구성 (setup_iam_and_api.sh)
# K-Market BigQuery Property Graph & Graph Agent (CAA / ADK) 실습 통합 API 및 IAM 설정
# Usage: ./setup_iam_and_api.sh [PROJECT_ID] [USER_EMAIL_1] [USER_EMAIL_2 ...]
# ==============================================================================

set -e

POC_PROJECT_ID="${1:-${POC_PROJECT_ID:-YOUR_PROJECT_ID}}"

if [ "$#" -ge 2 ]; then
    shift
    USERS=("$@")
else
    USERS=("${POC_USER:-user@example.com}")
fi

echo "==================================================="
echo "===> Target GCP Project: $POC_PROJECT_ID"
echo "===> Target Users: ${USERS[*]}"
echo "==================================================="

# ------------------------------------------------------------------------------
# 1. API 활성화 (Step 1 BigQuery Graph & Step 2 Graph Agent)
# ------------------------------------------------------------------------------
echo "===> Enabling APIs for Step 1 & Step 2..."

gcloud services enable \
    bigquery.googleapis.com \
    aiplatform.googleapis.com \
    geminidataanalytics.googleapis.com \
    cloudaicompanion.googleapis.com \
    --project="$POC_PROJECT_ID"

# ------------------------------------------------------------------------------
# 2. IAM Roles 부여
# ------------------------------------------------------------------------------
ROLES=(
    "roles/viewer"
    "roles/bigquery.jobUser"
    "roles/bigquery.dataEditor"
    "roles/aiplatform.user"
    "roles/geminidataanalytics.dataAgentCreator"
)

for USER_EMAIL in "${USERS[@]}"; do
    echo "===> Applying IAM policy bindings to $USER_EMAIL..."
    for ROLE in "${ROLES[@]}"; do
        gcloud projects add-iam-policy-binding "$POC_PROJECT_ID" \
            --member="user:$USER_EMAIL" \
            --role="$ROLE" --quiet > /dev/null
    done
done

echo "===> Verifying enabled APIs..."
gcloud services list --enabled --project="$POC_PROJECT_ID" \
    --filter="NAME:(bigquery.googleapis.com OR aiplatform.googleapis.com OR geminidataanalytics.googleapis.com)" \
    --format="table(config.name, state)"
