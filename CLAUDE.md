# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

gcal2agena is a Google Calendar to Org-Agenda Item Generator that converts Google Calendar data into Emacs Org-mode Agenda items.

## Current State

- **Status**: Early Planning
- **Main Script**: `gcal2agenda.py` - Python implementation using caldav library
- **Target**: Generate one `.org` file per month for the next 3 month from Google Calendar data
- **Output Format**: Emacs Org-Agenda compatible files (e.g., `2025-08.org`)

## Implementation Architecture

### Tech Stack
- **Python** with `caldav` library
- **CalDAV protocol** to access Google's calendar server
- Suitable python library to access Google Calendar using Application Password for Authentication
- **datetime module** for robust date/time handling

### Key Design Principles
- **Daily batch processing**: Generate 3 months ahead, removing any existing org files first
- **Proper Org-mode formatting**: 
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
- Meetings should be sorted by start time, earliest first
- Meeting times should be adjusted to Pacific Time Zone

## Implementation flow
1. Make changes to files, adding comments explaining the changes made
2. Run Python Linting on gcal2agenda.py
3. Only if gcal2agenda.py is lint clean, check in the changed files with detailed change comments

## Usage
- gcal2agenda.py should be called from a gcal2agenda.sh bash script that sets an environment variable called GCAL_APP_PASSWORD beforehand -> IMPORTANT: gcal2agenda.sh must not be checked into version control
