\"\"\"Seed data used by the artifact generators.\"\"\"
from __future__ import annotations

MESSAGES = [
    {
        "id": 1,
        "thread_id": "thread-1",
        "actor": "Mira Chen",
        "counterparty": "Jordan Vega",
        "timestamp": "2026-03-12T12:10:00Z",
        "body": "Asked Jordan to confirm the noon meetup near Harbor Cafe.",
        "direction": "INBOUND",
    },
    {
        "id": 2,
        "thread_id": "thread-1",
        "actor": "Jordan Vega",
        "counterparty": "Mira Chen",
        "timestamp": "2026-03-12T12:12:00Z",
        "body": "Confirmed arrival via the East Line and said the blue folio would come along.",
        "direction": "OUTBOUND",
    },
    {
        "id": 3,
        "thread_id": "thread-2",
        "actor": "Riley Brooks",
        "counterparty": "Jordan Vega",
        "timestamp": "2026-03-12T14:42:00Z",
        "body": "Sent the updated garage code and warned that parking closes at 19:30.",
        "direction": "INBOUND",
    },
    {
        "id": 4,
        "thread_id": "thread-2",
        "actor": "Jordan Vega",
        "counterparty": "Riley Brooks",
        "timestamp": "2026-03-12T14:44:00Z",
        "body": "Acknowledged the garage note and said the backup stop was Union Transit Hall.",
        "direction": "OUTBOUND",
    },
    {
        "id": 5,
        "thread_id": "thread-3",
        "actor": "Noah Bennett",
        "counterparty": "Jordan Vega",
        "timestamp": "2026-03-12T16:18:00Z",
        "body": "Shared an example tickets link and asked Jordan to review the event schedule.",
        "direction": "INBOUND",
    },
    {
        "id": 6,
        "thread_id": "thread-3",
        "actor": "Jordan Vega",
        "counterparty": "Noah Bennett",
        "timestamp": "2026-03-12T16:20:00Z",
        "body": "Said the venue looked crowded and asked for an alternate coffee stop.",
        "direction": "OUTBOUND",
    },
    {
        "id": 7,
        "thread_id": "thread-1",
        "actor": "Mira Chen",
        "counterparty": "Jordan Vega",
        "timestamp": "2026-03-12T21:36:00Z",
        "body": "Asked whether the meetup moved to the Market Square Hotel lobby.",
        "direction": "INBOUND",
    },
    {
        "id": 8,
        "thread_id": "thread-1",
        "actor": "Jordan Vega",
        "counterparty": "Mira Chen",
        "timestamp": "2026-03-12T21:38:00Z",
        "body": "Confirmed a short stop at Market Square Hotel before heading north.",
        "direction": "OUTBOUND",
    },
]

CALLS = [
    {
        "id": 21,
        "call_type": "PLACED",
        "contact": "Alex Mercer",
        "start": "2026-03-12T13:05:00Z",
        "end": "2026-03-12T13:09:00Z",
        "duration": 240,
        "summary": "Outbound call discussing parking validation near North Pier Garage.",
    },
    {
        "id": 22,
        "call_type": "RECEIVED",
        "contact": "Noah Bennett",
        "start": "2026-03-12T15:58:00Z",
        "end": "2026-03-12T16:02:00Z",
        "duration": 240,
        "summary": "Inbound call about a schedule change at Harbor Cafe.",
    },
    {
        "id": 23,
        "call_type": "PLACED",
        "contact": "Mira Chen",
        "start": "2026-03-12T20:48:00Z",
        "end": "2026-03-12T20:53:00Z",
        "duration": 300,
        "summary": "Outbound call coordinating the meetup shift toward Riverside Market.",
    },
    {
        "id": 24,
        "call_type": "RECEIVED",
        "contact": "Riley Brooks",
        "start": "2026-03-12T23:05:00Z",
        "end": "2026-03-12T23:07:00Z",
        "duration": 120,
        "summary": "Inbound call asking whether Jordan cleared the garage before close.",
    },
]

