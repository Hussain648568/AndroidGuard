package com.fyp.androidguard

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.ExperimentalAnimationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.HourglassTop
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.NotificationsActive
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.fyp.androidguard.models.LeakFinding
import com.fyp.androidguard.services.ActiveAnalysisJob
import com.fyp.androidguard.services.AnalysisStateManager
import com.fyp.androidguard.ui.screens.InstalledApp
import com.fyp.androidguard.ui.screens.MainViewModel
import com.fyp.androidguard.ui.screens.UiState
import com.fyp.androidguard.ui.theme.AndroidGuardTheme
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private var viewModelInstance: MainViewModel? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleNotificationIntent(intent)

        setContent {
            AndroidGuardTheme {
                val vm: MainViewModel = viewModel()
                viewModelInstance = vm
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    AppContent(viewModel = vm)
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleNotificationIntent(intent)
    }

    private fun handleNotificationIntent(intent: Intent?) {
        if (intent?.getBooleanExtra("EXTRA_SHOW_RESULT", false) == true) {
            val result = AnalysisStateManager.latestResult.value
            if (result != null) {
                viewModelInstance?.viewActiveResult(result)
            }
        }
    }
}

// Custom visible scrollbar modifier for mouse/emulator navigation
fun Modifier.verticalScrollbar(
    state: LazyListState,
    width: Dp = 6.dp,
    thumbColor: Color = Color(0xFF6200EE).copy(alpha = 0.5f)
): Modifier = drawWithContent {
    drawContent()
    val totalItems = state.layoutInfo.totalItemsCount
    val visibleItems = state.layoutInfo.visibleItemsInfo.size
    if (totalItems > 0 && visibleItems < totalItems) {
        val firstIndex = state.layoutInfo.visibleItemsInfo.firstOrNull()?.index ?: 0
        val trackHeight = size.height
        val thumbHeight = (visibleItems.toFloat() / totalItems.toFloat()) * trackHeight
        val thumbOffsetY = (firstIndex.toFloat() / totalItems.toFloat()) * trackHeight

        drawRoundRect(
            color = thumbColor,
            topLeft = Offset(size.width - width.toPx(), thumbOffsetY),
            size = Size(width.toPx(), thumbHeight.coerceAtLeast(20.dp.toPx())),
            cornerRadius = CornerRadius(4.dp.toPx(), 4.dp.toPx())
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalAnimationApi::class)
@Composable
fun AppContent(viewModel: MainViewModel = viewModel()) {
    val context = LocalContext.current
    val uiState by viewModel.uiState.collectAsState()
    val activeJob by viewModel.activeJob.collectAsState()

    // Request notification permissions for Android 13+ (API 33+)
    val notificationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { /* Permission result handled */ }

    LaunchedEffect(Unit) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
        viewModel.loadInstalledApps(context)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.Security,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(28.dp)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            "AndroidGuard",
                            fontWeight = FontWeight.Bold,
                            fontSize = 20.sp
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant,
                    titleContentColor = MaterialTheme.colorScheme.onSurfaceVariant
                ),
                navigationIcon = {
                    if (uiState !is UiState.AppList && uiState !is UiState.LoadingApps) {
                        IconButton(onClick = { viewModel.resetToAppList() }) {
                            Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                        }
                    }
                }
            )
        }
    ) { paddingValues ->
        Box(modifier = Modifier.padding(paddingValues)) {
            AnimatedContent(targetState = uiState, label = "ScreenTransition") { state ->
                when (state) {
                    is UiState.LoadingApps -> LoadingScreen("Discovering installed applications...")
                    is UiState.AppList -> AppListScreen(
                        apps = state.apps,
                        activeJob = activeJob,
                        onAppSelected = { app ->
                            viewModel.startBackgroundAnalysis(context, app)
                            Toast.makeText(
                                context,
                                "Analysis started in background for ${app.appName}! You can freely use other apps.",
                                Toast.LENGTH_LONG
                            ).show()
                        }
                    )
                    is UiState.Result -> ResultScreen(state, onBack = { viewModel.resetToAppList() })
                    is UiState.Error -> ErrorScreen(state.error) { viewModel.resetToAppList() }
                }
            }
        }
    }
}

@Composable
fun LoadingScreen(message: String) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        CircularProgressIndicator(
            modifier = Modifier.size(72.dp),
            strokeWidth = 6.dp,
            color = MaterialTheme.colorScheme.primary
        )
        Spacer(modifier = Modifier.height(28.dp))
        Text(
            text = message,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface
        )
    }
}

