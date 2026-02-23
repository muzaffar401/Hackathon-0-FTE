#!/bin/bash
#
# start_all.sh - Start all AI Employee services
# Starts file_watcher, gmail_watcher, whatsapp_watcher in background
# Runs scheduler in foreground as main process
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_DIR="$HOME/AI_Employee_Vault"
PROJECT_DIR="$HOME/AI_Employee_Project"
PID_DIR="$PROJECT_DIR/pids"

# PID file locations
FILE_WATCHER_PID=""
GMAIL_WATCHER_PID=""
WHATSAPP_WATCHER_PID=""
SCHEDULER_PID=""

echo -e "${CYAN}============================================================${NC}"
echo -e "${YELLOW}           AI EMPLOYEE VAULT - STARTING ALL SERVICES${NC}"
echo -e "${CYAN}============================================================${NC}"

# Create PID directory
mkdir -p "$PID_DIR"

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}[ERROR] Python not found. Please install Python 3.8+${NC}"
    exit 1
fi

# Check if venv exists, if not create it
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo -e "${YELLOW}[SETUP] Creating virtual environment...${NC}"
    cd "$PROJECT_DIR"
    python -m venv venv
    echo -e "${GREEN}[DONE] Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${CYAN}[INFO] Activating virtual environment...${NC}"
source "$PROJECT_DIR/venv/bin/activate"

# Install dependencies if needed
echo -e "${CYAN}[INFO] Checking dependencies...${NC}"
pip install -q schedule openai colorama python-dotenv watchdog google-auth google-auth-oauthlib google-api-python-client playwright requests 2>/dev/null || true

# Ensure directories exist
mkdir -p "$VAULT_DIR/Inbox"
mkdir -p "$VAULT_DIR/Needs_Action"
mkdir -p "$VAULT_DIR/Done"
mkdir -p "$VAULT_DIR/Pending_Approval"
mkdir -p "$VAULT_DIR/Approved"
mkdir -p "$VAULT_DIR/Rejected"
mkdir -p "$VAULT_DIR/Logs"
mkdir -p "$VAULT_DIR/Briefings"

cd "$VAULT_DIR"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}[SHUTDOWN] Stopping all services...${NC}"
    
    if [ -n "$FILE_WATCHER_PID" ] && kill -0 "$FILE_WATCHER_PID" 2>/dev/null; then
        echo -e "${CYAN}[STOP] File Watcher (PID: $FILE_WATCHER_PID)${NC}"
        kill "$FILE_WATCHER_PID" 2>/dev/null || true
    fi
    
    if [ -n "$GMAIL_WATCHER_PID" ] && kill -0 "$GMAIL_WATCHER_PID" 2>/dev/null; then
        echo -e "${CYAN}[STOP] Gmail Watcher (PID: $GMAIL_WATCHER_PID)${NC}"
        kill "$GMAIL_WATCHER_PID" 2>/dev/null || true
    fi
    
    if [ -n "$WHATSAPP_WATCHER_PID" ] && kill -0 "$WHATSAPP_WATCHER_PID" 2>/dev/null; then
        echo -e "${CYAN}[STOP] WhatsApp Watcher (PID: $WHATSAPP_WATCHER_PID)${NC}"
        kill "$WHATSAPP_WATCHER_PID" 2>/dev/null || true
    fi
    
    if [ -n "$SCHEDULER_PID" ] && kill -0 "$SCHEDULER_PID" 2>/dev/null; then
        echo -e "${CYAN}[STOP] Scheduler (PID: $SCHEDULER_PID)${NC}"
        kill "$SCHEDULER_PID" 2>/dev/null || true
    fi
    
    # Save PIDs for stop_all.sh
    echo "" > "$PID_DIR/last_pids.txt"
    
    echo -e "${GREEN}[DONE] All services stopped${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start File Watcher
echo -e "\n${GREEN}[START] File Watcher...${NC}"
python file_watcher.py &
FILE_WATCHER_PID=$!
echo "$FILE_WATCHER_PID" > "$PID_DIR/file_watcher.pid"
echo -e "${CYAN}       PID: $FILE_WATCHER_PID${NC}"
sleep 2

# Start Gmail Watcher
echo -e "${GREEN}[START] Gmail Watcher...${NC}"
python gmail_watcher.py &
GMAIL_WATCHER_PID=$!
echo "$GMAIL_WATCHER_PID" > "$PID_DIR/gmail_watcher.pid"
echo -e "${CYAN}       PID: $GMAIL_WATCHER_PID${NC}"
sleep 2

# Start WhatsApp Watcher
echo -e "${GREEN}[START] WhatsApp Watcher...${NC}"
python whatsapp_watcher.py &
WHATSAPP_WATCHER_PID=$!
echo "$WHATSAPP_WATCHER_PID" > "$PID_DIR/whatsapp_watcher.pid"
echo -e "${CYAN}       PID: $WHATSAPP_WATCHER_PID${NC}"
sleep 2

# Start Scheduler (foreground - main process)
echo -e "${GREEN}[START] Scheduler (main process)...${NC}"
echo -e "${CYAN}============================================================${NC}"
echo -e "${YELLOW} All background services started successfully!${NC}"
echo -e "${CYAN}============================================================${NC}"
echo -e "${GREEN} Running Services:${NC}"
echo -e "   - File Watcher:     ${CYAN}$FILE_WATCHER_PID${NC}"
echo -e "   - Gmail Watcher:    ${CYAN}$GMAIL_WATCHER_PID${NC}"
echo -e "   - WhatsApp Watcher: ${CYAN}$WHATSAPP_WATCHER_PID${NC}"
echo -e "   - Scheduler:        ${CYAN}FOREGROUND${NC}"
echo -e "${CYAN}============================================================${NC}"
echo -e "${YELLOW} Press Ctrl+C to stop all services${NC}"
echo -e "${CYAN}============================================================${NC}"

# Save all PIDs
cat > "$PID_DIR/all_pids.txt" << EOF
FILE_WATCHER_PID=$FILE_WATCHER_PID
GMAIL_WATCHER_PID=$GMAIL_WATCHER_PID
WHATSAPP_WATCHER_PID=$WHATSAPP_WATCHER_PID
SCHEDULER_PID=$$
EOF

# Run scheduler in foreground
python scheduler.py
SCHEDULER_PID=$!

# Wait for scheduler
wait $SCHEDULER_PID
