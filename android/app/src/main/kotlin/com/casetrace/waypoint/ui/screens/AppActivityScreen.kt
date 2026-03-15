package com.casetrace.waypoint.ui.screens

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
import com.casetrace.waypoint.data.local.AppEventEntity
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val eventFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("HH:mm z").withZone(ZoneId.of("America/New_York"))

@Composable
fun AppActivityScreen(events: List<AppEventEntity>) {
    LazyColumn(modifier = Modifier.padding(8.dp)) {
        items(events) { event ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    RowSummary(event)
                }
            }
        }
    }
}

@Composable
private fun RowSummary(event: AppEventEntity) {
    Text(event.eventType, style = MaterialTheme.typography.titleSmall)
    Text(event.summary, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(top = 4.dp))
    Text(
        text = eventFormatter.format(event.timestampStart),
        style = MaterialTheme.typography.bodySmall,
        modifier = Modifier.padding(top = 4.dp)
    )
}
