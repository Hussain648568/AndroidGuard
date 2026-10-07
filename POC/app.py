import os
import sys
import time
import json
import uuid
import threading
import subprocess
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file, abort
from werkzeug.utils import secure_filename
import psutil
import requests
from bs4 import BeautifulSoup

# Androguard & Google Play Scraper (silence loguru debug spam)
try:
    from loguru import logger
    logger.disable("androguard")
except Exception:
    pass

try:
    from androguard.core.apk import APK
except ImportError:
    try:
        from androguard.core.bytecodes.apk import APK
    except ImportError:
        APK = None

try:
    from google_play_scraper import app as gplay_app
except ImportError:
    gplay_app = None

# ---------------------------------------------------------------------------
# CONFIGURATION
# Configurable at the top of the app (or override with environment variables)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FLOWDROID_JAR = os.environ.get(
    "FLOWDROID_JAR",
    os.path.join(
        BASE_DIR,
        "flowdroid_poc",
        "FlowDroid",
        "soot-infoflow-cmd",
        "target",
        "soot-infoflow-cmd-jar-with-dependencies.jar"
    )
)

PLATFORMS_DIR = os.environ.get(
    "PLATFORMS_DIR",
    os.path.join(BASE_DIR, "flowdroid_poc", "android-platforms")
)

SOURCES_SINKS_FILE = os.environ.get(
    "SOURCES_SINKS_FILE",
    os.path.join(
        BASE_DIR,
        "flowdroid_poc",
        "FlowDroid",
        "soot-infoflow-android",
        "SourcesAndSinks.txt"
    )
)

DEFAULT_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", 1800))

# Normalize paths for Windows/Unix compatibility
FLOWDROID_JAR = os.path.abspath(FLOWDROID_JAR)
PLATFORMS_DIR = os.path.abspath(PLATFORMS_DIR)
SOURCES_SINKS_FILE = os.path.abspath(SOURCES_SINKS_FILE)

RUNS_DIR = os.path.abspath(os.path.join(BASE_DIR, "runs"))
UPLOADS_DIR = os.path.join(RUNS_DIR, "uploads")
OUTPUTS_DIR = os.path.join(RUNS_DIR, "outputs")
HISTORY_FILE = os.path.join(RUNS_DIR, "history.json")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB max APK upload

# ---------------------------------------------------------------------------
# IN-MEMORY RUN STORE & SINGLE-RUN LOCK
# ---------------------------------------------------------------------------
run_lock = threading.Lock()
is_running = False
active_run_id = None
runs_store = {}  # run_id -> run dictionary


def load_history():
    """Load past runs from JSON file if available."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to read history file: {e}")
    return []


def save_history(history_list):
    """Save past runs summary to JSON file."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_list, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to write history file: {e}")


run_history = load_history()


