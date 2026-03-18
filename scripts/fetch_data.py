#!/usr/bin/env python3
"""
MMCL Dashboard Data Fetcher
Fetches booking data from LibCal API for all three dashboard instances.
"""

import os
import json
import sys
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from pathlib import Path

import requests
from dotenv import load_dotenv


class LibCalClient:
    """LibCal API client with OAuth 2.0 authentication."""

    BASE_URL = "https://yorku.libcal.com/1.1"
    TOKEN_URL = "https://yorku.libcal.com/1.1/oauth/token"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

    def authenticate(self) -> None:
        """Obtain OAuth 2.0 access token using client credentials grant."""
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }

        response = requests.post(self.TOKEN_URL, data=payload)
        response.raise_for_status()

        data = response.json()
        self.access_token = data["access_token"]
        # Token typically expires in 3600 seconds (1 hour)
        expires_in = data.get("expires_in", 3600)
        print(f"✓ Authenticated with LibCal API (token expires in {expires_in}s)")

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        if not self.access_token:
            self.authenticate()

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authorization."""
        self._ensure_authenticated()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }

    def _fetch_paginated(self, endpoint: str, params: Dict[str, Any]) -> List[Dict]:
        """
        Fetch all results from a paginated endpoint.
        LibCal has a hard limit of 500 records per call.
        """
        all_results = []
        page = 1

        while True:
            paginated_params = {**params, "page": page, "limit": 500}
            url = f"{self.BASE_URL}/{endpoint}"

            response = requests.get(url, headers=self._get_headers(), params=paginated_params)
            response.raise_for_status()

            data = response.json()

            # Handle different response structures
            if isinstance(data, list):
                results = data
            elif isinstance(data, dict):
                # Some endpoints wrap results in a key
                results = data.get("bookings", data.get("appointments", data.get("items", [])))
            else:
                results = []

            if not results:
                break

            all_results.extend(results)

            # If we got fewer than 500 results, we've reached the end
            if len(results) < 500:
                break

            page += 1

        return all_results

    def fetch_space_bookings(self, location_id: int, start_date: str, end_date: str) -> List[Dict]:
        """Fetch space bookings for a location."""
        endpoint = "space/bookings"
        params = {
            "lid": location_id,
            "date": start_date,  # YYYY-MM-DD format
            "days": 1  # Fetch only the specified day
        }

        results = self._fetch_paginated(endpoint, params)
        print(f"  → Fetched {len(results)} space bookings for lid={location_id}")
        return results

    def fetch_equipment_bookings(self, location_id: int, start_date: str, end_date: str) -> List[Dict]:
        """Fetch equipment bookings for a location."""
        endpoint = "equipment/bookings"
        params = {
            "lid": location_id,
            "date": start_date,
            "days": 1
        }

        results = self._fetch_paginated(endpoint, params)
        print(f"  → Fetched {len(results)} equipment bookings for lid={location_id}")
        return results

    def fetch_appointments(self, group_id: int, start_date: str, end_date: str) -> List[Dict]:
        """Fetch appointments for a group."""
        endpoint = "appointments/bookings"
        params = {
            "gid": group_id,
            "date": start_date,
            "days": 1
        }

        try:
            results = self._fetch_paginated(endpoint, params)
            print(f"  → Fetched {len(results)} appointments for gid={group_id}")
            return results
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"  ⚠ Appointments API returned 403 for gid={group_id} (missing ap_r scope)")
                return []
            raise


def load_config(config_path: Path) -> Dict:
    """Load a dashboard configuration file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def get_today_date() -> str:
    """Get today's date in YYYY-MM-DD format."""
    return date.today().isoformat()


def fetch_dashboard_data(client: LibCalClient, config: Dict, config_name: str) -> Dict:
    """
    Fetch all data for a single dashboard instance.
    Returns a dictionary ready to be saved as data.json.
    """
    location_id = config["location_id"]
    location_name = config["location_name"]
    template = config["template"]
    today = get_today_date()

    print(f"\n📊 Fetching data for {location_name} (template: {template})")

    result = {
        "location_id": location_id,
        "location_name": location_name,
        "template": template,
        "shift_boundary": config.get("shift_boundary"),
        "fetch_timestamp": datetime.now().isoformat(),
        "date": today,
        "space_bookings": [],
        "equipment_bookings": [],
        "appointments": [],
        "teaching_events": []
    }

    # Fetch space bookings (all dashboards)
    result["space_bookings"] = client.fetch_space_bookings(location_id, today, today)

    # Media Lab dashboards: fetch equipment bookings
    if template == "media-lab":
        result["equipment_bookings"] = client.fetch_equipment_bookings(location_id, today, today)

        # Scott Media Lab: fetch teaching events from separate location
        if "teaching_events" in config and config["teaching_events"].get("enabled"):
            teaching_lid = config["teaching_events"]["location_id"]
            print(f"  → Fetching teaching events from lid={teaching_lid}")
            result["teaching_events"] = client.fetch_space_bookings(teaching_lid, today, today)

    # Makerspace dashboard: fetch appointments (if enabled)
    if template == "makerspace":
        appointments_config = config.get("appointments", {})
        if appointments_config.get("enabled"):
            for group in appointments_config.get("groups", []):
                group_id = group["group_id"]
                group_name = group["name"]
                print(f"  → Fetching appointments for {group_name} (gid={group_id})")
                group_appointments = client.fetch_appointments(group_id, today, today)

                # Tag appointments with their group info
                for appt in group_appointments:
                    appt["_group_id"] = group_id
                    appt["_group_name"] = group_name
                    appt["_workflow"] = group.get("workflow")

                result["appointments"].extend(group_appointments)
        else:
            print(f"  ⚠ Appointments disabled in config (awaiting API key with ap_r scope)")

    return result


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()

    client_id = os.getenv("LIBCAL_CLIENT_ID")
    client_secret = os.getenv("LIBCAL_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("❌ Error: LIBCAL_CLIENT_ID and LIBCAL_CLIENT_SECRET must be set in .env file")
        sys.exit(1)

    # Initialize LibCal client
    client = LibCalClient(client_id, client_secret)

    # Project root directory
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"
    docs_dir = project_root / "docs"

    # Dashboard configurations
    dashboards = [
        ("scott-media-lab.json", "scott"),
        ("markham-media-lab.json", "markham-media"),
        ("markham-makerspace.json", "markham-makerspace")
    ]

    print(f"🚀 MMCL Dashboard Data Fetch - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    for config_file, output_dir in dashboards:
        config_path = config_dir / config_file
        output_path = docs_dir / output_dir / "data.json"

        # Load config
        config = load_config(config_path)

        # Fetch data
        data = fetch_dashboard_data(client, config, config_file)

        # Save to JSON
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Saved to {output_path}")

    print(f"\n✅ All dashboard data fetched successfully")


if __name__ == "__main__":
    main()
