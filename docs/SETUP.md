# MMCL Dashboard Setup Guide

This guide covers setting up the MMCL Dashboard system on GitHub.

## Prerequisites

- GitHub repository created and initialized
- LibCal API credentials (Client ID and Client Secret)
- GitHub repository admin access

## Step 1: Configure GitHub Secrets

The GitHub Actions workflow requires LibCal API credentials to be stored as repository secrets.

1. Navigate to your repository on GitHub
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

   **Secret 1:**
   - Name: `LIBCAL_CLIENT_ID`
   - Value: `320` (your LibCal client ID)

   **Secret 2:**
   - Name: `LIBCAL_CLIENT_SECRET`
   - Value: `5c6908a560dd43f065fff001817630dc` (your LibCal client secret)

5. Click **Add secret** for each

## Step 2: Enable GitHub Pages

Configure GitHub Pages to serve the dashboards from the `docs/` directory.

1. Go to **Settings** → **Pages**
2. Under **Source**, select:
   - **Deploy from a branch**
3. Under **Branch**, select:
   - Branch: `main` (or `master`)
   - Folder: `/docs`
4. Click **Save**

GitHub Pages will deploy automatically whenever the `docs/` directory is updated by the GitHub Actions workflow.

## Step 3: Verify Workflow

1. Go to **Actions** tab in your repository
2. You should see the "Refresh Dashboard Data" workflow
3. Click **Run workflow** to trigger a manual run (optional)
4. Check the workflow run to ensure it completes successfully

## Step 4: Verify Deployment

After the first successful workflow run:

1. Check that `docs/*/data.json` files have been created and committed
2. Wait a few minutes for GitHub Pages to deploy
3. Visit your GitHub Pages URL:
   - Usually: `https://<username>.github.io/<repository-name>/`
   - Specific dashboards:
     - Scott: `https://<username>.github.io/<repository-name>/scott/`
     - Markham Media: `https://<username>.github.io/<repository-name>/markham-media/`
     - Markham Makerspace: `https://<username>.github.io/<repository-name>/markham-makerspace/`

## Workflow Schedule

The workflow runs automatically:
- **First run:** 07:45 EST daily (data ready before 08:00 opening)
- **Regular runs:** Every 30 minutes from 08:00-21:00 EST
- **Manual runs:** Can be triggered via Actions → Run workflow

**Note:** The schedule uses UTC times and assumes EST (UTC-5). If daylight saving time (EDT/UTC-4) is in effect, the times will shift by one hour. Adjust the cron schedule in `.github/workflows/refresh.yml` if needed.

## Troubleshooting

### Workflow fails with authentication error

- Check that `LIBCAL_CLIENT_ID` and `LIBCAL_CLIENT_SECRET` secrets are correctly set
- Verify credentials are valid by testing locally: `python scripts/fetch_data.py`

### No changes committed

- This is normal if LibCal data hasn't changed since the last run
- The workflow checks for changes before committing

### Pages not updating

- Check the **Pages** build and deployment under Actions tab
- Verify the `docs/` folder contains the expected files
- Check Pages settings are correct (branch: main, folder: /docs)

### Appointments returning 403 errors

- This is expected until a new LibCal API key with `ap_r` scope is obtained
- The workflow continues successfully with empty appointments arrays
- Update `config/markham-makerspace.json` and set `"appointments": {"enabled": true}` once the new key is available

## Next Steps

Once M4 and M5 are complete:
1. Uncomment the `generate_dashboard.py` step in `.github/workflows/refresh.yml`
2. The workflow will generate HTML dashboards in addition to fetching data
3. GitHub Pages will serve the full interactive dashboards

## Support

For issues or questions, contact the MMCL development team.
