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

### Task-Based Model (Core Dashboard Logic)

**Critical Context:** Dashboards are task-oriented, not booking-oriented. Each booking represents discrete tasks that staff must complete. The dashboard shows actionable tasks for the current day, not just a list of active bookings.

#### Task States

Every booking is categorized into exactly one state:

1. **START task** — Booking begins today, needs staff action (setup/checkout)
2. **END task** — Booking ends today, needs staff action (teardown/checkin)
3. **IN PROGRESS** — Patron is onsite, no immediate task (Media Lab spaces only)
4. **COMPLETED** — All tasks finished, shown in collapsed "Completed Today" section
5. **OVERDUE** — Equipment past return date, not checked in (persistent warning section)

#### Equipment Task Detection (Status-Based)

Equipment bookings use the LibCal `status` field to determine task state:

```python
# START task (checkout needed)
if fromDate.date == today AND status in ["Confirmed", "Self-Booked Confirmed", "Mediated Approved"]:
    show in shift list with "CHECKOUT NEEDED" task label

# END task (checkin needed)
if toDate.date == today AND status == "Checked Out":
    show in shift list with "CHECKIN NEEDED" task label

# COMPLETED
if status == "Checked In":
    show in "Completed Today" collapsed section

# OVERDUE
if toDate < now AND status not in ["Checked In", "Completed", "Returned"]:
    show in persistent "Overdue Items" section
```

**Multi-day equipment loans:**
- 7-day loan starting Monday → START task on Monday only, hidden Tue-Sat, END task on Sunday
- Do not show "in progress" state for equipment between start and end dates

#### Space/Makerspace Task Detection (Check-in Heuristic)

Media Lab spaces and Makerspace workstations do not have check-in/check-out status in the API. Use **fromDate minute detection** to infer check-in:

**Check-in Detection Rule:**
```python
def is_checked_in_space(booking):
    """
    Standard booking slots: :00, :15, :30, :45 minutes past the hour
    When patron checks in, LibCal updates fromDate to exact check-in time

    Examples:
      - fromDate = 9:00 AM → NOT checked in (standard slot)
      - fromDate = 9:36 AM → CHECKED IN (non-standard time)
    """
    from_dt = parse(booking["fromDate"])
    return from_dt.minute not in [0, 15, 30, 45]
```

**Media Lab Spaces:**
```python
# START task (setup needed)
if fromDate.date == today AND not checked_in AND fromDate > now:
    show in shift list (no task label for spaces)

# IN PROGRESS (patron onsite)
if checked_in AND now < toDate:
    show in persistent "Patron Onsite" section with "IN PROGRESS" task label

# COMPLETED
if toDate < now AND (checked_in OR status in ["Completed", "Returned"]):
    show in "Completed Today" collapsed section
```

**Teaching Events (Media Lab only) — time-based, no check-in heuristic:**
```python
# ONGOING — show in shift list while running (before OR during the event)
if fromDate.date == today AND toDate > now:
    show in shift list (no task label)

# COMPLETED
if fromDate.date == today AND toDate <= now:
    show in "Completed Today" collapsed section
```
Teaching events are never moved to "Patron Onsite" — they stay in the shift list until finished. This is because no one checks in for a teaching event, so the minute heuristic does not apply.

**Makerspace Workstations:**

Makerspace uses pure time-based logic (no check-in tracking in Phase 1):

```python
# UPCOMING task
if fromDate > now:
    show in shift list (no task label)

# IN PROGRESS (time-based, no check-in detection)
if fromDate <= now < toDate:
    show in persistent "In-Progress Jobs" section with "IN PROGRESS" task label

# COMPLETED
if toDate < now:
    show in "Completed Today" collapsed section
```

**Multi-day makerspace jobs:**
- 3-day print job starting Monday → Hidden Monday-Tuesday, shown in "In-Progress Jobs" section (not shift list) until completion

### Daily Filter Rule (Applied After Task Categorization)

Show a booking in the main shift list if it has a START or END task today:
- Equipment: `fromDate.date == today` (START) OR `toDate.date == today` (END)
- Spaces: `fromDate.date == today` AND not checked in AND fromDate > now (START only, no END task for spaces)

