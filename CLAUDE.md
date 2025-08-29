# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

gcal2agena is a Google Calendar to Org-Agenda Item Generator that converts Google Calendar data into Emacs Org-mode Agenda items.

## Current State

- **Status**: Implemented ✅
- **Main Script**: `gcal2agenda.py` - Python implementation using Google Calendar API
- **Target**: Generate one `.org` file per month for the current month + 2 future months from Google Calendar data
- **Output Format**: Emacs Org-Agenda compatible files (e.g., `2025-08.org`)
- **Dependencies**: See `requirements.txt` for required Python packages

## Implementation Architecture

### Tech Stack
- **Python** with Google Calendar API
- **OAuth 2.0** for secure authentication (no more app passwords needed)
- **Google API Client Libraries** for calendar access
- **datetime module** and **pytz** for robust date/time handling

### Key Design Principles
- **Daily batch processing**: Generate current month + 2 future months, removing only the 3 generated monthly org files first
- **Proper Org-mode formatting**: Include only title and time for events
- **Cron-friendly**: Designed for automated daily execution

## File Structure (When Implemented)

Expected output structure:
```
#+title: <DATE-STAMP>

* Event A
<2025-08-27 Tue 9:00-10:00>
* Event B
<2025-08-28 Wed 10:00-11:00>
...
x```
- Events should be sorted by start time, earliest first
- Event times should be adjusted to Pacific Time Zone
- All-day events should be handled as timed events from 6:00-6:30 AM
- Include all instances of recurring events within the 3-month window
- Cancelled events should not be listed

## Implementation flow
1. Make changes to files, adding comments explaining the changes made
2. Run Python Linting on gcal2agenda.py
3. Only if gcal2agenda.py is lint clean, check in the changed files with detailed change comments

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Google Cloud Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing project
3. Enable the Google Calendar API
4. Create OAuth 2.0 credentials:
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download the credentials file as `credentials.json`
5. Place `credentials.json` in the same directory as `gcal2agenda.py`

### 3. First Run
On the first run, the script will:
1. Open your browser for OAuth authentication
2. Save authentication tokens to `token.pickle` for future runs
3. Generate `.org` files for the current and next 2 months

## Usage & Environment Variables
- **Optional Environment Variable**: GCAL_CALENDARS (calendar names separated by "|", defaults to primary calendar)
- **Command Line Options**: 
  - `--output-dir`: Directory for .org files (defaults to current directory)
  - `--credentials`: Path to OAuth2 credentials file (defaults to credentials.json)
- **Calendar Selection**: Uses primary calendar unless GCAL_CALENDARS environment variable specifies one or more calendar names

### Example Usage
```bash
# Basic usage (primary calendar, current directory)
python gcal2agenda.py

# Specify output directory
python gcal2agenda.py --output-dir ~/org-agenda

# Use specific calendars
GCAL_CALENDARS="Work|Personal" python gcal2agenda.py

# Custom credentials file
python gcal2agenda.py --credentials /path/to/my-credentials.json
```
