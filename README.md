# AI Employee Vault - Complete Guide

## 📋 Overview

AI Employee Vault is a comprehensive autonomous business automation system that monitors, analyzes, and acts on business tasks across multiple channels. The system is organized into **Three Tiers** (Bronze, Silver, Gold), each adding more capabilities and integrations.

### Core Capabilities

| Tier | Focus | Features |
|------|-------|----------|
| **Bronze** | File & Task Management | File watching, AI analysis, action plans, approval workflow |
| **Silver** | Communication & Social | WhatsApp, Gmail, LinkedIn automation |
| **Gold** | Business Intelligence | Odoo ERP, Facebook, Instagram, Twitter, autonomous loops, weekly audits |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI EMPLOYEE VAULT SYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    BRONZE TIER - Core Foundation                     │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │   │
│  │  │  Inbox   │→ │ file_watcher │→ │ Needs_Action│→ │ orchestrator │  │   │
│  │  └──────────┘  └──────────────┘  └─────────────┘  └──────────────┘  │   │
│  │                                              │                       │   │
│  │                                              ↓                       │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │   │
│  │  │  Done    │← │   approve.py │← │Pending_Appro│← │    Plans     │  │   │
│  │  └──────────┘  └──────────────┘  └─────────────┘  └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    SILVER TIER - Communication                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   │
│  │  │  WhatsApp    │  │    Gmail     │  │      LinkedIn            │   │   │
│  │  │   Watcher    │  │   Watcher    │  │       Poster             │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      GOLD TIER - Business Intelligence               │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │   │
│  │  │  Odoo    │  │ Facebook │  │ Instagram│  │       Twitter        │ │   │
│  │  │   MCP    │  │   API    │  │   API    │  │         API          │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────────┘ │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │   │
│  │  │   Ralph Loop (Autonomous Worker)  │   Weekly Audit (CEO Brief)  │ │   │
│  │  └──────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Directory Structure

```
AI_Employee_Vault/
├── 📥 Inbox/                   # Drop new files here (Bronze)
├── ⚠️ Needs_Action/            # Pending tasks from all sources
├── 📋 Plans/                   # AI-generated action plans
├── ⏳ Pending_Approval/        # High-risk tasks awaiting approval
├── ✅ Approved/                # Content ready to publish (LinkedIn, Social)
├── 📁 Done/                    # Completed tasks
│   └── Threads/                # Twitter threads (Gold)
├── 📊 Logs/                    # JSON logs and test results
├── 📰 Briefings/               # CEO briefings, social summaries (Gold)
├── 💰 Accounting/              # Financial summaries (Gold)
├── 🚨 Needs_Action/            # Failed tasks, auth errors

├── 🤖 CORE SERVICES (Bronze)
│   ├── file_watcher.py         # Monitors Inbox for new files
│   ├── orchestrator.py         # AI analysis and plan generation
│   └── approve.py              # Approval management interface
│
├── 📱 COMMUNICATION (Silver)
│   ├── whatsapp_watcher.py     # WhatsApp Web keyword monitoring
│   ├── gmail_watcher.py        # Gmail unread/important monitoring
│   └── linkedin_poster.py      # LinkedIn post generation & publishing
│
├── 💼 BUSINESS INTELLIGENCE (Gold)
│   ├── odoo_mcp.py             # Odoo ERP integration (invoices, revenue)
│   ├── meta_poster.py          # Facebook & Instagram posting
│   ├── twitter_poster.py       # Twitter/X posting and threads
│   ├── ralph_loop.py           # Autonomous AI worker loop
│   ├── weekly_audit.py         # Weekly CEO briefing generator
│   └── test_gold.py            # Gold Tier test suite
│
├── 📄 CONFIGURATION & DOCS
│   ├── .env                    # Environment variables (API keys)
│   ├── Dashboard.md            # Live project dashboard
│   ├── Company_Handbook.md     # Company guidelines
│   └── README.md               # This file
│
AI_Employee_Project/
├── whatsapp_session/           # WhatsApp Web persistent session
├── gmail_credentials.json      # Google OAuth credentials
├── gmail_token.json            # Gmail OAuth token (auto-created)
├── whatsapp_processed.json     # Processed WhatsApp message tracking
└── processed_emails.json       # Processed Gmail message tracking
```