**Bookings appear in persistent sections instead of shift lists if:**
- **IN PROGRESS:** Checked in (Media Lab) or time-based (Makerspace), shown in dedicated section
- **COMPLETED:** All tasks done, shown in collapsed "Completed Today"
- **OVERDUE:** Equipment past due, shown in persistent "Overdue Items"

### Shift grouping
If `shift_boundary` is set in config: bookings with `fromDate.time < boundary` → Opening Shift; `>= boundary` → Closing Shift. Bookings spanning the boundary → Opening Shift group + "Shift Boundary" flag. If no boundary: single "Full Shift" group.

### Hour grouping within shift blocks
Within each shift block, bookings are further nested into collapsible hour subgroups (e.g. "11 AM — 3 tasks"), collapsed by default. Tasks whose task-relevant time (`from_datetime`) is more than **2 hours in the past** are pulled into a separate "**Still outstanding from earlier today**" group pinned at the top of the shift block, also collapsed, with amber styling. Implemented by `group_shift_bookings(bookings, now)` which adds `outstanding` and `hour_groups` keys to each shift dict.

### Booking types and visual treatment

| Type | Source | Visual | Task Label |
|---|---|---|---|
| Studio booking (START) | Spaces API, studio cids | Standard card, no workflow | None |
| Studio booking (IN PROGRESS) | Spaces API, checked in | Persistent "Patron Onsite" section | "IN PROGRESS" |
| Equipment loan (START) | Equipment API, status=Confirmed | Card with 📦 pickup indicator | "CHECKOUT NEEDED" |
| Equipment loan (END) | Equipment API, status=Checked Out | Card with ↩️ return indicator | "CHECKIN NEEDED" |
| Overdue loan | Equipment API, past toDate | Persistent "Overdue Items" section | "OVERDUE" |
| Makerspace workstation (upcoming) | Spaces API, makerspace cids | Card + workflow checklist panel | None |
| Makerspace workstation (IN PROGRESS) | Spaces API, time-based | Persistent "In-Progress Jobs" section + workflow | "IN PROGRESS" |
| Laser cutter appointment | Appointments API, group 6581 | Card + staff name + workflow | Context-dependent |
| Makerspace consultation | Appointments API, group 6372 | Card + staff name + workflow | Context-dependent |
| Teaching event | Spaces API, teaching cids | Distinct badge, no workflow | None |

**Task label badge styling:** Bright blue background (`#3AC2EF`), white text, bold weight. CSS class: `.badge.badge-task`

### Status badges

| LibCal status | Display | Colour |
|---|---|---|
| Confirmed / Self-Booked / Mediated Approved | CONFIRMED | York Red |
| Tentative | TENTATIVE | Amber |
| Mediated / Pending (not "Mediated Approved") | PENDING | Teal |
| Cancelled | Hidden (count only) | — |
| Checked In | CHECKED IN | Green |
| Completed | In collapsed section | Grey |

**Important:** "Mediated Approved" must be checked before the generic "mediated" substring in `map_status_to_class`, otherwise it incorrectly gets teal `status-pending` styling. Order matters.

---

## Workflow System

Workflows are defined in `workflows/*.json`. Assignment is by `cid` or space name pattern (see config). Steps are rendered as an **interactive checklist** with localStorage persistence. Each step has a checkbox; checking it marks the step completed (strikethrough, dimmed, green circle). A progress bar fills left-to-right in the collapsed card header as steps are checked. A step counter (`0 / N`) lives in the workflow panel header. State is keyed by `bookingId` and survives page refreshes within a browser session. In-progress job cards (Makerspace Zone D) display a full workflow panel with an inline horizontal progress bar instead of the header-bar version.

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
| M6 — Integration + staff review | ✅ Complete |
| M7 — Task-based model implementation | ✅ Complete (commit f29f662) |