# ---------------------------------------------------------------------------
# PROCESS MANAGEMENT (WINDOWS & CROSS-PLATFORM)
# ---------------------------------------------------------------------------
def kill_process_tree(pid):
    """Reliably kill a process and all its descendants on Windows & Unix."""
    if not pid:
        return
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        try:
            parent.kill()
        except psutil.NoSuchProcess:
            pass
    except psutil.NoSuchProcess:
        pass
    except Exception as e:
        print(f"Error terminating process tree {pid} via psutil: {e}")

    # Fallback specifically for Windows command prompt / taskkill
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# XML OUTPUT PARSING
# ---------------------------------------------------------------------------
def parse_flowdroid_xml(xml_path):
    """
    Parses FlowDroid XML results:
    - Root TerminationState attribute
    - PerformanceData metrics
    - Results table: Sink (Method & Statement) and feeding Sources (Method & Statement)
    """
    if not os.path.exists(xml_path):
        return None

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        termination_state = root.attrib.get("TerminationState", "Unknown")

        # Performance metrics
        perf_data = {
            "CallgraphConstructionSeconds": "-",
            "TaintPropagationSeconds": "-",
            "PathReconstructionSeconds": "-",
            "TotalRuntimeSeconds": "-",
            "MaxMemoryConsumption": "-",
            "SourceCount": "-",
            "SinkCount": "-"
        }
        perf_node = root.find("PerformanceData")
        if perf_node is not None:
            for entry in perf_node.findall("PerformanceEntry"):
                name = entry.attrib.get("Name")
                val = entry.attrib.get("Value")
                if name in perf_data:
                    perf_data[name] = val

        # Result findings
        findings = []
        results_node = root.find("Results")
        if results_node is not None:
            for result in results_node.findall("Result"):
                sink_elem = result.find("Sink")
                sink_stmt = sink_elem.attrib.get("Statement", "") if sink_elem is not None else ""
                sink_method = sink_elem.attrib.get("Method", "") if sink_elem is not None else ""

                sources_node = result.find("Sources")
                sources_list = []
                if sources_node is not None:
                    for src in sources_node.findall("Source"):
                        sources_list.append({
                            "statement": src.attrib.get("Statement", ""),
                            "method": src.attrib.get("Method", "")
                        })

                # If no explicit source elements, provide a fallback
                if not sources_list:
                    sources_list.append({"statement": "-", "method": "-"})

                for src in sources_list:
                    findings.append({
                        "source_statement": src["statement"],
                        "source_method": src["method"],
                        "sink_statement": sink_stmt,
                        "sink_method": sink_method
                    })

        return {
            "termination_state": termination_state,
            "performance_data": perf_data,
            "findings": findings,
            "total_findings": len(findings)
        }
    except Exception as e:
        print(f"Error parsing XML ({xml_path}): {e}")
        return None


# ---------------------------------------------------------------------------
# GOOGLE PLAY DATA SAFETY SECTION (DSS) EXTRACTOR
# ---------------------------------------------------------------------------
def get_clean_dss_for_ui(apk_file_path):
    """
    Extracts package name from APK using androguard and queries Google Play
    for its Data Safety Section (DSS) declarations.
    Returns a formatted JSON string as specified in Task 1.
    """
    package_name = "Unknown"
    try:
        if not APK:
            return json.dumps({
                "error": "Androguard is not installed or available.",
                "package_name": package_name
            }, indent=4)

        uploaded_apk = APK(apk_file_path)
        package_name = uploaded_apk.get_package() or "Unknown"

        if not gplay_app:
            return json.dumps({
                "error": "google-play-scraper is not installed or available.",
                "package_name": package_name
            }, indent=4)

        store_data = gplay_app(package_name, lang="en", country="us")

        # Enhanced scraping of Data Safety Section from Google Play store
        collected = []
        shared = []
        encrypted = "Not Declared"
        deletion = "Not Declared"
        try:
            url = f"https://play.google.com/store/apps/datasafety?id={package_name}&hl=en"
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for heading in soup.find_all(["h2", "h3"]):
                    title = heading.get_text().strip()
                    parent = heading.find_parent("section") or heading.parent
                    if "Data shared" in title:
                        for item in parent.find_all(["h3", "h4"]):
                            txt = item.get_text().strip()
                            if txt and txt not in shared and txt != title:
                                shared.append(txt)
                    elif "Data collected" in title:
                        for item in parent.find_all(["h3", "h4"]):
                            txt = item.get_text().strip()
                            if txt and txt not in collected and txt != title:
                                collected.append(txt)
                    elif "Security practices" in title:
                        sec_text = parent.get_text()
                        if "encrypted in transit" in sec_text.lower():
                            encrypted = "Yes, in transit"
                        if "delete" in sec_text.lower():
                            deletion = "Yes"
        except Exception:
            pass

        is_enc_bool = (encrypted.startswith("Yes") or bool(store_data.get("securityPractices")))
        is_del_bool = (deletion.startswith("Yes") or "delete" in str(store_data.get("securityPractices")).lower())
        coll_list = collected if collected else ([] if not store_data.get("collectedData") else store_data.get("collectedData"))
        shared_list = shared if shared else ([] if not store_data.get("sharedData") else store_data.get("sharedData"))

        ui_dss_data = {
            "package_name": package_name,
            # Top-level fields as specified in Task 1 snippet
            "app_name": store_data.get("title", "Unknown App"),
            "developer": store_data.get("developer", "Unknown"),
            "icon_url": store_data.get("icon", ""),
            "privacy_policy_link": store_data.get("privacyPolicy", "#"),
            "is_data_encrypted": is_enc_bool,
            "is_data_deletion_supported": is_del_bool,
            "data_collected": coll_list,
            "data_shared": shared_list,
            # Nested fields for structural compatibility
            "app_info": {
                "name": store_data.get("title", "Unknown App"),
                "developer": store_data.get("developer", "Unknown"),
                "icon_url": store_data.get("icon", ""),
                "privacy_policy_link": store_data.get("privacyPolicy", "#")
            },
            "data_safety_summary": {
                "is_data_encrypted": encrypted if encrypted != "Not Declared" else ("Yes, in transit" if store_data.get("securityPractices") else "Not Declared"),
                "can_request_deletion": deletion if deletion != "Not Declared" else ("Yes" if "delete" in str(store_data.get("securityPractices")).lower() else "Not Declared"),
                "data_collected": coll_list or ["No Data Collection Declared"],
                "data_shared_with_third_parties": shared_list or ["No Third-Party Sharing Declared"]
            }
        }
        return json.dumps(ui_dss_data, indent=4)

    except Exception as e:
        return json.dumps({
            "error": f"Data Safety Section not found on Google Play for this APK. (Package: {package_name})",
            "package_name": package_name
        }, indent=4)


