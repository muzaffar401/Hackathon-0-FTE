#!/usr/bin/env python3
"""
AI Orchestrator Service
Watches Needs_Action for tasks, sends to Qwen API for analysis, creates plans.
"""

import json
import os
import re
import shutil
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import openai
from colorama import init, Fore, Style
from dotenv import load_dotenv

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()


class Config:
    """Configuration constants."""
    HOME = Path.home()
    VAULT_DIR = HOME / "AI_Employee_Vault"
    PROJECT_DIR = HOME / "AI_Employee_Project"
    
    INBOX_DIR = VAULT_DIR / "Inbox"
    NEEDS_ACTION_DIR = VAULT_DIR / "Needs_Action"
    DONE_DIR = VAULT_DIR / "Done"
    PENDING_APPROVAL_DIR = VAULT_DIR / "Pending_Approval"
    LOGS_DIR = VAULT_DIR / "Logs"
    PLANS_DIR = PROJECT_DIR / "Plans"
    
    # OpenRouter API settings
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    
    # Polling interval (seconds)
    POLL_INTERVAL = 30
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 2


class OpenRouterClient:
    """Client for OpenRouter API with retry logic."""
    
    def __init__(self):
        self.api_key = Config.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=Config.OPENROUTER_BASE_URL
        )
        self.model = Config.OPENROUTER_MODEL
    
    def analyze_task(self, task_content: str, task_filename: str) -> Tuple[str, str, bool]:
        """
        Send task to OpenRouter API for analysis.
        Returns: (plan_content, risk_level, requires_approval)
        """
        system_prompt = """You are a Personal AI Employee. Analyze this task and create a step-by-step action plan in markdown with checkboxes. 
If task involves money, emails to unknown contacts, or deletions — mark as HIGH RISK and flag for human approval."""
        
        user_prompt = f"""Task file: {task_filename}

Task content:
{task_content}

Please create a detailed action plan with:
1. Clear objective
2. Step-by-step actions with checkboxes
3. Risk assessment (LOW/MEDIUM/HIGH)
4. Whether human approval is required

Format your response as valid markdown."""

        last_error = None
        
        for attempt in range(Config.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                
                plan_content = response.choices[0].message.content
                
                # Parse risk level and approval requirement from response
                risk_level, requires_approval = self._parse_risk_assessment(plan_content)
                
                return plan_content, risk_level, requires_approval
                
            except openai.APIError as e:
                last_error = e
                print(f"{Fore.YELLOW}[RETRY]{Style.RESET_ALL} API error (attempt {attempt + 1}/{Config.MAX_RETRIES}): {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
            except Exception as e:
                last_error = e
                print(f"{Fore.YELLOW}[RETRY]{Style.RESET_ALL} Unexpected error (attempt {attempt + 1}/{Config.MAX_RETRIES}): {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
        
        # All retries exhausted
        raise Exception(f"OpenRouter API failed after {Config.MAX_RETRIES} attempts: {last_error}")
    
    def _parse_risk_assessment(self, content: str) -> Tuple[str, bool]:
        """Parse risk level and approval requirement from AI response."""
        content_upper = content.upper()
        
        # Determine risk level
        if "HIGH RISK" in content_upper or "RISK_LEVEL: HIGH" in content_upper or "**HIGH**" in content_upper:
            risk_level = "HIGH"
        elif "MEDIUM" in content_upper or "RISK_LEVEL: MEDIUM" in content_upper:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Determine if approval is required
        requires_approval = (
            "REQUIRES APPROVAL: YES" in content_upper or
            "REQUIRES APPROVAL: TRUE" in content_upper or
            "FLAG FOR HUMAN APPROVAL" in content_upper or
            "HUMAN APPROVAL REQUIRED" in content_upper or
            (risk_level == "HIGH" and ("YES" in content_upper.split("APPROVAL")[-1] if "APPROVAL" in content_upper else False))
        )
        
        # Additional check for HIGH RISK tasks
        if risk_level == "HIGH":
            requires_approval = True
        
        return risk_level, requires_approval


class TaskOrchestrator:
    """Main orchestrator for processing tasks."""
    
    def __init__(self):
        self.openrouter_client: Optional[OpenRouterClient] = None
        self.processed_files = set()
        self._init_openrouter_client()
    
    def _init_openrouter_client(self):
        """Initialize OpenRouter client if API key is available."""
        try:
            self.openrouter_client = OpenRouterClient()
            print(f"{Fore.GREEN}[API]{Style.RESET_ALL} OpenRouter client initialized successfully.")
        except ValueError as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {e}")
            print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} Running without AI analysis. Tasks will be logged only.")
            self.openrouter_client = None
    
    def scan_needs_action(self) -> list:
        """Scan Needs_Action directory for new task files."""
        try:
            if not Config.NEEDS_ACTION_DIR.exists():
                Config.NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
                return []
            
            task_files = []
            for file_path in Config.NEEDS_ACTION_DIR.glob("*.md"):
                if str(file_path) not in self.processed_files:
                    task_files.append(file_path)
            
            return sorted(task_files, key=lambda x: x.stat().st_mtime)
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to scan Needs_Action: {e}")
            return []
    
    def read_task_file(self, file_path: Path) -> str:
        """Read the content of a task file."""
        try:
            return file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise Exception(f"Failed to read task file: {e}")
    
    def create_plan_file(self, task_filename: str, plan_content: str, risk_level: str, requires_approval: bool) -> Path:
        """Create a plan file in the Plans directory."""
        try:
            # Ensure Plans directory exists
            Config.PLANS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Generate plan filename
            safe_name = re.sub(r'[^\w\-_]', '_', task_filename.replace('.md', ''))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plan_filename = f"PLAN_{safe_name}_{timestamp}.md"
            plan_path = Config.PLANS_DIR / plan_filename
            
            # Create plan content with frontmatter
            created_timestamp = datetime.now().isoformat()
            
            # Extract sections from AI response or create defaults
            objective_match = re.search(r'## Objective\s*\n(.*?)(?=##|\Z)', plan_content, re.DOTALL | re.IGNORECASE)
            objective = objective_match.group(1).strip() if objective_match else "Analyze and complete the task."
            
            steps_match = re.search(r'## Steps?\s*\n(.*?)(?=##|\Z)', plan_content, re.DOTALL | re.IGNORECASE)
            steps = steps_match.group(1).strip() if steps_match else "- [ ] Review task details\n- [ ] Execute required actions"
            
            risk_match = re.search(r'## Risk Assessment\s*\n(.*?)(?=##|\Z)', plan_content, re.DOTALL | re.IGNORECASE)
            risk_assessment = risk_match.group(1).strip() if risk_match else f"Risk Level: {risk_level}"
            
            formatted_content = f"""---
created: {created_timestamp}
risk_level: {risk_level}
status: pending
---
## Objective
{objective}

## Steps
{steps}

## Risk Assessment
{risk_assessment}

## Requires Approval: {"YES" if requires_approval else "NO"}

---
## Full AI Analysis
{plan_content}
"""
            
            plan_path.write_text(formatted_content, encoding="utf-8")
            
            return plan_path
            
        except Exception as e:
            raise Exception(f"Failed to create plan file: {e}")
    
    def move_to_done(self, task_file: Path):
        """Move processed task file to Done directory."""
        try:
            Config.DONE_DIR.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"{timestamp}_{task_file.name}"
            dest_path = Config.DONE_DIR / new_name
            
            shutil.move(str(task_file), str(dest_path))
            
            return dest_path
            
        except Exception as e:
            raise Exception(f"Failed to move file to Done: {e}")
    
    def copy_to_pending_approval(self, plan_file: Path, task_file: Path):
        """Copy high-risk items to Pending_Approval directory."""
        try:
            Config.PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
            
            # Copy the plan file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_name = f"{timestamp}_{plan_file.name}"
            dest_path = Config.PENDING_APPROVAL_DIR / dest_name
            
            shutil.copy2(str(plan_file), str(dest_path))
            
            # Also copy original task file if it still exists
            if task_file.exists():
                task_dest = Config.PENDING_APPROVAL_DIR / f"{timestamp}_{task_file.name}"
                shutil.copy2(str(task_file), str(task_dest))
            
            return dest_path
            
        except Exception as e:
            raise Exception(f"Failed to copy to Pending_Approval: {e}")
    
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
    
    def process_task(self, task_file: Path):
        """Process a single task file."""
        try:
            filename = task_file.name
            
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[PROCESSING]{Style.RESET_ALL} Task: {Fore.YELLOW}{filename}{Style.RESET_ALL}")
            
            # Read task content
            task_content = self.read_task_file(task_file)
            
            # Send to OpenRouter API for analysis
            if self.openrouter_client:
                plan_content, risk_level, requires_approval = self.openrouter_client.analyze_task(
                    task_content, filename
                )
            else:
                # Fallback without AI
                plan_content = f"""## Objective
Review and complete the task: {filename}

## Steps
- [ ] Review task details
- [ ] Execute required actions
- [ ] Document results

## Risk Assessment
Risk Level: MEDIUM (AI analysis unavailable)

## Requires Approval: NO
"""
                risk_level = "MEDIUM"
                requires_approval = False
            
            # Create plan file
            plan_file = self.create_plan_file(filename, plan_content, risk_level, requires_approval)
            print(f"{Fore.GREEN}[CREATED]{Style.RESET_ALL} Plan: {Fore.BLUE}{plan_file.name}{Style.RESET_ALL}")
            
            # Handle high-risk tasks
            if requires_approval or risk_level == "HIGH":
                approval_file = self.copy_to_pending_approval(plan_file, task_file)
                print(f"{Fore.RED}[HIGH RISK]{Style.RESET_ALL} Copied to Pending_Approval: {Fore.RED}{approval_file.name}{Style.RESET_ALL}")
            
            # Move task to Done
            done_file = self.move_to_done(task_file)
            self.processed_files.add(str(task_file))
            print(f"{Fore.GREEN}[COMPLETE]{Style.RESET_ALL} Moved to Done: {Fore.BLUE}{done_file.name}{Style.RESET_ALL}")
            
            # Log the event
            self.log_event("task_processed", {
                "task_file": filename,
                "plan_file": plan_file.name,
                "risk_level": risk_level,
                "requires_approval": requires_approval,
                "done_file": done_file.name
            })
            
            # Print risk summary
            if risk_level == "HIGH":
                print(f"{Fore.RED}[RISK]{Style.RESET_ALL} Level: {Fore.RED}{risk_level}{Style.RESET_ALL} - Requires human approval")
            elif risk_level == "MEDIUM":
                print(f"{Fore.YELLOW}[RISK]{Style.RESET_ALL} Level: {Fore.YELLOW}{risk_level}{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}[RISK]{Style.RESET_ALL} Level: {Fore.GREEN}{risk_level}{Style.RESET_ALL}")
            
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to process task {task_file.name}: {e}")
            self.log_event("task_error", {
                "task_file": task_file.name,
                "error": str(e)
            })
    
    def run(self):
        """Main run loop."""
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} Orchestrator running. Polling every {Config.POLL_INTERVAL}s...")
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} Press Ctrl+C to stop.\n")
        
        while True:
            try:
                # Scan for new tasks
                tasks = self.scan_needs_action()
                
                if tasks:
                    print(f"{Fore.GREEN}[FOUND]{Style.RESET_ALL} {len(tasks)} new task(s) to process.")
                    for task_file in tasks:
                        self.process_task(task_file)
                else:
                    # Print idle status (without cluttering)
                    pass
                
                time.sleep(Config.POLL_INTERVAL)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Loop error: {e}")
                self.log_event("orchestrator_error", {"error": str(e)})
                time.sleep(Config.POLL_INTERVAL)


