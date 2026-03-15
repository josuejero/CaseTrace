package com.casetrace.waypoint.ui.screens

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
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
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.asImageBitmap
import com.casetrace.waypoint.data.local.PhotoEntity
import java.io.File
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val photoFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm").withZone(ZoneId.of("America/New_York"))

@Composable
fun PhotoScreen(photos: List<PhotoEntity>) {
    LazyColumn(modifier = Modifier.padding(8.dp)) {
        items(photos) { photo ->
            PhotoRow(photo)
        }
    }
}

@Composable
private fun PhotoRow(photo: PhotoEntity) {
    val context = LocalContext.current
    val bitmap = remember(photo.fileName) {
        val file = File(context.filesDir, "media/${photo.fileName}")
        file.takeIf { it.exists() }?.let { BitmapFactory.decodeFile(it.absolutePath) }
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            bitmap?.let {
                Image(
                    bitmap = it.asImageBitmap(),
                    contentDescription = photo.summary,
                    modifier = Modifier.fillMaxWidth()
                )
            }
            Text(photo.summary, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(top = 6.dp))
            Text(
                text = photoFormatter.format(photo.timestamp),
                style = MaterialTheme.typography.bodySmall
            )
            Text(
                text = "${photo.latitude}, ${photo.longitude} • ${photo.deviceModel} • orientation ${photo.orientation}",
                style = MaterialTheme.typography.bodySmall
            )
            Text(
                text = photo.fileName,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 2.dp)
            )
        }
    }
}
