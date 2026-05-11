#!/usr/bin/env bash
set -Eeuo pipefail

PRODUCTION_BACKUP_DIR="${PRODUCTION_BACKUP_DIR:-/media/zero/Storage1/gruzpotok-production-backups}"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-36}"
GRUZPOTOK_MIN_BYTES="${GRUZPOTOK_MIN_BYTES:-1000000}"
BOTDB_MIN_BYTES="${BOTDB_MIN_BYTES:-10000000}"
MIN_COPY_TABLES="${MIN_COPY_TABLES:-20}"

now_epoch="$(date +%s)"
overall_status=0

check_family() {
  local family="$1"
  local pattern="$2"
  local min_bytes="$3"

  echo "=== FAMILY=${family} ==="

  if [ ! -d "$PRODUCTION_BACKUP_DIR" ]; then
    echo "STATUS=fail"
    echo "REASON=backup_dir_missing"
    echo "DIR=${PRODUCTION_BACKUP_DIR}"
    overall_status=1
    return
  fi

  local latest
  latest="$(
    find "$PRODUCTION_BACKUP_DIR" -type f -name "$pattern" -printf '%T@ %p\n' 2>/dev/null \
      | sort -n \
      | tail -1 \
      | cut -d' ' -f2-
  )"

  if [ -z "${latest:-}" ]; then
    echo "STATUS=fail"
    echo "REASON=no_backup_found"
    echo "PATTERN=${pattern}"
    overall_status=1
    return
  fi

  local file_epoch age_hours bytes copy_tables

  file_epoch="$(stat -c %Y "$latest")"
  age_hours="$(( (now_epoch - file_epoch) / 3600 ))"
  bytes="$(stat -c %s "$latest")"

  echo "FILE=${latest}"
  echo "AGE_HOURS=${age_hours}"
  echo "BYTES=${bytes}"

  if [ "$age_hours" -gt "$MAX_AGE_HOURS" ]; then
    echo "STATUS=fail"
    echo "REASON=too_old"
    overall_status=1
    return
  fi

  if ! gzip -t "$latest"; then
    echo "GZIP=fail"
    echo "STATUS=fail"
    echo "REASON=gzip_integrity_failed"
    overall_status=1
    return
  fi

  echo "GZIP=ok"

  if [ "$bytes" -lt "$min_bytes" ]; then
    echo "STATUS=fail"
    echo "REASON=size_too_small"
    echo "MIN_BYTES=${min_bytes}"
    overall_status=1
    return
  fi

  copy_tables="$(gzip -cd "$latest" | grep -Ec '^COPY ' || true)"
  echo "COPY_TABLES=${copy_tables}"

  if [ "$copy_tables" -lt "$MIN_COPY_TABLES" ]; then
    echo "STATUS=fail"
    echo "REASON=copy_tables_too_low"
    echo "MIN_COPY_TABLES=${MIN_COPY_TABLES}"
    overall_status=1
    return
  fi

  echo "STATUS=ok"
}

check_family "gruzpotok" "gruzpotok_*.sql.gz" "$GRUZPOTOK_MIN_BYTES"
check_family "botdb" "botdb_*.sql.gz" "$BOTDB_MIN_BYTES"

if [ "$overall_status" -eq 0 ]; then
  echo "PRODUCTION_BACKUP_FRESHNESS=ok"
else
  echo "PRODUCTION_BACKUP_FRESHNESS=fail"
fi

exit "$overall_status"
