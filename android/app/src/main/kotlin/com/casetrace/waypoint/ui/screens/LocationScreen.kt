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
import com.casetrace.waypoint.domain.seed.SeedLocationPoint
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val locationFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("HH:mm z").withZone(ZoneId.of("America/New_York"))

@Composable
fun LocationScreen(locations: List<SeedLocationPoint>) {
    LazyColumn(modifier = Modifier.padding(8.dp)) {
        items(locations) { location ->
            LocationRow(location)
        }
    }
}

@Composable
private fun LocationRow(location: SeedLocationPoint) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(location.label, style = MaterialTheme.typography.titleSmall)
            Text(
                text = locationFormatter.format(location.timestamp),
                style = MaterialTheme.typography.bodySmall
            )
            Text(
                text = "${location.latitude}, ${location.longitude} • ±${location.accuracy}m",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 4.dp)
            )
        }
    }
}
