#!/bin/bash
# ViMax Project Backup Script
# Creates a timestamped backup of the entire project

# Get current timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="ViMax_backup_${TIMESTAMP}"
BACKUP_DIR="${HOME}/ViMax_backups"
PROJECT_DIR="/home/jerryxu/Project/ViMax"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

echo "=========================================="
echo "ViMax Project Backup"
echo "=========================================="
echo "Timestamp: ${TIMESTAMP}"
echo "Source: ${PROJECT_DIR}"
echo "Destination: ${BACKUP_DIR}/${BACKUP_NAME}"
echo "=========================================="

# Create backup using tar with compression
echo "Creating backup archive..."
cd "${PROJECT_DIR}/.." || exit 1

tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" \
    --exclude='ViMax/.venv' \
    --exclude='ViMax/__pycache__' \
    --exclude='ViMax/**/__pycache__' \
    --exclude='ViMax/.git' \
    --exclude='ViMax/node_modules' \
    --exclude='ViMax/.working_dir/*/videos' \
    --exclude='ViMax/.working_dir/*/cache' \
    ViMax

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
    echo "✓ Backup created successfully!"
    echo "  File: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
    echo "  Size: ${BACKUP_SIZE}"
    
    # List all backups
    echo ""
    echo "All backups in ${BACKUP_DIR}:"
    ls -lh "${BACKUP_DIR}" | grep "ViMax_backup"
    
    # Calculate total backup size
    TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
    echo ""
    echo "Total backup directory size: ${TOTAL_SIZE}"
else
    echo "✗ Backup failed!"
    exit 1
fi

echo "=========================================="
echo "Backup complete!"
echo "=========================================="

# Instructions for restoration
echo ""
echo "To restore this backup:"
echo "  tar -xzf ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz -C /desired/location/"
echo ""