def get_clean_dss_data(apk_file_path):
    """Helper that returns the DSS result as a python dictionary."""
    res = get_clean_dss_for_ui(apk_file_path)
    if isinstance(res, str):
        try:
            return json.loads(res)
        except Exception:
            pass
    return res


def extract_perf_from_logs(logs, elapsed_seconds=0):
    """Extracts performance statistics from FlowDroid console logs when XML is absent."""
    text = "\n".join(logs) if logs else ""

    callgraph_sec = "-"
    m = re.search(r"Callgraph construction took\s+(\d+)\s+seconds", text)
    if m:
        callgraph_sec = m.group(1)

    max_mem = "-"
    m = re.search(r"Maximum memory consumption:\s*(\d+)\s*MB", text)
    if m:
        max_mem = m.group(1)

    src_count = "-"
    m = re.search(r"with\s+(\d+)\s+sources", text)
    if not m:
        m = re.search(r"from\s+(\d+)\s+sources", text)
    if m:
        src_count = m.group(1)

    sink_count = "-"
    m = re.search(r"and\s+(\d+)\s+sinks", text)
    if m:
        sink_count = m.group(1)

    total_sec = str(round(elapsed_seconds)) if elapsed_seconds else "-"

    return {
        "CallgraphConstructionSeconds": callgraph_sec,
        "TaintPropagationSeconds": "-",
        "PathReconstructionSeconds": "-",
        "TotalRuntimeSeconds": total_sec,
        "MaxMemoryConsumption": max_mem,
        "SourceCount": src_count,
        "SinkCount": sink_count
    }


def write_zero_leak_xml(output_xml, perf_data):
    """Writes a standard FlowDroid-compatible results XML file for zero-leak runs."""
    root = ET.Element("DataFlowResults", {"FileFormatVersion": "102", "TerminationState": "Success"})
    ET.SubElement(root, "Results")
    perf_node = ET.SubElement(root, "PerformanceData")
    if perf_data:
        for k, v in perf_data.items():
            ET.SubElement(perf_node, "PerformanceEntry", {"Name": k, "Value": str(v)})
    tree = ET.ElementTree(root)
    tree.write(output_xml, encoding="utf-8", xml_declaration=True)


