# MMCL Staff Operations Dashboard

Three read-only staff-facing dashboards for the Making & Media Creation Lab (MMCL) at York University Libraries.

## Project Overview

Each dashboard shows on-shift staff what is happening at their physical location today:
- Space bookings
- Equipment loans
- Makerspace jobs
- Consultation appointments

All data is pulled from the Springshare LibCal API.

**Phase 1:** Static GitHub Pages site refreshed every 30 minutes via GitHub Actions
**Phase 2:** Docker-containerised interactive web app with persistent workflow state

## Dashboard Instances

| Instance | Template | LibCal lid | URL |
|----------|----------|------------|-----|
| Scott Media Lab | media-lab | 2632 | /scott/ |
| Markham Media Lab | media-lab | 3432 | /markham-media/ |
| Markham Makerspace | makerspace | 3430 | /markham-makerspace/ |

## Setup

### Local Development

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd MMCL_shiftBoard
   ```

2. **Create virtual environment**
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure credentials**
   ```bash
   cp .env.example .env
   # Edit .env and add your LibCal API credentials
   ```

5. **Test data fetch**
   ```bash
   python scripts/fetch_data.py
   ```

### GitHub Deployment

See [docs/SETUP.md](docs/SETUP.md) for complete GitHub Pages deployment instructions, including:
- Configuring GitHub Secrets
- Enabling GitHub Pages
- Setting up the automated workflow

## Repository Structure

```
/
├── config/              # Location-specific configuration
├── workflows/           # Workflow JSON definitions
├── scripts/             # Python scripts for data fetching and rendering
├── templates/           # Jinja2 HTML templates
├── static/              # CSS and JavaScript
├── docs/                # GitHub Pages output directory
└── .github/workflows/   # GitHub Actions configuration
```

## Development Status

**Phase 1 Milestones:**

- [x] M1 — Repo setup + config schema
- [x] M2 — Data fetch script
- [x] M3 — GitHub Actions workflow
- [x] M4 — Media Lab template
- [x] M5 — Makerspace template
- [ ] M6 — Integration + staff review

## Privacy Protection

**Phase 1 (GitHub Pages)** uses automatic privacy masking:
- Patron names shown as initials only
- Email addresses partially masked
- Full details in [docs/PRIVACY.md](docs/PRIVACY.md)

**Phase 2 (Docker)** will display full information with network-level access control.

## Documentation

- `CLAUDE.md` - Complete project briefing, API details, and workflow specifications
- `docs/PRIVACY.md` - Privacy protection documentation
- `docs/SETUP.md` - GitHub deployment guide

## License

Internal York University Libraries project.
