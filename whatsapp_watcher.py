#!/usr/bin/env python3
"""
WhatsApp Watcher Service
Monitors WhatsApp Web for unread messages containing keywords.
"""

import json
import os
import re
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple

from colorama import init, Fore, Style
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, BrowserContext

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
    NEEDS_ACTION_DIR = VAULT_DIR / "Needs_Action"
    LOGS_DIR = VAULT_DIR / "Logs"
    SESSION_DIR = PROJECT_DIR / "whatsapp_session"
    
    # WhatsApp settings
    WHATSAPP_URL = "https://web.whatsapp.com"
    POLL_INTERVAL = 30  # seconds
    LOAD_TIMEOUT = 30000  # 30 seconds
    
    # Keywords to monitor (case-insensitive)
    KEYWORDS = [
        "invoice",
        "payment",
        "urgent",
        "asap",
        "price",
        "quote",
        "help",
        "project",
    ]
    
    # Priority keywords (higher priority)
    URGENT_KEYWORDS = ["invoice", "payment", "urgent", "asap"]
    
    # Headless mode
    HEADLESS = os.getenv("WHATSAPP_HEADLESS", "false").lower() == "true"
    
    # Processed messages tracking
    PROCESSED_FILE = PROJECT_DIR / "whatsapp_processed.json"


class ProcessedMessages:
    """Manages processed messages tracking."""
    
    def __init__(self):
        self.file_path = Config.PROCESSED_FILE
        self.messages: Set[str] = set()
        self._load()
    
    def _load(self):
        """Load processed message IDs from file."""
        try:
            if self.file_path.exists():
                data = json.loads(self.file_path.read_text(encoding="utf-8"))
                self.messages = set(data.get("processed_ids", []))
        except Exception as e:
            print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} Could not load processed messages: {e}")
            self.messages = set()
    
    def _save(self):
        """Save processed message IDs to file."""
        try:
            Config.PROJECT_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "processed_ids": list(self.messages),
                "last_updated": datetime.now().isoformat()
            }
            self.file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Could not save processed messages: {e}")
    
    def is_processed(self, chat_id: str, timestamp: str) -> bool:
        """Check if a message has been processed."""
        msg_id = f"{chat_id}:{timestamp}"
        return msg_id in self.messages
    
    def mark_processed(self, chat_id: str, timestamp: str):
        """Mark a message as processed."""
        msg_id = f"{chat_id}:{timestamp}"
        self.messages.add(msg_id)
        self._save()


