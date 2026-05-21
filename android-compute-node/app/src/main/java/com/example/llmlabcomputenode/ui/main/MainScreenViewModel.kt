package com.example.llmlabcomputenode.ui.main

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.llmlabcomputenode.data.ComputeMode
import com.example.llmlabcomputenode.data.ConnectionState
import com.example.llmlabcomputenode.data.ProcessedTask
import com.example.llmlabcomputenode.data.WebSocketManager
import kotlinx.coroutines.flow.StateFlow

class MainScreenViewModel(application: Application) : AndroidViewModel(application) {
    
    val webSocketManager = WebSocketManager(application, viewModelScope)

    val connectionState: StateFlow<ConnectionState> = webSocketManager.connectionState
    val processedTasks: StateFlow<List<ProcessedTask>> = webSocketManager.processedTasks
    val cpuUsage: StateFlow<Float> = webSocketManager.cpuUsage
    val ramUsage: StateFlow<Float> = webSocketManager.ramUsage

    // Expose settings directly
    var host: String
        get() = webSocketManager.coordinatorHost
        set(value) {
            webSocketManager.coordinatorHost = value
        }

    var port: String
        get() = webSocketManager.coordinatorPort.toString()
        set(value) {
            webSocketManager.coordinatorPort = value.toIntOrNull() ?: 8000
        }

    var name: String
        get() = webSocketManager.nodeName
        set(value) {
            webSocketManager.nodeName = value
        }

    var mode: ComputeMode
        get() = webSocketManager.currentMode
        set(value) {
            webSocketManager.currentMode = value
        }

    init {
        // Start connection on initialization
        webSocketManager.start()
    }

    fun applySettingsAndReconnect(newHost: String, newPort: String, newName: String, newMode: ComputeMode) {
        host = newHost
        port = newPort
        name = newName
        mode = newMode
        webSocketManager.reconnect()
    }

    override fun onCleared() {
        super.onCleared()
        webSocketManager.stop()
    }
}
