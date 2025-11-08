#!/usr/bin/env python3
"""
Sync highlights from GoodLinks SQLite database to Readwise API.
Finds new highlights since the last sync and posts them to Readwise.
"""

import os
import json
import sqlite3
import requests
import argparse
from datetime import datetime

# Configuration
DATABASE_PATH = os.path.join(
    os.path.expanduser("~"),
    "Library",
    "Group Containers",
    "group.com.ngocluu.goodlinks",
    "Data",
    "data.sqlite"
)
LAST_SYNC_FILE = "last_sync.txt"
READWISE_API_URL = "https://readwise.io/api/v2/highlights/"


def get_last_sync_time():
    """Read the last sync timestamp from file. Returns None if file doesn't exist."""
    if os.path.exists(LAST_SYNC_FILE):
        with open(LAST_SYNC_FILE, "r") as f:
            content = f.read().strip()
            if content:
                try:
                    return float(content)
                except ValueError:
                    return None
    return None


def fetch_new_highlights(last_sync_time):
    """
    Query the GoodLinks database for new highlights.
    
    Args:
        last_sync_time: Unix timestamp of last sync (None if first run)
    
    Returns:
        List of tuples: (id, linkId, content, note, time, color, url, title, author)
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if last_sync_time is not None:
        query = """
        SELECT h.id, h.linkId, h.content, h.note, h.time, h.color, l.url, l.title, l.author
        FROM highlight h
        JOIN link l ON h.linkId = l.id
        WHERE h.time > ?
        ORDER BY h.time ASC
        """
        cursor.execute(query, (last_sync_time,))
    else:
        query = """
        SELECT h.id, h.linkId, h.content, h.note, h.time, h.color, l.url, l.title, l.author
        FROM highlight h
        JOIN link l ON h.linkId = l.id
        ORDER BY h.time ASC
        """
        cursor.execute(query)
    
    highlights = cursor.fetchall()
    conn.close()
    return highlights


def convert_timestamp_to_iso(unix_timestamp):
    """Convert Unix timestamp (double) to ISO 8601 format string."""
    dt = datetime.fromtimestamp(unix_timestamp)
    return dt.isoformat()


def build_readwise_payload(highlight):
    """
    Build the payload for Readwise API from a highlight tuple.
    
    Args:
        highlight: Tuple from database query (id, linkId, content, note, time, color, url, title, author)
    
    Returns:
        Dictionary with the payload data
    """
    highlight_id, link_id, content, note, time, color, url, title, author = highlight
    
    payload = {
        "text": content,
        "source_url": url if url else None,
        "title": title if title else None,
        "author": author if author else None,
        "highlighted_at": convert_timestamp_to_iso(time)
    }
    
    # Add note if present
    if note:
        payload["note"] = note
    
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}
    
    return payload


def post_highlights_to_readwise(highlights, api_token):
    """
    Post highlights to Readwise API.
    
    Args:
        highlights: List of highlight tuples from database query
        api_token: Readwise API token
    
    Raises:
        requests.RequestException: If the API request fails
    """
    # Build array of highlight payloads
    highlight_payloads = [build_readwise_payload(h) for h in highlights]
    
    # Wrap in the 'highlights' key as required by the API
    payload = {
        "highlights": highlight_payloads
    }
    
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(READWISE_API_URL, json=payload, headers=headers)
    response.raise_for_status()


def update_last_sync_time(last_highlight_time):
    """Update the last sync time file with the timestamp of the last processed highlight."""
    with open(LAST_SYNC_FILE, "w") as f:
        f.write(str(last_highlight_time))


def main():
    """Main execution function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Sync highlights from GoodLinks to Readwise API"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode: show what would be posted without actually posting"
    )
    args = parser.parse_args()
    
    dry_run = args.dry_run
    
    if dry_run:
        print("DRY RUN MODE: No highlights will be posted and last_sync.txt will not be updated.")
        print()
    
    # Get API token from environment variable (only required if not in dry run)
    api_token = os.getenv("READWISE_API_TOKEN")
    if not dry_run and not api_token:
        print("Error: READWISE_API_TOKEN environment variable is not set.")
        return
    
    # Get last sync time
    last_sync_time = get_last_sync_time()
    if last_sync_time:
        print(f"Last sync time: {datetime.fromtimestamp(last_sync_time).isoformat()}")
    else:
        print("No previous sync found. Processing all highlights.")
    
    # Fetch new highlights
    highlights = fetch_new_highlights(last_sync_time)
    
    if not highlights:
        print("No new highlights found.")
        return
    
    print(f"Found {len(highlights)} new highlight(s) to sync.")
    print()
    
    # Build the payload for Readwise API
    highlight_payloads = [build_readwise_payload(h) for h in highlights]
    payload = {
        "highlights": highlight_payloads
    }
    
    if dry_run:
        print("Would post the following payload to Readwise:")
        print(json.dumps(payload, indent=2))
        print()
        print(f"DRY RUN: Would sync {len(highlights)} highlight(s) to Readwise.")
        last_highlight_time = highlights[-1][4]  # time is at index 4
        print(f"DRY RUN: Would update last sync time to: {datetime.fromtimestamp(last_highlight_time).isoformat()}")
    else:
        # Post all highlights to Readwise in a single request
        # Stop on first error (exception will be raised)
        try:
            print(f"Posting {len(highlights)} highlight(s) to Readwise...")
            post_highlights_to_readwise(highlights, api_token)
            
            # If all successful, update last sync time with the highest timestamp
            last_highlight_time = highlights[-1][4]  # time is at index 4
            update_last_sync_time(last_highlight_time)
            print(f"Successfully synced {len(highlights)} highlight(s) to Readwise.")
            print(f"Last sync time updated to: {datetime.fromtimestamp(last_highlight_time).isoformat()}")
        
        except requests.RequestException as e:
            print(f"Error posting highlights to Readwise: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise


if __name__ == "__main__":
    main()