---

## 🥉 BRONZE TIER - Core Foundation

The Bronze Tier provides the fundamental task management and AI analysis capabilities.

### Features

- ✅ **File Monitoring** - Real-time Inbox watching
- ✅ **AI Analysis** - OpenRouter/Qwen integration for task understanding
- ✅ **Action Plans** - Step-by-step instructions generated by AI
- ✅ **Risk Assessment** - LOW/MEDIUM/HIGH classification
- ✅ **Approval Workflow** - Human review for high-risk tasks
- ✅ **Audit Trail** - Complete JSON logging

### Components

| File | Purpose |
|------|---------|
| `file_watcher.py` | Monitors Inbox, creates task files in Needs_Action |
| `orchestrator.py` | Analyzes tasks with AI, generates plans, assesses risk |
| `approve.py` | Interactive approval/rejection interface |
| `test_bronze.py` | Bronze Tier test suite (5 tests) |

### How to Start Bronze Tier

```bash
# Terminal 1: File Watcher
python file_watcher.py

# Terminal 2: Orchestrator
python orchestrator.py

# When needed: Approval Manager
python approve.py

# Test the setup
python test_bronze.py
```

### Bronze Tier Workflow

```
1. Drop file in Inbox/
   ↓
2. file_watcher.py detects → Creates task in Needs_Action/
   ↓
3. orchestrator.py picks up → Sends to AI
   ↓
4. AI returns: Plan + Risk Level
   ↓
5. If HIGH RISK → Copied to Pending_Approval/
   ↓
6. User runs approve.py → Approves/Rejects
   ↓
7. Task moved to Done/
```

### Test Results (5/5 = Success)

```bash
python test_bronze.py

# Tests:
# 1. Folder Structure - All directories exist
# 2. Required Files - Dashboard.md, Company_Handbook.md present
# 3. Dependencies - watchdog, colorama, openai, dotenv installed
# 4. API Connectivity - OpenRouter/Qwen responds
# 5. End-to-End - File drop → task creation works
```

---

## 🥈 SILVER TIER - Communication & Social

The Silver Tier adds communication channel monitoring and social media automation.

### Features

- ✅ **WhatsApp Monitoring** - Keyword-based task creation from WhatsApp Web
- ✅ **Gmail Monitoring** - Unread + Important emails → tasks
- ✅ **LinkedIn Automation** - AI-generated posts, approval workflow, auto-publishing

### Components

| File | Purpose |
|------|---------|
| `whatsapp_watcher.py` | Monitors WhatsApp Web, creates tasks for keyword matches |
| `gmail_watcher.py` | Polls Gmail API, creates tasks for important unread emails |
| `linkedin_poster.py` | Generates posts with AI, publishes approved content |

### WhatsApp Watcher Setup

```bash
# Install dependencies
pip install playwright colorama python-dotenv
playwright install chromium

# Start watcher
python whatsapp_watcher.py

# First run: Scan QR code with WhatsApp (Linked Devices)
# Session saved to AI_Employee_Project/whatsapp_session/
```

**Keywords Monitored:**
- **High Priority:** `invoice`, `payment`, `urgent`, `asap`
- **Normal:** `price`, `quote`, `help`, `project`

### Gmail Watcher Setup

```bash
# Install dependencies
pip install google-auth google-auth-oauthlib google-api-python-client colorama python-dotenv

# Google Cloud Console setup:
# 1. Go to https://console.cloud.google.com/
# 2. Create project → Enable Gmail API
# 3. Create OAuth 2.0 Client ID (Desktop app)
# 4. Download JSON → Save as AI_Employee_Project/gmail_credentials.json

# Start watcher
python gmail_watcher.py

# First run: Browser opens for Google sign-in
# Token saved to AI_Employee_Project/gmail_token.json
```

### LinkedIn Poster Setup

