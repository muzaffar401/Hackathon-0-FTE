#!/usr/bin/env python3
"""
LinkedIn Poster Service
Generates LinkedIn posts using AI and posts approved content automatically.
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
from typing import Optional, List, Dict, Any

import requests
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
    PENDING_APPROVAL_DIR = VAULT_DIR / "Pending_Approval"
    APPROVED_DIR = VAULT_DIR / "Approved"
    DONE_DIR = VAULT_DIR / "Done"
    LOGS_DIR = VAULT_DIR / "Logs"
    
    # LinkedIn API settings
    LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    LINKEDIN_AUTHOR_URN = os.getenv("LINKEDIN_AUTHOR_URN", "")
    LINKEDIN_API_URL = "https://api.linkedin.com/v2/ugcPosts"
    
    # Qwen/OpenRouter API settings
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Qwen API (alternative)
    QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
    QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL = "qwen-plus"
    
    # Scheduling
    POST_INTERVAL = 600  # 10 minutes in seconds
    
    # Dry run mode
    DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
    
    # System prompt for LinkedIn post generation
    LINKEDIN_SYSTEM_PROMPT = """You are a LinkedIn content expert. Write a professional LinkedIn post about the given topic.
Make it engaging, add 3-5 relevant hashtags, keep it under 300 words.
Format: Hook line → Main content → Call to action → Hashtags

Guidelines:
- Start with a strong hook that grabs attention
- Use short paragraphs for readability
- Include personal insights or actionable advice
- End with a call to action (question, comment invitation, etc.)
- Add 3-5 relevant hashtags at the end
- Keep tone professional but conversational
- Avoid overly promotional language
- Maximum 300 words"""


class LinkedInPoster:
    """LinkedIn posting service with AI content generation."""
    
    def __init__(self):
        self.api_client: Optional[requests.Session] = None
        self.ai_client: Optional[OpenAI] = None
        self._init_api_client()
        self._init_ai_client()
    
    def _init_api_client(self):
        """Initialize LinkedIn API client."""
        if Config.LINKEDIN_ACCESS_TOKEN:
            self.api_client = requests.Session()
            self.api_client.headers.update({
                "Authorization": f"Bearer {Config.LINKEDIN_ACCESS_TOKEN}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            })
            print(f"{Fore.GREEN}[API]{Style.RESET_ALL} LinkedIn API client initialized.")
        else:
            print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} LINKEDIN_ACCESS_TOKEN not set. Posting disabled.")
            self.api_client = None
    
    def _init_ai_client(self):
        """Initialize AI client for content generation."""
        api_key = Config.QWEN_API_KEY or Config.OPENROUTER_API_KEY
        base_url = Config.QWEN_BASE_URL if Config.QWEN_API_KEY else Config.OPENROUTER_BASE_URL
        model = Config.QWEN_MODEL if Config.QWEN_API_KEY else Config.OPENROUTER_MODEL
        
        if api_key:
            self.ai_client = OpenAI(api_key=api_key, base_url=base_url)
            print(f"{Fore.GREEN}[AI]{Style.RESET_ALL} AI client initialized ({model}).")
        else:
            print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} No AI API key set. Content generation disabled.")
            self.ai_client = None
    
    def generate_linkedin_post(self, topic: str) -> Optional[Path]:
        """
        FUNCTION 1: Generate LinkedIn post content using AI.
        
        Args:
            topic: The topic to generate content about
            
        Returns:
            Path to the generated post file, or None if failed
        """
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[GENERATE]{Style.RESET_ALL} Creating LinkedIn post about: {topic}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        if not self.ai_client:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} AI client not initialized.")
            print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Set QWEN_API_KEY or OPENROUTER_API_KEY in .env")
            return None
        
        try:
            # Call AI to generate content
            response = self.ai_client.chat.completions.create(
                model=Config.QWEN_MODEL if Config.QWEN_API_KEY else Config.OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": Config.LINKEDIN_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Generate a LinkedIn post about: {topic}"}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            generated_content = response.choices[0].message.content.strip()
            
            print(f"{Fore.GREEN}[GENERATED]{Style.RESET_ALL} Content created ({len(generated_content)} chars)")
            
            # Create pending approval file
            return self._save_pending_post(topic, generated_content)
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} AI generation failed: {e}")
            self._log_event("linkedin_generation_error", {"topic": topic, "error": str(e)})
            return None
    
    def _save_pending_post(self, topic: str, content: str) -> Optional[Path]:
        """Save generated post to Pending_Approval folder."""
        try:
            Config.PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_topic = re.sub(r'[^\w\-_]', '_', topic.lower())[:30]
            filename = f"LINKEDIN_{safe_topic}_{timestamp}.md"
            filepath = Config.PENDING_APPROVAL_DIR / filename
            
            # Create file content
            file_content = f"""---
