# AI Employee Vault - Complete Guide

## 📋 Overview

AI Employee Vault is an automated system that:
1. **Monitors files** dropped in the Inbox folder
2. **Watches WhatsApp & Gmail** for unread messages/emails with keywords and creates tasks in Needs_Action
3. **Analyzes tasks** using AI (OpenRouter/Qwen)
4. **Creates action plans** with step-by-step instructions
5. **Manages approvals** for high-risk tasks
6. **Posts to LinkedIn** from approved draft files (generate with AI, move to Approved/, auto-publish)

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI EMPLOYEE VAULT                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📥 Inbox          →  Drop new files here                       │
│       ↓                                                         │
│  👁️ file_watcher   →  Detects new files                        │
│       ↓                                                         │
│  ⚡ Needs_Action   →  Task files created here                   │
│       ↓                                                         │
│  🤖 orchestrator   →  Sends tasks to AI for analysis            │
│       ↓                                                         │
│  📋 Plans          →  AI-generated action plans                 │
│       ↓                                                         │
│  ⚠️ Pending_Approval → High-risk tasks flagged here             │
│       ↓                                                         │
│  ✅ approve.py     →  Manual approval interface                 │
│       ↓                                                         │
│  📁 Done           →  Completed tasks                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Directory Structure

```
AI_Employee_Vault/
├── Inbox/              # Drop new files here
├── Needs_Action/       # Pending tasks (from file, WhatsApp, Gmail watchers)
├── Plans/              # AI-generated plans (in AI_Employee_Project/Plans/)
├── Pending_Approval/   # High-risk tasks + LinkedIn draft posts
├── Approved/           # LinkedIn posts ready to publish
├── Done/               # Completed tasks + posted LinkedIn files
├── Logs/               # JSON logs (daily files)
├── file_watcher.py     # File monitoring service
├── whatsapp_watcher.py # WhatsApp Web watcher (keywords → tasks)
├── gmail_watcher.py    # Gmail watcher (unread important → tasks)
├── linkedin_poster.py  # LinkedIn post generator + publisher
├── orchestrator.py     # AI orchestration service
├── approve.py          # Approval manager
├── test_bronze.py      # Test suite
├── Dashboard.md        # Project dashboard
└── Company_Handbook.md # Company guidelines

AI_Employee_Project/
├── Plans/              # Action plans stored here
├── whatsapp_session/   # WhatsApp Web browser session (QR once)
├── whatsapp_processed.json
├── gmail_credentials.json  # Google OAuth client (you create)
├── gmail_token.json        # Gmail OAuth token (auto-created)
├── processed_emails.json
└── file_watcher.py     # Alternative location
```

---

## 🚀 Installation

### Step 1: Install Dependencies

```bash
pip install watchdog colorama openai python-dotenv
```

### Step 2: Set Up API Key

Create a `.env` file in the AI_Employee_Vault folder:

```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

**Where to get API keys:**
- OpenRouter: https://openrouter.ai/keys
- Qwen (DashScope): https://dashscope.console.aliyun.com/

---

## 📖 Components Detail

### 1️⃣ file_watcher.py

**Purpose:** Monitors the Inbox folder and creates task files when new files are detected.

**How to start:**
```bash
python file_watcher.py
```

**Output:**
```
============================================================
           AI EMPLOYEE FILE WATCHER SERVICE
============================================================
Monitoring: C:\Users\...\AI_Employee_Vault\Inbox
Tasks Dir:  C:\Users\...\AI_Employee_Vault\Needs_Action
Logs Dir:   C:\Users\...\AI_Employee_Vault\Logs
============================================================
Status: Starting...
============================================================

[SETUP] Checking directories...
[SETUP] Directories ready.
[SETUP] PID file: C:\...\Temp\file_watcher.pid
[START] Watching for new files...
[START] Press Ctrl+C to stop.
```

**When a new file is dropped:**
```
============================================================
[DETECTED] New file: report.pdf
[CREATED] Task file: 20260223_120000_report.pdf.md
============================================================
```

**Features:**
- ✅ Real-time file monitoring
- ✅ Automatic task file creation
- ✅ JSON logging
- ✅ Graceful Ctrl+C shutdown
- ✅ Colored terminal output
- ✅ Never crashes (full error handling)

---

### 2️⃣ orchestrator.py

**Purpose:** Picks up tasks from Needs_Action, sends them to AI for analysis, and creates action plans.

**How to start:**
```bash
python orchestrator.py
```

**Output:**
```
============================================================
║           AI Employee Orchestrator Service               ║
============================================================
  Needs_Action: C:\Users\...\AI_Employee_Vault\Needs_Action
  Plans Dir:    C:\Users\...\AI_Employee_Project\Plans
  OpenRouter:   anthropic/claude-3.5-sonnet
  Poll Interval: 30s
