import os
import uuid
import asyncio
import subprocess
import hashlib
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

app = FastAPI(title="AndroidGuard Analysis API")

BASE_DIR = Path(os.path.abspath(__file__)).parent.parent
UPLOADS_DIR = BASE_DIR / "runs" / "uploads"
REPORTS_DIR = BASE_DIR / "runs" / "reports"
CACHE_DIR = BASE_DIR / "runs" / "cache"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Status store (in-memory)
analysis_jobs = {}

def calculate_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def compute_risk_assessment(definitive_leaks_count: int, findings: list) -> dict:
    if definitive_leaks_count == 0:
        return {
            "score": 0.5,
            "grade": "A+",
            "severity": "CLEAN",
            "recommendation": "No dangerous taint leaks detected. Safe for deployment."
        }
    elif definitive_leaks_count <= 5:
        return {
            "score": 3.2,
            "grade": "B",
            "severity": "LOW",
            "recommendation": "Minor data propagation detected. Review sensitive method calls."
        }
    elif definitive_leaks_count <= 25:
        return {
            "score": 5.8,
            "grade": "C",
            "severity": "MEDIUM",
            "recommendation": "Multiple unconstrained data flows found. Inspect network & log sinks."
        }
    elif definitive_leaks_count <= 80:
        return {
            "score": 7.9,
            "grade": "D",
            "severity": "HIGH",
            "recommendation": "Heavy data exfiltration observed across third-party SDKs."
        }
    else:
        return {
            "score": 9.6,
            "grade": "F",
            "severity": "CRITICAL",
            "recommendation": "Severe security compromise. Extensive sensitive sources routed to sinks."
        }

def parse_flowdroid_xml(xml_path: Path, apk_path: str) -> dict:
    findings = []
    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
        for result in root.iter("Result"):
            sink_elem = result.find("Sink")
            sink_stmt = sink_elem.attrib.get("Statement", "") if sink_elem is not None else ""
            sink_method = sink_elem.attrib.get("Method", "") if sink_elem is not None else ""
            
            for src_elem in result.iter("Source"):
                src_stmt = src_elem.attrib.get("Statement", "")
                src_method = src_elem.attrib.get("Method", "")
                findings.append({
                    "source": {
                        "class": src_method.split(":")[0].strip("< ") if ":" in src_method else src_method,
                        "method": src_method,
                        "target_signature": src_stmt,
                        "category": "TAINT_SOURCE"
                    },
                    "sink": {
                        "class": sink_method.split(":")[0].strip("< ") if ":" in sink_method else sink_method,
                        "method": sink_method,
                        "target_signature": sink_stmt,
                        "category": "TAINT_SINK"
                    },
                    "confidence": "HIGH",
                    "link_level": "FlowDroid TaintFlow"
                })
    except Exception:
        pass
    
    leaks_count = len(findings)
    return {
        "apk_path": apk_path,
        "status": "success",
        "engine": "FlowDroid",
        "definitive_leaks_count": leaks_count,
        "risk_assessment": compute_risk_assessment(leaks_count, findings),
        "findings": findings
    }

