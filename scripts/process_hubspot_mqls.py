#!/usr/bin/env python3
"""
Process HubSpot MQL data and save SM_ KPIs to database.

Usage:
    python scripts/process_hubspot_mqls.py hubspot_mqls_q2_2026.json Q2 2026

Calculates and saves:
  SM_SAL_MQL_Volume  — SAL ICP MQLs created this quarter
  SM_AEC_MQL_Volume  — AEC ICP MQLs created this quarter
  SM_ICP_MQL_Share   — % of MQLs from ICP verticals (SAL + AEC)
  SM_SAL_MQL_SAL     — SAL MQL→SAL % (BDR acceptance rate)
  SM_AEC_MQL_SAL     — AEC MQL→SAL % (BDR acceptance rate)
  SM_SAL_MQL_SQL     — SAL MQL→SQL (marketing SQLs / SAL MQLs)
  SM_AEC_MQL_SQL     — AEC MQL→SQL (marketing SQLs / AEC MQLs)
  SM_SAL_SAL_SQL     — SAL SAL→SQL (marketing SQLs / SAL SALs)
  SM_AEC_SAL_SQL     — AEC SAL→SQL (marketing SQLs / AEC SALs)

SQL counts (by source bucket) are read from the DB (saved by process_hubspot_data.py).
"""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_db
from utils.kpi_calculator import calculate_variance
from scripts.fetch_hubspot_mqls import classify_industry, summarise


def load_sql_counts(db, quarter: str, year: int) -> dict:
    """Read SAL and AEC SQL counts (by source bucket) from DB."""
    kpis = db.get_latest_kpis(quarter, year)
    if kpis.empty:
        return {'sal': 0, 'aec': 0, 'sal_mkt': 0, 'aec_mkt': 0,
                'sal_sales': 0, 'aec_sales': 0, 'sal_csm': 0, 'aec_csm': 0}

    def _get(name):
        row = kpis[kpis['kpi_name'] == name]
        if row.empty:
            return 0
        try:
            return int(float(str(row.iloc[0]['actual_value']).replace('%', '').strip()))
        except (ValueError, TypeError):
            return 0

    return {
        'sal':        _get('SM_SAL_SQL_Volume'),       # marketing-attributed (current definition)
        'aec':        _get('SM_AEC_SQL_Volume'),
        'sal_total':  _get('SM_SAL_SQL_Total'),
        'aec_total':  _get('SM_AEC_SQL_Total'),
        'sal_sales':  _get('SM_SAL_SQL_SalesDriven'),
        'aec_sales':  _get('SM_AEC_SQL_SalesDriven'),
        'sal_csm':    _get('SM_SAL_SQL_CSMDriven'),
        'aec_csm':    _get('SM_AEC_SQL_CSMDriven'),
    }