type: linkedin_post
topic: {topic}
generated: {datetime.now().isoformat()}
status: pending_approval
---
## Post Content
{content}

## To Approve
Move this file to /Approved/ folder to schedule for posting.

## Notes
- Post will be published to LinkedIn automatically
- Check content for accuracy before approving
- File will move to /Done/ after successful posting
"""
            
            filepath.write_text(file_content, encoding="utf-8")
            
            print(f"{Fore.GREEN}[SAVED]{Style.RESET_ALL} Pending approval: {filename}")
            
            # Log the event
            self._log_event("linkedin_post_generated", {
                "topic": topic,
                "file": filename,
                "content_length": len(content)
            })
            
            return filepath
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to save post: {e}")
            return None
    
    def post_approved_content(self) -> int:
        """
        FUNCTION 2: Post approved LinkedIn content.
        
        Watches Approved/ folder for LINKEDIN_*.md files and posts them.
        
        Returns:
            Number of posts successfully published
        """
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[POSTER]{Style.RESET_ALL} Checking for approved LinkedIn posts...")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        if not self.api_client:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} LinkedIn API not configured.")
            return 0
        
        if not Config.APPROVED_DIR.exists():
            Config.APPROVED_DIR.mkdir(parents=True, exist_ok=True)
            return 0
        
        # Find approved LinkedIn post files
        approved_files = list(Config.APPROVED_DIR.glob("LINKEDIN_*.md"))
        
        if not approved_files:
            print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} No approved posts to publish.")
            return 0
        
        print(f"{Fore.GREEN}[FOUND]{Style.RESET_ALL} {len(approved_files)} approved post(s)")
        
        posted_count = 0
        
        for file_path in approved_files:
            try:
                # Read the file
                content = file_path.read_text(encoding="utf-8")
                
                # Parse frontmatter and extract post content
                post_data = self._parse_post_file(content)
                
                if not post_data:
                    print(f"{Fore.RED}[SKIP]{Style.RESET_ALL} Invalid file format: {file_path.name}")
                    continue
                
                # Extract post content (remove markdown headers)
                post_text = self._extract_post_text(post_data.get("content", ""))
                
                if not post_text:
                    print(f"{Fore.RED}[SKIP]{Style.RESET_ALL} No content found: {file_path.name}")
                    continue
                
                # Check dry run mode
                if Config.DRY_RUN:
                    print(f"{Fore.YELLOW}[DRY RUN]{Style.RESET_ALL} Would post: {file_path.name}")
                    print(f"  Topic: {post_data.get('topic', 'Unknown')}")
                    print(f"  Length: {len(post_text)} chars")
                    posted_count += 1
                    continue
                
                # Post to LinkedIn
                success = self._post_to_linkedin(post_text, post_data.get("topic", ""))
                
                if success:
                    # Move to Done folder
                    self._move_to_done(file_path)
                    posted_count += 1
                    print(f"{Fore.GREEN}[POSTED]{Style.RESET_ALL} Successfully published: {file_path.name}")
                else:
                    print(f"{Fore.RED}[FAILED]{Style.RESET_ALL} Could not post: {file_path.name}")
                    
            except Exception as e:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to process {file_path.name}: {e}")
                self._log_event("linkedin_post_error", {
                    "file": file_path.name,
                    "error": str(e)
                })
        
        if posted_count > 0:
            print(f"\n{Fore.GREEN}[SUMMARY]{Style.RESET_ALL} Posted {posted_count} content(s)")
        
        return posted_count
    
    def _parse_post_file(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse markdown file with frontmatter."""
        try:
            # Check for frontmatter
            if not content.startswith("---"):
                return None
            
            # Split frontmatter and content
            parts = content.split("---", 2)
            if len(parts) < 3:
                return None
            
            frontmatter = parts[1].strip()
            body = parts[2].strip()
            
            # Parse frontmatter
            data = {}
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    data[key.strip()] = value.strip()
            
            # Extract post content (after ## Post Content header)
            content_match = re.search(r'## Post Content\s*\n(.*?)(?=##|$)', body, re.DOTALL)
            post_content = content_match.group(1).strip() if content_match else body
            
            data["content"] = post_content
            
            return data
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Parse error: {e}")
            return None
    
    def _extract_post_text(self, content: str) -> str:
        """Extract clean post text from markdown content."""
        # Remove markdown formatting
        text = content
        
        # Remove code blocks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        
        # Remove inline code
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Remove bold/italic
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        
        # Remove extra whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text
    
    def _get_author_urn(self) -> str:
        """Resolve author URN: use config, or fetch current user from API."""
        urn = (Config.LINKEDIN_AUTHOR_URN or "").strip()
        # LinkedIn API accepts urn:li:member:ID or urn:li:company:ID for ugcPosts
        if urn and (urn.startswith("urn:li:member:") or urn.startswith("urn:li:person:") or urn.startswith("urn:li:organization:") or urn.startswith("urn:li:company:")):
            return urn
        if urn:
            return urn
        if not self.api_client:
            return ""
        try:
            # OpenID userinfo (works with profile scope)
            r = self.api_client.get("https://api.linkedin.com/v2/userinfo", timeout=10)
            if r.status_code != 200:
                r = self.api_client.get("https://api.linkedin.com/v2/me", timeout=10)
            if r.status_code == 200:
                data = r.json()
                pid = data.get("sub") or data.get("id")
                if pid:
                    return f"urn:li:person:{pid}"
        except Exception:
            pass
        return ""

    def _post_to_linkedin(self, text: str, topic: str) -> bool:
        """Post content to LinkedIn API. Author must be a person URN (urn:li:person:xxx)."""
        try:
            author = self._get_author_urn()
            if not author:
                print(f"{Fore.RED}[LINKEDIN]{Style.RESET_ALL} No author URN. Set LINKEDIN_AUTHOR_URN in .env or run --whoami")
                return False
            # LinkedIn UGC Posts API: author must be a person, not organization
            post_data = {
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Make the API request
            response = self.api_client.post(
                Config.LINKEDIN_API_URL,
                json=post_data,
                timeout=30
            )
            
            # Check response
            if response.status_code in [200, 201]:
                post_id = response.json().get("id", "unknown")
                print(f"{Fore.GREEN}[LINKEDIN]{Style.RESET_ALL} Post ID: {post_id}")
                
                # Log success
                self._log_event("linkedin_post_success", {
                    "topic": topic,
                    "post_id": post_id,
                    "length": len(text)
                })
                
                return True
            else:
                error_msg = response.text[:200] if response.text else "Unknown error"
                print(f"{Fore.RED}[LINKEDIN]{Style.RESET_ALL} API error ({response.status_code}): {error_msg}")
                if response.status_code == 403 and "/author" in error_msg:
                    print(f"{Fore.YELLOW}[FIX]{Style.RESET_ALL} Author URN must match the account that created the access token.")
                    print(f"{Fore.YELLOW}[FIX]{Style.RESET_ALL} Try: urn:li:person:YOUR_ID or urn:li:member:YOUR_ID (ID from the same OAuth flow as the token).")
                    print(f"{Fore.YELLOW}[FIX]{Style.RESET_ALL} Ensure the app has w_member_social and the token is for the account you want to post as.")
                
                self._log_event("linkedin_api_error", {
                    "topic": topic,
                    "status_code": response.status_code,
                    "error": error_msg
                })
                
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}[LINKEDIN]{Style.RESET_ALL} Request failed: {e}")
            self._log_event("linkedin_request_error", {
                "topic": topic,
                "error": str(e)
            })
            return False
        except Exception as e:
            print(f"{Fore.RED}[LINKEDIN]{Style.RESET_ALL} Unexpected error: {e}")
            return False
    
    def _move_to_done(self, file_path: Path):
        """Move posted file to Done folder."""
        try:
            Config.DONE_DIR.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"{timestamp}_POSTED_{file_path.name}"
            dest_path = Config.DONE_DIR / new_name
            
            shutil.move(str(file_path), str(dest_path))
            
            print(f"{Fore.GREEN}[MOVED]{Style.RESET_ALL} To Done: {new_name}")
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to move file: {e}")
    
    def _log_event(self, event_type: str, data: dict):
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
    
    def run_scheduler(self):
        """Run the posting scheduler (checks every 10 minutes)."""
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} LinkedIn Poster scheduler running.")
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} Checking for approved posts every {Config.POST_INTERVAL}s...")
        print(f"{Fore.GREEN}[START]{Style.RESET_ALL} Press Ctrl+C to stop.\n")
        
        try:
            while True:
                try:
                    # Check and post approved content
                    self.post_approved_content()
                    
                    # Wait for next interval
                    time.sleep(Config.POST_INTERVAL)
                    
                except Exception as e:
                    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Scheduler error: {e}")
                    self._log_event("linkedin_scheduler_error", {"error": str(e)})
                    time.sleep(Config.POST_INTERVAL)
                    
        except KeyboardInterrupt:
            raise
    
    def list_pending(self) -> List[Path]:
        """List all pending LinkedIn posts."""
        if not Config.PENDING_APPROVAL_DIR.exists():
            return []
        
        pending = list(Config.PENDING_APPROVAL_DIR.glob("LINKEDIN_*.md"))
        return sorted(pending, key=lambda x: x.stat().st_mtime)
    
    def list_approved(self) -> List[Path]:
        """List all approved LinkedIn posts waiting to be posted."""
        if not Config.APPROVED_DIR.exists():
            return []
        
        approved = list(Config.APPROVED_DIR.glob("LINKEDIN_*.md"))
        return sorted(approved, key=lambda x: x.stat().st_mtime)


