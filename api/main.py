import os
import uuid
import asyncio
import subprocess
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import json
from pathlib import Path

app = FastAPI(title="AndroidGuard Analysis API")

BASE_DIR = Path(os.path.abspath(__file__)).parent.parent
UPLOADS_DIR = BASE_DIR / "runs" / "uploads"
REPORTS_DIR = BASE_DIR / "runs" / "reports"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Status store (in-memory for Iteration 1)
analysis_jobs = {}

import xml.etree.ElementTree as ET

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
    
    return {
        "apk_path": apk_path,
        "status": "success",
        "engine": "FlowDroid",
        "definitive_leaks_count": len(findings),
        "findings": findings
    }

def run_analysis(run_id: str, apk_path: str):
    out_json = REPORTS_DIR / f"{run_id}_report.json"
    
    # 1. Primary Engine: FlowDroid
    analysis_jobs[run_id] = {"status": "running", "stage": "FlowDroid Precision Analysis"}
    flowdroid_jar = BASE_DIR / "FlowDroid-2.15.1" / "soot-infoflow-cmd" / "target" / "soot-infoflow-cmd-jar-with-dependencies.jar"
    platforms_dir = "C:/Users/musab/AppData/Local/Android/Sdk/platforms"
    sinks_file = BASE_DIR / "datasets" / "SourcesAndSinks.txt"
    out_xml = REPORTS_DIR / f"{run_id}_flowdroid.xml"
    
    flowdroid_cmd = [
        "java", "-Xmx4g", "-jar", str(flowdroid_jar),
        "-a", apk_path,
        "-p", platforms_dir,
        "-s", str(sinks_file),
        "-o", str(out_xml)
    ]
    
    try:
        # Run FlowDroid with 2 minute timeout before graceful fallback
        process = subprocess.run(flowdroid_cmd, capture_output=True, text=True, timeout=120)
        if process.returncode == 0 and out_xml.exists():
            report_data = parse_flowdroid_xml(out_xml, apk_path)
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
            analysis_jobs[run_id] = {"status": "success", "engine": "FlowDroid", "report_path": str(out_json)}
            return
        else:
            analysis_jobs[run_id]["stage"] = f"FlowDroid inconclusive (code {process.returncode}). Switching to Fallback Analyzer..."
    except subprocess.TimeoutExpired:
        analysis_jobs[run_id]["stage"] = "FlowDroid timeout/OOM. Switching to Fallback Analyzer..."
    except Exception as e:
        analysis_jobs[run_id]["stage"] = f"FlowDroid error ({e}). Switching to Fallback Analyzer..."
        
    # 2. Secondary Engine: Fallback Heuristic Analyzer
    analysis_jobs[run_id]["stage"] = "Running Fallback Analyzer (Multi-threaded Smali AST Engine)..."
    fallback_cmd = [
        "python", "-m", "fallback_analyzer.cli",
        apk_path,
        "--out", str(out_json),
        "--workers", "4"
    ]
    
    try:
        process = subprocess.run(fallback_cmd, capture_output=True, text=True, cwd=str(BASE_DIR), timeout=900)
        if process.returncode == 0 and out_json.exists():
            analysis_jobs[run_id] = {"status": "success", "engine": "Fallback", "report_path": str(out_json)}
        else:
            err_msg = process.stderr.strip() if process.stderr else "Fallback analyzer execution error."
            analysis_jobs[run_id] = {"status": "failed", "error": err_msg}
    except Exception as e:
        analysis_jobs[run_id] = {"status": "failed", "error": str(e)}


@app.post("/api/v1/analyze")
async def analyze_apk(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="File must be an APK.")
    
    run_id = str(uuid.uuid4())
    apk_path = UPLOADS_DIR / f"{run_id}.apk"
    
    with open(apk_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    analysis_jobs[run_id] = {"status": "queued"}
    background_tasks.add_task(run_analysis, run_id, str(apk_path))
    
    return {"run_id": run_id, "message": "Analysis started."}

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
        
    # For now, return raw JSON if Fallback, or a summary if FlowDroid XML
    if report_path.endswith(".json"):
        with open(report_path, "r") as f:
            return json.load(f)
    else:
        # TODO: Parse FlowDroid XML and return JSON representation
        return {"message": "FlowDroid completed (XML output)", "file": report_path}

