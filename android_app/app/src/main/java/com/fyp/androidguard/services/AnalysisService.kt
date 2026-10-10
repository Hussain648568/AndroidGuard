package com.fyp.androidguard.services

import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import com.fyp.androidguard.models.AnalysisReport
import com.fyp.androidguard.network.ApiClient
import com.fyp.androidguard.ui.screens.UiState
import com.google.gson.Gson
import kotlinx.coroutines.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class AnalysisService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var job: Job? = null

    companion object {
        const val EXTRA_APP_NAME = "EXTRA_APP_NAME"
        const val EXTRA_PACKAGE_NAME = "EXTRA_PACKAGE_NAME"
        const val EXTRA_SOURCE_DIR = "EXTRA_SOURCE_DIR"

        fun startAnalysis(context: Context, appName: String, packageName: String, sourceDir: String) {
            val intent = Intent(context, AnalysisService::class.java).apply {
                putExtra(EXTRA_APP_NAME, appName)
                putExtra(EXTRA_PACKAGE_NAME, packageName)
                putExtra(EXTRA_SOURCE_DIR, sourceDir)
            }
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val appName = intent?.getStringExtra(EXTRA_APP_NAME) ?: "Application"
        val packageName = intent?.getStringExtra(EXTRA_PACKAGE_NAME) ?: ""
        val sourceDir = intent?.getStringExtra(EXTRA_SOURCE_DIR) ?: ""

        if (sourceDir.isEmpty()) {
            stopSelf()
            return START_NOT_STICKY
        }

        // Start as foreground immediately
        val initialNotification = NotificationHelper.buildForegroundNotification(
            this,
            appName,
            "Extracting and uploading APK to analyzer..."
        )
        startForeground(NotificationHelper.FOREGROUND_NOTIFICATION_ID, initialNotification)

        AnalysisStateManager.setJob(
            ActiveAnalysisJob(appName, packageName, "Uploading APK to analyzer...")
        )

        job?.cancel()
        job = serviceScope.launch {
            try {
                performAnalysis(appName, packageName, sourceDir)
            } catch (e: Exception) {
                val errorMsg = e.message ?: "Analysis execution error"
                AnalysisStateManager.setError(errorMsg)
                NotificationHelper.showFailureNotification(this@AnalysisService, appName, errorMsg)
            } finally {
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }

        return START_NOT_STICKY
    }

    private suspend fun performAnalysis(appName: String, packageName: String, sourceDir: String) {
        val apkFile = File(sourceDir)
        if (!apkFile.exists()) {
            throw IllegalStateException("APK file not accessible on device: $sourceDir")
        }

        updateProgress(appName, "Uploading ${appName} APK to server...")

        val requestFile = apkFile.asRequestBody("application/vnd.android.package-archive".toMediaTypeOrNull())
        val safeName = appName.replace(" ", "_") + ".apk"
        val body = MultipartBody.Part.createFormData("file", safeName, requestFile)

        val uploadResponse = ApiClient.instance.uploadApk(body)
        val runId = uploadResponse.runId

        AnalysisStateManager.setJob(
            ActiveAnalysisJob(appName, packageName, "Queued on server...", runId)
        )

        // Poll for completion (supports up to 65 minutes for 30m FlowDroid + 30m Fallback)
        var isCompleted = false
        var pollCount = 0
        val maxPolls = (65 * 60) / 5 // every 5 seconds for 65 mins

        while (!isCompleted && pollCount < maxPolls) {
            delay(5000)
            pollCount++

            try {
                val statusRes = ApiClient.instance.getStatus(runId)
                when (statusRes.status) {
                    "queued", "running" -> {
                        val stage = statusRes.stage ?: "Deep analysis in progress (FlowDroid/Fallback)..."
                        updateProgress(appName, stage)
                    }
                    "success" -> {
                        isCompleted = true
                        updateProgress(appName, "Retrieving and parsing final audit report...")

                        val reportStr = ApiClient.instance.getReport(runId).string()
                        val report = try {
                            Gson().fromJson(reportStr, AnalysisReport::class.java)
                        } catch (e: Exception) {
                            AnalysisReport(definitive_leaks_count = 0)
                        }

                        val result = UiState.Result(report, reportStr, appName)
                        AnalysisStateManager.setResult(result)

                        NotificationHelper.showCompletionNotification(
                            this@AnalysisService,
                            appName,
                            report.definitive_leaks_count,
                            report.engine ?: "Static"
                        )
                    }
                    "failed" -> {
                        isCompleted = true
                        val error = statusRes.error ?: "Analysis failed on server"
                        AnalysisStateManager.setError(error)
                        NotificationHelper.showFailureNotification(this@AnalysisService, appName, error)
                    }
                }
            } catch (e: Exception) {
                // Ignore transient network hiccups during long runs
            }
        }

        if (!isCompleted) {
            val timeoutError = "Analysis timed out after 60+ minutes on server."
            AnalysisStateManager.setError(timeoutError)
            NotificationHelper.showFailureNotification(this@AnalysisService, appName, timeoutError)
        }
    }

    private fun updateProgress(appName: String, stage: String) {
        AnalysisStateManager.updateStage(stage)
        val notification = NotificationHelper.buildForegroundNotification(this, appName, stage)
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NotificationHelper.FOREGROUND_NOTIFICATION_ID, notification)
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
    }
}
