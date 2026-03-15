package com.casetrace.waypoint.domain

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import androidx.exifinterface.media.ExifInterface
import androidx.room.withTransaction
import com.casetrace.waypoint.data.local.*
import com.casetrace.waypoint.domain.seed.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import kotlin.math.abs
import kotlin.random.Random

private const val CASE_ID = "CT-2026-001"
private val EXIF_DATE_FORMAT: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyy:MM:dd HH:mm:ss").withZone(ZoneOffset.UTC)

class SeedUseCase(
    private val coreDatabase: CoreDatabase,
    private val webDatabase: WebDatabase,
    private val context: Context
) {
    suspend fun seed(profile: SeedProfile) = withContext(Dispatchers.IO) {
        val random = Random(profile.name.hashCode().toLong())
        coreDatabase.clearAllTables()
        webDatabase.clearAllTables()

        val messageDao = coreDatabase.messageDao()
        val callDao = coreDatabase.callDao()
        val photoDao = coreDatabase.photoDao()
        val eventDao = coreDatabase.appEventDao()
        val browserDao = webDatabase.browserVisitDao()

        messageDao.insertAll(*profile.messages.map { it.toEntity() }.toTypedArray())
        callDao.insertAll(*profile.calls.map { it.toEntity() }.toTypedArray())
        browserDao.insertAll(*profile.browsers.map { it.toEntity() }.toTypedArray())
        eventDao.insertAll(*profile.events.map { it.toEntity() }.toTypedArray())

        profile.photos.forEach { seedPhoto ->
            createPhotoAsset(seedPhoto, random)
            photoDao.insert(seedPhoto.toEntity())
        }

        writeLocationExport(profile.locations)
        writeAppEventLog(profile.events)
    }

    suspend fun mutateAndDelete(profile: SeedProfile) = withContext(Dispatchers.IO) {
        val messageDao = coreDatabase.messageDao()
        val browserDao = webDatabase.browserVisitDao()
        val mutatedMessage = profile.messages.first()
        val mutatedBrowser = profile.browsers.first()

        coreDatabase.withTransaction {
            messageDao.insertAll(
                MessageEntity(
                    id = mutatedMessage.id + 100,
                    threadId = "mutate-${profile.name}",
                    direction = mutatedMessage.direction,
                    timestamp = profile.deletedMessage.timestamp,
                    sender = profile.deletedMessage.actor,
                    recipient = profile.deletedMessage.counterparty,
                    body = profile.deletedMessage.body,
                    readFlag = false,
                    deletedFlag = true
                )
            )
            messageDao.update(
                mutatedMessage.copy(body = "[mutated] ${mutatedMessage.body}").toEntity()
            )
            messageDao.deleteById(mutatedMessage.id)
        }

        webDatabase.withTransaction {
            val newVisitId = mutatedBrowser.id + 100
            browserDao.insertAll(
                BrowserVisitEntity(
                    id = newVisitId,
                    title = profile.deletedBrowserVisit.title,
                    url = profile.deletedBrowserVisit.url,
                    typedUrl = true,
                    referrer = null,
                    timestamp = profile.deletedBrowserVisit.timestamp
                )
            )
            browserDao.deleteById(newVisitId)
        }
    }

    private fun writeLocationExport(points: List<com.casetrace.waypoint.domain.seed.SeedLocationPoint>) {
        val exportsDir = File(context.filesDir, "exports").apply { mkdirs() }
        val target = File(exportsDir, "location_trace.json")
        val root = JSONObject().apply {
            put("case_id", CASE_ID)
            val array = JSONArray()
            points.forEach {
                array.put(
                    JSONObject().apply {
                        put("timestamp_utc", it.timestamp.toString())
                        put("label", it.label)
                        put("latitude", it.latitude)
                        put("longitude", it.longitude)
                        put("accuracy_m", it.accuracy)
                    }
                )
            }
            put("points", array)
        }
        target.writeText(root.toString(2))
    }

    private fun writeAppEventLog(events: List<com.casetrace.waypoint.domain.seed.SeedAppEvent>) {
        val logsDir = File(context.filesDir, "logs").apply { mkdirs() }
        val target = File(logsDir, "app-events-20260312.jsonl")
        target.bufferedWriter().use { writer ->
            events.forEach { event ->
                val line = "{\"timestamp_utc\":\"${event.timestamp}\",\"event\":\"${event.eventType}\",\"summary\":\"${escapeJson(event.summary)}\"}"
                writer.appendLine(line)
            }
        }
    }

    private fun createPhotoAsset(photo: com.casetrace.waypoint.domain.seed.SeedPhoto, random: Random) {
        val mediaDir = File(context.filesDir, "media").apply { mkdirs() }
        val file = File(mediaDir, photo.fileName)
        val size = 640
        val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        val fillColor = Color.rgb(
            random.nextInt(64, 200),
            random.nextInt(64, 200),
            random.nextInt(64, 200)
        )
        canvas.drawColor(fillColor)
        val paint = Paint().apply {
            color = Color.WHITE
            textSize = 32f
            isAntiAlias = true
        }
        canvas.drawText(photo.fileName, 24f, size / 2f + 16f, paint)
        file.outputStream().use { bitmap.compress(Bitmap.CompressFormat.JPEG, 85, it) }
        val exif = ExifInterface(file)
        exif.setAttribute(ExifInterface.TAG_DATETIME_ORIGINAL, photo.timestamp.toExifString())
        exif.setAttribute(ExifInterface.TAG_DATETIME, photo.timestamp.toExifString())
        exif.setAttribute(ExifInterface.TAG_MODEL, photo.deviceModel)
        exif.setAttribute(ExifInterface.TAG_ORIENTATION, photo.orientation.toString())
        exif.setAttribute(ExifInterface.TAG_GPS_LATITUDE, photo.latitude.toExifCoordinate())
        exif.setAttribute(ExifInterface.TAG_GPS_LATITUDE_REF, if (photo.latitude >= 0) "N" else "S")
        exif.setAttribute(ExifInterface.TAG_GPS_LONGITUDE, photo.longitude.toExifCoordinate())
        exif.setAttribute(ExifInterface.TAG_GPS_LONGITUDE_REF, if (photo.longitude >= 0) "E" else "W")
        exif.saveAttributes()
    }

    private fun com.casetrace.waypoint.domain.seed.SeedMessage.toEntity() = MessageEntity(
        id = id,
        threadId = threadId,
        direction = direction,
        timestamp = timestamp,
        sender = actor,
        recipient = counterparty,
        body = body,
        readFlag = read,
        deletedFlag = false
    )

    private fun com.casetrace.waypoint.domain.seed.SeedCall.toEntity() = CallEntity(
        id = id,
        callType = callType,
        contactName = contactName,
        timestampStart = timestampStart,
        timestampEnd = timestampEnd,
        durationSeconds = durationSeconds,
        summary = summary
    )

    private fun com.casetrace.waypoint.domain.seed.SeedBrowserVisit.toEntity() = BrowserVisitEntity(
        id = id,
        title = title,
        url = url,
        typedUrl = typedUrl,
        referrer = referrer,
        timestamp = timestamp
    )

    private fun com.casetrace.waypoint.domain.seed.SeedPhoto.toEntity() = PhotoEntity(
        fileName = fileName,
        timestamp = timestamp,
        summary = summary,
        latitude = latitude,
        longitude = longitude,
        deviceModel = deviceModel,
        orientation = orientation
    )

    private fun com.casetrace.waypoint.domain.seed.SeedAppEvent.toEntity() = AppEventEntity(
        eventType = eventType,
        timestampStart = timestamp,
        timestampEnd = timestamp,
        summary = summary
    )

    private fun escapeJson(value: String) = value.replace("\"", "\\\"")

    private fun Double.toExifCoordinate(): String {
        val absolute = abs(this)
        val degrees = absolute.toInt()
        val minutesFull = (absolute - degrees) * 60
        val minutes = minutesFull.toInt()
        val seconds = ((minutesFull - minutes) * 60)
        return "${degrees}/1,${minutes}/1,${(seconds * 100).toInt()}/100"
    }

    private fun Instant.toExifString(): String = EXIF_DATE_FORMAT.format(this)
}
