package com.fyp.androidguard.models

import com.google.gson.annotations.SerializedName

data class AnalyzeResponse(
    @SerializedName("run_id") val runId: String,
    @SerializedName("message") val message: String,
    @SerializedName("cached") val cached: Boolean = false
)

data class CacheCheckResponse(
    val cached: Boolean,
    @SerializedName("run_id") val runId: String? = null,
    val message: String? = null
)

data class StatusResponse(
    @SerializedName("status") val status: String,
    @SerializedName("stage") val stage: String?,
    @SerializedName("engine") val engine: String?,
    @SerializedName("error") val error: String?,
    @SerializedName("cached") val cached: Boolean = false
)

data class FindingNode(
    val type: String? = null,
    val kind: String? = null,
    @SerializedName("class") val className: String? = null,
    val method: String? = null,
    val target_signature: String? = null,
    val category: String? = null,
    val file: String? = null,
    val line_no: Int? = null
)

data class LeakFinding(
    val source: FindingNode? = null,
    val sink: FindingNode? = null,
    val link_level: String? = null,
    val confidence: String? = null,
    val analysis_tier: String? = null
)

data class RiskAssessment(
    val score: Double = 0.0,
    val grade: String = "A+",
    val severity: String = "CLEAN",
    val recommendation: String = ""
)

data class AnalysisReport(
    val apk_path: String? = null,
    val status: String? = null,
    val engine: String? = null,
    val sha256: String? = null,
    val cached: Boolean = false,
    val total_raw_findings: Int = 0,
    val definitive_leaks_count: Int = 0,
    val risk_assessment: RiskAssessment? = null,
    val findings: List<LeakFinding> = emptyList()
)

data class AuditHistoryItem(
    val appName: String,
    val packageName: String,
    val sha256: String,
    val definitiveLeaksCount: Int,
    val riskScore: Double,
    val riskGrade: String,
    val severity: String,
    val engine: String,
    val timestamp: Long,
    val rawJson: String
)
