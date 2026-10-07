import React, { useState } from 'react';

/**
 * DataSafetyCard - React Component for AndroidGuard
 * 
 * Displays the Google Play Data Safety Section (DSS) declarations
 * in a high-tech cybersecurity card layout, with side-by-side or
 * integrated comparison against FlowDroid static bytecode findings.
 *
 * @param {Object} props
 * @param {Object} props.dssData - Clean DSS object from backend get_clean_dss_for_ui
 * @param {Array}  [props.flowdroidFindings=[]] - Array of FlowDroid findings
 * @param {number} [props.findingsCount] - Number of findings from FlowDroid
 * @param {string} [props.packageName] - Android package name
 * @param {boolean} [props.showComparison=true] - Whether to show the comparison view
 */
export default function DataSafetyCard({
  dssData,
  flowdroidFindings = [],
  findingsCount,
  packageName,
  showComparison = true,
}) {
  const resolvedFindingsCount = findingsCount !== undefined 
    ? findingsCount 
    : (flowdroidFindings ? flowdroidFindings.length : 0);

  // Unlisted or error state
  if (!dssData || dssData.error) {
    const pkg = dssData?.package_name || packageName || 'Unknown Package';
    return (
      <div className="w-full rounded-xl border border-slate-700/60 bg-slate-900/80 p-6 shadow-xl backdrop-blur-md text-slate-200 font-sans">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
          <div className="flex items-center gap-2">
            <span className="text-xl">📋</span>
            <h3 className="text-lg font-bold text-white tracking-wide">Google Play Data Safety</h3>
          </div>
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-slate-800 text-slate-400 border border-slate-700">
            Unlisted on Play Store
          </span>
        </div>

        <div className="flex items-start gap-4 p-4 rounded-lg bg-slate-800/40 border border-slate-700/50">
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 text-2xl">⚠️</div>
          <div>
            <h4 className="font-semibold text-slate-100 mb-1">Declaration Not Found on Play Store</h4>
            <p className="text-sm text-slate-400 mb-2">
              {dssData?.error || `No Play Store Data Safety Section found for package "${pkg}".`}
            </p>
            <p className="text-xs text-slate-500">
              This typically occurs with local benchmark APKs (e.g., DroidBench), internal test builds, or third-party enterprise packages.
            </p>
          </div>
        </div>

        {resolvedFindingsCount > 0 && (
          <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300">
            <strong>Static Analysis Note:</strong> FlowDroid detected {resolvedFindingsCount} data leak(s) in this APK. Since no Play Store record exists, ground-truth comparison cannot be performed.
          </div>
        )}
      </div>
    );
  }

  const {
    app_name = 'Android Application',
    developer = 'Unknown Developer',
    icon_url,
    privacy_policy_link,
    is_data_encrypted = false,
    is_data_deletion_supported = false,
    data_collected = [],
    data_shared = [],
  } = dssData;

  const resolvedPkg = dssData.package_name || packageName;

  // Potential discrepancy: Developer claims 0 collection & 0 sharing, but FlowDroid found leaks
  const hasDiscrepancy = resolvedFindingsCount > 0 && data_collected.length === 0 && data_shared.length === 0;

  return (
    <div className="w-full rounded-xl border border-slate-700/60 bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 p-6 shadow-2xl backdrop-blur-md text-slate-200 font-sans">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-4 mb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2.5 py-0.5 rounded-full">
              Verified Play Store Declaration
            </span>
          </div>
          <h3 className="text-xl font-bold text-white tracking-tight">Security & Privacy Declarations</h3>
        </div>

        <span className="text-xs font-mono text-slate-400 bg-slate-800/80 px-3 py-1 rounded-md border border-slate-700/60">
          {resolvedPkg}
        </span>
      </div>

      {/* App Metadata Row */}
      <div className="flex flex-wrap sm:flex-nowrap items-center gap-4 p-4 rounded-xl bg-slate-800/30 border border-slate-800 mb-6">
        <div className="flex-shrink-0 w-16 h-16 rounded-xl bg-slate-800 border border-slate-700/80 overflow-hidden flex items-center justify-center shadow-inner">
          {icon_url ? (
            <img src={icon_url} alt={`${app_name} icon`} className="w-full h-full object-cover" />
          ) : (
            <span className="text-3xl">📱</span>
          )}
        </div>

        <div className="flex-grow min-w-0">
          <h4 className="text-lg font-bold text-white truncate">{app_name}</h4>
          <p className="text-sm text-slate-400 truncate mb-1">
            By <span className="text-slate-300 font-medium">{developer}</span>
          </p>
          {privacy_policy_link && (
            <a
              href={privacy_policy_link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors font-medium"
            >
              <span>🔗</span> Official Privacy Policy
            </a>
          )}
        </div>
      </div>

      {/* Badges Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
        {/* Encryption Badge */}
        <div
          className={`flex items-center gap-3 p-3.5 rounded-xl border transition-all ${
            is_data_encrypted
              ? 'bg-emerald-950/20 border-emerald-800/50 text-emerald-300'
              : 'bg-amber-950/20 border-amber-800/50 text-amber-300'
          }`}
        >
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl flex-shrink-0 ${
              is_data_encrypted ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
            }`}
          >
            {is_data_encrypted ? '🛡️' : '⚠️'}
          </div>
          <div>
            <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Data Encryption</div>
            <div className="text-sm font-bold text-white">
              {is_data_encrypted ? 'Encrypted in Transit' : 'Not Declared / None'}
            </div>
          </div>
        </div>

        {/* Deletion Badge */}
        <div
          className={`flex items-center gap-3 p-3.5 rounded-xl border transition-all ${
            is_data_deletion_supported
              ? 'bg-emerald-950/20 border-emerald-800/50 text-emerald-300'
              : 'bg-amber-950/20 border-amber-800/50 text-amber-300'
          }`}
        >
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl flex-shrink-0 ${
              is_data_deletion_supported ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
            }`}
          >
            {is_data_deletion_supported ? '🗑️' : '⚠️'}
          </div>
          <div>
            <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Data Deletion</div>
            <div className="text-sm font-bold text-white">
              {is_data_deletion_supported ? 'Deletion Requests Supported' : 'No Deletion Mechanism Declared'}
            </div>
          </div>
        </div>
      </div>

      {/* Discrepancy / Compliance Alert Banner */}
      {showComparison && resolvedFindingsCount !== undefined && (
        <div className="mb-6">
          {hasDiscrepancy ? (
            <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/70 text-red-200">
              <div className="flex items-start gap-3">
                <span className="text-2xl">🚨</span>
                <div>
                  <h5 className="font-bold text-red-300 text-sm tracking-wide uppercase">
                    Critical Compliance Discrepancy
                  </h5>
                  <p className="text-xs mt-1 leading-relaxed">
                    FlowDroid static analysis identified <strong>{resolvedFindingsCount} data leak(s)</strong> in bytecode execution paths, but the developer has declared <strong>0 data collection and 0 data sharing</strong> on the Google Play Store. This discrepancy indicates potential Google Play policy non-compliance.
                  </p>
                </div>
              </div>
            </div>
          ) : resolvedFindingsCount > 0 ? (
            <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/70 text-amber-200">
              <div className="flex items-start gap-3">
                <span className="text-2xl">⚠️</span>
                <div>
                  <h5 className="font-bold text-amber-300 text-sm tracking-wide uppercase">
                    Compliance Verification Required
                  </h5>
                  <p className="text-xs mt-1 leading-relaxed">
                    FlowDroid identified <strong>{resolvedFindingsCount} static flow leak(s)</strong>. Cross-reference the FlowDroid sources and sinks with the declared categories below to verify whether all exfiltrated data types have been properly disclosed.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-200 flex items-center gap-3">
              <span className="text-xl">✅</span>
              <p className="text-xs">
                <strong>Bytecode Verified Clean:</strong> FlowDroid detected 0 information leaks in analyzed entry points.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Data Safety Lists: Two Columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Card A: Data Collected */}
        <div className="rounded-xl bg-slate-800/40 border border-slate-800 p-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
            <div className="flex items-center gap-2">
              <span className="text-emerald-400">📥</span>
              <h5 className="font-bold text-sm text-slate-100">Data This App Collects</h5>
            </div>
            <span className="text-xs px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 font-mono">
              {data_collected.length} categories
            </span>
          </div>

          {data_collected.length > 0 ? (
            <ul className="space-y-2 text-xs">
              {data_collected.map((item, i) => (
                <li key={i} className="flex items-center gap-2 p-2 rounded-lg bg-slate-900/60 border border-slate-800/80">
                  <span className="text-emerald-400 font-bold">•</span>
                  <span className="text-slate-200 font-medium">{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="p-4 rounded-lg bg-slate-900/40 text-center text-xs text-slate-400">
              <span className="text-emerald-400 mr-1">✓</span> No Data Collection Declared
            </div>
          )}
        </div>

        {/* Card B: Data Shared */}
        <div className="rounded-xl bg-slate-800/40 border border-slate-800 p-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
            <div className="flex items-center gap-2">
              <span className="text-blue-400">↗️</span>
              <h5 className="font-bold text-sm text-slate-100">Data Shared with Others</h5>
            </div>
            <span className="text-xs px-2 py-0.5 rounded bg-blue-950/60 text-blue-400 font-mono">
              {data_shared.length} categories
            </span>
          </div>

          {data_shared.length > 0 ? (
            <ul className="space-y-2 text-xs">
              {data_shared.map((item, i) => (
                <li key={i} className="flex items-center gap-2 p-2 rounded-lg bg-slate-900/60 border border-slate-800/80">
                  <span className="text-blue-400 font-bold">•</span>
                  <span className="text-slate-200 font-medium">{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="p-4 rounded-lg bg-slate-900/40 text-center text-xs text-slate-400">
              <span className="text-emerald-400 mr-1">✓</span> No Third-Party Sharing Declared
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
