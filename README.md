# 🛡️ AndroidGuard: Resilient Multi-Tier Static Analysis for Android Privacy Auditing

**Project Code:** F26-081-AndroidGuard  
**Institution:** FAST National University of Computer and Emerging Sciences (FAST-NUCES), Islamabad  
**Team Members:** Musab & Hussain  
**Current Milestone:** Mid-Evaluation Defense (Iteration 1: 100% Completed)  

---

## 📌 1. Project Context & High-Level Scope

### What is AndroidGuard?
AndroidGuard is an automated mobile application privacy auditing ecosystem designed to detect covert data exfiltration in Android applications. It operates on a **Client-Server Architecture**:
1. **Android Client (Mobile App):** Built with Kotlin & Jetpack Compose, running on the user's phone to select installed applications, compute on-device cryptographic hashes, initiate audits, display source-to-sink vulnerability traces, and export formal PDF reports.
2. **Analysis Server (FastAPI Daemon):** An asynchronous backend that manages execution pipelines, orchestrating heavy static taint analysis, failover recovery, and deterministic result caching.

### Scope Boundaries (Official Proposal Agreement)
- **Detection Only:** The system is strictly a **data leakage detection tool**, not an active kernel-level intrusion prevention or network blocking system.
- **Benign Store Applications:** The research scope is bounded to **benign applications available on the Google Play Store** (excluding obscure malware that evades app stores).
- **Zero-Crash Requirement:** The system must guarantee that security audits never terminate empty-handed or crash due to memory exhaustion.

---

## 🗺️ 2. The 4-Iteration Development Roadmap

The project is structured into **four sequential iterations** across FYP-I and FYP-II:

| Iteration | Focus Area | Status | Key Deliverables |
| :---: | :--- | :---: | :--- |
| **Iteration 1** | **Static Analysis** | **COMPLETED (100%)** *(Mid Goal)* | Dual-tier pipeline (FlowDroid 15GB + Smali AST Fallback), Axplorer permission mapping, SHA-256 caching (<0.5s), Jetpack Compose client, Analysis History, on-device PDF export. |
| **Iteration 2** | **Dynamic Analysis** | **NEXT MILESTONE** *(FYP-I Final)* | On-device local VPN (`VpnService`), per-UID target APK traffic isolation, continuous network monitoring, Disconnect.me & EasyPrivacy (EasyList) tracker domain matching, plaintext HTTP leak detection. |
| **Iteration 3** | **Policy Scrapping** | **PLANNED** *(FYP-II Phase 1)* | Privacy Policy extraction from developer URL, Google Play Store Data Safety Section (DSS) scraping, handling missing policies (direct leak evidence), structured JSON policy export. |
| **Iteration 4** | **LLM Policy Mapping & Scoring** | **PLANNED** *(FYP-II Final)* | LLM prompt pipeline ingesting static traces + dynamic traffic + policy text, differential flow verification, flagging undisclosed data harvesting, final objective security score & verdict. |

---

## 🔬 3. Iteration 1 Architecture & The Fallback Engine Innovation

```
                     ┌────────────────────────────────────────────────────────┐
                     │            📱 Android Client (Jetpack Compose)          │
                     │  - Selects installed APK & computes SHA-256 hash       │
                     │  - Checks cache via GET /api/v1/cache/check/{sha256}   │
                     └───────────────────────────┬────────────────────────────┘
                                                 │
                                 ┌───────────────┴───────────────┐
                     [Cache Hit: <0.5s]                          [Cache Miss: Upload APK]
                                 │                                               │
                                 ▼                                               ▼
                     ┌───────────────────────┐                   ┌───────────────────────────────┐
                     │ Instant JSON Report   │                   │   FastAPI Backend Worker      │
                     │ (No APK upload needed)│                   │   (Single-tenant task queue)  │
                     └───────────────────────┘                   └───────────────┬───────────────┘
                                                                                 │
                                                 ┌───────────────────────────────┴───────────────┐
                                                 ▼                                               ▼
                                      ┌───────────────────────┐                     ┌───────────────────────────┐
                                      │ Tier 1: FlowDroid     │                     │ Tier 2: Fallback Analyzer │
                                      │ - 15 GB Heap (-Xmx15g)│                     │ - Multi-core Smali AST    │
                                      │ - 30-min Timeout      │                     │ - O(N) memory complexity  │
                                      └──────────┬────────────┘                     │ - SuSi + Axplorer mapping │
                                                 │                                  │ - 3-Tier Proximity (L1-L3)│
                                      [On OOM / Timeout] ──────────────────────────►└─────────────┬─────────────┘
                                                                                                  │
                                                                                                  ▼
                                                                                    ┌───────────────────────────┐
                                                                                    │ Unified Findings JSON     │
                                                                                    │ (Zero crashes guaranteed) │
                                                                                    └───────────────────────────┘
```