def determine_run_outcome(exit_code, killed_by_timeout, output_xml, logs, elapsed_seconds=0):
    """
    Single source of truth to decide run outcome, findings count, results, and crash snippet.
    Guarantees consistency across main results panel, live monitor, and session history.
    """
    full_log_text = "\n".join(logs) if logs else ""
    xml_exists = os.path.exists(output_xml) and os.path.getsize(output_xml) > 0

    if killed_by_timeout:
        return {
            "outcome": "TIMEOUT",
            "findings_count": 0,
            "results": None,
            "crash_snippet": None,
            "xml_available": xml_exists
        }

    if exit_code != 0:
        crash_snip = "\n".join(logs[-30:]) if logs else "No output captured."
        return {
            "outcome": "CRASH",
            "findings_count": 0,
            "results": None,
            "crash_snippet": crash_snip,
            "xml_available": xml_exists
        }

    # Exit code is 0
    if xml_exists:
        parsed_results = parse_flowdroid_xml(output_xml)
        if parsed_results:
            t_state = parsed_results["termination_state"]
            outcome = "SUCCESS" if t_state == "Success" else f"PARTIAL: {t_state}"
            return {
                "outcome": outcome,
                "findings_count": parsed_results["total_findings"],
                "results": parsed_results,
                "crash_snippet": None,
                "xml_available": True
            }
        else:
            return {
                "outcome": "CRASH",
                "findings_count": 0,
                "results": None,
                "crash_snippet": "XML output file exists but failed XML parsing.",
                "xml_available": True
            }

    # Exit code 0, but no XML produced by FlowDroid CLI.
    # Check if this was a clean zero-leak completion.
    zero_leak_indicators = [
        "Found 0 leaks",
        "No results found",
        "0 leaks from",
        "No sources found, aborting analysis"
    ]
    is_zero_leak = any(indicator in full_log_text for indicator in zero_leak_indicators)

    if is_zero_leak:
        perf_data = extract_perf_from_logs(logs, elapsed_seconds)
        try:
            write_zero_leak_xml(output_xml, perf_data)
            parsed_results = parse_flowdroid_xml(output_xml)
        except Exception as e:
            print(f"Notice: Failed to write zero-leak XML: {e}")
            parsed_results = {
                "termination_state": "Success",
                "performance_data": perf_data,
                "findings": [],
                "total_findings": 0
            }

        return {
            "outcome": "SUCCESS",
            "findings_count": 0,
            "results": parsed_results,
            "crash_snippet": None,
            "xml_available": os.path.exists(output_xml)
        }

    # Exit code 0, no XML, and no zero-leak indicator -> unexpected crash
    crash_snip = "FlowDroid exited with code 0 but produced no output XML file.\nLast log lines:\n" + (
        "\n".join(logs[-30:]) if logs else "No logs recorded."
    )
    return {
        "outcome": "CRASH",
        "findings_count": 0,
        "results": None,
        "crash_snippet": crash_snip,
        "xml_available": False
    }


