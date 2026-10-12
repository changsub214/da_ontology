#!/usr/bin/env python3
"""Load the structured core-banking ledger into Spanner and BigQuery.

Placement is defined by `data/placement.yaml` (ADR 0002):

  Spanner  `finance-cs` / `starlight_bank`  : 트랜잭션성 5종
      loan_contracts (root) + collaterals / delinquency_events /
      rate_cut_requests / exception_approvals (INTERLEAVE IN PARENT)

  BigQuery `starlight_bank` (us-central1)   : 마스터·준정적 3종
      customers / financial_products / workout_histories

Everything else (OKF LEX layer, bridge edges, property graph) is built later on
top of these two stores.

Usage:
    python tools/load_stores.py spanner     # Spanner 5종 적재
    python tools/load_stores.py bigquery    # BigQuery 데이터셋 생성 + 마스터 3종 적재
    python tools/load_stores.py verify      # 적재 게이트 G01/G02/G04
    python tools/load_stores.py all
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import os
import sys
from typing import Any

PROJECT = os.environ.get("OKF_PROJECT", "finance-ontology-changseop")
LOCATION = os.environ.get("OKF_LOCATION", "us-central1")
SPANNER_INSTANCE = os.environ.get("OKF_SPANNER_INSTANCE", "finance-cs")
SPANNER_DATABASE = os.environ.get("OKF_SPANNER_DATABASE", "starlight_bank")
BQ_DATASET = os.environ.get("OKF_BQ_DATASET", "starlight_bank")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = os.path.join(ROOT, "finance", "data", "structured")

STR, INT, FLT, DATE = "STRING", "INT64", "FLOAT64", "DATE"

# --- Spanner: transactional tables --------------------------------------------
# NOTE: column order here must match the CSV header order used at insert time;
# we look columns up by name, so ordering differences are tolerated.
SPANNER_TABLES: dict[str, dict[str, str]] = {
    "loan_contracts": {
        "contract_id": STR, "customer_id": STR, "borrower_name": STR,
        "ksic_section_code": STR, "product_code": STR,
        "reg_dt": DATE, "contract_dt": DATE, "disburse_dt": DATE,
        "base_rate": FLT, "spread_rate": FLT, "pref_rate": FLT, "applied_rate": FLT,
        "contract_amt": INT, "outstanding_amt": INT, "overdue_days": INT,
        "asset_classification": STR, "rehab_priority_claim_yn": STR,
        "booked_provision_krw": INT, "account_status": STR,
    },
    "collaterals": {
        "contract_id": STR, "collateral_id": STR, "customer_id": STR,
        "collateral_type_code": STR, "guarantee_agency_code": STR,
        "guarantee_ratio_pct": FLT, "appraised_collateral_krw": INT,
    },
    "delinquency_events": {
        "contract_id": STR, "event_id": STR, "customer_id": STR,
        "overdue_days": INT, "overdue_principal_krw": INT,
        "overdue_interest_krw": INT, "write_off_yn": STR,
    },
    "rate_cut_requests": {
        "contract_id": STR, "request_id": STR, "customer_id": STR,
        "request_dt": DATE, "application_reason_code": STR, "patent_reg_no": STR,
        "credit_rating_before": STR, "credit_rating_after": STR,
        "yoy_revenue_growth_pct": FLT, "review_status_code": STR,
        "approved_cut_bp": INT,
    },
    "exception_approvals": {
        "contract_id": STR, "approval_id": STR, "customer_id": STR,
        "approval_type_code": STR, "approval_status": STR,
        "approver_role_code": STR, "approval_dt": DATE,
    },
}

# --- BigQuery: master / semi-static tables ------------------------------------
BQ_TABLES: dict[str, dict[str, str]] = {
    "customers": {
        "customer_id": STR, "borrower_name": STR, "corp_reg_no": STR,
        "ksic_section_code": STR, "ksic_detail_code": STR, "industry_name": STR,
        "credit_rating": STR, "tcb_tech_grade": STR, "debt_ratio_pct": FLT,
    },
    "financial_products": {
        "product_code": STR, "product_name": STR, "loan_category": STR,
        "target_segment": STR, "base_rate_benchmark": STR,
        "repayment_method": STR, "max_maturity_months": INT,
    },
    "workout_histories": {
        "workout_id": STR, "contract_id": STR, "customer_id": STR,
        "workout_start_dt": DATE, "consecutive_normal_repay_months": INT,
        "new_equity_paid_in_krw": INT, "legal_proceeding_code": STR,
    },
}

# G04: 적재되면 시나리오 정답이 새는(Answer Leakage) 컬럼 패턴.
FORBIDDEN_COLUMN_TOKENS = (
    "governing_pdf", "scenario", "golden", "is_answer",
    "min_prov_rate", "provision_rate_pct", "expected_",
)


def read_csv(name: str) -> list[dict[str, str]]:
    path = os.path.join(CSV_DIR, f"{name}.csv")
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def coerce(value: str, kind: str) -> Any:
    if value is None or value == "":
        return None
    if kind == INT:
        return int(float(value))
    if kind == FLT:
        return float(value)
    if kind == DATE:
        return _dt.date.fromisoformat(value)
    return value


def load_spanner() -> int:
    from google.cloud import spanner

    client = spanner.Client(project=PROJECT)
    database = client.instance(SPANNER_INSTANCE).database(SPANNER_DATABASE)

    total = 0
    for table, schema in SPANNER_TABLES.items():
        rows = read_csv(table)
        columns = list(schema.keys())
        values = [[coerce(r.get(c), schema[c]) for c in columns] for r in rows]
        # Delete-then-insert so the loader is idempotent. Deleting the root with
        # ON DELETE CASCADE also clears the interleaved children.
        with database.batch() as batch:
            if table == "loan_contracts":
                batch.delete("loan_contracts", spanner.KeySet(all_=True))
        with database.batch() as batch:
            batch.insert(table=table, columns=columns, values=values)
        print(f"  spanner  {table:<22} {len(values):>4} rows")
        total += len(values)
    print(f"[spanner] {SPANNER_INSTANCE}/{SPANNER_DATABASE}: {total} rows loaded")
    return total


def load_bigquery() -> int:
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT)
    dataset_id = f"{PROJECT}.{BQ_DATASET}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = LOCATION
    dataset.description = (
        "Starlight Bank — master/reference data + OKF LEX layer (ADR 0002). "
        "Transactional ledger lives in Spanner finance-cs/starlight_bank."
    )
    client.create_dataset(dataset, exists_ok=True)
    print(f"[bigquery] dataset ready: {dataset_id} ({LOCATION})")

    total = 0
    for table, schema in BQ_TABLES.items():
        bq_schema = [bigquery.SchemaField(c, t) for c, t in schema.items()]
        job_config = bigquery.LoadJobConfig(
            schema=bq_schema,
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        path = os.path.join(CSV_DIR, f"{table}.csv")
        with open(path, "rb") as fh:
            job = client.load_table_from_file(
                fh, f"{dataset_id}.{table}", job_config=job_config
            )
        job.result()
        n = client.get_table(f"{dataset_id}.{table}").num_rows
        print(f"  bigquery {table:<22} {n:>4} rows")
        total += n
    print(f"[bigquery] {dataset_id}: {total} rows loaded")
    return total


def verify() -> int:
    """Gates G01 (row parity), G02 (cross-store refs), G04 (no answer leakage)."""
    from google.cloud import bigquery, spanner

    failures: list[str] = []

    sp = spanner.Client(project=PROJECT).instance(SPANNER_INSTANCE).database(SPANNER_DATABASE)
    bq = bigquery.Client(project=PROJECT)

    # G01 — row counts match the CSV source of record.
    print("== G01 row counts ==")
    for table in SPANNER_TABLES:
        expected = len(read_csv(table))
        with sp.snapshot() as snap:
            got = list(snap.execute_sql(f"SELECT COUNT(*) FROM {table}"))[0][0]
        ok = expected == got
        print(f"  {'PASS' if ok else 'FAIL'} spanner  {table:<22} csv={expected:<4} db={got}")
        if not ok:
            failures.append(f"G01 spanner {table}: {expected} != {got}")
    for table in BQ_TABLES:
        expected = len(read_csv(table))
        got = bq.get_table(f"{PROJECT}.{BQ_DATASET}.{table}").num_rows
        ok = expected == got
        print(f"  {'PASS' if ok else 'FAIL'} bigquery {table:<22} csv={expected:<4} db={got}")
        if not ok:
            failures.append(f"G01 bigquery {table}: {expected} != {got}")

    # G02 — cross-store logical references (no DB-level FK exists by design).
    print("== G02 cross-store referential integrity ==")
    cust_ids = {r["customer_id"] for r in read_csv("customers")}
    prod_codes = {r["product_code"] for r in read_csv("financial_products")}
    with sp.snapshot() as snap:
        pairs = list(snap.execute_sql(
            "SELECT contract_id, customer_id, product_code FROM loan_contracts"))
    orphan_cust = [p[0] for p in pairs if p[1] not in cust_ids]
    orphan_prod = [p[0] for p in pairs if p[2] and p[2] not in prod_codes]
    for label, orphans in (("customer_id", orphan_cust), ("product_code", orphan_prod)):
        ok = not orphans
        print(f"  {'PASS' if ok else 'FAIL'} loan_contracts.{label} orphans={len(orphans)}"
              + ("" if ok else f" {orphans[:5]}"))
        if not ok:
            failures.append(f"G02 {label}: {len(orphans)} orphans")
    # children must point at an existing contract
    contract_ids = {p[0] for p in pairs}
    for child in ("collaterals", "delinquency_events", "rate_cut_requests",
                  "exception_approvals"):
        with sp.snapshot() as snap:
            got = {r[0] for r in snap.execute_sql(f"SELECT contract_id FROM {child}")}
        orphans = got - contract_ids
        ok = not orphans
        print(f"  {'PASS' if ok else 'FAIL'} {child:<22} orphan contracts={len(orphans)}")
        if not ok:
            failures.append(f"G02 {child}: {len(orphans)} orphans")
    # workout_histories lives in BigQuery but references Spanner contracts
    wk_orphans = [r["workout_id"] for r in read_csv("workout_histories")
                  if r["contract_id"] not in contract_ids]
    ok = not wk_orphans
    print(f"  {'PASS' if ok else 'FAIL'} workout_histories(BQ)->loan_contracts(Spanner) "
          f"orphans={len(wk_orphans)}")
    if not ok:
        failures.append(f"G02 workout_histories: {wk_orphans}")

    # G04 — no answer-leakage columns made it into either store.
    print("== G04 zero answer leakage ==")
    all_cols = [(t, c) for t, s in SPANNER_TABLES.items() for c in s]
    all_cols += [(t, c) for t, s in BQ_TABLES.items() for c in s]
    leaks = [f"{t}.{c}" for t, c in all_cols
             if any(tok in c.lower() for tok in FORBIDDEN_COLUMN_TOKENS)]
    ok = not leaks
    print(f"  {'PASS' if ok else 'FAIL'} forbidden columns={len(leaks)} {leaks}")
    if not ok:
        failures.append(f"G04: {leaks}")

    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)})")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("RESULT: PASS (G01 row counts · G02 cross-store refs · G04 no leakage)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["spanner", "bigquery", "verify", "all"])
    args = ap.parse_args()

    if args.command in ("spanner", "all"):
        load_spanner()
    if args.command in ("bigquery", "all"):
        load_bigquery()
    if args.command in ("verify", "all"):
        return verify()
    return 0


if __name__ == "__main__":
    sys.exit(main())
