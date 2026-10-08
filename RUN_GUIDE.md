# 🚀 Fallback Analyzer — Setup & Verification Guide

This guide contains all the commands and verification steps to ensure the Fallback Static Analyzer runs on your new laptop.

---

## 📋 Prerequisites Checklist

Before executing the analyzer, verify that your environment has **Python** and **Java** installed and added to your system `PATH`.

### Step 1: Check Python & Java Installations

Open PowerShell or Command Prompt inside your project directory (`c:\Users\Hussain Anees\OneDrive\Documents\FYP`) and run:

```powershell
python --version
java -version
```

- **Python:** Should be Python 3.10 or higher.
- **Java:** Should output Java Runtime / JDK (Java 11, 17, or 21+). Required by `apktool.jar`.

> **Note:** If `java -version` returns `'java' is not recognized`, install the Java JDK and ensure "Add to PATH" is selected.

---

## 📦 Step 2: Install Python Dependencies

Install the required testing and analysis packages:

```powershell
python -m pip install --upgrade pip
pip install pytest
```

---

## 🧪 Step 3: Run the Automated Unit Tests

Verify that your local code files, parser, linker, and scoring rules are functioning properly:

```powershell
python -m pytest fallback_analyzer/tests/
```

**Expected Result:**
```text
============================= 15 passed in 0.XXs ==============================
```
If all 15 tests pass, the fallback analyzer logic is intact and ready.

---

## 🔍 Step 4: Run the Analyzer on an APK

Make sure you are in the root `FYP` directory:
```powershell
cd "c:\Users\Hussain Anees\OneDrive\Documents\FYP"
```

### Option A: Quick Benchmark Test (~3 seconds)
Run against the small benchmark test app (`DirectLeak1.apk`):

```powershell
python -m fallback_analyzer.cli DirectLeak1.apk --workers 4
```

---

### Option B: Real-World Large APK Test (~60 seconds)
Run against the 80MB real-world app:

```powershell
python -m fallback_analyzer.cli "Quran, 16 Lines, Colored.apk" --workers 4
```

*(Always wrap filenames containing commas or spaces in quotes `""`)*

---

## 📊 Step 5: View the Analysis Results

### View the raw JSON report:
```powershell
Get-Content report.json -TotalCount 50
```

### View a quick summary of the top leaks:
```powershell
python summarize.py
```

---

## 🛠️ Command Reference & Flags Cheat Sheet

| Command / Flag | Purpose | Default Value |
|---|---|---|
| `python -m fallback_analyzer.cli <apk>` | Basic scan command | *Required* |
| `--workers N` | Number of CPU cores used in parallel | `1` |
| `--out <filename.json>` | Output file name and path | `report.json` |
| `--susi <path>` | Sources/Sinks definition file | `datasets/SourcesAndSinks.txt` |
| `--axplorer-framework <path>` | Axplorer framework permission map | `datasets/framework-map-25.txt` |
| `--axplorer-sdk <path>` | Axplorer SDK permission map | `datasets/sdk-map-25.txt` |