BROWSERS = [
    {
        "id": 1,
        "title": "Transit route planning",
        "url": "https://maps.example/transit/east-line",
        "typed": True,
        "referrer": None,
        "timestamp": "2026-03-12T12:22:00Z",
    },
    {
        "id": 2,
        "title": "Garage rates",
        "url": "https://parking.example/north-pier",
        "typed": False,
        "referrer": "https://maps.example/transit/east-line",
        "timestamp": "2026-03-12T13:18:00Z",
    },
    {
        "id": 3,
        "title": "Cafe menu",
        "url": "https://harborcafe.example/menu",
        "typed": True,
        "referrer": "https://parking.example/north-pier",
        "timestamp": "2026-03-12T15:47:00Z",
    },
    {
        "id": 4,
        "title": "Ticket queue",
        "url": "https://tickets.example/events/riverfront",
        "typed": False,
        "referrer": "https://harborcafe.example/menu",
        "timestamp": "2026-03-12T16:24:00Z",
    },
    {
        "id": 5,
        "title": "Riverside map",
        "url": "https://maps.example/routes/riverside-market",
        "typed": True,
        "referrer": "https://tickets.example/events/riverfront",
        "timestamp": "2026-03-12T21:12:00Z",
    },
    {
        "id": 6,
        "title": "Hotel lobby hours",
        "url": "https://marketsquarehotel.example/lobby-hours",
        "typed": False,
        "referrer": "https://maps.example/routes/riverside-market",
        "timestamp": "2026-03-12T22:41:00Z",
    },
]

LOCATIONS = [
    ("2026-03-12T12:05:00Z", 40.7527, -73.9772, 12.0, "Union Transit Hall"),
    ("2026-03-12T12:28:00Z", 40.7546, -73.9831, 9.5, "Eastline Books"),
    ("2026-03-12T13:16:00Z", 40.7489, -73.9854, 14.0, "North Pier Garage"),
    ("2026-03-12T15:52:00Z", 40.7418, -73.9892, 8.0, "Harbor Cafe"),
    ("2026-03-12T16:27:00Z", 40.7406, -73.9867, 10.0, "Riverfront Plaza"),
    ("2026-03-12T18:10:00Z", 40.7384, -73.9823, 11.5, "East Market Arcade"),
    ("2026-03-12T20:45:00Z", 40.7441, -73.9801, 7.8, "Riverside Market"),
    ("2026-03-12T21:50:00Z", 40.7468, -73.9777, 9.0, "Market Square Hotel"),
    ("2026-03-12T23:12:00Z", 40.7490, -73.9852, 13.0, "North Pier Garage"),
    ("2026-03-13T00:02:00Z", 40.7511, -73.9905, 15.0, "Night Ferry Terminal"),
]

APP_EVENTS = [
    ("2026-03-12T12:06:00Z", "session_start", "Waypoint session start for the daily itinerary seed."),
    ("2026-03-12T12:23:00Z", "transit_card_open", "Transit card module opened after the east-line lookup."),
    ("2026-03-12T13:17:00Z", "parking_note_saved", "Parking note saved: North Pier Garage closes at 19:30."),
    ("2026-03-12T15:49:00Z", "meetup_checklist_armed", "Meetup checklist marked active for the Harbor Cafe stop."),
    ("2026-03-12T16:26:00Z", "route_export_generated", "Route export generated for Riverfront Plaza."),
    ("2026-03-12T20:46:00Z", "checkin_created", "Check-in marker created for Riverside Market."),
    ("2026-03-12T21:52:00Z", "briefcase_note_edited", "Briefcase note edited at Market Square Hotel."),
    ("2026-03-13T00:04:00Z", "session_end", "Session end and cached route archive written."),
]

PHOTOS = [
    ("IMG_20260312_091300.jpg", "2026-03-12T13:13:00Z", "Photo of a garage level marker with synthetic EXIF location data.", 40.7489, -73.9854, "Pixel 7 Pro", 1),
    ("IMG_20260312_122500.jpg", "2026-03-12T16:25:00Z", "Photo of a receipt folder left on the Harbor Cafe table.", 40.7418, -73.9892, "Pixel 7 Pro", 1),
    ("IMG_20260312_171200.jpg", "2026-03-12T21:12:00Z", "Photo of a storefront board near Riverside Market.", 40.7441, -73.9801, "Pixel 7 Pro", 6),
    ("IMG_20260312_192000.jpg", "2026-03-12T23:20:00Z", "Photo of the hotel lobby directory before departure north.", 40.7468, -73.9777, "Pixel 7 Pro", 1),
]

DELETED_MESSAGE = {
    "timestamp": "2026-03-12T11:48:00Z",
    "actor": "Jordan Vega",
    "counterparty": "Mira Chen",
    "body": "Draft asking to use the Harbor Cafe rear entrance.",
}

DELETED_BROWSER = {
    "timestamp": "2026-03-12T20:39:00Z",
    "title": "Alleys service entry",
    "url": "https://maps.example/alleys/service-entry",
}

JSON_INDENT = 2
