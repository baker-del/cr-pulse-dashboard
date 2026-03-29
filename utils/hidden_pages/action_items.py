"""
Action Items — Table list (default) and Kanban board tracker
"""

import pandas as pd
import streamlit as st
from datetime import date, timedelta
from database.db import get_db


STATUSES    = ["Not Started", "In Progress", "Stalled", "Behind", "Completed"]
NEXT_STATUS = {
    "Not Started": "In Progress",
    "In Progress": "Completed",
    "Stalled":     "In Progress",
    "Behind":      "In Progress",
    "Completed":   None,
}
LANE_STYLE = {
    "Not Started": ("⏸️", "#9B9B9B"),
    "In Progress":  ("🔄", "#0F7D64"),
    "Stalled":      ("⚠️", "#f5a623"),
    "Behind":       ("🔴", "#E75944"),
    "Completed":    ("✅", "#4CAF50"),
}

# ── Team member roster ───────────────────────────────────────────────────────────
TEAM_MEMBERS = [
    "Andrew Sabin",
    "Baker Nanduru",
    "Hina Vinocha",
    "Eric Gregg",
    "Ryan Suydam",
    "Joergen Larsen",
    "Pete Cowing",
    "Stephen Banbury",
    "All Leads",
]

st.markdown("""
<style>
.kanban-card {
    background: #fff;
    border-radius: 6px;
    padding: 10px 12px 8px 14px;
    margin-bottom: 8px;
    border-left: 4px solid #ccc;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07);
}
.card-overdue { border-left-color: #E75944 !important; }
.card-soon    { border-left-color: #f5a623 !important; }
.card-ok      { border-left-color: #0F7D64 !important; }
.card-nodate  { border-left-color: #ccc !important; }
.card-done    { border-left-color: #4CAF50 !important; opacity: 0.75; }
.card-title   { font-weight: 600; font-size: 0.88rem; line-height: 1.35; }
.card-meta    { font-size: 0.76rem; color: #777; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

db      = get_db()
quarter = st.session_state.get('current_quarter', 'Q1')
year    = st.session_state.get('current_year', 2026)


def _parse_owners(owner_str: str) -> list[str]:
    """Split a comma-separated owner string into a list of names."""
    if not owner_str:
        return []
    return [o.strip() for o in owner_str.split(',') if o.strip()]


def _owners_for_display(owner_str: str) -> list[str]:
    """Return selected owners preloaded for the multi-select widget."""
    names = _parse_owners(owner_str)
    # Accept names from team list OR legacy short names
    valid = [n for n in names if n in TEAM_MEMBERS]
    return valid if valid else []


# ── Add / Edit form ─────────────────────────────────────────────────────────────
def show_form(existing=None):
    is_edit   = existing is not None
    title_str = "✏️ Edit Action" if is_edit else "＋ New Action Item"

    with st.form(key="action_form", clear_on_submit=False):
        st.subheader(title_str)

        desc = st.text_area(
            "Action Description *",
            value=existing.action_description if is_edit else "",
            height=90,
            placeholder="Describe what needs to be done…",
        )

        c1, c2 = st.columns(2)
        with c1:
            default_owners = _owners_for_display(existing.owner if is_edit else "")
            sel_owners = st.multiselect(
                "Owner(s)",
                options=TEAM_MEMBERS,
                default=default_owners,
                placeholder="Select team member(s)…",
            )

        with c2:
            cur_status = existing.status if is_edit else "Not Started"
            status_idx = STATUSES.index(cur_status) if cur_status in STATUSES else 0
            sel_status = st.selectbox("Status", STATUSES, index=status_idx)

            due_default = (
                existing.due_date if (is_edit and existing.due_date)
                else date.today() + timedelta(days=14)
            )
            due = st.date_input("Due Date", value=due_default)

        notes = st.text_area(
            "Notes (optional)",
            value=existing.notes if is_edit else "",
            height=70,
            placeholder="Additional context, links, blockers…",
        )

        sc1, sc2, sc3 = st.columns([1, 1, 4])
        with sc1:
            save   = st.form_submit_button("💾 Save", type="primary")
        with sc2:
            cancel = st.form_submit_button("Cancel")
        with sc3:
            delete = st.form_submit_button("🗑️ Delete") if is_edit else False

        if save:
            if not desc.strip():
                st.error("Please enter a description.")
            else:
                owner_str = ", ".join(sel_owners)
                payload = {
                    'kpi_name':           "Company Goals",
                    'action_description': desc.strip(),
                    'owner':              owner_str,
                    'status':             sel_status,
                    'due_date':           due,
                    'notes':              notes.strip(),
                }
                if is_edit:
                    payload['id'] = existing.id
                    if sel_status == 'Completed' and existing.status != 'Completed':
                        payload['completed_date'] = date.today()
                else:
                    payload['created_by'] = 'Dashboard'
                try:
                    db.save_action(payload)
                    st.session_state.show_action_form  = False
                    st.session_state.editing_action_id = None
                    st.toast("✅ Action saved!", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")

        if delete and is_edit:
            db.delete_action(existing.id)
            st.session_state.show_action_form  = False
            st.session_state.editing_action_id = None
            st.rerun()

        if cancel:
            st.session_state.show_action_form  = False
            st.session_state.editing_action_id = None
            st.rerun()


# ── Card helpers ────────────────────────────────────────────────────────────────
def due_info(action):
    if not action.due_date:
        return "card-nodate", "No date"
    days = (action.due_date - date.today()).days
    if action.status == "Completed":
        return "card-done", "✅ Done"
    if days < 0:
        return "card-overdue", f"🔴 {abs(days)}d overdue"
    if days <= 3:
        return "card-soon", f"🟡 Due {action.due_date.strftime('%-m/%-d')}"
    return "card-ok", f"📅 {action.due_date.strftime('%-m/%-d')}"


def render_card(action, lane_key: str):
    css, due_lbl = due_info(action)
    desc = action.action_description
    if len(desc) > 75:
        desc = desc[:72] + "…"

    notes_snip = (
        f"<div class='card-meta' style='margin-top:4px;font-style:italic'>{action.notes[:55]}…</div>"
        if action.notes else ""
    )

    st.markdown(f"""
    <div class="kanban-card {css}">
      <div class="card-title">{desc}</div>
      <div class="card-meta">👤 {action.owner or '—'} &nbsp;·&nbsp; {due_lbl}</div>
      {notes_snip}
    </div>
    """, unsafe_allow_html=True)

    bc1, bc2 = st.columns(2)
    with bc1:
        nxt = NEXT_STATUS.get(action.status)
        if nxt:
            lbl = "✅ Done" if nxt == "Completed" else f"▶ {nxt.split()[0]}"
            if st.button(lbl, key=f"nxt_{action.id}_{lane_key}", use_container_width=True):
                upd = {'id': action.id, 'status': nxt}
                if nxt == 'Completed':
                    upd['completed_date'] = date.today()
                db.save_action(upd)
                st.rerun()
    with bc2:
        if st.button("✏️", key=f"edt_{action.id}_{lane_key}",
                     use_container_width=True, help="Edit"):
            st.session_state.editing_action_id = action.id
            st.session_state.show_action_form  = True
            st.rerun()


# ── Page header ─────────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([7, 1])
with hc1:
    st.title("✅ Action Items")
with hc2:
    st.write("")
    if st.button("＋ Add", use_container_width=True, type="primary"):
        st.session_state.show_action_form  = True
        st.session_state.editing_action_id = None

st.markdown("---")

# ── Show form if requested ──────────────────────────────────────────────────────
if st.session_state.get('show_action_form', False):
    edit_id  = st.session_state.get('editing_action_id')
    existing = None
    if edit_id:
        existing = next((a for a in db.get_actions() if a.id == edit_id), None)
    show_form(existing)
    st.markdown("---")

# ── Filters ─────────────────────────────────────────────────────────────────────
all_actions = db.get_actions()

st.markdown("""
<style>
/* Cap multiselect tag area so it never grows more than ~2 rows tall */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div:first-child {
    max-height: 60px;
    overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)

fc1, fc2, fc3, fc4 = st.columns([2, 2, 1, 1])

with fc1:
    filter_owner = st.multiselect("Owner", TEAM_MEMBERS, placeholder="All owners")
with fc2:
    filter_status = st.multiselect("Status", STATUSES, placeholder="All statuses")
with fc3:
    show_done = st.checkbox("Show Completed", value=False)
with fc4:
    view = st.radio(
        "", ["📊 List", "📋 Board"], horizontal=True,
        key="action_view", label_visibility="collapsed",
        index=0,
    )

# Apply filters
acts = list(all_actions)
if filter_owner:
    # Match if any selected owner appears in the action's owner string
    acts = [a for a in acts if any(o in (a.owner or '') for o in filter_owner)]
if filter_status:
    acts = [a for a in acts if a.status in filter_status]
if not show_done:
    acts = [a for a in acts if a.status != 'Completed']

st.markdown("---")

# Organize by status, sorted by due date
by_status = {
    s: sorted(
        [a for a in acts if a.status == s],
        key=lambda x: (x.due_date or date(2099, 1, 1))
    )
    for s in STATUSES
}

active_statuses = STATUSES if show_done else [s for s in STATUSES if s != "Completed"]


# ── LIST VIEW (TABLE) ────────────────────────────────────────────────────────────
if view == "📊 List":
    if not acts:
        st.info("No action items. Click ＋ Add to create one.")
    else:
        rows = []
        for a in acts:
            if a.status == "Completed":
                urgency = "✅"
            elif a.due_date and (a.due_date - date.today()).days < 0:
                urgency = "🔴"
            elif a.due_date and (a.due_date - date.today()).days <= 3:
                urgency = "🟡"
            elif a.status in ("Stalled", "Behind"):
                urgency = "⚠️"
            else:
                urgency = "🟢"
            rows.append({
                '_id':    a.id,
                '':       urgency,
                'Action': a.action_description,
                'Owner':  a.owner or "",
                'Due':    a.due_date if a.due_date else None,
                'Status': a.status,
                'Notes':  a.notes or "",
            })

        tbl_df  = pd.DataFrame(rows)
        orig_df = tbl_df.copy()

        edited = st.data_editor(
            tbl_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                '_id':    None,
                '':       st.column_config.TextColumn('', width='small', disabled=True),
                'Action': st.column_config.TextColumn('Action', width='large', disabled=True),
                'Owner':  st.column_config.SelectboxColumn(
                    'Owner', width='medium',
                    options=TEAM_MEMBERS + [""],
                ),
                'Due':    st.column_config.DateColumn('Due', width='small', format='MMM D'),
                'Status': st.column_config.SelectboxColumn(
                    'Status', options=STATUSES, width='medium'
                ),
                'Notes':  st.column_config.TextColumn('Notes', width='large'),
            },
            num_rows='fixed',
            key='action_table',
        )

        # ── Auto-save: compare returned DataFrame vs original ───────────────────
        # (More reliable than edited_rows for SelectboxColumn changes)
        saved = 0
        for i in range(len(orig_df)):
            orig_row = orig_df.iloc[i]
            edit_row = edited.iloc[i]

            owner_changed  = str(edit_row['Owner']  or '') != str(orig_row['Owner']  or '')
            status_changed = str(edit_row['Status'] or '') != str(orig_row['Status'] or '')
            notes_changed  = str(edit_row['Notes']  or '') != str(orig_row['Notes']  or '')
            # Date comparison: treat None/NaT as equal
            def _d(v): return str(v) if v is not None and str(v) != 'NaT' else ''
            due_changed = _d(edit_row['Due']) != _d(orig_row['Due'])

            if not (owner_changed or status_changed or notes_changed or due_changed):
                continue

            action_id = int(orig_row['_id'])
            upd = {'id': action_id}
            if owner_changed:
                upd['owner'] = str(edit_row['Owner'] or '')
            if status_changed:
                upd['status'] = edit_row['Status']
                if edit_row['Status'] == 'Completed' and orig_row['Status'] != 'Completed':
                    upd['completed_date'] = date.today()
            if notes_changed:
                upd['notes'] = str(edit_row['Notes'] or '')
            if due_changed:
                upd['due_date'] = edit_row['Due'] if _d(edit_row['Due']) else None
            db.save_action(upd)
            saved += 1

        if saved:
            if 'action_table' in st.session_state:
                del st.session_state['action_table']
            st.toast("✅ Saved", icon="✅")
            st.rerun()

        _, cedit = st.columns([1, 6])
        with cedit:
            edit_opts = {f"{a.action_description[:55]}…" if len(a.action_description) > 55
                         else a.action_description: a.id
                         for a in acts}
            if edit_opts:
                sel_desc = st.selectbox(
                    "Full edit / delete:", list(edit_opts.keys()),
                    label_visibility="visible", key="tbl_edit_sel"
                )
                if st.button("✏️ Open Editor", key="tbl_open_edit"):
                    st.session_state.editing_action_id = edit_opts[sel_desc]
                    st.session_state.show_action_form  = True
                    st.rerun()


