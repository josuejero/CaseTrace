import json
import shutil
import sqlite3
from pathlib import Path
from fractions import Fraction

from PIL import Image, ImageDraw

from parser.common import load_json
from parser.models import PARSER_VERSION
from integrity import (
    HASH_ALGORITHM,
    append_processing_step,
    capture_git_commit,
    collect_file_entries,
    container_image_digest,
    examiner_name,
    gather_file_summary,
    sha256_digest,
    utc_timestamp,
    write_manifest,
    write_processing_log,
)

CASE_DIR = Path('cases/CT-2026-001')
FILES_DIR = CASE_DIR / 'files'
DB_DIR = FILES_DIR / 'databases'
EXPORTS_DIR = FILES_DIR / 'exports'
LOGS_DIR = FILES_DIR / 'logs'
MEDIA_DIR = FILES_DIR / 'media'
ACQUISITION_SCRIPT_VERSION = "phase2-acquisition/1.0.0"

MESSAGES = [
    {
        'id': 1,
        'thread_id': 'thread-1',
        'actor': 'Mira Chen',
        'counterparty': 'Jordan Vega',
        'timestamp': '2026-03-12T12:10:00Z',
        'body': 'Asked Jordan to confirm the noon meetup near Harbor Cafe.',
        'direction': 'INBOUND'
    },
    {
        'id': 2,
        'thread_id': 'thread-1',
        'actor': 'Jordan Vega',
        'counterparty': 'Mira Chen',
        'timestamp': '2026-03-12T12:12:00Z',
        'body': 'Confirmed arrival via the East Line and said the blue folio would come along.',
        'direction': 'OUTBOUND'
    },
    {
        'id': 3,
        'thread_id': 'thread-2',
        'actor': 'Riley Brooks',
        'counterparty': 'Jordan Vega',
        'timestamp': '2026-03-12T14:42:00Z',
        'body': 'Sent the updated garage code and warned that parking closes at 19:30.',
        'direction': 'INBOUND'
    },
    {
        'id': 4,
        'thread_id': 'thread-2',
        'actor': 'Jordan Vega',
        'counterparty': 'Riley Brooks',
        'timestamp': '2026-03-12T14:44:00Z',
        'body': 'Acknowledged the garage note and said the backup stop was Union Transit Hall.',
        'direction': 'OUTBOUND'
    },
    {
        'id': 5,
        'thread_id': 'thread-3',
        'actor': 'Noah Bennett',
        'counterparty': 'Jordan Vega',
        'timestamp': '2026-03-12T16:18:00Z',
        'body': 'Shared an example tickets link and asked Jordan to review the event schedule.',
        'direction': 'INBOUND'
    },
    {
        'id': 6,
        'thread_id': 'thread-3',
        'actor': 'Jordan Vega',
        'counterparty': 'Noah Bennett',
        'timestamp': '2026-03-12T16:20:00Z',
        'body': 'Said the venue looked crowded and asked for an alternate coffee stop.',
        'direction': 'OUTBOUND'
    },
    {
        'id': 7,
        'thread_id': 'thread-1',
        'actor': 'Mira Chen',
        'counterparty': 'Jordan Vega',
        'timestamp': '2026-03-12T21:36:00Z',
        'body': 'Asked whether the meetup moved to the Market Square Hotel lobby.',
        'direction': 'INBOUND'
    },
    {
        'id': 8,
        'thread_id': 'thread-1',
        'actor': 'Jordan Vega',
        'counterparty': 'Mira Chen',
        'timestamp': '2026-03-12T21:38:00Z',
        'body': 'Confirmed a short stop at Market Square Hotel before heading north.',
        'direction': 'OUTBOUND'
    }
]

