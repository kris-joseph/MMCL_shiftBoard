#!/usr/bin/env python3
"""
MMCL Dashboard Generator
Renders data.json files into HTML dashboards using Jinja2 templates.
"""

import os
import json
import sys
import re
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader


class DashboardGenerator:
    """Generates HTML dashboards from LibCal data and templates."""

    def __init__(self, project_root: Path, privacy_mode: bool = True):
        self.project_root = project_root
        self.templates_dir = project_root / "templates"
        self.workflows_dir = project_root / "workflows"
        self.static_dir = project_root / "static"
        self.config_dir = project_root / "config"
        self.privacy_mode = privacy_mode  # Enable for public GitHub Pages (Phase 1)

        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Load all workflows
        self.workflows = self._load_workflows()

    def _load_workflows(self) -> Dict[str, Dict]:
        """Load all workflow JSON files."""
        workflows = {}
        for workflow_file in self.workflows_dir.glob("*.json"):
            with open(workflow_file, 'r') as f:
                workflow_data = json.load(f)
                workflows[workflow_data["id"]] = workflow_data
        return workflows

    def mask_patron_name(self, first_name: str, last_name: str) -> str:
        """
        Mask patron name for privacy.
        Phase 1 (public): Returns initials (e.g., "A.M.")
        Phase 2 (private): Returns full name
        """
        if not self.privacy_mode:
            return f"{first_name} {last_name}".strip()

        # Return initials
        first_initial = first_name[0].upper() if first_name else ""
        last_initial = last_name[0].upper() if last_name else ""

        if first_initial and last_initial:
            return f"{first_initial}.{last_initial}."
        elif first_initial:
            return f"{first_initial}."
        elif last_initial:
            return f"{last_initial}."
        else:
            return "Patron"

    def mask_patron_email(self, email: str) -> str:
        """
        Mask patron email for privacy.
        Phase 1 (public): Returns masked email (e.g., "m***@my.yorku.ca")
        Phase 2 (private): Returns full email
        """
        if not self.privacy_mode:
            return email

        if not email or "@" not in email:
            return "***@***"

        # Split email into local and domain parts
        local, domain = email.split("@", 1)

        # Mask local part: show first character + asterisks
        if len(local) > 1:
            masked_local = local[0] + "***"
        elif len(local) == 1:
            masked_local = local[0] + "***"
        else:
            masked_local = "***"

        return f"{masked_local}@{domain}"

    def parse_datetime(self, dt_string: str) -> datetime:
        """Parse ISO 8601 datetime string from LibCal."""
        # LibCal format: "2026-03-17T11:30:00-04:00"
        return datetime.fromisoformat(dt_string)

    def format_date(self, dt: datetime) -> str:
        """Format date for display (e.g., 'Monday, March 17, 2026')."""
        return dt.strftime("%A, %B %d, %Y")

    def format_time(self, dt: datetime) -> str:
        """Format time for display (e.g., '11:30 AM')."""
        return dt.strftime("%-I:%M %p")

    def calculate_overdue_duration(self, due_date: datetime, now: datetime) -> str:
        """Calculate how long an item has been overdue."""
        delta = now - due_date
        hours = delta.total_seconds() / 3600

        if hours < 1:
            return "Less than 1 hour"
        elif hours < 24:
            return f"{int(hours)} hour{'s' if hours >= 2 else ''}"
        else:
            days = int(hours / 24)
            return f"{days} day{'s' if days != 1 else ''}"

    def is_today(self, dt_string: str, target_date: date) -> bool:
        """Check if a datetime string is on the target date."""
        dt = self.parse_datetime(dt_string)
        return dt.date() == target_date

    def get_shift_group(self, from_date_str: str, shift_boundary: Optional[str]) -> str:
        """Determine which shift a booking belongs to."""
        if not shift_boundary:
            return "Full Shift"

        from_dt = self.parse_datetime(from_date_str)
        boundary_time = datetime.strptime(shift_boundary, "%H:%M").time()

        if from_dt.time() < boundary_time:
            return "Opening Shift"
        else:
            return "Closing Shift"

    def spans_shift_boundary(self, from_date_str: str, to_date_str: str, shift_boundary: Optional[str]) -> bool:
        """Check if a booking spans the shift boundary."""
        if not shift_boundary:
            return False

        from_dt = self.parse_datetime(from_date_str)
        to_dt = self.parse_datetime(to_date_str)
        boundary_time = datetime.strptime(shift_boundary, "%H:%M").time()

        return from_dt.time() < boundary_time <= to_dt.time()

    def map_status_to_class(self, status: str) -> str:
        """Map LibCal status to CSS class."""
        status_lower = status.lower()
        if "confirmed" in status_lower or "self-booked" in status_lower or "mediated approved" in status_lower:
            return "status-confirmed"
        elif "tentative" in status_lower:
            return "status-tentative"
        elif "pending" in status_lower or "mediated" in status_lower:
            return "status-pending"
        elif "checked in" in status_lower:
            return "status-checked-in"
        elif "completed" in status_lower:
            return "status-completed"
        else:
            return "status-confirmed"

    def map_status_display(self, status: str) -> str:
        """Map LibCal status to display text."""
        status_lower = status.lower()
        if "confirmed" in status_lower or "self-booked" in status_lower:
            return "CONFIRMED"
        elif "mediated approved" in status_lower:
            return "CONFIRMED"
        elif "tentative" in status_lower:
            return "TENTATIVE"
        elif "pending" in status_lower or "mediated" in status_lower:
            return "PENDING"
        elif "checked in" in status_lower:
            return "CHECKED IN"
        elif "completed" in status_lower:
            return "COMPLETED"
        else:
            return status.upper()

    def get_workflow_phase(self, workflow: Dict, task_type: str) -> tuple:
        """Return the correct phase dict given task_type.

        task_type == "end_task" → phases.end
        All other task_types (start_task, upcoming, in_progress) → phases.start
        """
        phases = workflow.get("phases", {})
        if task_type == "end_task":
            phase = phases.get("end", {})
            phase_key = "end"
        else:
            phase = phases.get("start", {})
            phase_key = "start"
        return phase, phase_key

    def get_workflow_for_booking(self, booking: Dict, booking_type: str, task_type: str = "start_task") -> Optional[Dict]:
        """Get workflow data for a booking if applicable."""
        # Equipment loans always use equipment-loan workflow
        if booking_type == "equipment":
            workflow_id = "equipment-loan"
            workflow = self.workflows.get(workflow_id)
            if workflow:
                phase, _ = self.get_workflow_phase(workflow, task_type)
                phase_steps = phase.get("steps", [])
                return {
                    "type": "equipment-loan",
                    "phase_name": phase.get("name", "Equipment Checkout"),
                    "step_count": len(phase_steps),
                    "steps": [
                        {"number": step["step"], "description": step["description"]}
                        for step in phase_steps
                    ]
                }
        return None

    def is_checked_in_space(self, booking: Dict) -> bool:
        """
        Detect if a space/makerspace booking has been checked in.

        Standard booking slots are at :00, :15, :30, :45 minutes.
        When a patron checks in, fromDate gets updated to the exact check-in time.
        """
        from_dt = self.parse_datetime(booking["fromDate"])
        return from_dt.minute not in [0, 15, 30, 45]

    def get_booking_tasks(self, booking: Dict, booking_type: str, today: date, now: datetime) -> Dict:
        """
        Determine what tasks (START, END, IN_PROGRESS, COMPLETED) apply to a booking.

        Returns dict with:
        - has_start_task: bool
        - has_end_task: bool
        - is_in_progress: bool
        - is_completed: bool
        - task_time: datetime (for sorting - when the task occurs)
        """
        from_dt = self.parse_datetime(booking["fromDate"])
        to_dt = self.parse_datetime(booking["toDate"])
        status = booking.get("status", "").lower()

        # Skip cancelled bookings
        if "cancelled" in booking.get("status", "").lower():
            return {"has_start_task": False, "has_end_task": False, "is_in_progress": False, "is_completed": False}

        if booking_type == "equipment":
            # Equipment: Use status field for tracking
            has_start_task = (
                from_dt.date() == today and
                status in ["confirmed", "self-booked confirmed", "mediated approved", "mediated tentative"]
            )
            has_end_task = (
                to_dt.date() == today and
                status == "checked out"
            )
            is_completed = status == "checked in"
            is_in_progress = False  # Equipment doesn't have "in progress" state

            # Task time: use fromDate for START, toDate for END
            if has_start_task:
                task_time = from_dt
            elif has_end_task:
                task_time = to_dt
            else:
                task_time = from_dt

        else:  # space or makerspace
            # Spaces: Use fromDate minute detection for check-in
            checked_in = self.is_checked_in_space(booking)

            has_start_task = (
                from_dt.date() == today and
                not checked_in and
                from_dt > now  # Only show if not yet time
            )

            is_in_progress = (
                checked_in and
                now < to_dt  # Patron checked in, hasn't left yet
            )

            is_completed = (
                to_dt < now and
                (checked_in or status in ["completed", "returned"])
            )

            has_end_task = False  # Spaces don't have trackable END task in Phase 1
            task_time = from_dt

        return {
            "has_start_task": has_start_task,
            "has_end_task": has_end_task,
            "is_in_progress": is_in_progress,
            "is_completed": is_completed,
            "task_time": task_time
        }

    def calculate_timeline(self, bookings: List[Dict], today: date) -> List[Dict]:
        """
        Calculate hourly staff transaction counts for timeline.

        Counts start and end transactions separately - staff have tasks when bookings
        START (setup/checkout) and when they END (teardown/checkin), but not during.

        Example: 2-4 PM space booking creates transactions at 2 PM (setup) and 4 PM (teardown),
        but zero transactions at 3 PM.
        """
        # Operating hours: 8 AM - 9 PM (13 hours)
        hours = list(range(8, 22))  # 8-21 (8 AM - 9 PM)
        hour_counts = {hour: 0 for hour in hours}

        # Count start and end transactions for each hour
        for booking in bookings:
            from_dt = self.parse_datetime(booking["fromDate"])
            to_dt = self.parse_datetime(booking["toDate"])

            # Only count bookings happening today
            if from_dt.date() != today and to_dt.date() != today:
                continue

            # Skip cancelled bookings
            if "cancelled" in booking:
                continue

            # Count booking START transaction (setup/checkout)
            start_hour = from_dt.hour
            if start_hour in hours:
                hour_counts[start_hour] += 1

            # Count booking END transaction (teardown/checkin)
            end_hour = to_dt.hour
            if end_hour in hours:
                hour_counts[end_hour] += 1

        # Find max count for scaling
        max_count = max(hour_counts.values()) if hour_counts else 1
        max_count = max(max_count, 1)  # Avoid division by zero

        # Current hour
        current_hour = datetime.now().hour

        # Build timeline data
        timeline = []
        for hour in hours:
            count = hour_counts[hour]
            height = (count / max_count) * 100 if count > 0 else 0

            # Format hour label
            hour_12 = hour if hour <= 12 else hour - 12
            hour_12 = 12 if hour_12 == 0 else hour_12
            am_pm = "AM" if hour < 12 else "PM"
            label = f"{hour_12}{am_pm}"

            timeline.append({
                "label": label,
                "count": count,
                "height": height,
                "is_past": hour < current_hour
            })

        return timeline

    def group_shift_bookings(self, bookings: List[Dict], now: datetime) -> Dict:
        """Group shift bookings by task hour; pull tasks >2h overdue into an outstanding list."""
        cutoff = now - timedelta(hours=2)
        outstanding = []
        by_hour: Dict[int, Dict] = {}

        for booking in bookings:
            task_dt = booking.get("from_datetime")
            if task_dt and task_dt < cutoff:
                outstanding.append(booking)
            else:
                if task_dt:
                    hour_key = task_dt.hour
                    hour_label = task_dt.strftime("%-I %p")
                else:
                    hour_key = 99
                    hour_label = "—"
                if hour_key not in by_hour:
                    by_hour[hour_key] = {"label": hour_label, "bookings": []}
                by_hour[hour_key]["bookings"].append(booking)

        hour_groups = [
            {"label": data["label"], "count": len(data["bookings"]), "bookings": data["bookings"]}
            for _, data in sorted(by_hour.items())
        ]
        return {"outstanding": outstanding, "hour_groups": hour_groups}

    def process_media_lab_data(self, data: Dict, config: Optional[Dict] = None) -> Dict:
        """Process data for media lab dashboard using task-based model."""
        today = datetime.fromisoformat(data["date"]).date()
        shift_boundary = data.get("shift_boundary")
        location_name = data["location_name"]

        # All bookings (space + equipment + teaching)
        all_space_bookings = data.get("space_bookings", [])
        all_equipment_bookings = data.get("equipment_bookings", [])
        all_teaching_events = data.get("teaching_events", [])

        # Filter teaching events to specific space_id if configured
        teaching_events = all_teaching_events
        if config and all_teaching_events:
            teaching_config = config.get("teaching_events", {})
            filter_space_id = teaching_config.get("space_id")
            if filter_space_id:
                teaching_events = [
                    t for t in all_teaching_events
                    if t.get("eid") == filter_space_id
                ]
                print(f"  → Filtered teaching events to space_id={filter_space_id}: {len(all_teaching_events)} → {len(teaching_events)}")

        # Use fetch_timestamp to determine "now"
        fetch_timestamp_str = data.get("fetch_timestamp")
        if fetch_timestamp_str:
            now = datetime.fromisoformat(fetch_timestamp_str)
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
        else:
            now = datetime.now(timezone.utc)

        # Categorize all bookings by task state
        shift_tasks = {}  # Tasks that need to be done today (START or END)
        in_progress_spaces = []  # Spaces where patron is onsite
        completed_bookings = []  # Completed bookings
        overdue_equipment = []  # Equipment that's overdue

        # Initialize shift buckets
        for shift_name in (["Opening Shift", "Closing Shift"] if shift_boundary else ["Full Shift"]):
            shift_tasks[shift_name] = []

        # Process space bookings
        for booking in all_space_bookings:
            tasks = self.get_booking_tasks(booking, "space", today, now)

            if tasks["is_in_progress"]:
                in_progress_spaces.append(self._format_space_booking(booking, shift_boundary, now, "in_progress"))
            elif tasks["is_completed"]:
                completed_bookings.append(self._format_completed_item(booking))
            elif tasks["has_start_task"]:
                shift = self.get_shift_group(booking["fromDate"], shift_boundary)
                shift_tasks[shift].append(self._format_space_booking(booking, shift_boundary, now, "start_task"))

        # Process equipment bookings
        for booking in all_equipment_bookings:
            tasks = self.get_booking_tasks(booking, "equipment", today, now)

            if tasks["is_completed"]:
                completed_bookings.append(self._format_completed_item(booking))
            elif tasks["has_start_task"]:
                # Equipment pickup task
                shift = self.get_shift_group(booking["fromDate"], shift_boundary)
                shift_tasks[shift].append(self._format_equipment_booking(booking, shift_boundary, now, "start_task"))
            elif tasks["has_end_task"]:
                # Equipment return task
                shift = self.get_shift_group(booking["toDate"], shift_boundary)
                shift_tasks[shift].append(self._format_equipment_booking(booking, shift_boundary, now, "end_task"))
            elif self.parse_datetime(booking["toDate"]) < now and booking.get("status", "").lower() not in ["checked in", "completed", "returned"]:
                # Overdue equipment
                overdue_equipment.append(booking)

        # Process teaching events (treated like spaces but usually no check-in tracking)
        for booking in teaching_events:
            if "cancelled" in booking.get("status", "").lower():
                continue

            from_dt = self.parse_datetime(booking["fromDate"])
            to_dt = self.parse_datetime(booking["toDate"])

            if from_dt.date() == today and to_dt > now:
                # Show while ongoing today (before start OR currently running)
                shift = self.get_shift_group(booking["fromDate"], shift_boundary)
                shift_tasks[shift].append(self._format_teaching_booking(booking, shift_boundary))
            elif from_dt.date() == today and to_dt <= now:
                completed_bookings.append(self._format_completed_item(booking))

        # Build shift data structure
        shifts = []
        for shift_name, tasks in shift_tasks.items():
            # Sort by task time
            tasks.sort(key=lambda b: b["from_datetime"])
            grouped = self.group_shift_bookings(tasks, now)

            shifts.append({
                "name": shift_name,
                "space_count": len([t for t in tasks if t.get("booking_type") == "space"]),
                "equipment_count": len([t for t in tasks if t.get("booking_type") == "equipment"]),
                "teaching_count": len([t for t in tasks if t.get("booking_type") == "teaching"]),
                "bookings": tasks,
                "outstanding": grouped["outstanding"],
                "hour_groups": grouped["hour_groups"]
            })

        # Calculate timeline (include all bookings that start or end today)
        all_today_bookings = all_space_bookings + all_equipment_bookings + teaching_events
        timeline_bookings = [
            b for b in all_today_bookings
            if (self.is_today(b["fromDate"], today) or self.is_today(b["toDate"], today))
            and "cancelled" not in b.get("status", "").lower()
        ]
        timeline = self.calculate_timeline(timeline_bookings, today)

        # Format overdue items
        overdue_items = [self._format_overdue_item(item, now) for item in overdue_equipment]

        # Determine shift label for header
        shift_label = None
        if shift_boundary:
            current_time = now.time()
            boundary_time = datetime.strptime(shift_boundary, "%H:%M").time()
            shift_label = "Opening Shift" if current_time < boundary_time else "Closing Shift"

        has_teaching_events = any(
            b.get("booking_type") == "teaching"
            for shift in shifts
            for b in shift["bookings"]
        )

        return {
            "location_name": location_name,
            "current_date": self.format_date(today),
            "last_updated": now.astimezone(ZoneInfo("America/Toronto")).strftime("%-I:%M %p"),
            "shift_label": shift_label,
            "timeline": timeline,
            "shifts": shifts,
            "in_progress_spaces": in_progress_spaces,
            "overdue_items": overdue_items,
            "completed_items": completed_bookings,
            "has_teaching_events": has_teaching_events,
            "warnings": []  # For Phase 2: conflict detection
        }

    def _format_space_booking(self, booking: Dict, shift_boundary: Optional[str], now: datetime, task_type: str = "start_task") -> Dict:
        """Format a space booking for display with task context."""
        from_dt = self.parse_datetime(booking["fromDate"])
        to_dt = self.parse_datetime(booking["toDate"])

        # Determine task-specific display
        if task_type == "in_progress":
            task_label = "IN PROGRESS"
            card_class = "in-progress"
        else:  # start_task
            task_label = None
            card_class = ""

        return {
            "booking_id": booking.get("bookId", "N/A"),
            "booking_type": "space",
            "task_type": task_type,
            "task_label": task_label,
            "title": booking.get("item_name", "Unknown Space"),
            "category": booking.get("category_name", "Space"),
            "from_time": self.format_time(from_dt),
            "to_time": self.format_time(to_dt),
            "from_datetime": from_dt,  # For sorting
            "patron_name": self.mask_patron_name(booking.get("firstName", ""), booking.get("lastName", "")),
            "patron_email": self.mask_patron_email(booking.get("email", "")),
            "check_in_code": booking.get("check_in_code"),
            "status_display": self.map_status_display(booking.get("status", "")),
            "status_class": self.map_status_to_class(booking.get("status", "")),
            "card_class": card_class,
            "is_teaching_event": False,
            "spans_shift_boundary": self.spans_shift_boundary(booking["fromDate"], booking["toDate"], shift_boundary),
            "equipment_indicator": None,
            "workflow": None,
            "group_name": None
        }

    def _format_equipment_booking(self, booking: Dict, shift_boundary: Optional[str], now: datetime, task_type: str = "start_task") -> Dict:
        """Format an equipment booking for display with task context."""
        from_dt = self.parse_datetime(booking["fromDate"])
        to_dt = self.parse_datetime(booking["toDate"])

        # Equipment indicator based on task type
        if task_type == "start_task":
            equipment_indicator = {"type": "pickup", "label": "📦 Pickup"}
            task_label = "CHECKOUT NEEDED"
            sort_time = from_dt
            task_time = self.format_time(from_dt)
            task_time_label = "Checkout"
        else:  # end_task
            equipment_indicator = {"type": "return", "label": "↩️ Return"}
            task_label = "CHECKIN NEEDED"
            sort_time = to_dt
            task_time = self.format_time(to_dt)
            task_time_label = "Due back"

        return {
            "booking_id": booking.get("bookId", "N/A"),
            "booking_type": "equipment",
            "task_type": task_type,
            "task_label": task_label,
            "title": booking.get("item_name", "Unknown Equipment"),
            "category": booking.get("category_name", "Equipment"),
            "from_time": self.format_time(from_dt),
            "to_time": self.format_time(to_dt),
            "task_time": task_time,
            "task_time_label": task_time_label,
            "from_datetime": sort_time,  # For sorting
            "patron_name": self.mask_patron_name(booking.get("firstName", ""), booking.get("lastName", "")),
            "patron_email": self.mask_patron_email(booking.get("email", "")),
            "check_in_code": booking.get("check_in_code"),
            "status_display": self.map_status_display(booking.get("status", "")),
            "status_class": self.map_status_to_class(booking.get("status", "")),
            "card_class": "equipment-loan",
            "is_teaching_event": False,
            "spans_shift_boundary": self.spans_shift_boundary(booking["fromDate"], booking["toDate"], shift_boundary),
            "equipment_indicator": equipment_indicator,
            "workflow": self.get_workflow_for_booking(booking, "equipment", task_type),
            "group_name": booking.get("groupName")
        }

    def _format_teaching_booking(self, booking: Dict, shift_boundary: Optional[str]) -> Dict:
        """Format a teaching event for display."""
        from_dt = self.parse_datetime(booking["fromDate"])
        to_dt = self.parse_datetime(booking["toDate"])

        return {
            "booking_id": booking.get("bookId", "N/A"),
            "booking_type": "teaching",
            "station_type": "teaching",
            "title": booking.get("item_name", "Teaching Event"),
            "category": "Teaching Event",
            "from_time": self.format_time(from_dt),
            "to_time": self.format_time(to_dt),
            "from_datetime": from_dt,
            "patron_name": self.mask_patron_name(booking.get("firstName", ""), booking.get("lastName", "")),
            "patron_email": self.mask_patron_email(booking.get("email", "")),
            "check_in_code": booking.get("check_in_code"),
            "status_display": self.map_status_display(booking.get("status", "")),
            "status_class": self.map_status_to_class(booking.get("status", "")),
            "card_class": "teaching-event",
            "is_teaching_event": True,
            "spans_shift_boundary": self.spans_shift_boundary(booking["fromDate"], booking["toDate"], shift_boundary),
            "equipment_indicator": None,
            "workflow": None,
            "group_name": None
        }

    def _format_overdue_item(self, booking: Dict, now: datetime) -> Dict:
        """Format an overdue equipment item."""
        to_dt = self.parse_datetime(booking["toDate"])

        return {
            "booking_id": booking.get("bookId", "N/A"),
            "title": booking.get("item_name", "Unknown Equipment"),
            "category": booking.get("category_name", "Equipment"),
            "due_date": self.format_date(to_dt),
            "due_time": self.format_time(to_dt),
            "patron_name": self.mask_patron_name(booking.get("firstName", ""), booking.get("lastName", "")),
            "patron_email": self.mask_patron_email(booking.get("email", "")),
            "group_name": booking.get("groupName"),
            "overdue_duration": self.calculate_overdue_duration(to_dt, now)
        }

    def _format_completed_item(self, booking: Dict) -> Dict:
        """Format a completed booking."""
        from_dt = self.parse_datetime(booking["fromDate"])
        to_dt = self.parse_datetime(booking["toDate"])

        return {
            "booking_id": booking.get("bookId", "N/A"),
            "title": booking.get("item_name", "Unknown"),
            "category": booking.get("category_name", "Booking"),
            "from_time": self.format_time(from_dt),
            "to_time": self.format_time(to_dt),
            "patron_name": self.mask_patron_name(booking.get("firstName", ""), booking.get("lastName", ""))
        }

    def assign_workflow_to_workstation(self, booking: Dict, config: Dict) -> Optional[str]:
        """Assign workflow to a workstation booking based on config rules."""
        category_name = booking.get("category_name", "")
        item_name = booking.get("item_name", "")
        cid = booking.get("cid")

        # Find matching category in config
        for cat in config.get("space_categories", {}).get("workstations", []):
            if cat["cid"] == cid:
                # Check if workflow assignment is by space name pattern
                if cat.get("workflow_assignment") == "by_space_name":
                    for rule in cat.get("workflow_rules", []):
                        pattern = rule["pattern"]
                        if re.search(pattern, item_name, re.IGNORECASE):
                            return rule["workflow"]
                # Direct workflow assignment
                elif cat.get("workflow"):
                    return cat["workflow"]

        return None

    def process_makerspace_data(self, data: Dict, config: Dict) -> Dict:
        """Process data for makerspace dashboard using task-based model."""
        today = datetime.fromisoformat(data["date"]).date()
        shift_boundary = data.get("shift_boundary")
        location_name = data["location_name"]

        # Use fetch_timestamp to determine "now"
        fetch_timestamp_str = data.get("fetch_timestamp")
        if fetch_timestamp_str:
            now = datetime.fromisoformat(fetch_timestamp_str)
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
        else:
            now = datetime.now(timezone.utc)

        # All space bookings (workstations)
        all_space_bookings = data.get("space_bookings", [])
        all_appointments = data.get("appointments", [])

        # Categorize bookings by task state
        shift_tasks = {}  # Upcoming tasks (staff needs to help set up)
        in_progress_jobs = []  # Multi-day jobs in progress OR today's bookings where patron is onsite
        completed_bookings = []  # Completed bookings

        # Initialize shift buckets
        for shift_name in (["Opening Shift", "Closing Shift"] if shift_boundary else ["Full Shift"]):
            shift_tasks[shift_name] = []

        # Process workstation bookings (3D printers, sewing, etc.)
        for booking in all_space_bookings:
            if "cancelled" in booking.get("status", "").lower():
                continue

            from_dt = self.parse_datetime(booking["fromDate"])
            to_dt = self.parse_datetime(booking["toDate"])

            # Multi-day print jobs (started before today, end today or later)
            if from_dt.date() < today and to_dt.date() >= today:
                workflow_id = self.assign_workflow_to_workstation(booking, config)
                in_progress_jobs.append(self._format_in_progress_job(booking, today, config))
                continue

            # Check if booking is for today
            if from_dt.date() != today and to_dt.date() != today:
                continue

            # Teaching events (Makerspace Room)
            if booking.get("category_name") == "Makerspace Room":
                if from_dt > now:
                    shift = self.get_shift_group(booking["fromDate"], shift_boundary)
                    shift_tasks[shift].append(self._format_teaching_booking(booking, shift_boundary))
                continue

            # Regular workstation bookings - use time-based logic (no manual check-in in Phase 1)
            if from_dt > now:
                # UPCOMING: Show as task
                shift = self.get_shift_group(booking["fromDate"], shift_boundary)
                workflow_id = self.assign_workflow_to_workstation(booking, config)
                shift_tasks[shift].append(
                    self._format_workstation_booking(booking, shift_boundary, workflow_id, now, "upcoming")
                )
            elif from_dt <= now < to_dt:
                # IN PROGRESS: Patron is onsite
                workflow_id = self.assign_workflow_to_workstation(booking, config)
                in_progress_jobs.append(
                    self._format_workstation_booking(booking, shift_boundary, workflow_id, now, "in_progress")
                )
            elif to_dt < now:
                # COMPLETED: Booking has ended
                completed_bookings.append(self._format_completed_item(booking))

        # Process appointments (if enabled)
        for appointment in all_appointments:
            if "cancelled" in appointment.get("status", "").lower():
                continue

            from_dt = self.parse_datetime(appointment["fromDate"])
            to_dt = self.parse_datetime(appointment["toDate"])

            if from_dt.date() == today and from_dt > now:
                shift = self.get_shift_group(appointment["fromDate"], shift_boundary)
                shift_tasks[shift].append(self._format_appointment_booking(appointment, shift_boundary))

        # Build shift data structure
        shifts = []
        for shift_name, tasks in shift_tasks.items():
            # Sort by task time
            tasks.sort(key=lambda b: b["from_datetime"])
            grouped = self.group_shift_bookings(tasks, now)

            shifts.append({
                "name": shift_name,
                "workstation_count": len([t for t in tasks if t.get("booking_type") == "workstation"]),
                "appointment_count": len([t for t in tasks if t.get("booking_type") == "appointment"]),
                "teaching_count": len([t for t in tasks if t.get("booking_type") == "teaching"]),
                "bookings": tasks,
                "outstanding": grouped["outstanding"],
                "hour_groups": grouped["hour_groups"]
            })

        # Calculate timeline (include all bookings that start or end today)
        all_today_bookings = [
            b for b in all_space_bookings + all_appointments
            if (self.is_today(b["fromDate"], today) or self.is_today(b["toDate"], today))
            and "cancelled" not in b.get("status", "").lower()
        ]
        timeline = self.calculate_timeline(all_today_bookings, today)

        # Determine shift label
        shift_label = None
        if shift_boundary:
            current_time = now.time()
            boundary_time = datetime.strptime(shift_boundary, "%H:%M").time()
            shift_label = "Opening Shift" if current_time < boundary_time else "Closing Shift"

        # Check for laser cutter conflicts (if appointments enabled and conflict detection enabled)
        warnings = []
        if config.get("appointments", {}).get("enabled"):
            for group in config.get("appointments", {}).get("groups", []):
                if group.get("conflict_detection", {}).get("enabled"):
                    # Phase 2: Implement conflict detection logic
                    pass

        # Collect unique station types for filter buttons (from all bookings)
        station_types = set()
        for shift in shifts:
            for booking in shift["bookings"]:
                if booking.get("station_type"):
                    station_types.add((booking["station_type"], booking["category"]))
        for job in in_progress_jobs:
            if job.get("station_type"):
                station_types.add((job["station_type"], job["category"]))

        # Sort by category name and create filter list
        station_filters = [
            {"type": st_type, "label": st_label}
            for st_type, st_label in sorted(station_types, key=lambda x: x[1])
        ]

        return {
            "location_name": location_name,
            "current_date": self.format_date(today),
            "last_updated": now.astimezone(ZoneInfo("America/Toronto")).strftime("%-I:%M %p"),
            "shift_label": shift_label,
            "timeline": timeline,
            "shifts": shifts,
            "in_progress_jobs": in_progress_jobs,
            "completed_items": completed_bookings,
            "warnings": warnings,
            "station_filters": station_filters
        }

    def _format_workstation_booking(self, booking: Dict, shift_boundary: Optional[str], workflow_id: Optional[str], now: datetime = None, task_type: str = "upcoming") -> Dict:
        """Format a workstation booking for display with task context."""
        from_dt = self.parse_datetime(booking["fromDate"])
        to_dt = self.parse_datetime(booking["toDate"])

        # Calculate duration
        duration_hours = (to_dt - from_dt).total_seconds() / 3600
        duration_str = f"{duration_hours:.1f} hours" if duration_hours >= 1 else f"{int(duration_hours * 60)} minutes"

        # Calculate progress duration (for in_progress display)
        if now:
            progress_seconds = (now - from_dt).total_seconds()
            progress_hours = progress_seconds / 3600
            if progress_hours < 1:
                progress_duration = f"{int(progress_hours * 60)} minutes"
            elif progress_hours < 24:
                progress_duration = f"{progress_hours:.1f} hours"
            else:
                progress_duration = f"{progress_hours / 24:.1f} days"
        else:
            progress_duration = None

        # Load workflow if assigned
        workflow_data = None
        if workflow_id and workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            phase, _ = self.get_workflow_phase(workflow, task_type)
            phase_steps = phase.get("steps", [])
            workflow_data = {
                "name": workflow["name"],
                "phase_name": phase.get("name", workflow["name"]),
                "step_count": len(phase_steps),
                "safety_critical": workflow.get("safety_critical", False),
                "patron_operated": workflow.get("patron_operated", True),
                "steps": [
                    {
                        "number": step["step"],
                        "description": step["description"],
                        "type": step["type"],
                        "safety_required": step.get("safety_required", False)
                    }
                    for step in phase_steps
                ]
            }

        # Normalize station type for filtering
        category = booking.get("category_name", "Workstation")
        station_type = category.lower().replace(" & ", "-").replace(" ", "-")

        # Task-specific display
        if task_type == "in_progress":
            task_label = "IN PROGRESS"
            card_class = "workstation in-progress"
        else:  # upcoming
            task_label = None
            card_class = "workstation"

        return {
            "booking_id": booking.get("bookId", "N/A"),
            "booking_type": "workstation",
            "station_type": station_type,
            "task_type": task_type,
            "task_label": task_label,
            "title": booking.get("item_name", "Unknown Workstation"),
            "category": category,
            "from_time": self.format_time(from_dt),
            "to_time": self.format_time(to_dt),
            "from_datetime": from_dt,
            "patron_name": self.mask_patron_name(booking.get("firstName", ""), booking.get("lastName", "")),
            "patron_email": self.mask_patron_email(booking.get("email", "")),
            "check_in_code": booking.get("check_in_code"),
            "status_display": self.map_status_display(booking.get("status", "")),
            "status_class": self.map_status_to_class(booking.get("status", "")),
            "card_class": card_class,
            "is_teaching_event": False,
            "is_appointment": False,
            "spans_shift_boundary": self.spans_shift_boundary(booking["fromDate"], booking["toDate"], shift_boundary),
            "duration_hours": duration_str,
            "start_date": self.format_date(from_dt),
            "start_time": self.format_time(from_dt),
            "end_date": self.format_date(to_dt),
            "end_time": self.format_time(to_dt),
            "progress_duration": progress_duration,
            "workflow": workflow_data,
            "staff_name": None
        }

    def _format_appointment_booking(self, appointment: Dict, shift_boundary: Optional[str]) -> Dict:
        """Format an appointment booking for display."""
        from_dt = self.parse_datetime(appointment["fromDate"])
        to_dt = self.parse_datetime(appointment["toDate"])

        # Get workflow from appointment metadata (appointments always show start phase)
        workflow_id = appointment.get("_workflow")
        workflow_data = None
        if workflow_id and workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            phase, _ = self.get_workflow_phase(workflow, "start_task")
            phase_steps = phase.get("steps", [])
            workflow_data = {
                "name": workflow["name"],
                "phase_name": phase.get("name", workflow["name"]),
                "step_count": len(phase_steps),
                "safety_critical": workflow.get("safety_critical", False),
                "patron_operated": workflow.get("patron_operated", True),
                "steps": [
                    {
                        "number": step["step"],
                        "description": step["description"],
                        "type": step["type"],
                        "safety_required": step.get("safety_required", False)
                    }
                    for step in phase_steps
                ]
            }

        return {
            "booking_id": appointment.get("bookId", "N/A"),
            "booking_type": "appointment",
            "station_type": "appointment",
            "title": appointment.get("_group_name", "Appointment"),
            "category": "Appointment",
            "from_time": self.format_time(from_dt),
            "to_time": self.format_time(to_dt),
            "from_datetime": from_dt,
            "patron_name": self.mask_patron_name(appointment.get("firstName", ""), appointment.get("lastName", "")),
            "patron_email": self.mask_patron_email(appointment.get("email", "")),
            "check_in_code": appointment.get("check_in_code"),
            "status_display": self.map_status_display(appointment.get("status", "")),
            "status_class": self.map_status_to_class(appointment.get("status", "")),
            "card_class": "appointment",
            "is_teaching_event": False,
            "is_appointment": True,
            "spans_shift_boundary": self.spans_shift_boundary(appointment["fromDate"], appointment["toDate"], shift_boundary),
            "duration_hours": None,
            "workflow": workflow_data,
            "staff_name": appointment.get("staff_name")  # Phase 2: extract from appointment data
        }

    def _format_in_progress_job(self, booking: Dict, today: date, config: Dict) -> Dict:
        """Format an in-progress job for display."""
        from_dt = self.parse_datetime(booking["fromDate"])
        to_dt = self.parse_datetime(booking["toDate"])
        now = datetime.now(timezone.utc)

        # Calculate progress duration
        progress_seconds = (now - from_dt).total_seconds()
        progress_hours = progress_seconds / 3600
        if progress_hours < 1:
            progress_duration = f"{int(progress_hours * 60)} minutes"
        elif progress_hours < 24:
            progress_duration = f"{progress_hours:.1f} hours"
        else:
            progress_days = progress_hours / 24
            progress_duration = f"{progress_days:.1f} days"

        # Assign workflow (in-progress jobs show start phase for context)
        workflow_id = self.assign_workflow_to_workstation(booking, config)
        workflow_data = None
        if workflow_id and workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            phase, _ = self.get_workflow_phase(workflow, "start_task")
            workflow_data = {
                "name": workflow["name"],
                "phase_name": phase.get("name", workflow["name"]),
                "step_count": len(phase.get("steps", [])),
                "steps": [
                    {
                        "number": step["step"],
                        "description": step["description"],
                        "type": step["type"],
                        "safety_required": step.get("safety_required", False)
                    }
                    for step in phase.get("steps", [])
                ]
            }

        # Normalize station type for filtering
        category = booking.get("category_name", "Workstation")
        station_type = category.lower().replace(" & ", "-").replace(" ", "-")

        return {
            "booking_id": booking.get("bookId", "N/A"),
            "station_type": station_type,
            "title": booking.get("item_name", "Unknown"),
            "category": category,
            "start_date": self.format_date(from_dt),
            "start_time": self.format_time(from_dt),
            "end_date": self.format_date(to_dt),
            "end_time": self.format_time(to_dt),
            "patron_name": self.mask_patron_name(booking.get("firstName", ""), booking.get("lastName", "")),
            "patron_email": self.mask_patron_email(booking.get("email", "")),
            "progress_duration": progress_duration,
            "workflow": workflow_data
        }

    def generate_dashboard(self, data_file: Path, output_file: Path, template_name: str, config_file: Optional[Path] = None):
        """Generate a single dashboard HTML file."""
        # Load data
        with open(data_file, 'r') as f:
            data = json.load(f)

        # Load config if needed (for makerspace)
        config = None
        if config_file and config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)

        # Process based on template type
        if template_name == "media-lab":
            context = self.process_media_lab_data(data, config)
        elif template_name == "makerspace":
            if not config:
                raise ValueError("Makerspace template requires config file")
            context = self.process_makerspace_data(data, config)
        else:
            raise ValueError(f"Unknown template: {template_name}")

        # Render template
        template = self.jinja_env.get_template(f"{template_name}.html")
        context['asset_version'] = int(datetime.now(timezone.utc).timestamp())
        html = template.render(**context)

        # Write output
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(html)

        print(f"✓ Generated {output_file}")


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent

    # Privacy mode (enabled by default for Phase 1 - public GitHub Pages)
    # Set PRIVACY_MODE=false for Phase 2 (private on-site deployment)
    privacy_mode = os.getenv("PRIVACY_MODE", "true").lower() == "true"

    # Initialize generator
    generator = DashboardGenerator(project_root, privacy_mode=privacy_mode)

    if privacy_mode:
        print("🔒 Privacy mode ENABLED - Patron names and emails will be masked")
    else:
        print("🔓 Privacy mode DISABLED - Full patron information will be displayed")

    # Dashboard configurations: (data_file, output_file, template, config_file)
    dashboards = [
        ("docs/scott/data.json", "docs/scott/index.html", "media-lab", "config/scott-media-lab.json"),
        ("docs/markham-media/data.json", "docs/markham-media/index.html", "media-lab", "config/markham-media-lab.json"),
        ("docs/markham-makerspace/data.json", "docs/markham-makerspace/index.html", "makerspace", "config/markham-makerspace.json"),
    ]

    print(f"🎨 Generating dashboards - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    for data_file, output_file, template, config_file in dashboards:
        data_path = project_root / data_file
        output_path = project_root / output_file
        config_path = project_root / config_file if config_file else None

        if not data_path.exists():
            print(f"⚠ Skipping {data_file} (not found)")
            continue

        try:
            generator.generate_dashboard(data_path, output_path, template, config_path)
        except Exception as e:
            print(f"❌ Error generating {output_file}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    print(f"\n✅ All dashboards generated successfully")


if __name__ == "__main__":
    main()
