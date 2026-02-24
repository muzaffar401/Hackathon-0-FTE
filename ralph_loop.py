"""
Ralph Wiggum Pattern - Autonomous AI Agent Loop

This module implements a persistent worker pattern that keeps Qwen AI
working on a task until it's fully complete or max iterations reached.

Usage:
    ralph = RalphLoop(
        task_description="Your task here",
        completion_check_fn=lambda r: "<TASK_COMPLETE>" in r,
        max_iterations=10
    )
    result = ralph.run()
"""

import os
import json
import time
import shutil
import requests
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any, Union
from dotenv import load_dotenv
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "Logs"
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
DONE_DIR = BASE_DIR / "Done"
APPROVED_DIR = BASE_DIR / "Approved"
PENDING_DIR = BASE_DIR / "Pending_Approval"

# Ensure directories exist
for directory in [LOGS_DIR, NEEDS_ACTION_DIR, DONE_DIR, APPROVED_DIR, PENDING_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Qwen/OpenAI configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

# Ralph-specific configuration
RALPH_TEMPERATURE = 0.3  # Low temperature for consistent, focused output
RALPH_MAX_TOKENS = 4000  # High token limit for detailed work


class RalphLoop:
    """
    Autonomous AI worker loop that persists until task completion.
    
    Implements the "Ralph Wiggum" pattern - keeps working on a task
    until fully complete or max iterations reached.
    """
    
    def __init__(
        self,
        task_description: str,
        completion_check_fn: Optional[Callable[[str], bool]] = None,
        max_iterations: int = 10,
        delay_between_iterations: float = 1.0
    ):
        """
        Initialize Ralph Loop.
        
        Args:
            task_description: Clear description of the task to complete
            completion_check_fn: Function that takes response string and returns True if complete.
                                If None, defaults to checking for <TASK_COMPLETE> tag.
            max_iterations: Maximum number of iterations before giving up
            delay_between_iterations: Seconds to wait between iterations
        """
        self.task = task_description
        self.max_iter = max_iterations
        self.delay = delay_between_iterations
        self.iteration = 0
        self.history: List[Dict[str, str]] = []
        self.responses: List[str] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Default completion check - look for the tag
        if completion_check_fn is None:
            self.check_complete = lambda r: "<TASK_COMPLETE>" in r
        else:
            self.check_complete = completion_check_fn
        
        # System prompt for autonomous worker behavior
        self.system_prompt = """You are an autonomous AI worker. Your job is to complete tasks fully and thoroughly.

IMPORTANT RULES:
1. Work through the task step by step
2. Show your work and reasoning clearly
3. When the task is 100% complete, end your response with: <TASK_COMPLETE>
4. If the task is not yet complete, do NOT include <TASK_COMPLETE> - keep working
5. Each response should make meaningful progress toward completion
6. If you need more information or hit a blocker, state it clearly

Remember: Quality over speed. Complete the task properly before marking it done."""
    
    def _log(self, message: str, level: str = "INFO"):
        """Log message to console and file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [RALPH] [{level}] {message}\n"
        
        # Write to log file
        log_file = LOGS_DIR / "ralph_loop.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        # Print to console with colors
        if level == "ERROR":
            print(f"{Fore.RED}[RALPH] [{level}] {message}")
        elif level == "SUCCESS":
            print(f"{Fore.GREEN}[RALPH] [{level}] {message}")
        elif level == "WARNING":
            print(f"{Fore.YELLOW}[RALPH] [{level}] {message}")
        elif level == "ITERATION":
            print(f"{Fore.CYAN}[RALPH] [{level}] {message}")
        else:
            print(f"{Fore.WHITE}[RALPH] [{level}] {message}")
    
    def _call_qwen(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """
        Call Qwen/OpenRouter API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
        
        Returns:
            Response content string, or None if failed
        """
        try:
            if not OPENROUTER_API_KEY:
                self._log("OPENROUTER_API_KEY not set. Cannot call Qwen.", "ERROR")
                return None
            
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/ralph-loop",
                "X-Title": "Ralph Loop Agent"
            }
            
            payload = {
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "max_tokens": RALPH_MAX_TOKENS,
                "temperature": RALPH_TEMPERATURE
            }
            
            response = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120  # Longer timeout for complex tasks
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return content.strip()
            
        except requests.exceptions.Timeout:
            self._log("Qwen API request timed out", "ERROR")
            return None
        except requests.exceptions.RequestException as e:
            self._log(f"Qwen API request failed: {str(e)}", "ERROR")
            return None
        except Exception as e:
            self._log(f"Error calling Qwen: {str(e)}", "ERROR")
            return None
    
    def _build_messages(self) -> List[Dict[str, str]]:
        """Build the messages list for Qwen API call."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"TASK: {self.task}\n\nBegin working on this task now."}
        ]
        
        # Add conversation history
        for msg in self.history:
            messages.append(msg)
        
        return messages
    
    def _save_iteration_log(self, iteration: int, response: str, is_complete: bool):
        """Save detailed iteration log."""
        log_file = LOGS_DIR / f"ralph_iteration_{iteration:03d}.md"
        
        # Create summary of response (first 500 chars)
        response_summary = response[:500] + "..." if len(response) > 500 else response
        
        content = f"""# Ralph Loop - Iteration {iteration}

**Timestamp:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Task:** {self.task}
**Complete:** {is_complete}

## Response Summary

{response_summary}

## Full Response

{response}

---
*Generated by ralph_loop.py*
"""
        
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(content)
    
    def _create_failure_alert(self):
        """Create alert file when max iterations reached without completion."""
        alert_file = NEEDS_ACTION_DIR / f"RALPH_FAILED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        # Create task summary from history
        task_summary = "\n\n".join([
            f"### Iteration {i+1}\n{resp[:300]}..."
            for i, resp in enumerate(self.responses[-3:])  # Last 3 responses
        ])
        
        content = f"""---
type: ralph_failure
task: {self.task}
iterations_used: {self.iteration}
max_iterations: {self.max_iter}
failed_at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
status: needs_human_intervention
---
# Ralph Loop Failed to Complete Task

## Task Description

{self.task}

## Failure Details

- **Iterations Used:** {self.iteration} of {self.max_iter}
- **Start Time:** {self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else "N/A"}
- **End Time:** {self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else "N/A"}

## Recent Attempts

{task_summary}

## Human Action Required

The AI worker was unable to complete this task within the iteration limit.
Please review the logs in /Logs/ and either:
1. Break the task into smaller subtasks
2. Provide more specific instructions
3. Complete the task manually

---
*Generated by ralph_loop.py*
"""
        
        with open(alert_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        self._log(f"Failure alert created: {alert_file.name}", "WARNING")
        return alert_file
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the Ralph Loop until completion or max iterations.
        
        Returns:
            Dict with: success, iterations_used, final_response, history
        """
        import requests  # Import here to avoid circular dependency issues
        
        self._log(f"Starting Ralph Loop for task: {self.task[:100]}...", "INFO")
        self._log(f"Max iterations: {self.max_iter}", "INFO")
        
        self.start_time = datetime.now()
        self.iteration = 0
        self.history = []
        self.responses = []
        
        while self.iteration < self.max_iter:
            self.iteration += 1
            self._log(f"=== Iteration {self.iteration}/{self.max_iter} ===", "ITERATION")
            
            # Build messages with full history
            messages = self._build_messages()
            
            # Call Qwen
            self._log("Calling Qwen...", "INFO")
            response = self._call_qwen(messages)
            
            if response is None:
                self._log("Qwen call failed. Retrying...", "WARNING")
                time.sleep(self.delay)
                continue
            
            # Save response
            self.responses.append(response)
            self._save_iteration_log(self.iteration, response, False)
            
            # Log response summary
            response_preview = response[:200].replace("\n", " ") + "..." if len(response) > 200 else response.replace("\n", " ")
            self._log(f"Response: {response_preview}", "INFO")
            
            # Check for completion
            is_complete = self.check_complete(response)
            
            if is_complete:
                self.end_time = datetime.now()
                self._log(f"Task completed in {self.iteration} iteration(s)!", "SUCCESS")
                
                # Final log
                duration = (self.end_time - self.start_time).total_seconds()
                self._log(f"Total duration: {duration:.1f} seconds", "INFO")
                
                return {
                    "success": True,
                    "iterations_used": self.iteration,
                    "final_response": response,
                    "history": self.history.copy(),
                    "all_responses": self.responses.copy(),
                    "duration_seconds": duration,
                    "task": self.task
                }
            
            # Not complete - add to history and continue
            self.history.append({"role": "assistant", "content": response})
            
            # Add continuation prompt
            continuation_prompt = "Continue working on the task. You have not finished yet. "
            if self.iteration > 1:
                continuation_prompt += f"You have {self.max_iter - self.iteration} iteration(s) remaining. "
            continuation_prompt += "Review your previous work above and keep making progress. "
            continuation_prompt += "When the task is 100% complete, end with <TASK_COMPLETE>."
            
            self.history.append({"role": "user", "content": continuation_prompt})
            
            # Delay before next iteration
            if self.iteration < self.max_iter:
                self._log(f"Waiting {self.delay}s before next iteration...", "INFO")
                time.sleep(self.delay)
        
        # Max iterations reached without completion
        self.end_time = datetime.now()
        self._log(f"Max iterations ({self.max_iter}) reached without completion", "ERROR")
        
        # Create failure alert
        self._create_failure_alert()
        
        duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            "success": False,
            "iterations_used": self.iteration,
            "final_response": self.responses[-1] if self.responses else None,
            "history": self.history.copy(),
            "all_responses": self.responses.copy(),
            "duration_seconds": duration,
            "task": self.task,
            "failure_reason": "max_iterations_reached"
        }


# ============================================================================
# BUILT-IN COMPLETION CHECKERS
# ============================================================================

def file_moved_to_done(filename: str) -> Callable[[str], bool]:
    """
    Returns a completion checker that verifies if a file exists in /Done/.
    
    Usage:
        checker = file_moved_to_done("myfile.md")
        ralph = RalphLoop(task, completion_check_fn=checker)
    """
    def check(response: str) -> bool:
        return (DONE_DIR / filename).exists()
    return check


def file_created(filepath: Union[str, Path]) -> Callable[[str], bool]:
    """
    Returns a completion checker that verifies if a file exists at path.
    
    Usage:
        checker = file_created("/path/to/file.md")
        ralph = RalphLoop(task, completion_check_fn=checker)
    """
    path = Path(filepath)
    def check(response: str) -> bool:
        return path.exists()
    return check


def contains_phrase(phrase: str) -> Callable[[str], bool]:
    """
    Returns a completion checker that looks for a phrase in the response.
    
    Usage:
        checker = contains_phrase("TASK_COMPLETE")
        ralph = RalphLoop(task, completion_check_fn=checker)
    """
    def check(response: str) -> bool:
        return phrase in response
    return check


def all_files_processed() -> Callable[[str], bool]:
    """
    Returns a completion checker that verifies Needs_Action is empty.
    
    Usage:
        checker = all_files_processed()
        ralph = RalphLoop("Process all files", completion_check_fn=checker)
    """
    def check(response: str) -> bool:
        if not NEEDS_ACTION_DIR.exists():
            return True
        files = [f for f in NEEDS_ACTION_DIR.iterdir() if f.is_file() and not f.name.startswith(".")]
        return len(files) == 0
    return check


def directory_empty(dirpath: Union[str, Path]) -> Callable[[str], bool]:
    """
    Returns a completion checker that verifies a directory is empty.
    
    Usage:
        checker = directory_empty("/path/to/dir")
        ralph = RalphLoop(task, completion_check_fn=checker)
    """
    path = Path(dirpath)
    def check(response: str) -> bool:
        if not path.exists():
            return True
        files = [f for f in path.iterdir() if f.is_file() and not f.name.startswith(".")]
        return len(files) == 0
    return check


def compound_check(*checkers: Callable[[str], bool], require_all: bool = True) -> Callable[[str], bool]:
    """
    Returns a completion checker that combines multiple checkers.
    
    Args:
        *checkers: Variable number of checker functions
        require_all: If True, all must pass. If False, any one passing is enough.
    
    Usage:
        checker = compound_check(
            file_moved_to_done("file1.md"),
            contains_phrase("TASK_COMPLETE")
        )
    """
    def check(response: str) -> bool:
        results = [checker(response) for checker in checkers]
        if require_all:
            return all(results)
        else:
            return any(results)
    return check


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def process_needs_action(max_iterations: int = 10) -> Dict[str, Any]:
    """
    Process all files in /Needs_Action/ directory.
    
    Usage:
        result = process_needs_action()
    """
    task = (
        "Process all files in /Needs_Action/ directory. "
        "For each file: 1) Read and understand the task, 2) Create a plan, "
        "3) Execute the plan, 4) Move the file to /Done/ when complete. "
        "Process ALL files in the directory."
    )
    
    ralph = RalphLoop(
        task_description=task,
        completion_check_fn=all_files_processed(),
        max_iterations=max_iterations
    )
    
    return ralph.run()


def generate_report(report_type: str, max_iterations: int = 5) -> Dict[str, Any]:
    """
    Generate a complete report of the specified type.
    
    Args:
        report_type: Type of report (e.g., "weekly CEO briefing", "financial summary")
        max_iterations: Max iterations for generation
    
    Usage:
        result = generate_report("weekly CEO briefing")
    """
    task = (
        f"Generate a complete {report_type}. "
        "Include all relevant sections, data, and analysis. "
        "Make it comprehensive and professional. "
        "Save the report to /Briefings/ directory."
    )
    
    ralph = RalphLoop(
        task_description=task,
        completion_check_fn=compound_check(
            contains_phrase("<TASK_COMPLETE>"),
            file_created(BASE_DIR / "Briefings")  # Checks if Briefings dir has content
        ),
        max_iterations=max_iterations
    )
    
    return ralph.run()


# ============================================================================
# MAIN / TESTING
# ============================================================================

if __name__ == "__main__":
    print(f"{Fore.CYAN}=== Ralph Loop - Autonomous AI Worker ===")
    print(f"Model: {OPENROUTER_MODEL}")
    print(f"API Key configured: {'Yes' if OPENROUTER_API_KEY else 'No'}")
    print()
    
    # Example 1: Simple task with tag-based completion
    print(f"{Fore.CYAN}--- Example 1: Simple Task ---")
    
    ralph1 = RalphLoop(
        task_description="Write a 3-paragraph summary of best practices for AI agent design. End with <TASK_COMPLETE> when done.",
        completion_check_fn=contains_phrase("<TASK_COMPLETE>"),
        max_iterations=3,
        delay_between_iterations=0.5
    )
    
    result1 = ralph1.run()
    print(f"\n{Fore.GREEN}Result: {'SUCCESS' if result1['success'] else 'FAILED'}")
    print(f"Iterations used: {result1['iterations_used']}")
    print()
    
    # Example 2: File-based completion check
    print(f"{Fore.CYAN}--- Example 2: File Processing ---")
    
    ralph2 = RalphLoop(
        task_description="Create a test file called 'ralph_test_output.txt' in the /Done/ directory with some content.",
        completion_check_fn=file_created(DONE_DIR / "ralph_test_output.txt"),
        max_iterations=3
    )
    
    result2 = ralph2.run()
    print(f"\n{Fore.GREEN}Result: {'SUCCESS' if result2['success'] else 'FAILED'}")
    print(f"Iterations used: {result2['iterations_used']}")
    print()
    
    # Example 3: Process Needs_Action directory
    print(f"{Fore.CYAN}--- Example 3: Process Needs_Action ---")
    
    if NEEDS_ACTION_DIR.exists() and any(NEEDS_ACTION_DIR.iterdir()):
        ralph3 = RalphLoop(
            task_description="Process all files in /Needs_Action/ - read each one, create appropriate output, and move to /Done/",
            completion_check_fn=all_files_processed(),
            max_iterations=5
        )
        
        result3 = ralph3.run()
        print(f"\n{Fore.GREEN}Result: {'SUCCESS' if result3['success'] else 'FAILED'}")
        print(f"Iterations used: {result3['iterations_used']}")
    else:
        print(f"{Fore.YELLOW}No files in /Needs_Action/ to process")
    
    print(f"\n{Fore.CYAN}=== Ralph Loop Demo Complete ===")
