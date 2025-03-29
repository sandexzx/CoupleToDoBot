#!/bin/bash
# =====================================================
# Advanced Deployment Script for CoupleToDoBot Telegram Bot
# For Ubuntu 24.04 with Python 3.12
# Supports both fresh installation and updates
# =====================================================

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
UPDATE_MODE=false
CURRENT_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=""

# Log functions for better output
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --help          Show this help message"
    echo "  --update        Force update mode even for fresh installation"
    echo "  --fresh         Force fresh installation (will backup existing installation if any)"
    echo "  --rollback DIR  Rollback to a specific backup directory"
    echo
    echo "Examples:"
    echo "  $0                  # Auto-detect mode (fresh or update)"
    echo "  $0 --update         # Force update mode"
    echo "  $0 --fresh          # Force fresh installation"
    echo "  $0 --rollback /opt/backups/CoupleToDoBot_20240325_123456  # Rollback to backup"
    exit 0
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "Please run as root (use sudo)"
fi

# Process command line arguments
FORCE_UPDATE=false
FORCE_FRESH=false
ROLLBACK_DIR=""

while [ $# -gt 0 ]; do
    case "$1" in
        --help)
            show_help
            ;;
        --update)
            FORCE_UPDATE=true
            shift
            ;;
        --fresh)
            FORCE_FRESH=true
            shift
            ;;
        --rollback)
            if [ -z "$2" ]; then
                error "Rollback directory not specified"
            fi
            ROLLBACK_DIR="$2"
            shift 2
            ;;
        *)
            warn "Unknown option: $1"
            shift
            ;;
    esac
done

# =====================================================
# Configuration Variables
# =====================================================
PROJECT_NAME="CoupleToDoBot"
DEPLOY_DIR="/opt/${PROJECT_NAME}"
VENV_DIR="${DEPLOY_DIR}/venv"
SERVICE_NAME="coupletodobot"
GIT_REPO="https://github.com/sandexzx/CoupleToDoBot"
BACKUP_ROOT="/opt/coupleToDoBackups"
DB_FILE="couple_tasks.db"

# =====================================================
# Rollback mode
# =====================================================
if [ -n "$ROLLBACK_DIR" ]; then
    if [ ! -d "$ROLLBACK_DIR" ]; then
        error "Backup directory '$ROLLBACK_DIR' not found"
    fi
    
    log "Rolling back to backup: $ROLLBACK_DIR"
    
    # Stop the service if it's running
    if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
        log "Stopping the service..."
        systemctl stop "${SERVICE_NAME}.service"
    fi
    
    # Create a backup of the current state before rollback
    if [ -d "$DEPLOY_DIR" ]; then
        PRE_ROLLBACK_BACKUP="${BACKUP_ROOT}/${PROJECT_NAME}_pre_rollback_${CURRENT_DATE}"
        mkdir -p "$PRE_ROLLBACK_BACKUP"
        log "Creating backup of current state before rollback: $PRE_ROLLBACK_BACKUP"
        
        # Copy all files except the virtual environment
        cd "$DEPLOY_DIR"
        find . -maxdepth 1 -not -name "venv" -not -name "." | xargs -I{} cp -r {} "$PRE_ROLLBACK_BACKUP"
    fi
    
    # Restore from backup
    log "Restoring files from backup..."
    mkdir -p "$DEPLOY_DIR"
    
    # Copy all files from backup except database if it doesn't exist
    cd "$ROLLBACK_DIR"
    find . -maxdepth 1 -not -name "." -not -name "$DB_FILE" | xargs -I{} cp -r {} "$DEPLOY_DIR"
    
    # Only restore database if it doesn't exist in current deployment
    if [ ! -f "${DEPLOY_DIR}/${DB_FILE}" ] && [ -f "${ROLLBACK_DIR}/${DB_FILE}" ]; then
        log "Restoring database file..."
        cp "${ROLLBACK_DIR}/${DB_FILE}" "${DEPLOY_DIR}/${DB_FILE}"
    elif [ -f "${ROLLBACK_DIR}/${DB_FILE}" ]; then
        log "Database file already exists. To restore database, manually copy:"
        log "cp ${ROLLBACK_DIR}/${DB_FILE} ${DEPLOY_DIR}/${DB_FILE}"
    fi
    
    # Set permissions
    chown -R $(logname):$(logname) "$DEPLOY_DIR"
    
    # Restart service
    log "Restarting service..."
    systemctl restart "${SERVICE_NAME}.service"
    
    log "Rollback completed successfully!"
    log "Check service status: systemctl status ${SERVICE_NAME}"
    
    exit 0
