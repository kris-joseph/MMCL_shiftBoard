# Privacy Protection in MMCL Dashboards

## Overview

The MMCL Dashboard system includes privacy protection features to safeguard patron information when deployed to public-facing environments.

## Privacy Mode

### Phase 1 (GitHub Pages - Public)

**Privacy Mode: ENABLED (default)**

When deployed to GitHub Pages (publicly accessible), patron information is automatically masked:

- **Names**: Shown as initials only
  - "Anne Magsombol" → "A.M."
  - "Rebecca Caines" → "R.C."

- **Emails**: First character + asterisks, domain visible
  - "magzs110@my.yorku.ca" → "m***@my.yorku.ca"
  - "rcaines@yorku.ca" → "r***@yorku.ca"

This protects patron privacy while still allowing staff to identify bookings by context (time, resource, initials).

### Phase 2 (Docker - Private On-Site)

**Privacy Mode: DISABLED**

When deployed on-site via Docker (accessible only on university network), full patron information is displayed:

- **Names**: Full names shown
- **Emails**: Complete email addresses shown

This provides staff with complete information for patron assistance while maintaining privacy through network-level access control.

## Configuration

Privacy mode is controlled by the `PRIVACY_MODE` environment variable:

```bash
# .env file

# Phase 1 (public GitHub Pages) - DEFAULT
PRIVACY_MODE=true

# Phase 2 (private Docker deployment)
PRIVACY_MODE=false
```

### GitHub Actions (Phase 1)

The workflow automatically uses privacy mode (enabled by default). No configuration needed.

### Local Development

To test with full patron information locally:

```bash
PRIVACY_MODE=false python scripts/generate_dashboard.py
```

To test with masked information (matches production):

```bash
# Default - privacy mode enabled
python scripts/generate_dashboard.py
```

## What Information is Masked

✅ **Masked in Privacy Mode:**
- Patron first and last names
- Patron email addresses

❌ **NOT Masked (Required for Operations):**
- Booking times and durations
- Resource/space names
- Booking IDs and check-in codes
- Booking status
- Equipment groups
- Staff names (for appointments)

## Data Storage

**Important**: The `data.json` files in `docs/*/` directories contain **full patron information** from the LibCal API. These files are:

- ✅ Masked when rendered to HTML (privacy mode enabled)
- ⚠️ Stored in git repository with full data
- 🔒 Not directly accessible via GitHub Pages web interface
- 📝 Should be treated as sensitive data

The privacy masking occurs only during HTML generation, not during data fetching. This allows Phase 2 to access full information by simply toggling the `PRIVACY_MODE` flag.

## Security Considerations

1. **Public Deployment (Phase 1)**:
   - GitHub Pages serves only HTML files from `/docs/*/index.html`
   - `data.json` files are in the repo but not linked or indexed
   - HTML contains only masked patron information
   - Acceptable for public viewing

2. **Private Deployment (Phase 2)**:
   - Deployed on university network (not publicly accessible)
   - Network-level access control protects patron data
   - Full information displayed to authorized staff only

3. **Repository Access**:
   - Repository should be private to protect `data.json` files
   - Only authorized MMCL staff should have repository access
   - API credentials stored in GitHub Secrets (never in code)

## Compliance

This privacy approach balances:
- **FIPPA** (Ontario Freedom of Information and Protection of Privacy Act)
- **York University privacy policies**
- **Operational requirements** for staff to assist patrons
- **Security through obscurity** (masked data on public pages)
- **Access control** (full data only on private network)

## Audit Trail

All patron data access is logged:
- GitHub Actions workflow runs (timestamps, commits)
- LibCal API access (via LibCal's own logging)
- Phase 2 will add application-level access logging

## Future Enhancements (Phase 2)

- User authentication (staff login required)
- Role-based access control (different views for different staff roles)
- Audit logging of all patron data access
- Option to suppress specific bookings from public view entirely
