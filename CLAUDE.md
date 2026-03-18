# MMCL Staff Operations Dashboard — Claude Code Briefing

> This file is read by Claude Code at the start of every session.
> Full narrative requirements: `docs/requirements.docx` (v0.6)
> Full project plan: `docs/project-plan.md` (v1.0)

---

## Project in One Paragraph

Three read-only staff-facing dashboards for the Making & Media Creation Lab (MMCL) at York University Libraries. Each dashboard shows on-shift staff what is happening at their physical location today: space bookings, equipment loans, makerspace jobs, and consultation appointments — all pulled from the Springshare LibCal API. Phase 1 is a static GitHub Pages site refreshed every 30 minutes via GitHub Actions. Phase 2 (after Phase 1 is complete and reviewed) is a Docker-containerised interactive web app with persistent workflow state.

---

## Repository Structure

```
/
├── CLAUDE.md                        ← this file
├── config/
│   ├── scott-media-lab.json         ← location config, Scott (lid=2632)
│   ├── markham-media-lab.json       ← location config, Markham Media Lab (lid=3432)
│   └── markham-makerspace.json      ← location config, Markham Makerspace (lid=3430)
├── workflows/
│   ├── fdm-print.json               ← FDM 3D print job workflow
│   ├── resin-print.json             ← Resin 3D print job workflow
│   ├── sewing.json
│   ├── soldering.json
│   ├── vinyl-cutter.json
│   ├── heat-press.json
│   ├── embroidery.json
│   ├── laser-cutter-appointment.json
│   ├── makerspace-consultation.json
│   └── equipment-loan.json
├── scripts/
│   ├── fetch_data.py                ← fetches LibCal data → docs/*/data.json
│   └── generate_dashboard.py        ← renders data.json → docs/*/index.html
├── docs/                            ← GitHub Pages root
│   ├── scott/
│   │   ├── data.json
│   │   └── index.html
│   ├── markham-media/
│   │   ├── data.json
│   │   └── index.html
│   └── markham-makerspace/
│       ├── data.json
│       └── index.html
├── templates/
│   ├── media-lab.html               ← Jinja2 template, Media Lab
│   └── makerspace.html              ← Jinja2 template, Makerspace
├── static/
│   ├── style.css
│   └── dashboard.js
└── .github/workflows/
    └── refresh.yml                  ← cron every 30 min, 08:00–21:00 Toronto time
```

---

## Three Dashboard Instances

| Instance | Template | LibCal lid | Shift Boundary |
|---|---|---|---|
| Scott Media Lab | media-lab | 2632 | None (Full Shift) |
| Markham Media Lab | media-lab | 3432 | 13:00 |
| Markham Makerspace | makerspace | 3430 | 13:00 |

**Two templates, three instances.** `media-lab` covers studios + equipment loans. `makerspace` covers workstation bookings + appointments. All location-specific values live in `config/*.json` — no IDs are hardcoded in scripts or templates.

---

## LibCal API

**Base URL:** `https://yorku.libcal.com/api/1.1`
**Auth:** OAuth 2.0 client credentials (`POST /oauth/token`)
**Credentials:** `LIBCAL_CLIENT_ID` and `LIBCAL_CLIENT_SECRET` (GitHub Secrets / local `.env`)

### Endpoints used per dashboard

| Dashboard | Endpoint | Purpose |
|---|---|---|
| Both Media Labs | `GET /1.1/space/bookings?lid=<lid>` | Studio space bookings |
| Both Media Labs | `GET /1.1/equipment/bookings?lid=<lid>` | Equipment loans |
| Scott only | `GET /1.1/space/bookings?lid=3458` | Teaching events (separate location) |
| Makerspace | `GET /1.1/space/bookings?lid=3430` | Workstation bookings |
| Makerspace | `GET /1.1/appointments/bookings?group_id=<gid>` | Laser cutter + consultations |

**Makerspace does NOT use the Equipment API.** Equipment items use `groupId`/`groupName` fields (not `categoryId`) — different from spaces which use `cid`.

### Key API behaviours to handle
- **Pagination:** Hard limit 500 records per call. Always paginate; never assume one call is complete.
- **Keele (Scott) booking window:** 45 days. **Markham booking window:** 90 days.
- **Equipment categories endpoint** (`/equipment/categories`) returns 404 for these location IDs — do not use. Use `groupId` from item records instead.
- **Appointments endpoint** currently returns 403 with the current key. Gate behind a config flag (`"appointments_enabled": false`) so dashboards deploy without crashing until a new key with `ap_r` scope is available.

---

## Confirmed LibCal IDs