@Composable
fun AppListScreen(
    apps: List<InstalledApp>,
    activeJob: ActiveAnalysisJob?,
    onAppSelected: (InstalledApp) -> Unit
) {
    var searchQuery by remember { mutableStateOf("") }
    val filteredApps = remember(searchQuery, apps) {
        if (searchQuery.isBlank()) apps
        else apps.filter {
            it.appName.contains(searchQuery, ignoreCase = true) ||
            it.packageName.contains(searchQuery, ignoreCase = true)
        }
    }

    val listState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()

    Box(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.fillMaxSize()) {
            // Active Background Analysis Banner Card
            if (activeJob != null) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(24.dp),
                                strokeWidth = 3.dp,
                                color = MaterialTheme.colorScheme.onPrimaryContainer
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "Analyzing ${activeJob.appName} (in Background)",
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer
                                )
                                Text(
                                    text = activeJob.stage,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.85f),
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier
                                .background(
                                    MaterialTheme.colorScheme.surface.copy(alpha = 0.6f),
                                    shape = RoundedCornerShape(8.dp)
                                )
                                .padding(horizontal = 10.dp, vertical = 6.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.NotificationsActive,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "Takes up to 30 mins. You can freely use other apps. A notification will alert you when complete!",
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }
                }
            }

            // Search Bar for quick filtering on emulator
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 6.dp),
                placeholder = { Text("Search apps (e.g. 'Calculator')...") },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                trailingIcon = {
                    if (searchQuery.isNotEmpty()) {
                        IconButton(onClick = { searchQuery = "" }) {
                            Icon(Icons.Default.Clear, contentDescription = "Clear")
                        }
                    }
                },
                singleLine = true,
                shape = RoundedCornerShape(14.dp)
            )

            // Header info
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "${filteredApps.size} Installed Apps",
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "Tap Analyze to inspect in background",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline
                )
            }

            // LazyColumn with visible scrollbar
            LazyColumn(
                state = listState,
                contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 80.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScrollbar(listState)
            ) {
                itemsIndexed(filteredApps) { _, app ->
                    val isAppCurrentlyAnalyzing = activeJob?.packageName == app.packageName

                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = if (isAppCurrentlyAnalyzing)
                                MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.5f)
                            else
                                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                        ),
                        onClick = {
                            if (!isAppCurrentlyAnalyzing) onAppSelected(app)
                        }
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Image(
                                bitmap = app.icon,
                                contentDescription = null,
                                modifier = Modifier
                                    .size(50.dp)
                                    .clip(RoundedCornerShape(12.dp))
                            )
                            Spacer(modifier = Modifier.width(14.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = app.appName,
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                                Text(
                                    text = app.packageName,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            if (isAppCurrentlyAnalyzing) {
                                Surface(
                                    shape = RoundedCornerShape(10.dp),
                                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.15f)
                                ) {
                                    Row(
                                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text("Running", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                    }
                                }
                            } else {
                                Button(
                                    onClick = { onAppSelected(app) },
                                    shape = RoundedCornerShape(10.dp),
                                    contentPadding = PaddingValues(horizontal = 14.dp, vertical = 8.dp)
                                ) {
                                    Text("Analyze", fontWeight = FontWeight.SemiBold)
                                }
                            }
                        }
                    }
                }
            }
        }

        // Floating Scroll Helper Buttons for Emulator navigation
        Column(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(end = 16.dp, bottom = 16.dp)
        ) {
            SmallFloatingActionButton(
                onClick = {
                    coroutineScope.launch { listState.animateScrollToItem(0) }
                },
                containerColor = MaterialTheme.colorScheme.secondaryContainer,
                shape = CircleShape,
                modifier = Modifier.padding(bottom = 8.dp)
            ) {
                Icon(Icons.Default.KeyboardArrowUp, contentDescription = "Scroll to Top")
            }
            SmallFloatingActionButton(
                onClick = {
                    coroutineScope.launch {
                        if (filteredApps.isNotEmpty()) {
                            listState.animateScrollToItem(filteredApps.size - 1)
                        }
                    }
                },
                containerColor = MaterialTheme.colorScheme.secondaryContainer,
                shape = CircleShape
            ) {
                Icon(Icons.Default.KeyboardArrowDown, contentDescription = "Scroll to Bottom")
            }
        }
    }
}

