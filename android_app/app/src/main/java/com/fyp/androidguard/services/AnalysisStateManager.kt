package com.fyp.androidguard.services

import com.fyp.androidguard.ui.screens.UiState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

data class ActiveAnalysisJob(
    val appName: String,
    val packageName: String,
    val stage: String,
    val runId: String? = null
)

object AnalysisStateManager {
    private val _activeJob = MutableStateFlow<ActiveAnalysisJob?>(null)
    val activeJob: StateFlow<ActiveAnalysisJob?> = _activeJob

    private val _latestResult = MutableStateFlow<UiState.Result?>(null)
    val latestResult: StateFlow<UiState.Result?> = _latestResult

    private val _latestError = MutableStateFlow<String?>(null)
    val latestError: StateFlow<String?> = _latestError

    fun setJob(job: ActiveAnalysisJob?) {
        _activeJob.value = job
    }

    fun updateStage(stage: String) {
        _activeJob.value = _activeJob.value?.copy(stage = stage)
    }

    fun setResult(result: UiState.Result?) {
        _latestResult.value = result
        _activeJob.value = null
    }

    fun setError(error: String?) {
        _latestError.value = error
        _activeJob.value = null
    }

    fun clearResult() {
        _latestResult.value = null
    }
}
