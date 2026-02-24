"""
Gold Tier Test Suite

Runs 7 comprehensive tests to verify all AI Employee Gold Tier integrations.

Usage:
    python test_gold.py
"""

import os
import sys
import time
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
BRIEFINGS_DIR = BASE_DIR / "Briefings"
LOGS_DIR = BASE_DIR / "Logs"

# Ensure directories exist
for directory in [BRIEFINGS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Test results
TEST_RESULTS = []


def log_test(test_num: int, name: str, passed: bool, message: str = ""):
    """Log test result."""
    result = {
        "test_num": test_num,
        "name": name,
        "passed": passed,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    TEST_RESULTS.append(result)
    
    status = f"{Fore.GREEN}✅ PASS" if passed else f"{Fore.RED}❌ FAIL"
    print(f"\n{status} | Test {test_num}: {name}")
    if message:
        print(f"   {message}")


# ============================================================================
# TEST 1: Odoo Connection
# ============================================================================

def test_odoo_connection():
    """Test Odoo authentication."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"TEST 1: Odoo Connection")
    print(f"{'='*60}{Fore.RESET}")
    
    try:
        # Load credentials
        odoo_url = os.getenv("ODOO_URL", "")
        odoo_db = os.getenv("ODOO_DB", "")
        odoo_user = os.getenv("ODOO_USER", "")
        odoo_password = os.getenv("ODOO_PASSWORD", "")
        
        if not all([odoo_url, odoo_db, odoo_user, odoo_password]):
            log_test(1, "Odoo Connection", False, 
                    "Missing credentials in .env (ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)")
            return
        
        # Import odoo_mcp
        try:
            from odoo_mcp import authenticate
        except ImportError as e:
            log_test(1, "Odoo Connection", False, 
                    f"Cannot import odoo_mcp: {str(e)}")
            return
        
        # Try to authenticate
        uid = authenticate()
        
        if uid:
            log_test(1, "Odoo Connection", True, 
                    f"Connected successfully. UID: {uid}")
        else:
            log_test(1, "Odoo Connection", False, 
                    "Authentication failed - check credentials or Odoo server status")
    
    except Exception as e:
        log_test(1, "Odoo Connection", False, 
                f"Error: {str(e)}")


# ============================================================================
# TEST 2: Odoo Data Fetch
# ============================================================================

def test_odoo_data_fetch():
    """Test Odoo revenue data fetch."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"TEST 2: Odoo Data Fetch")
    print(f"{'='*60}{Fore.RESET}")
    
    try:
        # Import odoo_mcp
        try:
            from odoo_mcp import get_monthly_revenue
        except ImportError as e:
            log_test(2, "Odoo Data Fetch", False, 
                    f"Cannot import odoo_mcp: {str(e)}")
            return
        
        # Get current month/year
        current = datetime.now()
        year = current.year
        month = current.month
        
        # Fetch revenue
        revenue_data = get_monthly_revenue(year, month)
        
        if revenue_data and isinstance(revenue_data, dict) and "total_revenue" in revenue_data:
            log_test(2, "Odoo Data Fetch", True, 
                    f"Revenue data fetched: ${revenue_data.get('total_revenue', 0):,.2f}")
        else:
            log_test(2, "Odoo Data Fetch", False, 
                    f"Invalid response format: {revenue_data}")
    
    except Exception as e:
        log_test(2, "Odoo Data Fetch", False, 
                f"Error: {str(e)}")


# ============================================================================
# TEST 3: Facebook API
# ============================================================================

def test_facebook_api():
    """Test Facebook Page API connection."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"TEST 3: Facebook API")
    print(f"{'='*60}{Fore.RESET}")
    
    try:
        # Load credentials
        fb_page_id = os.getenv("FB_PAGE_ID", "")
        fb_token = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
        
        if not all([fb_page_id, fb_token]):
            log_test(3, "Facebook API", False, 
                    "Missing credentials in .env (FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN)")
            return
        
        # Make API request
        url = f"https://graph.facebook.com/v18.0/{fb_page_id}"
        params = {"access_token": fb_token}
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            page_name = data.get("name", "Unknown")
            log_test(3, "Facebook API", True, 
                    f"Connected to page: {page_name}")
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("error", {}).get("message", response.reason)
            log_test(3, "Facebook API", False, 
                    f"API Error ({response.status_code}): {error_msg}")
    
    except requests.exceptions.Timeout:
        log_test(3, "Facebook API", False, "Request timed out")
    except Exception as e:
        log_test(3, "Facebook API", False, f"Error: {str(e)}")


# ============================================================================
# TEST 4: Instagram API
# ============================================================================

def test_instagram_api():
    """Test Instagram Business API connection."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"TEST 4: Instagram API")
    print(f"{'='*60}{Fore.RESET}")
    
    try:
        # Load credentials
        ig_user_id = os.getenv("IG_USER_ID", "")
        ig_token = os.getenv("IG_ACCESS_TOKEN", "")
        
        if not all([ig_user_id, ig_token]):
            log_test(4, "Instagram API", False, 
                    "Missing credentials in .env (IG_USER_ID, IG_ACCESS_TOKEN)")
            return
        
        # Make API request
        url = f"https://graph.facebook.com/v18.0/{ig_user_id}"
        params = {"access_token": ig_token}
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            ig_name = data.get("name", data.get("username", "Unknown"))
            log_test(4, "Instagram API", True, 
                    f"Connected to account: {ig_name}")
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("error", {}).get("message", response.reason)
            log_test(4, "Instagram API", False, 
                    f"API Error ({response.status_code}): {error_msg}")
    
    except requests.exceptions.Timeout:
        log_test(4, "Instagram API", False, "Request timed out")
    except Exception as e:
        log_test(4, "Instagram API", False, f"Error: {str(e)}")


# ============================================================================
# TEST 5: Twitter API
# ============================================================================

def test_twitter_api():
    """Test Twitter API v2 connection using tweepy."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"TEST 5: Twitter API")
    print(f"{'='*60}{Fore.RESET}")
    
    try:
        # Load credentials
        api_key = os.getenv("TWITTER_API_KEY", "")
        api_secret = os.getenv("TWITTER_API_SECRET", "")
        access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
        access_secret = os.getenv("TWITTER_ACCESS_SECRET", "")
        
        if not all([api_key, api_secret, access_token, access_secret]):
            log_test(5, "Twitter API", False, 
                    "Missing credentials in .env (TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)")
            return
        
        # Try to import tweepy
        try:
            import tweepy
        except ImportError:
            log_test(5, "Twitter API", False, 
                    "tweepy not installed. Run: pip install tweepy")
            return
        
        # Authenticate with OAuth 1.0a
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        api = tweepy.API(auth)
        
        # Verify credentials
        try:
            user = api.verify_credentials()
            if user:
                log_test(5, "Twitter API", True, 
                        f"Connected as: @{user.screen_name} ({user.name})")
            else:
                log_test(5, "Twitter API", False, "Could not verify credentials")
        except tweepy.TweepError as e:
            log_test(5, "Twitter API", False, 
                    f"Authentication failed: {str(e)}")
    
    except Exception as e:
        log_test(5, "Twitter API", False, f"Error: {str(e)}")


# ============================================================================
# TEST 6: Ralph Loop (Dry Run)
# ============================================================================

def test_ralph_loop():
    """Test Ralph Loop with simple counting task."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"TEST 6: Ralph Loop (Dry Run)")
    print(f"{'='*60}{Fore.RESET}")
    
    try:
        # Import Ralph Loop
        try:
            from ralph_loop import RalphLoop, contains_phrase
        except ImportError as e:
            log_test(6, "Ralph Loop", False, 
                    f"Cannot import ralph_loop: {str(e)}")
            return
        
        # Check if API key is available
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            log_test(6, "Ralph Loop", False, 
                    "OPENROUTER_API_KEY not set in .env")
            return
        
        # Create simple task
        task = "Count from 1 to 3, then say <TASK_COMPLETE>"
        completion_check = lambda r: "<TASK_COMPLETE>" in r
        
        # Create and run Ralph Loop
        ralph = RalphLoop(
            task_description=task,
            completion_check_fn=completion_check,
            max_iterations=3,
            delay_between_iterations=0.5
        )
        
        result = ralph.run()
        
        if result and result.get("success"):
            iterations = result.get("iterations_used", 0)
            log_test(6, "Ralph Loop", True, 
                    f"Completed in {iterations} iteration(s)")
        else:
            failure_reason = result.get("failure_reason", "Unknown") if result else "No result"
            log_test(6, "Ralph Loop", False, 
                    f"Failed: {failure_reason}")
    
    except Exception as e:
        log_test(6, "Ralph Loop", False, f"Error: {str(e)}")


# ============================================================================
# TEST 7: Full Audit Dry Run
# ============================================================================

def test_full_audit():
    """Test full weekly audit in dry run mode."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"TEST 7: Full Audit (Dry Run)")
    print(f"{'='*60}{Fore.RESET}")
    
    try:
        # Set dry run mode
        os.environ["DRY_RUN"] = "true"
        
        # Import weekly_audit
        try:
            import weekly_audit
        except ImportError as e:
            log_test(7, "Full Audit", False, 
                    f"Cannot import weekly_audit: {str(e)}")
            return
        
        # Run audit
        result = weekly_audit.run_audit()
        
        # Check if briefing was created
        briefing_path = result.get("briefing_path")
        
        if briefing_path:
            briefing_file = Path(briefing_path)
            if briefing_file.exists():
                # Check content
                with open(briefing_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if len(content) > 100:  # At least some content
                    log_test(7, "Full Audit", True, 
                            f"Briefing created: {briefing_file.name} ({len(content)} chars)")
                else:
                    log_test(7, "Full Audit", False, 
                            "Briefing file is empty or too short")
            else:
                log_test(7, "Full Audit", False, 
                        f"Briefing file not found: {briefing_path}")
        else:
            error_msg = result.get("error", "Unknown error")
            log_test(7, "Full Audit", False, 
                    f"Audit failed: {error_msg}")
        
        # Reset dry run mode
        os.environ["DRY_RUN"] = "false"
    
    except Exception as e:
        os.environ["DRY_RUN"] = "false"
        log_test(7, "Full Audit", False, f"Error: {str(e)}")


# ============================================================================
# MAIN
# ============================================================================

def run_all_tests():
    """Run all 7 tests."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"   AI EMPLOYEE GOLD TIER - TEST SUITE")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{Fore.RESET}")
    
    # Run all tests
    test_odoo_connection()
    test_odoo_data_fetch()
    test_facebook_api()
    test_instagram_api()
    test_twitter_api()
    test_ralph_loop()
    test_full_audit()
    
    # Summary
    passed = sum(1 for r in TEST_RESULTS if r["passed"])
    total = len(TEST_RESULTS)
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"   TEST SUMMARY")
    print(f"{'='*60}{Fore.RESET}")
    
    for result in TEST_RESULTS:
        status = f"{Fore.GREEN}✅" if result["passed"] else f"{Fore.RED}❌"
        print(f"{status} Test {result['test_num']}: {result['name']}")
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"   Gold Tier: {passed}/{total} tests passed")
    print(f"{'='*60}{Fore.RESET}")
    
    if passed == total:
        print(f"\n{Fore.GREEN}{'🎉'*10}")
        print(f"✅ Gold Tier Complete — Ready for Submission!")
        print(f"{'🎉'*10}{Fore.RESET}")
    else:
        print(f"\n{Fore.YELLOW}{'⚠️ '*5}")
        print(f"Fix the following issues:{Fore.RESET}\n")
        
        for result in TEST_RESULTS:
            if not result["passed"]:
                print(f"{Fore.RED}  Test {result['test_num']} ({result['name']}):")
                print(f"    {result['message']}{Fore.RESET}\n")
        
        print(f"{Fore.YELLOW}After fixing, run: python test_gold.py{Fore.RESET}")
    
    # Save results to log
    log_file = LOGS_DIR / "test_results.md"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"# Gold Tier Test Results\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Score:** {passed}/{total}\n\n")
        
        for result in TEST_RESULTS:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            f.write(f"## Test {result['test_num']}: {result['name']}\n")
            f.write(f"**Status:** {status}\n")
            f.write(f"**Message:** {result['message']}\n\n")
    
    print(f"\n{Fore.CYAN}Results saved to: {log_file}{Fore.RESET}\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