============================================================

[API] OpenRouter client initialized successfully.
[START] Orchestrator running. Polling every 30s...
```

**When a task is processed:**
```
============================================================
[PROCESSING] Task: 20260223_120000_report.pdf.md
[CREATED] Plan: PLAN_report_pdf_20260223_120530.md
[HIGH RISK] Copied to Pending_Approval
[COMPLETE] Moved to Done: 20260223_120530_task.md
[RISK] Level: HIGH - Requires human approval
============================================================
```

**Features:**
- ✅ AI task analysis (OpenRouter/Qwen)
- ✅ Risk assessment (LOW/MEDIUM/HIGH)
- ✅ Automatic plan generation
- ✅ High-risk task flagging
- ✅ 3x retry on API failure
- ✅ 30-second polling interval

---

### 3️⃣ approve.py

**Purpose:** Manually review and approve/reject high-risk tasks.

**How to start:**
```bash
python approve.py
```

**Interactive Menu:**
```
============================================================
         PENDING APPROVAL MANAGER
============================================================

Found 2 pending item(s):

  [1] 20260223_120000_report.pdf.md
  [2] PLAN_report_pdf_20260223_120530.md

  [a] Approve all
  [r] Reject all
  [q] Quit

Select action [1-2, a, r, q]:
```

**Commands:**
| Command | Action |
|---------|--------|
| `1, 2, 3...` | Select specific item |
| `a` | Approve all pending items |
| `r` | Reject all pending items |
| `q` | Exit |

**When selecting an individual item:**
```
File: PLAN_report_pdf_20260223_120530.md
------------------------------------------------------------
## Objective
Review the financial report...

## Steps
- [ ] Open and read report
- [ ] Verify numbers
- [ ] Create summary

## Risk Assessment
Risk Level: HIGH (involves financial data)

## Requires Approval: YES
------------------------------------------------------------

Approve/Reject/Skip [a/r/s]:
```

**Command Line Mode:**
```bash
# List pending approvals
python approve.py list

# Approve specific file
python approve.py approve filename.md
```

---

### 4️⃣ test_bronze.py

**Purpose:** Test the system to ensure everything is working properly.

**How to run:**
```bash
python test_bronze.py
```

**Tests:**
| Test | Description |
|------|-------------|
| 1. Folder Structure | Checks all directories exist |
| 2. Required Files | Checks Dashboard.md, Company_Handbook.md |
| 3. Dependencies | Checks watchdog, colorama, openai, dotenv |
| 4. API Connectivity | Tests OpenRouter/Qwen API connection |
| 5. End-to-End | Tests file drop → task creation flow |

**Success Output:**
```
============================================================
Bronze Tier: 5/5 tests passed
============================================================