```bash
# Install dependencies
pip install requests colorama python-dotenv openai

# LinkedIn Developer setup:
# 1. Go to https://www.linkedin.com/developers/apps
# 2. Create app → Request: w_member_social, profile, openid
# 3. Get access token

# Add to .env:
LINKEDIN_ACCESS_TOKEN=your_token
LINKEDIN_AUTHOR_URN=urn:li:person:YOUR_ID  # Run: python linkedin_poster.py --whoami

# Generate a post draft
python linkedin_poster.py --generate "AI productivity tips"

# Post approved content (move from Pending_Approval to Approved first)
python linkedin_poster.py --post

# Run scheduler (posts every 10 minutes)
python linkedin_poster.py
```

### Start All Silver Tier Services

```bash
# Terminal 3: WhatsApp Watcher
python whatsapp_watcher.py

# Terminal 4: Gmail Watcher
python gmail_watcher.py

# Terminal 5: LinkedIn Poster (scheduler mode)
python linkedin_poster.py
```

---

## 🥇 GOLD TIER - Business Intelligence

The Gold Tier provides full business automation with ERP integration, social media management across all platforms, autonomous AI workers, and automated executive reporting.

### Features

- ✅ **Odoo ERP Integration** - Invoices, revenue, expenses, overdue tracking
- ✅ **Facebook Posting** - Page posts via Graph API
- ✅ **Instagram Posting** - Business account posts via Graph API
- ✅ **Twitter/X Posting** - Tweets and threads via API v2
- ✅ **Ralph Loop** - Autonomous AI worker that persists until task completion
- ✅ **Weekly Audit** - Automated Monday Morning CEO Briefing every Sunday

### Components

| File | Purpose |
|------|---------|
| `odoo_mcp.py` | Odoo JSON-RPC integration (invoices, revenue, expenses) |
| `meta_poster.py` | Facebook & Instagram post generation and publishing |
| `twitter_poster.py` | Twitter/X tweets, threads, engagement summaries |
| `ralph_loop.py` | Autonomous AI worker loop pattern |
| `weekly_audit.py` | Weekly business audit and CEO briefing generator |
| `test_gold.py` | Gold Tier test suite (7 tests) |

### Odoo ERP Setup

```bash
# Install dependencies
pip install requests python-dotenv colorama

# Docker setup (recommended):
docker run -p 8069:8069 odoo:17

# Or install Odoo Community: https://www.odoo.com/documentation

# Add to .env:
ODOO_URL=http://localhost:8069
ODOO_DB=your_db_name
ODOO_USER=admin
ODOO_PASSWORD=your_password
```

### Meta (Facebook/Instagram) Setup

```bash
# Install dependencies
pip install requests schedule python-dotenv colorama openai

# Facebook Developer setup:
# 1. Go to https://developers.facebook.com/
# 2. Create App → Business type
# 3. Add: Facebook Login + Instagram Graph API products
# 4. Get Page Access Token from Graph API Explorer
# 5. Convert to Long-Lived Token (60 days)

# Add to .env:
FB_PAGE_ID=your_page_id
FB_PAGE_ACCESS_TOKEN=your_token
IG_USER_ID=your_ig_user_id
IG_ACCESS_TOKEN=your_token
```

### Twitter/X Setup

```bash
# Install dependencies
pip install tweepy requests python-dotenv colorama openai

# Twitter Developer setup:
# 1. Go to https://developer.twitter.com/
# 2. Create Project + App
# 3. Apply for Elevated access (free, required for posting)
# 4. Generate all 4 keys from App Settings → Keys and Tokens

# Add to .env:
TWITTER_API_KEY=your_key
TWITTER_API_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_SECRET=your_token_secret
```

### Ralph Loop - Autonomous AI Worker

Ralph Loop keeps Qwen working on a task until it's 100% complete or max iterations reached.

```python
from ralph_loop import RalphLoop, contains_phrase

# Example: Process all files in Needs_Action
ralph = RalphLoop(
    task_description="Process all files in Needs_Action, create plans, move to Done",
    completion_check_fn=lambda r: "<TASK_COMPLETE>" in r,
    max_iterations=10
)
result = ralph.run()
```

**How it works:**
1. Sends task + history to Qwen
2. Gets response, saves to history
3. Checks for `<TASK_COMPLETE>` tag or custom checker
4. If complete → returns success
5. If not complete → adds "Continue working" prompt, increments iteration
6. If max iterations → creates alert in Needs_Action/

### Weekly Audit - CEO Briefing Generator

