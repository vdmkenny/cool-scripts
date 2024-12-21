#!/usr/bin/env python3

import sys
import requests
from ics import Calendar
from datetime import datetime, timezone
import yaml
from tzlocal import get_localzone
from zoneinfo import ZoneInfo
import argparse

# Constants for Unicode checkboxes
EMPTY_CHECKBOX = '☐'  # Outlined square

# Configure the maximum line width based on your receipt printer's specifications
MAX_LINE_WIDTH = 40  # Adjust as necessary

def load_config(config_path):
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except FileNotFoundError:
        print(f"Configuration file '{config_path}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        sys.exit(1)

def fetch_ics(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching iCal data from {url}: {e}")
        return None  # Return None to skip this calendar

def parse_events(ics_content, target_date, tz):
    try:
        cal = Calendar(ics_content)
    except Exception as e:
        print(f"Error parsing iCal data: {e}")
        return [], []

    timed_events = []
    all_day_tasks = []
    for event in cal.events:
        # Check if the event is on the target date
        if event.begin.date() != target_date:
            continue  # Skip events not on the target date

        if event.all_day:
            event_name = event.name.strip() if event.name else "No Title"
            # For all-day tasks, description and location are optional
            description = event.description.strip() if event.description and event.description.strip() else None
            location = event.location.strip() if event.location and event.location.strip() else None
            all_day_tasks.append({
                "name": event_name,
                "description": description,
                "location": location
            })
        else:
            # Convert event begin time to the specified timezone
            event_begin = event.begin.to(tz)
            event_time = event_begin.strftime('%H:%M')
            event_name = event.name.strip() if event.name else "No Title"
            # Description and location are optional
            description = event.description.strip() if event.description and event.description.strip() else None
            location = event.location.strip() if event.location and event.location.strip() else None
            timed_events.append({
                "time": event_time,
                "name": event_name,
                "description": description,
                "location": location
            })
    return timed_events, all_day_tasks

def format_event(event, show_description, show_location):
    """
    Formats a single event or task into a receipt-friendly string.
    """
    lines = []
    checkbox = EMPTY_CHECKBOX
    if 'time' in event:
        # Timed Event
        first_line = f"  {checkbox} {event['time']} - {event['name']}"
    else:
        # All-Day Task
        first_line = f"  {checkbox} {event['name']}"
    lines.append(first_line)

    # Add Description if available and configured
    if show_description and event.get('description'):
        lines.append(f"    Description: {event['description']}")  # Indent by 4 spaces

    # Add Location if available and configured
    if show_location and event.get('location'):
        lines.append(f"    Location: {event['location']}")  # Indent by 4 spaces

    return "\n".join(lines)

def format_header(target_date):
    """
    Formats the header with the agenda date.
    """
    # Format the date in a readable format, e.g., April 27, 2024
    formatted_date = target_date.strftime('%B %d, %Y')
    header_title = f"Agenda for {formatted_date}"
    header_underline = "=" * len(header_title)
    return f"{header_title}\n{header_underline}\n"  # Added newline after underline

def main():
    parser = argparse.ArgumentParser(description="Fetch and display today's calendar events and tasks from multiple iCal links.")
    parser.add_argument('-c', '--config', type=str, default='calendars.yaml', help='Path to YAML configuration file.')
    parser.add_argument('-d', '--date', type=str, default=None, help='Date to fetch events for (YYYY-MM-DD). Defaults to today.')
    args = parser.parse_args()

    config = load_config(args.config)

    # Determine timezone
    if 'timezone' in config and config['timezone']:
        try:
            tz = ZoneInfo(config['timezone'])
        except Exception as e:
            print(f"Invalid timezone '{config['timezone']}' in config file: {e}")
            sys.exit(1)
    else:
        # Use system's local timezone
        try:
            local_tz = get_localzone()
            tz = ZoneInfo(str(local_tz))
        except Exception as e:
            print(f"Error determining system's local timezone: {e}")
            tz = timezone.utc  # Fallback to UTC

    # Determine target date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        target_date = datetime.now(tz).date()

    # Prepare the header
    header = format_header(target_date)

    # Process each calendar
    calendars = config.get('calendars', [])
    if not calendars:
        print("No calendars found in the configuration.")
        sys.exit(1)

    output_lines = [header, ""]  # Added a blank line after the header
    for cal in calendars:
        name = cal.get('name')
        url = cal.get('url')
        show_description = cal.get('show_description', False)
        show_location = cal.get('show_location', False)

        if not name or not url:
            print(f"Skipping a calendar entry due to missing 'name' or 'url': {cal}")
            continue

        ics_content = fetch_ics(url)
        if not ics_content:
            continue  # Skip this calendar if fetching failed

        timed_events, all_day_tasks = parse_events(ics_content, target_date, tz)

        # Determine if the calendar has content to display
        has_events = bool(timed_events) or bool(all_day_tasks)
        if not has_events:
            continue  # Skip displaying this calendar if no relevant items today

        # Add calendar name as a header
        output_lines.append(f"{name}:")
        output_lines.append("-" * len(name))  # Underline the calendar name

        # Display timed events
        if timed_events:
            for event in sorted(timed_events, key=lambda x: x['time']):
                formatted_event = format_event(event, show_description, show_location)
                output_lines.append(formatted_event)

        # Display all-day tasks
        if all_day_tasks:
            if timed_events:
                output_lines.append("")  # Add a blank line before tasks if there are timed events
            for task in sorted(all_day_tasks, key=lambda x: x['name']):
                formatted_task = format_event(task, show_description, show_location)
                output_lines.append(formatted_task)

        output_lines.append("")  # Add an empty line for separation

    # Print the final output
    if output_lines:
        for line in output_lines:
            print(line)
    else:
        print(f"No events or tasks found for {target_date.strftime('%B %d, %Y')}.")

if __name__ == "__main__":
    main()

