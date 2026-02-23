#!/usr/bin/env python3
"""
Master Scheduler Service
Runs all Silver Tier components on schedule.
"""

import json
import os
import re
import signal
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import schedule
from colorama import init, Fore, Style
from dotenv import load_dotenv
from openai import OpenAI

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
    DONE_DIR = VAULT_DIR / "Done"
    BRIEFINGS_DIR = VAULT_DIR / "Briefings"
    LOGS_DIR = VAULT_DIR / "Logs"
    
    # Files
    DASHBOARD_FILE = VAULT_DIR / "Dashboard.md"
    BUSINESS_GOALS_FILE = VAULT_DIR / "Business_Goals.md"
    
    # AI Settings
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
    QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL = "qwen-plus"
    
    # Polling intervals (seconds)
    NEEDS_ACTION_INTERVAL = 30
    APPROVAL_INTERVAL = 15
    LINKEDIN_INTERVAL = 600  # 10 minutes


class AIBriefingGenerator:
    """Generates briefings using AI."""
    
    def __init__(self):
        self.client: Optional[OpenAI] = None
        self._init_client()
    
    def _init_client(self):
        """Initialize AI client."""
        api_key = Config.QWEN_API_KEY or Config.OPENROUTER_API_KEY
        base_url = Config.QWEN_BASE_URL if Config.QWEN_API_KEY else Config.OPENROUTER_BASE_URL
        model = Config.QWEN_MODEL if Config.QWEN_API_KEY else Config.OPENROUTER_MODEL
        
        if api_key:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            print(f"{Fore.GREEN}[AI]{Style.RESET_ALL} Briefing generator initialized ({model}).")
        else:
            print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} No AI API key. Briefings will be basic.")
            self.client = None
    
    def generate_daily_briefing(self) -> Optional[Path]:
        """Generate daily briefing from last 24 hours of completed tasks."""
        try:
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}[BRIEFING]{Style.RESET_ALL} Generating daily briefing...")
            
            # Get files from last 24 hours
            cutoff = datetime.now() - timedelta(hours=24)
            done_files = self._get_recent_files(cutoff)
            
            if not done_files:
                print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} No completed tasks in last 24 hours")
                return None
            
            # Count by type
            stats = self._count_by_type(done_files)
            
            # Generate summary
            if self.client:
                summary = self._ai_summarize(done_files, stats, "daily")
            else:
                summary = self._basic_summary(stats)
            
            # Save briefing
            briefing_path = self._save_briefing(summary, stats, "daily")
            
            print(f"{Fore.GREEN}[COMPLETE]{Style.RESET_ALL} Daily briefing saved: {briefing_path.name}")
            return briefing_path
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Daily briefing failed: {e}")
            return None
    
    def generate_weekly_ceo_briefing(self) -> Optional[Path]:
        """Generate weekly CEO briefing."""
        try:
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}[CEO BRIEFING]{Style.RESET_ALL} Generating weekly CEO briefing...")
            
            # Get files from last 7 days
            cutoff = datetime.now() - timedelta(days=7)
            done_files = self._get_recent_files(cutoff)
            
            # Read business goals
            business_goals = self._read_business_goals()
            
            if not done_files:
                print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} No completed tasks in last 7 days")
                return None
            
            # Count by type
            stats = self._count_by_type(done_files)
            
            # Generate AI briefing
            if self.client:
                summary = self._ai_ceo_briefing(done_files, stats, business_goals)
            else:
                summary = self._basic_summary(stats)
            
            # Save briefing
            briefing_path = self._save_briefing(summary, stats, "weekly_ceo")
            
            print(f"{Fore.GREEN}[COMPLETE]{Style.RESET_ALL} CEO briefing saved: {briefing_path.name}")
            return briefing_path
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} CEO briefing failed: {e}")
            return None
    
    def generate_linkedin_post_idea(self) -> Optional[Path]:
        """Generate LinkedIn post idea based on business goals."""
        try:
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}[LINKEDIN]{Style.RESET_ALL} Generating LinkedIn post idea...")
            
            # Read business goals
            business_goals = self._read_business_goals()
            
            if not self.client:
                print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} AI not available for post generation")
                return None
            
            # Generate post idea
            prompt = f"""You are a LinkedIn content strategist. Based on these business goals, suggest 3 engaging LinkedIn post ideas.

Business Goals:
{business_goals}

For each idea, provide:
1. Hook line
2. Main topic (2-3 sentences)
3. Call to action
4. 3-5 relevant hashtags

Keep each idea under 200 words. Make them professional but conversational."""

            response = self.client.chat.completions.create(
                model=Config.OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": "You are a LinkedIn content expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            post_ideas = response.choices[0].message.content.strip()
            
            # Save to Pending_Approval
            Config.VAULT_DIR.joinpath("Pending_Approval").mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"LINKEDIN_idea_{timestamp}.md"
            filepath = Config.VAULT_DIR / "Pending_Approval" / filename
            
            content = f"""---
type: linkedin_idea
generated: {datetime.now().isoformat()}
status: pending_review
---
## LinkedIn Post Ideas

{post_ideas}

## Next Steps
1. Review and select best idea
2. Move to Approved/ folder to schedule posting
3. Or use: python linkedin_poster.py --generate "your topic"
"""
            
            filepath.write_text(content, encoding="utf-8")
            
            print(f"{Fore.GREEN}[CREATED]{Style.RESET_ALL} Post ideas: {filename}")
            return filepath
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} LinkedIn idea generation failed: {e}")
            return None
    
    def _get_recent_files(self, cutoff: datetime) -> List[Path]:
        """Get files modified after cutoff date."""
        if not Config.DONE_DIR.exists():
            return []
        
        recent_files = []
        for file_path in Config.DONE_DIR.glob("*.md"):
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime > cutoff:
                    recent_files.append(file_path)
            except Exception:
                continue
        
        return sorted(recent_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def _count_by_type(self, files: List[Path]) -> Dict[str, int]:
        """Count files by type from frontmatter."""
        stats = {
            "total": len(files),
            "linkedin_post": 0,
            "email": 0,
            "file_drop": 0,
            "whatsapp_message": 0,
            "payment": 0,
            "other": 0,
        }
        
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                type_match = re.search(r'type:\s*(\w+)', content)
                if type_match:
                    file_type = type_match.group(1)
                    if file_type in stats:
                        stats[file_type] += 1
                    else:
                        stats["other"] += 1
                else:
                    stats["other"] += 1
            except Exception:
                stats["other"] += 1
        
        return stats
    
    def _read_business_goals(self) -> str:
        """Read business goals file."""
        if Config.BUSINESS_GOALS_FILE.exists():
            return Config.BUSINESS_GOALS_FILE.read_text(encoding="utf-8")
        return "No business goals file found."
    
    def _ai_summarize(self, files: List[Path], stats: Dict[str, int], briefing_type: str) -> str:
        """Generate AI summary of completed tasks."""
        try:
            # Get file names and types
            task_list = "\n".join([f"- {f.name}" for f in files[:20]])  # Limit to 20
            
            prompt = f"""Summarize these completed tasks in a CEO-friendly {briefing_type} briefing.

Statistics:
- Total tasks: {stats['total']}
- LinkedIn posts: {stats['linkedin_post']}
- Emails processed: {stats['email']}
- Files processed: {stats['file_drop']}
- WhatsApp messages: {stats['whatsapp_message']}
- Payments flagged: {stats['payment']}
- Other: {stats['other']}

Recent completed tasks (last 20):
{task_list}

Provide:
1. Executive summary (2-3 sentences)
2. Key accomplishments
3. Any patterns or insights
4. Suggested focus for tomorrow

Keep it concise and professional."""

            response = self.client.chat.completions.create(
                model=Config.OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": f"You are a business analyst creating a {briefing_type} briefing."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=600
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} AI summary failed: {e}")
            return self._basic_summary(stats)
    
    def _ai_ceo_briefing(self, files: List[Path], stats: Dict[str, int], business_goals: str) -> str:
        """Generate AI CEO briefing."""
        try:
            task_list = "\n".join([f"- {f.name}" for f in files[:30]])
            
            prompt = f"""Act as a business analyst. Based on these completed tasks and business goals,
write a Monday Morning CEO Briefing.

BUSINESS GOALS:
{business_goals}

COMPLETED TASKS (past 7 days):
{task_list}

STATISTICS:
- Total: {stats['total']}
- LinkedIn: {stats['linkedin_post']}
- Emails: {stats['email']}
- Files: {stats['file_drop']}
- WhatsApp: {stats['whatsapp_message']}
- Payments: {stats['payment']}

Create briefing with:
1. Revenue Impact Summary (what drove value)
2. Bottlenecks Found (what slowed us down)
3. 3 Proactive Suggestions for next week
4. Priority Focus Areas

Format professionally for CEO review."""

            response = self.client.chat.completions.create(
                model=Config.OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": "You are a strategic business analyst reporting to the CEO."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} AI CEO briefing failed: {e}")
            return self._basic_summary(stats)
    
    def _basic_summary(self, stats: Dict[str, int]) -> str:
        """Generate basic summary without AI."""
        return f"""## Activity Summary

- Total tasks completed: {stats['total']}
- LinkedIn posts: {stats['linkedin_post']}
- Emails processed: {stats['email']}
- Files processed: {stats['file_drop']}
- WhatsApp messages: {stats['whatsapp_message']}
- Payments flagged: {stats['payment']}
- Other: {stats['other']}

AI not available for detailed analysis."""
    
    def _save_briefing(self, summary: str, stats: Dict[str, int], briefing_type: str) -> Path:
        """Save briefing to file."""
        Config.BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        if briefing_type == "daily":
            filename = f"{today}_daily.md"
            title = "Daily Briefing"
        elif briefing_type == "weekly_ceo":
            filename = f"{today}_CEO_briefing.md"
            title = "Weekly CEO Briefing"
        else:
            filename = f"{today}_{briefing_type}.md"
            title = briefing_type.title()
        
        filepath = Config.BRIEFINGS_DIR / filename
        
        content = f"""---
type: {briefing_type}
generated: {datetime.now().isoformat()}
period: last 24 hours
---
# {title}

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Statistics
- Total tasks: {stats['total']}
- LinkedIn posts: {stats['linkedin_post']}
- Emails: {stats['email']}
- Files: {stats['file_drop']}
- WhatsApp: {stats['whatsapp_message']}
- Payments: {stats['payment']}

---

{summary}

---
*Generated automatically by AI Employee Scheduler*
"""
        
        filepath.write_text(content, encoding="utf-8")
        
        return filepath


class TaskScheduler:
    """Main scheduler service."""
    
    def __init__(self):
        self.briefing_generator = AIBriefingGenerator()
        self.running = True
        self._setup_schedule()
    
    def _setup_schedule(self):
        """Set up all scheduled tasks."""
        # Daily briefing at 08:00
        schedule.every().day.at("08:00").do(
            self.briefing_generator.generate_daily_briefing
        )
        print(f"{Fore.GREEN}[SCHEDULED]{Style.RESET_ALL} Daily briefing at 08:00")
        
        # LinkedIn post idea at 10:00
        schedule.every().day.at("10:00").do(
            self.briefing_generator.generate_linkedin_post_idea
        )
        print(f"{Fore.GREEN}[SCHEDULED]{Style.RESET_ALL} LinkedIn post idea at 10:00")
        
        # Weekly CEO briefing on Sunday at 21:00
        schedule.every().sunday.at("21:00").do(
            self.briefing_generator.generate_weekly_ceo_briefing
        )
        print(f"{Fore.GREEN}[SCHEDULED]{Style.RESET_ALL} Weekly CEO briefing on Sunday at 21:00")
        
        # Needs_Action check every 30 seconds
        schedule.every(Config.NEEDS_ACTION_INTERVAL // 60).minutes.do(
            self._check_needs_action
        )
        print(f"{Fore.GREEN}[SCHEDULED]{Style.RESET_ALL} Needs_Action check every {Config.NEEDS_ACTION_INTERVAL}s")
        
        # Approval check every 15 seconds (via approval_manager import)
        schedule.every(Config.APPROVAL_INTERVAL // 60).minutes.do(
            self._check_approvals
        )
        print(f"{Fore.GREEN}[SCHEDULED]{Style.RESET_ALL} Approval check every {Config.APPROVAL_INTERVAL}s")
        
        # LinkedIn posts every 10 minutes
        schedule.every(Config.LINKEDIN_INTERVAL // 60).minutes.do(
            self._check_linkedin_posts
        )
        print(f"{Fore.GREEN}[SCHEDULED]{Style.RESET_ALL} LinkedIn posts check every {Config.LINKEDIN_INTERVAL // 60} minutes")
    
    def _check_needs_action(self):
        """Check Needs_Action folder for new tasks."""
        try:
            if not Config.NEEDS_ACTION_DIR.exists():
                return
            
            task_files = list(Config.NEEDS_ACTION_DIR.glob("*.md"))
            if task_files:
                print(f"{Fore.CYAN}[TASKS]{Style.RESET_ALL} {len(task_files)} task(s) in Needs_Action")
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Needs_Action check failed: {e}")
    
    def _check_approvals(self):
        """Check approvals using approval_manager."""
        try:
            from approval_manager import ApprovalManager
            manager = ApprovalManager()
            manager.scan_and_process()
        except ImportError:
            pass
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Approval check failed: {e}")
    
    def _check_linkedin_posts(self):
        """Check LinkedIn approved posts."""
        try:
            from linkedin_poster import LinkedInPoster
            poster = LinkedInPoster()
            posted = poster.post_approved_content()
            if posted > 0:
                print(f"{Fore.GREEN}[LINKEDIN]{Style.RESET_ALL} Posted {posted} content(s)")
        except ImportError:
            pass
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} LinkedIn check failed: {e}")
    
    def run(self):
        """Run the scheduler loop."""
        print(f"\n{Fore.GREEN}[START]{Style.RESET_ALL} Scheduler running. Press Ctrl+C to stop.\n")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Scheduler error: {e}")
                time.sleep(5)
        
        print(f"{Fore.YELLOW}[SHUTDOWN]{Style.RESET_ALL} Scheduler stopped.")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False


