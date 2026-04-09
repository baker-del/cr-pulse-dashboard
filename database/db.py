"""
Database models and utility functions for KPI Dashboard

Uses SQLAlchemy ORM with support for both SQLite (local) and PostgreSQL (cloud)
"""

import os
from datetime import datetime, date
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Optional
import pandas as pd

Base = declarative_base()


# Database Models

class KPI(Base):
    """Stores all KPI data points (auto-captured + manual entry)"""
    __tablename__ = 'kpis'

    id = Column(Integer, primary_key=True, autoincrement=True)
    kpi_name = Column(String(100), nullable=False, index=True)
    owner = Column(String(50))
    cadence = Column(String(20))  # Weekly, Monthly, Quarterly
    quarter = Column(String(10))  # Q1, Q2, Q3, Q4
    year = Column(Integer)
    week_number = Column(Integer)  # For weekly tracking
    date = Column(Date, nullable=False)
    target_value = Column(String(50))  # String to handle percentages, dollar signs
    actual_value = Column(String(50))
    status = Column(String(20))  # On Track, At Risk, Behind
    variance_pct = Column(Float)
    source = Column(String(20))  # HubSpot, Manual, Engineering
    comments = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_by = Column(String(50))

    def to_dict(self):
        return {
            'id': self.id,
            'kpi_name': self.kpi_name,
            'owner': self.owner,
            'cadence': self.cadence,
            'quarter': self.quarter,
            'year': self.year,
            'week_number': self.week_number,
            'date': self.date.isoformat() if self.date else None,
            'target_value': self.target_value,
            'actual_value': self.actual_value,
            'status': self.status,
            'variance_pct': self.variance_pct,
            'source': self.source,
            'comments': self.comments,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_by': self.updated_by
        }


class Action(Base):
    """Tracks action items for KPIs that are off-track"""
    __tablename__ = 'actions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    kpi_name = Column(String(100), nullable=False, index=True)
    action_description = Column(Text, nullable=False)
    owner = Column(String(50))
    status = Column(String(20))  # Not Started, In Progress, Completed, Blocked
    due_date = Column(Date)
    created_date = Column(Date, default=date.today)
    completed_date = Column(Date)
    notes = Column(Text)
    created_by = Column(String(50))

    def to_dict(self):
        return {
            'id': self.id,
            'kpi_name': self.kpi_name,
            'action_description': self.action_description,
            'owner': self.owner,
            'status': self.status,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'notes': self.notes,
            'created_by': self.created_by
        }


class QuarterSnapshot(Base):
    """Locked quarter-end snapshots for historical tracking.

    Once a quarter is snapshotted, its KPI values are frozen here and
    the live KPI table will refuse further HubSpot-sync updates for
    that quarter/year combo.
    """
    __tablename__ = 'quarter_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    kpi_name = Column(String(100), nullable=False, index=True)
    owner = Column(String(50))
    quarter = Column(String(10), nullable=False)
    year = Column(Integer, nullable=False)
    target_value = Column(String(50))
    actual_value = Column(String(50))
    status = Column(String(20))
    variance_pct = Column(Float)
    source = Column(String(20))
    comments = Column(Text)
    snapshot_date = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'kpi_name': self.kpi_name,
            'owner': self.owner,
            'quarter': self.quarter,
            'year': self.year,
            'target_value': self.target_value,
            'actual_value': self.actual_value,
            'status': self.status,
            'variance_pct': self.variance_pct,
            'source': self.source,
            'comments': self.comments,
            'snapshot_date': self.snapshot_date.isoformat() if self.snapshot_date else None,
        }


