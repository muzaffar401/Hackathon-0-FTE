# 1. Go to developers.facebook.com
# 2. Create App → Business type
# 3. Add Facebook Login + Instagram Graph API products
# 4. Get Page Access Token from Graph API Explorer
# 5. Convert to Long-Lived Token (60 days)

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
from openai import OpenAI

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
APPROVED_DIR = BASE_DIR / "Approved"
PENDING_DIR = BASE_DIR / "Pending_Approval"
DONE_DIR = BASE_DIR / "Done"
LOGS_DIR = BASE_DIR / "Logs"
BRIEFINGS_DIR = BASE_DIR / "Briefings"

# Ensure directories exist
for directory in [APPROVED_DIR, PENDING_DIR, DONE_DIR, LOGS_DIR, BRIEFINGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Meta API Configuration
META_API_VERSION = "v18.0"
GRAPH_API_URL = f"https://graph.facebook.com/{META_API_VERSION}"

# Environment variables
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Qwen/OpenAI client (adjust base_url if using different provider)
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


def generate_social_post(topic, platform="both"):
    """
    Generate social media post content using Qwen AI.
    
    Args:
        topic: The topic/theme for the post
        platform: 'facebook', 'instagram', or 'both'
    
    Returns:
        Path to generated file, or None if failed
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Define platform-specific prompts
        platform_prompts = {
            "facebook": {
                "system": f"""You are a social media expert. Write an engaging post for Facebook.
Style guidelines:
- Conversational and friendly tone
- Maximum 150 words
- Include 2-3 relevant hashtags at the end
- Focus on engagement and conversation starters
- Avoid excessive emojis (1-2 max)""",
                "user": f"Write a Facebook post about: {topic}"
            },
            "instagram": {
                "system": f"""You are a social media expert. Write an engaging post for Instagram.
Style guidelines:
- Visual-focused, evocative language
- Maximum 100 words
- Include 5-8 relevant hashtags
- Emoji friendly (3-5 emojis)
- Focus on inspiration and aesthetics""",
                "user": f"Write an Instagram post about: {topic}"
            }
        }
        
        platforms_to_generate = ["facebook", "instagram"] if platform == "both" else [platform]
        generated_files = []
        
        for plat in platforms_to_generate:
            prompt_config = platform_prompts[plat]
            
            # Generate content using OpenAI-compatible API
            content = _call_qwen_api(
                system_prompt=prompt_config["system"],
                user_prompt=prompt_config["user"]
            )
            
            if not content:
                _log_to_file("meta_poster.log", f"Failed to generate content for {plat}", "ERROR")
                continue
            
            # Parse content and hashtags
            post_content, hashtags = _parse_post_content(content)
            
            # Create markdown file
            filename = f"META_{plat}_{timestamp}.md"
            filepath = PENDING_DIR / filename
            
            md_content = f"""---
type: meta_post
platform: {plat}
topic: {topic}
generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
status: pending_approval
---
## Post Content

{post_content}

## Hashtags

{hashtags}

## To Approve

Move this file to /Approved/ to publish this post.
"""
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            generated_files.append(filepath)
            _log_to_file("meta_poster.log", f"Generated {plat} post: {filename}", "SUCCESS")
        
        return generated_files if generated_files else None
        
    except Exception as e:
        _log_to_file("meta_poster.log", f"Error generating post: {str(e)}", "ERROR")
        return None


def _call_qwen_api(system_prompt, user_prompt):
    """Call Qwen/OpenRouter API to generate content."""
    try:
        if not OPENROUTER_API_KEY:
            _log_to_file("meta_poster.log", "OPENROUTER_API_KEY not set. Cannot generate content.", "ERROR")
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
            "max_tokens": 500,
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
        _log_to_file("meta_poster.log", f"API request failed: {str(e)}", "ERROR")
        return None
    except Exception as e:
        _log_to_file("meta_poster.log", f"Error calling Qwen API: {str(e)}", "ERROR")
        return None


def _parse_post_content(content):
    """Parse generated content to separate post text and hashtags."""
    lines = content.strip().split("\n")
    
    # Find hashtags (lines starting with #)
    hashtags = []
    post_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            hashtags.append(stripped)
        else:
            post_lines.append(line)
    
    # If no hashtags found, add default ones
    if not hashtags:
        hashtags = ["#SocialMedia", "#Content"]
    
    post_content = "\n".join(post_lines).strip()
    hashtag_string = " ".join(hashtags)
    
    return post_content, hashtag_string


def post_to_facebook(content):
    """
    Post content to Facebook Page.
    
    Args:
        content: The post content/message
    
    Returns:
        Post ID if successful, None otherwise
    """
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        _log_to_file("meta_poster.log", "Facebook credentials not configured", "ERROR")
        return None
    
    if DRY_RUN:
        _log_to_file("meta_poster.log", f"[DRY RUN] Would post to Facebook: {content[:50]}...", "INFO")
        return "dry_run_" + _generate_content_hash(content)
    
    try:
        url = f"{GRAPH_API_URL}/{FB_PAGE_ID}/feed"
        
        params = {
            "message": content,
            "access_token": FB_PAGE_ACCESS_TOKEN
        }
        
        response = requests.post(url, params=params, timeout=30)
        result = response.json()
        
        if "id" in result:
            post_id = result["id"]
            _log_to_file("meta_poster.log", f"Facebook post successful. Post ID: {post_id}", "SUCCESS")
            return post_id
        else:
            error_msg = result.get("error", {}).get("message", "Unknown error")
            _log_to_file("meta_poster.log", f"Facebook post failed: {error_msg}", "ERROR")
            return None
            
    except requests.exceptions.RequestException as e:
        _log_to_file("meta_poster.log", f"Facebook API request failed: {str(e)}", "ERROR")
        return None
    except Exception as e:
        _log_to_file("meta_poster.log", f"Error posting to Facebook: {str(e)}", "ERROR")
        return None


def post_to_instagram(content, image_url=None):
    """
    Post content to Instagram Business account.
    
    Args:
        content: The caption content
        image_url: Optional image URL (if not provided, creates text-only post)
    
    Returns:
        Post ID if successful, None otherwise
    """
    if not IG_USER_ID or not IG_ACCESS_TOKEN:
        _log_to_file("meta_poster.log", "Instagram credentials not configured", "ERROR")
        return None
    
    if DRY_RUN:
        _log_to_file("meta_poster.log", f"[DRY RUN] Would post to Instagram: {content[:50]}...", "INFO")
        return "dry_run_" + _generate_content_hash(content)
    
    try:
        # Step 1: Create media container
        container_url = f"{GRAPH_API_URL}/{IG_USER_ID}/media"
        
        # For Instagram, we need an image or video
        # If no image_url provided, we'll create a simple text post
        if not image_url:
            # Create a placeholder image URL (you should provide actual images)
            image_url = "https://via.placeholder.com/1080x1080.png?text=Post"
        
        container_params = {
            "caption": content,
            "image_url": image_url,
            "access_token": IG_ACCESS_TOKEN
        }
        
        # Create container
        container_response = requests.post(container_url, params=container_params, timeout=30)
        container_result = container_response.json()
        
        if "id" not in container_result:
            error_msg = container_result.get("error", {}).get("message", "Unknown error")
            _log_to_file("meta_poster.log", f"Instagram container creation failed: {error_msg}", "ERROR")
            return None
        
        container_id = container_result["id"]
        
        # Step 2: Publish the container
        publish_url = f"{GRAPH_API_URL}/{IG_USER_ID}/media_publish"
        publish_params = {
            "creation_id": container_id,
            "access_token": IG_ACCESS_TOKEN
        }
        
        publish_response = requests.post(publish_url, params=publish_params, timeout=30)
        publish_result = publish_response.json()
        
        if "id" in publish_result:
            post_id = publish_result["id"]
            _log_to_file("meta_poster.log", f"Instagram post successful. Post ID: {post_id}", "SUCCESS")
            return post_id
        else:
            error_msg = publish_result.get("error", {}).get("message", "Unknown error")
            _log_to_file("meta_poster.log", f"Instagram publish failed: {error_msg}", "ERROR")
            return None
            
    except requests.exceptions.RequestException as e:
        _log_to_file("meta_poster.log", f"Instagram API request failed: {str(e)}", "ERROR")
        return None
    except Exception as e:
        _log_to_file("meta_poster.log", f"Error posting to Instagram: {str(e)}", "ERROR")
        return None


def post_approved_content():
    """
    Watch /Approved/ for META_*.md files and post them.
    
    Returns:
        List of posted file info dicts
    """
    posted_files = []
    
    try:
        # Find all META_*.md files in Approved directory
        approved_files = list(APPROVED_DIR.glob("META_*.md"))
        
        if not approved_files:
            _log_to_file("meta_poster.log", "No approved META files to process", "INFO")
            return posted_files
        
        for filepath in approved_files:
            try:
                # Read the file
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Parse frontmatter
                frontmatter, body = _parse_frontmatter(content)
                
                # Check if already processed
                if frontmatter.get("status") == "posted":
                    _log_to_file("meta_poster.log", f"Skipping already posted file: {filepath.name}", "INFO")
                    continue
                
                platform = frontmatter.get("platform", "facebook")
                topic = frontmatter.get("topic", "untitled")
                
                # Extract post content and hashtags
                post_content = _extract_section(body, "Post Content")
                hashtags = _extract_section(body, "Hashtags")
                
                full_content = f"{post_content}\n\n{hashtags}".strip()
                
                # Post to appropriate platform(s)
                post_result = {
                    "file": filepath.name,
                    "platform": platform,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "success",
                    "post_id": None
                }
                
                if platform in ["facebook", "both"]:
                    fb_post_id = post_to_facebook(full_content)
                    if fb_post_id:
                        post_result["facebook_post_id"] = fb_post_id
                    else:
                        post_result["status"] = "partial"
                
                if platform in ["instagram", "both"]:
                    ig_post_id = post_to_instagram(full_content)
                    if ig_post_id:
                        post_result["instagram_post_id"] = ig_post_id
                    else:
                        post_result["status"] = "partial"
                
                # Log the post
                _log_post_result(post_result)
                
                # Move file to Done directory
                done_path = DONE_DIR / filepath.name
                shutil.move(str(filepath), str(done_path))
                
                # Update the file with posted status
                _update_file_status(done_path, post_result)
                
                # Update Dashboard
                _update_dashboard(post_result)
                
                posted_files.append(post_result)
                _log_to_file("meta_poster.log", f"Processed and moved: {filepath.name}", "SUCCESS")
                
            except Exception as e:
                _log_to_file("meta_poster.log", f"Error processing {filepath.name}: {str(e)}", "ERROR")
        
        return posted_files
        
    except Exception as e:
        _log_to_file("meta_poster.log", f"Error in post_approved_content: {str(e)}", "ERROR")
        return posted_files


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
    platform = result.get("platform", "unknown")
    status = result.get("status", "unknown")
    post_id = result.get("post_id") or result.get(f"{platform.split('_')[0]}_post_id", "N/A")
    
    log_message = f"Platform: {platform} | Status: {status} | Post ID: {post_id}"
    _log_to_file("facebook_posts.log" if "facebook" in platform else "instagram_posts.log", log_message, "SUCCESS")


def _update_file_status(filepath, post_result):
    """Update the markdown file with posted status."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Update frontmatter status
        content = content.replace("status: pending_approval", "status: posted")
        content = content.replace("status: posted", f"status: posted\nposted_at: {post_result['timestamp']}")
        
        # Add post IDs
        if "facebook_post_id" in post_result:
            content += f"\n\n## Posted\n- Facebook Post ID: {post_result['facebook_post_id']}"
        if "instagram_post_id" in post_result:
            content += f"\n- Instagram Post ID: {post_result['instagram_post_id']}"
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
    except Exception as e:
        _log_to_file("meta_poster.log", f"Error updating file status: {str(e)}", "ERROR")


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
        platform = post_result.get("platform", "unknown")
        status = post_result.get("status", "unknown")
        timestamp = post_result.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        activity_entry = f"- [{timestamp}] Posted to {platform.upper()} | Status: {status}\n"
        
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
        _log_to_file("meta_poster.log", f"Error updating dashboard: {str(e)}", "ERROR")


def get_post_summary():
    """
    Fetch last 7 days of posts from both platforms and generate summary.
    
    Returns:
        Path to summary file, or None if failed
    """
    try:
        today = datetime.now()
        seven_days_ago = today - timedelta(days=7)
        
        summary_data = {
            "facebook": {"posts": [], "total_likes": 0, "total_comments": 0, "total_shares": 0},
            "instagram": {"posts": [], "total_likes": 0, "total_comments": 0, "total_saves": 0},
            "generated_at": today.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Fetch Facebook posts
        if FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN:
            fb_posts = _fetch_facebook_posts(seven_days_ago)
            if fb_posts:
                summary_data["facebook"]["posts"] = fb_posts
                for post in fb_posts:
                    summary_data["facebook"]["total_likes"] += post.get("likes", 0)
                    summary_data["facebook"]["total_comments"] += post.get("comments", 0)
                    summary_data["facebook"]["total_shares"] += post.get("shares", 0)
        
        # Fetch Instagram posts
        if IG_USER_ID and IG_ACCESS_TOKEN:
            ig_posts = _fetch_instagram_posts(seven_days_ago)
            if ig_posts:
                summary_data["instagram"]["posts"] = ig_posts
                for post in ig_posts:
                    summary_data["instagram"]["total_likes"] += post.get("likes", 0)
                    summary_data["instagram"]["total_comments"] += post.get("comments", 0)
                    summary_data["instagram"]["total_saves"] += post.get("saves", 0)
        
        # Generate summary file
        summary_path = _generate_summary_file(summary_data)
        
        _log_to_file("meta_poster.log", f"Generated post summary: {summary_path}", "SUCCESS")
        return summary_path
        
    except Exception as e:
        _log_to_file("meta_poster.log", f"Error generating post summary: {str(e)}", "ERROR")
        return None


def _fetch_facebook_posts(since_date):
    """Fetch Facebook posts with engagement metrics."""
    try:
        url = f"{GRAPH_API_URL}/{FB_PAGE_ID}/posts"
        params = {
            "fields": "id,message,created_time,permalink_url,likes.summary(true),comments.summary(true),shares",
            "since": since_date.strftime("%Y-%m-%d"),
            "access_token": FB_PAGE_ACCESS_TOKEN,
            "limit": 50
        }
        
        response = requests.get(url, params=params, timeout=30)
        result = response.json()
        
        posts = []
        for post in result.get("data", []):
            post_data = {
                "id": post.get("id"),
                "message": post.get("message", "")[:100],
                "created_time": post.get("created_time"),
                "permalink": post.get("permalink_url"),
                "likes": post.get("likes", {}).get("summary", {}).get("total_count", 0),
                "comments": post.get("comments", {}).get("summary", {}).get("total_count", 0),
                "shares": post.get("shares", {}).get("count", 0)
            }
            posts.append(post_data)
        
        return posts
        
    except Exception as e:
        _log_to_file("meta_poster.log", f"Error fetching Facebook posts: {str(e)}", "ERROR")
        return []


def _fetch_instagram_posts(since_date):
    """Fetch Instagram posts with engagement metrics."""
    try:
        url = f"{GRAPH_API_URL}/{IG_USER_ID}/media"
        params = {
            "fields": "id,caption,timestamp,permalink,like_count,comments_count,saved",
            "since": since_date.strftime("%Y-%m-%d"),
            "access_token": IG_ACCESS_TOKEN,
            "limit": 50
        }
        
        response = requests.get(url, params=params, timeout=30)
        result = response.json()
        
        posts = []
        for post in result.get("data", []):
            post_data = {
                "id": post.get("id"),
                "caption": post.get("caption", "")[:100],
                "timestamp": post.get("timestamp"),
                "permalink": post.get("permalink"),
                "likes": post.get("like_count", 0),
                "comments": post.get("comments_count", 0),
                "saves": post.get("saved", 0)
            }
            posts.append(post_data)
        
        return posts
        
    except Exception as e:
        _log_to_file("meta_poster.log", f"Error fetching Instagram posts: {str(e)}", "ERROR")
        return []


def _generate_summary_file(summary_data):
    """Generate markdown summary file."""
    try:
        filename = f"social_summary_{datetime.now().strftime('%Y-%m-%d')}.md"
        filepath = BRIEFINGS_DIR / filename
        
        fb_data = summary_data.get("facebook", {})
        ig_data = summary_data.get("instagram", {})
        
        content = f"""# Social Media Summary

**Generated:** {summary_data.get("generated_at", "N/A")}

**Period:** Last 7 days

---

## Facebook Page

### Overview

| Metric | Value |
|--------|-------|
| Total Posts | {len(fb_data.get("posts", []))} |
| Total Likes | {fb_data.get("total_likes", 0)} |
| Total Comments | {fb_data.get("total_comments", 0)} |
| Total Shares | {fb_data.get("total_shares", 0)} |

### Recent Posts

| Date | Message | Likes | Comments | Shares |
|------|---------|-------|----------|--------|
"""
        
        for post in fb_data.get("posts", [])[:10]:
            date = post.get("created_time", "N/A")[:10] if post.get("created_time") else "N/A"
            message = post.get("message", "No content")[:50] + "..." if len(post.get("message", "")) > 50 else post.get("message", "No content")
            content += f"| {date} | {message} | {post.get('likes', 0)} | {post.get('comments', 0)} | {post.get('shares', 0)} |\n"
        
        if not fb_data.get("posts"):
            content += "| - | No posts in this period | - | - | - |\n"
        
        content += f"""
---

## Instagram Business

### Overview

| Metric | Value |
|--------|-------|
| Total Posts | {len(ig_data.get("posts", []))} |
| Total Likes | {ig_data.get("total_likes", 0)} |
| Total Comments | {ig_data.get("total_comments", 0)} |
| Total Saves | {ig_data.get("total_saves", 0)} |

### Recent Posts

| Date | Caption | Likes | Comments | Saves |
|------|---------|-------|----------|-------|
"""
        
        for post in ig_data.get("posts", [])[:10]:
            date = post.get("timestamp", "N/A")[:10] if post.get("timestamp") else "N/A"
            caption = post.get("caption", "No content")[:50] + "..." if len(post.get("caption", "")) > 50 else post.get("caption", "No content")
            content += f"| {date} | {caption} | {post.get('likes', 0)} | {post.get('comments', 0)} | {post.get('saves', 0)} |\n"
        
        if not ig_data.get("posts"):
            content += "| - | No posts in this period | - | - | - |\n"
        
        content += """
---

*Report generated by meta_poster.py*
"""
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return str(filepath)
        
    except Exception as e:
        _log_to_file("meta_poster.log", f"Error generating summary file: {str(e)}", "ERROR")
        return None


def run_scheduler():
    """Run the scheduler to check for approved content periodically."""
    _log_to_file("meta_poster.log", "Starting Meta Poster scheduler", "INFO")
    
    # Check for approved content every 15 minutes
    schedule.every(15).minutes.do(post_approved_content)
    
    # Generate summary daily at 9 AM
    schedule.every().day.at("09:00").do(get_post_summary)
    
    _log_to_file("meta_poster.log", "Scheduler configured: checking every 15 minutes", "INFO")
    
    while True:
        schedule.run_pending()
        time.sleep(60)


# Example usage / testing
if __name__ == "__main__":
    print(f"{Fore.CYAN}=== Meta Poster Tool ===")
    print(f"Facebook Page ID: {FB_PAGE_ID or 'Not configured'}")
    print(f"Instagram User ID: {IG_USER_ID or 'Not configured'}")
    print(f"Dry Run Mode: {DRY_RUN}")
    print()
    
    # Test generate_social_post
    print(f"{Fore.CYAN}--- Testing Post Generation ---")
    generated = generate_social_post("AI productivity tips", "both")
    if generated:
        print(f"{Fore.GREEN}Generated files: {generated}")
    
    # Test post_approved_content (move generated files to Approved first)
    print(f"\n{Fore.CYAN}--- Testing Post Publishing ---")
    posted = post_approved_content()
    if posted:
        print(f"{Fore.GREEN}Posted files: {posted}")
    
    # Test get_post_summary
    print(f"\n{Fore.CYAN}--- Testing Post Summary ---")
    summary = get_post_summary()
    if summary:
        print(f"{Fore.GREEN}Summary saved to: {summary}")
    
    print(f"\n{Fore.CYAN}To run scheduler: python meta_poster.py --scheduler")
