#!/usr/bin/env python3
"""
MMCL Dashboard Generator
Renders data.json files into HTML dashboards using Jinja2 templates.
"""

import os
import json
import sys
import re
from datetime import datetime, date, time, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

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
        if "confirmed" in status_lower or "self-booked" in status_lower:
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

    def get_workflow_for_booking(self, booking: Dict, booking_type: str) -> Optional[Dict]:
        """Get workflow data for a booking if applicable."""
        # Equipment loans always use equipment-loan workflow
        if booking_type == "equipment":
            workflow_id = "equipment-loan"
            workflow = self.workflows.get(workflow_id)
            if workflow:
                # Determine phase (checkout or return) based on time
                # For Phase 1, we show checkout steps by default
                return {
                    "type": "equipment-loan",
                    "phase_name": "Equipment Checkout",
                    "steps": [
                        {"number": step["step"], "description": step["description"]}
                        for step in workflow["phases"]["checkout"]["steps"]
                    ]
                }
        return None

    def calculate_timeline(self, bookings: List[Dict], today: date) -> List[Dict]:
        """Calculate hourly concurrent booking counts for timeline."""
        # Operating hours: 8 AM - 9 PM (13 hours)
        hours = list(range(8, 22))  # 8-21 (8 AM - 9 PM)
        hour_counts = {hour: 0 for hour in hours}

        # Count concurrent bookings for each hour
        for booking in bookings:
            from_dt = self.parse_datetime(booking["fromDate"])
            to_dt = self.parse_datetime(booking["toDate"])

            # Only count bookings happening today
            if from_dt.date() != today and to_dt.date() != today:
                continue

            # Skip cancelled bookings
            if "cancelled" in booking:
                continue

            # Count which hours this booking overlaps
            for hour in hours:
                # Make timezone-aware to match booking datetimes
                hour_start = datetime.combine(today, time(hour, 0)).replace(tzinfo=from_dt.tzinfo)
                hour_end = datetime.combine(today, time(hour + 1, 0)).replace(tzinfo=from_dt.tzinfo)

                # Check if booking overlaps this hour
                if from_dt < hour_end and to_dt > hour_start:
                    hour_counts[hour] += 1

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

    def process_media_lab_data(self, data: Dict) -> Dict:
        """Process data for media lab dashboard."""
        today = datetime.fromisoformat(data["date"]).date()
        shift_boundary = data.get("shift_boundary")
        location_name = data["location_name"]

        # All bookings (space + equipment + teaching)
        all_space_bookings = data.get("space_bookings", [])
        all_equipment_bookings = data.get("equipment_bookings", [])
        teaching_events = data.get("teaching_events", [])

        # Filter for today's bookings (not cancelled)
        def is_valid_today_booking(booking):
            if "cancelled" in booking:
                return False
            return (self.is_today(booking["fromDate"], today) or
                    self.is_today(booking["toDate"], today))

        space_bookings = [b for b in all_space_bookings if is_valid_today_booking(b)]
        equipment_bookings = [b for b in all_equipment_bookings if is_valid_today_booking(b)]
        teaching_bookings = [b for b in teaching_events if is_valid_today_booking(b)]

        # Find overdue equipment
        now = datetime.now(timezone.utc)
        overdue_equipment = [
            b for b in all_equipment_bookings
            if self.parse_datetime(b["toDate"]) < now and "cancelled" not in b
               and b.get("status", "").lower() not in ["completed", "returned"]
        ]

        # Find completed today
        completed_bookings = [
            b for b in all_space_bookings + all_equipment_bookings
            if is_valid_today_booking(b) and b.get("status", "").lower() in ["completed", "returned"]
        ]

        # Group bookings by shift
        shifts_data = {}
        for shift_name in (["Opening Shift", "Closing Shift"] if shift_boundary else ["Full Shift"]):
            shifts_data[shift_name] = {
                "space": [],
                "equipment": [],
                "teaching": []
            }

        # Categorize space bookings
        for booking in space_bookings:
            shift = self.get_shift_group(booking["fromDate"], shift_boundary)
            shifts_data[shift]["space"].append(self._format_space_booking(booking, shift_boundary))

        # Categorize equipment bookings
        for booking in equipment_bookings:
            shift = self.get_shift_group(booking["fromDate"], shift_boundary)
            shifts_data[shift]["equipment"].append(self._format_equipment_booking(booking, shift_boundary))

        # Categorize teaching events
        for booking in teaching_bookings:
            shift = self.get_shift_group(booking["fromDate"], shift_boundary)
            shifts_data[shift]["teaching"].append(self._format_teaching_booking(booking, shift_boundary))

        # Combine and sort bookings within each shift
        shifts = []
        for shift_name, shift_bookings in shifts_data.items():
            all_shift_bookings = (
                shift_bookings["space"] +
                shift_bookings["equipment"] +
                shift_bookings["teaching"]
            )

            # Sort by start time
            all_shift_bookings.sort(key=lambda b: b["from_datetime"])

            shifts.append({
                "name": shift_name,
                "space_count": len(shift_bookings["space"]),
                "equipment_count": len(shift_bookings["equipment"]),
                "teaching_count": len(shift_bookings["teaching"]),
                "bookings": all_shift_bookings
            })

        # Calculate timeline
        timeline = self.calculate_timeline(
            space_bookings + equipment_bookings + teaching_bookings,
            today
        )

        # Format overdue items
        overdue_items = [self._format_overdue_item(item, now) for item in overdue_equipment]

        # Format completed items
        completed_items = [self._format_completed_item(item) for item in completed_bookings]

        # Determine shift label for header
        shift_label = None
        if shift_boundary:
            current_time = datetime.now().time()
            boundary_time = datetime.strptime(shift_boundary, "%H:%M").time()
            shift_label = "Opening Shift" if current_time < boundary_time else "Closing Shift"

        return {
            "location_name": location_name,
            "current_date": self.format_date(today),
            "last_updated": datetime.now().strftime("%I:%M %p"),
            "shift_label": shift_label,
            "timeline": timeline,
            "shifts": shifts,
            "overdue_items": overdue_items,
            "completed_items": completed_items,
            "warnings": []  # For Phase 2: conflict detection
        }

    def _format_space_booking(self, booking: Dict, shift_boundary: Optional[str]) -> Dict:
        """Format a space booking for display."""
        from_dt = self.parse_datetime(booking["fromDate"])
        to_dt = self.parse_datetime(booking["toDate"])

        return {
            "booking_id": booking.get("bookId", "N/A"),
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
            "card_class": "",
            "is_teaching_event": False,
            "spans_shift_boundary": self.spans_shift_boundary(booking["fromDate"], booking["toDate"], shift_boundary),
            "equipment_indicator": None,
            "workflow": None,
            "group_name": None
        }

    def _format_equipment_booking(self, booking: Dict, shift_boundary: Optional[str]) -> Dict:
        """Format an equipment booking for display."""
        from_dt = self.parse_datetime(booking["fromDate"])
        to_dt = self.parse_datetime(booking["toDate"])

        # Determine if this is pickup or return based on current time
        now = datetime.now(timezone.utc)
        is_pickup = from_dt > now
        is_return = to_dt < now and from_dt < now

        equipment_indicator = None
        if is_pickup:
            equipment_indicator = {"type": "pickup", "label": "📦 Pickup"}
        elif is_return:
            equipment_indicator = {"type": "return", "label": "↩️ Return"}

        return {
            "booking_id": booking.get("bookId", "N/A"),
            "title": booking.get("item_name", "Unknown Equipment"),
            "category": booking.get("category_name", "Equipment"),
            "from_time": self.format_time(from_dt),
            "to_time": self.format_time(to_dt),
            "from_datetime": from_dt,
            "patron_name": self.mask_patron_name(booking.get("firstName", ""), booking.get("lastName", "")),
            "patron_email": self.mask_patron_email(booking.get("email", "")),
            "check_in_code": booking.get("check_in_code"),
            "status_display": self.map_status_display(booking.get("status", "")),
            "status_class": self.map_status_to_class(booking.get("status", "")),
            "card_class": "equipment-loan",
            "is_teaching_event": False,
            "spans_shift_boundary": self.spans_shift_boundary(booking["fromDate"], booking["toDate"], shift_boundary),
            "equipment_indicator": equipment_indicator,
            "workflow": self.get_workflow_for_booking(booking, "equipment"),
            "group_name": booking.get("groupName")
        }

    def _format_teaching_booking(self, booking: Dict, shift_boundary: Optional[str]) -> Dict:
        """Format a teaching event for display."""
        from_dt = self.parse_datetime(booking["fromDate"])
        to_dt = self.parse_datetime(booking["toDate"])

        return {
            "booking_id": booking.get("bookId", "N/A"),
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
            "patron_name": f"{booking.get('firstName', '')} {booking.get('lastName', '')}".strip()
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
        """Process data for makerspace dashboard."""
        today = datetime.fromisoformat(data["date"]).date()
        shift_boundary = data.get("shift_boundary")
        location_name = data["location_name"]

        # All space bookings (workstations)
        all_space_bookings = data.get("space_bookings", [])
        all_appointments = data.get("appointments", [])

        # Filter for today's bookings (not cancelled)
        def is_valid_today_booking(booking):
            if "cancelled" in booking:
                return False
            return (self.is_today(booking["fromDate"], today) or
                    self.is_today(booking["toDate"], today))

        # Separate in-progress jobs (started before today, end today or later)
        def is_in_progress(booking):
            if "cancelled" in booking:
                return False
            from_dt = self.parse_datetime(booking["fromDate"])
            to_dt = self.parse_datetime(booking["toDate"])
            return from_dt.date() < today and to_dt.date() >= today

        today_bookings = [b for b in all_space_bookings if is_valid_today_booking(b) and not is_in_progress(b)]
        in_progress_bookings = [b for b in all_space_bookings if is_in_progress(b)]
        today_appointments = [a for a in all_appointments if is_valid_today_booking(a)]

        # Find completed bookings
        completed_bookings = [
            b for b in all_space_bookings
            if is_valid_today_booking(b) and b.get("status", "").lower() in ["completed", "returned"]
        ]

        # Group bookings by shift
        shifts_data = {}
        for shift_name in (["Opening Shift", "Closing Shift"] if shift_boundary else ["Full Shift"]):
            shifts_data[shift_name] = {
                "workstations": [],
                "appointments": [],
                "teaching": []
            }

        # Categorize workstation bookings
        for booking in today_bookings:
            shift = self.get_shift_group(booking["fromDate"], shift_boundary)

            # Check if this is a teaching event
            if booking.get("category_name") == "Makerspace Room":
                shifts_data[shift]["teaching"].append(self._format_teaching_booking(booking, shift_boundary))
            else:
                # Assign workflow
                workflow_id = self.assign_workflow_to_workstation(booking, config)
                shifts_data[shift]["workstations"].append(
                    self._format_workstation_booking(booking, shift_boundary, workflow_id)
                )

        # Categorize appointments
        for appointment in today_appointments:
            shift = self.get_shift_group(appointment["fromDate"], shift_boundary)
            shifts_data[shift]["appointments"].append(
                self._format_appointment_booking(appointment, shift_boundary)
            )

        # Combine and sort bookings within each shift
        shifts = []
        for shift_name, shift_bookings in shifts_data.items():
            all_shift_bookings = (
                shift_bookings["workstations"] +
                shift_bookings["appointments"] +
                shift_bookings["teaching"]
            )

            # Sort by start time
            all_shift_bookings.sort(key=lambda b: b["from_datetime"])

            shifts.append({
                "name": shift_name,
                "workstation_count": len(shift_bookings["workstations"]),
                "appointment_count": len(shift_bookings["appointments"]),
                "teaching_count": len(shift_bookings["teaching"]),
                "bookings": all_shift_bookings
            })

        # Calculate timeline
        timeline = self.calculate_timeline(
            today_bookings + today_appointments,
            today
        )

        # Format in-progress jobs
        in_progress_jobs = [
            self._format_in_progress_job(job, today, config)
            for job in in_progress_bookings
        ]

        # Format completed items
        completed_items = [self._format_completed_item(item) for item in completed_bookings]

        # Determine shift label
        shift_label = None
        if shift_boundary:
            current_time = datetime.now().time()
            boundary_time = datetime.strptime(shift_boundary, "%H:%M").time()
            shift_label = "Opening Shift" if current_time < boundary_time else "Closing Shift"

        # Check for laser cutter conflicts (if appointments enabled and conflict detection enabled)
        warnings = []
        if config.get("appointments", {}).get("enabled"):
            for group in config.get("appointments", {}).get("groups", []):
                if group.get("conflict_detection", {}).get("enabled"):
                    # Phase 2: Implement conflict detection logic
                    pass

        return {
            "location_name": location_name,
            "current_date": self.format_date(today),
            "last_updated": datetime.now().strftime("%I:%M %p"),
            "shift_label": shift_label,
            "timeline": timeline,
            "shifts": shifts,
            "in_progress_jobs": in_progress_jobs,
            "completed_items": completed_items,
            "warnings": warnings
        }

    def _format_workstation_booking(self, booking: Dict, shift_boundary: Optional[str], workflow_id: Optional[str]) -> Dict:
        """Format a workstation booking for display."""
        from_dt = self.parse_datetime(booking["fromDate"])
        to_dt = self.parse_datetime(booking["toDate"])

        # Calculate duration
        duration_hours = (to_dt - from_dt).total_seconds() / 3600
        duration_str = f"{duration_hours:.1f} hours" if duration_hours >= 1 else f"{int(duration_hours * 60)} minutes"

        # Load workflow if assigned
        workflow_data = None
        if workflow_id and workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            workflow_data = {
                "name": workflow["name"],
                "step_count": len(workflow["steps"]),
                "safety_critical": workflow.get("safety_critical", False),
                "patron_operated": workflow.get("patron_operated", True),
                "steps": [
                    {
                        "number": step["step"],
                        "description": step["description"],
                        "type": step["type"],
                        "safety_required": step.get("safety_required", False)
                    }
                    for step in workflow["steps"]
                ]
            }

        return {
            "booking_id": booking.get("bookId", "N/A"),
            "title": booking.get("item_name", "Unknown Workstation"),
            "category": booking.get("category_name", "Workstation"),
            "from_time": self.format_time(from_dt),
            "to_time": self.format_time(to_dt),
            "from_datetime": from_dt,
            "patron_name": self.mask_patron_name(booking.get("firstName", ""), booking.get("lastName", "")),
            "patron_email": self.mask_patron_email(booking.get("email", "")),
            "check_in_code": booking.get("check_in_code"),
            "status_display": self.map_status_display(booking.get("status", "")),
            "status_class": self.map_status_to_class(booking.get("status", "")),
            "card_class": "workstation",
            "is_teaching_event": False,
            "is_appointment": False,
            "spans_shift_boundary": self.spans_shift_boundary(booking["fromDate"], booking["toDate"], shift_boundary),
            "duration_hours": duration_str,
            "workflow": workflow_data,
            "staff_name": None
        }

    def _format_appointment_booking(self, appointment: Dict, shift_boundary: Optional[str]) -> Dict:
        """Format an appointment booking for display."""
        from_dt = self.parse_datetime(appointment["fromDate"])
        to_dt = self.parse_datetime(appointment["toDate"])

        # Get workflow from appointment metadata
        workflow_id = appointment.get("_workflow")
        workflow_data = None
        if workflow_id and workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            workflow_data = {
                "name": workflow["name"],
                "step_count": len(workflow["steps"]),
                "safety_critical": workflow.get("safety_critical", False),
                "patron_operated": workflow.get("patron_operated", True),
                "steps": [
                    {
                        "number": step["step"],
                        "description": step["description"],
                        "type": step["type"],
                        "safety_required": step.get("safety_required", False)
                    }
                    for step in workflow["steps"]
                ]
            }

        return {
            "booking_id": appointment.get("bookId", "N/A"),
            "title": appointment.get("_group_name", "Appointment"),
            "category": "Appointment",
            "from_time": self.format_time(from_dt),
            "to_time": self.format_time(to_dt),
            "from_datetime": from_dt,
            "patron_name": f"{appointment.get('firstName', '')} {appointment.get('lastName', '')}".strip(),
            "patron_email": appointment.get("email", ""),
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

        # Assign workflow
        workflow_id = self.assign_workflow_to_workstation(booking, config)
        workflow_data = None
        if workflow_id and workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            workflow_data = {
                "name": workflow["name"],
                "step_count": len(workflow["steps"])
            }

        return {
            "booking_id": booking.get("bookId", "N/A"),
            "title": booking.get("item_name", "Unknown"),
            "category": booking.get("category_name", "Workstation"),
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
            context = self.process_media_lab_data(data)
        elif template_name == "makerspace":
            if not config:
                raise ValueError("Makerspace template requires config file")
            context = self.process_makerspace_data(data, config)
        else:
            raise ValueError(f"Unknown template: {template_name}")

        # Render template
        template = self.jinja_env.get_template(f"{template_name}.html")
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
        ("docs/scott/data.json", "docs/scott/index.html", "media-lab", None),
        ("docs/markham-media/data.json", "docs/markham-media/index.html", "media-lab", None),
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