def print_banner():
    """Print the startup banner."""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║{Fore.YELLOW}           AI Employee Orchestrator Service               {Fore.CYAN}║
╠══════════════════════════════════════════════════════════╣
║  Needs_Action: {Fore.GREEN}{Config.NEEDS_ACTION_DIR}{Fore.CYAN}
║  Plans Dir:    {Fore.GREEN}{Config.PLANS_DIR}{Fore.CYAN}
║  Done Dir:     {Fore.GREEN}{Config.DONE_DIR}{Fore.CYAN}
║  Logs Dir:     {Fore.GREEN}{Config.LOGS_DIR}{Fore.CYAN}
╠══════════════════════════════════════════════════════════╣
║  OpenRouter: {Fore.YELLOW}{Config.OPENROUTER_MODEL}{Fore.CYAN}
║  Poll Interval: {Fore.YELLOW}{Config.POLL_INTERVAL}s{Fore.CYAN}
╠══════════════════════════════════════════════════════════╣
║  {Fore.YELLOW}Status: {Fore.GREEN}Starting...{Fore.CYAN}                                      ║
╚══════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    print(banner)


def ensure_directories():
    """Ensure all required directories exist."""
    try:
        Config.NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
        Config.DONE_DIR.mkdir(parents=True, exist_ok=True)
        Config.PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
        Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        Config.PLANS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to create directories: {e}")
        raise