CALLS = [
    {
        'id': 21,
        'call_type': 'PLACED',
        'contact': 'Alex Mercer',
        'start': '2026-03-12T13:05:00Z',
        'end': '2026-03-12T13:09:00Z',
        'duration': 240,
        'summary': 'Outbound call discussing parking validation near North Pier Garage.'
    },
    {
        'id': 22,
        'call_type': 'RECEIVED',
        'contact': 'Noah Bennett',
        'start': '2026-03-12T15:58:00Z',
        'end': '2026-03-12T16:02:00Z',
        'duration': 240,
        'summary': 'Inbound call about a schedule change at Harbor Cafe.'
    },
    {
        'id': 23,
        'call_type': 'PLACED',
        'contact': 'Mira Chen',
        'start': '2026-03-12T20:48:00Z',
        'end': '2026-03-12T20:53:00Z',
        'duration': 300,
        'summary': 'Outbound call coordinating the meetup shift toward Riverside Market.'
    },
    {
        'id': 24,
        'call_type': 'RECEIVED',
        'contact': 'Riley Brooks',
        'start': '2026-03-12T23:05:00Z',
        'end': '2026-03-12T23:07:00Z',
        'duration': 120,
        'summary': 'Inbound call asking whether Jordan cleared the garage before close.'
    }
]

BROWSERS = [
    {
        'id': 1,
        'title': 'Transit route planning',
        'url': 'https://maps.example/transit/east-line',
        'typed': True,
        'referrer': None,
        'timestamp': '2026-03-12T12:22:00Z'
    },
    {
        'id': 2,
        'title': 'Garage rates',
        'url': 'https://parking.example/north-pier',
        'typed': False,
        'referrer': 'https://maps.example/transit/east-line',
        'timestamp': '2026-03-12T13:18:00Z'
    },
    {
        'id': 3,
        'title': 'Cafe menu',
        'url': 'https://harborcafe.example/menu',
        'typed': True,
        'referrer': 'https://parking.example/north-pier',
        'timestamp': '2026-03-12T15:47:00Z'
    },
    {
        'id': 4,
        'title': 'Ticket queue',
        'url': 'https://tickets.example/events/riverfront',
        'typed': False,
        'referrer': 'https://harborcafe.example/menu',
        'timestamp': '2026-03-12T16:24:00Z'
    },
    {
        'id': 5,
        'title': 'Riverside map',
        'url': 'https://maps.example/routes/riverside-market',
        'typed': True,
        'referrer': 'https://tickets.example/events/riverfront',
        'timestamp': '2026-03-12T21:12:00Z'
    },
    {
        'id': 6,
        'title': 'Hotel lobby hours',
        'url': 'https://marketsquarehotel.example/lobby-hours',
        'typed': False,
        'referrer': 'https://maps.example/routes/riverside-market',
        'timestamp': '2026-03-12T22:41:00Z'
    }
]

LOCATIONS = [
    ('2026-03-12T12:05:00Z', 40.7527, -73.9772, 12.0, 'Union Transit Hall'),
    ('2026-03-12T12:28:00Z', 40.7546, -73.9831, 9.5, 'Eastline Books'),
    ('2026-03-12T13:16:00Z', 40.7489, -73.9854, 14.0, 'North Pier Garage'),
    ('2026-03-12T15:52:00Z', 40.7418, -73.9892, 8.0, 'Harbor Cafe'),
    ('2026-03-12T16:27:00Z', 40.7406, -73.9867, 10.0, 'Riverfront Plaza'),
    ('2026-03-12T18:10:00Z', 40.7384, -73.9823, 11.5, 'East Market Arcade'),
    ('2026-03-12T20:45:00Z', 40.7441, -73.9801, 7.8, 'Riverside Market'),
    ('2026-03-12T21:50:00Z', 40.7468, -73.9777, 9.0, 'Market Square Hotel'),
    ('2026-03-12T23:12:00Z', 40.7490, -73.9852, 13.0, 'North Pier Garage'),
    ('2026-03-13T00:02:00Z', 40.7511, -73.9905, 15.0, 'Night Ferry Terminal')
]