# ---------------------------------------------------------------------------
# BACKGROUND WORKER FOR FLOWDROID RUN
# ---------------------------------------------------------------------------
def run_flowdroid_worker(run_id):
    global is_running, active_run_id

    run = runs_store.get(run_id)
    if not run:
        return

    apk_path = run["apk_path"]
    timeout_secs = run["timeout"]
    output_xml = run["output_xml"]

    cmd = [
        "java",
        "-jar", FLOWDROID_JAR,
        "-a", apk_path,
        "-p", PLATFORMS_DIR,
        "-s", SOURCES_SINKS_FILE,
        "-o", output_xml
    ]

    run["logs"].append(f"[INIT] FlowDroid JAR: {FLOWDROID_JAR}")
    run["logs"].append(f"[INIT] Android Platforms: {PLATFORMS_DIR}")
    run["logs"].append(f"[INIT] Sources & Sinks: {SOURCES_SINKS_FILE}")
    run["logs"].append(f"[INIT] Target APK: {apk_path} ({run['apk_size_mb']} MB)")
    run["logs"].append(f"[INIT] Timeout: {timeout_secs}s")

    # Extract Google Play Data Safety Section
    run["logs"].append("[INIT] Extracting Google Play Data Safety declarations...")
    try:
        dss_dict = get_clean_dss_data(apk_path)
        run["dss_data"] = dss_dict
        if dss_dict and "package_name" in dss_dict:
            run["package_name"] = dss_dict["package_name"]
            if "error" not in dss_dict:
                app_title = dss_dict.get("app_info", {}).get("name")
                run["logs"].append(f"[DSS] Play Store match: '{app_title}' (Package: {dss_dict['package_name']})")
            else:
                run["logs"].append(f"[DSS] Package: {dss_dict['package_name']} (Not found on Google Play)")

            # Cache DSS output
            dss_file = os.path.join(OUTPUTS_DIR, f"dss_{run_id}.json")
            with open(dss_file, "w", encoding="utf-8") as f:
                json.dump(dss_dict, f, indent=2)
    except Exception as e:
        run["logs"].append(f"[DSS] Notice: Data Safety extraction skipped ({e})")

    run["logs"].append(f"[INIT] Starting FlowDroid analysis command...")

    start_time = time.time()
    run["start_time"] = start_time
    run["status"] = "running"

    proc = None
    killed_by_timeout = False

    if not os.path.exists(FLOWDROID_JAR):
        run["logs"].append(f"[ERROR] FlowDroid JAR not found at: {FLOWDROID_JAR}")
        run["logs"].append("[HINT] Provide the FlowDroid JAR path via the FLOWDROID_JAR environment variable or .env file.")
    else:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            run["pid"] = proc.pid

            # Reader loop for streaming logs with non-blocking timeout check
            def log_reader():
                for line in iter(proc.stdout.readline, ""):
                    cleaned = line.rstrip("\r\n")
                    if cleaned:
                        run["logs"].append(cleaned)
                proc.stdout.close()

            reader_thread = threading.Thread(target=log_reader, daemon=True)
            reader_thread.start()

            # Monitor execution against timeout
            while proc.poll() is None:
                elapsed = time.time() - start_time
                run["elapsed_seconds"] = round(elapsed, 1)

                if elapsed > timeout_secs:
                    killed_by_timeout = True
                    run["logs"].append(f"[TIMEOUT] Execution exceeded {timeout_secs}s timeout. Terminating process tree...")
                    kill_process_tree(proc.pid)
                    break
                time.sleep(0.5)

            proc.wait()
            reader_thread.join(timeout=2.0)

        except Exception as e:
            run["logs"].append(f"[ERROR] Subprocess execution failed: {str(e)}")
            if proc and proc.pid:
                kill_process_tree(proc.pid)

    end_time = time.time()
    run["end_time"] = end_time
    run["elapsed_seconds"] = round(end_time - start_time, 1)
    run["exit_code"] = -1 if killed_by_timeout else (proc.returncode if proc else -1)

    # -----------------------------------------------------------------------
    # OUTCOME DETERMINATION (Single Source of Truth)
    # -----------------------------------------------------------------------
    outcome_data = determine_run_outcome(
        exit_code=run["exit_code"],
        killed_by_timeout=killed_by_timeout,
        output_xml=output_xml,
        logs=run["logs"],
        elapsed_seconds=run["elapsed_seconds"]
    )

    run["outcome"] = outcome_data["outcome"]
    run["status"] = "completed"
    run["findings_count"] = outcome_data["findings_count"]
    run["results"] = outcome_data["results"]
    run["crash_snippet"] = outcome_data["crash_snippet"]
    run["xml_available"] = outcome_data["xml_available"]

    # Record to history
    history_entry = {
        "run_id": run["run_id"],
        "apk_name": run["apk_name"],
        "package_name": run.get("package_name"),
        "app_title": run.get("dss_data", {}).get("app_info", {}).get("name") if run.get("dss_data") and "error" not in run["dss_data"] else None,
        "apk_size_mb": run["apk_size_mb"],
        "timestamp": datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S"),
        "timeout": timeout_secs,
        "elapsed_seconds": run["elapsed_seconds"],
        "outcome": outcome_data["outcome"],
        "findings_count": outcome_data["findings_count"],
        "xml_available": outcome_data["xml_available"]
    }
    run_history.insert(0, history_entry)
    save_history(run_history)

    # Release single-run lock
    with run_lock:
        is_running = False
        active_run_id = None


# ---------------------------------------------------------------------------
# FLASK ROUTES
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    config_info = {
        "flowdroid_jar": FLOWDROID_JAR,
        "platforms_dir": PLATFORMS_DIR,
        "sources_sinks_file": SOURCES_SINKS_FILE,
        "default_timeout": DEFAULT_TIMEOUT,
        "jar_exists": os.path.exists(FLOWDROID_JAR),
        "platforms_exists": os.path.exists(PLATFORMS_DIR),
        "sources_sinks_exists": os.path.exists(SOURCES_SINKS_FILE),
    }
    return render_template("index.html", config=config_info)