### Scott Media Lab (lid=2632)

**Space categories (studios):**

| cid | Name | Type |
|---|---|---|
| 5833 | Audio Recording Rooms | studio |
| 6842 | Flex Studio Spaces | studio |
| 5832 | VR Rooms | studio |
| 8413 | Scanning Stations | studio |
| 7878 | Class Support | non-public |
| 8034 | Events | non-public |

**Teaching events:** separate location `lid=3458`, `space_id=26820`. Requires a second API call.

**Space items:**

| space_id | Name |
|---|---|
| 21082 | Scott 203G - VR/Podcasting Room |
| 19905 | Scott 203K - Audio Recording Studio |
| 35844 | Scott 203L - Self-Service Scanning |
| 19904 | Scott 204 - Flex Studio |
| 21081 | Scott 207 - Editing Lab |
| 29187 | Scott 207C - Audio Recording Booth |
| 32502 | Scott 207D - Audio Recording Booth |

**Equipment groups (partial — paginated query needed for full list):**

| groupId | Name |
|---|---|
| 8143 | Camera Stabilizers |
| 8147 | Microphones |
| 8146 | Lighting |

---

### Markham Media Lab (lid=3432)

**Space categories:**

| cid | Name | Type |
|---|---|---|
| 7761 | Video Studios | studio |
| 7762 | Podcast Studios | studio |
| 7467 | Editing Studios | studio |
| 7951 | Large Studios | studio |
| 7770 | All Media Creation Suites | non-public |

**Space items:**

| space_id | Name |
|---|---|
| 30721 | Editing and Music Studio #1 (Rm 3060G) |
| 30722 | Editing and Music Studio #2 (Rm 3060F) |
| 30723 | Editing and Music Studio #3 (Rm 3060E) |
| 30719 | Green Screen Video Studio (Rm 3060C) |
| 30701 | Podcast Studio #2 (Rm 3060D) |
| 30720 | Video and Photo Studio (Rm 3060H) |

**Equipment groups (partial):**

| groupId | Name |
|---|---|
| 7832 | Camera Lenses |
| 8161 | Microphones |

---

### Markham Makerspace (lid=3430)

**Space categories (workstation types):**

| cid | Name | workflow_key |
|---|---|---|
| 7245 | 3D Printers | see space_id — FDM vs Resin differ |
| 7971 | Resin 3D Printers | resin-print |
| 7718 | Sewing & Cricut | sewing |
| 7722 | Soldering Stations | soldering |
| 7897 | 3D Scanners | (no workflow — equipment use, no job steps) |
| 7767 | Makerspace Room | teaching-event |

**FDM vs Resin disambiguation:** Both share `cid=7245` for some items. Distinguish by space name: Prusa Mini/MK4/XL/Core One → `fdm-print`; any "Resin" in name → `resin-print`.

**Space items (makerspace workstations):**

| space_id | Name | Type |
|---|---|---|
| 35142–35452 | Prusa Core One #1–4 | FDM (multicolour AMS) |
| 30724–30733 | Prusa Mini #01–10 | FDM (single colour) |
| 30735–30736 | Prusa MK4 #01–02 | FDM (single colour) |
| 30734, 35301–35302 | Prusa XL #1–3 | FDM (multicolour) |
| 31766–31770 | Bernette 35 #01–05 | Sewing |
| 31765 | Bernette 38 "Coco" | Sewing |
| 33845 | Cricut Cutter | Vinyl/Cricut |
| 33126, 33131–33132 | Revopoint Pop 3 3D Scanner | 3D Scanner |
| 31776, 32048–32052, 33169–33172 | Soldering Station #01–10 | Soldering |

**Appointments module:**

| Parameter | Value |
|---|---|
| Laser cutter group_id | 6581 |
| Makerspace consultation group_id | 6372 |
| Jacob Turola user_id | 42694 |
| Lana Yuan user_id | 43625 |

**Laser cutter conflict detection:** After fetching group_id=6581 appointments, check for time overlap between Jacob's and Lana's bookings. Overlap condition: `jacob.fromDate < lana.toDate AND jacob.toDate > lana.fromDate`. Surface as a warning banner + card-level flag. Do not auto-resolve.

**Laser cutter space_id:** TBC — does not yet exist in LibCal. Phase 2 prerequisite.

---

## Display Logic

### Daily filter rule
Show a booking if: `fromDate.date == today OR toDate.date == today`

**Exceptions:**
- **Makerspace only — In-Progress Jobs:** `fromDate.date < today AND toDate.date > today` → show in a separate persistent "In Progress" section, not the main list.
- **Media Lab only — Overdue Items:** `toDate.date < today AND status != returned/complete` → show in a persistent "Overdue" section, always visible.