### Why the Fallback Engine was Built:
- **The Problem:** FlowDroid is the academic gold standard for IFDS taint tracking, but on mid-to-large production APKs (e.g., YouTube, complex UI libraries, reactive frameworks), it suffers from **combinatorial callgraph explosion**. Even on 15GB+ servers, it crashes with Out-of-Memory (OOM) heap exceptions or hangs indefinitely ($>30$ minutes), resulting in a complete failure with **zero results**.
- **Our Solution:** A custom lightweight **Fallback Static Analyzer** (`fallback_analyzer/`):
  1. Decompiles bytecode into Smali via `apktool` using multi-core streaming ($\mathcal{O}(N)$ memory complexity, zero OOM risk).
  2. Ingests the **SuSi ML Dataset** (10,000+ verified Android Sources and Sinks).
  3. Uses the **Axplorer Dataset** to cross-reference identified sources against `AndroidManifest.xml` permissions to prune dead code.
  4. Links sources and sinks using a **3-Tier Proximity Model**:
     - *Level 1 (Intra-Procedural):* Same method block.
     - *Level 2 (Intra-Class):* Same class file.
     - *Level 3 (Component-Scoped):* Inner classes & asynchronous event listeners tied to an Activity.
     - *Level 4 Discarded:* Cross-component links are discarded to strictly suppress false alarms.

### Deterministic SHA-256 Caching Layer:
- The Android app computes the APK's SHA-256 hash locally before uploading.
- If previously analyzed, `GET /api/v1/cache/check/{sha256}` returns `cached: true`.
- The mobile client **aborts the 50MB APK upload completely** and loads the report in **under 0.5 seconds**.

### Strictly Factual Reporting (No Heuristic Grades):
- Early prototypes attempted heuristic 0-10 risk scores and letter grades (A+ to F).
- Per evaluation standards, speculative grades were completely removed.
- Reports (both plaintext text share and on-device PDF exports) strictly present **verifiable, definitive facts**: verified leak count, source/sink method signatures, and permission validation.

---

## 📂 4. Project Repository Structure

```
FYP/
├── android_app/                  # Native Android Client (Kotlin & Jetpack Compose)
│   ├── app/src/main/java/com/fyp/androidguard/
│   │   ├── MainActivity.kt       # Navigation, Installed Apps Catalog, History, Result View
│   │   ├── network/              # Retrofit & OkHttp (Dual-route: 10.0.2.2 & 127.0.0.1)
│   │   ├── services/             # AnalysisService (Background FGS), StateManager, HistoryManager
│   │   └── utils/                # CryptoUtils (SHA-256 streaming), ReportExporter (Canvas PDF generator)
│   └── build.gradle.kts
│
├── api/                          # FastAPI Backend Daemon
│   ├── main.py                   # REST API Orchestrator (FlowDroid -> Fallback Failover & Cache)
│   └── tests/                    # Automated unit tests for API endpoints
│
├── fallback_analyzer/            # Custom Multi-Core Smali AST Static Analyzer
│   ├── cli.py                    # Standalone CLI interface
│   ├── scanner.py                # Multi-process regex Smali stream scanner
│   ├── linker.py                 # 3-Tier structural proximity linker (L1, L2, L3)
│   ├── permission_mapper.py      # Axplorer permission mapping and manifest validator
│   ├── susi_loader.py            # SuSi source and sink loader
│   └── tests/                    # 15 unit tests covering parser, linker, and heuristics
│
├── datasets/                     # Scientific Threat Models & Permission Databases
│   ├── SourcesAndSinks.txt       # SuSi ML classified sources & sinks
│   ├── framework-map-25.txt      # Axplorer Android Framework API-to-permission mapping
│   └── sdk-map-25.txt            # Axplorer Android SDK API-to-permission mapping
│
├── FlowDroid-2.15.1/             # FlowDroid binary JAR distribution
├── runs/                         # Analysis runtime directories
│   ├── uploads/                  # Received APK files
│   ├── reports/                  # Generated JSON and XML reports
│   └── cache/                    # SHA-256 keyed instant JSON cache store
│
├── README.md                     # This file (Complete context & onboarding guide)
├── Architecture_Diagrams.md      # Mermaid horizontal architecture & sequence diagrams
├── FYP_Defense_Guide.md          # Technical defense Q&A guide
└── AndroidGuard_Mid_Defense_Presentation.pptx # Widescreen 16:9 presentation slide deck
```