def process_mqls(contacts: list, quarter: str, year: int):
    db      = get_db()
    today   = date.today()
    summary = summarise(contacts)
    sqls    = load_sql_counts(db, quarter, year)

    sal_mqls  = summary['sal']
    aec_mqls  = summary['aec']
    total_mql = summary['total']
    icp_pct   = summary['icp_pct']
    sal_sals  = summary['sal_sal']   # BDR-accepted SAL contacts
    aec_sals  = summary['aec_sal']

    sal_sql       = sqls['sal']        # marketing-attributed SQLs
    aec_sql       = sqls['aec']
    sal_sql_total = sqls.get('sal_total', sal_sql)
    aec_sql_total = sqls.get('aec_total', aec_sql)
    sal_sql_sales = sqls.get('sal_sales', 0)
    aec_sql_sales = sqls.get('aec_sales', 0)
    sal_sql_csm   = sqls.get('sal_csm', 0)
    aec_sql_csm   = sqls.get('aec_csm', 0)

    sal_mql_sal  = round(sal_sals / sal_mqls * 100, 1) if sal_mqls > 0 else 0
    aec_mql_sal  = round(aec_sals / aec_mqls * 100, 1) if aec_mqls > 0 else 0
    sal_sal_sql  = round(sal_sql / sal_sals * 100, 1)  if sal_sals > 0 else 0
    aec_sal_sql  = round(aec_sql / aec_sals * 100, 1)  if aec_sals > 0 else 0
    sal_conv     = round(sal_sql / sal_mqls * 100, 1)  if sal_mqls > 0 else 0
    aec_conv     = round(aec_sql / aec_mqls * 100, 1)  if aec_mqls > 0 else 0

    print(f"\n=== MQL METRICS {quarter} {year} ===")
    print(f"  SAL MQLs        : {sal_mqls}")
    print(f"  AEC MQLs        : {aec_mqls}")
    print(f"  Total MQLs      : {total_mql}")
    print(f"  ICP %           : {icp_pct}%")
    print(f"  SAL SALs (BDR)  : {sal_sals}  → MQL→SAL: {sal_mql_sal}%")
    print(f"  AEC SALs (BDR)  : {aec_sals}  → MQL→SAL: {aec_mql_sal}%")
    print(f"  SAL SQLs (mkt)  : {sal_sql}   → SAL→SQL: {sal_sal_sql}%  MQL→SQL: {sal_conv}%")
    print(f"  AEC SQLs (mkt)  : {aec_sql}   → SAL→SQL: {aec_sal_sql}%  MQL→SQL: {aec_conv}%")
    if sal_sql_total:
        print(f"  SAL SQL breakdown: Total={sal_sql_total} Mkt={sal_sql} Sales={sal_sql_sales} CSM={sal_sql_csm}")
    if aec_sql_total:
        print(f"  AEC SQL breakdown: Total={aec_sql_total} Mkt={aec_sql} Sales={aec_sql_sales} CSM={aec_sql_csm}")

    SM_TARGETS = {
        'SM_SAL_MQL_Volume': '180',
        'SM_AEC_MQL_Volume': '105',
        'SM_ICP_MQL_Share':  '90%',
        'SM_SAL_MQL_SAL':    '55%',
        'SM_AEC_MQL_SAL':    '40%',
        'SM_SAL_MQL_SQL':    '35%',
        'SM_AEC_MQL_SQL':    '35%',
        'SM_SAL_SAL_SQL':    '60%',
        'SM_AEC_SAL_SQL':    '60%',
    }

    kpi_entries = [
        {'kpi_name': 'SM_SAL_MQL_Volume', 'actual_value': str(sal_mqls),
         'target_value': SM_TARGETS['SM_SAL_MQL_Volume'],
         'comments': f"SAL ICP MQLs in {quarter} {year}"},
        {'kpi_name': 'SM_AEC_MQL_Volume', 'actual_value': str(aec_mqls),
         'target_value': SM_TARGETS['SM_AEC_MQL_Volume'],
         'comments': f"AEC ICP MQLs in {quarter} {year}"},
        {'kpi_name': 'SM_ICP_MQL_Share',  'actual_value': f"{icp_pct}%",
         'target_value': SM_TARGETS['SM_ICP_MQL_Share'],
         'comments': f"ICP MQLs: {sal_mqls + aec_mqls} / {total_mql}"},
        {'kpi_name': 'SM_SAL_MQL_SAL',    'actual_value': f"{sal_mql_sal}%",
         'target_value': SM_TARGETS['SM_SAL_MQL_SAL'],
         'comments': f"SAL: {sal_sals} accepted / {sal_mqls} MQLs"},
        {'kpi_name': 'SM_AEC_MQL_SAL',    'actual_value': f"{aec_mql_sal}%",
         'target_value': SM_TARGETS['SM_AEC_MQL_SAL'],
         'comments': f"AEC: {aec_sals} accepted / {aec_mqls} MQLs"},
        {'kpi_name': 'SM_SAL_MQL_SQL',    'actual_value': f"{sal_conv}%",
         'target_value': SM_TARGETS['SM_SAL_MQL_SQL'],
         'comments': f"SAL: {sal_sql} mkt SQLs / {sal_mqls} MQLs"},
        {'kpi_name': 'SM_AEC_MQL_SQL',    'actual_value': f"{aec_conv}%",
         'target_value': SM_TARGETS['SM_AEC_MQL_SQL'],
         'comments': f"AEC: {aec_sql} mkt SQLs / {aec_mqls} MQLs"},
        {'kpi_name': 'SM_SAL_SAL_SQL',    'actual_value': f"{sal_sal_sql}%",
         'target_value': SM_TARGETS['SM_SAL_SAL_SQL'],
         'comments': f"SAL: {sal_sql} mkt SQLs / {sal_sals} SALs"},
        {'kpi_name': 'SM_AEC_SAL_SQL',    'actual_value': f"{aec_sal_sql}%",
         'target_value': SM_TARGETS['SM_AEC_SAL_SQL'],
         'comments': f"AEC: {aec_sql} mkt SQLs / {aec_sals} SALs"},
    ]

    saved = skipped = 0
    for kpi in kpi_entries:
        variance_pct, status, _ = calculate_variance(kpi['actual_value'], kpi['target_value'])
        record = {**kpi, 'owner': 'S&M Initiative', 'cadence': 'Weekly',
                  'quarter': quarter, 'year': year, 'date': today,
                  'status': status, 'variance_pct': variance_pct,
                  'source': 'HubSpot', 'updated_by': 'MQL Sync'}
        try:
            result = db.save_kpi_if_changed(record)
            if result:
                saved += 1
                print(f"  ✓ {kpi['kpi_name']}: {kpi['actual_value']}")
            else:
                skipped += 1
                print(f"  — {kpi['kpi_name']}: unchanged")
        except Exception as e:
            print(f"  ✗ {kpi['kpi_name']}: {e}")

    print(f"\n✅ Saved {saved} MQL KPIs ({skipped} unchanged)")
    return saved


def main():
    if len(sys.argv) < 2:
        print("Usage: python process_hubspot_mqls.py <mqls.json> [quarter] [year]")
        sys.exit(1)

    mqls_file = sys.argv[1]
    quarter   = sys.argv[2] if len(sys.argv) > 2 else 'Q2'
    year      = int(sys.argv[3]) if len(sys.argv) > 3 else 2026

    with open(mqls_file) as f:
        contacts = json.load(f)

    print(f"Processing {len(contacts)} MQL contacts for {quarter} {year}...")
    process_mqls(contacts, quarter, year)


if __name__ == '__main__':
    main()
