package com.fyp.androidguard.models

import com.google.gson.annotations.SerializedName

data class AnalyzeResponse(
    @SerializedName("run_id") val runId: String,
    @SerializedName("message") val message: String
)

data class StatusResponse(
    @SerializedName("status") val status: String,
    @SerializedName("stage") val stage: String?,
    @SerializedName("engine") val engine: String?,
    @SerializedName("error") val error: String?
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

data class AnalysisReport(
    val apk_path: String? = null,
    val status: String? = null,
    val engine: String? = null,
    val total_raw_findings: Int = 0,
    val definitive_leaks_count: Int = 0,
    val findings: List<LeakFinding> = emptyList()
)