# ── BOARD VIEW ──────────────────────────────────────────────────────────────────
else:
    cols = st.columns(len(active_statuses))
    for col, status in zip(cols, active_statuses):
        emoji, color = LANE_STYLE[status]
        lane_acts    = by_status.get(status, [])
        with col:
            st.markdown(
                f"<div style='text-align:center;font-weight:700;font-size:0.95rem;"
                f"border-bottom:2px solid {color};padding-bottom:8px;margin-bottom:12px;'>"
                f"{emoji} {status} "
                f"<span style='color:#999;font-weight:normal;font-size:0.8rem;'>({len(lane_acts)})</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if not lane_acts:
                st.markdown(
                    "<div style='color:#bbb;font-size:0.82rem;text-align:center;padding:20px 0;'>Empty</div>",
                    unsafe_allow_html=True,
                )
            else:
                for action in lane_acts:
                    render_card(action, status[:2].lower())


st.markdown("---")

# ── Summary stats ────────────────────────────────────────────────────────────────
sc1, sc2, sc3, sc4, sc5 = st.columns(5)
with sc1:
    active = sum(1 for a in all_actions if a.status not in ('Completed',))
    st.metric("Active", active)
with sc2:
    overdue = sum(
        1 for a in all_actions
        if a.status not in ('Completed',) and a.due_date and a.due_date < date.today()
    )
    st.metric("Overdue", overdue)
with sc3:
    ip = sum(1 for a in all_actions if a.status == 'In Progress')
    st.metric("In Progress", ip)
with sc4:
    stalled = sum(1 for a in all_actions if a.status in ('Stalled', 'Behind'))
    st.metric("Stalled / Behind", stalled)
with sc5:
    done = sum(1 for a in all_actions if a.status == 'Completed')
    st.metric("Completed", done)