### Shift grouping
If `shift_boundary` is set in config: bookings with `fromDate.time < boundary` → Opening Shift; `>= boundary` → Closing Shift. Bookings spanning the boundary → Opening Shift group + "Shift Boundary" flag. If no boundary: single "Full Shift" group.

### Booking types and visual treatment

| Type | Source | Visual |
|---|---|---|
| Studio booking | Spaces API, studio cids | Standard card, no workflow |
| Equipment loan | Equipment API | Card with pickup/return indicator |
| Overdue loan | Equipment API, past toDate | Persistent section, distinct styling |
| Makerspace workstation | Spaces API, makerspace cids | Card + workflow checklist panel |
| Laser cutter appointment | Appointments API, group 6581 | Card + staff name + workflow |
| Makerspace consultation | Appointments API, group 6372 | Card + staff name + workflow |
| Teaching event | Spaces API, teaching cids | Distinct badge, no workflow |

### Status badges

| LibCal status | Display | Colour |
|---|---|---|
| Confirmed / Self-Booked | CONFIRMED | York Red |
| Tentative | TENTATIVE | Amber |
| Mediated / Pending | PENDING | Teal |
| Cancelled | Hidden (count only) | — |
| Checked In | CHECKED IN | Green |
| Completed | In collapsed section | Grey |

---

## Workflow System

Workflows are defined in `workflows/*.json`. Assignment is by `cid` or space name pattern (see config). Steps are rendered as a non-interactive checklist in Phase 1.

### Step types

| type | Behaviour |
|---|---|
| `verification` | Pass/Fail. Phase 1: staff reminder. Phase 2: check local training registry file |
| `preparation` | Staff task. Outcome: complete |
| `handoff` | Staff ↔ patron communication. Outcome: complete |
| `data_entry` | If `phase2_action: libcal_patch` → triggers PATCH on booking. If `phase2_action: ordering_log` → staff reminder only (SharePoint, no API access) |
| `timer` | Phase 1: show estimated completion time. Phase 2: live countdown |

### Workflow JSON schema

```json
{
  "id": "fdm-print",
  "name": "FDM 3D Print Job",
  "steps": [
    {
      "step": 1,
      "type": "verification",
      "description": "Confirm patron has completed FDM orientation training",
      "notes": "Phase 2: check local training registry file",
      "phase2_action": "check_training_registry"
    }
  ]
}
```

### FDM print workflow (11 steps)
1. `verification` — Confirm FDM orientation training
2. `preparation` — Receive file; load into slicer
3. `preparation` — Slice file; check errors, supports, infill; agree with patron
4. `handoff` — Provide estimated duration and cost
5. `data_entry` — Update booking duration to match slicer estimate (`phase2_action: libcal_patch`)
6. `preparation` — Set up printer: load filament, clean/level bed. Multicolour (AMS): load all colours
7. `preparation` — Send file to printer; start job
8. `timer` — Monitor: print in progress
9. `preparation` — Remove parts; clean bed
10. `data_entry` — Record in ordering log: weight, price, patron info (`phase2_action: ordering_log`)
11. `handoff` — Give patron order number for payment at front desk

### Resin print workflow (15 steps) — STAFF OPERATED ONLY, patron does not touch printer
1. `verification` — Confirm resin orientation training (separate from FDM)
2. `preparation` — Receive file; load into resin slicer (Chitubox/Lychee)
3. `preparation` — Configure supports and orientation; agree with patron
4. `handoff` — Provide estimated duration and cost
5. `data_entry` — Update booking duration (`phase2_action: libcal_patch`)
6. `verification` — Staff puts on PPE (nitrile gloves, eye protection)
7. `preparation` — Inspect FEP film; confirm no damage BEFORE adding resin
8. `preparation` — Shake resin bottle; pour into vat; level build plate
9. `preparation` — Send file; start print
10. `timer` — Monitor: print in progress
11. `preparation` — Remove build plate; wash parts in IPA
12. `preparation` — UV cure parts
13. `preparation` — Remove supports; inspect; clean vat and plate. Dispose waste resin per protocol
14. `data_entry` — Record in ordering log (`phase2_action: ordering_log`)
15. `handoff` — Give patron order number

### Equipment loan workflow (2 phases, all categories)
**Checkout:** verify identity → check components against printed list in kit → confirm batteries charged → inspect condition → check out in LibCal → provide return instructions  
**Return:** receive item → check components → inspect vs checkout notes → check in LibCal → flag damage/missing

---

## Visual Design — York University Brand

