package com.example.llmlabcomputenode.data

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.webkit.WebView
import com.example.llmlabcomputenode.data.models.TaskResponsePayload
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.util.Locale
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

enum class ComputeMode(val displayName: String) {
    MOCK_REASONING("Mock Reasoning Model"),
    MATH_SOLVER("Mathematical Execution"),
    JS_SANDBOX("JS WebView Sandbox")
}

class ComputeEngine(private val context: Context) {

    private val jsonParser = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
    }

    suspend fun executeTask(
        code: String,
        mode: ComputeMode
    ): TaskResponsePayload = withContext(Dispatchers.Default) {
        val startTime = System.currentTimeMillis()
        
        // Extract prompt if available in the code string (e.g., const prompt = "review dashboard";)
        val promptRegex = """const prompt\s*=\s*"(.*?)";""".toRegex()
        val promptMatch = promptRegex.find(code)
        val prompt = promptMatch?.groupValues?.get(1) ?: "No prompt extracted"

        val logs = mutableListOf<String>()
        val resultPayload = when (mode) {
            ComputeMode.MOCK_REASONING -> {
                logs.add("Initializing high-performance mobile compute profile...")
                Thread.sleep(300)
                logs.add("Extracted prompt: '$prompt'")
                logs.add("Analyzing linguistic patterns and semantics...")
                Thread.sleep(400)
                logs.add("Running mock inference step (temperature: 0.7)...")
                Thread.sleep(300)
                logs.add("Applying local tensor weights...")
                
                val stopwords = setOf("a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i", "if", "in", "into", "is", "it", "its", "me", "of", "on", "or", "our", "should", "that", "the", "their", "then", "this", "to", "we", "what", "when", "where", "which", "with", "you", "your")
                val words = prompt.lowercase(Locale.ROOT).split(Regex("[^a-zA-Z0-9']+")).filter { it.isNotEmpty() }
                val keywords = words.filter { it.length > 3 && it !in stopwords }.distinct().take(8)
                val clauses = prompt.split(Regex("[?.!,]|\\band\\b|\\bthen\\b", RegexOption.IGNORE_CASE)).map { it.trim() }.filter { it.isNotEmpty() }.take(4)
                val summary = clauses.firstOrNull() ?: prompt.take(120)

                logs.add("Formulating structural conclusion.")
                TaskResponsePayload(
                    kind = "browser_microgpt",
                    summary = "Reasoning Result: $summary",
                    keywords = keywords,
                    clauses = clauses,
                    prompt_length = prompt.length,
                    execution_time_ms = System.currentTimeMillis() - startTime,
                    logs = logs
                )
            }
            ComputeMode.MATH_SOLVER -> {
                logs.add("Math Engine activated.")
                logs.add("Searching prompt for arithmetic expressions: '$prompt'")
                
                // Look for arithmetic expressions e.g. "2 + 2", "12 * 45", etc.
                val mathRegex = """(\d+)\s*([\+\-\*/])\s*(\d+)""".toRegex()
                val mathMatch = mathRegex.find(prompt)
                
                val resultText = if (mathMatch != null) {
                    val num1 = mathMatch.groupValues[1].toDouble()
                    val op = mathMatch.groupValues[2]
                    val num2 = mathMatch.groupValues[3].toDouble()
                    logs.add("Found expression: $num1 $op $num2")
                    val result = when (op) {
                        "+" -> num1 + num2
                        "-" -> num1 - num2
                        "*" -> num1 * num2
                        "/" -> if (num2 != 0.0) num1 / num2 else Double.NaN
                        else -> 0.0
                    }
                    "Math Solver Result: $num1 $op $num2 = $result"
                } else {
                    logs.add("No explicit arithmetic found. Defaulting to string length calculations.")
                    "Calculated length of string is ${prompt.length}"
                }
                
                val stopwords = setOf("a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i", "if", "in", "into", "is", "it", "its", "me", "of", "on", "or", "our", "should", "that", "the", "their", "then", "this", "to", "we", "what", "when", "where", "which", "with", "you", "your")
                val words = prompt.lowercase(Locale.ROOT).split(Regex("[^a-zA-Z0-9']+")).filter { it.isNotEmpty() }
                val keywords = words.filter { it.length > 3 && it !in stopwords }.distinct().take(8)
                val clauses = prompt.split(Regex("[?.!,]|\\band\\b|\\bthen\\b", RegexOption.IGNORE_CASE)).map { it.trim() }.filter { it.isNotEmpty() }.take(4)
                
                logs.add("Math solver computation complete.")
                TaskResponsePayload(
                    kind = "browser_microgpt",
                    summary = resultText,
                    keywords = keywords,
                    clauses = clauses,
                    prompt_length = prompt.length,
                    execution_time_ms = System.currentTimeMillis() - startTime,
                    logs = logs
                )
            }
            ComputeMode.JS_SANDBOX -> {
                logs.add("Spinning up hidden WebView Javascript Sandbox...")
                val rawJsResult = executeJsInWebView(code)
                logs.add("WebView evaluated successfully. Raw result: $rawJsResult")
                
                // Parse returned JSON from evaluateJavascript
                try {
                    val jsonObj = jsonParser.parseToJsonElement(rawJsResult).jsonObject
                    val kind = jsonObj["kind"]?.jsonPrimitive?.content ?: "browser_microgpt"
                    val summary = jsonObj["summary"]?.jsonPrimitive?.content ?: ""
                    val keywords = jsonObj["keywords"]?.let { elem ->
                        try {
                            jsonParser.decodeFromString<List<String>>(elem.toString())
                        } catch (e: Exception) {
                            emptyList()
                        }
                    } ?: emptyList()
                    val clauses = jsonObj["clauses"]?.let { elem ->
                        try {
                            jsonParser.decodeFromString<List<String>>(elem.toString())
                        } catch (e: Exception) {
                            emptyList()
                        }
                    } ?: emptyList()
                    val promptLength = jsonObj["prompt_length"]?.jsonPrimitive?.content?.toIntOrNull() ?: prompt.length
                    
                    logs.add("Parsed JSON fields from sandbox.")
                    TaskResponsePayload(
                        kind = kind,
                        summary = summary,
                        keywords = keywords,
                        clauses = clauses,
                        prompt_length = promptLength,
                        execution_time_ms = System.currentTimeMillis() - startTime,
                        logs = logs
                    )
                } catch (e: Exception) {
                    logs.add("Failed to parse WebView JSON: ${e.message}. Falling back.")
                    TaskResponsePayload(
                        kind = "browser_microgpt",
                        summary = "Raw WebView Output: $rawJsResult",
                        keywords = listOf("webview", "error"),
                        clauses = listOf(prompt),
                        prompt_length = prompt.length,
                        execution_time_ms = System.currentTimeMillis() - startTime,
                        logs = logs
                    )
                }
            }
        }
        
        resultPayload
    }

    private suspend fun executeJsInWebView(code: String): String = suspendCancellableCoroutine { cont ->
        Handler(Looper.getMainLooper()).post {
            try {
                val webView = WebView(context)
                webView.settings.javaScriptEnabled = true
                
                // The evaluateJavascript requires a expression that returns a value.
                // Since the provided code has "return {...}", we wrap it inside a self-invoking function:
                val wrappedCode = "(function() {\n$code\n})()"
                
                webView.evaluateJavascript(wrappedCode) { result ->
                    if (cont.isActive) {
                        if (result == null || result == "null") {
                            cont.resume("{}")
                        } else {
                            // Android's evaluateJavascript returns double-quoted or escaped string representation of the JSON object.
                            // We need to unescape if it's a JSON string.
                            val cleaned = if (result.startsWith("\"") && result.endsWith("\"") && result.length > 1) {
                                // Simple unescape
                                result.substring(1, result.length - 1)
                                    .replace("\\\"", "\"")
                                    .replace("\\\\", "\\")
                            } else {
                                result
                            }
                            cont.resume(cleaned)
                        }
                    }
                }
            } catch (e: Exception) {
                if (cont.isActive) {
                    cont.resumeWithException(e)
                }
            }
        }
    }
}