class WhatsAppWatcher:
    """Main WhatsApp watcher service."""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.processed = ProcessedMessages()
        self._first_run = not Config.SESSION_DIR.exists()
    
    def launch_browser(self):
        """Launch Chromium with persistent context."""
        try:
            self.playwright = sync_playwright().start()
            
            # Determine headless mode
            # First run: always visible for QR code scan
            # Subsequent runs: use config setting
            headless = False if self._first_run else Config.HEADLESS
            
            print(f"{Fore.CYAN}[BROWSER]{Style.RESET_ALL} Launching Chromium (headless={headless})...")
            
            # Create session directory
            Config.SESSION_DIR.mkdir(parents=True, exist_ok=True)
            
            # Launch with persistent context
            self.browser = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(Config.SESSION_DIR),
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
                viewport={"width": 1280, "height": 720},
            )
            
            self.context = self.browser
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            
            # Add anti-detection
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            print(f"{Fore.GREEN}[BROWSER]{Style.RESET_ALL} Browser launched successfully.")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to launch browser: {e}")
            return False
    
    def navigate_to_whatsapp(self) -> bool:
        """Navigate to WhatsApp Web and wait for load."""
        try:
            print(f"{Fore.CYAN}[NAV]{Style.RESET_ALL} Navigating to WhatsApp Web...")
            
            self.page.goto(Config.WHATSAPP_URL, timeout=Config.LOAD_TIMEOUT)
            
            # Wait for page to load
            self.page.wait_for_load_state("networkidle", timeout=Config.LOAD_TIMEOUT)
            
            # Check if we need QR code (first time or session expired)
            if self._first_run or self._is_qr_visible():
                print(f"{Fore.YELLOW}[QR]{Style.RESET_ALL} Please scan QR code with WhatsApp mobile app...")
                print(f"{Fore.YELLOW}[QR]{Style.RESET_ALL} Waiting up to 60 seconds...")
                
                # Wait for QR to be scanned (main app to appear)
                try:
                    self.page.wait_for_selector('div[data-testid="default-user-sidebar"]', timeout=60000)
                    print(f"{Fore.GREEN}[AUTH]{Style.RESET_ALL} WhatsApp authenticated!")
                    self._first_run = False
                except Exception:
                    print(f"{Fore.RED}[TIMEOUT]{Style.RESET_ALL} QR code scan timed out.")
                    return False
            
            # Wait for chat list
            self._wait_for_chat_list()
            
            print(f"{Fore.GREEN}[READY]{Style.RESET_ALL} WhatsApp Web loaded.")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Navigation failed: {e}")
            return False
    
    def _is_qr_visible(self) -> bool:
        """Check if QR code is visible on page."""
        try:
            qr_selector = 'div[data-testid="qr-container"]'
            return self.page.is_visible(qr_selector)
        except Exception:
            return False
    
    def _wait_for_chat_list(self, timeout: int = 10):
        """Wait for chat list to be available."""
        try:
            # Wait for chat list container
            self.page.wait_for_selector('div[role="grid"]', timeout=timeout * 1000)
        except Exception:
            pass  # Continue anyway
    
    def get_unread_chats(self) -> List[Dict[str, Any]]:
        """Get list of chats with unread messages."""
        unread_chats = []
        seen_names = set()

        try:
            # WhatsApp Web: try multiple selectors (DOM changes between versions)
            chat_list = (
                self.page.query_selector('div[data-testid="chat-list"]')
                or self.page.query_selector('div[role="grid"]')
                or self.page.query_selector('#pane-side')
                or self.page.query_selector('div[id="pane-side"]')
            )
            if not chat_list:
                return []

            # Chat items are usually links; also accept list rows
            chat_items = chat_list.query_selector_all('a[role="link"]')
            if not chat_items:
                chat_items = chat_list.query_selector_all('div[role="row"]')

            for chat_item in chat_items:
                try:
                    has_unread = False

                    # Method 1: data-testid unread badge (current WA Web)
                    unread_badge = chat_item.query_selector('[data-testid="unread-count"]')
                    if unread_badge:
                        has_unread = True

                    # Method 2: cell unread indicator
                    if not has_unread:
                        green_dot = chat_item.query_selector('[data-testid="cell-chat-unread"]')
                        if green_dot:
                            has_unread = True

                    # Method 3: aria-label on the link or its children (e.g. "Muzammil, 1 unread message")
                    if not has_unread:
                        aria_label = chat_item.get_attribute("aria-label") or ""
                        if not aria_label:
                            try:
                                aria_label = chat_item.evaluate("""
                                    el => {
                                        const l = el.getAttribute('aria-label');
                                        if (l) return l;
                                        const child = el.querySelector('[aria-label]');
                                        return child ? child.getAttribute('aria-label') || '' : '';
                                    }
                                """) or ""
                            except Exception:
                                pass
                        if aria_label and "unread" in aria_label.lower():
                            has_unread = True

                    # Method 4: any descendant with aria-label containing "unread"
                    if not has_unread:
                        desc = chat_item.query_selector('[aria-label*="unread" i]')
                        if desc:
                            has_unread = True

                    # Method 5: unread count badge = span with only a number (e.g. "1")
                    if not has_unread:
                        for span in chat_item.query_selector_all("span"):
                            try:
                                text = span.inner_text().strip()
                                if text.isdigit() and 1 <= int(text) <= 99:
                                    has_unread = True
                                    break
                            except Exception:
                                continue

                    if has_unread:
                        # Extract chat name from the title element
                        title_elem = chat_item.query_selector('span[dir="auto"]')
                        if title_elem:
                            name = title_elem.inner_text().strip()
                        else:
                            # Try aria-label as fallback
                            aria_label = chat_item.get_attribute("aria-label") or ""
                            name = aria_label.split("\n")[0].strip() if aria_label else "Unknown"
                        
                        # Skip if no valid name or duplicate
                        if not name or name in seen_names:
                            continue
                        
                        seen_names.add(name)

                        # Generate unique chat ID from name
                        chat_id = f"chat_{hash(name)}"

                        unread_chats.append({
                            "name": name[:50],
                            "id": chat_id,
                            "title": name,
                        })

                except Exception as e:
                    # Skip this chat if we can't extract info
                    continue

            if unread_chats:
                print(f"{Fore.GREEN}[FOUND]{Style.RESET_ALL} {len(unread_chats)} unread chat(s)")
            else:
                print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} No unread chats found")

            return unread_chats

        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to get unread chats: {e}")
            return []
    
    def _get_chat_list_container(self):
        """Return the same chat list container used in get_unread_chats."""
        return (
            self.page.query_selector('div[data-testid="chat-list"]')
            or self.page.query_selector('div[role="grid"]')
            or self.page.query_selector('#pane-side')
            or self.page.query_selector('div[id="pane-side"]')
        )

    def open_chat(self, chat_name: str) -> bool:
        """Open a specific chat by name."""
        try:
            # Scope to the chat list panel only (same as get_unread_chats)
            chat_list = self._get_chat_list_container()
            if not chat_list:
                print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} Chat list not found")
                return False

            chat_items = chat_list.query_selector_all('a[role="link"]')
            if not chat_items:
                chat_items = chat_list.query_selector_all('div[role="row"]')

            def normalize(s: str) -> str:
                return " ".join(s.split()).strip() if s else ""

            chat_name_norm = normalize(chat_name)

            for chat_item in chat_items:
                try:
                    # Primary: match by first span[dir="auto"] (usually the contact/chat name)
                    title_elem = chat_item.query_selector('span[dir="auto"]')
                    if title_elem:
                        current = normalize(title_elem.inner_text())
                        first_line = normalize(current.split("\n")[0]) if current else ""
                        # Match when first line equals or starts with chat name (e.g. "Muzammil" or "Muzammil urgent")
                        if first_line == chat_name_norm or (chat_name_norm and first_line.startswith(chat_name_norm)):
                            chat_item.click()
                            time.sleep(1.5)
                            return True
                except Exception:
                    continue

            # Fallback: match by aria-label (e.g. "Muzammil, 1 unread message")
            for chat_item in chat_items:
                try:
                    aria_label = chat_item.get_attribute("aria-label") or ""
                    if not aria_label:
                        try:
                            aria_label = chat_item.evaluate("""
                                el => {
                                    const l = el.getAttribute('aria-label');
                                    if (l) return l;
                                    const c = el.querySelector('[aria-label]');
                                    return c ? (c.getAttribute('aria-label') || '') : '';
                                }
                            """) or ""
                        except Exception:
                            pass
                    if chat_name_norm in normalize(aria_label) or chat_name in aria_label:
                        chat_item.click()
                        time.sleep(1.5)
                        return True
                except Exception:
                    continue

            print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} Chat not found: {chat_name}")
            return False

        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to open chat: {e}")
            return False

    def _extract_text_from_message_element(self, elem) -> str:
        """Extract message text from a bubble element using multiple selectors."""
        text = ""
        sel = elem.query_selector('span[data-lexical-text="true"]')
        if sel:
            text = sel.inner_text().strip()
        if not text:
            sel = elem.query_selector('[data-testid="copyable-text"]')
            if sel:
                text = sel.inner_text().strip()
        if not text:
            sel = elem.query_selector('.copyable-text')
            if sel:
                text = sel.inner_text().strip()
        if not text:
            sel = elem.query_selector('span[dir="auto"]')
            if sel:
                text = sel.inner_text().strip()
        if not text:
            text = elem.inner_text().strip()
        return text or ""

    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """Get the last message from current chat. Prefers last incoming message (the unread one)."""
        try:
            time.sleep(1.2)

            last_msg = None
            timestamp = datetime.now().isoformat()

            # 1) Last incoming message (unread)
            for selector in ['div[data-testid="message-in"]', 'div[role="row"]']:
                try:
                    messages = self.page.query_selector_all(selector)
                    if selector == 'div[data-testid="message-in"]':
                        incoming = messages
                    else:
                        incoming = [m for m in messages if m.get_attribute("data-testid") == "message-in"]
                    if not incoming and messages:
                        incoming = messages[-1:] if messages else []
                    if incoming:
                        last_elem = incoming[-1]
                        text = self._extract_text_from_message_element(last_elem)
                        if text:
                            time_elem = last_elem.query_selector('span[title]')
                            if time_elem:
                                try:
                                    timestamp = time_elem.get_attribute("title") or timestamp
                                except Exception:
                                    pass
                            last_msg = {"text": text, "timestamp": timestamp}
                            break
                except Exception:
                    continue
                if last_msg:
                    break

            # 2) Any message bubble
            if not last_msg:
                for sel in ['div[data-testid="message-in"]', 'div[data-testid="message-out"]', 'div[data-testid="bubble"]', 'div[role="row"]']:
                    try:
                        messages = self.page.query_selector_all(sel)
                        if messages:
                            last_elem = messages[-1]
                            text = self._extract_text_from_message_element(last_elem)
                            if text:
                                time_elem = last_elem.query_selector('span[title]')
                                if time_elem:
                                    try:
                                        timestamp = time_elem.get_attribute("title") or timestamp
                                    except Exception:
                                        pass
                                last_msg = {"text": text, "timestamp": timestamp}
                                break
                    except Exception:
                        continue

            # 3) JS fallback: last copyable/lexical text in #main
            if not last_msg:
                try:
                    result = self.page.evaluate("""
                        () => {
                            const main = document.querySelector('#main') || document.querySelector('[role="main"]') || document.body;
                            const spans = main.querySelectorAll('span[data-lexical-text="true"], .copyable-text, [data-testid="copyable-text"]');
                            for (let i = spans.length - 1; i >= 0; i--) {
                                const t = spans[i].innerText.trim();
                                if (t.length > 0 && t.length < 5000) return t;
                            }
                            return null;
                        }
                    """)
                    if result:
                        last_msg = {"text": result, "timestamp": timestamp}
                except Exception:
                    pass

            # 4) Message list / #main inner text, last meaningful line
            if not last_msg:
                try:
                    msg_list = self.page.query_selector('div[data-testid="message-list"]') or self.page.query_selector('#main')
                    if msg_list:
                        all_text = msg_list.inner_text()
                        if all_text:
                            lines = [l.strip() for l in all_text.split("\n") if l.strip() and len(l.strip()) > 1]
                            for line in reversed(lines):
                                if len(line) > 2 and not re.match(r"^[\d:\s]+(AM|PM)?$", line, re.I) and line.lower() not in ("read", "delivered"):
                                    last_msg = {"text": line, "timestamp": timestamp}
                                    break
                except Exception:
                    pass

            return last_msg

        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to get last message: {e}")
            return None
    
    def check_keywords(self, text: str) -> Tuple[bool, List[str]]:
        """Check if text contains monitored keywords."""
        if not text:
            return False, []
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in Config.KEYWORDS:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return len(found_keywords) > 0, found_keywords
    
    def determine_priority(self, keywords: List[str]) -> str:
        """Determine message priority based on keywords."""
        for kw in keywords:
            if kw in Config.URGENT_KEYWORDS:
                return "urgent"
        return "high"
    
    def create_task_file(self, chat_name: str, message: Dict[str, Any], keywords: List[str]) -> Optional[Path]:
        """Create a task file for a WhatsApp message."""
        try:
            Config.NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r'[^\w\-_]', '_', chat_name)[:30]
            filename = f"WHATSAPP_{safe_name}_{timestamp}.md"
            filepath = Config.NEEDS_ACTION_DIR / filename
            
            # Determine priority
            priority = self.determine_priority(keywords)
            
            # Get message preview (first 100 chars)
            full_text = message.get("text", "")
            preview = full_text[:100] + "..." if len(full_text) > 100 else full_text
            
            # Create content
            content = f"""---
type: whatsapp
from: {chat_name}
message_preview: {preview}
received: {datetime.now().isoformat()}
priority: {priority}
status: pending
keyword_matched: {', '.join(keywords)}
---
## Message Content
{full_text}

## Suggested Actions
- [ ] Draft reply
- [ ] Check if invoice/payment needed
- [ ] Notify human if payment involved

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
    
    def process_unread_messages(self):
        """Process all unread messages."""
        try:
            # Get unread chats
            unread_chats = self.get_unread_chats()
            
            if not unread_chats:
                return
            
            processed_count = 0
            
            for chat in unread_chats:
                chat_name = chat["name"]
                chat_id = chat["id"]
                
                print(f"\n{Fore.CYAN}[CHECKING]{Style.RESET_ALL} Chat: {chat_name}")
                
                # Open the chat
                if not self.open_chat(chat_name):
                    print(f"{Fore.YELLOW}[SKIP]{Style.RESET_ALL} Could not open chat")
                    continue
                
                # Get last message
                message = self.get_last_message()
                
                if not message or not message.get("text"):
                    print(f"{Fore.YELLOW}[SKIP]{Style.RESET_ALL} No message found")
                    continue
                
                msg_text = message.get("text", "")
                
                # Check if already processed
                msg_timestamp = message.get("timestamp", str(datetime.now().timestamp()))
                if self.processed.is_processed(chat_id, msg_timestamp):
                    print(f"{Fore.YELLOW}[SKIP]{Style.RESET_ALL} Already processed")
                    continue
                
                # Check for keywords
                has_keywords, keywords = self.check_keywords(msg_text)
                
                if has_keywords:
                    print(f"{Fore.GREEN}[MATCH]{Style.RESET_ALL} Keywords: {', '.join(keywords)}")
                    
                    # Create task file
                    task_file = self.create_task_file(chat_name, message, keywords)
                    
                    if task_file:
                        # Mark as processed
                        self.processed.mark_processed(chat_id, msg_timestamp)
                        
                        # Log the event
                        self.log_event("whatsapp_message", {
                            "chat": chat_name,
                            "keywords": keywords,
                            "task_file": task_file.name
                        })
                        
                        print(f"{Fore.GREEN}[CREATED]{Style.RESET_ALL} Task: {task_file.name}")
                        processed_count += 1
                    else:
                        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to create task file")
                else:
                    preview = (msg_text[:60] + "…") if len(msg_text) > 60 else msg_text
                    print(f"{Fore.YELLOW}[SKIP]{Style.RESET_ALL} No keywords matched (read: {repr(preview)})")
                
                # Small delay between chats
                time.sleep(0.5)
            
            if processed_count > 0:
                print(f"\n{Fore.GREEN}[SUMMARY]{Style.RESET_ALL} Processed {processed_count} message(s)")
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Process error: {e}")
            self.log_event("whatsapp_error", {"error": str(e)})
    
    def close(self):
        """Close browser and cleanup."""
        try:
            if self.browser:
                self.browser.close()
                print(f"{Fore.GREEN}[CLOSED]{Style.RESET_ALL} Browser closed.")
            
            if self.playwright:
                self.playwright.stop()
                
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Cleanup error: {e}")
    
    def run(self):
        """Main run loop."""
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} WhatsApp Watcher running. Polling every {Config.POLL_INTERVAL}s...")
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} Press Ctrl+C to stop.\n")
        
        try:
            while True:
                try:
                    # Process unread messages
                    self.process_unread_messages()
                    
                    # Wait for next poll
                    time.sleep(Config.POLL_INTERVAL)
                    
                except Exception as e:
                    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Loop error: {e}")
                    self.log_event("whatsapp_loop_error", {"error": str(e)})
                    time.sleep(Config.POLL_INTERVAL)
                    
        except KeyboardInterrupt:
            raise
    
    def run_once(self):
        """Run once and exit (for testing)."""
        try:
            self.process_unread_messages()
        finally:
            self.close()


def print_banner():
    """Print the startup banner."""
    session_status = "NEW (QR scan required)" if not Config.SESSION_DIR.exists() else "EXISTING (saved session)"
    
    banner = f"""
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.YELLOW}           WHATSAPP WATCHER SERVICE{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.CYAN}Vault Dir:     {Fore.GREEN}{Config.VAULT_DIR}{Style.RESET_ALL}
{Fore.CYAN}Session Dir:   {Fore.GREEN}{Config.SESSION_DIR}{Style.RESET_ALL}
{Fore.CYAN}Session Status:{Fore.YELLOW} {session_status}{Style.RESET_ALL}
{Fore.CYAN}Poll Interval: {Fore.GREEN}{Config.POLL_INTERVAL}s{Style.RESET_ALL}
{Fore.CYAN}Headless:      {Fore.GREEN}{Config.HEADLESS}{Style.RESET_ALL}
{Fore.CYAN}Keywords:      {Fore.GREEN}{len(Config.KEYWORDS)}{Style.RESET_ALL}
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
    sys.exit(0)