@Composable
fun ResultScreen(result: UiState.Result, onBack: () -> Unit) {
    val context = LocalContext.current
    val report = result.report
    val leakCount = report.definitive_leaks_count
    val hasLeaks = leakCount > 0
    var selectedTab by remember { mutableIntStateOf(0) }

    Column(modifier = Modifier.fillMaxSize()) {
        // Executive Summary Banner
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            shape = RoundedCornerShape(18.dp),
            colors = CardDefaults.cardColors(
                containerColor = if (hasLeaks) Color(0xFFFFEBEE) else Color(0xFFE8F5E9)
            )
        ) {
            Column(modifier = Modifier.padding(18.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = if (hasLeaks) Icons.Default.Warning else Icons.Default.CheckCircle,
                        contentDescription = null,
                        tint = if (hasLeaks) Color(0xFFD32F2F) else Color(0xFF2E7D32),
                        modifier = Modifier.size(36.dp)
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Column {
                        Text(
                            text = result.appName,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )
                        Text(
                            text = if (hasLeaks) "Definitive Leaks Found: $leakCount" else "Clean - No Leaks Detected",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = if (hasLeaks) Color(0xFFD32F2F) else Color(0xFF2E7D32)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Metadata Chips
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    SuggestionChip(
                        onClick = {},
                        label = { Text("Engine: ${report.engine ?: "Static Multi-Tier"}") }
                    )
                    SuggestionChip(
                        onClick = {},
                        label = { Text(if (hasLeaks) "Risk: CRITICAL" else "Risk: LOW") }
                    )
                }
            }
        }

        // Tab Navigation
        TabRow(selectedTabIndex = selectedTab) {
            Tab(
                selected = selectedTab == 0,
                onClick = { selectedTab = 0 },
                text = { Text("Detected Leaks ($leakCount)") }
            )
            Tab(
                selected = selectedTab == 1,
                onClick = { selectedTab = 1 },
                text = { Text("Raw Evidence JSON") }
            )
        }

        // Tab Content
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
        ) {
            if (selectedTab == 0) {
                if (report.findings.isEmpty()) {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text("No leak paths recorded.", color = MaterialTheme.colorScheme.outline)
                    }
                } else {
                    val leakListState = rememberLazyListState()
                    LazyColumn(
                        state = leakListState,
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScrollbar(leakListState)
                    ) {
                        itemsIndexed(report.findings) { index, leak ->
                            LeakCard(index + 1, leak)
                        }
                    }
                }
            } else {
                // Raw JSON Tab
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Evidence Dump", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
                        TextButton(onClick = {
                            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                            val clip = ClipData.newPlainText("AndroidGuard Report", result.rawJson)
                            clipboard.setPrimaryClip(clip)
                            Toast.makeText(context, "Copied report to clipboard!", Toast.LENGTH_SHORT).show()
                        }) {
                            Text("Copy JSON")
                        }
                    }
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .weight(1f),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1E1E))
                    ) {
                        Text(
                            text = result.rawJson,
                            color = Color(0xFF00FF66),
                            fontFamily = FontFamily.Monospace,
                            fontSize = 11.sp,
                            modifier = Modifier
                                .verticalScroll(rememberScrollState())
                                .padding(12.dp)
                        )
                    }
                }
            }
        }

        // Action Buttons
        Surface(
            tonalElevation = 4.dp,
            modifier = Modifier.fillMaxWidth()
        ) {
            Button(
                onClick = onBack,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
                    .height(50.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Analyze Another App", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

@Composable
fun LeakCard(index: Int, leak: LeakFinding) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Leak #$index",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.error
                )
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = MaterialTheme.colorScheme.errorContainer
                ) {
                    Text(
                        text = leak.confidence ?: "CONFIRMED",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Source section
            Text(
                text = "SOURCE (Data Origin):",
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFE65100)
            )
            Text(
                text = leak.source?.target_signature ?: leak.source?.method ?: "Unknown Source",
                fontFamily = FontFamily.Monospace,
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier
                    .background(Color(0xFFFFF3E0), shape = RoundedCornerShape(6.dp))
                    .padding(6.dp)
                    .fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Sink section
            Text(
                text = "SINK (Data Exfiltration Point):",
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFB71C1C)
            )
            Text(
                text = leak.sink?.target_signature ?: leak.sink?.method ?: "Unknown Sink",
                fontFamily = FontFamily.Monospace,
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier
                    .background(Color(0xFFFFEBEE), shape = RoundedCornerShape(6.dp))
                    .padding(6.dp)
                    .fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Context info
            val className = leak.source?.className ?: leak.sink?.className ?: ""
            if (className.isNotEmpty()) {
                Text(
                    text = "Location: $className",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}

@Composable
fun ErrorScreen(error: String, onRetry: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Default.Warning,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.error,
            modifier = Modifier.size(64.dp)
        )
        Spacer(modifier = Modifier.height(18.dp))
        Text(
            text = "Analysis Failed",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.error
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = error,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(24.dp))
        Button(
            onClick = onRetry,
            shape = RoundedCornerShape(12.dp)
        ) {
            Text("Go Back")
        }
    }
}