[SUCCESS] Bronze Tier Complete - Ready for Submission!
```

---

## 📱 Watchers & LinkedIn Poster (WhatsApp, Gmail, LinkedIn)

These services monitor external channels (WhatsApp, Gmail) and create task files in **Needs_Action**, and post approved content to LinkedIn. They run independently and can be used together with the file watcher and orchestrator.

---

### 5️⃣ WhatsApp Watcher (`whatsapp_watcher.py`)

**Purpose:** Monitors WhatsApp Web for **unread** chats whose **last message** contains certain keywords, then creates a task file in `Needs_Action/` for each match so you (or the orchestrator) can act on them.

#### How it works

1. **Browser:** Launches Chromium (Playwright) and opens WhatsApp Web. Uses a **persistent session** so you only scan the QR code once; after that it reuses `AI_Employee_Project/whatsapp_session/`.
2. **Polling:** Every **30 seconds** it:
   - Finds the chat list (left panel) and detects chats with an unread indicator (badge, aria-label, or numeric span).
   - For each unread chat: opens the chat, reads the **last (incoming) message** from the conversation, and checks if it contains any configured **keywords**.
   - If keywords match: creates a markdown task file in `Needs_Action/` (e.g. `WHATSAPP_Muzammil_20260223_013031.md`), logs the event, and marks that message as processed so it is not created again.
3. **No keyword match:** Chats whose last message does not contain any keyword are skipped (no task file). You’ll see something like `[SKIP] No keywords matched (read: '…')` so you know what text was read.
4. **Processed tracking:** Processed message IDs are stored in `AI_Employee_Project/whatsapp_processed.json` so the same message never creates duplicate tasks.

#### Keywords (configurable in code)

- **High priority:** `invoice`, `payment`, `urgent`, `asap`
- **Normal:** `price`, `quote`, `help`, `project`

All matching is case-insensitive.

#### Prerequisites

```bash
pip install playwright colorama python-dotenv
playwright install chromium
```

#### Configuration

| Item | Location | Description |
|------|----------|-------------|
| Session (cookies/profile) | `AI_Employee_Project/whatsapp_session/` | Created on first run; keep it so you don’t re-scan QR. |
| Processed messages | `AI_Employee_Project/whatsapp_processed.json` | Auto-created; do not edit unless you want to “re-process” a message. |
| Task output | `Needs_Action/` | `WHATSAPP_<name>_<timestamp>.md` |
| Logs | `Logs/YYYY-MM-DD.json` | Events like `whatsapp_message`, `whatsapp_error`. |

**Environment (optional):**

- `WHATSAPP_HEADLESS=true` — run browser in background (default: `false`, window visible).

#### How to run

```bash
# Start watcher (stays running, polls every 30s)
python whatsapp_watcher.py
```

**First run:** A browser window opens; scan the QR code with WhatsApp (Linked Devices). After that, the session is saved and later runs reuse it.

**Output example:**

```
============================================================
           WHATSAPP WATCHER SERVICE