def main():
    """Main entry point for the WhatsApp watcher service."""
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
        
        # Create watcher
        watcher = WhatsAppWatcher()
        
        # Launch browser
        if not watcher.launch_browser():
            print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} Could not launch browser.")
            sys.exit(1)
        
        # Navigate to WhatsApp
        if not watcher.navigate_to_whatsapp():
            print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} Could not load WhatsApp Web.")
            watcher.close()
            sys.exit(1)
        
        # Run main loop
        watcher.run()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[SHUTDOWN]{Style.RESET_ALL} Stopping...")
    except Exception as e:
        print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Cleanup happens in signal handler or exception
        pass


if __name__ == "__main__":
    main()

# ============================================================================
# WHATSAPP WATCHER SETUP INSTRUCTIONS
# ============================================================================
#
# 1. Install Playwright:
#    pip install playwright
#
# 2. Install Chromium browser:
#    playwright install chromium
#
# 3. Run the script:
#    python whatsapp_watcher.py
#
# 4. First run - QR Code Scan:
#    - Browser window will open
#    - Scan QR code with WhatsApp mobile app:
#      Settings > Linked Devices > Link a Device
#    - Session saves automatically after scan
#
# 5. Subsequent runs:
#    - Session loads from whatsapp_session/
#    - No QR scan needed
#    - Set WHATSAPP_HEADLESS=true for background mode
#
# ENVIRONMENT VARIABLES:
# - WHATSAPP_HEADLESS: true/false (default: false)
#
# KEYWORDS MONITORED:
# - invoice, payment, urgent, asap (HIGH PRIORITY)
# - price, quote, help, project (NORMAL PRIORITY)
#
# TROUBLESHOOTING:
# - Session expired: Delete whatsapp_session/ folder and re-scan QR
# - Browser won't launch: Run 'playwright install chromium'
# - Messages not detected: Check WhatsApp Web is loaded properly
#
# pip install playwright colorama python-dotenv
# playwright install chromium