| Element | Value |
|---|---|
| Primary font | IBM Plex Sans (Google Fonts) |
| Secondary fonts | IBM Plex Serif (long-form), IBM Plex Mono (IDs/codes) |
| York Red | `#E31837` — primary accent, headers, badges |
| York Red Medium | `#AF0D1A` — secondary |
| York Red Dark | `#810001` — table headers, deep accents |
| Light Grey | `#E1DFDC` — backgrounds, callout boxes |
| Pewter | `#D6CFCA` — table alternates |
| Grey Dark | `#686260` — supporting text, captions |
| Bright Blue | `#3AC2EF` — interactive/accent only, use sparingly |
| White | `#FFFFFF` |
| Black | `#000000` |

**AODA:** 4.5:1 contrast for normal text, 3:1 for large. York Red on White passes (≈4.6:1). Do NOT use tints of York Red — brand policy prohibits them.

**Dashboard layout zones (both templates):**
- **Zone A** — fixed header: location name, service type, date, last updated, shift label
- **Zone B** — Peak Load Timeline: hourly bar chart of concurrent bookings, past hours dimmed
- **Zone C** — main booking list: grouped by shift, sorted by `fromDate` ascending
- **Zone D** — persistent sections: Overdue Items (Media Lab) / In-Progress Jobs (Makerspace) + Completed Today (collapsed)

---

## GitHub Actions — `refresh.yml`

```yaml
# Runs every 30 min, 08:00–21:00 Toronto (UTC-5 = 13:00–02:00 UTC)
# Cron: */30 13-23,0-2 * * *  (approximation — adjust for DST)
# Also: workflow_dispatch for manual runs
# Steps: checkout → python setup → fetch_data.py (×3) → generate_dashboard.py (×3) → commit → deploy Pages
# Secrets: LIBCAL_CLIENT_ID, LIBCAL_CLIENT_SECRET
```

First daily run should be at 07:45 so data is ready before 08:00 opening.

---

## Phase 1 Milestone Status

| Milestone | Status |
|---|---|
| M1 — Repo setup + config schema | ✅ Complete |
| M2 — Data fetch script | ✅ Complete |
| M3 — GitHub Actions workflow | ✅ Complete |
| M4 — Media Lab template | ✅ Complete |
| M5 — Makerspace template | ✅ Complete |
| M6 — Integration + staff review | Ready for review |

**Phase 1 Complete - Ready for Deployment:**
- ✅ All dashboards functional with privacy masking
- ✅ Automated GitHub Actions workflow configured
- ⏳ Awaiting GitHub repository creation and Pages setup
- ⏳ New LibCal API key with `ap_r` scope for appointments (optional - works without)
- ⏳ Complete equipment group IDs via paginated audit query (partial list working)

**Phase 2 Pre-work:**
- [ ] University server identified for Docker deployment
- [ ] Network access configuration for on-site deployment

---

## Phase 2 — Broad Scope (detail after Phase 1)

- Python/Flask backend replacing GitHub Actions polling (5-min interval)
- SQLite for workflow completion state persistence
- Interactive workflow checklists (checkboxes, per-booking-ID state)
- LibCal write-back: `PATCH /1.1/space/booking/{id}` for duration updates (requires `sp_w` scope)
- Training registry file check for orientation verification steps (populated by separate eClass/LibWizard script — out of scope for this project)
- Docker container with volume-mounted config and workflow files
- Laser cutter space secondary conflict check (once space created in LibCal)

---

## Key Constraints and Non-Obvious Facts

- **Makerspace workstations are LibCal Spaces, not Equipment.** Never query the Equipment API for the Makerspace dashboard.
- **Scott teaching events are in a separate LibCal location** (lid=3458, space_id=26820) — requires a second API call beyond the main lid=2632 fetch.
- **Laser cutter has no LibCal space record** — the Appointments API is the only source of truth for laser cutter sessions. No corresponding equipment booking exists.
- **FDM and Resin printers may share cid=7245** in some items — disambiguate by space name, not cid alone.
- **Ordering log is SharePoint/Excel** — no API access possible (university Office 365 auth constraints). All ordering log steps are staff reminders only.
- **Training records are in a separate spreadsheet** — not in LibCal. Phase 1 verification steps are staff reminders. Phase 2 checks a local registry file populated by a separate pipeline.
- **Appointments API currently 403** with client_id=308 — gate all Appointments fetches behind `config.appointments_enabled` flag.
- **LibCal API 500-record limit** — paginate all booking fetches.
- **Equipment items use `groupId`/`groupName`**, not `categoryId` — the `/equipment/categories` endpoint returns 404 for MMCL locations.