============================================================
[READY] WhatsApp Web loaded.
[START] WhatsApp Watcher running. Polling every 30s...
[FOUND] 2 unread chat(s)
[CHECKING] Chat: Muzammil
[MATCH] Keywords: urgent
[CREATED] Task: WHATSAPP_Muzammil_20260223_013031.md
```

#### Task file format (WhatsApp)

```markdown
---
type: whatsapp
from: Muzammil
message_preview: urgent
received: 2026-02-23T01:30:31
priority: urgent
status: pending
keyword_matched: urgent
---
## Message Content
<full message text>
## Suggested Actions
- [ ] Draft reply
- [ ] Check if invoice/payment needed
```

#### Troubleshooting (WhatsApp)

- **“No unread chats found”** — Unread detection uses several methods (badge, aria-label, numeric badge). If your WhatsApp Web layout changed, the script may need selector updates.
- **“Chat not found”** — The script only searches inside the left-panel chat list. If the list isn’t loaded or scrolled, it can miss the chat; ensure WhatsApp Web is fully loaded.
- **“No message found” / “No keywords matched”** — The last message in the open chat is read with multiple selectors (e.g. `data-lexical-text`, copyable text). If the log shows `(read: '')` or wrong text, the DOM may have changed.
- **Session expired** — Delete `whatsapp_session/` and run again; you’ll be asked to scan the QR code again.

---

### 6️⃣ Gmail Watcher (`gmail_watcher.py`)

**Purpose:** Polls Gmail for **unread + important** emails and creates one task file per email in `Needs_Action/`. Each email is processed only once (tracked by message ID).

#### How it works

1. **Auth:** Uses Google OAuth 2.0 with **read-only** Gmail scope. On first run (or when token is missing/expired) a browser opens for you to sign in; the token is saved in `AI_Employee_Project/gmail_token.json`.
2. **Polling:** Every **120 seconds** it:
   - Calls Gmail API: `is:unread is:important`, up to 50 messages.
   - Skips any message ID already in `processed_emails`.
   - For each new email: fetches metadata (From, To, Subject, Date) and snippet, determines **priority** (urgent / high / medium) from subject and sender, then creates `EMAIL_<id>_<timestamp>.md` in `Needs_Action/` and marks the ID as processed.
3. **Priority rules:** “Urgent” if subject contains words like `invoice`, `payment`, `urgent`, `asap`, `immediate`, `deadline`; “high” if From matches known contacts (e.g. boss@, manager@, hr@); otherwise “medium”.
4. **Rate limits:** On 429, the script waits 5 minutes then retries. On 401 (token expired), it prompts for re-auth on next run.

#### Prerequisites

```bash
pip install google-auth google-auth-oauthlib google-api-python-client colorama python-dotenv
```

#### Configuration

| Item | Location | Description |
|------|----------|-------------|
| OAuth credentials | `AI_Employee_Project/gmail_credentials.json` | From Google Cloud Console (OAuth 2.0 Client ID, desktop app). |
| Token | `AI_Employee_Project/gmail_token.json` | Auto-created after first sign-in; do not share. |
| Processed emails | `AI_Employee_Project/processed_emails.json` | List of processed message IDs. |
| Task output | `Needs_Action/` | `EMAIL_<id>_<timestamp>.md` |
| Logs | `Logs/YYYY-MM-DD.json` | Events like `gmail_message`, `gmail_error`. |

**Gmail API setup (one-time):**

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create/select project → enable **Gmail API**.
2. Create **OAuth 2.0 Client ID** (Desktop application), download JSON, and save it as `AI_Employee_Project/gmail_credentials.json` (path is in code).
3. Run `python gmail_watcher.py`; browser opens for sign-in; after approval, `gmail_token.json` is created.

#### How to run

```bash
# Start watcher (stays running, polls every 120s)
python gmail_watcher.py
```

**Output example:**

```
[AUTH] Gmail API connected.
[START] Gmail Watcher running. Polling every 120s...
[FOUND] 3 new email(s)
[CREATED] Task: EMAIL_abc123_20260223_120530.md
```

#### Task file format (Gmail)

```markdown
---
type: email
from: sender@example.com
subject: Invoice due
received: 2026-02-23T12:05:30
priority: urgent
status: pending
---
## Email Content
<snippet>
## Suggested Actions
- [ ] Reply to sender
- [ ] Forward if needed
```

#### Troubleshooting (Gmail)

- **“Credentials file not found”** — Ensure `gmail_credentials.json` is in `AI_Employee_Project/` (see `Config.CREDENTIALS_FILE` in script).
- **“Token expired”** — Delete `gmail_token.json` and run again; you’ll get a new browser sign-in.
- **429 rate limit** — Script waits and retries; reduce polling frequency in code if needed.

---

### 7️⃣ LinkedIn Poster (`linkedin_poster.py`)

**Purpose:** (1) **Generate** LinkedIn post drafts from a topic using AI and save them to `Pending_Approval/`. (2) **Post** approved content: any `LINKEDIN_*.md` file you move to `Approved/` is published to your LinkedIn profile via the LinkedIn API, then moved to `Done/`.

#### How it works

1. **Generate (`--generate "topic"`):** Calls OpenRouter (or Qwen) with a LinkedIn-style system prompt, gets one post, and saves a markdown file in `Pending_Approval/` with frontmatter (topic, status) and a “Post Content” section. No LinkedIn token needed for this step.
2. **Approve:** You move the file from `Pending_Approval/` to `Approved/` when you’re happy with it (manual step).
3. **Post (`--post` or scheduler):** For each `LINKEDIN_*.md` in `Approved/`:
   - Parses frontmatter and “## Post Content”; strips markdown to plain text.
   - Resolves **author URN**: uses `LINKEDIN_AUTHOR_URN` from `.env`, or (if empty) fetches the current user from LinkedIn’s OpenID **userinfo** endpoint (`/v2/userinfo`) so the post is published as the token’s account.
   - Calls LinkedIn **UGC Posts API** (`POST /v2/ugcPosts`) with that author and the cleaned text.
   - On success: moves the file to `Done/` with a timestamped name (e.g. `20260223_031121_POSTED_...`).
4. **Scheduler (default):** If you run with no arguments (or `--schedule`), it loops forever and runs the “post approved content” logic every **600 seconds** (10 minutes).

#### Prerequisites

```bash
pip install requests colorama python-dotenv openai
```

- **LinkedIn:** Create an app at [LinkedIn Developers](https://www.linkedin.com/developers/apps). Request **w_member_social** (post on behalf of user). For `--whoami` and auto-author: **profile** and **openid**.
- **AI (optional):** OpenRouter or Qwen API key for post generation.

#### Configuration

| Item | Location | Description |
|------|----------|-------------|
| `.env` | `AI_Employee_Vault/.env` | `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_AUTHOR_URN`; optional `OPENROUTER_API_KEY` / `QWEN_API_KEY` for generation. |
| Pending drafts | `Pending_Approval/` | Generated posts; move to `Approved/` when ready. |
| Ready to post | `Approved/` | Script posts everything matching `LINKEDIN_*.md` here. |
| Posted | `Done/` | Files moved here after successful post. |
| Logs | `Logs/YYYY-MM-DD.json` | Events like `linkedin_post_success`, `linkedin_api_error`. |

**Environment variables:**

```bash
# Required for posting
LINKEDIN_ACCESS_TOKEN=<your OAuth 2.0 access token>
LINKEDIN_AUTHOR_URN=urn:li:person:YOUR_ID   # optional if token has profile+openid (then run --whoami to get ID)

