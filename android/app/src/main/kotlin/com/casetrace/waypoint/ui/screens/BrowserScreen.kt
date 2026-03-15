package com.casetrace.waypoint.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.casetrace.waypoint.data.local.BrowserVisitEntity
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val browserFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("HH:mm z").withZone(ZoneId.of("America/New_York"))

@Composable
fun BrowserScreen(visits: List<BrowserVisitEntity>) {
    LazyColumn(modifier = Modifier.padding(8.dp)) {
        items(visits) { visit ->
            BrowserRow(visit)
        }
    }
}

@Composable
private fun BrowserRow(visit: BrowserVisitEntity) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                visit.url,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.clickable { }
            )
            Text(visit.title, style = MaterialTheme.typography.titleSmall)
            Column(modifier = Modifier.padding(top = 4.dp)) {
                Text("Visited at ${browserFormatter.format(visit.timestamp)}", style = MaterialTheme.typography.bodySmall)
                visit.referrer?.let { Text("Referrer: $it", style = MaterialTheme.typography.bodySmall) }
                Text("Typed URL: ${visit.typedUrl}", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
