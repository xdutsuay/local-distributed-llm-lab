package com.example.llmlabcomputenode.data.models

import kotlinx.serialization.Serializable

@Serializable
data class DataStats(
    val cpu_usage: Float,
    val ram_usage: Float,
    val tasks_processed: Int,
    val compute_mode: String
)

@Serializable
data class Heartbeat(
    val node_id: String,
    val capabilities: List<String>,
    val model: String = "Llama-3-Mobile",
    val current_task: String = "",
    val data_stats: DataStats,
    val api_base: String = "",
    val timestamp: Double
)

@Serializable
data class ExecuteTaskRequest(
    val type: String, // "execute_task"
    val task_id: String,
    val code: String,
    val timestamp: Double
)

@Serializable
data class TaskResponsePayload(
    val kind: String = "browser_microgpt",
    val summary: String,
    val keywords: List<String>,
    val clauses: List<String>,
    val prompt_length: Int,
    val execution_time_ms: Long,
    val logs: List<String> = emptyList()
)

@Serializable
data class ExecuteTaskResponse(
    val node_id: String,
    val task_id: String,
    val response: TaskResponsePayload,
    val status: String, // "success", "error"
    val error: String? = null
)