**Phase 1 Complete - Ready for Deployment:**
- ✅ All dashboards functional with privacy masking (including completed section)
- ✅ Task-oriented display logic with START/END task detection
- ✅ Check-in detection via fromDate minute heuristic
- ✅ Persistent sections: "Patron Onsite", "In-Progress Jobs", "Overdue Items", "Completed Today"
- ✅ Task labels and visual indicators (CHECKOUT NEEDED, CHECKIN NEEDED, IN PROGRESS)
- ✅ Automated GitHub Actions workflow configured (with `permissions: contents: write`)
- ✅ Live on GitHub Pages: https://kris-joseph.github.io/MMCL_shiftBoard/
- ✅ Hour grouping within shift blocks; outstanding tasks surfaced separately
- ✅ Equipment loan task time displayed prominently in card header
- ✅ Teaching events filter on both dashboards
- ✅ Correct Toronto timezone for "last updated" display
- ✅ Interactive workflow checklists with localStorage persistence and progress bars (commit d5bf063)
- ✅ Cache-busting `?v=<timestamp>` on all static asset URLs — regenerated on every GitHub Actions run
- ⏳ New LibCal API key with `ap_r` scope for appointments (optional - works without)
- ⏳ Complete equipment group IDs via paginated audit query (partial list working)

**Phase 2 Pre-work:**
- [ ] University server identified for Docker deployment
- [ ] Network access configuration for on-site deployment

---

## Implementation Notes — Task-Based Model

### Key Functions (scripts/generate_dashboard.py)

**`is_checked_in_space(booking) -> bool`**
- Detects if a space/makerspace booking has been checked in
- Returns `True` if `fromDate.minute` not in `[0, 15, 30, 45]`
- Standard LibCal booking slots are at quarter-hour intervals
- When patron checks in, LibCal updates `fromDate` to exact check-in time

**`get_booking_tasks(booking, booking_type, today, now) -> Dict`**
- Central task state determination for all booking types
- Returns dict with: `has_start_task`, `has_end_task`, `is_in_progress`, `is_completed`, `task_time`
- Handles three logic paths:
  - **Equipment:** Status-based detection ("Confirmed" → START, "Checked Out" → END)
  - **Media Lab Spaces:** Check-in heuristic + time comparison
  - **Makerspace:** Time-based only (fromDate <= now < toDate)

**`process_media_lab_data(data, config) -> Dict`**
- Categorizes all bookings into: `shift_tasks`, `in_progress_spaces`, `completed_bookings`, `overdue_equipment`
- Each booking appears in exactly one category
- Multi-day equipment loans only show on first day (START) or last day (END)
- Returns context for Jinja2 template with persistent sections populated

**`process_makerspace_data(data, config) -> Dict`**
- Categorizes bookings into: `shift_tasks`, `in_progress_jobs`, `completed_bookings`
- Multi-day print jobs always appear in `in_progress_jobs` (not shift list)
- Time-based in-progress detection: `fromDate <= now < toDate`
- Returns context with workflow assignments for makerspace workstations

**`_format_space_booking(booking, shift_boundary, now, task_type) -> Dict`**
**`_format_equipment_booking(booking, shift_boundary, now, task_type) -> Dict`**
- Accept `task_type` parameter: `"start_task"`, `"end_task"`, `"in_progress"`
- Return `task_label` field for display in template badges
- Equipment bookings include `equipment_indicator` (📦 Pickup / ↩️ Return)
- Equipment bookings also include `task_time` (the single task-relevant time string) and `task_time_label` ("Checkout" for START, "Due back" for END) — displayed prominently in the card header bar using `.task-time-prominent` CSS class

**`group_shift_bookings(bookings, now) -> Dict`**
- Splits a sorted list of shift bookings into `outstanding` (task_time > 2h ago) and `hour_groups` (remaining, keyed by hour)
- Returns `{"outstanding": [...], "hour_groups": [{"label": "11 AM", "count": N, "bookings": [...]}]}`
- Called in both `process_media_lab_data` and `process_makerspace_data` after sorting; adds `outstanding` and `hour_groups` to each shift dict

**`_format_completed_item(booking) -> Dict`**
- Uses `mask_patron_name()` — do NOT use raw `firstName + " " + lastName` concatenation here

**`get_workflow_for_booking(booking, booking_type, task_type) -> Optional[Dict]`**
- Used by `_format_equipment_booking()` to build equipment loan workflow data
- Must return `step_count` as well as `steps` — both are needed by templates
- Equipment loan workflow dict shape: `{type, phase_name, step_count, steps[]}`

**`_format_in_progress_job(booking, today, config) -> Dict`**
- Returns `workflow` dict that now includes the full `steps` list (not just `step_count`)
- Required so the in-progress job card in Zone D can render interactive checkboxes
- In-progress jobs use inline progress bar (`.workflow-inline-progress`), not header-bar progress

### Workflow Checklist — JavaScript (`static/dashboard.js`)