APP_EVENTS = [
    ('2026-03-12T12:06:00Z', 'session_start', 'Waypoint session start for the daily itinerary seed.'),
    ('2026-03-12T12:23:00Z', 'transit_card_open', 'Transit card module opened after the east-line lookup.'),
    ('2026-03-12T13:17:00Z', 'parking_note_saved', 'Parking note saved: North Pier Garage closes at 19:30.'),
    ('2026-03-12T15:49:00Z', 'meetup_checklist_armed', 'Meetup checklist marked active for the Harbor Cafe stop.'),
    ('2026-03-12T16:26:00Z', 'route_export_generated', 'Route export generated for Riverfront Plaza.'),
    ('2026-03-12T20:46:00Z', 'checkin_created', 'Check-in marker created for Riverside Market.'),
    ('2026-03-12T21:52:00Z', 'briefcase_note_edited', 'Briefcase note edited at Market Square Hotel.'),
    ('2026-03-13T00:04:00Z', 'session_end', 'Session end and cached route archive written.')
]

PHOTOS = [
    ('IMG_20260312_091300.jpg', '2026-03-12T13:13:00Z', 'Photo of a garage level marker with synthetic EXIF location data.', 40.7489, -73.9854, 'Pixel 7 Pro', 1),
    ('IMG_20260312_122500.jpg', '2026-03-12T16:25:00Z', 'Photo of a receipt folder left on the Harbor Cafe table.', 40.7418, -73.9892, 'Pixel 7 Pro', 1),
    ('IMG_20260312_171200.jpg', '2026-03-12T21:12:00Z', 'Photo of a storefront board near Riverside Market.', 40.7441, -73.9801, 'Pixel 7 Pro', 6),
    ('IMG_20260312_192000.jpg', '2026-03-12T23:20:00Z', 'Photo of the hotel lobby directory before departure north.', 40.7468, -73.9777, 'Pixel 7 Pro', 1)
]

DELETED_MESSAGE = {
    'timestamp': '2026-03-12T11:48:00Z',
    'actor': 'Jordan Vega',
    'counterparty': 'Mira Chen',
    'body': 'Draft asking to use the Harbor Cafe rear entrance.'
}

DELETED_BROWSER = {
    'timestamp': '2026-03-12T20:39:00Z',
    'title': 'Alleys service entry',
    'url': 'https://maps.example/alleys/service-entry'
}

JSON_INDENT = 2


def create_core_database():
    temp_dir = Path('build/tmp_seed_core')
    temp_dir.mkdir(parents=True, exist_ok=True)
    db_path = temp_dir / 'waypoint_core.db'
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA wal_autocheckpoint=0;')
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY,
            thread_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            body TEXT NOT NULL,
            read_flag INTEGER NOT NULL,
            deleted_flag INTEGER NOT NULL
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE calls (
            id INTEGER PRIMARY KEY,
            call_type TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            timestamp_start TEXT NOT NULL,
            timestamp_end TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            summary TEXT NOT NULL
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            summary TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            device_model TEXT NOT NULL,
            orientation INTEGER NOT NULL
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE app_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            timestamp_start TEXT NOT NULL,
            timestamp_end TEXT NOT NULL,
            summary TEXT NOT NULL
        );
        """
    )

    for idx, message in enumerate(MESSAGES):
        read_flag = 1 if idx < 6 else 0
        cursor.execute(
            """INSERT INTO messages(id, thread_id, direction, timestamp, sender, recipient, body, read_flag, deleted_flag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                message['id'],
                message['thread_id'],
                message['direction'],
                message['timestamp'],
                message['actor'],
                message['counterparty'],
                message['body'],
                read_flag,
            ),
        )

    for call in CALLS:
        cursor.execute(
            """INSERT INTO calls(id, call_type, contact_name, timestamp_start, timestamp_end, duration_seconds, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                call['id'],
                call['call_type'],
                call['contact'],
                call['start'],
                call['end'],
                call['duration'],
                call['summary'],
            ),
        )

    for photo in PHOTOS:
        cursor.execute(
            """INSERT INTO photos(file_name, timestamp, summary, latitude, longitude, device_model, orientation)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            photo,
        )

    for event in APP_EVENTS:
        cursor.execute(
            """INSERT INTO app_events(event_type, timestamp_start, timestamp_end, summary)
            VALUES (?, ?, ?, ?)""",
            (event[1], event[0], event[0], event[2]),
        )

    conn.commit()
    mutate_core_database(conn)
    wal_path = db_path.with_suffix('.db-wal')
    shm_path = db_path.with_suffix('.db-shm')
    target_db = DB_DIR / 'waypoint_core.db'
    target_wal = DB_DIR / 'waypoint_core.db-wal'
    target_shm = DB_DIR / 'waypoint_core.db-shm'
    DB_DIR.mkdir(parents=True, exist_ok=True)
    if not wal_path.exists():
        raise RuntimeError(f'core WAL missing after commit: {wal_path}')
    shutil.copy(wal_path, target_wal)
    if not shm_path.exists():
        raise RuntimeError(f'core SHM missing after commit: {shm_path}')
    shutil.copy(shm_path, target_shm)
    conn.close()
    shutil.copy(db_path, target_db)


