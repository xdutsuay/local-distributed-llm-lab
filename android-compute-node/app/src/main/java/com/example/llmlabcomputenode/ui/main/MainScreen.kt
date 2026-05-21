package com.example.llmlabcomputenode.ui.main

import android.app.Application
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import java.util.Locale
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation3.runtime.NavKey
import com.example.llmlabcomputenode.data.ComputeMode
import com.example.llmlabcomputenode.data.ConnectionState
import com.example.llmlabcomputenode.data.ProcessedTask
import com.example.llmlabcomputenode.theme.DarkBackground
import com.example.llmlabcomputenode.theme.NeonCyan
import com.example.llmlabcomputenode.theme.NeonViolet
import com.example.llmlabcomputenode.theme.TextPrimary
import com.example.llmlabcomputenode.theme.TextSecondary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    onItemClick: (NavKey) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current.applicationContext as Application
    val viewModel: MainScreenViewModel = viewModel { MainScreenViewModel(context) }
    val connectionState by viewModel.connectionState.collectAsStateWithLifecycle()
    val tasks by viewModel.processedTasks.collectAsStateWithLifecycle()
    val cpuUsage by viewModel.cpuUsage.collectAsStateWithLifecycle()
    val ramUsage by viewModel.ramUsage.collectAsStateWithLifecycle()

    var activeTab by remember { mutableStateOf(0) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.DeveloperMode,
                            contentDescription = "Node Profile",
                            tint = NeonCyan,
                            modifier = Modifier.size(28.dp)
                        )
                        Column {
                            Text(
                                text = "LLM LAB",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = NeonCyan,
                                letterSpacing = 2.sp
                            )
                            Text(
                                text = "MOBILE COMPUTE NODE",
                                fontSize = 10.sp,
                                color = TextSecondary,
                                letterSpacing = 1.sp
                            )
                        }
                    }
                },
                actions = {
                    ConnectionPulseIndicator(connectionState)
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = DarkBackground,
                    titleContentColor = TextPrimary
                )
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = Color(0xFF131317),
                tonalElevation = 8.dp
            ) {
                NavigationBarItem(
                    selected = activeTab == 0,
                    onClick = { activeTab = 0 },
                    icon = { Icon(Icons.Rounded.Home, contentDescription = "Dashboard") },
                    label = { Text("Dashboard") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = NeonCyan,
                        selectedTextColor = NeonCyan,
                        indicatorColor = Color(0x2000F0FF),
                        unselectedIconColor = TextSecondary,
                        unselectedTextColor = TextSecondary
                    )
                )
                NavigationBarItem(
                    selected = activeTab == 1,
                    onClick = { activeTab = 1 },
                    icon = { Icon(Icons.Rounded.List, contentDescription = "Tasks") },
                    label = { Text("Tasks") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = NeonCyan,
                        selectedTextColor = NeonCyan,
                        indicatorColor = Color(0x2000F0FF),
                        unselectedIconColor = TextSecondary,
                        unselectedTextColor = TextSecondary
                    )
                )
                NavigationBarItem(
                    selected = activeTab == 2,
                    onClick = { activeTab = 2 },
                    icon = { Icon(Icons.Rounded.Settings, contentDescription = "Settings") },
                    label = { Text("Settings") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = NeonCyan,
                        selectedTextColor = NeonCyan,
                        indicatorColor = Color(0x2000F0FF),
                        unselectedIconColor = TextSecondary,
                        unselectedTextColor = TextSecondary
                    )
                )
            }
        },
        containerColor = DarkBackground
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(DarkBackground)
        ) {
            when (activeTab) {
                0 -> DashboardTab(
                    connectionState = connectionState,
                    cpuUsage = cpuUsage,
                    ramUsage = ramUsage,
                    totalTasks = tasks.size,
                    currentMode = viewModel.mode,
                    nodeName = viewModel.name,
                    host = viewModel.host
                )
                1 -> TasksTab(tasks = tasks)
                2 -> SettingsTab(
                    viewModel = viewModel
                )
            }
        }
    }
}

