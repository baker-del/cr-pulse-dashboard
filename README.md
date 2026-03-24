# KPI Dashboard - Setup & User Guide

A Streamlit web application for tracking company KPIs with auto-capture from HubSpot, manual entry, trend graphs, and action item tracking.

## 🎯 Features

- **Auto-capture KPIs from HubSpot** - New Logo ARR, Expansion ARR, SQLs, Pipeline, Win Rates
- **Manual KPI entry** - Employee NPS, Engineering metrics, Renewal Risk, etc.
- **Interactive trend graphs** - Visualize KPI progress over time
- **Action item tracking** - Manage actions for off-track KPIs
- **Multi-user access** - 4-10 users with simple authentication
- **Export data** - Download KPIs and actions as CSV

---

## 🚀 Quick Start (First Time Setup)

### Step 1: Install Python Dependencies

Open Terminal and navigate to the project directory:

```bash
cd "/Users/baker/Documents/AI Projects/KPI Dashboard"
```

Install required packages:

```bash
pip3 install -r requirements.txt
```

### Step 2: Initialize Database

Run the database initialization script:

```bash
python3 database/init_db.py
```

This will:
- Create the SQLite database
- Create tables (kpis, actions, targets)
- Load 2026 annual targets from CSV

You should see:
```
✅ Tables created successfully
✅ Loaded 30+ KPI targets for 2026
✅ Database initialization complete!
```

### Step 3: Run the Application

Start the Streamlit app:

```bash
streamlit run app.py
```

The app will open in your default browser at: `http://localhost:8501`

---

## 📱 How to Use the Dashboard

### **1. Dashboard Page (📊)**

**What it does:**
- Shows KPI summary cards for key metrics
- Displays interactive trend graphs
- Lists all KPIs in a sortable table

**How to use:**
1. Select a KPI from the dropdown to view its trend
2. Choose time period (last 4 weeks, 12 weeks, quarter, year)
3. Use filters to view specific KPIs by owner, status, or cadence
4. Export data to CSV for offline analysis

### **2. Manual Entry Page (✏️)**

**What it does:**
- Allows you to enter KPI values that aren't auto-captured from HubSpot

**How to use:**
1. Select the KPI you want to enter (e.g., Employee NPS, Renewal Risk)
2. Enter the actual value (can include $, %, commas)
3. Add optional comments for context
4. Click "Save Entry"
5. View recent entries below the form

**Manual Entry KPIs:**
- Employee NPS
- Renewal Risk
- Core Product Adoption
- CFT/CRS Monthly Active Users
- Total Surveys Sent
- Engineering metrics (SLA, incidents, etc.)
- Cash EBITDA

### **3. Action Items Page (✅)**

**What it does:**
- Tracks action items for KPIs that are off-track

**How to use:**
1. Click "+ Add New Action" to create an action item
2. Select the related KPI
3. Enter action description, owner, due date
4. Track status: Not Started → In Progress → Completed
5. Mark actions as complete when done
6. Filter by status, owner, or KPI

**Best Practice:**
- Create actions for any KPI below 70% of target
- Set realistic due dates (1-2 weeks)
- Update status weekly

### **4. Settings Page (⚙️)**

**What it does:**
- Database management
- HubSpot sync instructions
- Data export

**Key Functions:**
1. **Load Targets** - Initialize database with annual targets (one-time setup)
2. **HubSpot Sync** - Instructions for syncing data from HubSpot via Claude
3. **Export Data** - Download KPIs and actions as CSV

---

## 🔄 Syncing HubSpot Data

Since this is a local deployment, HubSpot data is synced through Claude:

### To Sync HubSpot KPIs:

1. Go to the **Settings** page in the app
2. Click "Request HubSpot Sync"
3. Ask Claude:

   **"Please sync HubSpot KPIs for Q1 2026 and save to the database"**

4. Claude will:
   - Fetch deal data from HubSpot using MCP tools
   - Calculate KPIs (New Logo ARR, Expansion ARR, SQLs, Pipeline, Win Rates)
   - Save results to the database

5. Refresh the Dashboard page to see updated data

