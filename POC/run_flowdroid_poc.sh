#!/usr/bin/env bash
#
# FlowDroid POC runner — PriviScan / AndroidGuard FYP
#
# WHAT THIS DOES
#   1. Clones and builds FlowDroid (Maven — needs real internet access,
#      i.e. run this on your own laptop, NOT inside a locked-down sandbox).
#   2. Downloads the Android platform stub jars FlowDroid needs.
#   3. Sets up three APK test tiers:
#        small  -> DroidBench (known-answer benchmark apps, auto-downloaded)
#        medium -> a real open-source F-Droid app (you drop the APK in manually)
#        large  -> a real installed app pulled from your own phone via adb
#   4. Runs FlowDroid on every APK it finds, with a per-app timeout,
#      and logs time / success / timeout / crash into results.csv.
#
# REQUIREMENTS (install these first if missing):
#   - git
#   - Java JDK 11+   (java -version)
#   - Maven          (mvn -version)
#   - adb            (optional, only needed for the "large" tier auto-pull hint)
#
# USAGE
#   chmod +x run_flowdroid_poc.sh
#   ./run_flowdroid_poc.sh
#
# After it finishes, open results.csv — that table, plus the per-app
# log_*.txt and results_*.xml files, is your POC evidence.

set -uo pipefail

WORKDIR="flowdroid_poc"
TIMEOUT_SECS="${TIMEOUT_SECS:-1800}"   # 30 min per app by default; override with:
                                       #   TIMEOUT_SECS=600 ./run_flowdroid_poc.sh

echo "=== FlowDroid POC setup starting in ./$WORKDIR ==="
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# ---------------------------------------------------------------------------
# 0. Prerequisite check
# ---------------------------------------------------------------------------
missing=0
for tool in git java mvn; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "MISSING: $tool — please install it before running this script."
    missing=1
  fi
done
if [ "$missing" -eq 1 ]; then
  echo "Aborting — install the missing tool(s) above and re-run."
  exit 1
fi
if ! command -v adb >/dev/null 2>&1; then
  echo "NOTE: adb not found — the 'large tier' auto-pull hint will be skipped."
  echo "      (install Android platform-tools if you want to pull a real app from your phone)"
fi

# ---------------------------------------------------------------------------
# 1. Clone + build FlowDroid
# ---------------------------------------------------------------------------
if [ ! -d FlowDroid ]; then
  echo "--- Cloning FlowDroid ---"
  git clone --recurse-submodules https://github.com/secure-software-engineering/FlowDroid.git
else
  echo "--- FlowDroid already cloned, skipping ---"
fi

echo "--- Building FlowDroid with Maven (this can take a few minutes) ---"
(cd FlowDroid && mvn -q clean package -DskipTests)

FD_JAR=$(find FlowDroid/soot-infoflow-cmd/target -maxdepth 1 -name "soot-infoflow-cmd*jar-with-dependencies.jar" 2>/dev/null | head -1)
if [ -z "$FD_JAR" ]; then
  echo "ERROR: build finished but the runnable jar wasn't found under FlowDroid/soot-infoflow-cmd/target/"
  echo "       Check the Maven build output above for errors."
  exit 1
fi
FD_JAR_ABS="$(pwd)/$FD_JAR"
SINKS_SOURCES="$(pwd)/FlowDroid/soot-infoflow-android/SourcesAndSinks.txt"
echo "FlowDroid jar ready: $FD_JAR_ABS"

# ---------------------------------------------------------------------------
# 2. Android platform stub jars
# ---------------------------------------------------------------------------
if [ ! -d android-platforms ]; then
  echo "--- Cloning Android platform stubs ---"
  git clone https://github.com/Sable/android-platforms.git
else
  echo "--- android-platforms already cloned, skipping ---"
fi
PLATFORMS_DIR="$(pwd)/android-platforms"

