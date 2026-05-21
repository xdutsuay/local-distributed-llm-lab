package com.example.llmlabcomputenode.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val NeonDarkColorScheme = darkColorScheme(
    primary = NeonCyan,
    secondary = NeonViolet,
    background = DarkGraphite,
    surface = CardBackground,
    onPrimary = Color.Black,
    onSecondary = Color.White,
    onBackground = TextPrimary,
    onSurface = TextPrimary
)

@Composable
fun LLMLabComputeNodeTheme(
    darkTheme: Boolean = true, // Force premium dark mode for performance console style
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = NeonDarkColorScheme,
        typography = Typography,
        content = content
    )
}
