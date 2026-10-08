package com.fyp.androidguard.ui.screens

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.BitmapDrawable
import android.graphics.drawable.Drawable
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fyp.androidguard.models.StatusResponse
import com.fyp.androidguard.network.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import org.json.JSONObject
import java.io.File

data class InstalledApp(
    val appName: String,
    val packageName: String,
    val sourceDir: String,
    val icon: ImageBitmap
)

sealed class UiState {
    object LoadingApps : UiState()
    data class AppList(val apps: List<InstalledApp>) : UiState()
    data class Uploading(val message: String, val appName: String) : UiState()
    data class Analyzing(val stage: String, val appName: String) : UiState()
    data class Result(val leaksFound: Int, val rawJson: String, val appName: String) : UiState()
    data class Error(val error: String) : UiState()
}

class MainViewModel : ViewModel() {

    private val _uiState = MutableStateFlow<UiState>(UiState.LoadingApps)
    val uiState: StateFlow<UiState> = _uiState

    private var activeRunId: String? = null
    private var cachedAppList: List<InstalledApp> = emptyList()

    fun loadInstalledApps(context: Context) {
        if (cachedAppList.isNotEmpty()) {
            _uiState.value = UiState.AppList(cachedAppList)
            return
        }
        viewModelScope.launch {
            _uiState.value = UiState.LoadingApps
            val apps = withContext(Dispatchers.IO) {
                val pm = context.packageManager
                val packages = pm.getInstalledApplications(PackageManager.GET_META_DATA)
                
                packages.filter { appInfo -> 
                    // Filter out core system apps that are not launchable (optional, but keeps list clean)
                    pm.getLaunchIntentForPackage(appInfo.packageName) != null
                }.map { appInfo ->
                    val name = pm.getApplicationLabel(appInfo).toString()
                    val iconDrawable = pm.getApplicationIcon(appInfo)
                    InstalledApp(
                        appName = name,
                        packageName = appInfo.packageName,
                        sourceDir = appInfo.sourceDir,
                        icon = drawableToImageBitmap(iconDrawable)
                    )
                }.sortedBy { it.appName.lowercase() }
            }
            cachedAppList = apps
            _uiState.value = UiState.AppList(apps)
        }
    }

    private fun drawableToImageBitmap(drawable: Drawable): ImageBitmap {
        if (drawable is BitmapDrawable && drawable.bitmap != null) {
            return drawable.bitmap.asImageBitmap()
        }
        val bitmap = Bitmap.createBitmap(
            drawable.intrinsicWidth.coerceAtLeast(1),
            drawable.intrinsicHeight.coerceAtLeast(1),
            Bitmap.Config.ARGB_8888
        )
        val canvas = Canvas(bitmap)
        drawable.setBounds(0, 0, canvas.width, canvas.height)
        drawable.draw(canvas)
        return bitmap.asImageBitmap()
    }

    fun analyzeApp(app: InstalledApp) {
        viewModelScope.launch {
            _uiState.value = UiState.Uploading("Extracting APK...", app.appName)
            try {
                val file = File(app.sourceDir)
                if (!file.exists()) {
                    _uiState.value = UiState.Error("APK file not found on device.")
                    return@launch
                }

                _uiState.value = UiState.Uploading("Uploading ${app.appName} to Analyzer...", app.appName)
                val requestFile = file.asRequestBody("application/vnd.android.package-archive".toMediaTypeOrNull())
                // Safe filename
                val safeName = app.appName.replace(" ", "_") + ".apk"
                val body = MultipartBody.Part.createFormData("file", safeName, requestFile)

                val response = ApiClient.instance.uploadApk(body)
                activeRunId = response.runId
                
                pollStatus(app.appName)

            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "Upload failed")
            }
        }
    }

    private fun pollStatus(appName: String) {
        val runId = activeRunId ?: return
        viewModelScope.launch {
            while (true) {
                try {
                    val statusRes = ApiClient.instance.getStatus(runId)
                    when (statusRes.status) {
                        "queued", "running" -> {
                            val stage = statusRes.stage ?: "Initializing..."
                            _uiState.value = UiState.Analyzing("Analyzing: ${stage}", appName)
                        }
                        "success" -> {
                            fetchReport(runId, appName)
                            break
                        }
                        "failed" -> {
                            _uiState.value = UiState.Error(statusRes.error ?: "Analysis failed")
                            break
                        }
                    }
                } catch (e: Exception) {
                    // Ignore transient network errors during polling
                }
                delay(5000) // Poll every 5 seconds
            }
        }
    }

    private suspend fun fetchReport(runId: String, appName: String) {
        try {
            _uiState.value = UiState.Analyzing("Fetching Final Report...", appName)
            val reportStr = ApiClient.instance.getReport(runId).string()
            val json = JSONObject(reportStr)
            val leakCount = json.optInt("definitive_leaks_count", 0)
            
            _uiState.value = UiState.Result(leakCount, reportStr, appName)
        } catch (e: Exception) {
            _uiState.value = UiState.Error(e.message ?: "Failed to fetch report")
        }
    }

    fun resetToAppList() {
        if (cachedAppList.isNotEmpty()) {
            _uiState.value = UiState.AppList(cachedAppList)
        } else {
            _uiState.value = UiState.LoadingApps
        }
    }
}
