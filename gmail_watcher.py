#!/usr/bin/env python3
"""
Gmail Watcher Service
Polls Gmail for unread important emails and creates task files.
"""

import base64
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from colorama import init, Fore, Style
from dotenv import load_dotenv

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()


class Config:
    """Configuration constants."""
    HOME = Path.home()
    VAULT_DIR = HOME / "AI_Employee_Vault"
    PROJECT_DIR = HOME / "AI_Employee_Project"
    
    # Directories
    INBOX_DIR = VAULT_DIR / "Inbox"
    NEEDS_ACTION_DIR = VAULT_DIR / "Needs_Action"
    LOGS_DIR = VAULT_DIR / "Logs"
    
    # Gmail files
    CREDENTIALS_FILE = PROJECT_DIR / "gmail_credentials.json"
    TOKEN_FILE = PROJECT_DIR / "gmail_token.json"
    PROCESSED_FILE = PROJECT_DIR / "processed_emails.json"
    
    # Gmail API settings
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    POLL_INTERVAL = 120  # seconds
    RATE_LIMIT_WAIT = 300  # 5 minutes
    TOKEN_ERROR_WAIT = 60  # 1 minute
    
    # Known contacts (add your important contacts here)
    KNOWN_CONTACTS = [
        "boss@",
        "manager@",
        "hr@",
        "support@",
        "billing@",
    ]
    
    # Priority keywords
    URGENT_KEYWORDS = ["invoice", "payment", "urgent", "asap", "immediate", "deadline"]


class ProcessedEmails:
    """Manages the processed emails tracking file."""
    
    def __init__(self):
        self.file_path = Config.PROCESSED_FILE
        self.email_ids = set()
        self._load()
    
    def _load(self):
        """Load processed email IDs from file."""
        try:
            if self.file_path.exists():
                data = json.loads(self.file_path.read_text(encoding="utf-8"))
                self.email_ids = set(data.get("processed_ids", []))
        except Exception as e:
            print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} Could not load processed emails: {e}")
            self.email_ids = set()
    
    def _save(self):
        """Save processed email IDs to file."""
        try:
            Config.PROJECT_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "processed_ids": list(self.email_ids),
                "last_updated": datetime.now().isoformat()
            }
            self.file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Could not save processed emails: {e}")
    
    def is_processed(self, email_id: str) -> bool:
        """Check if an email has been processed."""
        return email_id in self.email_ids
    
    def mark_processed(self, email_id: str):
        """Mark an email as processed."""
        self.email_ids.add(email_id)
        self._save()