def print_banner():
    """Print the startup banner."""
    dry_run_status = "YES (no actual posts)" if Config.DRY_RUN else "NO (will post)"
    
    banner = f"""
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.YELLOW}           LINKEDIN POSTER SERVICE{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.CYAN}Pending Dir:   {Fore.GREEN}{Config.PENDING_APPROVAL_DIR}{Style.RESET_ALL}
{Fore.CYAN}Approved Dir:  {Fore.GREEN}{Config.APPROVED_DIR}{Style.RESET_ALL}
{Fore.CYAN}Done Dir:      {Fore.GREEN}{Config.DONE_DIR}{Style.RESET_ALL}
{Fore.CYAN}Logs Dir:      {Fore.GREEN}{Config.LOGS_DIR}{Style.RESET_ALL}
{Fore.CYAN}Dry Run:       {Fore.YELLOW}{dry_run_status}{Style.RESET_ALL}
{Fore.CYAN}Post Interval: {Fore.GREEN}{Config.POST_INTERVAL}s{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
"""
    print(banner)


def ensure_directories():
    """Ensure all required directories exist."""
    try:
        Config.PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
        Config.APPROVED_DIR.mkdir(parents=True, exist_ok=True)
        Config.DONE_DIR.mkdir(parents=True, exist_ok=True)
        Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to create directories: {e}")
        raise


