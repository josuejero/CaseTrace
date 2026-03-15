package com.casetrace.waypoint.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import com.casetrace.waypoint.data.local.MessageEntity
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val messageFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("HH:mm z").withZone(ZoneId.of("America/New_York"))

@Composable
fun MessagesScreen(messages: List<MessageEntity>) {
    LazyColumn(modifier = Modifier.padding(8.dp)) {
        items(messages) { message ->
            MessageRow(message)
        }
    }
}

@Composable
private fun MessageRow(message: MessageEntity) {
    Card(modifier = Modifier
        .fillMaxWidth()
        .padding(vertical = 4.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "${message.sender} → ${message.recipient}",
                    style = MaterialTheme.typography.titleSmall
                )
                Text(
                    text = messageFormatter.format(message.timestamp),
                    style = MaterialTheme.typography.bodySmall
                )
            }
            Text(message.body, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(top = 4.dp))
            Text(
                text = "Thread ${message.threadId} • ${message.direction.name} • ${if (message.readFlag) "read" else "unread"}",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 6.dp)
            )
        }
    }
}