The workflow checklist is implemented entirely in `dashboard.js` with four concerns:

| Function | Purpose |
|---|---|
| `window.onStepChecked(checkbox)` | Called by `onchange` on each checkbox; updates step visual, calls `updateWorkflowProgress`, persists to localStorage |
| `updateWorkflowProgress(card)` | Recalculates checked/total; updates `.workflow-header-progress-fill` width, `.workflow-inline-progress-fill` width, and `.workflow-step-counter` text |
| `saveCheckedSteps(bookingId, steps[])` / `loadCheckedSteps(bookingId)` | localStorage read/write; keyed as `mmcl_steps_<bookingId>`; **these two functions are the Phase 2 replacement points** |
| `initWorkflowCheckboxes()` | Runs at page load; restores saved state from localStorage and calls `updateWorkflowProgress` for each card with saved steps |

**Progress bar anatomy:**
- **Header bar progress** (collapsible cards): `<div class="workflow-header-progress"><div class="workflow-header-progress-fill"></div></div>` — absolutely positioned at `bottom: 0` inside `.booking-card-header-bar` (which must have `position: relative`). Track is `rgba(0,0,0,0.25)`, fill is green (`var(--status-checked-in)`).
- **Inline progress** (in-progress job cards): `<div class="workflow-inline-progress"><div class="workflow-inline-progress-fill"></div></div>` — 4px bar above the step list.

### Static Asset Cache-Busting

Both templates append `?v={{ asset_version }}` to CSS and JS URLs. `asset_version` is set in `generate_dashboard()` as `int(datetime.now(timezone.utc).timestamp())` immediately before `template.render()`. This ensures each GitHub Actions run produces a unique URL, forcing browsers to fetch the latest `dashboard.js` and `style.css` rather than serving a cached version. **Do not remove this** — stale JS cache was confirmed to silently break the workflow checklist.

### Template Context Variables (Both Templates)

**Main shift list:**
- `shifts[].bookings[]` — All bookings in this shift (kept for counts; templates render from `hour_groups` and `outstanding`)
- `shifts[].outstanding[]` — Bookings whose task time is >2h in the past
- `shifts[].hour_groups[]` — Remaining bookings grouped by hour: `{label, count, bookings[]}`
- Each booking has `task_label` (may be `None`), `task_type`, and for equipment: `task_time`, `task_time_label`

**Persistent sections:**
- `in_progress_spaces[]` — Media Lab only, spaces where patron is checked in
- `in_progress_jobs[]` — Makerspace only, multi-day jobs + time-based in-progress workstations
- `overdue_items[]` — Media Lab only, equipment past due date
- `completed_items[]` — Both templates, collapsed section at bottom

**Filters:**
- Media Lab: `data-booking-type` attributes (`"space"`, `"equipment"`, `"teaching"`); Teaching Events filter button shown only when `has_teaching_events` is True
- Makerspace: `data-station-type` attributes (e.g., `"fdm-printer"`, `"sewing"`, `"soldering"`); Teaching Events filter appears automatically when teaching bookings exist
- Filter JS also hides `.hour-group` elements when all their cards are filtered out

### Known Limitations

**LibCal API does not expose check-in timestamps:**
- The Springshare web dashboard shows "checked in at 9:36 AM"
- This timestamp is NOT available via API (no `checkedInAt` or `checkedOutAt` fields)
- Workaround: fromDate minute heuristic (detects check-in but not exact time)

**Equipment status field edge cases:**
- Some equipment bookings may have status "Mediated Approved" instead of "Confirmed"
- Both are treated as START tasks (checkout needed)
- "Self-Booked Confirmed" also treated as START task

**Makerspace has no check-in tracking:**
- Phase 1 uses time-based logic only (`fromDate <= now < toDate`)
- Staff do not manually check in patrons for makerspace workstations
- Phase 2 may add optional check-in workflow for multi-day jobs

**Timezone handling:**
- All LibCal `fromDate` and `toDate` values are timezone-aware
- `fetch_timestamp` from `data.json` may be naive — code ensures conversion to `timezone.utc`
- All time comparisons use timezone-aware datetimes
- `last_updated` display time is converted to `America/Toronto` via `zoneinfo.ZoneInfo` before formatting — do NOT format directly from `now` (which is UTC)

