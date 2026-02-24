# 1. Go to developer.twitter.com
# 2. Create Project + App
# 3. Apply for Elevated access (free, needed for posting)
# 4. Generate all 4 keys from App Settings → Keys and Tokens

import os
import json
import requests
import schedule
import time
import shutil
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from colorama import Fore, Style, init
from typing import List, Optional, Dict, Any

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
APPROVED_DIR = BASE_DIR / "Approved"
PENDING_DIR = BASE_DIR / "Pending_Approval"
DONE_DIR = BASE_DIR / "Done"
THREADS_DIR = DONE_DIR / "Threads"
LOGS_DIR = BASE_DIR / "Logs"
BRIEFINGS_DIR = BASE_DIR / "Briefings"

# Ensure directories exist
for directory in [APPROVED_DIR, PENDING_DIR, DONE_DIR, THREADS_DIR, LOGS_DIR, BRIEFINGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Twitter API v2 Configuration
TWITTER_API_URL = "https://api.twitter.com/2"
TWITTER_UPLOAD_URL = "https://upload.twitter.com/1.1"

# Environment variables
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Qwen/OpenAI client configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")


def _log_to_file(filename, message, level="INFO"):
    """Log message to a file in the Logs directory."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    log_file = LOGS_DIR / filename
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    # Also print to console
    if level == "ERROR":
        print(f"{Fore.RED}[{level}] {message}")
    elif level == "SUCCESS":
        print(f"{Fore.GREEN}[{level}] {message}")
    elif level == "WARNING":
        print(f"{Fore.YELLOW}[{level}] {message}")
    else:
        print(f"{Fore.CYAN}[{level}] {message}")


def _generate_content_hash(content):
    """Generate a unique hash for content to create unique filenames."""
    return hashlib.md5(content.encode()).hexdigest()[:8]


def _get_oauth1_headers(method, url, params=None, body=None):
    """
    Generate OAuth 1.0a headers for Twitter API requests.
    """
    import base64
    import hmac
    import hashlib
    import urllib.parse
    import time
    import random
    
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        _log_to_file("twitter_poster.log", "Twitter OAuth credentials not configured", "ERROR")
        return {}
    
    # OAuth parameters
    oauth_params = {
        "oauth_consumer_key": TWITTER_API_KEY,
        "oauth_token": TWITTER_ACCESS_TOKEN,
        "oauth_nonce": ''.join([str(random.randint(0, 9)) for _ in range(32)]),
        "oauth_timestamp": str(int(time.time())),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_version": "1.0"
    }
    
    # Combine all parameters for signature base
    all_params = {**oauth_params}
    if params:
        all_params.update(params)
    
    # Sort and encode parameters
    encoded_params = "&".join(
        f"{urllib.parse.quote(str(k), '')}={urllib.parse.quote(str(v), '')}"
        for k, v in sorted(all_params.items())
    )
    
    # Create signature base string
    base_url = url.split("?")[0]
    signature_base = (
        f"{method.upper()}&"
        f"{urllib.parse.quote(base_url, '')}&"
        f"{urllib.parse.quote(encoded_params, '')}"
    )
    
    # Create signing key
    signing_key = (
        f"{urllib.parse.quote(TWITTER_API_SECRET, '')}&"
        f"{urllib.parse.quote(TWITTER_ACCESS_SECRET, '')}"
    )
    
    # Generate signature
    signature = hmac.new(
        signing_key.encode("utf-8"),
        signature_base.encode("utf-8"),
        hashlib.sha1
    ).digest()
    
    oauth_params["oauth_signature"] = base64.b64encode(signature).decode("utf-8")
    
    # Build Authorization header
    auth_header = "OAuth " + ", ".join(
        f'{k}="{urllib.parse.quote(str(v), "")}"'
        for k, v in sorted(oauth_params.items())
    )
    
    return {"Authorization": auth_header}


def generate_tweet(topic):
    """
    Generate a tweet using Qwen AI.
    
    Args:
        topic: The topic/theme for the tweet
    
    Returns:
        Path to generated file, or None if failed
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        system_prompt = f"""Write a professional tweet about {topic}.
Requirements:
- Maximum 280 characters (including hashtags)
- Include exactly 2 relevant hashtags
- Make it engaging and shareable
- No filler words or generic phrases
- Professional but conversational tone
- Start with a hook, end with value"""
        
        user_prompt = f"Write a tweet about: {topic}"
        
        # Generate content using Qwen/OpenRouter API
        content = _call_qwen_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=100
        )
        
        if not content:
            _log_to_file("twitter_poster.log", "Failed to generate tweet content", "ERROR")
            return None
        
        # Clean up content - remove quotes if present
        content = content.strip().strip('"').strip("'")
        
        # Ensure it fits Twitter limits
        if len(content) > 280:
            content = content[:277] + "..."
        
        # Count characters
        char_count = len(content)
        
        # Create markdown file
        filename = f"TWITTER_{timestamp}.md"
        filepath = PENDING_DIR / filename
        
        md_content = f"""---
type: twitter_post
topic: {topic}
char_count: {char_count}
generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
status: pending_approval
---
## Tweet Content

{content}

## To Approve

Move this file to /Approved/ to publish this tweet.
"""
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        _log_to_file("twitter_poster.log", f"Generated tweet: {filename} ({char_count} chars)", "SUCCESS")
        return filepath
        
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error generating tweet: {str(e)}", "ERROR")
        return None


