package com.fyp.androidguard.ui.screens

import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.BitmapDrawable
import android.graphics.drawable.Drawable
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fyp.androidguard.models.AnalysisReport
import com.fyp.androidguard.services.ActiveAnalysisJob
import com.fyp.androidguard.services.AnalysisService
import com.fyp.androidguard.services.AnalysisStateManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class InstalledApp(
    val appName: String,
    val packageName: String,
    val sourceDir: String,
    val icon: ImageBitmap
)

sealed class UiState {
    object LoadingApps : UiState()
    data class AppList(val apps: List<InstalledApp>) : UiState()
    data class Result(val report: AnalysisReport, val rawJson: String, val appName: String) : UiState()
    data class Error(val error: String) : UiState()
}

class MainViewModel : ViewModel() {

    private val _uiState = MutableStateFlow<UiState>(UiState.LoadingApps)
    val uiState: StateFlow<UiState> = _uiState

    val activeJob: StateFlow<ActiveAnalysisJob?> = AnalysisStateManager.activeJob

    private var cachedAppList: List<InstalledApp> = emptyList()

    init {
        viewModelScope.launch {
            AnalysisStateManager.latestResult.collect { result ->
                if (result != null) {
                    _uiState.value = result
                }
            }
        }
        viewModelScope.launch {
            AnalysisStateManager.latestError.collect { error ->
                if (error != null) {
                    _uiState.value = UiState.Error(error)
                }
            }
        }
    }

    fun loadInstalledApps(context: Context) {
        if (cachedAppList.isNotEmpty()) {
            if (_uiState.value !is UiState.Result) {
                _uiState.value = UiState.AppList(cachedAppList)
            }
            return
        }
        viewModelScope.launch {
            _uiState.value = UiState.LoadingApps
            val apps = withContext(Dispatchers.IO) {
                val pm = context.packageManager
                val packages = pm.getInstalledApplications(PackageManager.GET_META_DATA)

                packages.filter { appInfo ->
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
            if (_uiState.value !is UiState.Result) {
                _uiState.value = UiState.AppList(apps)
            }
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

    fun startBackgroundAnalysis(context: Context, app: InstalledApp) {
        // Starts background foreground service: does NOT freeze the UI!
        AnalysisService.startAnalysis(context, app.appName, app.packageName, app.sourceDir)
        // Ensure user stays on the app list so they can do other things
        if (cachedAppList.isNotEmpty()) {
            _uiState.value = UiState.AppList(cachedAppList)
        }
    }

    fun resetToAppList() {
        AnalysisStateManager.clearResult()
        AnalysisStateManager.setError(null)
        if (cachedAppList.isNotEmpty()) {
            _uiState.value = UiState.AppList(cachedAppList)
        } else {
            _uiState.value = UiState.LoadingApps
        }
    }

    fun viewActiveResult(result: UiState.Result) {
        _uiState.value = result
    }
}
