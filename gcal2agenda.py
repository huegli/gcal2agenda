#!/usr/bin/env python3
"""
gcal2agenda.py - Google Calendar to Org-Agenda Item Generator

Converts Google Calendar data into Emacs Org-mode Agenda items.
Generates one .org file per month for the current month + 2 future months.
"""

import os
import sys
import argparse
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import pytz

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Google Calendar API scopes - read-only access to calendar
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Pacific timezone for event time conversion
PACIFIC_TZ = pytz.timezone('America/Los_Angeles')


class CalendarAuthenticator:
    """Handles OAuth2 authentication for Google Calendar API"""
    
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.pickle'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = None
    
    def authenticate(self) -> Credentials:
        """Authenticate and return Google Calendar API credentials"""
        # Load existing token if available
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        # If there are no valid credentials, obtain new ones
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                # Refresh expired credentials
                self.creds.refresh(Request())
            else:
                # Run OAuth flow for new credentials
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"OAuth2 credentials file '{self.credentials_path}' not found. "
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save credentials for future runs
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)
        
        return self.creds


class CalendarEventFetcher:
    """Fetches and processes Google Calendar events"""
    
    def __init__(self, credentials: Credentials):
        self.service = build('calendar', 'v3', credentials=credentials)
        self.calendars_to_process = self._get_calendars_to_process()
    
    def _get_calendars_to_process(self) -> List[str]:
        """Determine which calendars to process based on environment variable"""
        calendar_names = os.environ.get('GCAL_CALENDARS', '').strip()
        
        if not calendar_names:
            # Use primary calendar
            return ['primary']
        
        # Split calendar names by "|" and clean them
        calendar_list = [name.strip() for name in calendar_names.split('|') if name.strip()]
        return calendar_list if calendar_list else ['primary']
    
    def _get_calendar_id(self, calendar_name: str) -> Optional[str]:
        """Get calendar ID from calendar name or return primary if it's 'primary'"""
        if calendar_name == 'primary':
            return 'primary'
        
        try:
            # List all calendars to find matching name
            calendar_list = self.service.calendarList().list().execute()
            
            for calendar_entry in calendar_list.get('items', []):
                if calendar_entry.get('summary', '').lower() == calendar_name.lower():
                    return calendar_entry['id']
            
            print(f"Warning: Calendar '{calendar_name}' not found. Skipping.")
            return None
            
        except HttpError as error:
            print(f"Error accessing calendar list: {error}")
            return None
    
    def fetch_events_for_period(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch events for the specified time period from all configured calendars"""
        all_events = []
        
        for calendar_name in self.calendars_to_process:
            calendar_id = self._get_calendar_id(calendar_name)
            if not calendar_id:
                continue
            
            try:
                # Convert dates to RFC3339 format for API
                time_min = start_date.isoformat() + 'Z'
                time_max = end_date.isoformat() + 'Z'
                
                # Fetch events from the calendar
                events_result = self.service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=2500,
                    singleEvents=True,  # Expand recurring events
                    orderBy='startTime',
                    showDeleted=False  # Exclude cancelled events
                ).execute()
                
                events = events_result.get('items', [])
                
                # Filter out cancelled events (additional safety check)
                filtered_events = [
                    event for event in events 
                    if event.get('status', '').lower() != 'cancelled'
                ]
                
                all_events.extend(filtered_events)
                print(f"Fetched {len(filtered_events)} events from calendar: {calendar_name}")
                
            except HttpError as error:
                print(f"Error fetching events from calendar '{calendar_name}': {error}")
                continue
        
        # Sort all events by start time
        all_events.sort(key=lambda x: self._get_event_start_time(x))
        
        return all_events
    
    def _get_event_start_time(self, event: Dict) -> datetime:
        """Extract start time from event, handling both datetime and date formats"""
        start = event.get('start', {})
        
        if 'dateTime' in start:
            # Timed event
            return datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
        elif 'date' in start:
            # All-day event
            return datetime.fromisoformat(start['date'] + 'T00:00:00+00:00')
        else:
            # Fallback to epoch
            return datetime.fromtimestamp(0, tz=pytz.UTC)


class OrgModeFormatter:
    """Formats calendar events into Org-mode agenda items"""
    
    def __init__(self):
        self.pacific_tz = PACIFIC_TZ
    
    def format_events_for_month(self, events: List[Dict], year: int, month: int) -> str:
        """Format events for a specific month into Org-mode format"""
        # Filter events for the specific month
        month_events = []
        for event in events:
            event_start = self._get_event_start_time(event)
            event_start_pacific = event_start.astimezone(self.pacific_tz)
            
            if event_start_pacific.year == year and event_start_pacific.month == month:
                month_events.append(event)
        
        # Generate Org-mode content
        month_name = datetime(year, month, 1).strftime('%Y-%m')
        content_lines = [f'#+title: {month_name}', '']
        
        for event in month_events:
            org_entry = self._format_single_event(event)
            if org_entry:
                content_lines.append(org_entry)
        
        return '\n'.join(content_lines)
    
    def _format_single_event(self, event: Dict) -> Optional[str]:
        """Format a single event into Org-mode entry"""
        title = event.get('summary', 'No Title').strip()
        if not title:
            title = 'No Title'
        
        # Get event start time
        start = event.get('start', {})
        end = event.get('end', {})
        
        if 'dateTime' in start and 'dateTime' in end:
            # Timed event
            start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            
            # Convert to Pacific Time
            start_pacific = start_dt.astimezone(self.pacific_tz)
            end_pacific = end_dt.astimezone(self.pacific_tz)
            
            # Format time range
            time_str = self._format_time_range(start_pacific, end_pacific)
            
        elif 'date' in start:
            # All-day event - convert to 6:00-6:30 AM as specified
            start_date = datetime.fromisoformat(start['date'] + 'T00:00:00')
            start_pacific = self.pacific_tz.localize(start_date.replace(hour=6, minute=0))
            end_pacific = self.pacific_tz.localize(start_date.replace(hour=6, minute=30))
            
            # Format time range
            time_str = self._format_time_range(start_pacific, end_pacific)
        else:
            # Fallback - skip events without proper time info
            return None
        
        return f'* {title}\n{time_str}'
    
    def _format_time_range(self, start_dt: datetime, end_dt: datetime) -> str:
        """Format datetime range into Org-mode timestamp format"""
        # Format: <2025-08-27 Tue 9:00-10:00>
        day_name = start_dt.strftime('%a')
        date_str = start_dt.strftime('%Y-%m-%d')
        start_time = start_dt.strftime('%H:%M')
        end_time = end_dt.strftime('%H:%M')
        
        return f'<{date_str} {day_name} {start_time}-{end_time}>'
    
    def _get_event_start_time(self, event: Dict) -> datetime:
        """Extract start time from event, handling both datetime and date formats"""
        start = event.get('start', {})
        
        if 'dateTime' in start:
            return datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
        elif 'date' in start:
            return datetime.fromisoformat(start['date'] + 'T00:00:00+00:00')
        else:
            return datetime.fromtimestamp(0, tz=pytz.UTC)


class OrgFileManager:
    """Manages creation and cleanup of Org-mode files"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def cleanup_existing_files(self, year_month_list: List[str]):
        """Remove existing monthly org files before generating new ones"""
        for year_month in year_month_list:
            file_path = self.output_dir / f'{year_month}.org'
            if file_path.exists():
                file_path.unlink()
                print(f"Removed existing file: {file_path}")
    
    def write_monthly_file(self, year_month: str, content: str):
        """Write Org-mode content to monthly file"""
        file_path = self.output_dir / f'{year_month}.org'
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Generated: {file_path}")


def get_month_range() -> List[tuple]:
    """Get list of (year, month) tuples for current + 2 future months"""
    now = datetime.now()
    months = []
    
    for i in range(3):  # Current month + 2 future months
        target_date = now.replace(day=1) + timedelta(days=32 * i)
        target_date = target_date.replace(day=1)  # First day of month
        months.append((target_date.year, target_date.month))
    
    return months


def main():
    """Main function to orchestrate the calendar to org-mode conversion"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert Google Calendar events to Org-mode agenda items')
    parser.add_argument(
        '--output-dir', 
        default='.',
        help='Directory to save .org files (default: current directory)'
    )
    parser.add_argument(
        '--credentials', 
        default='credentials.json',
        help='Path to OAuth2 credentials file (default: credentials.json)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize components
        print("Authenticating with Google Calendar...")
        authenticator = CalendarAuthenticator(credentials_path=args.credentials)
        credentials = authenticator.authenticate()
        
        print("Initializing calendar access...")
        event_fetcher = CalendarEventFetcher(credentials)
        formatter = OrgModeFormatter()
        file_manager = OrgFileManager(args.output_dir)
        
        # Get month range
        months = get_month_range()
        year_months = [f"{year:04d}-{month:02d}" for year, month in months]
        
        print(f"Processing months: {', '.join(year_months)}")
        
        # Cleanup existing files
        file_manager.cleanup_existing_files(year_months)
        
        # Calculate date range for API call
        first_month = datetime(months[0][0], months[0][1], 1)
        last_month = datetime(months[-1][0], months[-1][1], 1)
        
        # Get last day of last month
        if last_month.month == 12:
            next_month = last_month.replace(year=last_month.year + 1, month=1)
        else:
            next_month = last_month.replace(month=last_month.month + 1)
        
        end_date = next_month - timedelta(days=1)
        end_date = end_date.replace(hour=23, minute=59, second=59)
        
        print(f"Fetching events from {first_month.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
        
        # Fetch events for the entire period
        all_events = event_fetcher.fetch_events_for_period(first_month, end_date)
        
        print(f"Total events fetched: {len(all_events)}")
        
        # Generate files for each month
        for year, month in months:
            year_month = f"{year:04d}-{month:02d}"
            print(f"Generating {year_month}.org...")
            
            content = formatter.format_events_for_month(all_events, year, month)
            file_manager.write_monthly_file(year_month, content)
        
        print("✅ Calendar conversion completed successfully!")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nTo set up OAuth2 authentication:")
        print("1. Go to Google Cloud Console (console.cloud.google.com)")
        print("2. Create a project and enable Google Calendar API")
        print("3. Create OAuth2 credentials (Desktop application)")
        print("4. Download credentials.json file to this directory")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()