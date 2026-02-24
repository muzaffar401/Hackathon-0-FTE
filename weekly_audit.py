"""
Weekly Audit - Monday Morning CEO Briefing Generator

Runs every Sunday at 21:00 to generate a comprehensive business audit
and CEO briefing for Monday morning.

Usage:
    python weekly_audit.py              # Run manually
    python weekly_audit.py --schedule   # Run as scheduler
"""

import os
import re
import json
import schedule
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
VAULT_DIR = BASE_DIR / "Briefings"
ACCOUNTING_DIR = BASE_DIR / "Accounting"
DONE_DIR = BASE_DIR / "Done"
PLANS_DIR = BASE_DIR / "Plans"
LOGS_DIR = BASE_DIR / "Logs"

# Ensure directories exist
for directory in [VAULT_DIR, ACCOUNTING_DIR, DONE_DIR, PLANS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Import other modules
try:
    from odoo_mcp import get_monthly_revenue, get_overdue_invoices, get_expenses, generate_financial_summary
    ODOO_AVAILABLE = True
except ImportError:
    ODOO_AVAILABLE = False
    print(f"{Fore.YELLOW}[WARNING] odoo_mcp not available - financial data will be limited")

try:
    from meta_poster import get_post_summary as get_meta_summary
    META_AVAILABLE = True
except ImportError:
    META_AVAILABLE = False
    print(f"{Fore.YELLOW}[WARNING] meta_poster not available - Meta data will be limited")

try:
    from twitter_poster import get_twitter_summary
    TWITTER_AVAILABLE = True
except ImportError:
    TWITTER_AVAILABLE = False
    print(f"{Fore.YELLOW}[WARNING] twitter_poster not available - Twitter data will be limited")

try:
    from ralph_loop import RalphLoop, contains_phrase, file_created
    RALPH_AVAILABLE = True
except ImportError:
    RALPH_AVAILABLE = False
    print(f"{Fore.YELLOW}[WARNING] ralph_loop not available - will use direct Qwen calls")

# Qwen/OpenAI configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

# Subscription patterns to detect
SUBSCRIPTION_PATTERNS = {
    'netflix': 'Netflix',
    'spotify': 'Spotify',
    'notion': 'Notion',
    'slack': 'Slack',
    'adobe': 'Adobe',
    'github': 'GitHub',
    'dropbox': 'Dropbox',
    'zoom': 'Zoom',
    'microsoft': 'Microsoft 365',
    'google': 'Google Workspace',
    'aws': 'Amazon Web Services',
    'azure': 'Microsoft Azure',
    'salesforce': 'Salesforce',
    'hubspot': 'HubSpot',
    'mailchimp': 'Mailchimp',
    'canva': 'Canva',
    'figma': 'Figma',
    'jetbrains': 'JetBrains'
}


def _log(message: str, level: str = "INFO"):
    """Log message to console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [AUDIT] [{level}] {message}\n"
    
    # Write to log file
    log_file = LOGS_DIR / "weekly_audit.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    # Print to console with colors
    if level == "ERROR":
        print(f"{Fore.RED}[AUDIT] [{level}] {message}")
    elif level == "SUCCESS":
        print(f"{Fore.GREEN}[AUDIT] [{level}] {message}")
    elif level == "WARNING":
        print(f"{Fore.YELLOW}[AUDIT] [{level}] {message}")
    elif level == "STEP":
        print(f"{Fore.CYAN}[AUDIT] [{level}] {message}")
    else:
        print(f"{Fore.WHITE}[AUDIT] [{level}] {message}")


def _call_qwen(messages: List[Dict[str, str]], temperature: float = 0.3) -> Optional[str]:
    """Call Qwen/OpenRouter API."""
    try:
        if not OPENROUTER_API_KEY:
            _log("OPENROUTER_API_KEY not set. Cannot call Qwen.", "ERROR")
            return None
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/weekly-audit",
            "X-Title": "Weekly Audit System"
        }
        
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "max_tokens": 4000,
            "temperature": temperature
        }
        
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        return content.strip()
        
    except requests.exceptions.Timeout:
        _log("Qwen API request timed out", "ERROR")
        return None
    except requests.exceptions.RequestException as e:
        _log(f"Qwen API request failed: {str(e)}", "ERROR")
        return None
    except Exception as e:
        _log(f"Error calling Qwen: {str(e)}", "ERROR")
        return None


# ============================================================================
# STEP 1: FINANCIAL DATA
# ============================================================================

def collect_financial_data() -> Dict[str, Any]:
    """
    Collect financial data from Odoo.
    
    Returns:
        Dict with revenue, expenses, profit, overdue invoices
    """
    _log("STEP 1: Collecting Financial Data", "STEP")
    
    financial_data = {
        "revenue": None,
        "expenses": None,
        "profit": 0.0,
        "profit_margin": 0.0,
        "overdue_invoices": [],
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if not ODOO_AVAILABLE:
        _log("Odoo module not available - skipping financial data", "WARNING")
        return financial_data
    
    try:
        current = datetime.now()
        year = current.year
        month = current.month
        
        # Get monthly revenue
        _log("Fetching monthly revenue from Odoo...", "INFO")
        revenue_data = get_monthly_revenue(year, month)
        if revenue_data:
            financial_data["revenue"] = revenue_data
            _log(f"Revenue: ${revenue_data.get('total_revenue', 0):,.2f}", "INFO")
        
        # Get overdue invoices
        _log("Fetching overdue invoices...", "INFO")
        overdue = get_overdue_invoices()
        if overdue:
            financial_data["overdue_invoices"] = overdue
            total_overdue = sum(inv.get("amount_due", inv.get("amount", 0)) for inv in overdue)
            _log(f"Overdue: {len(overdue)} invoices, ${total_overdue:,.2f} total", "WARNING")
        
        # Get expenses
        _log("Fetching monthly expenses...", "INFO")
        expenses_data = get_expenses(month, year)
        if expenses_data:
            financial_data["expenses"] = expenses_data
            _log(f"Expenses: ${expenses_data.get('total_expenses', 0):,.2f}", "INFO")
        
        # Calculate profit
        if revenue_data and expenses_data:
            revenue = revenue_data.get("total_revenue", 0)
            expenses = expenses_data.get("total_expenses", 0)
            financial_data["profit"] = round(revenue - expenses, 2)
            financial_data["profit_margin"] = round((financial_data["profit"] / revenue * 100) if revenue > 0 else 0, 2)
            _log(f"Profit: ${financial_data['profit']:,.2f} ({financial_data['profit_margin']}% margin)", "SUCCESS")
        
    except Exception as e:
        _log(f"Error collecting financial data: {str(e)}", "ERROR")
    
    return financial_data


# ============================================================================
# STEP 2: TASK COMPLETION DATA
# ============================================================================

def collect_task_data() -> Dict[str, Any]:
    """
    Analyze task completion data from /Done/ directory.
    
    Returns:
        Dict with task counts, completion times, bottlenecks
    """
    _log("STEP 2: Analyzing Task Completion Data", "STEP")
    
    task_data = {
        "completed_tasks": [],
        "task_counts": {
            "emails": 0,
            "whatsapp": 0,
            "files": 0,
            "social_posts": 0,
            "other": 0
        },
        "longest_tasks": [],
        "bottlenecks": [],
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        # Scan /Done/ directory
        if DONE_DIR.exists():
            _log(f"Scanning {DONE_DIR} for completed tasks...", "INFO")
            
            for filepath in DONE_DIR.iterdir():
                if not filepath.is_file():
                    continue
                
                # Check if modified in last 7 days
                try:
                    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                    if mtime < seven_days_ago:
                        continue
                except Exception:
                    continue
                
                # Categorize by type
                filename = filepath.name.lower()
                if "email" in filename:
                    task_data["task_counts"]["emails"] += 1
                elif "whatsapp" in filename:
                    task_data["task_counts"]["whatsapp"] += 1
                elif "meta" in filename or "twitter" in filename or "social" in filename:
                    task_data["task_counts"]["social_posts"] += 1
                elif filepath.suffix in [".md", ".txt", ".pdf", ".doc"]:
                    task_data["task_counts"]["files"] += 1
                else:
                    task_data["task_counts"]["other"] += 1
                
                # Read file for timing info
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Try to extract timestamps from frontmatter
                    created = None
                    completed = None
                    
                    if "---" in content:
                        lines = content.split("\n")
                        in_frontmatter = False
                        for line in lines:
                            if line.strip() == "---":
                                in_frontmatter = not in_frontmatter
                                continue
                            if in_frontmatter:
                                if "generated:" in line or "created:" in line:
                                    try:
                                        date_str = line.split(":", 1)[1].strip()
                                        created = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
                                    except ValueError:
                                        pass
                                if "posted_at:" in line or "completed:" in line:
                                    try:
                                        date_str = line.split(":", 1)[1].strip()
                                        completed = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
                                    except ValueError:
                                        pass
                    
                    if created and completed:
                        duration = (completed - created).total_seconds() / 60  # minutes
                        task_data["completed_tasks"].append({
                            "file": filepath.name,
                            "duration_minutes": round(duration, 1),
                            "completed_at": completed.strftime("%Y-%m-%d %H:%M:%S")
                        })
                
                except Exception:
                    pass
        
        # Find longest tasks
        if task_data["completed_tasks"]:
            sorted_tasks = sorted(task_data["completed_tasks"], 
                                  key=lambda x: x["duration_minutes"], 
                                  reverse=True)
            task_data["longest_tasks"] = sorted_tasks[:5]
            _log(f"Completed {len(task_data['completed_tasks'])} tasks this week", "INFO")
        
        # Check for bottlenecks in /Plans/
        if PLANS_DIR.exists():
            _log("Checking for bottlenecks in /Plans/...", "INFO")
            three_days_ago = datetime.now() - timedelta(days=3)
            
            for filepath in PLANS_DIR.iterdir():
                if not filepath.is_file():
                    continue
                
                try:
                    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                    if mtime < three_days_ago:
                        days_old = (datetime.now() - mtime).days
                        task_data["bottlenecks"].append({
                            "file": filepath.name,
                            "days_stagnant": days_old
                        })
                except Exception:
                    pass
            
            if task_data["bottlenecks"]:
                _log(f"Found {len(task_data['bottlenecks'])} stagnant plans", "WARNING")
        
    except Exception as e:
        _log(f"Error collecting task data: {str(e)}", "ERROR")
    
    return task_data


# ============================================================================
# STEP 3: SOCIAL MEDIA PERFORMANCE
# ============================================================================

def collect_social_data() -> Dict[str, Any]:
    """
    Collect social media performance data.
    
    Returns:
        Dict with combined social metrics
    """
    _log("STEP 3: Collecting Social Media Performance", "STEP")
    
    social_data = {
        "meta": None,
        "twitter": None,
        "total_posts": 0,
        "total_engagement": 0,
        "best_platform": None,
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Get Meta (Facebook/Instagram) data
    if META_AVAILABLE:
        try:
            _log("Fetching Meta (Facebook/Instagram) summary...", "INFO")
            meta_summary = get_meta_summary()
            if meta_summary:
                # Try to read the generated file
                try:
                    with open(meta_summary, "r", encoding="utf-8") as f:
                        content = f.read()
                    social_data["meta"] = {"file": meta_summary, "content_preview": content[:500]}
                except Exception:
                    social_data["meta"] = {"file": meta_summary}
                _log("Meta data collected", "INFO")
        except Exception as e:
            _log(f"Error fetching Meta data: {str(e)}", "WARNING")
    
    # Get Twitter data
    if TWITTER_AVAILABLE:
        try:
            _log("Fetching Twitter summary...", "INFO")
            twitter_summary = get_twitter_summary()
            if twitter_summary:
                try:
                    with open(twitter_summary, "r", encoding="utf-8") as f:
                        content = f.read()
                    social_data["twitter"] = {"file": twitter_summary, "content_preview": content[:500]}
                except Exception:
                    social_data["twitter"] = {"file": twitter_summary}
                _log("Twitter data collected", "INFO")
        except Exception as e:
            _log(f"Error fetching Twitter data: {str(e)}", "WARNING")
    
    # Determine best platform (simplified - would need actual metrics)
    platforms_active = []
    if social_data["meta"]:
        platforms_active.append("Meta (Facebook/Instagram)")
    if social_data["twitter"]:
        platforms_active.append("Twitter")
    
    social_data["total_posts"] = len(platforms_active)
    
    if platforms_active:
        social_data["best_platform"] = platforms_active[0]  # Default to first active
    
    _log(f"Social data collected from {len(platforms_active)} platform(s)", "INFO")
    
    return social_data


# ============================================================================
# STEP 4: SUBSCRIPTION AUDIT
# ============================================================================

def audit_subscriptions() -> Dict[str, Any]:
    """
    Audit recurring subscriptions from accounting summaries.
    
    Returns:
        Dict with detected subscriptions and flags
    """
    _log("STEP 4: Auditing Subscriptions", "STEP")
    
    subscription_data = {
        "detected_subscriptions": [],
        "flagged_subscriptions": [],
        "total_monthly_recurring": 0.0,
        "audited_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        # Look for accounting summaries
        if not ACCOUNTING_DIR.exists():
            _log("Accounting directory not found", "WARNING")
            return subscription_data
        
        # Find most recent summary
        summaries = sorted(ACCOUNTING_DIR.glob("*_summary.md"), reverse=True)
        
        if not summaries:
            _log("No accounting summaries found", "INFO")
            return subscription_data
        
        latest_summary = summaries[0]
        _log(f"Reading {latest_summary.name}...", "INFO")
        
        with open(latest_summary, "r", encoding="utf-8") as f:
            content = f.read().lower()
        
        # Detect subscriptions
        for key, name in SUBSCRIPTION_PATTERNS.items():
            if key in content:
                subscription_data["detected_subscriptions"].append({
                    "name": name,
                    "key": key,
                    "source": latest_summary.name
                })
                _log(f"Detected subscription: {name}", "INFO")
        
        # Flag subscriptions without recent justification
        # (Simplified logic - in production, would check against task completion)
        for sub in subscription_data["detected_subscriptions"]:
            # Flag if no related task found in /Done/ recently
            related_tasks = 0
            if DONE_DIR.exists():
                for filepath in DONE_DIR.iterdir():
                    if filepath.is_file():
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                file_content = f.read().lower()
                            if sub["key"] in file_content or sub["name"].lower() in file_content:
                                related_tasks += 1
                        except Exception:
                            pass
            
            if related_tasks == 0:
                subscription_data["flagged_subscriptions"].append({
                    **sub,
                    "reason": "No recent business activity detected",
                    "action": "Review necessity of this subscription"
                })
                _log(f"FLAGGED: {sub['name']} - no recent business justification", "WARNING")
        
        # Estimate monthly recurring (would need actual amounts in production)
        subscription_data["total_monthly_recurring"] = len(subscription_data["detected_subscriptions"]) * 50.0  # Placeholder
        
    except Exception as e:
        _log(f"Error auditing subscriptions: {str(e)}", "ERROR")
    
    return subscription_data


# ============================================================================
# STEP 5 & 6: CEO BRIEFING GENERATION
# ============================================================================

def generate_ceo_briefing(
    financial_data: Dict[str, Any],
    task_data: Dict[str, Any],
    social_data: Dict[str, Any],
    subscription_data: Dict[str, Any]
) -> Optional[str]:
    """
    Generate CEO briefing using Qwen via Ralph Loop.
    
    Returns:
        Path to generated briefing file, or None if failed
    """
    _log("STEP 5-6: Generating CEO Briefing", "STEP")
    
    try:
        # Prepare data summary for Qwen
        data_summary = f"""
## Financial Data
- Revenue: ${financial_data.get('revenue', {}).get('total_revenue', 'N/A')}
- Expenses: ${financial_data.get('expenses', {}).get('total_expenses', 'N/A')}
- Profit: ${financial_data.get('profit', 'N/A')}
- Profit Margin: {financial_data.get('profit_margin', 'N/A')}%
- Overdue Invoices: {len(financial_data.get('overdue_invoices', []))} invoices

## Task Completion (Last 7 Days)
- Emails: {task_data.get('task_counts', {}).get('emails', 0)}
- WhatsApp: {task_data.get('task_counts', {}).get('whatsapp', 0)}
- Files: {task_data.get('task_counts', {}).get('files', 0)}
- Social Posts: {task_data.get('task_counts', {}).get('social_posts', 0)}
- Longest Tasks: {[t['file'] for t in task_data.get('longest_tasks', [])[:3]]}
- Bottlenecks: {[b['file'] for b in task_data.get('bottlenecks', [])]}

## Social Media
- Platforms Active: {social_data.get('total_posts', 0)}
- Best Platform: {social_data.get('best_platform', 'N/A')}

## Subscriptions
- Detected: {[s['name'] for s in subscription_data.get('detected_subscriptions', [])]}
- Flagged for Review: {[s['name'] for s in subscription_data.get('flagged_subscriptions', [])]}
"""
        
        # Create the task for Ralph Loop
        briefing_task = f"""You are a senior business analyst. Based on the following business data, write a comprehensive Monday Morning CEO Briefing.

{data_summary}

Your briefing MUST include these sections:
1. **Executive Summary** - 3-4 sentences summarizing the week
2. **Revenue vs Target** - Analyze financial performance
3. **Top 3 Wins This Week** - Specific achievements with metrics
4. **Bottlenecks** - Identify issues with root cause analysis
5. **Cost Optimization** - Specific suggestions based on subscription audit
6. **Next Week Priorities** - 3-5 actionable priorities

Requirements:
- Be specific, not generic
- Use actual numbers from the data
- Flag any concerning trends
- End with <TASK_COMPLETE> when the briefing is complete"""

        # Use Ralph Loop if available, otherwise direct Qwen call
        if RALPH_AVAILABLE:
            _log("Using Ralph Loop for briefing generation...", "INFO")
            ralph = RalphLoop(
                task_description=briefing_task,
                completion_check_fn=contains_phrase("<TASK_COMPLETE>"),
                max_iterations=5,
                delay_between_iterations=2.0
            )
            result = ralph.run()
            briefing_content = result.get("final_response", "") if result else ""
        else:
            _log("Using direct Qwen call for briefing generation...", "INFO")
            messages = [
                {"role": "system", "content": "You are a senior business analyst. Write comprehensive CEO briefings."},
                {"role": "user", "content": briefing_task}
            ]
            briefing_content = _call_qwen(messages, temperature=0.3) or ""
        
        if not briefing_content:
            _log("Failed to generate briefing content", "ERROR")
            return None
        
        # Clean up content (remove <TASK_COMPLETE> tag)
        briefing_content = briefing_content.replace("<TASK_COMPLETE>", "").strip()
        
        # Save briefing
        today = datetime.now()
        filename = f"{today.strftime('%Y-%m-%d')}_CEO_briefing.md"
        filepath = VAULT_DIR / filename
        
        # Format as markdown with frontmatter
        revenue = financial_data.get('revenue', {}).get('total_revenue', 0) or 0
        expenses = financial_data.get('expenses', {}).get('total_expenses', 0) or 0
        profit = financial_data.get('profit', 0) or 0
        
        full_content = f"""---
generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
period: {(today - timedelta(days=7)).strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}
revenue: {revenue}
expenses: {expenses}
profit: {profit}
---

# Monday Morning CEO Briefing

{briefing_content}

---
*Generated by AI Employee Gold Tier - Weekly Audit System*
"""
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        _log(f"CEO Briefing saved to {filepath}", "SUCCESS")
        return str(filepath)
        
    except Exception as e:
        _log(f"Error generating CEO briefing: {str(e)}", "ERROR")
        return None


# ============================================================================
# STEP 7: UPDATE DASHBOARD
# ============================================================================

def update_dashboard(
    briefing_path: str,
    financial_data: Dict[str, Any]
) -> bool:
    """
    Update Dashboard.md with latest figures and briefing link.
    
    Returns:
        True if successful, False otherwise
    """
    _log("STEP 7: Updating Dashboard", "STEP")
    
    try:
        dashboard_path = BASE_DIR / "Dashboard.md"
        
        # Create dashboard if it doesn't exist
        if not dashboard_path.exists():
            dashboard_content = "# Dashboard\n\n"
        else:
            with open(dashboard_path, "r", encoding="utf-8") as f:
                dashboard_content = f.read()
        
        # Prepare update content
        today = datetime.now()
        revenue = financial_data.get('revenue', {}).get('total_revenue', 'N/A')
        expenses = financial_data.get('expenses', {}).get('total_expenses', 'N/A')
        profit = financial_data.get('profit', 'N/A')
        
        update_section = f"""
## Weekly Audit Summary (Updated {today.strftime('%Y-%m-%d %H:%M')})

| Metric | Value |
|--------|-------|
| Revenue | ${revenue} |
| Expenses | ${expenses} |
| Profit | ${profit} |
| Latest Briefing | [{today.strftime('%Y-%m-%d')} CEO Briefing]({briefing_path}) |

"""
        
        # Check if section exists and update it
        if "## Weekly Audit Summary" in dashboard_content:
            # Replace existing section
            lines = dashboard_content.split("\n")
            new_lines = []
            in_section = False
            
            for line in lines:
                if line.strip().startswith("## Weekly Audit Summary"):
                    in_section = True
                    new_lines.append(update_section.strip())
                elif in_section and line.strip().startswith("## "):
                    in_section = False
                    new_lines.append(line)
                elif not in_section:
                    new_lines.append(line)
            
            dashboard_content = "\n".join(new_lines)
        else:
            # Add new section
            dashboard_content += update_section
        
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(dashboard_content)
        
        _log("Dashboard updated successfully", "SUCCESS")
        return True
        
    except Exception as e:
        _log(f"Error updating dashboard: {str(e)}", "ERROR")
        return False


# ============================================================================
# MAIN AUDIT FUNCTION
# ============================================================================

def run_audit() -> Dict[str, Any]:
    """
    Run the complete weekly audit process.
    
    Returns:
        Dict with audit results and briefing path
    """
    _log("=" * 60, "INFO")
    _log("WEEKLY AUDIT STARTED", "SUCCESS")
    _log("=" * 60, "INFO")
    
    audit_result = {
        "success": False,
        "briefing_path": None,
        "financial_data": None,
        "task_data": None,
        "social_data": None,
        "subscription_data": None,
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "completed_at": None
    }
    
    try:
        # Step 1: Financial Data
        audit_result["financial_data"] = collect_financial_data()
        
        # Step 2: Task Data
        audit_result["task_data"] = collect_task_data()
        
        # Step 3: Social Data
        audit_result["social_data"] = collect_social_data()
        
        # Step 4: Subscription Audit
        audit_result["subscription_data"] = audit_subscriptions()
        
        # Step 5 & 6: Generate CEO Briefing
        briefing_path = generate_ceo_briefing(
            audit_result["financial_data"],
            audit_result["task_data"],
            audit_result["social_data"],
            audit_result["subscription_data"]
        )
        
        if briefing_path:
            audit_result["briefing_path"] = briefing_path
            
            # Step 7: Update Dashboard
            update_dashboard(briefing_path, audit_result["financial_data"])
            
            audit_result["success"] = True
            _log("=" * 60, "INFO")
            _log("WEEKLY AUDIT COMPLETED SUCCESSFULLY", "SUCCESS")
            _log(f"Briefing: {briefing_path}", "SUCCESS")
            _log("=" * 60, "INFO")
        else:
            _log("Failed to generate CEO briefing", "ERROR")
        
    except Exception as e:
        _log(f"Audit failed with error: {str(e)}", "ERROR")
        audit_result["error"] = str(e)
    
    audit_result["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return audit_result


# ============================================================================
# SCHEDULER
# ============================================================================

def run_scheduler():
    """Run the weekly audit scheduler (Sundays at 21:00)."""
    _log("Starting Weekly Audit Scheduler", "INFO")
    _log("Schedule: Every Sunday at 21:00", "INFO")
    
    # Schedule for Sunday at 21:00
    schedule.every().sunday.at("21:00").do(run_audit)
    
    _log("Scheduler started. Waiting for scheduled time...", "INFO")
    
    while True:
        schedule.run_pending()
        time.sleep(60)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print(f"{Fore.CYAN}=== Weekly Audit System ===")
    print(f"Odoo Integration: {'Available' if ODOO_AVAILABLE else 'Not available'}")
    print(f"Meta Integration: {'Available' if META_AVAILABLE else 'Not available'}")
    print(f"Twitter Integration: {'Available' if TWITTER_AVAILABLE else 'Not available'}")
    print(f"Ralph Loop: {'Available' if RALPH_AVAILABLE else 'Not available'}")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
        print(f"{Fore.CYAN}Running as scheduler (Sundays at 21:00)...")
        print(f"Press Ctrl+C to stop{Fore.RESET}")
        run_scheduler()
    else:
        print(f"{Fore.CYAN}Running manual audit...{Fore.RESET}")
        result = run_audit()
        
        if result["success"]:
            print(f"\n{Fore.GREEN}Audit completed successfully!")
            print(f"Briefing saved to: {result['briefing_path']}")
        else:
            print(f"\n{Fore.RED}Audit failed: {result.get('error', 'Unknown error')}")