Runs every Sunday at 21:00, generates Monday Morning CEO Briefing.

```bash
# Run manual audit
python weekly_audit.py

# Run as scheduler (Sundays at 21:00)
python weekly_audit.py --schedule
```

**Audit Flow (7 Steps):**

| Step | Data Source | Output |
|------|-------------|--------|
| 1 | Odoo ERP | Revenue, expenses, profit, overdue invoices |
| 2 | /Done/ folder | Task completion stats, bottlenecks |
| 3 | Meta + Twitter | Social media performance summary |
| 4 | Accounting summaries | Subscription audit (18 patterns detected) |
| 5 | Qwen via Ralph Loop | CEO briefing generation |
| 6 | File system | Saves to Briefings/YYYY-MM-DD_CEO_briefing.md |
| 7 | Dashboard.md | Updates with latest figures |

**Briefing Sections:**
- Executive Summary
- Revenue vs Target
- Top 3 Wins This Week
- Bottlenecks (with root cause)
- Cost Optimization Suggestions
- Next Week Priorities

### Gold Tier Test Suite

```bash
python test_gold.py

# Tests (7 total):
# 1. Odoo Connection - authenticate() returns UID
# 2. Odoo Data Fetch - get_monthly_revenue() returns data
# 3. Facebook API - Graph API returns page info
# 4. Instagram API - Graph API returns account info
# 5. Twitter API - verify_credentials() succeeds
# 6. Ralph Loop - Completes counting task in ≤3 iterations
# 7. Full Audit - CEO briefing file created with content

# Success: 7/7 tests passed
# Output: "✅ Gold Tier Complete — Ready for Submission!"
```

### Start All Gold Tier Services

```bash
# Run weekly audit scheduler
python weekly_audit.py --schedule

# Or run individual components as needed
python odoo_mcp.py          # Test Odoo connection
python meta_poster.py       # Test Meta posting
python twitter_poster.py    # Test Twitter posting
python ralph_loop.py        # Test autonomous loop
```

---

## 🚀 Complete Installation Guide

### Prerequisites

- Python 3.8+
- pip package manager
- API keys (see below)

### Step 1: Clone/Download Repository

```bash
# Navigate to your project directory
cd C:\Users\YourName\AI_Employee_Vault
```

### Step 2: Install All Dependencies

```bash
# Bronze Tier
pip install watchdog colorama openai python-dotenv

# Silver Tier
pip install playwright google-auth google-auth-oauthlib google-api-python-client requests schedule

# Gold Tier
pip install tweepy

# Install Playwright browsers
playwright install chromium
```

### Step 3: Create .env File

Create `.env` in the `AI_Employee_Vault` folder:

```bash
# ===========================================
# API KEYS - Configure based on your tier
# ===========================================

# OpenRouter (required for AI analysis)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# --- BRONZE TIER (optional) ---
# No additional keys needed

# --- SILVER TIER ---
# WhatsApp: No keys needed (uses browser session)

# Gmail
# LINKEDIN_ACCESS_TOKEN=your_linkedin_token
# LINKEDIN_AUTHOR_URN=urn:li:person:YOUR_ID

# --- GOLD TIER ---
# Odoo ERP
ODOO_URL=http://localhost:8069
ODOO_DB=your_db_name
ODOO_USER=admin
ODOO_PASSWORD=your_password

# Meta (Facebook/Instagram)
FB_PAGE_ID=your_page_id
FB_PAGE_ACCESS_TOKEN=your_token
IG_USER_ID=your_ig_user_id
IG_ACCESS_TOKEN=your_token

# Twitter/X
TWITTER_API_KEY=your_key
TWITTER_API_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_SECRET=your_token_secret

# Global Settings
DRY_RUN=false
```

### Step 4: Verify Installation

```bash
# Run appropriate test suite
python test_bronze.py    # For Bronze Tier
python test_gold.py      # For Gold Tier (includes all tiers)
```

---

## 📊 API Key Setup Details

### OpenRouter (Required for all tiers)

1. Go to https://openrouter.ai/keys
2. Create account / sign in
3. Create new API key
4. Copy key to `.env` as `OPENROUTER_API_KEY`