class GmailWatcher:
    """Main Gmail watcher service."""
    
    def __init__(self):
        self.service = None
        self.processed_emails = ProcessedEmails()
        self._authenticated = False
        
    def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth2."""
        try:
            if not GOOGLE_LIBS_AVAILABLE:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Google API libraries not installed.")
                print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Run: pip install google-auth google-auth-oauthlib google-api-python-client")
                return False
            
            creds = None
            
            # Load existing token
            if Config.TOKEN_FILE.exists():
                try:
                    creds = Credentials.from_authorized_user_file(
                        Config.TOKEN_FILE, Config.SCOPES
                    )
                except Exception as e:
                    print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} Invalid token file: {e}")
                    Config.TOKEN_FILE.unlink(missing_ok=True)
                    creds = None
            
            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        print(f"{Fore.GREEN}[AUTH]{Style.RESET_ALL} Token refreshed successfully.")
                    except Exception as e:
                        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Token refresh failed: {e}")
                        Config.TOKEN_FILE.unlink(missing_ok=True)
                        creds = None
                
                if not creds and Config.CREDENTIALS_FILE.exists():
                    print(f"{Fore.CYAN}[AUTH]{Style.RESET_ALL} Starting OAuth flow...")
                    print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} A browser window should open for authentication.")
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            Config.CREDENTIALS_FILE, Config.SCOPES
                        )
                        creds = flow.run_local_server(port=0, open_browser=True)
                        
                        # Save token
                        Config.PROJECT_DIR.mkdir(parents=True, exist_ok=True)
                        Config.TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
                        print(f"{Fore.GREEN}[AUTH]{Style.RESET_ALL} Authentication successful!")
                        
                    except Exception as e:
                        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} OAuth flow failed: {e}")
                        return False
                elif not creds:
                    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Credentials file not found: {Config.CREDENTIALS_FILE}")
                    print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} See setup instructions at bottom of this file.")
                    return False
            
            # Build service
            self.service = build("gmail", "v1", credentials=creds)
            self._authenticated = True
            print(f"{Fore.GREEN}[AUTH]{Style.RESET_ALL} Gmail API connected.")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Authentication failed: {e}")
            return False
    
    def fetch_emails(self) -> List[Dict[str, Any]]:
        """Fetch unread important emails from Gmail."""
        if not self.service:
            return []
        
        try:
            # Query: unread and important
            results = self.service.users().messages().list(
                userId="me",
                q="is:unread is:important",
                maxResults=50
            ).execute()
            
            messages = results.get("messages", [])
            emails = []
            
            for msg in messages:
                msg_id = msg["id"]
                
                # Skip if already processed
                if self.processed_emails.is_processed(msg_id):
                    continue
                
                # Get full message
                message = self.service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"]
                ).execute()
                
                # Get snippet
                snippet = message.get("snippet", "")
                
                # Parse headers
                headers = message.get("payload", {}).get("headers", [])
                email_data = {
                    "id": msg_id,
                    "snippet": snippet,
                    "from": "",
                    "to": "",
                    "subject": "",
                    "date": ""
                }
                
                for header in headers:
                    name = header.get("name", "").lower()
                    value = header.get("value", "")
                    if name == "from":
                        email_data["from"] = value
                    elif name == "to":
                        email_data["to"] = value
                    elif name == "subject":
                        email_data["subject"] = value
                    elif name == "date":
                        email_data["date"] = value
                
                emails.append(email_data)
            
            return emails
            
        except HttpError as e:
            if e.resp.status == 429:
                print(f"{Fore.YELLOW}[RATE LIMIT]{Style.RESET_ALL} API rate limited. Waiting {Config.RATE_LIMIT_WAIT}s...")
                time.sleep(Config.RATE_LIMIT_WAIT)
            elif e.resp.status == 401:
                print(f"{Fore.RED}[AUTH ERROR]{Style.RESET_ALL} Token expired. Please re-authenticate.")
                raise Exception("Token expired")
            else:
                print(f"{Fore.RED}[API ERROR]{Style.RESET_ALL} Gmail API error: {e}")
            return []
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Fetch error: {e}")
            return []
    
    def determine_priority(self, email: Dict[str, Any]) -> str:
        """Determine email priority based on rules."""
        subject = email.get("subject", "").lower()
        sender = email.get("from", "").lower()
        
        # Check for urgent keywords
        for keyword in Config.URGENT_KEYWORDS:
            if keyword in subject:
                return "urgent"
        
        # Check for known contacts
        for contact in Config.KNOWN_CONTACTS:
            if contact in sender:
                return "high"
        
        # Default
        return "medium"
    
    def create_task_file(self, email: Dict[str, Any]) -> Optional[Path]:
        """Create a task file for an email."""
        try:
            Config.NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            safe_id = email["id"][:16]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"EMAIL_{safe_id}_{timestamp}.md"
            filepath = Config.NEEDS_ACTION_DIR / filename
            
            # Determine priority
            priority = self.determine_priority(email)
            
            # Decode snippet if base64
            snippet = email.get("snippet", "")
            try:
                # Gmail snippets are already decoded, but handle if needed
                if "==" in snippet and len(snippet) > 50:
                    snippet = base64.urlsafe_b64decode(snippet + "==").decode("utf-8", errors="ignore")
            except:
                pass
            
            # Create content
            content = f"""---
type: email
from: {email.get("from", "Unknown")}
subject: {email.get("subject", "No Subject")}
received: {datetime.now().isoformat()}
priority: {priority}
status: pending
---
## Email Content
{snippet}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward if needed
- [ ] Archive after processing

## Notes