def signal_handler(signum, frame):
    """Handle Ctrl+C and other termination signals."""
    print(f"\n{Fore.YELLOW}[SHUTDOWN]{Style.RESET_ALL} Received termination signal...")
    print(f"{Fore.GREEN}[GOODBYE]{Style.RESET_ALL} LinkedIn Poster stopped gracefully.")
    sys.exit(0)


def main():
    """Main entry point for the LinkedIn poster service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LinkedIn Poster Service")
    parser.add_argument("--generate", "-g", type=str, help="Generate a LinkedIn post about a topic")
    parser.add_argument("--post", "-p", action="store_true", help="Post approved content now")
    parser.add_argument("--list", "-l", action="store_true", help="List pending/approved posts")
    parser.add_argument("--schedule", "-s", action="store_true", help="Run scheduler (default)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without posting")
    parser.add_argument("--whoami", action="store_true", help="Print your LinkedIn person URN for .env (required for posting)")
    parser.add_argument("--test-linkedin", action="store_true", help="Verify token and author URN (GET posts for author)")
    
    args = parser.parse_args()
    
    try:
        # Print startup banner
        print_banner()
        
        # Ensure directories exist
        print(f"{Fore.GREEN}[SETUP]{Style.RESET_ALL} Checking directories...")
        ensure_directories()
        print(f"{Fore.GREEN}[SETUP]{Style.RESET_ALL} Directories ready.")
        
        # Override dry run if specified
        if args.dry_run:
            Config.DRY_RUN = True
            print(f"{Fore.YELLOW}[DRY RUN]{Style.RESET_ALL} Mode enabled - no actual posts")
        
        # Create poster instance
        poster = LinkedInPoster()
        
        # Handle commands
        if args.generate:
            # Generate a new post
            poster.generate_linkedin_post(args.generate)
            
        elif args.post:
            # Post approved content immediately
            poster.post_approved_content()
            
        elif args.list:
            # List pending and approved posts
            pending = poster.list_pending()
            approved = poster.list_approved()
            
            print(f"\n{Fore.CYAN}Pending Approval ({len(pending)}):{Style.RESET_ALL}")
            for p in pending:
                print(f"  - {p.name}")
            
            print(f"\n{Fore.CYAN}Approved/Ready to Post ({len(approved)}):{Style.RESET_ALL}")
            for a in approved:
                print(f"  - {a.name}")

        elif args.whoami:
            # Print current user's URN for .env (try OpenID userinfo first, then /v2/me)
            if not poster.api_client:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} LINKEDIN_ACCESS_TOKEN not set in .env")
                sys.exit(1)
            try:
                # OpenID Connect userinfo (works with profile scope)
                r = poster.api_client.get("https://api.linkedin.com/v2/userinfo", timeout=10)
                if r.status_code != 200:
                    r = poster.api_client.get("https://api.linkedin.com/v2/me", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    pid = data.get("sub") or data.get("id")
                    if pid:
                        print(f"\n{Fore.GREEN}Your user ID (sub): {pid}{Style.RESET_ALL}")
                        print(f"{Fore.GREEN}Add to .env (try in this order if one fails):{Style.RESET_ALL}")
                        print(f"LINKEDIN_AUTHOR_URN=urn:li:person:{pid}")
                        print(f"  or  LINKEDIN_AUTHOR_URN=urn:li:member:{pid}\n")
                    else:
                        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No sub/id in response: {data}")
                else:
                    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} LinkedIn API ({r.status_code}): {r.text[:300]}")
                    if r.status_code == 403:
                        print(f"{Fore.YELLOW}[FIX]{Style.RESET_ALL} Request 'profile' and 'openid' scopes when generating the token.")
            except Exception as e:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {e}")
                sys.exit(1)

        elif args.test_linkedin:
            # Verify token + author: try to fetch posts for the configured author
            if not poster.api_client:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} LINKEDIN_ACCESS_TOKEN not set")
                sys.exit(1)
            author = poster._get_author_urn()
            if not author:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} LINKEDIN_AUTHOR_URN not set in .env")
                sys.exit(1)
            print(f"\n{Fore.CYAN}[TEST]{Style.RESET_ALL} Author: {author}")
            try:
                import urllib.parse
                encoded = urllib.parse.quote(author, safe="")
                url = f"https://api.linkedin.com/v2/ugcPosts?q=authors&authors=List({encoded})&count=1"
                r = poster.api_client.get(url, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    total = data.get("paging", {}).get("total", 0)
                    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Token has access to this author. Total posts: {total}")
                else:
                    print(f"{Fore.RED}[FAIL]{Style.RESET_ALL} ({r.status_code}) {r.text[:250]}")
                    if r.status_code == 403:
                        print(f"{Fore.YELLOW}[FIX]{Style.RESET_ALL} Token may not be for this author, or app needs r_member_social.")
            except Exception as e:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {e}")
                sys.exit(1)
                
        else:
            # Run scheduler (default)
            # Set up signal handlers
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Run scheduler
            poster.run_scheduler()
        
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# ============================================================================
# LINKEDIN POSTER SETUP INSTRUCTIONS
# ============================================================================
#
# 1. LinkedIn Developer Account:
#    - Go to https://www.linkedin.com/developers/
#    - Sign in and create a developer account
#
# 2. Create LinkedIn App:
#    - Go to https://www.linkedin.com/developers/apps
#    - Click "Create app"
#    - Fill in app details (name, logo, etc.)
#    - Link to a LinkedIn Company Page (required)
#
# 3. Request Permissions:
#    - r_liteprofile - Read basic profile
#    - w_member_social - Post on behalf of user
#    - Submit for approval (may take 1-2 business days)
#
# 4. Get Access Token:
#    - Use OAuth 2.0 authorization code flow
#    - Or generate a test token from app dashboard
#    - Token format: Bearer AQ... (long string)
#
# 5. Get Author URN:
#    - Your LinkedIn member URN format: urn:li:person:XXXXX
#    - Find it via API: GET https://api.linkedin.com/v2/me
#    - Or from app dashboard after authentication
#
# 6. Configure .env:
#    LINKEDIN_ACCESS_TOKEN=your_access_token_here
#    LINKEDIN_AUTHOR_URN=urn:li:person:your_id_here
#
# 7. Optional - AI Configuration:
#    OPENROUTER_API_KEY=sk-or-v1-xxxxx (for post generation)
#    QWEN_API_KEY=your_qwen_key (alternative AI)
#
# 8. Dry Run Mode (test without posting):
#    DRY_RUN=true
#
# USAGE:
#
# Generate a post:
#   python linkedin_poster.py --generate "AI in healthcare"
#
# Post approved content:
#   python linkedin_poster.py --post
#
# List pending/approved:
#   python linkedin_poster.py --list
#
# Run scheduler (default):
#   python linkedin_poster.py --schedule
#
# Dry run (test mode):
#   python linkedin_poster.py --post --dry-run
#
# APPROVAL WORKFLOW:
# 1. Generate post → saves to Pending_Approval/
# 2. Review content in Pending_Approval/
# 3. Move file to Approved/ when ready
# 4. Scheduler auto-posts from Approved/ every 10 minutes
# 5. Posted files move to Done/
#
# pip install requests schedule colorama python-dotenv openai