**Alternative:** Qwen (DashScope)
1. Go to https://dashscope.console.aliyun.com/
2. Create API key
3. Use `QWEN_API_KEY` in `.env`

### Google OAuth (Gmail Watcher - Silver)

1. Go to https://console.cloud.google.com/
2. Create new project
3. Enable **Gmail API**
4. Create **OAuth 2.0 Client ID** (Desktop application)
5. Download JSON → Save as `AI_Employee_Project/gmail_credentials.json`
6. First run of `gmail_watcher.py` will create token automatically

### LinkedIn (Silver)

1. Go to https://www.linkedin.com/developers/apps
2. Create new app
3. Request permissions: **w_member_social**, **profile**, **openid**
4. Generate access token
5. Get author URN: `python linkedin_poster.py --whoami`

### Odoo (Gold)

**Option A: Docker (Recommended)**
```bash
docker run -p 8069:8069 odoo:17
# Access: http://localhost:8069
# Create database, admin user
```

**Option B: Local Installation**
1. Download from https://www.odoo.com/documentation
2. Install and configure
3. Note URL, database, credentials

### Meta/Facebook (Gold)

1. Go to https://developers.facebook.com/
2. Create app → Business type
3. Add products: **Facebook Login**, **Instagram Graph API**
4. Get Page Access Token from Graph API Explorer
5. Convert to Long-Lived Token (60 days validity)

### Twitter/X (Gold)

1. Go to https://developer.twitter.com/
2. Create Project + App
3. Apply for **Elevated** access (free, required for posting)
4. Generate all 4 keys from App Settings → Keys and Tokens

---

## 🔄 Complete Workflow Examples

### Example 1: Process a PDF Report (Bronze)

```bash
# 1. Drop file in Inbox
cp quarterly_report.pdf Inbox/

# 2. file_watcher.py detects and creates task
# → Needs_Action/20260223_120000_quarterly_report.pdf.md

# 3. orchestrator.py analyzes with AI
# → Creates plan in Plans/
# → If HIGH RISK → Copies to Pending_Approval/

# 4. Review and approve
python approve.py
# → Select item → Approve

# 5. Task completed → Moved to Done/
```

### Example 2: WhatsApp Invoice Alert (Silver)

```bash
# 1. Start WhatsApp watcher
python whatsapp_watcher.py

# 2. Receive WhatsApp: "urgent - invoice attached"
# → Watcher detects keyword "urgent" + "invoice"
# → Creates task: Needs_Action/WHATSAPP_Contact_20260223_013031.md

# 3. orchestrator.py processes task
# → Creates action plan
# → Moves to Done/ when complete
```

### Example 3: LinkedIn Post Generation (Silver)

```bash
# 1. Generate post draft
python linkedin_poster.py --generate "AI productivity tips"
# → Creates: Pending_Approval/LINKEDIN_facebook_20260223_120000.md

# 2. Review and approve
# → Move file from Pending_Approval/ to Approved/

# 3. Post (automatic via scheduler or manual)
python linkedin_poster.py --post
# → Posts to LinkedIn → Moves to Done/
```

### Example 4: Weekly CEO Briefing (Gold)

```bash
# 1. Automatic: Every Sunday at 21:00
# OR manual:
python weekly_audit.py

# 2. Audit collects:
# - Financial data from Odoo
# - Task completion stats from /Done/
# - Social media performance
# - Subscription audit

# 3. Qwen generates briefing via Ralph Loop
# → Briefings/2026-02-23_CEO_briefing.md

# 4. Dashboard.md updated with latest figures
```

### Example 5: Autonomous Task Processing (Gold)

```python
from ralph_loop import RalphLoop, all_files_processed

# Process all pending tasks autonomously
ralph = RalphLoop(
    task_description="Process all files in Needs_Action - read, plan, execute, move to Done",
    completion_check_fn=all_files_processed(),
    max_iterations=10
)
result = ralph.run()

# Ralph will keep working until all files are processed
# or max iterations reached
```

---

