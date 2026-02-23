#!/usr/bin/env python3
"""
File Watcher Service
Monitors Inbox directory for new files and creates task files in Needs_Action.
"""

import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

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
    INBOX_DIR = VAULT_DIR / "Inbox"
    NEEDS_ACTION_DIR = VAULT_DIR / "Needs_Action"
    LOGS_DIR = VAULT_DIR / "Logs"
    PID_FILE = Path("/tmp/file_watcher.pid")
    
    # Windows-specific PID file location
    if sys.platform == "win32":
        PID_FILE = Path(os.environ.get("TEMP", os.environ.get("TMP", "."))) / "file_watcher.pid"


class FileWatcherHandler(FileSystemEventHandler):
    """Handles file system events in the Inbox directory."""
    
    def __init__(self):
        super().__init__()
        self.processed_files = set()
    
    def on_created(self, event):
        """Handle file creation events."""
        try:
            if event.is_directory:
                return
            
            if not isinstance(event, FileCreatedEvent):
                return
            
            file_path = Path(event.src_path)
            
            # Skip if already processed (handles duplicate events)
            if str(file_path) in self.processed_files:
                return
            
            # Small delay to ensure file is fully written
            time.sleep(0.1)
            
            self._process_new_file(file_path)
            
        except Exception as e:
            self._log_error(f"Error handling file creation: {e}")
    
    def _process_new_file(self, file_path: Path):
        """Process a newly detected file."""
        try:
            filename = file_path.name
            timestamp = datetime.now()
            iso_timestamp = timestamp.isoformat()
            
            # Mark as processed
            self.processed_files.add(str(file_path))
            
            # Create task file
            task_file = self._create_task_file(filename, iso_timestamp)
            
            # Log the event
            self._log_event("file_detected", {
                "original_file": str(file_path),
                "task_file": str(task_file),
                "timestamp": iso_timestamp
            })
            
            # Print colored output
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[DETECTED]{Style.RESET_ALL} New file: {Fore.YELLOW}{filename}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[CREATED]{Style.RESET_ALL} Task file: {Fore.BLUE}{task_file.name}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
            
        except Exception as e:
            self._log_error(f"Error processing file {file_path}: {e}")
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to process file: {e}")
    
    def _create_task_file(self, filename: str, timestamp: str) -> Path:
        """Create a markdown task file in Needs_Action directory."""
        try:
            # Generate task filename
            safe_timestamp = datetime.fromisoformat(timestamp).strftime("%Y%m%d_%H%M%S")
            task_filename = f"{safe_timestamp}_{filename}.md"
            task_path = Config.NEEDS_ACTION_DIR / task_filename
            
            # Ensure directory exists
            Config.NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
            
            # Create task file content
            content = f"""---
type: file_drop
original_name: {filename}
received: {timestamp}
priority: medium
status: pending
---
## File Details

## Suggested Actions
- [ ] Review file
- [ ] Process and respond
## Notes
"""
            
            # Write the file
            task_path.write_text(content, encoding="utf-8")
            
            return task_path
            
        except Exception as e:
            raise Exception(f"Failed to create task file: {e}")
    
    def _log_event(self, event_type: str, data: dict):
        """Log an event to the daily JSON log file."""
        try:
            # Ensure logs directory exists
            Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Get today's log file
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = Config.LOGS_DIR / f"{today}.json"
            
            # Load existing logs or create new
            logs = []
            if log_file.exists():
                try:
                    logs = json.loads(log_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, Exception):
                    logs = []
            
            # Add new event
            logs.append({
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": data
            })
            
            # Write back
            log_file.write_text(json.dumps(logs, indent=2), encoding="utf-8")
            
        except Exception as e:
            print(f"{Fore.RED}[LOG ERROR]{Style.RESET_ALL} Failed to log event: {e}")
    
    def _log_error(self, message: str):
        """Log an error message."""
        try:
            self._log_event("error", {"message": message})
        except Exception:
            pass
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}")


def print_banner():
    """Print the startup banner."""
    banner = f"""
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.YELLOW}           AI EMPLOYEE FILE WATCHER SERVICE{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.CYAN}Monitoring: {Fore.GREEN}{Config.INBOX_DIR}{Style.RESET_ALL}
{Fore.CYAN}Tasks Dir:  {Fore.GREEN}{Config.NEEDS_ACTION_DIR}{Style.RESET_ALL}
{Fore.CYAN}Logs Dir:   {Fore.GREEN}{Config.LOGS_DIR}{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.YELLOW}Status: Starting...{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
"""
    print(banner)


def write_pid_file() -> Optional[Path]:
    """Write the PID file to track the running process."""
    try:
        Config.PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        Config.PID_FILE.write_text(str(os.getpid()))
        return Config.PID_FILE
    except Exception as e:
        print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} Could not write PID file: {e}")
        return None


def remove_pid_file():
    """Remove the PID file on shutdown."""
    try:
        if Config.PID_FILE.exists():
            Config.PID_FILE.unlink()
    except Exception:
        pass


def ensure_directories():
    """Ensure all required directories exist."""
    try:
        Config.INBOX_DIR.mkdir(parents=True, exist_ok=True)
        Config.NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
        Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to create directories: {e}")
        raise


def signal_handler(signum, frame):
    """Handle Ctrl+C and other termination signals."""
    print(f"\n{Fore.YELLOW}[SHUTDOWN]{Style.RESET_ALL} Received termination signal...")
    print(f"{Fore.YELLOW}[SHUTDOWN]{Style.RESET_ALL} Cleaning up...")
    remove_pid_file()
    print(f"{Fore.GREEN}[GOODBYE]{Style.RESET_ALL} File watcher stopped gracefully.")
    sys.exit(0)


def main():
    """Main entry point for the file watcher service."""
    try:
        # Print startup banner
        print_banner()
        
        # Ensure directories exist
        print(f"{Fore.GREEN}[SETUP]{Style.RESET_ALL} Checking directories...")
        ensure_directories()
        print(f"{Fore.GREEN}[SETUP]{Style.RESET_ALL} Directories ready.")
        
        # Write PID file
        pid_path = write_pid_file()
        if pid_path:
            print(f"{Fore.GREEN}[SETUP]{Style.RESET_ALL} PID file: {pid_path}")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create observer and handler
        event_handler = FileWatcherHandler()
        observer = Observer()
        observer.schedule(event_handler, str(Config.INBOX_DIR), recursive=False)
        
        # Start monitoring
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} Watching for new files...")
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} Press Ctrl+C to stop.\n")
        
        observer.start()
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} Unexpected error: {e}")
        remove_pid_file()
        sys.exit(1)
    finally:
        try:
            observer.stop()
            observer.join()
        except Exception:
            pass
        remove_pid_file()


if __name__ == "__main__":
    main()

# pip install watchdog colorama python-dotenv
