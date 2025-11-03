#!/usr/bin/env bash
set -euo pipefail

# Storage benchmark script (console output)
# - Iterates files under storage-test-files/
# - Creates a benchmark bucket
# - Uploads and downloads each file via backend endpoints using curl
# - Prints file size, upload speed, download TTFB, total time, and secs/GB

API_URL=${API_URL:-http://localhost:3000}
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# Load API_KEY from .env.dev if present
if [ -f .env.dev ]; then
  set -a
  # shellcheck disable=SC1091
  source .env.dev
  set +a
fi

: "${API_KEY:?API_KEY missing (source .env.dev or export API_KEY)}"

BUCKET=${1:-bench-$(date +%Y%m%d%H%M%S)}
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
echo "📦 Storage Benchmark"
echo "API_URL=$API_URL  BUCKET=$BUCKET  RUN_ID=$RUN_ID"

# Temp directory to persist downloaded bytes (simulate browser disk writes)
TMP_DIR=${TMP_DIR:-/tmp/selfdb-bench/$RUN_ID}
mkdir -p "$TMP_DIR"

create_bucket() {
  curl -sS -X POST \
    "$API_URL/api/v1/buckets" \
    -H "x-api-key: $API_KEY" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"$BUCKET\",\"public\":false}" \
    >/dev/null || true
}

size_of() {
  local f="$1"
  if stat -f%z "$f" >/dev/null 2>&1; then
    stat -f%z "$f"
  else
    wc -c < "$f"
  fi
}

# URL-encode a path component (RFC 3986)
urlencode() {
  local raw="$1"
  local length="${#raw}"
  local i c
  for (( i = 0; i < length; i++ )); do
    c="${raw:i:1}"
    case "$c" in
      [a-zA-Z0-9.~_-]) printf '%s' "$c" ;;
      *) printf '%%%02X' "'$c" ;;
    esac
  done
}

human_bytes() {
  awk -v b="$1" 'function f(x){return (x<1024)?sprintf("%d B",x):(x<1048576)?sprintf("%.1f KB",x/1024):(x<1073741824)?sprintf("%.1f MB",x/1048576):sprintf("%.2f GB",x/1073741824)} BEGIN{print f(b)}'
}

secs_per_gb() {
  awk -v t="$1" -v s="$2" 'BEGIN{gb=s/1073741824; if(gb>0) printf("%.3f", t/gb); else print "-"}'
}

bench_upload() {
  local f="$1"
  local rel="${f#storage-test-files/}"
  local path="bench/$RUN_ID/$rel"
  curl -sS -o /dev/null -w "%{http_code} %{time_total} %{speed_upload}" \
    -H "x-api-key: $API_KEY" \
    -F "bucket=$BUCKET" \
    -F "path=$path" \
    -F "file=@$f" \
    "$API_URL/api/v1/files/upload"
}

bench_download() {
  local rel="$1"
  local path="bench/$RUN_ID/$rel"
  local enc_path
  enc_path="$(urlencode "$path")"
  local url="$API_URL/api/v1/files/$BUCKET/$enc_path"
  # Full download metrics (write to disk to match browser behavior)
  local outfile="$TMP_DIR/${rel//\//_}"
  curl -sS -o "$outfile" -w "%{http_code} %{time_starttransfer} %{time_total} %{speed_download}" \
    -H "x-api-key: $API_KEY" \
    "$url"
  # Remove downloaded file after timing is measured
  rm -f "$outfile" || true
}

if [ ! -d storage-test-files ]; then
  echo "storage-test-files directory not found in $PROJECT_ROOT" >&2
  exit 1
fi

echo "Creating/ensuring bucket: $BUCKET"
create_bucket

echo "Running benchmark over files in storage-test-files/ (run_id=$RUN_ID)"
printf "%-40s  %12s  %12s  %10s  %12s  %14s  %14s\n" "file" "size" "up_speed" "dl_ttfb" "dl_total" "up_s/GB" "dl_s/GB"
printf "%-40s  %12s  %12s  %10s  %12s  %14s  %14s\n" "----------------------------------------" "------------" "------------" "----------" "------------" "--------------" "--------------"
UPLOADED_LIST=$(mktemp)
while IFS= read -r -d '' f; do
  rel="${f#storage-test-files/}"
  size_bytes=$(size_of "$f")
  up_metrics=$(bench_upload "$f")
  up_code=$(echo "$up_metrics" | awk '{print $1}')
  up_total=$(echo "$up_metrics" | awk '{print $2}')
  up_speed=$(echo "$up_metrics" | awk '{print $3}')

  # track uploaded path for cleanup
  echo "bench/$RUN_ID/$rel" >> "$UPLOADED_LIST"

  dl_full=$(bench_download "$rel")
  dl_code=$(echo "$dl_full" | awk '{print $1}')
  dl_ttfb=$(echo "$dl_full" | awk '{print $2}')
  dl_total=$(echo "$dl_full" | awk '{print $3}')
  dl_speed=$(echo "$dl_full" | awk '{print $4}')

  up_s_per_gb=$(secs_per_gb "$up_total" "$size_bytes")
  dl_s_per_gb=$(secs_per_gb "$dl_total" "$size_bytes")

  printf "%-40s  %12s  %12s  %10.3fs  %12.3fs  %14s  %14s\n" \
    "$rel" "$(human_bytes "$size_bytes")" "$(awk -v s="$up_speed" 'BEGIN{printf "%.2f MB/s", s/1048576}')" \
    "$dl_ttfb" "$dl_total" "$up_s_per_gb" "$dl_s_per_gb"
done < <(find storage-test-files -type f -print0)

echo "🧹 Cleaning up uploaded files and bucket..."
while IFS= read -r p; do
  enc_p="$(urlencode "$p")"
  curl -sS -X DELETE -o /dev/null -w "" \
    -H "x-api-key: $API_KEY" \
    "$API_URL/api/v1/files/$BUCKET/$enc_p" || true
done < "$UPLOADED_LIST"
rm -f "$UPLOADED_LIST"

# delete bucket (ignore errors)
curl -sS -X DELETE -o /dev/null -w "" \
  -H "x-api-key: $API_KEY" \
  "$API_URL/api/v1/buckets/$BUCKET" || true

echo "Benchmark complete."
exit 0