## 🛠️ Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **API key not found** | Check `.env` file exists in AI_Employee_Vault folder |
| **File watcher crashes** | Ensure file has read permissions; check Logs/ for errors |
| **Tasks not processing** | Verify orchestrator.py is running; check API key has credits |
| **WhatsApp session expired** | Delete `whatsapp_session/` and re-scan QR code |
| **Gmail token expired** | Delete `gmail_token.json` and re-authenticate |
| **LinkedIn 403 error** | Run `python linkedin_poster.py --whoami` and update URN in .env |
| **Odoo connection failed** | Verify Odoo server is running at ODOO_URL |
| **Twitter auth failed** | Ensure all 4 Twitter credentials are set; check Elevated access |
| **Ralph Loop not completing** | Increase max_iterations; check if task is too vague |
| **Weekly audit fails** | Check all Gold Tier dependencies are installed |

### Debug Mode

Enable verbose logging by checking `Logs/` folder:

```bash
# View today's log
type Logs\2026-02-23.json

# Or on Linux/Mac
cat Logs/2026-02-23.json
```

### Test Diagnostics

```bash
# Run test suite for your tier
python test_bronze.py    # Bronze
python test_gold.py      # Gold (includes all tiers)

# Results saved to Logs/test_results.md
```

---

## 📊 Quick Reference

### Start All Services (Gold Tier)

```bash
# Terminal 1: File Watcher (Bronze)
python file_watcher.py

# Terminal 2: Orchestrator (Bronze)
python orchestrator.py

# Terminal 3: WhatsApp Watcher (Silver)
python whatsapp_watcher.py

# Terminal 4: Gmail Watcher (Silver)
python gmail_watcher.py

# Terminal 5: LinkedIn Poster (Silver)
python linkedin_poster.py

# Terminal 6: Weekly Audit Scheduler (Gold)
python weekly_audit.py --schedule

# When needed: Approval Manager
python approve.py
```

### Stop Services

- Press `Ctrl+C` in each terminal

### Check Status

```bash
# View pending approvals
python approve.py list

# View dashboard
type Dashboard.md

# View test results
type Logs\test_results.md
```

---

## 📝 File Format Reference

### Task File (Needs_Action/)

```markdown
---
type: file_drop/whatsapp/email
from: sender_name
received: 2026-02-23T12:00:00
priority: urgent/high/medium
status: pending
---
## Content
<message or file details>

## Suggested Actions
- [ ] Action 1
- [ ] Action 2
```

### Plan File (Plans/)

```markdown
---
created: 2026-02-23T12:05:30
risk_level: LOW/MEDIUM/HIGH
status: pending
---
## Objective
<task objective>

## Steps
- [ ] Step 1
- [ ] Step 2

## Risk Assessment
Risk Level: HIGH - <reason>

## Requires Approval: YES
```

### CEO Briefing (Briefings/)

```markdown
---
generated: 2026-02-23T21:30:00
period: 2026-02-16 to 2026-02-23
revenue: 50000
expenses: 35000
profit: 15000
---

# Monday Morning CEO Briefing

## Executive Summary
<summary>

## Revenue vs Target
<analysis>

## Top 3 Wins This Week
1. <win>
2. <win>
3. <win>

## Bottlenecks
<issues with root cause>

## Cost Optimization
<suggestions>

## Next Week Priorities
1. <priority>
2. <priority>
3. <priority>
```

---

## 🎯 Best Practices

1. **Run file_watcher.py continuously** when system is active
2. **Check approve.py daily** for pending high-risk tasks
3. **Review Briefings/ weekly** for CEO insights
4. **Monitor Logs/ folder** for audit trail
5. **Run test suites** after any configuration changes
6. **Keep sessions secure** - don't share gmail_token.json or whatsapp_session/
7. **Use DRY_RUN=true** when testing social media posting
8. **Back up .env file** securely (contains API keys)

---

## 📞 Support

**Diagnostic Steps:**
1. Check logs in `Logs/` folder
2. Run `python test_bronze.py` or `python test_gold.py`
3. Verify API keys are valid and have credits
4. Ensure all services are running

**Common Commands:**
```bash
# List pending approvals
python approve.py list

# Test connectivity
python test_gold.py

# View dashboard
type Dashboard.md
```

---

**Version:** 2.0.0 (Gold Tier)
**Last Updated:** 2026-02-24
**Tiers:** Bronze ✅ | Silver ✅ | Gold ✅