def print_banner():
    """Print the startup banner."""
    banner = f"""
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.YELLOW}           AI EMPLOYEE SCHEDULER SERVICE{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.CYAN}Vault Dir:     {Fore.GREEN}{Config.VAULT_DIR}{Style.RESET_ALL}
{Fore.CYAN}Briefings Dir: {Fore.GREEN}{Config.BRIEFINGS_DIR}{Style.RESET_ALL}
{Fore.CYAN}Logs Dir:      {Fore.GREEN}{Config.LOGS_DIR}{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
"""
    print(banner)


def ensure_directories():
    """Ensure all required directories exist."""
    try:
        Config.BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
        Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to create directories: {e}")
        raise


def signal_handler(signum, frame):
    """Handle Ctrl+C and other termination signals."""
    print(f"\n{Fore.YELLOW}[SHUTDOWN]{Style.RESET_ALL} Received termination signal...")
    print(f"{Fore.GREEN}[GOODBYE]{Style.RESET_ALL} Scheduler stopped gracefully.")
    sys.exit(0)


def main():
    """Main entry point for the scheduler service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Employee Scheduler")
    parser.add_argument("--daily", action="store_true", help="Run daily briefing now")
    parser.add_argument("--weekly", action="store_true", help="Run CEO briefing now")
    parser.add_argument("--linkedin", action="store_true", help="Generate LinkedIn idea now")
    parser.add_argument("--once", action="store_true", help="Run scheduled tasks once and exit")
    
    args = parser.parse_args()
    
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
        
        # Handle one-time commands BEFORE creating scheduler
        if args.daily:
            generator = AIBriefingGenerator()
            generator.generate_daily_briefing()
            return
        elif args.weekly:
            generator = AIBriefingGenerator()
            generator.generate_weekly_ceo_briefing()
            return
        elif args.linkedin:
            generator = AIBriefingGenerator()
            generator.generate_linkedin_post_idea()
            return
        elif args.once:
            print(f"\n{Fore.CYAN}[RUNNING]{Style.RESET_ALL} All scheduled tasks once...")
            scheduler = TaskScheduler()
            schedule.run_all()
            return
        
        # Create scheduler for continuous mode
        scheduler = TaskScheduler()
        
        # Run scheduler loop
        scheduler.run()
        
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# pip install schedule openai colorama python-dotenv
