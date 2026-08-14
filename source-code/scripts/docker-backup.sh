#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
BACKUP_FILE="${BACKUP_DIR}/buyoh-payroll-${TIMESTAMP}.dump"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"

cd "${PROJECT_DIR}"
mkdir -p "${BACKUP_DIR}"

echo "Checking PostgreSQL container..."

if ! docker compose --env-file .env.docker exec -T db \
    pg_isready -U payroll_user -d buyoh_payroll >/dev/null; then
    echo "ERROR: PostgreSQL is not ready."
    exit 1
fi

echo "Creating payroll backup..."

docker compose --env-file .env.docker exec -T db \
    pg_dump \
        --format=custom \
        --compress=9 \
        --no-owner \
        --no-acl \
        --username=payroll_user \
        --dbname=buyoh_payroll \
    > "${BACKUP_FILE}"

chmod 600 "${BACKUP_FILE}"

if ! pg_restore --list "${BACKUP_FILE}" >/dev/null; then
    echo "ERROR: Backup validation failed."
    exit 1
fi

sha256sum "${BACKUP_FILE}" > "${CHECKSUM_FILE}"
chmod 600 "${CHECKSUM_FILE}"

echo "Backup completed successfully:"
echo "${BACKUP_FILE}"
du -h "${BACKUP_FILE}"
