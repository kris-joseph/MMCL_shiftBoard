# GitHub Actions Workflows

## refresh.yml

Automatically refreshes dashboard data from LibCal API every 30 minutes during operating hours.

### Schedule

**Toronto Time (EST/UTC-5):**
- First run: 07:45 (data ready before 08:00 opening)
- Regular runs: Every 30 minutes from 08:00-21:00
- Total: ~27 runs per day

**Cron expressions (UTC):**
- `45 12 * * *` - First run at 12:45 UTC (07:45 EST)
- `0,30 13-23 * * *` - Every 30 min from 13:00-23:30 UTC
- `0,30 0-1 * * *` - Every 30 min from 00:00-01:30 UTC
- `0 2 * * *` - Final run at 02:00 UTC (21:00 EST)

### What it does

1. Checks out the repository
2. Sets up Python 3.13
3. Installs dependencies from `requirements.txt`
4. Runs `scripts/fetch_data.py` to fetch LibCal data
5. (Phase 1 complete) Runs `scripts/generate_dashboard.py` to generate HTML
6. Commits changes to `docs/*/data.json` (and `docs/*/index.html` when ready)
7. Pushes to repository
8. GitHub Pages auto-deploys from `docs/` directory

### Required Secrets

Set these in **Settings → Secrets and variables → Actions**:

- `LIBCAL_CLIENT_ID` - LibCal OAuth client ID
- `LIBCAL_CLIENT_SECRET` - LibCal OAuth client secret

### Manual Triggering

You can manually trigger the workflow:

1. Go to **Actions** tab
2. Select "Refresh Dashboard Data"
3. Click **Run workflow**
4. Select branch (usually `main`)
5. Click **Run workflow**

### Debugging

View workflow runs under the **Actions** tab. Each run shows:
- Fetch output (number of bookings retrieved)
- Commit status (whether changes were committed)
- Deployment summary

If a run fails:
- Check the error in the failed step
- Verify secrets are correctly set
- Test locally: `python scripts/fetch_data.py`

### Future Enhancements (Phase 2)

When moving to Phase 2 (Docker deployment):
- This workflow will be replaced by a Flask app with 5-minute polling
- The cron schedule will no longer be needed
- Data will be stored in SQLite instead of JSON files
