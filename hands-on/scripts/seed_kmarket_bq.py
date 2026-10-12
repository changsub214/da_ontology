#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1-Click BigQuery Seeding Script for the K-Market Ontology & Property Graph Hands-on Workshop.

Usage:
    python3 scripts/seed_kmarket_bq.py --project YOUR_PROJECT_ID
"""

from __future__ import annotations

import argparse
import os
from google.cloud import bigquery

HERE = os.path.dirname(os.path.abspath(__file__))
SQL_DIR = os.path.abspath(os.path.join(HERE, "..", "sql"))


def run_sql_file(client: bigquery.Client, project_id: str, filename: str) -> None:
    path = os.path.join(SQL_DIR, filename)
    with open(path, "r", encoding="utf-8") as fh:
        raw_sql = fh.read()
    bound_sql = raw_sql.replace("YOUR_PROJECT_ID", project_id)
    print(f"===> Executing {filename} on project `{project_id}`...")
    job = client.query(bound_sql)
    job.result()
    print(f"  [OK] {filename} completed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed K-Market E-Commerce & Ontology Graph in BigQuery")
    parser.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT", "YOUR_PROJECT_ID"))
    parser.add_argument("--location", default="us-central1")
    args = parser.parse_args()

    client = bigquery.Client(project=args.project, location=args.location)
    run_sql_file(client, args.project, "01_seed_kmarket_tables.sql")
    run_sql_file(client, args.project, "02_create_ecommerce_graph.sql")
    print("\n✅ K-Market BigQuery Property Graph (`kmarket_ontology.ecommerce_graph`) is ready!")


if __name__ == "__main__":
    main()
