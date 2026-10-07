#!/usr/bin/env bash
#
# run_apks_in_folder.sh — run FlowDroid ONLY on the APK(s) sitting in one folder.
#
# Use this AFTER run_flowdroid_poc.sh has already done the one-time setup
# (built FlowDroid, downloaded android-platforms). This script does not
# touch the small/DroidBench tier again — it only analyzes whatever APK(s)
# you point it at.
#
# USAGE
#   ./run_apks_in_folder.sh <folder> <tier-label>
#
# EXAMPLES
#   ./run_apks_in_folder.sh flowdroid_poc/apks/large  large
#   ./run_apks_in_folder.sh flowdroid_poc/apks/medium medium
#   ./run_apks_in_folder.sh some/other/folder         custom
#
# Results are APPENDED to flowdroid_poc/results.csv (existing rows are kept).
# Per-app logs/xml land in flowdroid_poc/ just like before.
#
# Override the per-app timeout (default 30 min) with:
#   TIMEOUT_SECS=600 ./run_apks_in_folder.sh flowdroid_poc/apks/large large

set -uo pipefail

FOLDER="${1:-}"
TIER="${2:-custom}"
TIMEOUT_SECS="${TIMEOUT_SECS:-1800}"
WORKDIR="flowdroid_poc"

if [ -z "$FOLDER" ]; then
  echo "Usage: $0 <folder-with-apks> <tier-label>"
  echo "Example: $0 flowdroid_poc/apks/large large"
  exit 1
fi
if [ ! -d "$FOLDER" ]; then
  echo "ERROR: folder not found: $FOLDER"
  exit 1
fi

FD_JAR=$(find "$WORKDIR/FlowDroid/soot-infoflow-cmd/target" -maxdepth 1 -name "soot-infoflow-cmd*jar-with-dependencies.jar" 2>/dev/null | head -1)
if [ -z "$FD_JAR" ]; then
  echo "ERROR: FlowDroid jar not found under $WORKDIR/FlowDroid/soot-infoflow-cmd/target/"
  echo "       Run run_flowdroid_poc.sh at least once first (setup step)."
  exit 1
fi
FD_JAR_ABS="$(pwd)/$FD_JAR"
PLATFORMS_DIR="$(pwd)/$WORKDIR/android-platforms"
SINKS_SOURCES="$(pwd)/$WORKDIR/FlowDroid/soot-infoflow-android/SourcesAndSinks.txt"

if [ ! -d "$PLATFORMS_DIR" ]; then
  echo "ERROR: android-platforms not found at $PLATFORMS_DIR"
  echo "       Run run_flowdroid_poc.sh at least once first (setup step)."
  exit 1
fi

RESULTS="$WORKDIR/results.csv"
if [ ! -f "$RESULTS" ]; then
  echo "tier,apk,size_mb,seconds,exit_status,outcome,findings" > "$RESULTS"
fi

run_one() {
  local tier="$1" apk="$2"
  local name size_mb out_xml log_file start end elapsed status outcome findings

  name=$(basename "$apk" .apk)
  size_mb=$(du -m "$apk" 2>/dev/null | cut -f1)
  out_xml="$WORKDIR/results_${tier}_${name}.xml"
  log_file="$WORKDIR/log_${tier}_${name}.txt"

  echo "--- Running FlowDroid on [$tier] $name (${size_mb} MB) ---"
  start=$(date +%s)
  timeout "$TIMEOUT_SECS" java -jar "$FD_JAR_ABS" \
      -a "$apk" \
      -p "$PLATFORMS_DIR" \
      -s "$SINKS_SOURCES" \
      -o "$out_xml" > "$log_file" 2>&1
  status=$?
  end=$(date +%s)
  elapsed=$((end - start))

  if [ "$status" -eq 124 ]; then
    outcome="TIMEOUT"; findings="N/A"
  elif [ "$status" -ne 0 ]; then
    outcome="CRASH"; findings="N/A"
  else
    outcome="SUCCESS"
    findings=$(grep -oc "<Result" "$out_xml" 2>/dev/null || echo "0")
  fi

  echo "$tier,$name,$size_mb,$elapsed,$status,$outcome,$findings" >> "$RESULTS"
  echo "    -> ${elapsed}s | $outcome | findings=$findings   (log: $log_file)"
}

shopt -s nullglob
found=0
for apk in "$FOLDER"/*.apk; do
  found=1
  run_one "$TIER" "$apk"
done
shopt -u nullglob

if [ "$found" -eq 0 ]; then
  echo "No .apk files found in $FOLDER — nothing to do."
  exit 0
fi

echo ""
echo "===== UPDATED RESULTS (all tiers so far) ====="
if command -v column >/dev/null 2>&1; then
  column -s, -t "$RESULTS"
else
  cat "$RESULTS"
fi
