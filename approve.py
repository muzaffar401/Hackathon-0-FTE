#!/usr/bin/env python3
"""
Approval Manager
Review and approve/reject pending tasks.
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

from colorama import init, Fore, Style
from dotenv import load_dotenv

init(autoreset=True)
load_dotenv()


class Config:
    HOME = Path.home()
    VAULT_DIR = HOME / "AI_Employee_Vault"
    PROJECT_DIR = HOME / "AI_Employee_Project"
    
    PENDING_DIR = VAULT_DIR / "Pending_Approval"
    DONE_DIR = VAULT_DIR / "Done"
    PLANS_DIR = PROJECT_DIR / "Plans"
    LOGS_DIR = VAULT_DIR / "Logs"


def list_pending():
    """List all pending approval files."""
    if not Config.PENDING_DIR.exists():
        return []
    return sorted(Config.PENDING_DIR.glob("*.md"))


def read_plan(path: Path) -> str:
    """Read plan file content."""
    return path.read_text(encoding="utf-8")


def log_approval(plan_name: str, action: str):
    """Log approval/rejection action."""
    Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = Config.LOGS_DIR / f"{today}.json"
    
    import json
    logs = []
    if log_file.exists():
        try:
            logs = json.loads(log_file.read_text(encoding="utf-8"))
        except:
            logs = []
    
    logs.append({
        "type": "approval_action",
        "timestamp": datetime.now().isoformat(),
        "data": {"file": plan_name, "action": action}
    })
    
    log_file.write_text(json.dumps(logs, indent=2), encoding="utf-8")


def approve_file(plan_path: Path):
    """Approve a pending file - move to Done."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = Config.DONE_DIR / f"{timestamp}_APPROVED_{plan_path.name}"
        shutil.move(str(plan_path), str(dest))
        log_approval(plan_path.name, "APPROVED")
        print(f"{Fore.GREEN}[APPROVED]{Style.RESET_ALL} Moved to Done: {dest.name}")
        return True
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to approve: {e}")
        return False


def reject_file(plan_path: Path):
    """Reject a pending file - move back to Needs_Action as new task."""
    try:
        from pathlib import Path
        needs_action = Config.VAULT_DIR / "Needs_Action"
        needs_action.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = needs_action / f"{timestamp}_REJECTED_{plan_path.name}"
        shutil.move(str(plan_path), str(dest))
        log_approval(plan_path.name, "REJECTED")
        print(f"{Fore.YELLOW}[REJECTED]{Style.RESET_ALL} Moved to Needs_Action: {dest.name}")
        return True
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to reject: {e}")
        return False


def show_menu():
    """Show interactive approval menu."""
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}         PENDING APPROVAL MANAGER{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    pending = list_pending()
    
    if not pending:
        print(f"{Fore.GREEN}No pending approvals.{Style.RESET_ALL}")
        return
    
    print(f"Found {len(pending)} pending item(s):\n")
    
    for i, path in enumerate(pending, 1):
        print(f"  [{i}] {path.name}")
    
    print(f"\n  [a] Approve all")
    print(f"  [r] Reject all")
    print(f"  [q] Quit")
    
    while True:
        try:
            choice = input(f"\n{Fore.CYAN}Select action [1-{len(pending)}, a, r, q]: {Style.RESET_ALL}").strip().lower()
            
            if choice == "q":
                print(f"{Fore.YELLOW}Exiting.{Style.RESET_ALL}")
                return
            elif choice == "a":
                for path in pending:
                    approve_file(path)
                print(f"{Fore.GREEN}All approved.{Style.RESET_ALL}")
                return
            elif choice == "r":
                for path in pending:
                    reject_file(path)
                print(f"{Fore.YELLOW}All rejected.{Style.RESET_ALL}")
                return
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(pending):
                    selected = pending[idx]
                    print(f"\n{Fore.CYAN}{'-'*60}{Style.RESET_ALL}")
                    print(f"File: {selected.name}")
                    print(f"{Fore.CYAN}{'-'*60}{Style.RESET_ALL}")
                    
                    # Show preview
                    content = read_plan(selected)
                    # Show first 50 lines
                    lines = content.split("\n")[:50]
                    print("\n".join(lines))
                    if len(content.split("\n")) > 50:
                        print(f"\n... ({len(content.split(chr(10))) - 50} more lines)")
                    
                    action = input(f"\n{Fore.CYAN}Approve/Reject/Skip [a/r/s]: {Style.RESET_ALL}").strip().lower()
                    
                    if action == "a":
                        approve_file(selected)
                    elif action == "r":
                        reject_file(selected)
                    else:
                        print(f"{Fore.YELLOW}Skipped.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Invalid selection.{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Invalid option.{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Exiting.{Style.RESET_ALL}")
            return
        except EOFError:
            print(f"\n{Fore.YELLOW}Exiting.{Style.RESET_ALL}")
            return


def main():
    if len(sys.argv) > 1:
        # Command line mode
        cmd = sys.argv[1]
        if cmd == "list":
            pending = list_pending()
            if pending:
                for p in pending:
                    print(p.name)
            else:
                print("No pending approvals.")
        elif cmd == "approve" and len(sys.argv) > 2:
            name = sys.argv[2]
            path = Config.PENDING_DIR / name
            if path.exists():
                approve_file(path)
            else:
                print(f"{Fore.RED}File not found: {name}{Style.RESET_ALL}")
        else:
            print(f"Usage: python approve.py [list|approve <filename>]")
    else:
        # Interactive mode
        show_menu()


if __name__ == "__main__":
    main()

# pip install colorama python-dotenv
