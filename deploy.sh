#!/bin/bash
# =====================================================
# Deployment Script for CoupleToDoBot Telegram Bot
# For Ubuntu 24.04 with Python 3.12
# =====================================================

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log function for better output
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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "Please run as root (use sudo)"
fi

# =====================================================
# Configuration Variables
# =====================================================
PROJECT_NAME="CoupleToDoBot"
DEPLOY_DIR="/opt/${PROJECT_NAME}"
VENV_DIR="${DEPLOY_DIR}/venv"
SERVICE_NAME="coupletodobot"
GIT_REPO="https://github.com/sandexzx/CoupleToDoBot"

log "Will deploy from GitHub repository: ${GIT_REPO}"

# =====================================================
# Check System and Install Dependencies
# =====================================================
log "Checking system and installing required packages..."

# Update package lists
apt update -qq || error "Failed to update package lists"

# Install required packages
apt install -y python3.12 python3.12-venv python3.12-dev git sqlite3 || error "Failed to install dependencies"

# =====================================================
# Create Project Directory and Setup
# =====================================================
log "Setting up project directory at ${DEPLOY_DIR}..."

# Create project directory if it doesn't exist
mkdir -p "$DEPLOY_DIR"

# Clone from GitHub repository
log "Cloning repository from ${GIT_REPO}..."
rm -rf "${DEPLOY_DIR}/temp_clone"
git clone "$GIT_REPO" "${DEPLOY_DIR}/temp_clone" || error "Failed to clone repository"

# Copy files from the cloned repository
cp -r "${DEPLOY_DIR}/temp_clone"/* "$DEPLOY_DIR/"
rm -rf "${DEPLOY_DIR}/temp_clone"

# Check if requirements.txt exists, if not create it
if [ ! -f "${DEPLOY_DIR}/requirements.txt" ]; then
    log "Creating requirements.txt file based on project analysis..."
    echo "aiogram==3.19.0" > "${DEPLOY_DIR}/requirements.txt"
fi

# =====================================================
# Setup Virtual Environment
# =====================================================
log "Creating Python virtual environment..."

# Create virtual environment
python3.12 -m venv "$VENV_DIR" || error "Failed to create virtual environment"

# Activate virtual environment and install dependencies
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "${DEPLOY_DIR}/requirements.txt" || error "Failed to install Python dependencies"

# =====================================================
# Database Setup
# =====================================================
log "Setting up database..."

# SQLite is used in this project, ensure the data directory exists
mkdir -p "${DEPLOY_DIR}/data"

# Set appropriate permissions for the database directory
chown -R $(logname):$(logname) "${DEPLOY_DIR}/data"
chmod 755 "${DEPLOY_DIR}/data"

# Set permissions for the entire project directory
chown -R $(logname):$(logname) "${DEPLOY_DIR}"

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

# Reload systemd, enable and start the service
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl start "${SERVICE_NAME}.service"

# Check if service is running
if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
    log "Service is running successfully!"
else
    warn "Service failed to start, checking logs..."
    journalctl -u "${SERVICE_NAME}.service" -n 20
    error "Service failed to start. Please check the logs above for details."
fi

# =====================================================
# Finalize and Show Usage Instructions
# =====================================================
log "Deployment completed successfully!"
echo
echo -e "${BLUE}=== ${PROJECT_NAME} Deployment Information ===${NC}"
echo -e "Installation directory: ${DEPLOY_DIR}"
echo -e "Python virtual environment: ${VENV_DIR}"
echo -e "Systemd service name: ${SERVICE_NAME}"
echo
echo -e "${BLUE}=== Management Commands ===${NC}"
echo -e "Start the bot:    ${GREEN}sudo systemctl start ${SERVICE_NAME}${NC}"
echo -e "Stop the bot:     ${GREEN}sudo systemctl stop ${SERVICE_NAME}${NC}"
echo -e "Restart the bot:  ${GREEN}sudo systemctl restart ${SERVICE_NAME}${NC}"
echo -e "Check status:     ${GREEN}sudo systemctl status ${SERVICE_NAME}${NC}"
echo -e "View logs:        ${GREEN}sudo journalctl -u ${SERVICE_NAME} -f${NC}"
echo
echo -e "${BLUE}=== Database Location ===${NC}"
echo -e "Database file:    ${GREEN}${DEPLOY_DIR}/couple_tasks.db${NC}"
echo -e "To backup:        ${GREEN}cp ${DEPLOY_DIR}/couple_tasks.db /path/to/backup/${NC}"
echo
echo -e "Your bot should now be running! If you need to make changes to the code,"
echo -e "update the files in ${DEPLOY_DIR} and restart the service."

exit 0