def run_analysis(run_id: str, apk_path: str, sha256: str):
    out_json = REPORTS_DIR / f"{run_id}_report.json"
    cache_json = CACHE_DIR / f"{sha256}.json"
    
    # 1. Primary Engine: FlowDroid
    analysis_jobs[run_id] = {
        "status": "running",
        "stage": "Running Primary Engine: FlowDroid Precision Analysis (up to 30 mins)...",
        "sha256": sha256
    }
    flowdroid_jar = BASE_DIR / "FlowDroid-2.15.1" / "soot-infoflow-cmd" / "target" / "soot-infoflow-cmd-jar-with-dependencies.jar"
    platforms_dir = "C:/Users/musab/AppData/Local/Android/Sdk/platforms"
    sinks_file = BASE_DIR / "datasets" / "SourcesAndSinks.txt"
    out_xml = REPORTS_DIR / f"{run_id}_flowdroid.xml"
    
    flowdroid_cmd = [
        "java", "-Xmx15g", "-jar", str(flowdroid_jar),
        "-a", apk_path,
        "-p", platforms_dir,
        "-s", str(sinks_file),
        "-o", str(out_xml)
    ]
    
    print(f"[*] Starting FlowDroid precision analysis for job {run_id}...")
    try:
        # Run FlowDroid with 30 minute timeout (1800 seconds)
        process = subprocess.run(flowdroid_cmd, capture_output=True, text=True, timeout=1800)
        if process.returncode == 0 and out_xml.exists() and out_xml.stat().st_size > 0:
            print(f"[+] FlowDroid completed successfully for job {run_id}!")
            report_data = parse_flowdroid_xml(out_xml, apk_path)
            report_data["sha256"] = sha256
            
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
            with open(cache_json, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
                
            analysis_jobs[run_id] = {
                "status": "success",
                "engine": "FlowDroid",
                "stage": "FlowDroid Completed Successfully",
                "sha256": sha256,
                "report_path": str(out_json)
            }
            return
        else:
            err_reason = f"code {process.returncode}" if process.returncode != 0 else "empty/missing XML output"
            print(f"[-] FlowDroid failed for job {run_id} ({err_reason}).")
            if process.stderr:
                print(f"    FlowDroid stderr: {process.stderr[:300]}")
            analysis_jobs[run_id]["stage"] = f"FlowDroid failed ({err_reason}). Switching to Fallback Analyzer..."
    except subprocess.TimeoutExpired:
        print(f"[-] FlowDroid timed out (30m) for job {run_id}.")
        analysis_jobs[run_id]["stage"] = "FlowDroid timed out (30m). Switching to Fallback Analyzer..."
    except Exception as e:
        print(f"[-] FlowDroid exception for job {run_id}: {e}")
        analysis_jobs[run_id]["stage"] = f"FlowDroid error ({e}). Switching to Fallback Analyzer..."
        
    # 2. Secondary Engine: Fallback Heuristic Analyzer (Only runs if FlowDroid failed above)
    analysis_jobs[run_id]["stage"] = "Running Fallback Analyzer (Multi-threaded Smali AST Engine)..."
    print(f"[*] Engaging Fallback Analyzer for job {run_id}...")
    fallback_cmd = [
        "python", "-m", "fallback_analyzer.cli",
        apk_path,
        "--out", str(out_json),
        "--workers", "4"
    ]
    
    try:
        process = subprocess.run(fallback_cmd, capture_output=True, text=True, cwd=str(BASE_DIR), timeout=1800)
        if process.returncode == 0 and out_json.exists():
            # Load Fallback JSON and augment with risk assessment and sha256
            try:
                with open(out_json, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                leaks_count = report_data.get("definitive_leaks_count", 0)
                findings = report_data.get("findings", [])
                report_data["engine"] = "Fallback"
                report_data["sha256"] = sha256
                report_data["risk_assessment"] = compute_risk_assessment(leaks_count, findings)
                
                with open(out_json, "w", encoding="utf-8") as f:
                    json.dump(report_data, f, indent=2)
                with open(cache_json, "w", encoding="utf-8") as f:
                    json.dump(report_data, f, indent=2)
            except Exception:
                pass
                
            analysis_jobs[run_id] = {
                "status": "success",
                "engine": "Fallback",
                "stage": "Fallback Analyzer Completed Successfully",
                "sha256": sha256,
                "report_path": str(out_json)
            }
        else:
            err_msg = process.stderr.strip() if process.stderr else f"Fallback analyzer exited with code {process.returncode}."
            analysis_jobs[run_id] = {"status": "failed", "error": err_msg}
    except subprocess.TimeoutExpired:
        analysis_jobs[run_id] = {"status": "failed", "error": "Fallback Analyzer timed out (30m limit reached)."}
    except Exception as e:
        analysis_jobs[run_id] = {"status": "failed", "error": str(e)}


@app.get("/api/v1/cache/check/{sha256}")
def check_cache(sha256: str):
    cache_json = CACHE_DIR / f"{sha256}.json"
    if cache_json.exists():
        try:
            with open(cache_json, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            # Create a virtual completed run_id so client can query or read it
            cached_run_id = str(uuid.uuid4())
            out_json = REPORTS_DIR / f"{cached_run_id}_report.json"
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(cached_data, f, indent=2)
                
            analysis_jobs[cached_run_id] = {
                "status": "success",
                "engine": cached_data.get("engine", "Cache"),
                "stage": "Instantly retrieved from Cache",
                "cached": True,
                "sha256": sha256,
                "report_path": str(out_json)
            }
            return {
                "cached": True,
                "run_id": cached_run_id,
                "message": "Found in cache! No upload required.",
                "report": cached_data
            }
        except Exception as e:
            return {"cached": False, "error": str(e)}
    return {"cached": False}


@app.post("/api/v1/analyze")
async def analyze_apk(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="File must be an APK.")
    
    run_id = str(uuid.uuid4())
    apk_path = UPLOADS_DIR / f"{run_id}.apk"
    
    with open(apk_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    # Calculate SHA-256
    sha256 = calculate_sha256(apk_path)
    cache_json = CACHE_DIR / f"{sha256}.json"
    
    # Check cache hit on upload
    if cache_json.exists():
        try:
            with open(cache_json, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            out_json = REPORTS_DIR / f"{run_id}_report.json"
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(cached_data, f, indent=2)
                
            analysis_jobs[run_id] = {
                "status": "success",
                "engine": cached_data.get("engine", "Cache"),
                "stage": "Loaded from SHA-256 Cache (Instant)",
                "cached": True,
                "sha256": sha256,
                "report_path": str(out_json)
            }
            return {
                "run_id": run_id,
                "cached": True,
                "message": "Analysis loaded instantly from cache!"
            }
        except Exception:
            pass
            
    # Cache Miss -> Queue background execution
    analysis_jobs[run_id] = {"status": "queued", "sha256": sha256}
    background_tasks.add_task(run_analysis, run_id, str(apk_path), sha256)
    
    return {"run_id": run_id, "cached": False, "message": "Analysis started."}

@app.get("/api/v1/status/{run_id}")
def get_status(run_id: str):
    if run_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return analysis_jobs[run_id]

@app.get("/api/v1/report/{run_id}")
def get_report(run_id: str):
    if run_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Run ID not found")
    
    job = analysis_jobs[run_id]
    if job.get("status") != "success":
        raise HTTPException(status_code=400, detail="Report not ready or analysis failed")
        
    report_path = job.get("report_path")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report file missing")
        
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)
