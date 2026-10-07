document.addEventListener('DOMContentLoaded', () => {
    // -----------------------------------------------------------------------
    // MODULE SWITCHER ELEMENTS & STATE (2 MODULES: DSS & FLOWDROID)
    // -----------------------------------------------------------------------
    const tabDss = document.getElementById('tabDss');
    const tabFlowdroid = document.getElementById('tabFlowdroid');

    const viewDss = document.getElementById('viewDss');
    const viewFlowdroid = document.getElementById('viewFlowdroid');
    const activeModuleIndicator = document.getElementById('activeModuleIndicator');

    const tabs = [
        { id: 'dss', tabEl: tabDss, viewEl: viewDss, label: 'Play Store Data Safety' },
        { id: 'flowdroid', tabEl: tabFlowdroid, viewEl: viewFlowdroid, label: 'FlowDroid Taint Analysis' }
    ];

    let currentModule = 'dss';

    function switchModule(targetId) {
        const found = tabs.find(t => t.id === targetId);
        if (!found) return;

        currentModule = targetId;

        // Update tabs
        tabs.forEach(t => {
            if (t.id === targetId) {
                t.tabEl.classList.add('active');
                const pill = t.tabEl.querySelector('.module-active-pill');
                if (pill) pill.textContent = '● Active Interface';
                t.viewEl.classList.remove('hidden');
                t.viewEl.classList.add('active');
            } else {
                t.tabEl.classList.remove('active');
                const pill = t.tabEl.querySelector('.module-active-pill');
                if (pill) pill.textContent = '○ Click to switch';
                t.viewEl.classList.add('hidden');
                t.viewEl.classList.remove('active');
            }
        });

        if (activeModuleIndicator) {
            activeModuleIndicator.textContent = `Active: ${found.label}`;
            if (targetId === 'dss') {
                activeModuleIndicator.className = 'info-pill pill-green';
            } else {
                activeModuleIndicator.className = 'info-pill';
            }
        }

        // Update URL hash
        try {
            history.replaceState(null, null, '#' + targetId);
        } catch (e) {}
    }

    tabs.forEach(t => {
        if (t.tabEl) {
            t.tabEl.addEventListener('click', () => switchModule(t.id));
            t.tabEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    switchModule(t.id);
                }
            });
        }
    });

    // Check initial hash
    if (window.location.hash) {
        const hashId = window.location.hash.replace('#', '').toLowerCase();
        if (['dss', 'flowdroid'].includes(hashId)) {
            switchModule(hashId);
        }
    }

    // Config Drawer Toggle
    const configToggleBtn = document.getElementById('configToggleBtn');
    const configInfoCard = document.getElementById('configInfoCard');
    if (configToggleBtn && configInfoCard) {
        configToggleBtn.addEventListener('click', () => {
            configInfoCard.classList.toggle('hidden');
        });
    }

    // -----------------------------------------------------------------------
    // SYNCHRONIZED FILE SELECTION (SHARED STATE ACROSS ALL VIEWS)
    // -----------------------------------------------------------------------
    let currentFile = null;

    const fileInputs = [
        document.getElementById('dssFileInput'),
        document.getElementById('fdFileInput')
    ].filter(Boolean);

    const dropzones = [
        document.getElementById('dssDropzone'),
        document.getElementById('fdDropzone')
    ].filter(Boolean);

    const btnExtractDss = document.getElementById('btnDssExtractAction');
    const btnRunFlowdroid = document.getElementById('btnRunFlowdroidAction');

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    }

    function handleFileSelection(file) {
        if (!file) return;
        if (!file.name.toLowerCase().endsWith('.apk')) {
            alert('Please select a valid Android APK (.apk) file.');
            resetFileSelection();
            return;
        }

        currentFile = file;
        const formattedSize = formatFileSize(file.size);

        // Update all file display labels
        document.querySelectorAll('.file-name-sync').forEach(el => el.textContent = file.name);
        document.querySelectorAll('.file-size-sync').forEach(el => el.textContent = formattedSize);
        document.querySelectorAll('.prompt-sync').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('.details-sync').forEach(el => el.classList.remove('hidden'));

        // Enable action buttons
        if (btnExtractDss) btnExtractDss.disabled = false;
        if (btnRunFlowdroid) btnRunFlowdroid.disabled = false;
    }

    function resetFileSelection() {
        currentFile = null;
        fileInputs.forEach(input => { input.value = ''; });

        document.querySelectorAll('.prompt-sync').forEach(el => el.classList.remove('hidden'));
        document.querySelectorAll('.details-sync').forEach(el => el.classList.add('hidden'));

        if (btnExtractDss) btnExtractDss.disabled = true;
        if (btnRunFlowdroid) btnRunFlowdroid.disabled = true;
    }

    // Attach listeners to all file inputs & dropzones
    fileInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                handleFileSelection(e.target.files[0]);
            }
        });
    });

    dropzones.forEach(dz => {
        dz.addEventListener('dragover', (e) => {
            e.preventDefault();
            dz.classList.add('dragover');
        });
        dz.addEventListener('dragleave', () => {
            dz.classList.remove('dragover');
        });
        dz.addEventListener('drop', (e) => {
            e.preventDefault();
            dz.classList.remove('dragover');
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleFileSelection(e.dataTransfer.files[0]);
            }
        });
    });

    // Clear file buttons
    document.querySelectorAll('.btn-clear-file').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            resetFileSelection();
        });
    });

    // -----------------------------------------------------------------------
    // DSS CARD POPULATION HELPER (POWERS BOTH VIEW 1 & VIEW 3)
    // -----------------------------------------------------------------------
    function populateDssCard(dssData, prefix) {
        const dssCardSection = document.getElementById(prefix === 'v1' ? 'dssStandaloneCard' : null);
        const statusBadge = document.getElementById(`${prefix}DssStatusBadge`);
        const appIcon = document.getElementById(`${prefix}DssAppIcon`);
        const appName = document.getElementById(`${prefix}DssAppName`);
        const appDev = document.getElementById(`${prefix}DssAppDeveloper`);
        const pkgTag = document.getElementById(`${prefix}DssPackageName`);
        const privLink = document.getElementById(`${prefix}DssPrivacyLink`);

        const badgeEnc = document.getElementById(`${prefix}BadgeEncryption`);
        const iconEnc = document.getElementById(`${prefix}IconEncryption`);
        const textEnc = document.getElementById(`${prefix}TextEncryption`);

        const badgeDel = document.getElementById(`${prefix}BadgeDeletion`);
        const iconDel = document.getElementById(`${prefix}IconDeletion`);
        const textDel = document.getElementById(`${prefix}TextDeletion`);

        const collList = document.getElementById(`${prefix}DssCollectedList`);
        const sharedList = document.getElementById(`${prefix}DssSharedList`);

        const unlistedNotice = document.getElementById(`${prefix}DssUnlistedNotice`);
        const unlistedText = document.getElementById(`${prefix}DssUnlistedText`);

        if (dssCardSection) dssCardSection.classList.remove('hidden');

        if (!dssData) {
            if (unlistedNotice) unlistedNotice.classList.remove('hidden');
            if (unlistedText) unlistedText.textContent = 'No Data Safety declaration available for this APK.';
            return;
        }

        // Handle error / unlisted package
        if (dssData.error) {
            if (unlistedNotice) unlistedNotice.classList.remove('hidden');
            if (unlistedText) unlistedText.textContent = dssData.error;
            if (statusBadge) {
                statusBadge.textContent = 'Unlisted on Play Store';
                statusBadge.style.background = 'rgba(148, 163, 184, 0.15)';
                statusBadge.style.color = '#94a3b8';
            }
            if (appName) appName.textContent = dssData.package_name || 'Unlisted Package';
            if (appDev) appDev.textContent = 'Developer: Unknown (Test / Benchmark APK)';
            if (pkgTag) pkgTag.textContent = dssData.package_name || 'N/A';
            if (privLink) privLink.style.display = 'none';
            if (appIcon) {
                appIcon.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%2364748b"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>';
            }
            if (badgeEnc && textEnc && iconEnc) {
                badgeEnc.className = 'security-badge badge-warning-shield';
                iconEnc.textContent = '⚠️';
                textEnc.textContent = 'Unverified (Unlisted)';
            }
            if (badgeDel && textDel && iconDel) {
                badgeDel.className = 'security-badge badge-warning-shield';
                iconDel.textContent = '⚠️';
                textDel.textContent = 'Unverified (Unlisted)';
            }
            if (collList) collList.innerHTML = '<li class="text-muted"><span style="color:#94a3b8;">—</span> No Play Store declaration found</li>';
            if (sharedList) sharedList.innerHTML = '<li class="text-muted"><span style="color:#94a3b8;">—</span> No Play Store declaration found</li>';
            return;
        }

        // Valid Play Store Data
        if (unlistedNotice) unlistedNotice.classList.add('hidden');

        if (statusBadge) {
            statusBadge.textContent = 'Play Store Declared';
            statusBadge.style.background = 'rgba(16, 185, 129, 0.15)';
            statusBadge.style.color = '#10b981';
        }

        const title = dssData.app_name || (dssData.app_info && dssData.app_info.name) || dssData.package_name || 'Android Application';
        const developer = dssData.developer || (dssData.app_info && dssData.app_info.developer) || 'Unknown Developer';
        const iconUrl = dssData.icon_url || (dssData.app_info && dssData.app_info.icon_url);
        const policyUrl = dssData.privacy_policy_link || (dssData.app_info && dssData.app_info.privacy_policy_link);

        if (appName) appName.textContent = title;
        if (appDev) appDev.textContent = `Developer: ${developer}`;
        if (pkgTag) pkgTag.textContent = dssData.package_name || 'N/A';

        if (appIcon) {
            if (iconUrl) {
                appIcon.src = iconUrl;
                appIcon.style.display = 'block';
            } else {
                appIcon.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%2310b981"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/></svg>';
            }
        }

        if (privLink) {
            if (policyUrl && policyUrl !== '#') {
                privLink.href = policyUrl;
                privLink.style.display = 'inline-flex';
            } else {
                privLink.style.display = 'none';
            }
        }

        // Encryption Badge
        const isEncrypted = dssData.is_data_encrypted === true || (dssData.data_safety_summary && String(dssData.data_safety_summary.is_data_encrypted).toLowerCase().includes('yes'));
        if (badgeEnc && textEnc && iconEnc) {
            if (isEncrypted) {
                badgeEnc.className = 'security-badge badge-green-shield';
                iconEnc.textContent = '🛡️';
                textEnc.textContent = 'Yes, in transit';
            } else {
                badgeEnc.className = 'security-badge badge-warning-shield';
                iconEnc.textContent = '⚠️';
                textEnc.textContent = 'Not declared or no';
            }
        }

        // Deletion Badge
        const isDeletion = dssData.is_data_deletion_supported === true || (dssData.data_safety_summary && String(dssData.data_safety_summary.can_request_deletion).toLowerCase().includes('yes'));
        if (badgeDel && textDel && iconDel) {
            if (isDeletion) {
                badgeDel.className = 'security-badge badge-green-shield';
                iconDel.textContent = '🗑️';
                textDel.textContent = 'Request supported';
            } else {
                badgeDel.className = 'security-badge badge-warning-shield';
                iconDel.textContent = '⚠️';
                textDel.textContent = 'Not declared or no';
            }
        }

        // Data Collected
        const collectedItems = dssData.data_collected || (dssData.data_safety_summary && dssData.data_safety_summary.data_collected) || [];
        if (collList) {
            collList.innerHTML = '';
            const validItems = collectedItems.filter(i => i && !i.toLowerCase().includes('no data collection declared'));
            if (validItems.length > 0) {
                validItems.forEach(item => {
                    const li = document.createElement('li');
                    li.innerHTML = `<span style="color: #10b981; font-weight: bold; margin-right: 6px;">●</span> <span>${escapeHtml(item)}</span>`;
                    collList.appendChild(li);
                });
            } else {
                collList.innerHTML = '<li class="text-muted"><span style="color:#10b981;">✓</span> No Data Collection Declared</li>';
            }
        }

        // Data Shared
        const sharedItems = dssData.data_shared || (dssData.data_safety_summary && dssData.data_safety_summary.data_shared_with_third_parties) || [];
        if (sharedList) {
            sharedList.innerHTML = '';
            const validItems = sharedItems.filter(i => i && !i.toLowerCase().includes('no third-party sharing declared'));
            if (validItems.length > 0) {
                validItems.forEach(item => {
                    const li = document.createElement('li');
                    li.innerHTML = `<span style="color: #3b82f6; font-weight: bold; margin-right: 6px;">●</span> <span>${escapeHtml(item)}</span>`;
                    sharedList.appendChild(li);
                });
            } else {
                sharedList.innerHTML = '<li class="text-muted"><span style="color:#10b981;">✓</span> No Third-Party Sharing Declared</li>';
            }
        }
    }

    // -----------------------------------------------------------------------
    // VIEW 1: DATA SAFETY EXTRACTOR EXECUTION
    // -----------------------------------------------------------------------
    const dssLoadingNotice = document.getElementById('dssLoadingNotice');

    if (btnExtractDss) {
        btnExtractDss.addEventListener('click', async () => {
            if (!currentFile) {
                alert('Please select an APK file first.');
                return;
            }

            btnExtractDss.disabled = true;
            if (dssLoadingNotice) dssLoadingNotice.classList.remove('hidden');

            const formData = new FormData();
            formData.append('apk_file', currentFile);

            try {
                const resp = await fetch('/api/extract-dss', {
                    method: 'POST',
                    body: formData
                });

                const data = await resp.json();
                if (!resp.ok) {
                    throw new Error(data.error || `Server responded with ${resp.status}`);
                }

                populateDssCard(data, 'v1');

                const dssCard = document.getElementById('dssStandaloneCard');
                if (dssCard) {
                    dssCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            } catch (err) {
                alert(`Data Safety Extraction Error: ${err.message}`);
            } finally {
                btnExtractDss.disabled = false;
                if (dssLoadingNotice) dssLoadingNotice.classList.add('hidden');
            }
        });
    }

    // -----------------------------------------------------------------------
    // TIMERS & LOG APENDERS
    // -----------------------------------------------------------------------
    let activeTimer = null;
    let timerStartTime = null;

    function startTimer(elapsedEl) {
        if (!elapsedEl) return;
        timerStartTime = Date.now();
        elapsedEl.textContent = '0.0s';
        if (activeTimer) clearInterval(activeTimer);

        activeTimer = setInterval(() => {
            if (timerStartTime) {
                const secs = ((Date.now() - timerStartTime) / 1000).toFixed(1);
                elapsedEl.textContent = `${secs}s`;
            }
        }, 200);
    }

    function stopTimer(elapsedEl, finalSecs) {
        if (activeTimer) {
            clearInterval(activeTimer);
            activeTimer = null;
        }
        if (elapsedEl && finalSecs !== undefined && finalSecs !== null) {
            elapsedEl.textContent = `${finalSecs}s`;
        }
    }

    function setLiveBadge(badgeEl, status) {
        if (!badgeEl) return;
        badgeEl.className = 'status-badge';
        if (status === 'running') {
            badgeEl.classList.add('badge-running');
            badgeEl.textContent = '● RUNNING...';
        } else if (status === 'completed') {
            badgeEl.classList.add('badge-success');
            badgeEl.textContent = 'FINISHED';
        } else {
            badgeEl.classList.add('badge-idle');
            badgeEl.textContent = 'IDLE';
        }
    }

    function setOutcomeBadge(badgeEl, outcome) {
        if (!badgeEl) return;
        badgeEl.className = 'outcome-badge';

        if (!outcome) {
            badgeEl.classList.add('badge-idle');
            badgeEl.textContent = 'IDLE';
            return;
        }

        const outUpper = outcome.toUpperCase();
        if (outUpper.startsWith('SUCCESS')) {
            badgeEl.classList.add('badge-success');
            badgeEl.textContent = '✓ SUCCESS';
        } else if (outUpper.startsWith('PARTIAL')) {
            badgeEl.classList.add('badge-partial');
            badgeEl.textContent = `⚠ ${outcome}`;
        } else if (outUpper.startsWith('TIMEOUT')) {
            badgeEl.classList.add('badge-timeout');
            badgeEl.textContent = '⏱ TIMEOUT';
        } else if (outUpper.startsWith('CRASH')) {
            badgeEl.classList.add('badge-crash');
            badgeEl.textContent = '✕ CRASH';
        } else {
            badgeEl.classList.add('badge-idle');
            badgeEl.textContent = outcome;
        }
    }

    // -----------------------------------------------------------------------
    // FINDINGS TABLE RENDERING
    // -----------------------------------------------------------------------
    function renderFindings(findings, tbodyEl, noMsgEl, tableEl) {
        if (!tbodyEl) return;
        tbodyEl.innerHTML = '';

        if (!findings || findings.length === 0) {
            if (tableEl) tableEl.classList.add('hidden');
            if (noMsgEl) noMsgEl.classList.remove('hidden');
            return;
        }

        if (tableEl) tableEl.classList.remove('hidden');
        if (noMsgEl) noMsgEl.classList.add('hidden');

        findings.forEach((f, idx) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight: 700; color: #64748b;">${idx + 1}</td>
                <td>
                    <span class="method-tag" title="${escapeHtml(f.source_method)}">${escapeHtml(f.source_method)}</span>
                    <span class="statement-tag" title="${escapeHtml(f.source_statement)}">${escapeHtml(f.source_statement)}</span>
                </td>
                <td>
                    <span class="statement-tag" style="border-left-color: #ef4444;" title="${escapeHtml(f.sink_statement)}">${escapeHtml(f.sink_statement)}</span>
                </td>
                <td>
                    <span class="method-tag" title="${escapeHtml(f.sink_method)}">${escapeHtml(f.sink_method)}</span>
                </td>
            `;
            tbodyEl.appendChild(tr);
        });
    }

    // -----------------------------------------------------------------------
    // VIEW 2: FLOWDROID STATIC ANALYSIS EXECUTION
    // -----------------------------------------------------------------------
    const fdRunForm = document.getElementById('fdRunForm');
    const fdTimeoutInput = document.getElementById('fdTimeoutInput');
    const fdRunStateNotice = document.getElementById('fdRunStateNotice');
    const fdLiveStatusBadge = document.getElementById('fdLiveStatusBadge');
    const fdElapsedTime = document.getElementById('fdElapsedTime');
    const fdChkAutoScroll = document.getElementById('fdChkAutoScroll');
    const fdBtnClearLogs = document.getElementById('fdBtnClearLogs');
    const fdTerminalLogs = document.getElementById('fdTerminalLogs');
    const fdTerminalPlaceholder = document.getElementById('fdTerminalPlaceholder');
    const fdTerminalWindow = document.getElementById('fdTerminalWindow');

    const fdResultsSection = document.getElementById('fdResultsSection');
    const fdOutcomeBadge = document.getElementById('fdOutcomeBadge');
    const fdBtnDownloadXml = document.getElementById('fdBtnDownloadXml');
    const fdCrashAlertBox = document.getElementById('fdCrashAlertBox');
    const fdCrashSnippetText = document.getElementById('fdCrashSnippetText');

    const fdMetricTotalFindings = document.getElementById('fdMetricTotalFindings');
    const fdMetricSourceCount = document.getElementById('fdMetricSourceCount');
    const fdMetricSinkCount = document.getElementById('fdMetricSinkCount');
    const fdMetricTotalRuntime = document.getElementById('fdMetricTotalRuntime');
    const fdMetricCallgraph = document.getElementById('fdMetricCallgraph');
    const fdMetricMaxMemory = document.getElementById('fdMetricMaxMemory');

    const fdFindingsTable = document.getElementById('fdFindingsTable');
    const fdFindingsTableBody = document.getElementById('fdFindingsTableBody');
    const fdNoFindingsMessage = document.getElementById('fdNoFindingsMessage');
    const fdFindingsSearchInput = document.getElementById('fdFindingsSearchInput');

    let fdCurrentFindings = [];

    if (fdBtnClearLogs) {
        fdBtnClearLogs.addEventListener('click', () => {
            if (fdTerminalLogs) fdTerminalLogs.textContent = '';
            if (fdTerminalPlaceholder) fdTerminalPlaceholder.classList.remove('hidden');
        });
    }

    if (fdRunForm) {
        fdRunForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!currentFile) {
                alert('Please select an APK file first.');
                return;
            }

            const timeoutVal = parseInt(fdTimeoutInput.value, 10) || 1800;
            const formData = new FormData();
            formData.append('apk_file', currentFile);
            formData.append('timeout', timeoutVal);

            btnRunFlowdroid.disabled = true;
            if (fdRunStateNotice) fdRunStateNotice.classList.remove('hidden');
            setLiveBadge(fdLiveStatusBadge, 'running');
            if (fdTerminalLogs) fdTerminalLogs.textContent = '';
            if (fdTerminalPlaceholder) fdTerminalPlaceholder.classList.add('hidden');
            if (fdResultsSection) fdResultsSection.classList.add('hidden');
            if (fdCrashAlertBox) fdCrashAlertBox.classList.add('hidden');

            startTimer(fdElapsedTime);

            try {
                const resp = await fetch('/api/run', {
                    method: 'POST',
                    body: formData
                });

                if (!resp.ok) {
                    const err = await resp.json().catch(() => ({}));
                    throw new Error(err.error || `Server responded with ${resp.status}`);
                }

                const data = await resp.json();
                pollFlowdroidRun(data.run_id);
            } catch (err) {
                stopTimer(fdElapsedTime, 0);
                setLiveBadge(fdLiveStatusBadge, 'idle');
                btnRunFlowdroid.disabled = false;
                if (fdRunStateNotice) fdRunStateNotice.classList.add('hidden');
                alert(`FlowDroid execution error: ${err.message}`);
            }
        });
    }

    function pollFlowdroidRun(runId) {
        let lineCount = 0;
        const interval = setInterval(async () => {
            try {
                const resp = await fetch(`/api/poll/${runId}?since_line=${lineCount}`);
                if (!resp.ok) return;

                const data = await resp.json();

                if (data.new_logs && data.new_logs.length > 0) {
                    if (fdTerminalPlaceholder) fdTerminalPlaceholder.classList.add('hidden');
                    fdTerminalLogs.textContent += data.new_logs.join('\n') + '\n';
                    lineCount += data.new_logs.length;
                    if (fdChkAutoScroll && fdChkAutoScroll.checked && fdTerminalWindow) {
                        fdTerminalWindow.scrollTop = fdTerminalWindow.scrollHeight;
                    }
                }

                if (data.status === 'completed') {
                    clearInterval(interval);
                    stopTimer(fdElapsedTime, data.elapsed_seconds);
                    setLiveBadge(fdLiveStatusBadge, 'completed');
                    btnRunFlowdroid.disabled = false;
                    if (fdRunStateNotice) fdRunStateNotice.classList.add('hidden');

                    displayFlowdroidResults(data);
                    loadHistory();
                }
            } catch (err) {
                console.error('FlowDroid poll error:', err);
            }
        }, 1200);
    }

    function displayFlowdroidResults(data) {
        if (!fdResultsSection) return;
        fdResultsSection.classList.remove('hidden');
        setOutcomeBadge(fdOutcomeBadge, data.outcome);

        if (data.xml_available && data.run_id && fdBtnDownloadXml) {
            fdBtnDownloadXml.href = `/api/download/${data.run_id}/xml`;
            fdBtnDownloadXml.classList.remove('disabled');
        } else if (fdBtnDownloadXml) {
            fdBtnDownloadXml.href = '#';
            fdBtnDownloadXml.classList.add('disabled');
        }

        if (data.outcome === 'CRASH' || (data.crash_snippet && data.crash_snippet.trim().length > 0)) {
            if (fdCrashSnippetText) fdCrashSnippetText.textContent = data.crash_snippet || 'No error details captured.';
            if (fdCrashAlertBox) fdCrashAlertBox.classList.remove('hidden');
        } else {
            if (fdCrashAlertBox) fdCrashAlertBox.classList.add('hidden');
        }

        const results = data.results || {};
        const perf = results.performance_data || {};

        if (fdMetricTotalRuntime) fdMetricTotalRuntime.textContent = perf.TotalRuntimeSeconds || (data.elapsed_seconds ? Math.round(data.elapsed_seconds) : '-');
        if (fdMetricCallgraph) fdMetricCallgraph.textContent = perf.CallgraphConstructionSeconds || '-';
        if (fdMetricMaxMemory) fdMetricMaxMemory.textContent = perf.MaxMemoryConsumption || '-';
        if (fdMetricSourceCount) fdMetricSourceCount.textContent = perf.SourceCount || '-';
        if (fdMetricSinkCount) fdMetricSinkCount.textContent = perf.SinkCount || '-';
        if (fdMetricTotalFindings) fdMetricTotalFindings.textContent = data.findings_count !== undefined ? data.findings_count : (results.total_findings || 0);

        fdCurrentFindings = results.findings || [];
        renderFindings(fdCurrentFindings, fdFindingsTableBody, fdNoFindingsMessage, fdFindingsTable);

        fdResultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    if (fdFindingsSearchInput) {
        fdFindingsSearchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (!query) {
                renderFindings(fdCurrentFindings, fdFindingsTableBody, fdNoFindingsMessage, fdFindingsTable);
                return;
            }
            const filtered = fdCurrentFindings.filter(f =>
                (f.source_method && f.source_method.toLowerCase().includes(query)) ||
                (f.source_statement && f.source_statement.toLowerCase().includes(query)) ||
                (f.sink_method && f.sink_method.toLowerCase().includes(query)) ||
                (f.sink_statement && f.sink_statement.toLowerCase().includes(query))
            );
            renderFindings(filtered, fdFindingsTableBody, fdNoFindingsMessage, fdFindingsTable);
        });
    }

    // -----------------------------------------------------------------------
    // SESSION HISTORY (SHARED SYNC ACROSS VIEWS)
    // -----------------------------------------------------------------------
    async function loadHistory() {
        try {
            const resp = await fetch('/api/history');
            if (!resp.ok) return;

            const historyList = await resp.json();
            renderHistoryTables(historyList);
        } catch (err) {
            console.error('Failed to load history:', err);
        }
    }

    function renderHistoryTables(items) {
        const tbodies = document.querySelectorAll('.history-tbody-sync');
        tbodies.forEach(tbody => {
            tbody.innerHTML = '';

            if (!items || items.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-muted text-center">No runs recorded yet in this session.</td></tr>`;
                return;
            }

            items.forEach(item => {
                const tr = document.createElement('tr');
                let badgeClass = 'badge-idle';
                const outUpper = (item.outcome || '').toUpperCase();
                if (outUpper.startsWith('SUCCESS')) badgeClass = 'badge-success';
                else if (outUpper.startsWith('PARTIAL')) badgeClass = 'badge-partial';
                else if (outUpper.startsWith('TIMEOUT')) badgeClass = 'badge-timeout';
                else if (outUpper.startsWith('CRASH')) badgeClass = 'badge-crash';

                tr.innerHTML = `
                    <td style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;">${escapeHtml(item.timestamp)}</td>
                    <td style="font-weight: 600;">${escapeHtml(item.apk_name)}</td>
                    <td style="font-family: 'JetBrains Mono', monospace;">${item.apk_size_mb} MB</td>
                    <td style="font-family: 'JetBrains Mono', monospace;">${item.elapsed_seconds}s</td>
                    <td><span class="outcome-badge ${badgeClass}" style="font-size: 0.76rem; padding: 3px 8px;">${escapeHtml(item.outcome)}</span></td>
                    <td style="font-weight: 700;">${item.findings_count}</td>
                    <td style="text-align: right;">
                        <button type="button" class="btn-sm btn-outline btn-view-run" data-run-id="${item.run_id}">View Results</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        });

        // Re-attach view button listeners
        document.querySelectorAll('.btn-view-run').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const runId = e.target.getAttribute('data-run-id');
                await viewPastRun(runId);
            });
        });
    }

    async function viewPastRun(runId) {
        try {
            const resp = await fetch(`/api/run/${runId}`);
            if (!resp.ok) {
                alert('Could not retrieve past run details.');
                return;
            }

            const runData = await resp.json();

            // Switch to FlowDroid view if in DSS
            if (currentModule === 'dss') {
                switchModule('flowdroid');
            }
            if (fdTerminalLogs) fdTerminalLogs.textContent = (runData.logs || []).join('\n') + '\n';
            if (fdTerminalPlaceholder) fdTerminalPlaceholder.classList.add('hidden');
            stopTimer(fdElapsedTime, runData.elapsed_seconds);
            setLiveBadge(fdLiveStatusBadge, 'completed');
            displayFlowdroidResults(runData);
        } catch (err) {
            alert(`Error viewing past run: ${err.message}`);
        }
    }

    // Refresh history buttons
    document.querySelectorAll('.btn-refresh-hist').forEach(btn => {
        btn.addEventListener('click', loadHistory);
    });

    // Clear history buttons
    document.querySelectorAll('.btn-clear-hist').forEach(btn => {
        btn.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to clear the session run history?')) return;
            try {
                const resp = await fetch('/api/history/clear', { method: 'POST' });
                if (resp.ok) {
                    renderHistoryTables([]);
                } else {
                    alert('Failed to clear history.');
                }
            } catch (err) {
                alert('Error connecting to server.');
            }
        });
    });

    // -----------------------------------------------------------------------
    // HELPERS
    // -----------------------------------------------------------------------
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Initial load
    loadHistory();
});