class WeeklyCohort(Base):
    """Weekly funnel cohort rows for S&M Efficiency (SAL and AEC)."""
    __tablename__ = 'weekly_cohorts'

    id           = Column(Integer, primary_key=True, autoincrement=True)
    quarter      = Column(String(10), nullable=False, index=True)
    year         = Column(Integer,    nullable=False, index=True)
    vertical     = Column(String(10), nullable=False)   # SAL or AEC
    week_label   = Column(String(20), nullable=False)   # e.g. "Apr 1"
    week_start   = Column(Date,       nullable=False)
    total_mqls   = Column(Integer, default=0)
    icp_mqls     = Column(Integer, default=0)
    icp_pct      = Column(Float,   default=0)
    sal_n        = Column(Integer, default=0)   # BDR-accepted contacts
    mql_sal_pct  = Column(Float,   default=0)
    sql_mkt      = Column(Integer, default=0)
    sql_sales    = Column(Integer, default=0)
    sql_csm      = Column(Integer, default=0)
    sql_total    = Column(Integer, default=0)
    sal_sql_pct  = Column(Float,   default=0)
    pipeline     = Column(Float,   default=0)
    cum_mqls     = Column(Integer, default=0)
    cum_sals     = Column(Integer, default=0)
    cum_sqls_mkt = Column(Integer, default=0)
    cum_mql_sal  = Column(Float,   default=0)
    cum_sal_sql  = Column(Float,   default=0)
    cum_mql_sql  = Column(Float,   default=0)
    lead_sources = Column(Text,    default='')
    updated_at   = Column(DateTime, default=datetime.now)


class Target(Base):
    """Stores quarterly targets (loaded from CSV)"""
    __tablename__ = 'targets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    kpi_name = Column(String(100), nullable=False, unique=True, index=True)
    owner = Column(String(50))
    year = Column(Integer)
    q1_target = Column(String(50))
    q2_target = Column(String(50))
    q3_target = Column(String(50))
    q4_target = Column(String(50))
    annual_target = Column(String(50))

    def to_dict(self):
        return {
            'id': self.id,
            'kpi_name': self.kpi_name,
            'owner': self.owner,
            'year': self.year,
            'q1_target': self.q1_target,
            'q2_target': self.q2_target,
            'q3_target': self.q3_target,
            'q4_target': self.q4_target,
            'annual_target': self.annual_target
        }


# Database Connection