**Teaching events use time-based logic, not check-in heuristic:**
- The minute heuristic only applies to regular space bookings where LibCal updates `fromDate` on patron check-in
- Nobody checks in for a teaching event; `fromDate` stays at the standard slot time
- Teaching events must remain visible in the shift list from before they start until they end (`toDate > now`)

---

## Phase 2 — Broad Scope (detail after Phase 1)

**Already scaffolded in Phase 1 (UI layer complete, persistence layer needs replacing):**
- ✅ Interactive workflow checklists — checkboxes, step completion visuals, progress bars all built
- ✅ Step counter and header progress bar wired up
- 🔁 **Replace localStorage with server-side persistence:** In `dashboard.js`, `saveCheckedSteps()` and `loadCheckedSteps()` are the only two functions that touch localStorage. In Phase 2, replace these with API calls (`POST /api/workflow-state` and `GET /api/workflow-state/:bookingId`). The UI layer (`onStepChecked`, `initWorkflowCheckboxes`, `updateWorkflowProgress`) does not need to change.

**Still to build:**
- Python/Flask backend replacing GitHub Actions polling (5-min interval)
- SQLite for workflow completion state persistence (replaces localStorage)
- LibCal write-back: `PATCH /1.1/space/booking/{id}` for duration updates (requires `sp_w` scope) — triggered by `data_entry` steps with `phase2_action: libcal_patch`
- Training registry file check for `verification` steps with `phase2_action: check_training_registry` (populated by separate eClass/LibWizard script — out of scope for this project)
- Docker container with volume-mounted config and workflow files
- Laser cutter space secondary conflict check (once space created in LibCal)
- Timer step live countdown (for `type: timer` steps currently showing "Phase 2: Live countdown timer")

---

## Key Constraints and Non-Obvious Facts

- **Check-in detection uses fromDate minute heuristic.** LibCal does NOT expose check-in timestamps via API, even though Springshare's dashboard shows them. Standard booking slots are at :00/:15/:30/:45. When a patron checks in, LibCal updates `fromDate` to the exact check-in time (e.g., 9:36 AM). If `fromDate.minute not in [0, 15, 30, 45]`, the booking is checked in. This heuristic is the ONLY way to detect check-ins for spaces in Phase 1.
- **Equipment uses status field, not check-in heuristic.** Equipment bookings have explicit status tracking: "Confirmed" → checkout needed, "Checked Out" → checkin needed, "Checked In" → completed. Do NOT use the minute heuristic for equipment.
- **Multi-day equipment loans only show on first/last day.** A 7-day equipment loan starting Monday should only appear in Monday's shift list (START task) and Sunday's shift list (END task). Do NOT show equipment bookings on days between start and end.
- **Makerspace workstations are LibCal Spaces, not Equipment.** Never query the Equipment API for the Makerspace dashboard.
- **Scott teaching events are in a separate LibCal location** (lid=3458, space_id=26820) — requires a second API call beyond the main lid=2632 fetch.
- **Laser cutter has no LibCal space record** — the Appointments API is the only source of truth for laser cutter sessions. No corresponding equipment booking exists.
- **FDM and Resin printers may share cid=7245** in some items — disambiguate by space name, not cid alone.
- **Ordering log is SharePoint/Excel** — no API access possible (university Office 365 auth constraints). All ordering log steps are staff reminders only.
- **Training records are in a separate spreadsheet** — not in LibCal. Phase 1 verification steps are staff reminders. Phase 2 checks a local registry file populated by a separate pipeline.
- **Appointments API currently 403** with client_id=308 — gate all Appointments fetches behind `config.appointments_enabled` flag.
- **LibCal API 500-record limit** — paginate all booking fetches.
- **Equipment items use `groupId`/`groupName`**, not `categoryId` — the `/equipment/categories` endpoint returns 404 for MMCL locations.
- **All patron name/email fields must use `mask_patron_name()` / `mask_patron_email()`** — applies to every `_format_*` method including `_format_appointment_booking()`. Raw string concatenation (`firstName + " " + lastName`) is a privacy violation on the public GitHub Pages site. A bug where appointments bypassed masking was fixed in this session.
- **Browser caching of static assets** — `dashboard.js` and `style.css` must have `?v={{ asset_version }}` appended in templates. Without this, browsers serve the cached old JS even after a deploy, silently breaking any new JavaScript features.