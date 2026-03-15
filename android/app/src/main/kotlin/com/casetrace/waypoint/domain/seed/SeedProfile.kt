package com.casetrace.waypoint.domain.seed

import com.casetrace.waypoint.data.local.CallType
import com.casetrace.waypoint.data.local.MessageDirection
import java.time.Instant

private fun iso(value: String) = Instant.parse(value)

data class SeedMessage(
    val id: Long,
    val timestamp: Instant,
    val actor: String,
    val counterparty: String,
    val body: String,
    val threadId: String,
    val read: Boolean,
    val direction: MessageDirection
)

data class SeedCall(
    val id: Long,
    val callType: CallType,
    val contactName: String,
    val timestampStart: Instant,
    val timestampEnd: Instant,
    val durationSeconds: Int,
    val summary: String
)

data class SeedBrowserVisit(
    val id: Long,
    val title: String,
    val url: String,
    val typedUrl: Boolean,
    val referrer: String?,
    val timestamp: Instant
)

data class SeedLocationPoint(
    val timestamp: Instant,
    val latitude: Double,
    val longitude: Double,
    val accuracy: Double,
    val label: String
)

data class SeedPhoto(
    val fileName: String,
    val timestamp: Instant,
    val summary: String,
    val latitude: Double,
    val longitude: Double,
    val deviceModel: String,
    val orientation: Int
)

data class SeedAppEvent(
    val timestamp: Instant,
    val summary: String,
    val eventType: String
)

data class SeedDeletedMessage(val timestamp: Instant, val actor: String, val counterparty: String, val body: String)

data class SeedDeletedBrowserVisit(val timestamp: Instant, val actor: String, val url: String, val title: String)

data class SeedProfile(
    val name: String,
    val messages: List<SeedMessage>,
    val calls: List<SeedCall>,
    val browsers: List<SeedBrowserVisit>,
    val locations: List<SeedLocationPoint>,
    val photos: List<SeedPhoto>,
    val events: List<SeedAppEvent>,
    val deletedMessage: SeedDeletedMessage,
    val deletedBrowserVisit: SeedDeletedBrowserVisit
)

