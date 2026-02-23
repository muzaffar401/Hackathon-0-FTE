#!/usr/bin/env python3
"""
Bronze Tier Test Suite
Tests folder structure, files, dependencies, API, and end-to-end functionality.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

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
    PLANS_DIR = VAULT_DIR / "Plans"
    LOGS_DIR = VAULT_DIR / "Logs"
    
    # Required files
    DASHBOARD_FILE = VAULT_DIR / "Dashboard.md"
    HANDBOOK_FILE = VAULT_DIR / "Company_Handbook.md"
    
    # Test file
    TEST_FILE = INBOX_DIR / "test_drop.txt"


class TestResult:
    """Store test results."""
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message


def print_header(text: str):
    """Print a formatted test header."""
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}TEST: {text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")


def print_result(result: TestResult):
    """Print test result with color."""
    if result.passed:
        status = f"{Fore.GREEN}[PASS]{Style.RESET_ALL}"
    else:
        status = f"{Fore.RED}[FAIL]{Style.RESET_ALL}"
    
    print(f"\n{status} {result.name}")
    if result.message:
        print(f"   {result.message}")


def test_folder_structure() -> TestResult:
    """TEST 1: Check required folder structure exists."""
    print_header("Folder Structure")
    
    required_folders = [
        ("Needs_Action", Config.NEEDS_ACTION_DIR),
        ("Inbox", Config.INBOX_DIR),
        ("Done", Config.DONE_DIR),
        ("Plans", Config.PLANS_DIR),
        ("Logs", Config.LOGS_DIR),
    ]
    
    missing = []
    existing = []
    
    for name, path in required_folders:
        if path.exists() and path.is_dir():
            existing.append(name)
            print(f"  {Fore.GREEN}[+]{Style.RESET_ALL} {name}: {path}")
        else:
            missing.append(name)
            print(f"  {Fore.RED}[-]{Style.RESET_ALL} {name}: {path} (MISSING)")
    
    if missing:
        return TestResult(
            "Folder Structure",
            False,
            f"Missing folders: {', '.join(missing)}"
        )
    
    return TestResult(
        "Folder Structure",
        True,
        f"All {len(existing)} folders exist"
    )


def test_required_files() -> TestResult:
    """TEST 2: Check Dashboard.md and Company_Handbook.md exist and are not empty."""
    print_header("Required Files")
    
    files_to_check = [
        ("Dashboard.md", Config.DASHBOARD_FILE),
        ("Company_Handbook.md", Config.HANDBOOK_FILE),
    ]
    
    all_ok = True
    issues = []
    
    for name, path in files_to_check:
        if not path.exists():
            print(f"  {Fore.RED}[-]{Style.RESET_ALL} {name}: FILE NOT FOUND")
            all_ok = False
            issues.append(f"{name} not found")
        elif path.stat().st_size == 0:
            print(f"  {Fore.RED}[-]{Style.RESET_ALL} {name}: FILE IS EMPTY")
            all_ok = False
            issues.append(f"{name} is empty")
        else:
            size = path.stat().st_size
            print(f"  {Fore.GREEN}[+]{Style.RESET_ALL} {name}: {size} bytes")
    
    if all_ok:
        return TestResult(
            "Required Files",
            True,
            "All required files exist and have content"
        )
    
    return TestResult(
        "Required Files",
        False,
        "; ".join(issues)
    )


def test_dependencies() -> TestResult:
    """TEST 3: Check required Python packages can be imported."""
    print_header("Dependencies")
    
    dependencies = {
        "watchdog": "File system monitoring",
        "colorama": "Colored terminal output",
        "openai": "OpenRouter/Qwen API client",
        "dotenv": "Environment variable loading (python-dotenv)",
    }
    
    missing = []
    installed = []
    
    for package, description in dependencies.items():
        try:
            if package == "dotenv":
                __import__("dotenv")
            else:
                __import__(package)
            installed.append(package)
            print(f"  {Fore.GREEN}[+]{Style.RESET_ALL} {package}: {description}")
        except ImportError:
            missing.append(package)
            print(f"  {Fore.RED}[-]{Style.RESET_ALL} {package}: NOT INSTALLED")
    
    if missing:
        install_cmd = "pip install " + " ".join(missing)
        return TestResult(
            "Dependencies",
            False,
            f"Missing: {', '.join(missing)}\n   Install with: {install_cmd}"
        )
    
    return TestResult(
        "Dependencies",
        True,
        f"All {len(installed)} dependencies installed"
    )


def test_qwen_api() -> TestResult:
    """TEST 4: Test Qwen/OpenRouter API connectivity."""
    print_header("Qwen API Connectivity")
    
    # Try QWEN_API_KEY first, then fall back to OPENROUTER_API_KEY
    api_key = os.getenv("QWEN_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
    api_source = "QWEN_API_KEY" if os.getenv("QWEN_API_KEY") else "OPENROUTER_API_KEY" if os.getenv("OPENROUTER_API_KEY") else None
    
    if not api_key:
        print(f"  {Fore.RED}[-]{Style.RESET_ALL} No API key found in .env")
        return TestResult(
            "Qwen API Connectivity",
            False,
            "Add QWEN_API_KEY=your_key or OPENROUTER_API_KEY=your_key to .env file"
        )
    
    print(f"  {Fore.GREEN}[+]{Style.RESET_ALL} {api_source} found in .env")
    
    try:
        import openai
        
        # Determine which API to use
        if os.getenv("QWEN_API_KEY"):
            # Use Qwen API
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            model = "qwen-plus"
        else:
            # Use OpenRouter API
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        
        print(f"  {Fore.GREEN}[+]{Style.RESET_ALL} OpenAI client initialized ({model})")
        print(f"  {Fore.CYAN}[>]{Style.RESET_ALL} Sending test message...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Reply with just the word: CONNECTED"},
                {"role": "user", "content": "Reply with just the word: CONNECTED"}
            ],
            max_tokens=10
        )
        
        reply = response.choices[0].message.content.strip()
        print(f"  {Fore.GREEN}[+]{Style.RESET_ALL} Response received: '{reply}'")
        
        if "CONNECTED" in reply.upper():
            return TestResult(
                "Qwen API Connectivity",
                True,
                "API responded successfully"
            )
        else:
            return TestResult(
                "Qwen API Connectivity",
                True,
                f"API responded (unexpected format): '{reply}'"
            )
            
    except ImportError as e:
        return TestResult(
            "Qwen API Connectivity",
            False,
            f"openai package not installed: {e}"
        )
    except Exception as e:
        return TestResult(
            "Qwen API Connectivity",
            False,
            f"API error: {e}"
        )


def test_end_to_end() -> TestResult:
    """TEST 5: End-to-end file drop test."""
    print_header("End-to-End File Drop Test")
    
    # Ensure file_watcher is running check
    print(f"  {Fore.YELLOW}[!]{Style.RESET_ALL} NOTE: file_watcher.py should be running for this test")
    print(f"  {Fore.CYAN}[>]{Style.RESET_ALL} Creating test file: {Config.TEST_FILE}")
    
    try:
        # Ensure Inbox exists
        Config.INBOX_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create test file
        test_content = f"Test file created at {datetime.now().isoformat()}"
        Config.TEST_FILE.write_text(test_content, encoding="utf-8")
        print(f"  {Fore.GREEN}[+]{Style.RESET_ALL} Test file created")
        
        # Wait for file_watcher to process
        print(f"  {Fore.CYAN}[>]{Style.RESET_ALL} Waiting 5 seconds for processing...")
        time.sleep(5)
        
        # Check if task file appeared in Needs_Action
        task_files = list(Config.NEEDS_ACTION_DIR.glob("*.md"))
        
        # Look for our test file (should have been converted to .md)
        test_processed = False
        matching_file = None
        
        for tf in task_files:
            content = tf.read_text(encoding="utf-8")
            if "test_drop.txt" in content or "test_drop" in tf.name.lower():
                test_processed = True
                matching_file = tf
                break
        
        # Clean up test file from Inbox (if still exists)
        if Config.TEST_FILE.exists():
            Config.TEST_FILE.unlink()
            print(f"  {Fore.CYAN}[>]{Style.RESET_ALL} Cleaned up test file from Inbox")
        
        if test_processed:
            print(f"  {Fore.GREEN}[+]{Style.RESET_ALL} Task file created: {matching_file.name}")
            return TestResult(
                "End-to-End File Drop Test",
                True,
                f"File processed successfully: {matching_file.name}"
            )
        else:
            print(f"  {Fore.RED}[-]{Style.RESET_ALL} No task file created in Needs_Action")
            print(f"  {Fore.YELLOW}[!]{Style.RESET_ALL} Make sure file_watcher.py is running:")
            print(f"     python file_watcher.py")
            return TestResult(
                "End-to-End File Drop Test",
                False,
                "file_watcher.py did not process the test file"
            )
            
    except Exception as e:
        # Clean up on error
        if Config.TEST_FILE.exists():
            Config.TEST_FILE.unlink()
        return TestResult(
            "End-to-End File Drop Test",
            False,
            f"Error during test: {e}"
        )


def run_all_tests():
    """Run all bronze tier tests and print summary."""
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}          BRONZE TIER TEST SUITE{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    results = []
    
    # Run all tests
    results.append(test_folder_structure())
    results.append(test_required_files())
    results.append(test_dependencies())
    results.append(test_qwen_api())
    results.append(test_end_to_end())
    
    # Print summary
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}TEST SUMMARY{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    
    for i, result in enumerate(results, 1):
        status = f"{Fore.GREEN}PASS{Style.RESET_ALL}" if result.passed else f"{Fore.RED}FAIL{Style.RESET_ALL}"
        print(f"  Test {i}: {result.name} - {status}")
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Bronze Tier: {passed_count}/{total_count} tests passed{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    if passed_count == total_count:
        print(f"\n{Fore.GREEN}[SUCCESS] Bronze Tier Complete - Ready for Submission!{Style.RESET_ALL}\n")
    else:
        print(f"\n{Fore.RED}[INCOMPLETE] Fix the following issues:{Style.RESET_ALL}\n")
        
        for result in results:
            if not result.passed:
                print(f"  * {result.name}: {result.message}")
        
        print(f"\n{Fore.YELLOW}Run tests again after fixing: python test_bronze.py{Style.RESET_ALL}\n")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