@Composable
fun ConnectionPulseIndicator(state: ConnectionState) {
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val scale by infiniteTransition.animateFloat(
        initialValue = 0.8f,
        targetValue = 1.3f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseScale"
    )

    val color by animateColorAsState(
        targetValue = when (state) {
            ConnectionState.CONNECTED -> NeonCyan
            ConnectionState.CONNECTING -> Color(0xFFFFB300)
            ConnectionState.DISCONNECTED -> Color(0xFFFF3D00)
            ConnectionState.IDLE -> Color.Gray
        },
        label = "statusColor"
    )

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(end = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(
            text = state.name,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            color = color,
            letterSpacing = 1.sp
        )
        Box(contentAlignment = Alignment.Center) {
            if (state == ConnectionState.CONNECTED || state == ConnectionState.CONNECTING) {
                Box(
                    modifier = Modifier
                        .size(16.dp)
                        .scale(scale)
                        .clip(CircleShape)
                        .background(color.copy(alpha = 0.4f))
                )
            }
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(color)
            )
        }
    }
}

@Composable
fun DashboardTab(
    connectionState: ConnectionState,
    cpuUsage: Float,
    ramUsage: Float,
    totalTasks: Int,
    currentMode: ComputeMode,
    nodeName: String,
    host: String
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Status Card
        item {
            GlassCard {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = "NODE TELEMETRY ACTIVE",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = NeonCyan,
                        letterSpacing = 2.sp
                    )
                    Text(
                        text = nodeName,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = Color.White
                    )
                    Text(
                        text = "Connected to master coordinator at $host",
                        fontSize = 12.sp,
                        color = TextSecondary,
                        textAlign = TextAlign.Center
                    )
                }
            }
        }

        // Hardware metrics
        item {
            GlassCard {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Text(
                        text = "RESOURCE MONITOR",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = NeonViolet,
                        letterSpacing = 2.sp
                    )

                    // CPU Usage
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text("CPU Activity", color = TextPrimary, fontSize = 14.sp)
                            Text("${cpuUsage.toInt()}%", color = NeonCyan, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                        LinearProgressIndicator(
                            progress = { cpuUsage / 100f },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(8.dp)
                                .clip(RoundedCornerShape(4.dp)),
                            color = NeonCyan,
                            trackColor = Color(0xFF1D262F)
                        )
                    }

                    // RAM Usage
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text("RAM Utilization", color = TextPrimary, fontSize = 14.sp)
                            Text("${ramUsage.toInt()}%", color = NeonViolet, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                        LinearProgressIndicator(
                            progress = { ramUsage / 100f },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(8.dp)
                                .clip(RoundedCornerShape(4.dp)),
                            color = NeonViolet,
                            trackColor = Color(0xFF261D2F)
                        )
                    }
                }
            }
        }

        // Compute Statistics
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Stat 1: Processed count
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(16.dp))
                        .background(Color(0xFF16161B))
                        .border(1.dp, Color(0x1AFFFFFF), RoundedCornerShape(16.dp))
                        .padding(16.dp)
                ) {
                    Column {
                        Text("TOTAL TASKS", fontSize = 10.sp, color = TextSecondary, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = totalTasks.toString(),
                            fontSize = 32.sp,
                            fontWeight = FontWeight.Black,
                            color = NeonCyan
                        )
                    }
                }

                // Stat 2: Active Profile
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(16.dp))
                        .background(Color(0xFF16161B))
                        .border(1.dp, Color(0x1AFFFFFF), RoundedCornerShape(16.dp))
                        .padding(16.dp)
                ) {
                    Column {
                        Text("COMPUTE PROFILE", fontSize = 10.sp, color = TextSecondary, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = currentMode.name.replace("_", " "),
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = NeonViolet,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun TasksTab(tasks: List<ProcessedTask>) {
    if (tasks.isEmpty()) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Icon(
                    imageVector = Icons.Rounded.Inbox,
                    contentDescription = "No tasks",
                    tint = TextSecondary,
                    modifier = Modifier.size(64.dp)
                )
                Text(
                    text = "No tasks processed yet.",
                    fontSize = 16.sp,
                    color = TextSecondary,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    text = "Waiting for Coordinator requests...",
                    fontSize = 12.sp,
                    color = TextSecondary.copy(alpha = 0.6f)
                )
            }
        }
    } else {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Text(
                    text = "LIVE TASK STREAM",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = NeonCyan,
                    letterSpacing = 2.sp,
                    modifier = Modifier.padding(bottom = 4.dp)
                )
            }
            items(tasks) { task ->
                TaskCard(task)
            }
        }
    }
}