def _call_qwen_api(system_prompt, user_prompt, max_tokens=500):
    """Call Qwen/OpenRouter API to generate content."""
    try:
        if not OPENROUTER_API_KEY:
            _log_to_file("twitter_poster.log", "OPENROUTER_API_KEY not set. Cannot generate content.", "ERROR")
            return None
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        return content.strip()
        
    except requests.exceptions.RequestException as e:
        _log_to_file("twitter_poster.log", f"API request failed: {str(e)}", "ERROR")
        return None
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error calling Qwen API: {str(e)}", "ERROR")
        return None


def post_tweet(content):
    """
    Post a tweet using Twitter API v2.
    
    Args:
        content: The tweet content (max 280 characters)
    
    Returns:
        Tweet ID if successful, None otherwise
    """
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        _log_to_file("twitter_poster.log", "Twitter credentials not configured", "ERROR")
        return None
    
    if DRY_RUN:
        _log_to_file("twitter_poster.log", f"[DRY RUN] Would post tweet: {content[:50]}...", "INFO")
        return "dry_run_" + _generate_content_hash(content)
    
    try:
        url = f"{TWITTER_API_URL}/tweets"
        
        # Get OAuth headers
        headers = _get_oauth1_headers("POST", url)
        headers["Content-Type"] = "application/json"
        
        payload = {
            "text": content
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 201:
            result = response.json()
            tweet_id = result.get("data", {}).get("id")
            _log_to_file("twitter_poster.log", f"Tweet posted successfully. ID: {tweet_id}", "SUCCESS")
            return tweet_id
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("errors", [{}])[0].get("message", response.reason)
            _log_to_file("twitter_poster.log", f"Tweet failed: {error_msg} (Status: {response.status_code})", "ERROR")
            return None
            
    except requests.exceptions.RequestException as e:
        _log_to_file("twitter_poster.log", f"Twitter API request failed: {str(e)}", "ERROR")
        return None
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error posting tweet: {str(e)}", "ERROR")
        return None


def post_reply(content, reply_to_tweet_id):
    """
    Post a reply tweet to an existing tweet.
    
    Args:
        content: The reply content
        reply_to_tweet_id: The ID of the tweet to reply to
    
    Returns:
        Tweet ID if successful, None otherwise
    """
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        _log_to_file("twitter_poster.log", "Twitter credentials not configured", "ERROR")
        return None
    
    if DRY_RUN:
        _log_to_file("twitter_poster.log", f"[DRY RUN] Would post reply: {content[:50]}...", "INFO")
        return "dry_run_" + _generate_content_hash(content)
    
    try:
        url = f"{TWITTER_API_URL}/tweets"
        
        headers = _get_oauth1_headers("POST", url)
        headers["Content-Type"] = "application/json"
        
        payload = {
            "text": content,
            "reply": {
                "in_reply_to_tweet_id": reply_to_tweet_id
            }
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 201:
            result = response.json()
            tweet_id = result.get("data", {}).get("id")
            _log_to_file("twitter_poster.log", f"Reply posted successfully. ID: {tweet_id}", "SUCCESS")
            return tweet_id
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("errors", [{}])[0].get("message", response.reason)
            _log_to_file("twitter_poster.log", f"Reply failed: {error_msg}", "ERROR")
            return None
            
    except requests.exceptions.RequestException as e:
        _log_to_file("twitter_poster.log", f"Twitter API request failed: {str(e)}", "ERROR")
        return None
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error posting reply: {str(e)}", "ERROR")
        return None


def post_approved_tweet():
    """
    Watch /Approved/ for TWITTER_*.md files and post them.
    
    Returns:
        List of posted tweet info dicts
    """
    posted_tweets = []
    
    try:
        # Find all TWITTER_*.md files in Approved directory
        approved_files = list(APPROVED_DIR.glob("TWITTER_*.md"))
        
        if not approved_files:
            _log_to_file("twitter_poster.log", "No approved TWITTER files to process", "INFO")
            return posted_tweets
        
        for filepath in approved_files:
            try:
                # Read the file
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Parse frontmatter
                frontmatter, body = _parse_frontmatter(content)
                
                # Check if already processed
                if frontmatter.get("status") == "posted":
                    _log_to_file("twitter_poster.log", f"Skipping already posted file: {filepath.name}", "INFO")
                    continue
                
                topic = frontmatter.get("topic", "untitled")
                
                # Extract tweet content
                tweet_content = _extract_section(body, "Tweet Content")
                
                if not tweet_content:
                    _log_to_file("twitter_poster.log", f"No tweet content found in {filepath.name}", "ERROR")
                    continue
                
                # Post the tweet
                tweet_id = post_tweet(tweet_content)
                
                post_result = {
                    "file": filepath.name,
                    "topic": topic,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "success" if tweet_id else "failed",
                    "tweet_id": tweet_id,
                    "content": tweet_content
                }
                
                if tweet_id:
                    # Log the post
                    _log_post_result(post_result)
                    
                    # Move file to Done directory
                    done_path = DONE_DIR / filepath.name
                    shutil.move(str(filepath), str(done_path))
                    
                    # Update the file with posted status
                    _update_file_status(done_path, post_result)
                    
                    # Update Dashboard
                    _update_dashboard(post_result)
                    
                    posted_tweets.append(post_result)
                    _log_to_file("twitter_poster.log", f"Processed and moved: {filepath.name}", "SUCCESS")
                else:
                    _log_to_file("twitter_poster.log", f"Failed to post: {filepath.name}", "ERROR")
                    post_result["status"] = "failed"
                    posted_tweets.append(post_result)
                
            except Exception as e:
                _log_to_file("twitter_poster.log", f"Error processing {filepath.name}: {str(e)}", "ERROR")
        
        return posted_tweets
        
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error in post_approved_tweet: {str(e)}", "ERROR")
        return posted_tweets


def post_thread(topics_list):
    """
    Post multiple connected tweets as a thread.
    
    Args:
        topics_list: List of topics/tweets for the thread
    
    Returns:
        Dict with thread info and tweet IDs, or None if failed
    """
    if not topics_list or len(topics_list) == 0:
        _log_to_file("twitter_poster.log", "No topics provided for thread", "ERROR")
        return None
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        thread_tweets = []
        previous_tweet_id = None
        
        _log_to_file("twitter_poster.log", f"Starting thread with {len(topics_list)} tweets", "INFO")
        
        for i, topic in enumerate(topics_list):
            # Generate tweet content for this part of the thread
            if i == 0:
                # First tweet - normal post
                system_prompt = f"""Write the FIRST tweet in a thread about {topic}.
Requirements:
- Maximum 280 characters
- Include a hook to encourage reading more
- End with (1/{len(topics_list)}) to indicate thread position
- Professional but engaging tone"""
                
                tweet_content = _call_qwen_api(
                    system_prompt=system_prompt,
                    user_prompt=f"Write the first tweet in a thread about: {topic}",
                    max_tokens=100
                )
                
                if tweet_content:
                    tweet_id = post_tweet(tweet_content)
                    if tweet_id:
                        previous_tweet_id = tweet_id
                        thread_tweets.append({
                            "position": 1,
                            "content": tweet_content,
                            "tweet_id": tweet_id
                        })
                        _log_to_file("twitter_poster.log", f"Thread tweet 1/{len(topics_list)} posted: {tweet_id}", "SUCCESS")
            else:
                # Subsequent tweets - replies
                system_prompt = f"""Write tweet {i+1} of a thread about {topic}.
Requirements:
- Maximum 280 characters
- Continue the narrative from previous tweets
- End with ({i+1}/{len(topics_list)}) to indicate thread position
- Add value and keep readers engaged"""
                
                tweet_content = _call_qwen_api(
                    system_prompt=system_prompt,
                    user_prompt=f"Write tweet {i+1} of a thread about: {topic}",
                    max_tokens=100
                )
                
                if tweet_content and previous_tweet_id:
                    tweet_id = post_reply(tweet_content, previous_tweet_id)
                    if tweet_id:
                        previous_tweet_id = tweet_id
                        thread_tweets.append({
                            "position": i + 1,
                            "content": tweet_content,
                            "tweet_id": tweet_id,
                            "reply_to": previous_tweet_id
                        })
                        _log_to_file("twitter_poster.log", f"Thread tweet {i+1}/{len(topics_list)} posted: {tweet_id}", "SUCCESS")
        
        if not thread_tweets:
            _log_to_file("twitter_poster.log", "Thread posting failed - no tweets posted", "ERROR")
            return None
        
        # Save thread info to file
        thread_info = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "topics": topics_list,
            "tweet_count": len(thread_tweets),
            "tweets": thread_tweets,
            "first_tweet_id": thread_tweets[0].get("tweet_id") if thread_tweets else None
        }
        
        # Save thread file
        thread_filename = f"thread_{timestamp}.md"
        thread_filepath = THREADS_DIR / thread_filename
        
        thread_content = f"""---
type: twitter_thread
created: {thread_info['timestamp']}
tweet_count: {thread_info['tweet_count']}
first_tweet_id: {thread_info['first_tweet_id']}
---
# Twitter Thread

## Topics
{chr(10).join(f'- {t}' for t in topics_list)}

## Tweets
"""
        
        for tweet in thread_tweets:
            thread_content += f"""
### Tweet {tweet['position']}
**ID:** {tweet['tweet_id']}
**Content:** {tweet['content']}
"""
            if 'reply_to' in tweet:
                thread_content += f"**Reply to:** {tweet['reply_to']}\n"
        
        thread_content += "\n---\n*Thread posted by twitter_poster.py*\n"
        
        with open(thread_filepath, "w", encoding="utf-8") as f:
            f.write(thread_content)
        
        _log_to_file("twitter_poster.log", f"Thread saved to {thread_filepath}", "SUCCESS")
        
        return thread_info
        
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error posting thread: {str(e)}", "ERROR")
        return None


def _parse_frontmatter(content):
    """Parse YAML frontmatter from markdown content."""
    lines = content.strip().split("\n")
    
    if not lines[0].strip() == "---":
        return {}, content
    
    frontmatter = {}
    body_start = 0
    
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            body_start = i + 1
            break
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()
    
    body = "\n".join(lines[body_start:]).strip()
    return frontmatter, body


def _extract_section(content, section_name):
    """Extract content under a specific section header."""
    lines = content.split("\n")
    in_section = False
    section_content = []
    
    for line in lines:
        if line.strip().startswith(f"## {section_name}"):
            in_section = True
            continue
        elif line.strip().startswith("## "):
            if in_section:
                break
        elif in_section:
            section_content.append(line)
    
    return "\n".join(section_content).strip()


def _log_post_result(result):
    """Log post result to the logs file."""
    log_message = f"Tweet ID: {result.get('tweet_id', 'N/A')} | Topic: {result.get('topic', 'N/A')} | Status: {result.get('status', 'unknown')}"
    _log_to_file("twitter_posts.log", log_message, "SUCCESS")


def _update_file_status(filepath, post_result):
    """Update the markdown file with posted status."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Update frontmatter status
        content = content.replace("status: pending_approval", "status: posted")
        content = content.replace("status: posted", f"status: posted\nposted_at: {post_result['timestamp']}")
        
        # Add tweet ID
        if post_result.get("tweet_id"):
            content += f"\n\n## Posted\n- Tweet ID: {post_result['tweet_id']}\n- URL: https://twitter.com/i/web/status/{post_result['tweet_id']}"
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error updating file status: {str(e)}", "ERROR")


def _update_dashboard(post_result):
    """Update Dashboard.md with recent activity."""
    try:
        dashboard_path = BASE_DIR / "Dashboard.md"
        
        # Create dashboard if it doesn't exist
        if not dashboard_path.exists():
            dashboard_content = "# Dashboard\n\n## Recent Activity\n\n"
        else:
            with open(dashboard_path, "r", encoding="utf-8") as f:
                dashboard_content = f.read()
        
        # Create activity entry
        topic = post_result.get("topic", "unknown")
        status = post_result.get("status", "unknown")
        timestamp = post_result.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        tweet_id = post_result.get("tweet_id", "N/A")
        
        activity_entry = f"- [{timestamp}] Tweet posted: {topic} | ID: {tweet_id} | Status: {status}\n"
        
        # Insert after "## Recent Activity" header
        if "## Recent Activity" in dashboard_content:
            lines = dashboard_content.split("\n")
            new_lines = []
            inserted = False
            
            for line in lines:
                new_lines.append(line)
                if line.strip() == "## Recent Activity" and not inserted:
                    new_lines.append(activity_entry)
                    inserted = True
            
            dashboard_content = "\n".join(new_lines)
        else:
            dashboard_content += f"\n## Recent Activity\n{activity_entry}"
        
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(dashboard_content)
            
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error updating dashboard: {str(e)}", "ERROR")


def get_twitter_summary():
    """
    Fetch last 7 days of tweet metrics and generate summary.
    
    Returns:
        Path to summary file, or None if failed
    """
    try:
        today = datetime.now()
        seven_days_ago = today - timedelta(days=7)
        
        summary_data = {
            "tweets": [],
            "total_impressions": 0,
            "total_likes": 0,
            "total_retweets": 0,
            "total_replies": 0,
            "engagement_rate": 0.0,
            "best_performing": None,
            "generated_at": today.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Fetch tweets with metrics
        tweets = _fetch_tweets_with_metrics(seven_days_ago)
        
        if tweets:
            summary_data["tweets"] = tweets
            
            for tweet in tweets:
                impressions = tweet.get("impressions", 0)
                likes = tweet.get("likes", 0)
                retweets = tweet.get("retweets", 0)
                replies = tweet.get("replies", 0)
                
                summary_data["total_impressions"] += impressions
                summary_data["total_likes"] += likes
                summary_data["total_retweets"] += retweets
                summary_data["total_replies"] += replies
                
                # Track best performing tweet
                if summary_data["best_performing"] is None:
                    summary_data["best_performing"] = tweet
                elif likes + retweets + replies > summary_data["best_performing"].get("total_engagement", 0):
                    summary_data["best_performing"] = tweet
            
            # Calculate engagement rate
            total_engagement = summary_data["total_likes"] + summary_data["total_retweets"] + summary_data["total_replies"]
            if summary_data["total_impressions"] > 0:
                summary_data["engagement_rate"] = round(
                    (total_engagement / summary_data["total_impressions"]) * 100, 2
                )
        
        # Generate summary file
        summary_path = _generate_summary_file(summary_data)
        
        _log_to_file("twitter_poster.log", f"Generated Twitter summary: {summary_path}", "SUCCESS")
        return summary_path
        
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error generating Twitter summary: {str(e)}", "ERROR")
        return None


def _fetch_tweets_with_metrics(since_date):
    """Fetch tweets with engagement metrics from Twitter API."""
    try:
        if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
            _log_to_file("twitter_poster.log", "Twitter credentials not configured", "ERROR")
            return []
        
        # First, get the user's tweet IDs
        url = f"{TWITTER_API_URL}/tweets/search/recent"
        
        headers = _get_oauth1_headers("GET", url)
        
        # Note: Twitter API v2 search requires Elevated access
        params = {
            "query": "from:me",  # Tweets from authenticated user
            "max_results": 100,
            "tweet.fields": "created_at,public_metrics,context_annotations"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            # If search fails, try user timeline endpoint
            _log_to_file("twitter_poster.log", "Search failed, trying user timeline", "WARNING")
            return _fetch_user_timeline(since_date)
        
        result = response.json()
        tweets = []
        
        for tweet in result.get("data", []):
            metrics = tweet.get("public_metrics", {})
            tweet_data = {
                "id": tweet.get("id"),
                "text": tweet.get("text", "")[:100],
                "created_at": tweet.get("created_at"),
                "impressions": metrics.get("impression_count", 0),
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "total_engagement": metrics.get("like_count", 0) + metrics.get("retweet_count", 0) + metrics.get("reply_count", 0)
            }
            tweets.append(tweet_data)
        
        return tweets
        
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error fetching tweets: {str(e)}", "ERROR")
        return []


def _fetch_user_timeline(since_date):
    """Fetch user's tweet timeline as fallback."""
    try:
        # Get user ID first
        me_url = f"{TWITTER_API_URL}/users/me"
        me_headers = _get_oauth1_headers("GET", me_url)
        
        me_response = requests.get(me_url, headers=me_headers, timeout=30)
        if me_response.status_code != 200:
            _log_to_file("twitter_poster.log", "Could not fetch user ID", "ERROR")
            return []
        
        user_id = me_response.json().get("data", {}).get("id")
        if not user_id:
            return []
        
        # Fetch user's tweets
        url = f"{TWITTER_API_URL}/users/{user_id}/tweets"
        headers = _get_oauth1_headers("GET", url)
        
        params = {
            "max_results": 100,
            "tweet.fields": "created_at,public_metrics",
            "exclude": "retweets,replies"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            _log_to_file("twitter_poster.log", f"Timeline fetch failed: {response.status_code}", "ERROR")
            return []
        
        result = response.json()
        tweets = []
        
        for tweet in result.get("data", []):
            metrics = tweet.get("public_metrics", {})
            tweet_data = {
                "id": tweet.get("id"),
                "text": tweet.get("text", "")[:100],
                "created_at": tweet.get("created_at"),
                "impressions": metrics.get("impression_count", 0),
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "total_engagement": metrics.get("like_count", 0) + metrics.get("retweet_count", 0) + metrics.get("reply_count", 0)
            }
            tweets.append(tweet_data)
        
        return tweets
        
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error fetching timeline: {str(e)}", "ERROR")
        return []


def _generate_summary_file(summary_data):
    """Generate markdown summary file."""
    try:
        filename = f"twitter_summary_{datetime.now().strftime('%Y-%m-%d')}.md"
        filepath = BRIEFINGS_DIR / filename
        
        content = f"""# Twitter Summary

**Generated:** {summary_data.get("generated_at", "N/A")}

**Period:** Last 7 days

---

## Overview

| Metric | Value |
|--------|-------|
| Total Tweets | {len(summary_data.get("tweets", []))} |
| Total Impressions | {summary_data.get("total_impressions", 0):,} |
| Total Likes | {summary_data.get("total_likes", 0):,} |
| Total Retweets | {summary_data.get("total_retweets", 0):,} |
| Total Replies | {summary_data.get("total_replies", 0):,} |
| **Engagement Rate** | **{summary_data.get("engagement_rate", 0):.2f}%** |

---

## Best Performing Tweet

"""
        
        best = summary_data.get("best_performing")
        if best:
            content += f"""
| Metric | Value |
|--------|-------|
| Tweet ID | {best.get("id", "N/A")} |
| Posted | {best.get("created_at", "N/A")[:10] if best.get("created_at") else "N/A"} |
| Content | {best.get("text", "N/A")} |
| Impressions | {best.get("impressions", 0):,} |
| Likes | {best.get("likes", 0):,} |
| Retweets | {best.get("retweets", 0):,} |
| Replies | {best.get("replies", 0):,} |

[View Tweet](https://twitter.com/i/web/status/{best.get("id", "")})
"""
        else:
            content += "*No tweets in this period*\n"
        
        content += """
---

## Recent Tweets

| Date | Content | Impressions | Likes | RTs | Replies |
|------|---------|-------------|-------|-----|---------|
"""
        
        for tweet in summary_data.get("tweets", [])[:10]:
            date = tweet.get("created_at", "N/A")[:10] if tweet.get("created_at") else "N/A"
            text = tweet.get("text", "No content")[:40] + "..." if len(tweet.get("text", "")) > 40 else tweet.get("text", "No content")
            content += f"| {date} | {text} | {tweet.get('impressions', 0):,} | {tweet.get('likes', 0):,} | {tweet.get('retweets', 0):,} | {tweet.get('replies', 0):,} |\n"
        
        if not summary_data.get("tweets"):
            content += "| - | No tweets in this period | - | - | - | - |\n"
        
        content += """
---

*Report generated by twitter_poster.py*
"""
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return str(filepath)
        
    except Exception as e:
        _log_to_file("twitter_poster.log", f"Error generating summary file: {str(e)}", "ERROR")
        return None


def run_scheduler():
    """Run the scheduler to check for approved tweets periodically."""
    _log_to_file("twitter_poster.log", "Starting Twitter Poster scheduler", "INFO")
    
    # Check for approved tweets every 15 minutes
    schedule.every(15).minutes.do(post_approved_tweet)
    
    # Generate summary daily at 9 AM
    schedule.every().day.at("09:00").do(get_twitter_summary)
    
    _log_to_file("twitter_poster.log", "Scheduler configured: checking every 15 minutes", "INFO")
    
    while True:
        schedule.run_pending()
        time.sleep(60)


# Example usage / testing
if __name__ == "__main__":
    print(f"{Fore.CYAN}=== Twitter Poster Tool ===")
    print(f"API Key configured: {'Yes' if TWITTER_API_KEY else 'No'}")
    print(f"Access Token configured: {'Yes' if TWITTER_ACCESS_TOKEN else 'No'}")
    print(f"Dry Run Mode: {DRY_RUN}")
    print()
    
    # Test generate_tweet
    print(f"{Fore.CYAN}--- Testing Tweet Generation ---")
    generated = generate_tweet("AI productivity tips")
    if generated:
        print(f"{Fore.GREEN}Generated file: {generated}")
    
    # Test post_approved_tweet (move generated file to Approved first)
    print(f"\n{Fore.CYAN}--- Testing Tweet Posting ---")
    posted = post_approved_tweet()
    if posted:
        print(f"{Fore.GREEN}Posted tweets: {posted}")
    
    # Test post_thread
    print(f"\n{Fore.CYAN}--- Testing Thread Posting ---")
    thread = post_thread(["AI tip 1", "AI tip 2", "AI tip 3"])
    if thread:
        print(f"{Fore.GREEN}Thread posted: {thread.get('tweet_count')} tweets")
    
    # Test get_twitter_summary
    print(f"\n{Fore.CYAN}--- Testing Twitter Summary ---")
    summary = get_twitter_summary()
    if summary:
        print(f"{Fore.GREEN}Summary saved to: {summary}")
    
    print(f"\n{Fore.CYAN}To run scheduler: python twitter_poster.py --scheduler")