"""
            
            filepath.write_text(content, encoding="utf-8")
            
            return filepath
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to create task file: {e}")
            return None
    
    def log_event(self, event_type: str, data: dict):
        """Log an event to the daily JSON log file."""
        try:
            Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = Config.LOGS_DIR / f"{today}.json"
            
            logs = []
            if log_file.exists():
                try:
                    logs = json.loads(log_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, Exception):
                    logs = []
            
            logs.append({
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": data
            })
            
            log_file.write_text(json.dumps(logs, indent=2), encoding="utf-8")
            
        except Exception as e:
            print(f"{Fore.RED}[LOG ERROR]{Style.RESET_ALL} Failed to log event: {e}")
    
    def process_emails(self):
        """Fetch and process new emails."""
        try:
            emails = self.fetch_emails()
            
            if not emails:
                return
            
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[FOUND]{Style.RESET_ALL} {len(emails)} new email(s)")
            
            for email in emails:
                subject = email.get("subject", "No Subject")
                sender = email.get("from", "Unknown")
                priority = self.determine_priority(email)
                
                # Create task file
                task_file = self.create_task_file(email)
                
                if task_file:
                    # Mark as processed
                    self.processed_emails.mark_processed(email["id"])
                    
                    # Log the event
                    self.log_event("email_processed", {
                        "email_id": email["id"],
                        "from": sender,
                        "subject": subject,
                        "priority": priority,
                        "task_file": task_file.name
                    })
                    
                    # Print status
                    priority_color = Fore.RED if priority == "urgent" else (Fore.YELLOW if priority == "high" else Fore.GREEN)
                    print(f"  {Fore.GREEN}[+]{Style.RESET_ALL} {subject[:50]}... ({priority_color}{priority}{Style.RESET_ALL})")
                else:
                    print(f"  {Fore.RED}[-]{Style.RESET_ALL} Failed to create task for: {subject[:30]}...")
            
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Process error: {e}")
            self.log_event("gmail_error", {"error": str(e)})
    
    def run(self):
        """Main run loop."""
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} Gmail Watcher running. Polling every {Config.POLL_INTERVAL}s...")
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} Press Ctrl+C to stop.\n")
        
        while True:
            try:
                # Check authentication
                if not self._authenticated:
                    if not self.authenticate():
                        print(f"{Fore.YELLOW}[WAIT]{Style.RESET_ALL} Retrying in {Config.POLL_INTERVAL}s...")
                        time.sleep(Config.POLL_INTERVAL)
                        continue
                
                # Process emails
                self.process_emails()
                
                # Wait for next poll
                time.sleep(Config.POLL_INTERVAL)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                error_msg = str(e)
                
                # Handle token expiration
                if "Token expired" in error_msg or "401" in error_msg:
                    print(f"{Fore.RED}[AUTH]{Style.RESET_ALL} Authentication token expired.")
                    print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Delete gmail_token.json and restart to re-authenticate.")
                    print(f"{Fore.YELLOW}[WAIT]{Style.RESET_ALL} Pausing for {Config.TOKEN_ERROR_WAIT}s...")
                    self._authenticated = False
                    time.sleep(Config.TOKEN_ERROR_WAIT)
                else:
                    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Loop error: {e}")
                    self.log_event("gmail_watcher_error", {"error": error_msg})
                    time.sleep(Config.POLL_INTERVAL)


def print_banner():
    """Print the startup banner."""
    banner = f"""
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.YELLOW}           GMAIL WATCHER SERVICE{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.CYAN}Vault Dir:  {Fore.GREEN}{Config.VAULT_DIR}{Style.RESET_ALL}
{Fore.CYAN}Poll Interval: {Fore.GREEN}{Config.POLL_INTERVAL}s{Style.RESET_ALL}
{Fore.CYAN}Scopes:     {Fore.GREEN}gmail.readonly{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.YELLOW}Status: Starting...{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
"""
    print(banner)


def ensure_directories():
    """Ensure all required directories exist."""
    try:
        Config.NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
        Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        Config.PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to create directories: {e}")
        raise


def signal_handler(signum, frame):
    """Handle Ctrl+C and other termination signals."""
    print(f"\n{Fore.YELLOW}[SHUTDOWN]{Style.RESET_ALL} Received termination signal...")
    print(f"{Fore.GREEN}[GOODBYE]{Style.RESET_ALL} Gmail Watcher stopped gracefully.")
    sys.exit(0)


def main():
    """Main entry point for the Gmail watcher service."""
    try:
        # Print startup banner
        print_banner()
        
        # Ensure directories exist
        print(f"{Fore.GREEN}[SETUP]{Style.RESET_ALL} Checking directories...")
        ensure_directories()
        print(f"{Fore.GREEN}[SETUP]{Style.RESET_ALL} Directories ready.")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create and run watcher
        watcher = GmailWatcher()
        
        # Initial authentication
        if not watcher.authenticate():
            print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} Could not authenticate with Gmail.")
            print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} See setup instructions below.")
            sys.exit(1)
        
        watcher.run()
        
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# ============================================================================
# GMAIL API SETUP INSTRUCTIONS
# ============================================================================
#
# 1. Go to Google Cloud Console:
#    https://console.cloud.google.com/
#
# 2. Create a new project (or select existing one)
#
# 3. Enable the Gmail API:
#    - Go to "APIs & Services" > "Library"
#    - Search for "Gmail API"
#    - Click "Enable"
#
# 4. Create OAuth 2.0 credentials:
#    - Go to "APIs & Services" > "Credentials"
#    - Click "Create Credentials" > "OAuth client ID"
#    - Application type: "Desktop app"
#    - Give it a name (e.g., "Gmail Watcher")
#    - Click "Create"
#
# 5. Download credentials:
#    - Click the download icon for your newly created credentials
#    - Save the file as: gmail_credentials.json
#    - Place it in: ~/AI_Employee_Project/gmail_credentials.json
#
# 6. Run the script:
#    python gmail_watcher.py
#    - A browser window will open for OAuth authentication
#    - Sign in with your Google account
#    - Grant permissions
#    - The token will be saved automatically
#
# 7. First run complete!
#    - The script will now poll Gmail every 120 seconds
#    - New emails will create task files in Needs_Action/
#
# TROUBLESHOOTING:
# - If token expires: Delete gmail_token.json and run again
# - If credentials invalid: Re-download from Google Cloud Console
# - If API not enabled: Enable Gmail API in Google Cloud Console
#
# pip install google-auth google-auth-oauthlib google-api-python-client colorama python-dotenv