def mutate_core_database(conn):
    cursor = conn.cursor()
    mutated = MESSAGES[0]
    cursor.execute(
        """INSERT INTO messages(id, thread_id, direction, timestamp, sender, recipient, body, read_flag, deleted_flag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (
            mutated['id'] + 100,
            'mutate-case_alpha',
            mutated['direction'],
            DELETED_MESSAGE['timestamp'],
            DELETED_MESSAGE['actor'],
            DELETED_MESSAGE['counterparty'],
            DELETED_MESSAGE['body'],
            0,
        ),
    )
    cursor.execute(
        """UPDATE messages SET body = ? WHERE id = ?""",
        (f"[mutated] {mutated['body']}", mutated['id']),
    )
    cursor.execute("DELETE FROM messages WHERE id = ?", (mutated['id'],))
    conn.commit()


def create_web_database():
    temp_dir = Path('build/tmp_seed_web')
    temp_dir.mkdir(parents=True, exist_ok=True)
    db_path = temp_dir / 'waypoint_web.db'
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA wal_autocheckpoint=0;')
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE browser_history (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            typed_url INTEGER NOT NULL,
            referrer TEXT,
            timestamp TEXT NOT NULL
        );
        """
    )

    for visit in BROWSERS:
        cursor.execute(
            """INSERT INTO browser_history(id, title, url, typed_url, referrer, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                visit['id'],
                visit['title'],
                visit['url'],
                1 if visit['typed'] else 0,
                visit['referrer'],
                visit['timestamp'],
            ),
        )

    conn.commit()
    mutate_browser_database(conn)
    wal_path = db_path.with_suffix('.db-wal')
    shm_path = db_path.with_suffix('.db-shm')
    target_db = DB_DIR / 'waypoint_web.db'
    target_wal = DB_DIR / 'waypoint_web.db-wal'
    target_shm = DB_DIR / 'waypoint_web.db-shm'
    DB_DIR.mkdir(parents=True, exist_ok=True)
    if not wal_path.exists():
        raise RuntimeError(f'web WAL missing after commit: {wal_path}')
    shutil.copy(wal_path, target_wal)
    if not shm_path.exists():
        raise RuntimeError(f'web SHM missing after commit: {shm_path}')
    shutil.copy(shm_path, target_shm)
    conn.close()
    shutil.copy(db_path, target_db)


def mutate_browser_database(conn):
    cursor = conn.cursor()
    visit = BROWSERS[0]
    new_id = visit['id'] + 100
    cursor.execute(
        """INSERT INTO browser_history(id, title, url, typed_url, referrer, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (
            new_id,
            DELETED_BROWSER['title'],
            DELETED_BROWSER['url'],
            1,
            None,
            DELETED_BROWSER['timestamp'],
        ),
    )
    cursor.execute("DELETE FROM browser_history WHERE id = ?", (new_id,))
    conn.commit()


def write_exports():
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        'case_id': 'CT-2026-001',
        'points': [
            {
                'timestamp_utc': timestamp,
                'label': label,
                'latitude': lat,
                'longitude': lon,
                'accuracy_m': acc,
            }
            for timestamp, lat, lon, acc, label in LOCATIONS
        ]
    }
    (EXPORTS_DIR / 'location_trace.json').write_text(json.dumps(payload, indent=JSON_INDENT))


def write_logs():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    target = LOGS_DIR / 'app-events-20260312.jsonl'
    with target.open('w') as handle:
        for timestamp, event, summary in APP_EVENTS:
            handle.write(json.dumps({'timestamp_utc': timestamp, 'event': event, 'summary': summary}) + '\n')