fi

# =====================================================
# Detect installation type
# =====================================================
if [ -d "$DEPLOY_DIR" ]; then
    if $FORCE_FRESH; then
        log "Force fresh installation mode enabled. Existing installation will be backed up."
        UPDATE_MODE=false
    else
        log "Existing installation detected. Running in update mode."
        UPDATE_MODE=true
    fi
else
    if $FORCE_UPDATE; then
        log "Force update mode enabled, but no existing installation found."
        warn "Will proceed with fresh installation."
    fi
    log "No existing installation found. Running in fresh installation mode."
    UPDATE_MODE=false
fi

# =====================================================
# Check System and Install Dependencies
# =====================================================
log "Checking system and installing required packages..."

# Update package lists
apt update -qq || error "Failed to update package lists"

# Install required packages
apt install -y python3.12 python3.12-venv python3.12-dev git sqlite3 || error "Failed to install dependencies"

# =====================================================
# Backup existing installation
# =====================================================
if [ -d "$DEPLOY_DIR" ]; then
    mkdir -p "$BACKUP_ROOT"
    BACKUP_DIR="${BACKUP_ROOT}/${PROJECT_NAME}_${CURRENT_DATE}"
    mkdir -p "$BACKUP_DIR"
    
    log "Creating backup of existing installation: $BACKUP_DIR"
    
    # Copy all files except the virtual environment
    cd "$DEPLOY_DIR"
    find . -maxdepth 1 -not -name "venv" -not -name "." | xargs -I{} cp -r {} "$BACKUP_DIR"
    
    # If it's a fresh install (overwrite), move existing deployment out of the way
    if ! $UPDATE_MODE; then
        log "Moving existing installation aside (fresh install mode)"
        mkdir -p "${DEPLOY_DIR}_old"
        
        # Move all files except venv
        find "$DEPLOY_DIR" -maxdepth 1 -not -name "venv" -not -name "." | xargs -I{} mv {} "${DEPLOY_DIR}_old"
    fi
fi

# =====================================================
# Save important config files and database
# =====================================================
if $UPDATE_MODE; then
    log "Saving important files before update..."
    
    # Create a temporary directory for important files
    TEMP_SAVE_DIR="/tmp/${PROJECT_NAME}_temp_${CURRENT_DATE}"
    mkdir -p "$TEMP_SAVE_DIR"
    
    # Save database file if it exists
    if [ -f "${DEPLOY_DIR}/${DB_FILE}" ]; then
        log "Saving database file..."
        cp "${DEPLOY_DIR}/${DB_FILE}" "${TEMP_SAVE_DIR}/"
    else
        warn "No database file found at ${DEPLOY_DIR}/${DB_FILE}"
    fi
    
    # Save config.py if it was modified
    if [ -f "${DEPLOY_DIR}/config.py" ]; then
        # Check if config.py was modified by comparing with the version in Git
        TEMP_GIT_DIR="/tmp/${PROJECT_NAME}_git_${CURRENT_DATE}"
        mkdir -p "$TEMP_GIT_DIR"
        git clone --depth 1 "$GIT_REPO" "$TEMP_GIT_DIR" > /dev/null 2>&1
        
        if ! cmp -s "${DEPLOY_DIR}/config.py" "${TEMP_GIT_DIR}/config.py" > /dev/null 2>&1; then
            log "Saving modified config.py..."
            cp "${DEPLOY_DIR}/config.py" "${TEMP_SAVE_DIR}/"
        else
            log "config.py has not been modified, no need to save"
        fi
        
        rm -rf "$TEMP_GIT_DIR"
    fi
    
    # Save any other custom files you might have
    # e.g., .env file if it exists
    if [ -f "${DEPLOY_DIR}/.env" ]; then
        log "Saving .env file..."
        cp "${DEPLOY_DIR}/.env" "${TEMP_SAVE_DIR}/"
    fi