# Optional: AI post generation
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
# or
QWEN_API_KEY=...
```

**Getting the author URN:** After you have a token with **profile** and **openid** scopes, run:

```bash
python linkedin_poster.py --whoami
```

It calls `/v2/userinfo` and prints the correct `LINKEDIN_AUTHOR_URN=urn:li:person:XXXX` (or `urn:li:member:XXXX`) to put in `.env`. The author **must** match the account that created the token.

#### How to run

```bash
# Generate a draft (uses AI if OPENROUTER_API_KEY or QWEN_API_KEY set)
python linkedin_poster.py --generate "AI in healthcare"

# List pending and approved posts
python linkedin_poster.py --list

# Post all approved posts now (no scheduler)
python linkedin_poster.py --post

# Test without posting
python linkedin_poster.py --post --dry-run

# Get your author URN for .env (token must have profile + openid)
python linkedin_poster.py --whoami

# Verify token and author (optional)
python linkedin_poster.py --test-linkedin

# Run scheduler: every 10 min post from Approved/ (default)
python linkedin_poster.py
# or
python linkedin_poster.py --schedule
```

**Output example (post):**

```
[POSTER] Checking for approved LinkedIn posts...
[FOUND] 1 approved post(s)
[LINKEDIN] Post ID: urn:li:share:7431460613773524992
[MOVED] To Done: 20260223_031121_POSTED_LINKEDIN_ai_automation_....md
[POSTED] Successfully published: LINKEDIN_ai_automation_....md
```

#### Post file format (LinkedIn)

- **Pending_Approval / Approved:** Markdown with YAML frontmatter and a `## Post Content` section. The script strips markdown and sends the content as plain text to LinkedIn.
- **Done:** Same content, filename prefixed with timestamp and `_POSTED_`.

#### Troubleshooting (LinkedIn)

- **403 on `/author`** — The token’s user and `LINKEDIN_AUTHOR_URN` must match. Run `--whoami` with the same token and set the printed URN in `.env`. Use **person** URN from userinfo (e.g. `urn:li:person:7FQ01B2oRZ`).
- **“Not enough permissions”** — App needs **w_member_social**. Re-create the token with that scope and update `LINKEDIN_ACCESS_TOKEN`.
- **Generation fails** — Set `OPENROUTER_API_KEY` or `QWEN_API_KEY` (and optionally model) in `.env`.

---

## 🔄 Complete Workflow

### Step-by-Step Process

```
1. USER drops file in Inbox/
   └── Example: "quarterly_report.pdf"
   
2. file_watcher.py detects the file
   └── Creates: Needs_Action/20260223_120000_quarterly_report.pdf.md
   
3. orchestrator.py picks up task (within 30 seconds)
   └── Sends to AI for analysis
   
4. AI analyzes and returns:
   - Action plan with steps
   - Risk level (LOW/MEDIUM/HIGH)
   - Approval requirement
   
5. System creates:
   - Plans/PLAN_quarterly_report_20260223_120530.md
   - If HIGH RISK → Copies to Pending_Approval/
   
6. User runs: python approve.py
   └── Reviews and approves/rejects
   
7. Approved files → Done/
   Rejected files → Needs_Action/ (for reprocessing)
```