object SeedProfiles {
    val caseAlpha: SeedProfile by lazy {
        SeedProfile(
            name = "case_alpha",
            messages = listOf(
                SeedMessage(1, iso("2026-03-12T12:10:00Z"), "Mira Chen", "Jordan Vega", "Asked Jordan to confirm the noon meetup near Harbor Cafe.", "thread-1", true, MessageDirection.INBOUND),
                SeedMessage(2, iso("2026-03-12T12:12:00Z"), "Jordan Vega", "Mira Chen", "Confirmed arrival via the East Line and said the blue folio would come along.", "thread-1", true, MessageDirection.OUTBOUND),
                SeedMessage(3, iso("2026-03-12T14:42:00Z"), "Riley Brooks", "Jordan Vega", "Sent the updated garage code and warned that parking closes at 19:30.", "thread-2", true, MessageDirection.INBOUND),
                SeedMessage(4, iso("2026-03-12T14:44:00Z"), "Jordan Vega", "Riley Brooks", "Acknowledged the garage note and said the backup stop was Union Transit Hall.", "thread-2", true, MessageDirection.OUTBOUND),
                SeedMessage(5, iso("2026-03-12T16:18:00Z"), "Noah Bennett", "Jordan Vega", "Shared an example tickets link and asked Jordan to review the event schedule.", "thread-3", true, MessageDirection.INBOUND),
                SeedMessage(6, iso("2026-03-12T16:20:00Z"), "Jordan Vega", "Noah Bennett", "Said the venue looked crowded and asked for an alternate coffee stop.", "thread-3", true, MessageDirection.OUTBOUND),
                SeedMessage(7, iso("2026-03-12T21:36:00Z"), "Mira Chen", "Jordan Vega", "Asked whether the meetup moved to the Market Square Hotel lobby.", "thread-1", false, MessageDirection.INBOUND),
                SeedMessage(8, iso("2026-03-12T21:38:00Z"), "Jordan Vega", "Mira Chen", "Confirmed a short stop at Market Square Hotel before heading north.", "thread-1", false, MessageDirection.OUTBOUND)
            ),
            calls = listOf(
                SeedCall(21, CallType.PLACED, "Alex Mercer", iso("2026-03-12T13:05:00Z"), iso("2026-03-12T13:09:00Z"), 240, "Outbound call discussing parking validation near North Pier Garage."),
                SeedCall(22, CallType.RECEIVED, "Noah Bennett", iso("2026-03-12T15:58:00Z"), iso("2026-03-12T16:02:00Z"), 240, "Inbound call about a schedule change at Harbor Cafe."),
                SeedCall(23, CallType.PLACED, "Mira Chen", iso("2026-03-12T20:48:00Z"), iso("2026-03-12T20:53:00Z"), 300, "Outbound call coordinating the meetup shift toward Riverside Market."),
                SeedCall(24, CallType.RECEIVED, "Riley Brooks", iso("2026-03-12T23:05:00Z"), iso("2026-03-12T23:07:00Z"), 120, "Inbound call asking whether Jordan cleared the garage before close.")
            ),
            browsers = listOf(
                SeedBrowserVisit(1, "Transit route planning", "https://maps.example/transit/east-line", true, null, iso("2026-03-12T12:22:00Z")),
                SeedBrowserVisit(2, "Garage rates", "https://parking.example/north-pier", false, "https://maps.example/transit/east-line", iso("2026-03-12T13:18:00Z")),
                SeedBrowserVisit(3, "Cafe menu", "https://harborcafe.example/menu", true, "https://parking.example/north-pier", iso("2026-03-12T15:47:00Z")),
                SeedBrowserVisit(4, "Ticket queue", "https://tickets.example/events/riverfront", false, "https://harborcafe.example/menu", iso("2026-03-12T16:24:00Z")),
                SeedBrowserVisit(5, "Riverside map", "https://maps.example/routes/riverside-market", true, "https://tickets.example/events/riverfront", iso("2026-03-12T21:12:00Z")),
                SeedBrowserVisit(6, "Hotel lobby hours", "https://marketsquarehotel.example/lobby-hours", false, "https://maps.example/routes/riverside-market", iso("2026-03-12T22:41:00Z"))
            ),
            locations = listOf(
                SeedLocationPoint(iso("2026-03-12T12:05:00Z"), 40.7527, -73.9772, 12.0, "Union Transit Hall"),
                SeedLocationPoint(iso("2026-03-12T12:28:00Z"), 40.7546, -73.9831, 9.5, "Eastline Books"),
                SeedLocationPoint(iso("2026-03-12T13:16:00Z"), 40.7489, -73.9854, 14.0, "North Pier Garage"),
                SeedLocationPoint(iso("2026-03-12T15:52:00Z"), 40.7418, -73.9892, 8.0, "Harbor Cafe"),
                SeedLocationPoint(iso("2026-03-12T16:27:00Z"), 40.7406, -73.9867, 10.0, "Riverfront Plaza"),
                SeedLocationPoint(iso("2026-03-12T18:10:00Z"), 40.7384, -73.9823, 11.5, "East Market Arcade"),
                SeedLocationPoint(iso("2026-03-12T20:45:00Z"), 40.7441, -73.9801, 7.8, "Riverside Market"),
                SeedLocationPoint(iso("2026-03-12T21:50:00Z"), 40.7468, -73.9777, 9.0, "Market Square Hotel"),
                SeedLocationPoint(iso("2026-03-12T23:12:00Z"), 40.7490, -73.9852, 13.0, "North Pier Garage"),
                SeedLocationPoint(iso("2026-03-13T00:02:00Z"), 40.7511, -73.9905, 15.0, "Night Ferry Terminal")
            ),
            photos = listOf(
                SeedPhoto("IMG_20260312_091300.jpg", iso("2026-03-12T13:13:00Z"), "Photo of a garage level marker with synthetic EXIF location data.", 40.7489, -73.9854, "Pixel 7 Pro", 1),
                SeedPhoto("IMG_20260312_122500.jpg", iso("2026-03-12T16:25:00Z"), "Photo of a receipt folder left on the Harbor Cafe table.", 40.7418, -73.9892, "Pixel 7 Pro", 1),
                SeedPhoto("IMG_20260312_171200.jpg", iso("2026-03-12T21:12:00Z"), "Photo of a storefront board near Riverside Market.", 40.7441, -73.9801, "Pixel 7 Pro", 6),
                SeedPhoto("IMG_20260312_192000.jpg", iso("2026-03-12T23:20:00Z"), "Photo of the hotel lobby directory before departure north.", 40.7468, -73.9777, "Pixel 7 Pro", 1)
            ),
            events = listOf(
                SeedAppEvent(iso("2026-03-12T12:06:00Z"), "Waypoint session start for the daily itinerary seed.", "session_start"),
                SeedAppEvent(iso("2026-03-12T12:23:00Z"), "Transit card module opened after the east-line lookup.", "transit_card_open"),
                SeedAppEvent(iso("2026-03-12T13:17:00Z"), "Parking note saved: North Pier Garage closes at 19:30.", "parking_note_saved"),
                SeedAppEvent(iso("2026-03-12T15:49:00Z"), "Meetup checklist marked active for the Harbor Cafe stop.", "meetup_checklist_armed"),
                SeedAppEvent(iso("2026-03-12T16:26:00Z"), "Route export generated for Riverfront Plaza.", "route_export_generated"),
                SeedAppEvent(iso("2026-03-12T20:46:00Z"), "Check-in marker created for Riverside Market.", "checkin_created"),
                SeedAppEvent(iso("2026-03-12T21:52:00Z"), "Briefcase note edited at Market Square Hotel.", "briefcase_note_edited"),
                SeedAppEvent(iso("2026-03-13T00:04:00Z"), "Session end and cached route archive written.", "session_end")
            ),
            deletedMessage = SeedDeletedMessage(
                iso("2026-03-12T11:48:00Z"),
                "Jordan Vega",
                "Mira Chen",
                "Draft asking to use the Harbor Cafe rear entrance."
            ),
            deletedBrowserVisit = SeedDeletedBrowserVisit(
                iso("2026-03-12T20:39:00Z"),
                "Jordan Vega",
                "https://maps.example/alleys/service-entry",
                "Alleys service entry"
            )
        )
    }
}
