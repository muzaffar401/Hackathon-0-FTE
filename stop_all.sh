#!/bin/bash
#
# stop_all.sh - Stop all AI Employee services
# Kills all running watcher and scheduler processes
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

echo -e "${CYAN}============================================================${NC}"
echo -e "${YELLOW}           AI EMPLOYEE VAULT - STOPPING ALL SERVICES${NC}"
echo -e "${CYAN}============================================================${NC}"

# Check if PID directory exists
if [ ! -d "$PID_DIR" ]; then
    echo -e "${YELLOW}[INFO] No PID directory found. Checking for running processes...${NC}"
    
    # Try to find and kill processes by name
    pkill -f "file_watcher.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] File Watcher${NC}" || echo -e "${YELLOW}[SKIP] File Watcher not running${NC}"
    pkill -f "gmail_watcher.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] Gmail Watcher${NC}" || echo -e "${YELLOW}[SKIP] Gmail Watcher not running${NC}"
    pkill -f "whatsapp_watcher.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] WhatsApp Watcher${NC}" || echo -e "${YELLOW}[SKIP] WhatsApp Watcher not running${NC}"
    pkill -f "scheduler.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] Scheduler${NC}" || echo -e "${YELLOW}[SKIP] Scheduler not running${NC}"
    pkill -f "approval_manager.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] Approval Manager${NC}" || echo -e "${YELLOW}[SKIP] Approval Manager not running${NC}"
    pkill -f "linkedin_poster.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] LinkedIn Poster${NC}" || echo -e "${YELLOW}[SKIP] LinkedIn Poster not running${NC}"
    
    echo -e "\n${GREEN}[DONE] All services stopped${NC}"
    exit 0
fi

# Read PIDs from files
STOPPED_COUNT=0

# Stop File Watcher
if [ -f "$PID_DIR/file_watcher.pid" ]; then
    PID=$(cat "$PID_DIR/file_watcher.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${CYAN}[STOP] File Watcher (PID: $PID)...${NC}"
        kill "$PID" 2>/dev/null && ((STOPPED_COUNT++)) || echo -e "${YELLOW}[WARN] Could not stop PID $PID${NC}"
    else
        echo -e "${YELLOW}[SKIP] File Watcher not running${NC}"
    fi
    rm -f "$PID_DIR/file_watcher.pid"
fi

# Stop Gmail Watcher
if [ -f "$PID_DIR/gmail_watcher.pid" ]; then
    PID=$(cat "$PID_DIR/gmail_watcher.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${CYAN}[STOP] Gmail Watcher (PID: $PID)...${NC}"
        kill "$PID" 2>/dev/null && ((STOPPED_COUNT++)) || echo -e "${YELLOW}[WARN] Could not stop PID $PID${NC}"
    else
        echo -e "${YELLOW}[SKIP] Gmail Watcher not running${NC}"
    fi
    rm -f "$PID_DIR/gmail_watcher.pid"
fi

# Stop WhatsApp Watcher
if [ -f "$PID_DIR/whatsapp_watcher.pid" ]; then
    PID=$(cat "$PID_DIR/whatsapp_watcher.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${CYAN}[STOP] WhatsApp Watcher (PID: $PID)...${NC}"
        kill "$PID" 2>/dev/null && ((STOPPED_COUNT++)) || echo -e "${YELLOW}[WARN] Could not stop PID $PID${NC}"
    else
        echo -e "${YELLOW}[SKIP] WhatsApp Watcher not running${NC}"
    fi
    rm -f "$PID_DIR/whatsapp_watcher.pid"
fi

# Stop Scheduler
if [ -f "$PID_DIR/scheduler.pid" ]; then
    PID=$(cat "$PID_DIR/scheduler.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${CYAN}[STOP] Scheduler (PID: $PID)...${NC}"
        kill "$PID" 2>/dev/null && ((STOPPED_COUNT++)) || echo -e "${YELLOW}[WARN] Could not stop PID $PID${NC}"
    else
        echo -e "${YELLOW}[SKIP] Scheduler not running${NC}"
    fi
    rm -f "$PID_DIR/scheduler.pid"
fi

# Also try to kill by process name (fallback)
echo -e "\n${CYAN}[INFO] Checking for any remaining processes...${NC}"
pkill -f "file_watcher.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] File Watcher (by name)${NC}"
pkill -f "gmail_watcher.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] Gmail Watcher (by name)${NC}"
pkill -f "whatsapp_watcher.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] WhatsApp Watcher (by name)${NC}"
pkill -f "scheduler.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] Scheduler (by name)${NC}"
pkill -f "approval_manager.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] Approval Manager (by name)${NC}"
pkill -f "linkedin_poster.py" 2>/dev/null && echo -e "${GREEN}[STOPPED] LinkedIn Poster (by name)${NC}"

# Clear all PIDs file
rm -f "$PID_DIR/all_pids.txt"
rm -f "$PID_DIR/last_pids.txt"

echo -e "\n${CYAN}============================================================${NC}"
echo -e "${GREEN}               ALL SERVICES STOPPED SUCCESSFULLY${NC}"
echo -e "${CYAN}============================================================${NC}"
echo -e "${YELLOW} To start services again, run: ./start_all.sh${NC}"
echo -e ""
