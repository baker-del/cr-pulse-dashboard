"""
Import action items from ClearlyRated team Google Sheet (rows 4-31).

Run once to seed the database:
    python scripts/import_action_items.py

Safe to re-run — skips items whose description already exists.
"""

import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_db

# ---------------------------------------------------------------------------
# Raw action items from Google Sheet (action items tab, rows 4-31)
# Format: (description, due_date, status, owner, notes)
# Status mapping: Complete/Closed → Completed | WIP/WIP-late → In Progress | New → Not Started
# ---------------------------------------------------------------------------
ACTION_ITEMS = [
    ("Finalize customer account, CSM coverage",           date(2026, 2,  1),  "Completed",   "Eric",             ""),
    ("Finalize top risk accounts for 1H",                 date(2026, 2,  9),  "Completed",   "Eric",             ""),
    ("Finalize growth plans for leaders",                 date(2026, 2,  7),  "Not Started", "Baker",            ""),
    ("ROI Calculators",                                   date(2026, 2,  1),  "Completed",   "Hina",             ""),
    ("Demo accounts for Accounting/Staffing/Legal",       date(2026, 2,  5),  "In Progress", "Hina",             ""),
    ("MAP - Finish formulas",                             date(2026, 2,  6),  "In Progress", "Pete",             ""),
    ("Formalize KPI and bonus structure for Support",     date(2026, 2,  6),  "In Progress", "Joergen",          ""),
    ("Lead engagement workflow",                          date(2026, 2, 13),  "In Progress", "Pete/Shannon",     ""),
    ("Maturity Model",                                    date(2026, 2, 20),  "In Progress", "Pete/Colby",       ""),
    ("Accelerate product development",                    date(2026, 2,  7),  "In Progress", "Hina/Joergen",     "Late"),
    ("Cleanup Glassdoor reviews",                         date(2026, 2,  7),  "Completed",   "Andrew",           ""),
    ("Finalize and rollout CR pricing calculator",        date(2026, 2,  7),  "In Progress", "Andrew",           ""),
    ("Finalize CX Bootcamp prospect journey workflow",    date(2026, 2,  7),  "In Progress", "Stephen",          ""),
    ("Finalize rules of engagement for events",           date(2026, 2,  7),  "Not Started", "Stephen",          ""),
    ("Launch weekly podcast program",                     date(2026, 2, 26),  "Not Started", "Stephen",          ""),
    ("Dashboards for CSMs",                               date(2026, 2, 14),  "Not Started", "Joergen",          ""),
    ("Finalize Product AI plan for Q2/Q3",                date(2026, 2, 15),  "In Progress", "Hina",             ""),
    ("Specs for top 5 CSM items",                         date(2026, 2, 16),  "Not Started", "Hina",             ""),
    ("Cascade annual goals",                              date(2026, 2, 17),  "In Progress", "All",              ""),
    ("New improved product demo",                         date(2026, 2, 18),  "Not Started", "Hina",             ""),
    ("Finalize new onboarding process",                   date(2026, 2, 18),  "In Progress", "Eric",             ""),
    ("Finalize CS playbooks",                             date(2026, 2, 28),  "In Progress", "Eric",             ""),
    ("Finalize top expansion accounts for Q2+",           date(2026, 2, 28),  "Not Started", "Eric",             ""),
    ("Transition proposals in one tool",                  date(2026, 4,  1),  "In Progress", "Andrew/Jennette",  ""),
    ("Hiring plan for two devs in Hyderabad Dev Center",  date(2026, 4, 15),  "In Progress", "Joergen",          ""),
    ("Managers to ask new employees for reviews",         None,               "Not Started", "Managers",         "Glassdoor"),
]

# Best-fit KPI mapping for each action item
KPI_MAP = {
    "Finalize customer account, CSM coverage":          "NRR",
    "Finalize top risk accounts for 1H":                "High Risk Accounts (Next 6 Months)",
    "Finalize growth plans for leaders":                "Employee NPS",
    "ROI Calculators":                                  "Win Rate (Overall)",
    "Demo accounts for Accounting/Staffing/Legal":      "Win Rate (Overall)",
    "MAP - Finish formulas":                            "New Logo ARR",
    "Formalize KPI and bonus structure for Support":    "Employee NPS",
    "Lead engagement workflow":                         "SQL",
    "Maturity Model":                                   "Win Rate (Overall)",
    "Accelerate product development":                   "Core Product Adoption (Workflow Penetration)",
    "Cleanup Glassdoor reviews":                        "Employee NPS",
    "Finalize and rollout CR pricing calculator":       "Win Rate (Overall)",
    "Finalize CX Bootcamp prospect journey workflow":   "Total Surveys Sent",
    "Finalize rules of engagement for events":          "New Logo Pipeline Created",
    "Launch weekly podcast program":                    "New Logo Pipeline Created",
    "Dashboards for CSMs":                              "NRR",
    "Finalize Product AI plan for Q2/Q3":               "AI Coded %",
    "Specs for top 5 CSM items":                        "NRR",
    "Cascade annual goals":                             "Employee NPS",
    "New improved product demo":                        "Total Surveys Sent",
    "Finalize new onboarding process":                  "Logo Retention",
    "Finalize CS playbooks":                            "NRR",
    "Finalize top expansion accounts for Q2+":          "Expansion ARR",
    "Transition proposals in one tool":                 "Win Rate (Overall)",
    "Hiring plan for two devs in Hyderabad Dev Center": "AI Coded %",
    "Managers to ask new employees for reviews":        "Employee NPS",
}


def main():
    db = get_db()

    existing     = db.get_actions()
    existing_set = {a.action_description.lower().strip() for a in existing}

    inserted = 0
    skipped  = 0

    for desc, due, status, owner, notes in ACTION_ITEMS:
        if desc.lower().strip() in existing_set:
            skipped += 1
            continue

        completed_date = None
        if status == "Completed":
            completed_date = due or date(2026, 2, 15)

        db.save_action({
            'kpi_name':           KPI_MAP.get(desc, "Company Goals"),
            'action_description': desc,
            'owner':              owner,
            'status':             status,
            'due_date':           due,
            'created_date':       date(2026, 2, 1),
            'completed_date':     completed_date,
            'notes':              notes,
            'created_by':         'Import',
        })
        inserted += 1

    print(f"Done: {inserted} action items imported, {skipped} already existed.")


if __name__ == '__main__':
    main()