### Auto-Captured KPIs:
- New Logo ARR (from Client Savvy & Sales pipelines)
- Expansion ARR (from Expansion pipeline)
- SQLs - Total, Inbound, Outbound
- New Logo Pipeline Created (Total, SAL, Accounting, AEC)
- Qualified Pipeline Coverage
- Win Rates (CFT/Project Based, CR/NPS Based)

---

## 👥 Multi-User Access (Local Network)

### For Your Team to Access the Dashboard:

#### Option 1: Same Computer Access
- Users on the same computer can access at: `http://localhost:8501`

#### Option 2: Local Network Access
1. Find your computer's IP address:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

2. Share this URL with your team:
   ```
   http://YOUR_IP_ADDRESS:8501
   ```
   (e.g., `http://192.168.1.100:8501`)

3. Team members must be on the same network (office WiFi or VPN)

**Important:**
- Your computer must be running for team access
- Keep the Terminal window open with Streamlit running
- If you restart, team needs to re-access the URL

---

## 📊 Typical Weekly Workflow

### Monday Morning:
1. **Review Dashboard** - Check all KPI statuses
2. **Sync HubSpot** - Get latest sales/pipeline data
3. **Update Action Items** - Mark completed actions, add new ones

### Mid-Week:
4. **Enter Manual KPIs** - Add weekly metrics (active users, response rates, etc.)

### End of Week/Month:
5. **Enter Monthly/Quarterly KPIs** - Employee NPS, Cash EBITDA
6. **Export Data** - Download CSV for leadership review
7. **Create Actions** - For any KPI <70% of target

---

## 🔧 Troubleshooting

### App won't start:
```bash
# Check if Python is installed
python3 --version

# Reinstall dependencies
pip3 install -r requirements.txt --upgrade

# Try running again
streamlit run app.py
```

### Database error:
```bash
# Reinitialize database
python3 database/init_db.py
```

### Port already in use:
```bash
# Use a different port
streamlit run app.py --server.port 8502
```

### Can't access from other computers:
- Check firewall settings
- Ensure port 8501 is allowed
- Confirm computers are on same network

---

## 📁 Project Structure

```
KPI Dashboard/
├── app.py                      # Main application entry point
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .streamlit/
│   └── config.toml            # Streamlit configuration (colors, theme)
├── database/
│   ├── db.py                  # Database models and functions
│   ├── init_db.py             # Database initialization script
│   └── kpi_dashboard.db       # SQLite database (created on first run)
├── pages/
│   ├── 1_📊_Dashboard.py      # Main dashboard with graphs
│   ├── 2_✏️_Manual_Entry.py   # Manual KPI entry form
│   ├── 3_✅_Action_Items.py   # Action tracking page
│   └── 4_⚙️_Settings.py       # Settings and sync
├── utils/
│   ├── charts.py              # Plotly chart generation
│   ├── colors.py              # Color palette and styling
│   └── kpi_calculator.py      # KPI calculations and variance
└── assets/
    └── annual_targets_2026.csv # 2026 quarterly targets
```

---

## 🔒 Security Notes

### Current Setup (Local Deployment):
- No authentication required (all users trusted)
- Database is local SQLite file
- Only accessible on local network

### Future Enhancements:
- Add user authentication (streamlit-authenticator)
- Role-based access (Admin vs Viewer)
- Cloud deployment with HTTPS
- Automated backups

---

## 📈 Future Enhancements

**Planned Features:**
- Email notifications for off-track KPIs
- Scheduled HubSpot sync (daily/weekly)
- PDF report generation
- Mobile-responsive design improvements
- Slack integration for weekly summaries
- Advanced analytics and forecasting

---

## 💾 Backup & Restore

### Backup Database:
```bash
cp database/kpi_dashboard.db database/kpi_dashboard_backup_$(date +%Y%m%d).db
```

### Restore from Backup:
```bash
cp database/kpi_dashboard_backup_YYYYMMDD.db database/kpi_dashboard.db
```

**Recommendation:** Backup weekly or before major changes.

---

## 📞 Support

For issues or questions:
1. Check this README
2. Review error messages in Terminal
3. Ask Claude for help with specific issues

---

## 🎉 You're Ready!

Start the app and begin tracking your KPIs:

```bash
streamlit run app.py
```

Then navigate to:
1. **Settings** → Load Targets
2. **Manual Entry** → Add some KPIs
3. **Dashboard** → View your data

Happy KPI tracking! 📊
