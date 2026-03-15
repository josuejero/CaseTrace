package com.casetrace.waypoint

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Circle
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.casetrace.waypoint.domain.seed.SeedProfiles
import com.casetrace.waypoint.ui.screens.AppActivityScreen
import com.casetrace.waypoint.ui.screens.BrowserScreen
import com.casetrace.waypoint.ui.screens.CallsScreen
import com.casetrace.waypoint.ui.screens.LocationScreen
import com.casetrace.waypoint.ui.screens.MessagesScreen
import com.casetrace.waypoint.ui.screens.PhotoScreen
import com.casetrace.waypoint.ui.theme.CaseTraceTheme
import com.casetrace.waypoint.ui.viewmodel.MainViewModel
import com.casetrace.waypoint.ui.viewmodel.MainViewModelFactory
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val zoneId = ZoneId.of("America/New_York")
private val timestampFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm z").withZone(zoneId)

sealed class WaypointScreen(val route: String, val label: String) {
    object Messages : WaypointScreen("messages", "Messages")
    object Calls : WaypointScreen("calls", "Calls")
    object Browser : WaypointScreen("browser", "Browser")
    object Location : WaypointScreen("location", "Location")
    object Photos : WaypointScreen("photos", "Photos")
    object AppActivity : WaypointScreen("app_activity", "App Activity")
}

private val allScreens = listOf(
    WaypointScreen.Messages,
    WaypointScreen.Calls,
    WaypointScreen.Browser,
    WaypointScreen.Location,
    WaypointScreen.Photos,
    WaypointScreen.AppActivity
)

class MainActivity : ComponentActivity() {
    private val container by lazy { (application as WaypointApp).container }
    private val viewModel: MainViewModel by viewModels {
        MainViewModelFactory(container.repository, container.seedUseCase)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CaseTraceTheme {
                WaypointAppContent(viewModel)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WaypointAppContent(viewModel: MainViewModel) {
    val navController = rememberNavController()
    val snackbarHostState = remember { SnackbarHostState() }
    val seededAt by viewModel.seededAt.collectAsState()
    val mutatedAt by viewModel.mutatedAt.collectAsState()
    val messages by viewModel.messages.collectAsState(initial = emptyList())
    val calls by viewModel.calls.collectAsState(initial = emptyList())
    val photos by viewModel.photos.collectAsState(initial = emptyList())
    val browserVisits by viewModel.browserVisits.collectAsState(initial = emptyList())
    val appEvents by viewModel.appEvents.collectAsState(initial = emptyList())
    val locationPoints by viewModel.locationPoints.collectAsState()

    LaunchedEffect(viewModel.snackbar) {
        viewModel.snackbar.collect { snackbarHostState.showSnackbar(it) }
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        topBar = {
            WaypointTopBar(
                seededAt = seededAt,
                mutatedAt = mutatedAt,
                onSeed = { viewModel.seedDevice() },
                onMutate = { viewModel.mutateAndDelete() }
            )
        },
        bottomBar = { WaypointNavigationBar(navController) },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        content = { innerPadding ->
            NavHost(
                navController = navController,
                startDestination = WaypointScreen.Messages.route,
                modifier = Modifier.padding(innerPadding)
            ) {
                composable(WaypointScreen.Messages.route) {
                    MessagesScreen(messages)
                }
                composable(WaypointScreen.Calls.route) {
                    CallsScreen(calls)
                }
                composable(WaypointScreen.Browser.route) {
                    BrowserScreen(browserVisits)
                }
                composable(WaypointScreen.Location.route) {
                    LocationScreen(locationPoints)
                }
                composable(WaypointScreen.Photos.route) {
                    PhotoScreen(photos)
                }
                composable(WaypointScreen.AppActivity.route) {
                    AppActivityScreen(appEvents)
                }
            }
        }
    )
}

@Composable
fun WaypointTopBar(
    seededAt: Instant?,
    mutatedAt: Instant?,
    onSeed: () -> Unit,
    onMutate: () -> Unit
) {
    TopAppBar(
        title = {
            Row(modifier = Modifier.fillMaxWidth()) {
                Text("CaseTrace Waypoint", style = MaterialTheme.typography.titleMedium)
                Spacer(modifier = Modifier.width(12.dp))
                ColumnTimeline(seededAt, mutatedAt)
            }
        },
        actions = {
            TextButton(onClick = onSeed) {
                Text("Seed Device")
            }
            TextButton(onClick = onMutate) {
                Text("Mutate + Delete")
            }
        }
    )
}

@Composable
fun ColumnTimeline(seededAt: Instant?, mutatedAt: Instant?) {
    val seedLabel = seededAt?.let { "Seeded ${timestampFormatter.format(it)}" } ?: "Seed pending"
    val mutateLabel = mutatedAt?.let { "Mutated ${timestampFormatter.format(it)}" } ?: "Mutation pending"
    Column {
        Text(seedLabel, style = MaterialTheme.typography.bodySmall)
        Text(mutateLabel, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
fun WaypointNavigationBar(navController: NavHostController) {
    NavigationBar {
        val backStackEntry by navController.currentBackStackEntryAsState()
        val currentRoute = backStackEntry?.destination?.route
        allScreens.forEach { screen ->
                NavigationBarItem(
                    selected = currentRoute == screen.route,
                    onClick = {
                        navController.navigate(screen.route) {
                            popUpTo(WaypointScreen.Messages.route)
                            launchSingleTop = true
                        }
                    },
                    label = { Text(screen.label) },
                    icon = { Icon(Icons.Filled.Circle, contentDescription = null) }
                )
        }
    }
}
