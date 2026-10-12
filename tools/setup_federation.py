#!/usr/bin/env python3
"""Wire BigQuery to the Spanner ledger (zero-copy) and expose it as ONT views.

ADR 0002 / placement.yaml A2: BigQuery reads the Spanner transactional ledger
through a **Spanner external dataset** (no replication, no CDC), and standard
views in `starlight_bank` re-expose those federated tables so that they can be
used as property-graph element tables later.

Documented constraints handled here:
  * You can't create a view *inside* an external dataset, so the `ont_*` views
    live in the standard `starlight_bank` dataset.
  * Spanner primary keys aren't visible in BigQuery, so any future
    CREATE PROPERTY GRAPH over these views must declare KEY (...) explicitly.
  * Queries against external dataset tables always use Data Boost.

Usage:
    python tools/setup_federation.py            # create + smoke test
    python tools/setup_federation.py --test     # smoke test only
"""

from __future__ import annotations

import argparse
import os
import sys

PROJECT = os.environ.get("OKF_PROJECT", "finance-ontology-changseop")
LOCATION = os.environ.get("OKF_LOCATION", "us-central1")
SPANNER_INSTANCE = os.environ.get("OKF_SPANNER_INSTANCE", "finance-cs")
SPANNER_DATABASE = os.environ.get("OKF_SPANNER_DATABASE", "starlight_bank")
BQ_DATASET = os.environ.get("OKF_BQ_DATASET", "starlight_bank")
BQ_EXT_DATASET = os.environ.get("OKF_BQ_EXT_DATASET", "starlight_bank_ext")

FEDERATED_TABLES = [
    "loan_contracts",
    "collaterals",
    "delinquency_events",
    "rate_cut_requests",
    "exception_approvals",
]

EXTERNAL_SOURCE = (
    f"google-cloudspanner:/projects/{PROJECT}"
    f"/instances/{SPANNER_INSTANCE}/databases/{SPANNER_DATABASE}"
)


def run(client, sql: str, label: str):
    print(f"-- {label}")
    job = client.query(sql)
    result = job.result()
    return result


def create_external_schema(client) -> None:
    sql = (
        f"CREATE EXTERNAL SCHEMA IF NOT EXISTS `{PROJECT}.{BQ_EXT_DATASET}`\n"
        f"  OPTIONS (\n"
        f"    external_source = '{EXTERNAL_SOURCE}',\n"
        f"    location = '{LOCATION}');"
    )
    run(client, sql, f"CREATE EXTERNAL SCHEMA {BQ_EXT_DATASET} -> {SPANNER_INSTANCE}/{SPANNER_DATABASE}")


def create_ont_views(client) -> None:
    for table in FEDERATED_TABLES:
        sql = (
            f"CREATE OR REPLACE VIEW `{PROJECT}.{BQ_DATASET}.ont_{table}` AS\n"
            f"SELECT * FROM `{PROJECT}.{BQ_EXT_DATASET}.{table}`;"
        )
        run(client, sql, f"CREATE VIEW {BQ_DATASET}.ont_{table}")


def smoke_test(client) -> int:
    failures = []

    # 1) federated row counts must match what Spanner holds
    print("\n== F01 federated row counts (BigQuery reading Spanner live) ==")
    expected = {"loan_contracts": 100, "collaterals": 3, "delinquency_events": 7,
                "rate_cut_requests": 2, "exception_approvals": 3}
    for table, want in expected.items():
        got = list(client.query(
            f"SELECT COUNT(*) AS n FROM `{PROJECT}.{BQ_DATASET}.ont_{table}`"
        ).result())[0]["n"]
        ok = got == want
        print(f"  {'PASS' if ok else 'FAIL'} ont_{table:<22} expected={want:<4} got={got}")
        if not ok:
            failures.append(f"F01 {table}: {want} != {got}")

    # 2) the headline demo: one SQL statement joining the Spanner ledger with
    #    the BigQuery master tables.
    print("\n== F02 cross-store join in a single statement ==")
    sql = f"""
        SELECT
          c.ksic_section_code              AS ksic,
          COUNT(*)                          AS contracts,
          SUM(l.outstanding_amt)            AS outstanding_krw,
          ROUND(AVG(l.applied_rate), 3)     AS avg_applied_rate
        FROM `{PROJECT}.{BQ_DATASET}.ont_loan_contracts` AS l   -- Spanner (federated)
        JOIN `{PROJECT}.{BQ_DATASET}.customers`          AS c   -- BigQuery (native)
          ON l.customer_id = c.customer_id
        WHERE c.ksic_section_code IN ('F', 'G', 'H', 'L')       -- 제29조1항1호가목 단서 업종
        GROUP BY ksic
        ORDER BY ksic
    """
    rows = list(client.query(sql).result())
    for r in rows:
        print(f"  KSIC {r['ksic']}: contracts={r['contracts']:<3} "
              f"outstanding={r['outstanding_krw']:,} avg_rate={r['avg_applied_rate']}")
    ok = len(rows) > 0
    print(f"  {'PASS' if ok else 'FAIL'} cross-store join returned {len(rows)} group(s)")
    if not ok:
        failures.append("F02: cross-store join returned no rows")

    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)})")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("RESULT: PASS (F01 federated counts · F02 single-statement cross-store join)")
    return 0


def main() -> int:
    from google.cloud import bigquery

    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="skip DDL, run smoke test only")
    args = ap.parse_args()

    client = bigquery.Client(project=PROJECT, location=LOCATION)
    if not args.test:
        create_external_schema(client)
        create_ont_views(client)
    return smoke_test(client)


if __name__ == "__main__":
    sys.exit(main())
