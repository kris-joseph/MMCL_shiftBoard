# MMCL Dashboard Scripts

## fetch_data.py

Fetches booking data from the LibCal API for all three dashboard instances and saves to `docs/*/data.json`.

### Usage

```bash
# Ensure dependencies are installed
pip install -r requirements.txt

# Run the script
python scripts/fetch_data.py
```

### What it does

1. **Authenticates** with LibCal API using OAuth 2.0 client credentials from `.env`
2. **Fetches data** for each dashboard:
   - **Scott Media Lab:** Space bookings, equipment bookings, teaching events (from separate location)
   - **Markham Media Lab:** Space bookings, equipment bookings
   - **Markham Makerspace:** Space bookings, appointments (when API key with `ap_r` scope is available)
3. **Handles pagination** automatically (LibCal has 500 record limit per call)
4. **Saves output** to:
   - `docs/scott/data.json`
   - `docs/markham-media/data.json`
   - `docs/markham-makerspace/data.json`

### Configuration

The script reads from:
- `.env` file for API credentials (`LIBCAL_CLIENT_ID`, `LIBCAL_CLIENT_SECRET`)
- `config/*.json` files for dashboard-specific settings

### Output format

Each `data.json` file contains:

```json
{
  "location_id": 2632,
  "location_name": "Scott Media Lab",
  "template": "media-lab",
  "shift_boundary": null,
  "fetch_timestamp": "2026-03-17T22:04:49.946375",
  "date": "2026-03-17",
  "space_bookings": [...],
  "equipment_bookings": [...],
  "appointments": [...],
  "teaching_events": [...]
}
```

**Note**: `data.json` files contain full patron names and email addresses from the LibCal API. See [docs/PRIVACY.md](../docs/PRIVACY.md) for privacy protection details.

### Error handling

- **403 on Appointments API:** Script continues with empty appointments array and logs a warning
- **Authentication failures:** Script exits with error message
- **Network errors:** HTTP exceptions are raised and script exits

## generate_dashboard.py

Renders `data.json` files into static HTML dashboards using Jinja2 templates.

### Usage

```bash
# Ensure dependencies are installed (including Jinja2)
pip install -r requirements.txt

# Run the script
python scripts/generate_dashboard.py
```

### What it does

1. **Loads data** from `docs/*/data.json` files
2. **Processes bookings** with business logic:
   - Filters for today's date
   - Groups by shift (Opening/Closing or Full Shift)
   - Identifies overdue equipment
   - Sorts bookings by time
   - Calculates peak load timeline (hourly concurrent bookings)
3. **Loads workflows** from `workflows/*.json`
4. **Renders HTML** using Jinja2 templates:
   - `templates/media-lab.html` for Scott and Markham Media Lab
   - `templates/makerspace.html` for Markham Makerspace (M5)
5. **Saves output** to:
   - `docs/scott/index.html`
   - `docs/markham-media/index.html`
   - `docs/markham-makerspace/index.html` (M5)

### Features

- **Shift grouping**: Bookings grouped by shift boundary if configured
- **Timeline visualization**: Hourly bar chart of concurrent bookings
- **Status badges**: Color-coded status indicators (Confirmed, Tentative, Pending, Checked In)
- **Overdue tracking**: Separate section for overdue equipment loans
- **Workflow display**: Read-only checklists for equipment loans (Phase 1)
- **Responsive design**: Mobile-friendly layout with York University branding
- **Accessibility**: AODA compliant with proper contrast ratios and ARIA labels

### Output format

Each dashboard includes:
- **Header**: Location name, date, last updated time, current shift
- **Peak Load Timeline**: Visual bar chart of hourly booking density
- **Booking Cards**: Detailed information for each booking
- **Persistent Sections**: Overdue items, completed bookings (collapsible)

### Privacy protection

**Phase 1 (GitHub Pages - Public):**
Patron information is automatically masked in generated HTML:
- Names: Initials only ("A.M." instead of "Anne Magsombol")
- Emails: Masked ("m***@my.yorku.ca" instead of full email)

**Phase 2 (Docker - Private):**
Full patron information displayed (network-level access control).

Control via environment variable:
```bash
# Default for Phase 1
PRIVACY_MODE=true python scripts/generate_dashboard.py

# Phase 2 deployment
PRIVACY_MODE=false python scripts/generate_dashboard.py
```

See [docs/PRIVACY.md](../docs/PRIVACY.md) for complete privacy documentation.

### Workflow integration

Equipment loans automatically include checkout workflow steps. Phase 2 will add:
- Interactive checkboxes for workflow steps
- Persistent state tracking in SQLite
- Real-time workflow progress updates