---

## 📝 File Formats

### Task File (Needs_Action/)
```markdown
---
type: file_drop
original_name: quarterly_report.pdf
received: 2026-02-23T12:00:00
priority: medium
status: pending
---
## File Details

## Suggested Actions
- [ ] Review file
- [ ] Process and respond
## Notes
```

### Plan File (Plans/)
```markdown
---
created: 2026-02-23T12:05:30
risk_level: HIGH
status: pending
---
## Objective
Review quarterly financial report and create summary.

## Steps
- [ ] Open and read full report
- [ ] Verify all financial figures
- [ ] Create executive summary
- [ ] Flag any anomalies

## Risk Assessment
Risk Level: HIGH - Contains sensitive financial data

## Requires Approval: YES
```

### Log File (Logs/YYYY-MM-DD.json)
```json
[
  {
    "type": "file_detected",
    "timestamp": "2026-02-23T12:00:00",
    "data": {
      "original_file": "C:\\...\\Inbox\\report.pdf",
      "task_file": "C:\\...\\Needs_Action\\task.md"
    }
  },
  {
    "type": "task_processed",
    "timestamp": "2026-02-23T12:05:30",
    "data": {
      "risk_level": "HIGH",
      "requires_approval": true
    }
  }
]
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# OpenRouter API (orchestrator, LinkedIn generation)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxx
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Alternative: Qwen API
# QWEN_API_KEY=your-qwen-key
# QWEN_MODEL=qwen-plus

# WhatsApp Watcher (optional)
# WHATSAPP_HEADLESS=true

# LinkedIn Poster (required for posting)
# LINKEDIN_ACCESS_TOKEN=your-oauth-token
# LINKEDIN_AUTHOR_URN=urn:li:person:YOUR_ID   # get via: python linkedin_poster.py --whoami
# DRY_RUN=true   # test without posting
```

### Available Models (OpenRouter)

| Model | Use Case |
|-------|----------|
| `anthropic/claude-3.5-sonnet` | Best overall |
| `openai/gpt-4o-mini` | Fast & cheap |
| `google/gemini-pro-1.5` | Long context |
| `meta-llama/llama-3-70b` | Open source |

---

## 🛠️ Troubleshooting

### Problem: file_watcher.py crashes
**Solution:** May be Unicode error. Use the latest version.

### Problem: API key not found
**Solution:** Check `.env` file exists in AI_Employee_Vault folder.

### Problem: Tasks not being processed
**Solution:** 
1. Ensure orchestrator.py is running
2. Start with `python orchestrator.py`

### Problem: Pending_Approval is empty
**Solution:** This is normal. Only HIGH RISK tasks appear here.

### Problem: Tests are failing
**Solution:**
```bash
# Reinstall dependencies
pip install --upgrade watchdog colorama openai python-dotenv

# Then test again
python test_bronze.py
```

---

## 📊 Quick Reference

### Start All Services
```bash
# Terminal 1: File Watcher
python file_watcher.py

# Terminal 2: Orchestrator
python orchestrator.py

# Optional - Terminal 3: WhatsApp Watcher (polls every 30s)
python whatsapp_watcher.py

# Optional - Terminal 4: Gmail Watcher (polls every 120s)
python gmail_watcher.py

# Optional - LinkedIn Poster (scheduler: posts from Approved/ every 10 min)
python linkedin_poster.py

# When needed: Approval Manager
python approve.py
```

### Stop Services
- Press `Ctrl+C` in both terminals

### Check Logs
```bash
# Today's log
type Logs\2026-02-23.json

# All logs folder
dir Logs\
```

### View Pending Approvals
```bash
python approve.py list
```

---

## 🎯 Best Practices

1. **Always run file_watcher.py** in background when the system is active
2. **Run orchestrator.py** separately for AI processing
3. **Check approve.py daily** for pending approvals
4. **Review Logs/** folder for audit trail
5. **Run test_bronze.py** after any changes

---

## 📞 Support

**Issues:**
1. Check logs in `Logs/` folder
2. Run `python test_bronze.py` for diagnostics
3. Ensure API key is valid and has credits

---

**Version:** 1.0.0  
**Last Updated:** 2026-02-23
