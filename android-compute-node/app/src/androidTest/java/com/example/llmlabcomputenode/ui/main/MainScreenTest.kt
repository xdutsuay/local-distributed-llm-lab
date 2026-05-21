package com.example.llmlabcomputenode.ui.main

import androidx.activity.ComponentActivity
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.navigation3.runtime.NavKey
import org.junit.Rule
import org.junit.Test

/** UI smoke test for [MainScreen]. */
class MainScreenTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun mainScreen_renders_title() {
        composeTestRule.setContent {
            MainScreen(onItemClick = { _: NavKey -> })
        }
        composeTestRule.onNodeWithText("LLM LAB").assertExists()
    }
}