class Database:
    """Database connection and utility functions"""

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize database connection

        Args:
            db_url: Database URL. If None, uses SQLite in database/ directory
        """
        if db_url is None:
            # Default to SQLite in project directory
            db_path = os.path.join(os.path.dirname(__file__), 'kpi_dashboard.db')
            db_url = f'sqlite:///{db_path}'

        self.engine = create_engine(db_url, echo=False, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False,
                                         expire_on_commit=True, bind=self.engine)

    def create_tables(self):
        """Create all tables if they don't exist"""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()

    # KPI Functions

    def get_kpis(self, quarter: str = None, year: int = None, kpi_name: str = None) -> List[KPI]:
        """
        Fetch KPIs with optional filters

        Args:
            quarter: Filter by quarter (Q1, Q2, Q3, Q4)
            year: Filter by year
            kpi_name: Filter by KPI name

        Returns:
            List of KPI objects
        """
        session = self.get_session()
        try:
            query = session.query(KPI)

            if quarter:
                query = query.filter(KPI.quarter == quarter)
            if year:
                query = query.filter(KPI.year == year)
            if kpi_name:
                query = query.filter(KPI.kpi_name == kpi_name)

            query = query.order_by(KPI.date.desc())
            return query.all()
        finally:
            session.close()

    def save_kpi_if_changed(self, kpi_data: Dict) -> Optional[KPI]:
        """Save KPI only when actual_value is present and differs from the latest stored value.

        Returns the saved KPI record, or None if skipped (no data / unchanged).
        This preserves the original 'date' (Last Updated) when no new data exists.
        """
        # Refuse updates to locked (snapshotted) quarters
        q = kpi_data.get('quarter')
        y = kpi_data.get('year')
        if q and y and self.is_quarter_locked(q, y):
            return None

        actual = str(kpi_data.get('actual_value', '') or '').strip()

        # Skip if no actual value
        if not actual or actual in ('None', 'nan'):
            return None

        # Compare against the latest stored value for this KPI/quarter/year
        session = self.get_session()
        try:
            latest = session.query(KPI).filter(
                KPI.kpi_name == kpi_data['kpi_name'],
                KPI.quarter  == kpi_data.get('quarter'),
                KPI.year     == kpi_data.get('year'),
            ).order_by(KPI.date.desc(), KPI.id.desc()).first()

            target = str(kpi_data.get('target_value', '') or '').strip()
            if latest and str(latest.actual_value or '').strip() == actual \
                    and str(latest.target_value or '').strip() == target:
                return None  # Value unchanged — leave existing record and date intact
        finally:
            session.close()

        return self.save_kpi(kpi_data)

    def save_kpi(self, kpi_data: Dict) -> KPI:
        """
        Save or update a KPI value

        Args:
            kpi_data: Dictionary with KPI fields

        Returns:
            Saved KPI object
        """
        session = self.get_session()
        try:
            kpi = KPI(**kpi_data)
            session.add(kpi)
            session.commit()
            session.refresh(kpi)
            return kpi
        finally:
            session.close()

    def get_kpi_trends(self, kpi_name: str, weeks: int = 12) -> pd.DataFrame:
        """
        Get time series data for a KPI

        Args:
            kpi_name: Name of the KPI
            weeks: Number of weeks of history

        Returns:
            DataFrame with date, actual_value, target_value
        """
        session = self.get_session()
        try:
            query = session.query(KPI).filter(
                KPI.kpi_name == kpi_name
            ).order_by(KPI.date.desc()).limit(weeks * 7)  # Approximate

            kpis = query.all()

            data = []
            for kpi in kpis:
                data.append({
                    'date': kpi.date,
                    'actual_value': kpi.actual_value,
                    'target_value': kpi.target_value,
                    'variance_pct': kpi.variance_pct
                })

            return pd.DataFrame(data)
        finally:
            session.close()

    def get_latest_kpis_all_periods(self) -> pd.DataFrame:
        """Get the most recent entry for each KPI across all quarters/years."""
        session = self.get_session()
        try:
            kpis = session.query(KPI).order_by(KPI.date.desc()).all()
            kpi_dict: dict = {}
            for kpi in kpis:
                if kpi.kpi_name not in kpi_dict:
                    kpi_dict[kpi.kpi_name] = kpi
            data = [kpi.to_dict() for kpi in kpi_dict.values()]
            return pd.DataFrame(data) if data else pd.DataFrame()
        finally:
            session.close()

    def get_latest_kpis(self, quarter: str, year: int) -> pd.DataFrame:
        """
        Get the latest value for each KPI in a quarter

        Args:
            quarter: Quarter (Q1, Q2, Q3, Q4)
            year: Year

        Returns:
            DataFrame with latest KPI values
        """
        session = self.get_session()
        try:
            # Get all KPIs for the quarter
            kpis = session.query(KPI).filter(
                KPI.quarter == quarter,
                KPI.year == year
            ).all()

            # Group by kpi_name and get latest (by date, then by id as tiebreaker)
            kpi_dict = {}
            for kpi in kpis:
                existing = kpi_dict.get(kpi.kpi_name)
                if existing is None:
                    kpi_dict[kpi.kpi_name] = kpi
                elif kpi.date > existing.date:
                    kpi_dict[kpi.kpi_name] = kpi
                elif kpi.date == existing.date and kpi.id > existing.id:
                    kpi_dict[kpi.kpi_name] = kpi

            # Convert to DataFrame
            data = [kpi.to_dict() for kpi in kpi_dict.values()]
            return pd.DataFrame(data)
        finally:
            session.close()

    # Action Functions

    def get_actions(self, status: str = None, kpi_name: str = None) -> List[Action]:
        """
        Fetch action items with optional filters

        Args:
            status: Filter by status (Not Started, In Progress, Completed, Blocked)
            kpi_name: Filter by KPI name

        Returns:
            List of Action objects
        """
        session = self.get_session()
        try:
            query = session.query(Action)

            if status:
                query = query.filter(Action.status == status)
            if kpi_name:
                query = query.filter(Action.kpi_name == kpi_name)

            query = query.order_by(Action.due_date.asc())
            return query.all()
        finally:
            session.close()

    def save_action(self, action_data: Dict) -> Action:
        """
        Save or update an action item

        Args:
            action_data: Dictionary with action fields

        Returns:
            Saved Action object
        """
        session = self.get_session()
        try:
            if 'id' in action_data and action_data['id']:
                # Update existing action
                action = session.query(Action).filter(Action.id == action_data['id']).first()
                if action:
                    for key, value in action_data.items():
                        if key != 'id' and value is not None:
                            setattr(action, key, value)
            else:
                # Create new action
                action = Action(**action_data)
                session.add(action)

            session.commit()
            session.refresh(action)
            return action
        finally:
            session.close()

    def delete_action(self, action_id: int):
        """Delete an action item"""
        session = self.get_session()
        try:
            action = session.query(Action).filter(Action.id == action_id).first()
            if action:
                session.delete(action)
                session.commit()
        finally:
            session.close()

    # Target Functions

    def get_targets(self, year: int = 2026) -> List[Target]:
        """
        Get all targets for a year

        Args:
            year: Year (default: 2026)

        Returns:
            List of Target objects
        """
        session = self.get_session()
        try:
            return session.query(Target).filter(Target.year == year).all()
        finally:
            session.close()

    def get_target(self, kpi_name: str, year: int = 2026) -> Optional[Target]:
        """
        Get target for a specific KPI

        Args:
            kpi_name: Name of the KPI
            year: Year (default: 2026)

        Returns:
            Target object or None
        """
        session = self.get_session()
        try:
            return session.query(Target).filter(
                Target.kpi_name == kpi_name,
                Target.year == year
            ).first()
        finally:
            session.close()

    def save_target(self, target_data: Dict) -> Target:
        """
        Save or update a target

        Args:
            target_data: Dictionary with target fields

        Returns:
            Saved Target object
        """
        session = self.get_session()
        try:
            # Check if target exists
            existing = session.query(Target).filter(
                Target.kpi_name == target_data['kpi_name'],
                Target.year == target_data.get('year', 2026)
            ).first()

            if existing:
                # Update existing
                for key, value in target_data.items():
                    if value is not None:
                        setattr(existing, key, value)
                target = existing
            else:
                # Create new
                target = Target(**target_data)
                session.add(target)

            session.commit()
            session.refresh(target)
            return target
        finally:
            session.close()

    # Quarter Snapshot / Locking Functions

    def is_quarter_locked(self, quarter: str, year: int) -> bool:
        """Check if a quarter has been snapshotted (locked)."""
        session = self.get_session()
        try:
            count = session.query(QuarterSnapshot).filter(
                QuarterSnapshot.quarter == quarter,
                QuarterSnapshot.year == year,
            ).count()
            return count > 0
        finally:
            session.close()

    def snapshot_quarter(self, quarter: str, year: int) -> int:
        """Copy all current KPI records for a quarter into quarter_snapshots.

        Returns the number of KPI rows snapshotted.
        Raises ValueError if the quarter is already locked.
        """
        if self.is_quarter_locked(quarter, year):
            raise ValueError(f"{quarter} {year} is already snapshotted/locked.")

        # Get the latest value for each KPI in this quarter
        latest_df = self.get_latest_kpis(quarter, year)
        if latest_df.empty:
            raise ValueError(f"No KPI data found for {quarter} {year}.")

        session = self.get_session()
        try:
            count = 0
            for _, row in latest_df.iterrows():
                snap = QuarterSnapshot(
                    kpi_name=row['kpi_name'],
                    owner=row.get('owner'),
                    quarter=quarter,
                    year=year,
                    target_value=row.get('target_value'),
                    actual_value=row.get('actual_value'),
                    status=row.get('status'),
                    variance_pct=row.get('variance_pct'),
                    source=row.get('source'),
                    comments=row.get('comments'),
                )
                session.add(snap)
                count += 1
            session.commit()
            return count
        finally:
            session.close()

    def get_quarter_snapshot(self, quarter: str, year: int) -> pd.DataFrame:
        """Retrieve the locked snapshot for a quarter."""
        session = self.get_session()
        try:
            snaps = session.query(QuarterSnapshot).filter(
                QuarterSnapshot.quarter == quarter,
                QuarterSnapshot.year == year,
            ).all()
            data = [s.to_dict() for s in snaps]
            return pd.DataFrame(data) if data else pd.DataFrame()
        finally:
            session.close()

    def load_targets_from_csv(self, csv_path: str, year: int = 2026):
        """
        Load targets from CSV file into database

        Args:
            csv_path: Path to CSV file
            year: Year for these targets
        """
        df = pd.read_csv(csv_path)

        for _, row in df.iterrows():
            target_data = {
                'kpi_name': row['KPI'],
                'owner': row.get('Owner', ''),
                'year': year,
                'q1_target': row.get('Q1', ''),
                'q2_target': row.get('Q2', ''),
                'q3_target': row.get('Q3', ''),
                'q4_target': row.get('Q4', ''),
                'annual_target': row.get('2026_Target', '')
            }
            self.save_target(target_data)


    # ── Weekly cohort methods ─────────────────────────────────────────────────

    def save_weekly_cohorts(self, rows: list, quarter: str, year: int, vertical: str):
        """
        Upsert weekly cohort rows for a quarter/year/vertical.
        Deletes existing rows for that combo, then inserts fresh ones.
        """
        session = self.get_session()
        try:
            session.query(WeeklyCohort).filter_by(
                quarter=quarter, year=year, vertical=vertical
            ).delete()
            for r in rows:
                session.add(WeeklyCohort(
                    quarter      = quarter,
                    year         = year,
                    vertical     = vertical,
                    week_label   = r['week_label'],
                    week_start   = r['week_start'].date() if hasattr(r['week_start'], 'date') else r['week_start'],
                    total_mqls   = r.get('total_mqls',   0),
                    icp_mqls     = r.get('icp_mqls',     0),
                    icp_pct      = r.get('icp_pct',      0),
                    sal_n        = r.get('sal_n',         0),
                    mql_sal_pct  = r.get('mql_sal_pct',  0),
                    sql_mkt      = r.get('sql_mkt',      0),
                    sql_sales    = r.get('sql_sales',    0),
                    sql_csm      = r.get('sql_csm',      0),
                    sql_total    = r.get('sql_total',    0),
                    sal_sql_pct  = r.get('sal_sql_pct',  0),
                    pipeline     = r.get('pipeline',     0),
                    cum_mqls     = r.get('cum_mqls',     0),
                    cum_sals     = r.get('cum_sals',     0),
                    cum_sqls_mkt = r.get('cum_sqls_mkt', 0),
                    cum_mql_sal  = r.get('cum_mql_sal',  0),
                    cum_sal_sql  = r.get('cum_sal_sql',  0),
                    cum_mql_sql  = r.get('cum_mql_sql',  0),
                    lead_sources = r.get('lead_sources', ''),
                    updated_at   = datetime.now(),
                ))
            session.commit()
        finally:
            session.close()

    def get_weekly_cohorts(self, quarter: str, year: int) -> dict:
        """
        Returns {'sal': [...], 'aec': [...], 'file_date': str} from DB,
        matching the same structure as load_weekly_cohorts() in the page.
        Returns None if no data found.
        """
        session = self.get_session()
        try:
            rows = session.query(WeeklyCohort).filter_by(
                quarter=quarter, year=year
            ).order_by(WeeklyCohort.vertical, WeeklyCohort.week_start).all()
        finally:
            session.close()

        if not rows:
            return None

        def _to_dict(r):
            return {
                'week_start':    r.week_start,
                'week_label':    r.week_label,
                'lead_sources':  r.lead_sources or '—',
                'total_mqls':    r.total_mqls,
                'icp_mqls':      r.icp_mqls,
                'icp_pct':       r.icp_pct,
                'sal_n':         r.sal_n,
                'mql_sal_pct':   r.mql_sal_pct,
                'sql_mkt':       r.sql_mkt,
                'sql_sales':     r.sql_sales,
                'sql_csm':       r.sql_csm,
                'sql_total':     r.sql_total,
                'sal_sql_pct':   r.sal_sql_pct,
                'pipeline':      r.pipeline,
                'cum_mqls':      r.cum_mqls,
                'cum_sals':      r.cum_sals,
                'cum_sqls_mkt':  r.cum_sqls_mkt,
                'cum_mql_sal':   r.cum_mql_sal,
                'cum_sal_sql':   r.cum_sal_sql,
                'cum_mql_sql':   r.cum_mql_sql,
            }

        sal = [_to_dict(r) for r in rows if r.vertical == 'SAL']
        aec = [_to_dict(r) for r in rows if r.vertical == 'AEC']

        latest = max(rows, key=lambda r: r.updated_at)
        file_date = latest.updated_at.strftime('%b %-d, %Y %-I:%M %p')
        return {'sal': sal, 'aec': aec, 'file_date': file_date}


# Global database instance
_db_instance = None


def get_db() -> Database:
    """Get global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
