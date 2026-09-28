package org.projecteden.farmermobile

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
import org.projecteden.farmermobile.ui.screens.cropplan.CropPlanScreen
import org.projecteden.farmermobile.ui.screens.history.AdviceHistoryScreen
import org.projecteden.farmermobile.ui.screens.myfarm.MyFarmScreen
import org.projecteden.farmermobile.ui.screens.rotationdetail.RotationDetailScreen
import org.projecteden.farmermobile.ui.screens.today.TodayAdviceScreen

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
                        backStack.add(RotationDetailNavKey)
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
        }
    )
}

@Composable
fun EdenMainScaffold(
    onNavigateToDetail: () -> Unit
) {
    var selectedTab by rememberSaveable { mutableStateOf(EdenTab.TODAY) }

    Scaffold(
        containerColor = Surface,
        bottomBar = {
            EdenBottomNavBar(
                selectedTab = selectedTab,
                onTabSelected = { tab ->
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
                        onNavigateToPlan = {
                            selectedTab = EdenTab.PLAN
                        }
                    )
                }
                EdenTab.PLAN -> {
                    CropPlanScreen(
                        onNavigateToDetail = onNavigateToDetail
                    )
                }
                EdenTab.HISTORY -> {
                    AdviceHistoryScreen(
                        onNavigateToDetail = onNavigateToDetail
                    )
                }
                EdenTab.FARM -> {
                    MyFarmScreen()
                }
            }
        }
    }
}