@app.route("/api/run", methods=["POST"])
def start_run():
    global is_running, active_run_id

    if "apk_file" not in request.files:
        return jsonify({"error": "No APK file uploaded"}), 400

    file = request.files["apk_file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith(".apk"):
        return jsonify({"error": "Only .apk files are supported"}), 400

    try:
        timeout = int(request.form.get("timeout", DEFAULT_TIMEOUT))
        if timeout <= 0:
            timeout = DEFAULT_TIMEOUT
    except ValueError:
        timeout = DEFAULT_TIMEOUT

    with run_lock:
        if is_running:
            return jsonify({
                "error": "Another analysis is already running. Please wait for it to complete.",
                "active_run_id": active_run_id
            }), 409

        is_running = True
        run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        active_run_id = run_id

    safe_name = secure_filename(file.filename) or "target.apk"
    saved_apk_path = os.path.join(UPLOADS_DIR, f"{run_id}_{safe_name}")
    file.save(saved_apk_path)

    file_size_bytes = os.path.getsize(saved_apk_path)
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

    output_xml_path = os.path.join(OUTPUTS_DIR, f"results_{run_id}.xml")

    run_record = {
        "run_id": run_id,
        "apk_name": safe_name,
        "apk_size_bytes": file_size_bytes,
        "apk_size_mb": file_size_mb,
        "apk_path": saved_apk_path,
        "output_xml": output_xml_path,
        "timeout": timeout,
        "status": "queued",
        "outcome": None,
        "start_time": None,
        "end_time": None,
        "elapsed_seconds": 0,
        "exit_code": None,
        "logs": [],
        "results": None,
        "crash_snippet": None,
        "findings_count": 0,
        "xml_available": False,
        "dss_data": None,
        "package_name": None,
        "pid": None
    }
    runs_store[run_id] = run_record

    worker_thread = threading.Thread(target=run_flowdroid_worker, args=(run_id,), daemon=True)
    worker_thread.start()

    return jsonify({
        "success": True,
        "run_id": run_id,
        "apk_name": safe_name,
        "apk_size_mb": file_size_mb,
        "timeout": timeout
    })


@app.route("/api/poll/<run_id>")
def poll_run(run_id):
    run = runs_store.get(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404

    try:
        since_line = int(request.args.get("since_line", 0))
    except ValueError:
        since_line = 0

    all_logs = run["logs"]
    new_logs = all_logs[since_line:] if since_line < len(all_logs) else []

    current_elapsed = run["elapsed_seconds"]
    if run["status"] == "running" and run["start_time"]:
        current_elapsed = round(time.time() - run["start_time"], 1)

    response_data = {
        "run_id": run_id,
        "status": run["status"],
        "outcome": run["outcome"],
        "elapsed_seconds": current_elapsed,
        "total_lines": len(all_logs),
        "new_logs": new_logs,
        "findings_count": run["findings_count"],
        "xml_available": run["xml_available"],
        "dss_data": run.get("dss_data"),
        "package_name": run.get("package_name")
    }

    if run["status"] == "completed":
        response_data["results"] = run["results"]
        response_data["crash_snippet"] = run["crash_snippet"]
        response_data["exit_code"] = run["exit_code"]

    return jsonify(response_data)


@app.route("/api/run/<run_id>")
def get_run_details(run_id):
    """Fetch complete run details for past runs."""
    run = runs_store.get(run_id)
    if not run:
        # Check if output XML exists in outputs folder to reconstruct
        output_xml = os.path.join(OUTPUTS_DIR, f"results_{run_id}.xml")
        xml_exists = os.path.exists(output_xml)
        parsed = parse_flowdroid_xml(output_xml) if xml_exists else None

        dss_file = os.path.join(OUTPUTS_DIR, f"dss_{run_id}.json")
        dss_data = None
        if os.path.exists(dss_file):
            try:
                with open(dss_file, "r", encoding="utf-8") as f:
                    dss_data = json.load(f)
            except Exception:
                pass

        # Look in history
        for h in run_history:
            if h["run_id"] == run_id:
                return jsonify({
                    "run_id": run_id,
                    "apk_name": h["apk_name"],
                    "package_name": h.get("package_name"),
                    "apk_size_mb": h["apk_size_mb"],
                    "status": "completed",
                    "outcome": h["outcome"],
                    "elapsed_seconds": h["elapsed_seconds"],
                    "logs": ["[INFO] Full log not retained across server restart."],
                    "results": parsed,
                    "findings_count": h["findings_count"],
                    "xml_available": xml_exists,
                    "dss_data": dss_data
                })
        return jsonify({"error": "Run not found"}), 404

    return jsonify({
        "run_id": run["run_id"],
        "apk_name": run["apk_name"],
        "package_name": run.get("package_name"),
        "apk_size_mb": run["apk_size_mb"],
        "status": run["status"],
        "outcome": run["outcome"],
        "elapsed_seconds": run["elapsed_seconds"],
        "logs": run["logs"],
        "results": run["results"],
        "crash_snippet": run["crash_snippet"],
        "findings_count": run["findings_count"],
        "xml_available": run["xml_available"],
        "dss_data": run.get("dss_data")
    })


@app.route("/api/download/<run_id>/xml")
def download_xml(run_id):
    xml_path = os.path.join(OUTPUTS_DIR, f"results_{run_id}.xml")
    if not os.path.exists(xml_path):
        abort(404, description="XML results file not found.")

    run = runs_store.get(run_id)
    apk_base = (
        run["apk_name"].rsplit(".", 1)[0]
        if run and run.get("apk_name")
        else run_id
    )
    download_name = f"results_{apk_base}.xml"

    return send_file(
        xml_path,
        as_attachment=True,
        download_name=download_name,
        mimetype="application/xml"
    )


@app.route("/api/history")
def get_history():
    return jsonify(run_history)


@app.route("/api/history/clear", methods=["POST"])
def clear_history():
    global run_history
    run_history.clear()
    save_history([])
    try:
        for f in os.listdir(OUTPUTS_DIR):
            if not (active_run_id and active_run_id in f):
                try:
                    os.remove(os.path.join(OUTPUTS_DIR, f))
                except Exception:
                    pass
        for f in os.listdir(UPLOADS_DIR):
            if not (active_run_id and active_run_id in f):
                try:
                    os.remove(os.path.join(UPLOADS_DIR, f))
                except Exception:
                    pass
    except Exception as e:
        print(f"Notice: Cleanup on clear history: {e}")
    return jsonify({"success": True, "message": "History cleared successfully."})


@app.route("/api/extract-dss", methods=["POST"])
def extract_dss_endpoint():
    """
    Dedicated endpoint to extract Google Play Data Safety information
    from an uploaded APK file or an existing run_id.
    """
    if "apk_file" in request.files:
        file = request.files["apk_file"]
        if file and file.filename != "":
            safe_filename_val = secure_filename(file.filename) or "temp.apk"
            temp_name = f"temp_dss_{int(time.time())}_{uuid.uuid4().hex[:4]}_{safe_filename_val}"
            temp_path = os.path.join(UPLOADS_DIR, temp_name)
            file.save(temp_path)
            try:
                data = get_clean_dss_data(temp_path)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
            return jsonify(data)

    run_id = request.form.get("run_id") or request.args.get("run_id")
    if run_id and run_id in runs_store:
        apk_path = runs_store[run_id]["apk_path"]
        if os.path.exists(apk_path):
            data = get_clean_dss_data(apk_path)
            runs_store[run_id]["dss_data"] = data
            return jsonify(data)

    return jsonify({"error": "No APK file or valid run_id provided"}), 400


if __name__ == "__main__":
    print("=" * 60)
    print("AndroidGuard — Android Privacy Compliance & Taint Analyzer")
    print(f"FlowDroid JAR:      {FLOWDROID_JAR}")
    print(f"Platforms Dir:      {PLATFORMS_DIR}")
    print(f"Sources/Sinks File: {SOURCES_SINKS_FILE}")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False)
