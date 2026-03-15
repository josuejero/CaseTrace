package com.casetrace.waypoint.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.casetrace.waypoint.data.local.CallEntity
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val callFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("HH:mm z").withZone(ZoneId.of("America/New_York"))

@Composable
fun CallsScreen(calls: List<CallEntity>) {
    LazyColumn(modifier = Modifier.padding(8.dp)) {
        items(calls) { call ->
            CallRow(call)
        }
    }
}

@Composable
private fun CallRow(call: CallEntity) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(modifier = Modifier.fillMaxWidth()) {
                Text(call.contactName, style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                Text(
                    callFormatter.format(call.timestampStart),
                    style = MaterialTheme.typography.bodySmall
                )
            }
            Text(
                text = "${call.callType.name.lowercase().capitalize()} call • ${call.durationSeconds} sec",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 6.dp)
            )
            Text(call.summary, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(top = 4.dp))
            Text(
                callFormatter.format(call.timestampEnd),
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 2.dp)
            )
        }
    }
}
