#!/usr/bin/env python3
"""
Approval Manager Service
Manages the Human-in-the-Loop workflow for approvals and rejections.
"""

import json
import os
import re
import shutil
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

from colorama import init, Fore, Style
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

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
    PENDING_APPROVAL_DIR = VAULT_DIR / "Pending_Approval"
    APPROVED_DIR = VAULT_DIR / "Approved"
    REJECTED_DIR = VAULT_DIR / "Rejected"
    DONE_DIR = VAULT_DIR / "Done"
    LOGS_DIR = VAULT_DIR / "Logs"
    
    # Dashboard file
    DASHBOARD_FILE = VAULT_DIR / "Dashboard.md"
    
    # Polling interval
    POLL_INTERVAL = 15  # seconds
    
    # Approval expiry (24 hours)
    APPROVAL_EXPIRY_HOURS = 24


class DashboardUpdater:
    """Updates the Dashboard.md file with activity."""
    
    @staticmethod
    def increment_counter(counter_name: str):
        """Increment a counter in the Dashboard."""
        try:
            if not Config.DASHBOARD_FILE.exists():
                return
            
            content = Config.DASHBOARD_FILE.read_text(encoding="utf-8")
            
            # Find and increment the counter
            patterns = {
                "approved": r'(✅ Approved:\s*)(\d+)',
                "rejected": r'(❌ Rejected:\s*)(\d+)',
                "pending": r'(⏳ Pending:\s*)(\d+)',
                "linkedin_posts": r'(📝 LinkedIn Posts:\s*)(\d+)',
                "emails_processed": r'(📧 Emails Processed:\s*)(\d+)',
                "payments_flagged": r'(💰 Payments Flagged:\s*)(\d+)',
            }
            
            if counter_name in patterns:
                pattern = patterns[counter_name]
                match = re.search(pattern, content)
                if match:
                    prefix = match.group(1)
                    current = int(match.group(2))
                    new_value = current + 1
                    content = re.sub(pattern, f"{prefix}{new_value}", content)
                    Config.DASHBOARD_FILE.write_text(content, encoding="utf-8")
                    print(f"{Fore.GREEN}[DASHBOARD]{Style.RESET_ALL} Updated {counter_name} counter")
                    
        except Exception as e:
            print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} Could not update dashboard: {e}")
    
    @staticmethod
    def add_activity_entry(action: str, details: str, status: str):
        """Add an entry to Recent Activity section."""
        try:
            if not Config.DASHBOARD_FILE.exists():
                return
            
            content = Config.DASHBOARD_FILE.read_text(encoding="utf-8")
            
            # Create activity entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            status_icon = "✅" if status == "approved" else "❌" if status == "rejected" else "⏳"
            entry = f"- [{timestamp}] {status_icon} {action}: {details[:100]}"
            
            # Find Recent Activity section and add entry
            activity_header = "## Recent Activity"
            if activity_header in content:
                # Insert after the header
                parts = content.split(activity_header, 1)
                new_content = f"{parts[0]}{activity_header}\n{entry}\n{parts[1]}"
                Config.DASHBOARD_FILE.write_text(new_content, encoding="utf-8")
                print(f"{Fore.GREEN}[DASHBOARD]{Style.RESET_ALL} Added activity entry")
            else:
                # Add Recent Activity section
                new_section = f"\n## Recent Activity\n{entry}\n"
                content += new_section
                Config.DASHBOARD_FILE.write_text(content, encoding="utf-8")
                
        except Exception as e:
            print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} Could not update activity: {e}")