fi

# =====================================================
# Clone Repository
# =====================================================
log "Cloning repository from ${GIT_REPO}..."
TEMP_CLONE_DIR="/tmp/${PROJECT_NAME}_clone_${CURRENT_DATE}"
rm -rf "$TEMP_CLONE_DIR"
git clone "$GIT_REPO" "$TEMP_CLONE_DIR" || error "Failed to clone repository"

# =====================================================
# Create or Update Project Directory
# =====================================================
log "Setting up project directory at ${DEPLOY_DIR}..."

# Create project directory if it doesn't exist
mkdir -p "$DEPLOY_DIR"

# Copy files from the cloned repository
log "Updating project files..."
cp -r "${TEMP_CLONE_DIR}"/* "$DEPLOY_DIR/"

# =====================================================
# Restore Important Files
# =====================================================
if $UPDATE_MODE; then
    log "Restoring important files..."
    
    # Restore database file
    if [ -f "${TEMP_SAVE_DIR}/${DB_FILE}" ]; then
        log "Restoring database file..."
        cp "${TEMP_SAVE_DIR}/${DB_FILE}" "${DEPLOY_DIR}/"
    fi
    
    # Restore config.py if it was saved
    if [ -f "${TEMP_SAVE_DIR}/config.py" ]; then
        log "Restoring modified config.py..."
        cp "${TEMP_SAVE_DIR}/config.py" "${DEPLOY_DIR}/"
    fi
    
    # Restore .env file if it was saved
    if [ -f "${TEMP_SAVE_DIR}/.env" ]; then
        log "Restoring .env file..."
        cp "${TEMP_SAVE_DIR}/.env" "${DEPLOY_DIR}/"
    fi
    
    # Clean up temporary directory
    rm -rf "$TEMP_SAVE_DIR"
fi

# Check if requirements.txt exists, if not create it
if [ ! -f "${DEPLOY_DIR}/requirements.txt" ]; then
    log "Creating requirements.txt file based on project analysis..."
    echo "aiogram==3.19.0" > "${DEPLOY_DIR}/requirements.txt"
fi

# Clean up temp clone directory
rm -rf "$TEMP_CLONE_DIR"

# =====================================================
# Setup Virtual Environment
# =====================================================
if [ ! -d "$VENV_DIR" ] || ! $UPDATE_MODE; then
    log "Creating new Python virtual environment..."
    
    # If update mode and venv exists, backup old venv
    if $UPDATE_MODE && [ -d "$VENV_DIR" ]; then
        log "Backing up existing virtual environment..."
        mv "$VENV_DIR" "${VENV_DIR}_old"
    fi
    
    # Create virtual environment
    python3.12 -m venv "$VENV_DIR" || error "Failed to create virtual environment"
else
    log "Updating existing virtual environment..."
fi

# Activate virtual environment and install dependencies
log "Installing Python dependencies..."
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "${DEPLOY_DIR}/requirements.txt" || error "Failed to install Python dependencies"

# =====================================================
# Database Setup
# =====================================================
log "Setting up database directory..."

# Ensure data directory exists
mkdir -p "${DEPLOY_DIR}/data"

# Set appropriate permissions for the entire project directory
chown -R $(logname):$(logname) "${DEPLOY_DIR}"
chmod 755 "${DEPLOY_DIR}/data"

# =====================================================
# Create Systemd Service
# =====================================================
log "Creating systemd service..."

# Detect main file (main.py in this case)
MAIN_FILE="main.py"
if [ ! -f "${DEPLOY_DIR}/${MAIN_FILE}" ]; then
    # Try to find another Python file with a main function
    for file in "${DEPLOY_DIR}"/*.py; do
        if grep -q "if __name__ == \"__main__\"" "$file"; then
            MAIN_FILE=$(basename "$file")
            break
        fi
    done
fi

log "Detected main file: ${MAIN_FILE}"

# Create systemd service file
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=${PROJECT_NAME} Telegram Bot
After=network.target

[Service]
User=$(logname)
Group=$(logname)
WorkingDirectory=${DEPLOY_DIR}
Environment="PATH=${VENV_DIR}/bin"
ExecStart=${VENV_DIR}/bin/python3 ${DEPLOY_DIR}/${MAIN_FILE}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable the service (if not already enabled)
systemctl enable "${SERVICE_NAME}.service"

# Stop the service if it's running (for update)
if $UPDATE_MODE && systemctl is-active --quiet "${SERVICE_NAME}.service"; then
    log "Stopping the service for update..."
    systemctl stop "${SERVICE_NAME}.service"
fi

# Start/restart the service
log "Starting the service..."
systemctl restart "${SERVICE_NAME}.service"

# Check if service is running
if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
    log "Service is running successfully!"
else
    warn "Service failed to start, checking logs..."
    journalctl -u "${SERVICE_NAME}.service" -n 20
    
    if $UPDATE_MODE && [ -n "$BACKUP_DIR" ]; then
        warn "Update failed. Would you like to rollback to previous version? (y/n)"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            log "Rolling back to backup..."
            $0 --rollback "$BACKUP_DIR"
            exit 0
        fi
    fi
    
    error "Service failed to start. Please check the logs above for details."
fi

# Clean up old backups (keep only 5 most recent)
if [ -d "$BACKUP_ROOT" ]; then
    log "Cleaning up old backups (keeping 5 most recent)..."
    cd "$BACKUP_ROOT"
    ls -1td "${PROJECT_NAME}_"* | tail -n +6 | xargs -r rm -rf
fi

# Clean up old venv if it exists
if [ -d "${VENV_DIR}_old" ]; then
    log "Cleaning up old virtual environment..."
    rm -rf "${VENV_DIR}_old"
fi

# Clean up old deployment if it exists
if [ -d "${DEPLOY_DIR}_old" ]; then
    log "Cleaning up old deployment files..."
    rm -rf "${DEPLOY_DIR}_old"
fi

# =====================================================
# Finalize and Show Usage Instructions
# =====================================================
if $UPDATE_MODE; then
    log "Update completed successfully!"
else
    log "Fresh installation completed successfully!"
fi

echo
echo -e "${BLUE}=== ${PROJECT_NAME} Deployment Information ===${NC}"
echo -e "Installation directory: ${DEPLOY_DIR}"
echo -e "Python virtual environment: ${VENV_DIR}"
echo -e "Systemd service name: ${SERVICE_NAME}"
if [ -n "$BACKUP_DIR" ]; then
    echo -e "Backup created at: ${BACKUP_DIR}"
fi
echo
echo -e "${BLUE}=== Management Commands ===${NC}"
echo -e "Start the bot:    ${GREEN}sudo systemctl start ${SERVICE_NAME}${NC}"
echo -e "Stop the bot:     ${GREEN}sudo systemctl stop ${SERVICE_NAME}${NC}"
echo -e "Restart the bot:  ${GREEN}sudo systemctl restart ${SERVICE_NAME}${NC}"
echo -e "Check status:     ${GREEN}sudo systemctl status ${SERVICE_NAME}${NC}"
echo -e "View logs:        ${GREEN}sudo journalctl -u ${SERVICE_NAME} -f${NC}"
echo
echo -e "${BLUE}=== Database Location ===${NC}"
echo -e "Database file:    ${GREEN}${DEPLOY_DIR}/${DB_FILE}${NC}"
echo -e "To backup:        ${GREEN}cp ${DEPLOY_DIR}/${DB_FILE} /path/to/backup/${NC}"
echo
echo -e "${BLUE}=== Update & Rollback ===${NC}"
echo -e "Update bot:       ${GREEN}sudo $0 --update${NC}"
echo -e "Fresh install:    ${GREEN}sudo $0 --fresh${NC}"
if [ -n "$BACKUP_DIR" ]; then
    echo -e "Rollback:        ${GREEN}sudo $0 --rollback ${BACKUP_DIR}${NC}"
fi
echo
echo -e "Your bot should now be running! If you need help or more options, run:"
echo -e "${GREEN}sudo $0 --help${NC}"

exit 0
