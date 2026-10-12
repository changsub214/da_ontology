#!/bin/bash

# ==============================================================================
# 워크숍 완료 후 임시 IAM 권한 회수 (cleanup_iam_roles.sh)
# Usage: ./cleanup_iam_roles.sh [PROJECT_ID] [USER_EMAIL_1] [USER_EMAIL_2 ...]
# ==============================================================================

set -e

POC_PROJECT_ID="${1:-${POC_PROJECT_ID:-YOUR_PROJECT_ID}}"

if [ "$#" -ge 2 ]; then
    shift
    USERS=("$@")
else
    USERS=("${POC_USER:-user@example.com}")
fi

ROLES_TO_REMOVE=(
    "roles/bigquery.dataEditor"
    "roles/geminidataanalytics.dataAgentCreator"
    "roles/aiplatform.user"
    "roles/bigquery.jobUser"
)

for USER_EMAIL in "${USERS[@]}"; do
    echo "===> Removing temporary workshop roles for $USER_EMAIL..."
    for ROLE in "${ROLES_TO_REMOVE[@]}"; do
        gcloud projects remove-iam-policy-binding "$POC_PROJECT_ID" \
            --member="user:$USER_EMAIL" \
            --role="$ROLE" --quiet > /dev/null || true
    done
done
