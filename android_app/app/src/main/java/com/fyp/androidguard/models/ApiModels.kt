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

data class LeakFinding(
    val source: String,
    val sink: String,
    val confidence: String
)

data class ReportResponse(
    val status: String,
    val definitive_leaks_count: Int,
    val apk_path: String
)
