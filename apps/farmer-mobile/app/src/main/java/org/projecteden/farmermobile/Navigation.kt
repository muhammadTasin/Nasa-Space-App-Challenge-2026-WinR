package org.projecteden.farmermobile

import android.util.Log
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.ui.NavDisplay
import org.projecteden.farmermobile.theme.Surface
import org.projecteden.farmermobile.ui.components.EdenBottomNavBar
import org.projecteden.farmermobile.ui.components.EdenTab
import org.projecteden.farmermobile.ui.screens.ai.AiAssistantScreen
import org.projecteden.farmermobile.ui.screens.cropplan.CropPlanScreen
import org.projecteden.farmermobile.ui.screens.erosion.RiverErosionScreen
import org.projecteden.farmermobile.ui.screens.history.AdviceHistoryScreen
import org.projecteden.farmermobile.ui.screens.myfarm.MyFarmScreen
import org.projecteden.farmermobile.ui.screens.rotationdetail.RotationDetailScreen
import org.projecteden.farmermobile.ui.screens.today.TodayAdviceScreen
import org.projecteden.farmermobile.ui.screens.weather.WeatherScreen

@Composable
fun MainNavigation() {
    val backStack = rememberNavBackStack(MainNavKey)

    NavDisplay(
        backStack = backStack,
        onBack = {
            if (backStack.size > 1) {
                backStack.removeLastOrNull()
            }
        },
        entryProvider = entryProvider {
            entry<MainNavKey> {
                EdenMainScaffold(
                    onNavigateToDetail = {
                        Log.i("EDEN_APP", "rotation_detail_opened")
                        backStack.add(RotationDetailNavKey)
                    },
                    onNavigateToPlan = {
                        Log.i("EDEN_APP", "crop_plan_opened")
                        backStack.add(CropPlanNavKey)
                    },
                    onNavigateToHistory = {
                        Log.i("EDEN_APP", "advice_history_opened")
                        backStack.add(AdviceHistoryNavKey)
                    }
                )
            }
            entry<RotationDetailNavKey> {
                RotationDetailScreen(
                    onBack = {
                        backStack.removeLastOrNull()
                    }
                )
            }
            entry<CropPlanNavKey> {
                CropPlanScreen(
                    onNavigateToDetail = {
                        backStack.add(RotationDetailNavKey)
                    }
                )
            }
            entry<AdviceHistoryNavKey> {
                AdviceHistoryScreen(
                    onNavigateToDetail = {
                        backStack.add(RotationDetailNavKey)
                    }
                )
            }
        }
    )
}

@Composable
fun EdenMainScaffold(
    onNavigateToDetail: () -> Unit,
    onNavigateToPlan: () -> Unit,
    onNavigateToHistory: () -> Unit
) {
    var selectedTab by rememberSaveable { mutableStateOf(EdenTab.TODAY) }

    Scaffold(
        containerColor = Surface,
        bottomBar = {
            EdenBottomNavBar(
                selectedTab = selectedTab,
                onTabSelected = { tab ->
                    Log.i("EDEN_APP", "tab_selected:${tab.name.lowercase()}")
                    selectedTab = tab
                }
            )
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (selectedTab) {
                EdenTab.TODAY -> {
                    TodayAdviceScreen(
                        onNavigateToPlan = onNavigateToPlan,
                        onNavigateToProfile = { selectedTab = EdenTab.FARM }
                    )
                }
                EdenTab.WEATHER -> {
                    WeatherScreen(
                        onNavigateToProfile = { selectedTab = EdenTab.FARM }
                    )
                }
                EdenTab.EROSION -> {
                    RiverErosionScreen(
                        onNavigateToProfile = { selectedTab = EdenTab.FARM }
                    )
                }
                EdenTab.AI -> {
                    AiAssistantScreen(
                        onNavigateToProfile = { selectedTab = EdenTab.FARM }
                    )
                }
                EdenTab.FARM -> {
                    MyFarmScreen()
                }
            }
        }
    }
}