---

## 🚀 5. Quick-Start & Execution Guide

Follow these steps on any new computer or development environment to run the system:

### Step 1: Environment Prerequisites
Verify your environment has Python 3.10+, Java JDK 11+, and Android SDK installed:
```powershell
python --version   # Python 3.10 or higher
java -version     # JDK 11, 17, or 21+ (Required by FlowDroid & Apktool)
adb version       # Android Debug Bridge
```

### Step 2: Install Python Dependencies
```powershell
pip install fastapi uvicorn requests pytest python-multipart psutil
pip install -r fallback_analyzer/requirements.txt
```

### Step 3: Run the Automated Unit Test Suites
Verify that both the backend API and the fallback engine pass 100% of tests:
```powershell
# 1. Test Backend API endpoints
pytest api/tests/

# 2. Test Fallback Analyzer parser & linker
pytest fallback_analyzer/tests/
```
*(Both suites must report 100% green passing status).*

### Step 4: Start the FastAPI Backend Server
Run the backend daemon bound to all network interfaces on port 8080:
```powershell
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
```
- Test in your browser: `http://127.0.0.1:8080/docs` (Swagger UI).

### Step 5: Configure Android Reverse Tunnel (Crucial for Emulator / USB Device)
Open a second terminal window and forward port 8080 to the connected emulator or device:
```powershell
adb reverse tcp:8080 tcp:8080
```
*(Note: The Android app is already pre-configured to use `http://10.0.2.2:8080/` by default, but `adb reverse` provides a dual-route guarantee).*

### Step 6: Launch the Android Mobile App
Open `android_app/` in Android Studio:
1. Select your emulator (e.g., Pixel / Medium Phone API 34+).
2. Press **Run (`Shift + F10`)** or build via command line:
   ```powershell
   cd android_app
   ./gradlew assembleDebug
   adb install -r app/build/outputs/apk/debug/app-debug.apk
   ```
3. Open the **AndroidGuard** app on the device.
4. Tap **Analyze** on any application:
   - Repeat scans hit the cache and load in **< 0.5 seconds**.
   - Tap **View Report** to open the findings screen.
   - Tap **Export PDF** to generate an on-device audit report.

---

## 🛡️ 6. Key Rules & Guardrails for Antigravity AI Assistants

When assisting in future sessions on this repository, strictly abide by these project rules:

1. **4 Iterations Roadmap:** The project has exactly 4 iterations (Static $\rightarrow$ Dynamic $\rightarrow$ Policy $\rightarrow$ LLM). Do not alter this scope.
2. **Team Members:** The team consists of exactly **Musab** and **Hussain** (2 members).
3. **Zero-Red-Build Rule:** Never commit or alter code that breaks `pytest api/tests/` or `pytest fallback_analyzer/tests/`.
4. **No Speculative Risk Scores:** Do not reintroduce letter grades (A+ to F) or numerical risk scores (0.0 to 10.0). Focus strictly on factual, definitive leak flows and source-to-sink method traces.
5. **Always Keep Dual-Engine Failover:** FlowDroid must remain Tier 1 with an automated fallback to the Fallback AST Analyzer on OOM or timeout.
6. **Preserve SHA-256 Cache:** Never bypass the pre-upload cryptographic cache check; it is vital for system performance.