def create_photos():
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    for file_name, timestamp, summary, lat, lon, device, orientation in PHOTOS:
        img = Image.new('RGB', (640, 480), color=(230, 240, 255))
        draw = ImageDraw.Draw(img)
        draw.text((24, 36), file_name, fill=(0, 0, 0))
        draw.text((24, 100), summary, fill=(30, 30, 30))
        img_path = MEDIA_DIR / file_name
        exif = img.getexif()
        exif[306] = timestamp.replace('T', ' ').replace('Z', '')
        exif[36867] = exif[306]
        exif[271] = 'Google'
        exif[272] = device
        exif[274] = orientation
        gps_info = {
            1: 'N' if lat >= 0 else 'S',
            2: _to_dms(lat),
            3: 'E' if lon >= 0 else 'W',
            4: _to_dms(abs(lon)),
        }
        exif[34853] = gps_info
        img.save(img_path, exif=exif)


def _to_dms(value: float):
    degrees = int(value)
    minutes_full = (value - degrees) * 60
    minutes = int(minutes_full)
    seconds = round((minutes_full - minutes) * 60 * 100)
    return (
        Fraction(degrees, 1),
        Fraction(minutes, 1),
        Fraction(seconds, 100),
    )


def _relative_to_or_str(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)


def update_hash_manifest():
    case_metadata = load_json(CASE_DIR / "case.json")
    case_id = case_metadata["case_id"]
    entries = collect_file_entries(FILES_DIR, CASE_DIR)
    summary = gather_file_summary(entries)
    environment = {"git_commit": capture_git_commit()}
    digest = container_image_digest()
    if digest:
        environment["container_image_digest"] = digest
    manifest = {
        "case_id": case_id,
        "algorithm": HASH_ALGORITHM,
        "generated_at": utc_timestamp(),
        "acquisition": {
            "acquired_at": case_metadata["acquisition"]["acquired_at"],
            "operator": examiner_name(),
            "script_version": ACQUISITION_SCRIPT_VERSION,
            "device": case_metadata["device"],
            "method": case_metadata["acquisition"]["method"],
        },
        "app": {
            "package": case_metadata["seed_app"]["package_name"],
            "label": case_metadata["seed_app"]["label"],
            "version": case_metadata["seed_app"]["version"],
        },
        "environment": environment,
        "parser_version": PARSER_VERSION,
        "files": entries,
    }
    report_file = CASE_DIR / "reports" / "recovery.html"
    report_rel = _relative_to_or_str(report_file, CASE_DIR)
    report_timestamp = utc_timestamp()
    report_digest = sha256_digest(report_file) if report_file.exists() else None
    manifest["report"] = {
        "generated_at": report_timestamp,
        "path": report_rel,
        "sha256": report_digest,
    }
    manifest["generated_at"] = report_timestamp
    write_manifest(CASE_DIR, manifest)
    write_processing_log(CASE_DIR, {"case_id": case_id, "generated_at": utc_timestamp(), "steps": []})
    append_processing_step(
        CASE_DIR,
        case_id,
        stage="acquisition",
        description="Seed files crafted in tools/generate_seed_artifacts",
        actor=examiner_name(),
        details={
            "script_version": ACQUISITION_SCRIPT_VERSION,
            "hash_summary": summary,
        },
    )
    append_processing_step(
        CASE_DIR,
        case_id,
        stage="analysis",
        description="Normalized artifact fixtures produced",
        actor=examiner_name(),
        details={
            "parser_version": PARSER_VERSION,
            "hash_summary": summary,
        },
    )
    append_processing_step(
        CASE_DIR,
        case_id,
        stage="report_export",
        description="Logged WAL recovery report sample",
        actor=examiner_name(),
        details={
            "report_path": report_rel,
            "report_sha256": report_digest,
            "hash_summary": summary,
        },
    )

def main():
    create_photos()
    create_core_database()
    create_web_database()
    write_exports()
    write_logs()
    update_hash_manifest()


if __name__ == '__main__':
    main()
