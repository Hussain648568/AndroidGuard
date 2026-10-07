# FlowDroid APK Taint Analyzer Web App

A lightweight local web application built with Python Flask and a single HTML page (vanilla JavaScript & CSS) for running [FlowDroid](https://github.com/secure-software-engineering/FlowDroid) static taint analysis on Android APK files.

---

## Features

1. **Local File Picker & Drag-and-Drop**:
   - Easily choose or drop `.apk` files.
   - Shows file name and size before running.
2. **Execution Controls**:
   - Configurable timeout in seconds (default: 1800s / 30 mins).
   - Single-tenant execution guard: prevents accidental parallel runs that could starve system RAM.
3. **Live Console & Log Streaming**:
   - Real-time streaming of FlowDroid's stdout and stderr in a dark monospace terminal box.
   - Live elapsed-time counter with automatic scrolling.
4. **Reliable Windows Process Management**:
   - Subprocess tree termination using `psutil` and Windows `taskkill /F /T` fallback upon timeout, ensuring no orphaned Java processes are left in the background.
5. **Accurate Outcome Determination**:
   - `TIMEOUT`: when the run hits the user-specified wall-clock timeout.
   - `CRASH`: when the process exits with an error code or fails to produce XML, with the last ~30 lines of log displayed in a crash box.
   - `PARTIAL: <state>`: when FlowDroid completes partially (e.g. `DataFlowOutOfMemory`, `DataFlowTimeout`).
   - `SUCCESS`: when FlowDroid completes normally (`TerminationState="Success"`).
6. **XML Results Parsing & Display**:
   - Performance metrics cards: Callgraph construction time, Taint propagation time, Path reconstruction time, Total runtime, Peak memory, Sources, and Sinks.
   - Data flow findings table: Source (statement & method) ➔ Sink (statement & method).
   - Real-time search/filter bar for findings.
   - "Download raw XML" button for exporting FlowDroid's output.
7. **Session Run History**:
   - Records past runs in this session.
   - Allows clicking "View Results" on any past run to inspect its metrics, findings table, and terminal logs without re-analyzing.

---

## Quick Start

### 1. Requirements
- Python 3.10+
- Java JDK 11+ (`java -version`)
- Flask (`pip install Flask psutil`)

### 2. Run the App
From the project root directory (`POC`):
```bash
python app.py
```
Or with Git Bash / PowerShell:
```powershell
python app.py
```

### 3. Open in Browser
Open:
```
http://127.0.0.1:5000
```

---

## Configuration

Paths are pre-configured to default to the existing FlowDroid setup in this repository:
- **FlowDroid JAR**: `flowdroid_poc/FlowDroid/soot-infoflow-cmd/target/soot-infoflow-cmd-jar-with-dependencies.jar`
- **Android Platforms**: `flowdroid_poc/android-platforms`
- **Sources & Sinks**: `flowdroid_poc/FlowDroid/soot-infoflow-android/SourcesAndSinks.txt`

To override any path, set environment variables in your shell or copy `.env.example`:
```bash
export FLOWDROID_JAR="path/to/soot-infoflow-cmd-jar-with-dependencies.jar"
export PLATFORMS_DIR="path/to/android-platforms"
export SOURCES_SINKS_FILE="path/to/SourcesAndSinks.txt"
export DEFAULT_TIMEOUT=1800
python app.py
```

---

## Running Automated Tests

Run the test suite verifying the endpoints, timeout handling, XML parsing, and crash categorization:
```bash
python test_app.py
```