# ---------------------------------------------------------------------------
# 3. Small tier — DroidBench (known-answer apps, good first sanity check)
# ---------------------------------------------------------------------------
if [ ! -d DroidBench ]; then
  echo "--- Cloning DroidBench ---"
  git clone https://github.com/secure-software-engineering/DroidBench.git
else
  echo "--- DroidBench already cloned, skipping ---"
fi
mkdir -p apks/small
find DroidBench -iname "*.apk" -exec cp {} apks/small/ \; 2>/dev/null
small_count=$(find apks/small -iname "*.apk" 2>/dev/null | wc -l)
echo "Small tier: $small_count DroidBench APK(s) ready in apks/small/"
if [ "$small_count" -eq 0 ]; then
  echo "  (DroidBench ships source projects that need building into APKs on some"
  echo "   branches — check DroidBench/README.md if this stays at 0.)"
fi

# ---------------------------------------------------------------------------
# 4. Medium tier — a real, legally-redistributable open-source app
# ---------------------------------------------------------------------------
mkdir -p apks/medium
medium_count=$(find apks/medium -iname "*.apk" 2>/dev/null | wc -l)
if [ "$medium_count" -eq 0 ]; then
  echo ""
  echo ">>> MEDIUM TIER — manual step needed <<<"
  echo "    Go to https://f-droid.org/en/packages/, pick any real app,"
  echo "    download its APK, and drop it into: $(pwd)/apks/medium/"
  echo "    (F-Droid apps are real, open-source, and freely redistributable —"
  echo "     avoids any Play Store scraping/ToS concern.)"
  echo ""
fi

# ---------------------------------------------------------------------------
# 5. Large tier — a real, obfuscated app pulled from your own phone
# ---------------------------------------------------------------------------
mkdir -p apks/large
large_count=$(find apks/large -iname "*.apk" 2>/dev/null | wc -l)
if [ "$large_count" -eq 0 ]; then
  echo ""
  echo ">>> LARGE TIER — manual step needed <<<"
  echo "    Pull a real installed app's APK from your own device (legal —"
  echo "    it's your own phone, your own installed app, not redistribution):"
  echo "      PKG=com.instagram.android   # or any large app you have installed"
  echo "      adb shell pm path \$PKG"
  echo "      adb pull <path-printed-above> $(pwd)/apks/large/base.apk"
  echo ""
fi

# ---------------------------------------------------------------------------
# 6. Run FlowDroid on every APK found, with a timeout, and log results
# ---------------------------------------------------------------------------
RESULTS="results.csv"
echo "tier,apk,size_mb,seconds,exit_status,outcome,findings" > "$RESULTS"

run_one() {
  local tier="$1" apk="$2"
  local name size_mb out_xml log_file start end elapsed status outcome findings

  name=$(basename "$apk" .apk)
  size_mb=$(du -m "$apk" 2>/dev/null | cut -f1)
  out_xml="results_${tier}_${name}.xml"
  log_file="log_${tier}_${name}.txt"

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
  echo "    -> ${elapsed}s | $outcome | findings=$findings"
}

for tier in small medium large; do
  shopt -s nullglob
  for apk in apks/"$tier"/*.apk; do
    run_one "$tier" "$apk"
  done
  shopt -u nullglob
done

echo ""
echo "===== SUMMARY ====="
if command -v column >/dev/null 2>&1; then
  column -s, -t "$RESULTS"
else
  cat "$RESULTS"
fi
echo ""
echo "Full results: $(pwd)/$RESULTS"
echo "Per-app logs: log_<tier>_<name>.txt   |   Per-app raw output: results_<tier>_<name>.xml"
echo ""
echo "This CSV + the per-app logs are your POC evidence:"
echo "  - success rate and timing per tier"
echo "  - concrete TIMEOUT/CRASH cases on real, large apps (if any)"
echo "  -> feed the observed failure pattern into your design decision"
echo "     (e.g. per-app timeout + fallback-to-manifest-only strategy)."