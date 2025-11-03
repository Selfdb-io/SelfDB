#!/usr/bin/env bash

set -euo pipefail

CONFIG_DIR="${PGBOUNCER_CONFIG_DIR:-/etc/pgbouncer}"
CONFIG_FILE="${PGBOUNCER_CONFIG_FILE:-${CONFIG_DIR}/pgbouncer.ini}"
USERLIST_FILE="${PGBOUNCER_USERLIST_FILE:-${CONFIG_DIR}/userlist.txt}"
RUN_DIR="${PGBOUNCER_RUN_DIR:-/var/run/pgbouncer}"
LOG_DIR="${PGBOUNCER_LOG_DIR:-/var/log/pgbouncer}"

REQUIRED_VARS=(DATABASES_HOST DATABASES_PORT DATABASES_USER DATABASES_PASSWORD DATABASES_DBNAME)
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo "ERROR: Environment variable ${var} is required but not set." >&2
        exit 1
    fi
done

LISTEN_ADDR="${LISTEN_ADDR:-0.0.0.0}"
LISTEN_PORT="${LISTEN_PORT:-6432}"
AUTH_TYPE="${AUTH_TYPE:-md5}"
POOL_MODE="${POOL_MODE:-session}"
MAX_CLIENT_CONN="${MAX_CLIENT_CONN:-100}"
DEFAULT_POOL_SIZE="${DEFAULT_POOL_SIZE:-20}"
RESERVE_POOL_SIZE="${RESERVE_POOL_SIZE:-0}"
SERVER_LIFETIME="${SERVER_LIFETIME:-3600}"
SERVER_IDLE_TIMEOUT="${SERVER_IDLE_TIMEOUT:-600}"
QUERY_WAIT_TIMEOUT="${QUERY_WAIT_TIMEOUT:-120}"
CLIENT_IDLE_TIMEOUT="${CLIENT_IDLE_TIMEOUT:-0}"
ADMIN_USERS="${ADMIN_USERS:-${DATABASES_USER}}"
STATS_USERS="${STATS_USERS:-${DATABASES_USER}}"
IGNORE_STARTUP_PARAMETERS="${IGNORE_STARTUP_PARAMETERS:-extra_float_digits}"

AUTH_QUERY_DEFAULT='SELECT usename, CASE WHEN valuntil IS NULL OR valuntil > pg_catalog.now() THEN passwd ELSE NULL END FROM pg_catalog.pg_shadow WHERE usename=$1'
AUTH_QUERY="${AUTH_QUERY:-$AUTH_QUERY_DEFAULT}"

mkdir -p "${CONFIG_DIR}" "${RUN_DIR}" "${LOG_DIR}"

DATABASE_ALIAS="${DATABASES_ALIAS:-${DATABASES_DBNAME}}"
DATABASE_LINE="${DATABASE_ALIAS} = host=${DATABASES_HOST} port=${DATABASES_PORT} user=${DATABASES_USER}"

if [ -n "${DATABASES_PASSWORD:-}" ]; then
    DATABASE_LINE="${DATABASE_LINE} password=${DATABASES_PASSWORD}"
fi

DATABASE_LINE="${DATABASE_LINE} dbname=${DATABASES_DBNAME}"

{
    printf '[databases]\n'
    printf '%s\n' "${DATABASE_LINE}"

    printf '\n[pgbouncer]\n'
    printf 'logfile = /dev/stdout\n'
    printf 'pidfile = %s/pgbouncer.pid\n' "${RUN_DIR}"
    printf 'listen_addr = %s\n' "${LISTEN_ADDR}"
    printf 'listen_port = %s\n' "${LISTEN_PORT}"
    printf 'auth_type = %s\n' "${AUTH_TYPE}"
    printf 'auth_file = %s\n' "${USERLIST_FILE}"
    printf 'auth_query = %s\n' "${AUTH_QUERY}"
    printf 'admin_users = %s\n' "${ADMIN_USERS}"
    printf 'stats_users = %s\n' "${STATS_USERS}"
    printf 'pool_mode = %s\n' "${POOL_MODE}"
    printf 'max_client_conn = %s\n' "${MAX_CLIENT_CONN}"
    printf 'default_pool_size = %s\n' "${DEFAULT_POOL_SIZE}"
    printf 'reserve_pool_size = %s\n' "${RESERVE_POOL_SIZE}"
    printf 'server_lifetime = %s\n' "${SERVER_LIFETIME}"
    printf 'server_idle_timeout = %s\n' "${SERVER_IDLE_TIMEOUT}"
    printf 'query_wait_timeout = %s\n' "${QUERY_WAIT_TIMEOUT}"
    printf 'client_idle_timeout = %s\n' "${CLIENT_IDLE_TIMEOUT}"
    printf 'ignore_startup_parameters = %s\n' "${IGNORE_STARTUP_PARAMETERS}"
} > "${CONFIG_FILE}"

chmod 600 "${CONFIG_FILE}"

printf '"%s" "%s"\n' "${DATABASES_USER}" "${DATABASES_PASSWORD}" > "${USERLIST_FILE}"
chmod 600 "${USERLIST_FILE}"

exec "$@"