class ApprovalRequest:
    """Creates and manages approval requests."""
    
    @staticmethod
    def create(action_type: str, details: Dict[str, Any], risk_level: str = "MEDIUM") -> Optional[Path]:
        """
        Create an approval request file in Pending_Approval folder.
        
        Args:
            action_type: Type of action (linkedin_post, email_reply, payment, etc.)
            details: Dictionary with action details
            risk_level: HIGH, MEDIUM, or LOW
            
        Returns:
            Path to created file, or None if failed
        """
        try:
            Config.PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_type = re.sub(r'[^\w\-_]', '_', action_type.lower())[:20]
            filename = f"APPROVAL_{safe_type}_{timestamp}.md"
            filepath = Config.PENDING_APPROVAL_DIR / filename
            
            # Calculate expiry
            expires = datetime.now() + timedelta(hours=Config.APPROVAL_EXPIRY_HOURS)
            
            # Format details
            details_text = "\n".join([f"- **{k}**: {v}" for k, v in details.items()])
            
            # Create content
            content = f"""---
type: {action_type}
risk_level: {risk_level}
created: {datetime.now().isoformat()}
expires: {expires.isoformat()}
status: pending
---
## Action Required

{details_text}

## Risk Assessment
Risk Level: {risk_level}

## To Approve
Move this file to /Approved/ folder to execute this action.

## To Reject
Move this file to /Rejected/ folder to decline this action.

## Notes
- Approval expires in {Config.APPROVAL_EXPIRY_HOURS} hours
- High risk actions require manual review
- Rejected actions are logged for audit

"""
            
            filepath.write_text(content, encoding="utf-8")
            
            print(f"{Fore.GREEN}[CREATED]{Style.RESET_ALL} Approval request: {filename}")
            
            # Log the request
            ApprovalManager._log_event("approval_request_created", {
                "type": action_type,
                "risk_level": risk_level,
                "file": filename
            })
            
            return filepath
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to create approval request: {e}")
            return None


