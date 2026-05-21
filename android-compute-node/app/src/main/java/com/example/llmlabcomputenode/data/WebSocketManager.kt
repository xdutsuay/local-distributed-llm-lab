package com.example.llmlabcomputenode.data

import android.content.Context
import android.net.TrafficStats
import android.os.Debug
import com.example.llmlabcomputenode.data.models.DataStats
import com.example.llmlabcomputenode.data.models.ExecuteTaskRequest
import com.example.llmlabcomputenode.data.models.ExecuteTaskResponse
import com.example.llmlabcomputenode.data.models.Heartbeat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okhttp3.Response
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID
import java.util.concurrent.TimeUnit

enum class ConnectionState {
    IDLE,
    CONNECTING,
    CONNECTED,
    DISCONNECTED
}

data class ProcessedTask(
    val id: String,
    val timestamp: String,
    val prompt: String,
    val response: String,
    val latencyMs: Long,
    val status: String,
    val logs: List<String> = emptyList()
)

class WebSocketManager(
    private val context: Context,
    private val scope: CoroutineScope
) {
    private val client = OkHttpClient.Builder()
        .readTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .connectTimeout(10, TimeUnit.SECONDS)
        .build()

    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    private val computeEngine = ComputeEngine(context)

    // User settings
    var coordinatorHost: String = "10.0.2.2" // Emulator default to host loopback
    var coordinatorPort: Int = 8000
    var nodeName: String = "Android-Compute-Node-${UUID.randomUUID().toString().take(4)}"
    var currentMode: ComputeMode = ComputeMode.MOCK_REASONING

    // State Flows
    private val _connectionState = MutableStateFlow(ConnectionState.IDLE)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _processedTasks = MutableStateFlow<List<ProcessedTask>>(emptyList())
    val processedTasks: StateFlow<List<ProcessedTask>> = _processedTasks.asStateFlow()

    private val _cpuUsage = MutableStateFlow(0f)
    val cpuUsage: StateFlow<Float> = _cpuUsage.asStateFlow()

    private val _ramUsage = MutableStateFlow(0f)
    val ramUsage: StateFlow<Float> = _ramUsage.asStateFlow()

    private var webSocket: WebSocket? = null
    private var connectionJob: Job? = null
    private var heartbeatJob: Job? = null
    private var statsJob: Job? = null
    private var isClosedIntentionally = false

    fun start() {
        isClosedIntentionally = false
        if (connectionJob?.isActive == true) return
        
        connectionJob = scope.launch(Dispatchers.IO) {
            connectLoop()
        }
        
        statsJob = scope.launch(Dispatchers.IO) {
            statsCollectionLoop()
        }
    }

    fun stop() {
        isClosedIntentionally = true
        connectionJob?.cancel()
        heartbeatJob?.cancel()
        statsJob?.cancel()
        webSocket?.close(1000, "Stopped intentionally")
        webSocket = null
        _connectionState.value = ConnectionState.IDLE
    }

    fun reconnect() {
        stop()
        start()
    }

    private suspend fun connectLoop() {
        while (!isClosedIntentionally) {
            if (_connectionState.value != ConnectionState.CONNECTED) {
                _connectionState.value = ConnectionState.CONNECTING
                val url = "ws://$coordinatorHost:$coordinatorPort/ws/join"
                val request = Request.Builder().url(url).build()
                
                webSocket = client.newWebSocket(request, SocketListener())
            }
            // Check connection status or delay before trying to reconnect if lost
            delay(5000)
        }
    }

    private suspend fun statsCollectionLoop() {
        while (true) {
            // Read simulated or runtime hardware usage
            val runtime = Runtime.getRuntime()
            val usedMem = (runtime.totalMemory() - runtime.freeMemory()).toFloat()
            val maxMem = runtime.maxMemory().toFloat()
            val ramPercent = if (maxMem > 0f) (usedMem / maxMem) * 100f else 0f
            
            // Mock CPU usage dynamically fluctuating
            val mockCpu = (20..65).random().toFloat()
            
            _ramUsage.value = ramPercent
            _cpuUsage.value = mockCpu
            
            delay(2000)
        }
    }

    private fun startHeartbeats(ws: WebSocket) {
        heartbeatJob?.cancel()
        heartbeatJob = scope.launch(Dispatchers.IO) {
            while (_connectionState.value == ConnectionState.CONNECTED) {
                try {
                    val stats = DataStats(
                        cpu_usage = _cpuUsage.value,
                        ram_usage = _ramUsage.value,
                        tasks_processed = _processedTasks.value.size,
                        compute_mode = currentMode.displayName
                    )
                    
                    val hb = Heartbeat(
                        node_id = nodeName,
                        capabilities = listOf("javascript_execution", "llm_inference", "mobile_compute"),
                        model = "Mobile-Compute-Node",
                        current_task = if (_connectionState.value == ConnectionState.CONNECTED) "Idle" else "Offline",
                        data_stats = stats,
                        api_base = "ws://$coordinatorHost:$coordinatorPort/ws/join",
                        timestamp = System.currentTimeMillis() / 1000.0
                    )
                    
                    val payload = json.encodeToString(hb)
                    ws.send(payload)
                } catch (e: Exception) {
                    e.printStackTrace()
                }
                delay(5000) // Heartbeat every 5 seconds
            }
        }
    }

    private inner class SocketListener : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            _connectionState.value = ConnectionState.CONNECTED
            // Start heartbeats immediately to register node
            startHeartbeats(webSocket)
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            scope.launch(Dispatchers.Default) {
                try {
                    val request = json.decodeFromString<ExecuteTaskRequest>(text)
                    if (request.type == "execute_task") {
                        handleExecuteTask(webSocket, request)
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            if (!isClosedIntentionally) {
                _connectionState.value = ConnectionState.DISCONNECTED
            }
            heartbeatJob?.cancel()
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            if (!isClosedIntentionally) {
                _connectionState.value = ConnectionState.DISCONNECTED
            }
            heartbeatJob?.cancel()
        }
    }

    private suspend fun handleExecuteTask(ws: WebSocket, request: ExecuteTaskRequest) {
        val startTime = System.currentTimeMillis()
        
        // Extract prompt
        val promptRegex = """const prompt\s*=\s*"(.*?)";""".toRegex()
        val promptMatch = promptRegex.find(request.code)
        val prompt = promptMatch?.groupValues?.get(1) ?: "Raw JavaScript Evaluation"

        try {
            val responsePayload = computeEngine.executeTask(request.code, currentMode)
            val duration = System.currentTimeMillis() - startTime
            
            val taskResponse = ExecuteTaskResponse(
                node_id = nodeName,
                task_id = request.task_id,
                response = responsePayload,
                status = "success"
            )
            
            ws.send(json.encodeToString(taskResponse))
            
            // Log successful task
            val sdf = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
            val formattedTime = sdf.format(Date(startTime))
            
            val processed = ProcessedTask(
                id = request.task_id,
                timestamp = formattedTime,
                prompt = prompt,
                response = responsePayload.summary,
                latencyMs = duration,
                status = "Success",
                logs = responsePayload.logs
            )
            
            _processedTasks.update { listOf(processed) + it.take(49) }
            
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - startTime
            val taskResponse = ExecuteTaskResponse(
                node_id = nodeName,
                task_id = request.task_id,
                response = com.example.llmlabcomputenode.data.models.TaskResponsePayload(
                    summary = "Execution failed: ${e.message}",
                    keywords = emptyList(),
                    clauses = emptyList(),
                    prompt_length = prompt.length,
                    execution_time_ms = duration
                ),
                status = "error",
                error = e.message
            )
            
            ws.send(json.encodeToString(taskResponse))
            
            val sdf = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
            val formattedTime = sdf.format(Date(startTime))
            
            val processed = ProcessedTask(
                id = request.task_id,
                timestamp = formattedTime,
                prompt = prompt,
                response = "Error: ${e.message}",
                latencyMs = duration,
                status = "Error",
                logs = listOf("Task crashed: ${e.message}")
            )
            
            _processedTasks.update { listOf(processed) + it.take(49) }
        }
    }
}
