package com.example.llmlabcomputenode.ui.main

import com.example.llmlabcomputenode.data.models.ExecuteTaskRequest
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Test

class MainScreenViewModelTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun parseExecuteTaskRequest_fromCoordinatorPayload() {
        val raw = """
            {
              "type": "execute_task",
              "task_id": "task-abc",
              "code": "const prompt = \"hello\"; return { kind: \"browser_microgpt\", summary: \"hello\" };",
              "timestamp": 1710000000.0
            }
        """.trimIndent()
        val request = json.decodeFromString<ExecuteTaskRequest>(raw)
        assertEquals("execute_task", request.type)
        assertEquals("task-abc", request.task_id)
    }
}