@Composable
fun TaskCard(task: ProcessedTask) {
    var expanded by remember { mutableStateOf(false) }
    
    val statusColor = if (task.status == "Success") NeonCyan else Color(0xFFFF3D00)
    val statusIcon = if (task.status == "Success") Icons.Rounded.CheckCircle else Icons.Rounded.Error

    GlassCard {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .animateContentSize()
                .clickable { expanded = !expanded }
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Icon(
                        imageVector = statusIcon,
                        contentDescription = task.status,
                        tint = statusColor,
                        modifier = Modifier.size(18.dp)
                    )
                    Text(
                        text = "TASK // " + task.id.take(8).uppercase(Locale.ROOT),
                        color = Color.White,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace
                    )
                }
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(4.dp))
                        .background(statusColor.copy(alpha = 0.15f))
                        .padding(horizontal = 6.dp, vertical = 2.dp)
                ) {
                    Text(
                        text = "${task.latencyMs} ms",
                        color = statusColor,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            Text(
                text = "Prompt: ${task.prompt}",
                color = TextPrimary,
                fontSize = 14.sp,
                maxLines = if (expanded) 10 else 2,
                overflow = TextOverflow.Ellipsis
            )

            Text(
                text = "Result: ${task.response}",
                color = TextSecondary,
                fontSize = 13.sp,
                maxLines = if (expanded) 20 else 2,
                overflow = TextOverflow.Ellipsis
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = task.timestamp,
                    color = TextSecondary.copy(alpha = 0.6f),
                    fontSize = 11.sp
                )
                
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Text(
                        text = if (expanded) "Hide Thinking" else "Inspect Thinking",
                        fontSize = 11.sp,
                        color = NeonViolet,
                        fontWeight = FontWeight.Bold
                    )
                    Icon(
                        imageVector = if (expanded) Icons.Rounded.ExpandLess else Icons.Rounded.ExpandMore,
                        contentDescription = "Expand",
                        tint = NeonViolet,
                        modifier = Modifier.size(16.dp)
                    )
                }
            }

            if (expanded && task.logs.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Divider(color = Color(0x15FFFFFF))
                Spacer(modifier = Modifier.height(8.dp))
                
                Text(
                    text = "REASONING LOGS",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    color = NeonViolet,
                    letterSpacing = 1.sp
                )
                
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color(0xFF0F0F12))
                        .border(1.dp, Color(0x0FFFFFFF), RoundedCornerShape(8.dp))
                        .padding(10.dp)
                ) {
                    task.logs.forEach { log ->
                        Text(
                            text = "> $log",
                            color = NeonCyan,
                            fontSize = 12.sp,
                            fontFamily = FontFamily.Monospace,
                            modifier = Modifier.padding(vertical = 2.dp)
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun SettingsTab(viewModel: MainScreenViewModel) {
    var hostInput by remember { mutableStateOf(viewModel.host) }
    var portInput by remember { mutableStateOf(viewModel.port) }
    var nameInput by remember { mutableStateOf(viewModel.name) }
    var selectedMode by remember { mutableStateOf(viewModel.mode) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "COORDINATOR ROUTING",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = NeonCyan,
                letterSpacing = 2.sp
            )
        }

        // Connection fields
        item {
            GlassCard {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedTextField(
                        value = hostInput,
                        onValueChange = { hostInput = it },
                        label = { Text("Coordinator Host Address") },
                        modifier = Modifier.fillMaxWidth(),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = NeonCyan,
                            unfocusedBorderColor = Color(0x33FFFFFF),
                            focusedLabelColor = NeonCyan,
                            unfocusedLabelColor = TextSecondary
                        ),
                        singleLine = true
                    )

                    OutlinedTextField(
                        value = portInput,
                        onValueChange = { portInput = it },
                        label = { Text("Coordinator Port") },
                        modifier = Modifier.fillMaxWidth(),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = NeonCyan,
                            unfocusedBorderColor = Color(0x33FFFFFF),
                            focusedLabelColor = NeonCyan,
                            unfocusedLabelColor = TextSecondary
                        ),
                        singleLine = true
                    )

                    OutlinedTextField(
                        value = nameInput,
                        onValueChange = { nameInput = it },
                        label = { Text("Compute Node Identifier") },
                        modifier = Modifier.fillMaxWidth(),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = NeonCyan,
                            unfocusedBorderColor = Color(0x33FFFFFF),
                            focusedLabelColor = NeonCyan,
                            unfocusedLabelColor = TextSecondary
                        ),
                        singleLine = true
                    )
                }
            }
        }

        // Compute profiles selection
        item {
            Text(
                text = "COMPUTE PROFILE",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = NeonViolet,
                letterSpacing = 2.sp
            )
        }

        item {
            GlassCard {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    ComputeMode.values().forEach { mode ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(8.dp))
                                .clickable { selectedMode = mode }
                                .padding(8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            RadioButton(
                                selected = selectedMode == mode,
                                onClick = { selectedMode = mode },
                                colors = RadioButtonDefaults.colors(
                                    selectedColor = NeonCyan,
                                    unselectedColor = Color(0x33FFFFFF)
                                )
                            )
                            Column {
                                Text(
                                    text = mode.displayName,
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp
                                )
                                Text(
                                    text = when (mode) {
                                        ComputeMode.MOCK_REASONING -> "Simulates high-end reasoning inference with deep thoughts."
                                        ComputeMode.MATH_SOLVER -> "Direct arithmetic resolver evaluating math terms inside query."
                                        ComputeMode.JS_SANDBOX -> "Runs a fully-isolated WebView Javascript engine to execute actual code."
                                    },
                                    color = TextSecondary,
                                    fontSize = 12.sp
                                )
                            }
                        }
                    }
                }
            }
        }

        // Save & Reconnect Button
        item {
            Button(
                onClick = {
                    viewModel.applySettingsAndReconnect(
                        newHost = hostInput,
                        newPort = portInput,
                        newName = nameInput,
                        newMode = selectedMode
                    )
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp)
                    .clip(RoundedCornerShape(12.dp)),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.Transparent
                ),
                contentPadding = PaddingValues()
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(
                            Brush.horizontalGradient(
                                colors = listOf(NeonCyan, NeonViolet)
                            )
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(Icons.Rounded.Refresh, contentDescription = "Reconnect", tint = Color.Black)
                        Text(
                            text = "APPLY PROFILE & RECONNECT",
                            color = Color.Black,
                            fontWeight = FontWeight.ExtraBold,
                            fontSize = 14.sp,
                            letterSpacing = 1.sp
                        )
                    }
                }
            }
            Spacer(modifier = Modifier.height(20.dp))
        }
    }
}

@Composable
fun GlassCard(
    content: @Composable () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Color(0xFF131317))
            .border(1.dp, Color(0x12FFFFFF), RoundedCornerShape(16.dp))
    ) {
        content()
    }
}