class ApprovalManager:
    """Main approval manager service."""
    
    def __init__(self):
        self.processed_files = set()
        self.dashboard = DashboardUpdater()
    
    def process_approved_file(self, file_path: Path):
        """Process a file that was moved to Approved folder."""
        try:
            if str(file_path) in self.processed_files:
                return
            
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[APPROVED]{Style.RESET_ALL} Processing: {file_path.name}")
            
            # Read file content
            content = file_path.read_text(encoding="utf-8")
            
            # Parse frontmatter
            frontmatter = self._parse_frontmatter(content)
            
            if not frontmatter:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Invalid file format")
                self._move_to_done(file_path, "invalid")
                return
            
            action_type = frontmatter.get("type", "unknown")
            
            print(f"{Fore.CYAN}[TYPE]{Style.RESET_ALL} {action_type}")
            
            # Execute based on type
            success = False
            
            if action_type == "linkedin_post":
                success = self._execute_linkedin_post(file_path, content)
            elif action_type == "email_reply":
                success = self._execute_email_reply(file_path, content)
            elif action_type == "payment":
                success = self._execute_payment(file_path, content)
            elif action_type == "file_drop":
                success = self._execute_file_drop(file_path, content)
            elif action_type == "whatsapp_message":
                success = self._execute_whatsapp_message(file_path, content)
            else:
                print(f"{Fore.YELLOW}[UNKNOWN]{Style.RESET_ALL} Unknown action type: {action_type}")
                success = self._execute_generic(file_path, content, action_type)
            
            # Move to Done and update counters
            if success:
                self._move_to_done(file_path, "approved")
                self.dashboard.increment_counter("approved")
                self.dashboard.add_activity_entry(action_type, file_path.name, "approved")
                
                # Increment type-specific counter
                if action_type == "linkedin_post":
                    self.dashboard.increment_counter("linkedin_posts")
                elif action_type == "email_reply":
                    self.dashboard.increment_counter("emails_processed")
                elif action_type == "payment":
                    self.dashboard.increment_counter("payments_flagged")
            else:
                print(f"{Fore.RED}[FAILED]{Style.RESET_ALL} Action execution failed")
                self._move_to_done(file_path, "failed")
            
            self.processed_files.add(str(file_path))
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to process approved file: {e}")
            self._log_event("approval_error", {"file": str(file_path), "error": str(e)})
    
    def process_rejected_file(self, file_path: Path):
        """Process a file that was moved to Rejected folder."""
        try:
            if str(file_path) in self.processed_files:
                return
            
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[REJECTED]{Style.RESET_ALL} Processing: {file_path.name}")
            
            # Read file content
            content = file_path.read_text(encoding="utf-8")
            
            # Parse frontmatter
            frontmatter = self._parse_frontmatter(content)
            
            action_type = frontmatter.get("type", "unknown") if frontmatter else "unknown"
            
            # Log rejection
            print(f"{Fore.YELLOW}[LOG]{Style.RESET_ALL} Rejection logged for: {action_type}")
            
            self._log_event("approval_rejected", {
                "type": action_type,
                "file": file_path.name
            })
            
            # Update dashboard
            self.dashboard.increment_counter("rejected")
            self.dashboard.add_activity_entry(action_type, file_path.name, "rejected")
            
            # Move to Done with rejected status
            self._move_to_done(file_path, "rejected")
            
            self.processed_files.add(str(file_path))
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to process rejected file: {e}")
            self._log_event("rejection_error", {"file": str(file_path), "error": str(e)})
    
    def _execute_linkedin_post(self, file_path: Path, content: str) -> bool:
        """Execute LinkedIn post action."""
        try:
            print(f"{Fore.CYAN}[LINKEDIN]{Style.RESET_ALL} Posting to LinkedIn...")
            
            # Import and call linkedin_poster
            from linkedin_poster import LinkedInPoster
            
            poster = LinkedInPoster()
            
            # Extract post content
            post_match = re.search(r'## Post Content\s*\n(.*?)(?=##|$)', content, re.DOTALL)
            post_text = post_match.group(1).strip() if post_match else content
            
            if not post_text:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No post content found")
                return False
            
            # Post to LinkedIn
            success = poster._post_to_linkedin(post_text, "Approved via Approval Manager")
            
            if success:
                print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Posted to LinkedIn")
            
            return success
            
        except ImportError:
            print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} linkedin_poster not available")
            # Simulate for testing
            print(f"{Fore.GREEN}[SIMULATED]{Style.RESET_ALL} LinkedIn post would be published")
            return True
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} LinkedIn post failed: {e}")
            return False
    
    def _execute_email_reply(self, file_path: Path, content: str) -> bool:
        """Execute email reply action."""
        try:
            print(f"{Fore.CYAN}[EMAIL]{Style.RESET_ALL} Processing email reply...")
            
            # Email MCP not yet configured
            print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Email MCP not yet configured — manual action needed")
            
            # Log what needs to be done
            from_match = re.search(r'from:\s*(.+)', content)
            subject_match = re.search(r'subject:\s*(.+)', content)
            
            if from_match:
                print(f"  To: {from_match.group(1).strip()}")
            if subject_match:
                print(f"  Subject: {subject_match.group(1).strip()}")
            
            return True  # Logged for manual action
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Email processing failed: {e}")
            return False
    
    def _execute_payment(self, file_path: Path, content: str) -> bool:
        """Execute payment action."""
        try:
            print(f"{Fore.CYAN}[PAYMENT]{Style.RESET_ALL} Processing payment...")
            
            # NEVER auto-execute payments
            print(f"{Fore.RED}[SECURITY]{Style.RESET_ALL} Payment requires manual execution — NEVER auto-pay")
            print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Payment details logged for manual review")
            
            # Extract payment details for logging
            amount_match = re.search(r'amount:\s*(.+)', content)
            recipient_match = re.search(r'recipient:\s*(.+)', content)
            
            if amount_match:
                print(f"  Amount: {amount_match.group(1).strip()}")
            if recipient_match:
                print(f"  Recipient: {recipient_match.group(1).strip()}")
            
            return True  # Logged for manual action
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Payment processing failed: {e}")
            return False
    
    def _execute_file_drop(self, file_path: Path, content: str) -> bool:
        """Execute file drop action."""
        try:
            print(f"{Fore.CYAN}[FILE]{Style.RESET_ALL} Processing file drop task...")
            
            # File was already processed by orchestrator
            print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} File drop task completed")
            
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} File drop processing failed: {e}")
            return False
    
    def _execute_whatsapp_message(self, file_path: Path, content: str) -> bool:
        """Execute WhatsApp message action."""
        try:
            print(f"{Fore.CYAN}[WHATSAPP]{Style.RESET_ALL} Processing WhatsApp message...")
            
            # Extract message details
            from_match = re.search(r'from:\s*(.+)', content)
            keyword_match = re.search(r'keyword_matched:\s*(.+)', content)
            
            if from_match:
                print(f"  From: {from_match.group(1).strip()}")
            if keyword_match:
                print(f"  Keywords: {keyword_match.group(1).strip()}")
            
            print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} WhatsApp message logged for follow-up")
            
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} WhatsApp processing failed: {e}")
            return False
    
    def _execute_generic(self, file_path: Path, content: str, action_type: str) -> bool:
        """Execute generic/unknown action type."""
        try:
            print(f"{Fore.CYAN}[GENERIC]{Style.RESET_ALL} Processing {action_type}...")
            print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Generic action logged for review")
            
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Generic action failed: {e}")
            return False
    
    def _move_to_done(self, file_path: Path, status: str):
        """Move file to Done folder with status prefix."""
        try:
            Config.DONE_DIR.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"{timestamp}_{status.upper()}_{file_path.name}"
            dest_path = Config.DONE_DIR / new_name
            
            shutil.move(str(file_path), str(dest_path))
            
            print(f"{Fore.GREEN}[MOVED]{Style.RESET_ALL} To Done: {new_name}")
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to move file: {e}")
    
    def _parse_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse YAML frontmatter from markdown content."""
        try:
            if not content.startswith("---"):
                return None
            
            parts = content.split("---", 2)
            if len(parts) < 3:
                return None
            
            frontmatter = parts[1].strip()
            data = {}
            
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    data[key.strip()] = value.strip()
            
            return data
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Parse error: {e}")
            return None
    
    @staticmethod
    def _log_event(event_type: str, data: dict):
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
    
    def scan_and_process(self):
        """Scan Approved and Rejected folders and process files."""
        try:
            # Process approved files
            if Config.APPROVED_DIR.exists():
                approved_files = list(Config.APPROVED_DIR.glob("*.md"))
                for file_path in approved_files:
                    if str(file_path) not in self.processed_files:
                        self.process_approved_file(file_path)
            
            # Process rejected files
            if Config.REJECTED_DIR.exists():
                rejected_files = list(Config.REJECTED_DIR.glob("*.md"))
                for file_path in rejected_files:
                    if str(file_path) not in self.processed_files:
                        self.process_rejected_file(file_path)
                        
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Scan error: {e}")
    
    def run(self):
        """Main run loop."""
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} Approval Manager running. Polling every {Config.POLL_INTERVAL}s...")
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} Press Ctrl+C to stop.\n")
        
        try:
            while True:
                try:
                    self.scan_and_process()
                    time.sleep(Config.POLL_INTERVAL)
                except Exception as e:
                    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Loop error: {e}")
                    time.sleep(Config.POLL_INTERVAL)
        except KeyboardInterrupt:
            raise


class ApprovalWatcher(FileSystemEventHandler):
    """Watches Approved and Rejected folders for new files."""
    
    def __init__(self, manager: ApprovalManager):
        super().__init__()
        self.manager = manager
    
    def on_created(self, event):
        """Handle file creation events."""
        try:
            if event.is_directory:
                return
            
            file_path = Path(event.src_path)
            
            # Small delay to ensure file is fully written
            time.sleep(0.1)
            
            if "Approved" in str(file_path):
                print(f"{Fore.GREEN}[DETECTED]{Style.RESET_ALL} New approved file: {file_path.name}")
                self.manager.process_approved_file(file_path)
            elif "Rejected" in str(file_path):
                print(f"{Fore.YELLOW}[DETECTED]{Style.RESET_ALL} New rejected file: {file_path.name}")
                self.manager.process_rejected_file(file_path)
                
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Watcher error: {e}")


def print_banner():
    """Print the startup banner."""
    banner = f"""
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.YELLOW}           APPROVAL MANAGER SERVICE{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.CYAN}Pending Dir:   {Fore.GREEN}{Config.PENDING_APPROVAL_DIR}{Style.RESET_ALL}
{Fore.CYAN}Approved Dir:  {Fore.GREEN}{Config.APPROVED_DIR}{Style.RESET_ALL}
{Fore.CYAN}Rejected Dir:  {Fore.GREEN}{Config.REJECTED_DIR}{Style.RESET_ALL}
{Fore.CYAN}Done Dir:      {Fore.GREEN}{Config.DONE_DIR}{Style.RESET_ALL}
{Fore.CYAN}Dashboard:     {Fore.GREEN}{Config.DASHBOARD_FILE}{Style.RESET_ALL}
{Fore.CYAN}Poll Interval: {Fore.GREEN}{Config.POLL_INTERVAL}s{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
"""
    print(banner)


def ensure_directories():
    """Ensure all required directories exist."""
    try:
        Config.PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
        Config.APPROVED_DIR.mkdir(parents=True, exist_ok=True)
        Config.REJECTED_DIR.mkdir(parents=True, exist_ok=True)
        Config.DONE_DIR.mkdir(parents=True, exist_ok=True)
        Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to create directories: {e}")
        raise


def signal_handler(signum, frame):
    """Handle Ctrl+C and other termination signals."""
    print(f"\n{Fore.YELLOW}[SHUTDOWN]{Style.RESET_ALL} Received termination signal...")
    print(f"{Fore.GREEN}[GOODBYE]{Style.RESET_ALL} Approval Manager stopped gracefully.")
    sys.exit(0)


def main():
    """Main entry point for the approval manager service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Approval Manager Service")
    parser.add_argument("--create", "-c", type=str, help="Create an approval request")
    parser.add_argument("--type", "-t", type=str, help="Action type for approval request")
    parser.add_argument("--risk", "-r", type=str, default="MEDIUM", help="Risk level (HIGH/MEDIUM/LOW)")
    parser.add_argument("--watch", "-w", action="store_true", help="Run watcher mode (default)")
    parser.add_argument("--scan", "-s", action="store_true", help="Scan once and exit")
    
    args = parser.parse_args()
    
    try:
        # Print startup banner
        print_banner()
        
        # Ensure directories exist
        print(f"{Fore.GREEN}[SETUP]{Style.RESET_ALL} Checking directories...")
        ensure_directories()
        print(f"{Fore.GREEN}[SETUP]{Style.RESET_ALL} Directories ready.")
        
        # Create manager
        manager = ApprovalManager()
        
        # Handle commands
        if args.create:
            # Create approval request
            details = {"description": args.create}
            if args.type:
                details["action_type"] = args.type
            
            ApprovalRequest.create(
                action_type=args.type or "generic_action",
                details=details,
                risk_level=args.risk
            )
            
        elif args.scan:
            # Scan once
            manager.scan_and_process()
            
        else:
            # Run watcher mode (default)
            # Set up signal handlers
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Set up file system watchers
            event_handler = ApprovalWatcher(manager)
            observer = Observer()
            
            # Watch Approved folder
            if Config.APPROVED_DIR.exists():
                observer.schedule(event_handler, str(Config.APPROVED_DIR), recursive=False)
                print(f"{Fore.GREEN}[WATCH]{Style.RESET_ALL} Monitoring: {Config.APPROVED_DIR}")
            
            # Watch Rejected folder
            if Config.REJECTED_DIR.exists():
                observer.schedule(event_handler, str(Config.REJECTED_DIR), recursive=False)
                print(f"{Fore.GREEN}[WATCH]{Style.RESET_ALL} Monitoring: {Config.REJECTED_DIR}")
            
            observer.start()
            
            # Run main loop
            manager.run()
            
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# pip install watchdog colorama python-dotenv