def signal_handler(signum, frame):
    """Handle Ctrl+C and other termination signals."""
    print(f"\n{Fore.YELLOW}[SHUTDOWN]{Style.RESET_ALL} Received termination signal...")
    print(f"{Fore.YELLOW}[SHUTDOWN]{Style.RESET_ALL} Cleaning up...")
    print(f"{Fore.GREEN}[GOODBYE]{Style.RESET_ALL} Orchestrator stopped gracefully.")
    sys.exit(0)


def main():
    """Main entry point for the orchestrator service."""
    try:
        # Print startup banner
        print_banner()
        
        # Ensure directories exist
        print(f"{Fore.GREEN}[SETUP]{Style.RESET_ALL} Checking directories...")
        ensure_directories()
        print(f"{Fore.GREEN}[SETUP]{Style.RESET_ALL} Directories ready.")
        
        # Check for API key
        if not Config.OPENROUTER_API_KEY:
            print(f"{Fore.RED}[WARNING]{Style.RESET_ALL} OPENROUTER_API_KEY not set in environment.")
            print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Create a .env file with: OPENROUTER_API_KEY=your_key_here")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create and run orchestrator
        orchestrator = TaskOrchestrator()
        orchestrator.run()
        
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# pip install openai colorama python-dotenv
# Set env: OPENROUTER_API_KEY=your_key_here
# Optional: OPENROUTER_MODEL=anthropic/claude-3.5-sonnet (default: openai/gpt-4o-mini)
