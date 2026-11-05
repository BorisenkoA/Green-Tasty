#!/usr/bin/env python3
"""Local development API for the Green Tasty Angular application."""

from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("GREEN_TASTY_DATA_DIR", ROOT / "data")).resolve()
DATABASE_PATH = DATA_DIR / "restaurant.sqlite3"
SECRET_PATH = DATA_DIR / "token-secret"
PASSWORD_ITERATIONS = 310_000
TOKEN_LIFETIME_SECONDS = 60 * 60 * 12
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
NAME_PATTERN = re.compile(r"^[A-Za-z'-]{2,50}$")


LOCATIONS = [
    {
        "id": "location-abashidze",
        "address": "9 Abashidze Street, Tbilisi",
        "description": "A relaxed neighborhood restaurant serving fresh, seasonal food.",
        "totalCapacity": 42,
        "averageOccupancy": "68%",
        "imageUrl": "assets/img/locations/abashidze-street-9.jpg",
        "rating": 4.8,
    },
    {
        "id": "location-baratashvili",
        "address": "14 Baratashvili Street, Tbilisi",
        "description": "A bright city-center dining room with a menu for every season.",
        "totalCapacity": 56,
        "averageOccupancy": "74%",
        "imageUrl": "assets/img/locations/baratashvili-street-14.jpg",
        "rating": 4.7,
    },
    {
        "id": "location-rustaveli",
        "address": "48 Rustaveli Avenue, Tbilisi",
        "description": "Fresh local ingredients and thoughtful vegetarian cooking.",
        "totalCapacity": 64,
        "averageOccupancy": "81%",
        "imageUrl": "assets/img/locations/rustaveli-avenue-48.jpg",
        "rating": 4.9,
    },
]

DISHES = [
    {
        "id": "dish-avocado-bowl",
        "name": "Avocado & Pine Nut Bowl",
        "imageUrl": "assets/img/dishes/avocado-pine-nut-bowl.jpg",
        "price": 14.5,
        "state": "Available",
        "weight": "320 g",
        "dishType": "MainCourse",
        "description": "A bright bowl of avocado, greens, grains and toasted pine nuts.",
        "calories": "420 kcal",
        "proteins": "12 g",
        "carbohydrates": "38 g",
        "fats": "24 g",
        "vitamins": "A, C, E",
        "locationId": "location-abashidze",
    },
    {
        "id": "dish-strawberry-salad",
        "name": "Strawberry Mint Salad",
        "imageUrl": "assets/img/dishes/fresh-strawberry-mint-salad.jpg",
        "price": 11.0,
        "state": "Available",
        "weight": "250 g",
        "dishType": "Salad",
        "description": "Fresh strawberries, mint and crisp seasonal greens.",
        "calories": "280 kcal",
        "proteins": "6 g",
        "carbohydrates": "34 g",
        "fats": "13 g",
        "vitamins": "A, C, K",
        "locationId": "location-baratashvili",
    },
    {
        "id": "dish-sweet-potato-lentil",
        "name": "Roasted Sweet Potato & Lentil Salad",
        "imageUrl": "assets/img/dishes/roasted-sweet-potato-and-lentil-salad.jpg",
        "price": 13.5,
        "state": "Available",
        "weight": "350 g",
        "dishType": "MainCourse",
        "description": "Roasted sweet potato with warm lentils and fresh herbs.",
        "calories": "390 kcal",
        "proteins": "16 g",
        "carbohydrates": "54 g",
        "fats": "12 g",
        "vitamins": "A, B, C",
        "locationId": "location-rustaveli",
    },
    {
        "id": "dish-spring-salad",
        "name": "Spring Garden Salad",
        "imageUrl": "assets/img/dishes/spring-salad.jpg",
        "price": 10.5,
        "state": "Available",
        "weight": "230 g",
        "dishType": "Salad",
        "description": "A crisp seasonal salad with greens and a citrus dressing.",
        "calories": "240 kcal",
        "proteins": "7 g",
        "carbohydrates": "29 g",
        "fats": "11 g",
        "vitamins": "A, C, K",
        "locationId": "location-abashidze",
    },
]


def connect_database() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def initialize_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect_database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Customer',
                profile_image TEXT
            );
            CREATE TABLE IF NOT EXISTS locations (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dishes (
                id TEXT PRIMARY KEY,
                location_id TEXT NOT NULL REFERENCES locations(id),
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS records (
                kind TEXT NOT NULL,
                id TEXT NOT NULL,
                owner_id TEXT,
                created_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (kind, id)
            );
            CREATE INDEX IF NOT EXISTS records_by_owner ON records(kind, owner_id);
            """
        )
        user_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(users)")
        }
        if "profile_image" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN profile_image TEXT")
        if connection.execute("SELECT COUNT(*) FROM locations").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO locations (id, payload) VALUES (?, ?)",
                [(location["id"], json.dumps(location)) for location in LOCATIONS],
            )
        if connection.execute("SELECT COUNT(*) FROM dishes").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO dishes (id, location_id, payload) VALUES (?, ?, ?)",
                [
                    (dish["id"], dish["locationId"], json.dumps(dish))
                    for dish in DISHES
                ],
            )
        if connection.execute(
            "SELECT COUNT(*) FROM records WHERE kind = 'table'"
        ).fetchone()[0] == 0:
            now = utc_now()
            connection.executemany(
                "INSERT INTO records (kind, id, owner_id, created_at, payload) VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        "table",
                        f"table-{location['id']}-{number}",
                        location["id"],
                        now,
                        json.dumps(
                            {
                                "id": f"table-{location['id']}-{number}",
                                "tableNumber": number,
                                "locationId": location["id"],
                                "capacity": [2, 4, 4, 6, 8][number - 1],
                            }
                        ),
                    )
                    for location in LOCATIONS
                    for number in range(1, 6)
                ],
            )
    if not os.environ.get("LOCAL_API_SECRET") and not SECRET_PATH.exists():
        secret_fd = os.open(SECRET_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(secret_fd, "wb") as secret_file:
            secret_file.write(secrets.token_bytes(32))


def token_secret() -> bytes:
    configured_secret = os.environ.get("LOCAL_API_SECRET")
    if configured_secret:
        if len(configured_secret) < 32:
            raise RuntimeError("LOCAL_API_SECRET must contain at least 32 characters.")
        return configured_secret.encode("utf-8")
    return SECRET_PATH.read_bytes()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def load_record(row: sqlite3.Row | None) -> dict[str, object] | None:
    return json.loads(row["payload"]) if row else None


def save_record(
    connection: sqlite3.Connection,
    kind: str,
    record_id: str,
    value: dict[str, object],
    owner_id: str | None = None,
    created_at: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO records (kind, id, owner_id, created_at, payload)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(kind, id) DO UPDATE SET
            owner_id = excluded.owner_id,
            payload = excluded.payload
        """,
        (kind, record_id, owner_id, created_at or utc_now(), json.dumps(value)),
    )


def records_of(
    connection: sqlite3.Connection, kind: str, owner_id: str | None = None
) -> list[dict[str, object]]:
    if owner_id is None:
        rows = connection.execute(
            "SELECT payload FROM records WHERE kind = ? ORDER BY created_at",
            (kind,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT payload FROM records WHERE kind = ? AND owner_id = ? ORDER BY created_at",
            (kind, owner_id),
        ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def image_url(value: object, fallback: str) -> str:
    if not isinstance(value, str) or not value:
        return fallback
    if value.startswith(("data:", "https://", "http://", "assets/")):
        return value
    return f"data:image/jpeg;base64,{value}"


def normalize_feedback_type(value: object) -> str | None:
    if value in ("Service", 0, "0"):
        return "Service"
    if value in ("CuisineExperience", 1, "1"):
        return "CuisineExperience"
    return None


def encode_segment(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def create_token(user: sqlite3.Row) -> str:
    now = int(time.time())
    header = encode_segment(b'{"alg":"HS256","typ":"JWT"}')
    payload = encode_segment(
        json.dumps(
            {
                "sub": user["id"],
                "email": user["email"],
                "role": user["role"],
                "iat": now,
                "exp": now + TOKEN_LIFETIME_SECONDS,
            },
            separators=(",", ":"),
        ).encode("utf-8")
    )
    message = f"{header}.{payload}".encode("ascii")
    signature = encode_segment(hmac.new(token_secret(), message, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return encode_segment(digest), encode_segment(salt)


def verify_password(password: str, password_hash: str, password_salt: str) -> bool:
    salt = base64.urlsafe_b64decode(password_salt + "=" * (-len(password_salt) % 4))
    expected_hash = base64.urlsafe_b64decode(
        password_hash + "=" * (-len(password_hash) % 4)
    )
    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def public_user(user: sqlite3.Row) -> dict[str, str]:
    return {
        "id": user["id"],
        "firstName": user["first_name"],
        "lastName": user["last_name"],
        "email": user["email"],
        "role": user["role"],
    }


def decode_token(token: str) -> dict[str, object] | None:
    try:
        header, payload, signature = token.split(".")
        message = f"{header}.{payload}".encode("ascii")
        expected = hmac.new(token_secret(), message, hashlib.sha256).digest()
        provided = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, provided):
            return None
        claims = json.loads(
            base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        )
        if int(claims["exp"]) <= int(time.time()):
            return None
        return claims
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "GreenTastyLocalAPI/1.0"

    def log_message(self, format_string: str, *args: object) -> None:
        sys.stderr.write(
            "%s - %s\n"
            % (self.address_string(), format_string % args)
        )

    def end_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin in ("http://localhost:4200", "http://127.0.0.1:4200"):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        self.send_header(
            "Access-Control-Allow-Headers", "Authorization, Content-Type"
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def send_json(self, status: int, value: object) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def read_json(self) -> dict[str, object] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 15_000_000:
                return None
            value = json.loads(self.rfile.read(length))
            return value if isinstance(value, dict) else None
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def authenticated_user(self) -> sqlite3.Row | None:
        authorization = self.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        claims = decode_token(token)
        if not claims:
            return None
        with connect_database() as connection:
            return connection.execute(
                "SELECT * FROM users WHERE id = ?", (claims.get("sub"),)
            ).fetchone()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlsplit(self.path).path.rstrip("/") or "/"
        try:
            if path == "/health":
                self.send_json(200, {"status": "ok"})
            elif path == "/locations":
                with connect_database() as connection:
                    rows = connection.execute(
                        "SELECT payload FROM locations ORDER BY rowid"
                    ).fetchall()
                self.send_json(200, [json.loads(row["payload"]) for row in rows])
            elif path == "/dishes/popular":
                with connect_database() as connection:
                    rows = connection.execute(
                        "SELECT payload FROM dishes ORDER BY rowid LIMIT 4"
                    ).fetchall()
                self.send_json(200, [json.loads(row["payload"]) for row in rows])
            elif path == "/dishes":
                self.get_dishes()
            elif path.startswith("/locations/") and path.endswith("/dishes"):
                location_id = unquote(path[len("/locations/") : -len("/dishes")].strip("/"))
                with connect_database() as connection:
                    rows = connection.execute("SELECT payload FROM dishes ORDER BY rowid").fetchall()
                dishes = [json.loads(row["payload"]) for row in rows]
                self.send_json(
                    200,
                    [
                        dish
                        for dish in dishes
                        if dish.get("locationId") == location_id
                        or location_id in dish.get("locationIds", [])
                    ],
                )
            elif path.startswith("/locations/") and path.endswith("/tables/all"):
                location_id = unquote(path[len("/locations/") : -len("/tables/all")].strip("/"))
                with connect_database() as connection:
                    tables = records_of(connection, "table", location_id)
                self.send_json(200, tables)
            elif path.startswith("/locations/"):
                location_id = unquote(path.removeprefix("/locations/"))
                with connect_database() as connection:
                    row = connection.execute(
                        "SELECT payload FROM locations WHERE id = ?", (location_id,)
                    ).fetchone()
                if row is None:
                    self.send_json(404, {"error": "Location not found"})
                else:
                    self.send_json(200, json.loads(row["payload"]))
            elif path.startswith("/dishes/"):
                dish_id = unquote(path.removeprefix("/dishes/"))
                with connect_database() as connection:
                    row = connection.execute(
                        "SELECT payload FROM dishes WHERE id = ?", (dish_id,)
                    ).fetchone()
                if row is None:
                    self.send_json(404, {"error": "Dish not found"})
                else:
                    self.send_json(200, json.loads(row["payload"]))
            elif path == "/me":
                user = self.authenticated_user()
                if user is None:
                    self.send_json(401, {"error": "Please sign in again."})
                else:
                    self.send_json(200, public_user(user))
            elif path == "/users":
                self.get_users()
            elif path == "/notifications":
                self.get_notifications()
            elif path == "/available-tables":
                self.get_available_tables()
            elif path == "/feedback":
                self.get_feedback()
            elif path == "/feedback/token":
                self.get_feedback_token()
            elif path == "/reports":
                self.get_reports()
            elif path in ("/reports/generate", "/reports/download"):
                self.get_report(path.endswith("/download"))
            elif path.startswith("/tables/") and path.endswith("/available-time-slots"):
                table_id = unquote(path[len("/tables/") : -len("/available-time-slots")].strip("/"))
                self.get_table_time_slots(table_id)
            elif path.startswith("/locations/") and path.endswith("/tables/all"):
                location_id = unquote(path[len("/locations/") : -len("/tables/all")].strip("/"))
                with connect_database() as connection:
                    tables = records_of(connection, "table", location_id)
                self.send_json(200, tables)
            elif path.startswith("/reservations/") and path.endswith("/feedback"):
                reservation_id = unquote(path[len("/reservations/") : -len("/feedback")].strip("/"))
                self.get_reservation_feedback(reservation_id)
            elif path.startswith("/reservations/") and path.endswith("/invite-token"):
                reservation_id = unquote(path[len("/reservations/") : -len("/invite-token")].strip("/"))
                self.get_invite_token(reservation_id)
            elif path.startswith("/reservations/") and path.endswith("/guest-session-id"):
                reservation_id = unquote(path[len("/reservations/") : -len("/guest-session-id")].strip("/"))
                self.get_owner_session(reservation_id)
            elif path.startswith("/reservations/") and path.endswith("/table"):
                self.send_json(405, {"error": "Method not allowed"})
            elif path.startswith("/reservations/") and path.endswith("/status"):
                self.send_json(405, {"error": "Method not allowed"})
            elif path.startswith("/reservations/"):
                reservation_id = unquote(path.removeprefix("/reservations/"))
                if reservation_id == "":
                    self.get_reservations()
                else:
                    self.get_reservation(reservation_id)
            elif path == "/reservations":
                self.get_reservations()
            elif path == "/orders":
                self.get_orders()
            elif path.startswith("/orders/"):
                self.get_order(unquote(path.removeprefix("/orders/")))
            elif path.startswith("/guest/sessions/") and path.endswith("/menu"):
                session_id = unquote(path[len("/guest/sessions/") : -len("/menu")].strip("/"))
                self.get_guest_menu(session_id)
            elif path.startswith("/guest/sessions/"):
                session_id = unquote(path.removeprefix("/guest/sessions/"))
                self.get_guest_session(session_id)
            elif path.startswith("/guest/groups/") and path.endswith("/sessions"):
                group_id = unquote(path[len("/guest/groups/") : -len("/sessions")].strip("/"))
                self.get_group_sessions(group_id)
            elif path.startswith("/guest/groups/") and path.endswith("/status"):
                group_id = unquote(path[len("/guest/groups/") : -len("/status")].strip("/"))
                self.get_group_status(group_id)
            elif path.startswith("/guest/invites/"):
                self.get_guest_invite(unquote(path.removeprefix("/guest/invites/")))
            elif path.startswith("/users/") and path.endswith("/profile-image"):
                user_id = unquote(path[len("/users/") : -len("/profile-image")].strip("/"))
                self.get_profile_image(user_id)
            elif path.startswith("/waiters/") and path.endswith("/location"):
                waiter_id = unquote(path[len("/waiters/") : -len("/location")].strip("/"))
                self.get_waiter_location(waiter_id)
            elif path.startswith("/users/") and path.endswith("/name"):
                user_id = unquote(path[len("/users/") : -len("/name")].strip("/"))
                with connect_database() as connection:
                    user = connection.execute(
                        "SELECT first_name, last_name FROM users WHERE id = ?",
                        (user_id,),
                    ).fetchone()
                if user is None:
                    self.send_json(404, {"error": "User not found"})
                else:
                    self.send_json(
                        200,
                        {"name": f"{user['first_name']} {user['last_name']}"},
                    )
            elif path.startswith("/locations/"):
                location_id = unquote(path.removeprefix("/locations/"))
                with connect_database() as connection:
                    row = connection.execute(
                        "SELECT payload FROM locations WHERE id = ?", (location_id,)
                    ).fetchone()
                if row is None:
                    self.send_json(404, {"error": "Location not found"})
                else:
                    self.send_json(200, json.loads(row["payload"]))
            else:
                self.send_json(404, {"error": "Not found"})
        except sqlite3.Error:
            self.log_error("Database error while handling GET %s", path)
            self.send_json(500, {"error": "Database error"})

    def require_user(self) -> sqlite3.Row | None:
        user = self.authenticated_user()
        if user is None:
            self.send_json(401, {"error": "Please sign in again."})
        return user

    @staticmethod
    def can_access_reservation(
        user: sqlite3.Row, reservation: dict[str, object]
    ) -> bool:
        if user["role"] == "Admin":
            return True
        if user["role"] == "Waiter":
            return reservation.get("waiterId") == user["id"]
        return reservation.get("customerId") == user["id"]

    def get_users(self) -> None:
        if self.require_admin() is None:
            return
        query = parse_qs(urlsplit(self.path).query)
        name = query.get("fullName", [""])[0].casefold()
        with connect_database() as connection:
            rows = connection.execute(
                "SELECT * FROM users ORDER BY first_name, last_name"
            ).fetchall()
        users = [public_user(row) for row in rows]
        if name:
            users = [
                user
                for user in users
                if name in f"{user['firstName']} {user['lastName']}".casefold()
            ]
        self.send_json(200, users)

    def get_profile_image(self, user_id: str) -> None:
        with connect_database() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        if row is None:
            self.send_json(404, {"error": "User not found"})
            return
        image = row["profile_image"] if "profile_image" in row.keys() else None
        self.send_json(
            200,
            {"presignedUrl": image_url(image, "assets/img/avatar.png")},
        )

    def get_waiter_location(self, waiter_id: str) -> None:
        with connect_database() as connection:
            waiter = connection.execute(
                "SELECT role FROM users WHERE id = ?", (waiter_id,)
            ).fetchone()
            assignment = connection.execute(
                "SELECT payload FROM records WHERE kind = 'waiter' AND id = ?",
                (waiter_id,),
            ).fetchone()
        if waiter is None or waiter["role"] != "Waiter":
            self.send_json(404, {"error": "Waiter not found"})
            return
        details = load_record(assignment) or {}
        self.send_json(200, {"locationId": details.get("locationId", LOCATIONS[0]["id"])})

    def get_notifications(self) -> None:
        user = self.require_user()
        if user is None:
            return
        with connect_database() as connection:
            notifications = records_of(connection, "notification", user["id"])
        self.send_json(200, notifications)

    def get_available_tables(self) -> None:
        query = parse_qs(urlsplit(self.path).query)
        try:
            capacity = max(1, int(query.get("capacity", ["1"])[0]))
        except ValueError:
            self.send_json(400, {"error": "Invalid table capacity"})
            return
        location_id = query.get("locationId", [None])[0]
        if location_id and location_id not in {location["id"] for location in LOCATIONS}:
            with connect_database() as connection:
                location_rows = connection.execute(
                    "SELECT payload FROM locations"
                ).fetchall()
            matching_location = next(
                (
                    json.loads(row["payload"])
                    for row in location_rows
                    if json.loads(row["payload"]).get("address") == location_id
                ),
                None,
            )
            location_id = matching_location["id"] if matching_location else location_id
        start = parse_datetime(query.get("startTime", [None])[0])
        if query.get("startTime") and start is None:
            self.send_json(400, {"error": "Invalid startTime"})
            return
        with connect_database() as connection:
            tables = records_of(connection, "table")
            reservations = records_of(connection, "reservation")
        available = []
        for table in tables:
            if int(table["capacity"]) < capacity:
                continue
            if location_id and table["locationId"] != location_id:
                continue
            if start and self.table_is_reserved(table["id"], start, start + timedelta(hours=2), reservations):
                continue
            available.append({**table, "timeRanges": []})
        self.send_json(200, available)

    @staticmethod
    def table_is_reserved(
        table_id: object,
        start: datetime,
        end: datetime,
        reservations: list[dict[str, object]],
        exclude_id: str | None = None,
    ) -> bool:
        for reservation in reservations:
            if (
                reservation.get("tableId") == table_id
                and reservation.get("id") != exclude_id
                and int(reservation.get("status", 0)) == 0
            ):
                reserved_start = parse_datetime(reservation.get("startTime"))
                reserved_end = parse_datetime(reservation.get("endTime"))
                if reserved_start and reserved_end and start < reserved_end and end > reserved_start:
                    return True
        return False

    def get_table_time_slots(self, table_id: str) -> None:
        query = parse_qs(urlsplit(self.path).query)
        date_time = parse_datetime(query.get("startTime", [None])[0])
        if date_time is None:
            self.send_json(400, {"error": "A valid startTime is required"})
            return
        with connect_database() as connection:
            table = load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = 'table' AND id = ?",
                    (table_id,),
                ).fetchone()
            )
            reservations = records_of(connection, "reservation")
        if table is None:
            self.send_json(404, {"error": "Table not found"})
            return
        date_time = date_time.replace(hour=0, minute=0, second=0, microsecond=0)
        slots = []
        for minutes in range(11 * 60, 19 * 60 + 1, 30):
            start = date_time + timedelta(minutes=minutes)
            end = start + timedelta(hours=2)
            if not self.table_is_reserved(table_id, start, end, reservations):
                slots.append({"start": start.isoformat().replace("+00:00", "Z"), "end": end.isoformat().replace("+00:00", "Z")})
        self.send_json(200, slots)

    def get_reservations(self) -> None:
        user = self.require_user()
        if user is None:
            return
        with connect_database() as connection:
            reservations = records_of(connection, "reservation")
            orders = records_of(connection, "order")
        reservations = [
            item for item in reservations if self.can_access_reservation(user, item)
        ]
        self.send_json(200, [self.enrich_reservation(item, orders) for item in reservations])

    def enrich_reservation(
        self,
        reservation: dict[str, object],
        orders: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        with connect_database() as connection:
            table = load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = 'table' AND id = ?",
                    (reservation.get("tableId"),),
                ).fetchone()
            )
            location_id = table.get("locationId") if table else None
            row = connection.execute(
                "SELECT payload FROM locations WHERE id = ?", (location_id,)
            ).fetchone()
            location = load_record(row)
        result = {
            **reservation,
            "locationAddress": location.get("address", "") if location else "",
            "restaurantName": (location.get("address", "").split(",")[0] if location else ""),
            "tableCapacity": table.get("capacity", 0) if table else 0,
            "tableName": f"Table {table['tableNumber']}" if table else "",
            "waiterId": reservation.get("waiterId", ""),
            "createdByRole": reservation.get("createdByRole", "Customer"),
        }
        order = next((o for o in (orders or []) if o.get("reservationId") == reservation["id"]), None)
        if order:
            result["preOrder"] = order
            result["preOrders"] = [order]
            result["hasSubmittedPreOrder"] = order.get("status") == 1
        return result

    def get_reservation(self, reservation_id: str) -> None:
        user = self.require_user()
        if user is None:
            return
        with connect_database() as connection:
            reservation = load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = 'reservation' AND id = ?",
                    (reservation_id,),
                ).fetchone()
            )
            orders = records_of(connection, "order")
        if reservation is None:
            self.send_json(404, {"error": "Reservation not found"})
            return
        if not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot access this reservation"})
            return
        self.send_json(200, self.enrich_reservation(reservation, orders))

    def get_orders(self) -> None:
        user = self.require_user()
        if user is None:
            return
        with connect_database() as connection:
            orders = records_of(connection, "order")
            reservations = {r["id"]: r for r in records_of(connection, "reservation")}
        orders = [
            order
            for order in orders
            if self.can_access_reservation(
                user, reservations.get(order["reservationId"], {})
            )
        ]
        self.send_json(200, [self.enrich_order(order) for order in orders])

    def get_order(self, reservation_id: str) -> None:
        user = self.require_user()
        if user is None:
            return
        with connect_database() as connection:
            order = load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = 'order' AND id = ?",
                    (reservation_id,),
                ).fetchone()
            )
        if order is None:
            self.send_json(404, {"error": "Order not found"})
            return
        reservation = self.get_record("reservation", reservation_id)
        if reservation is None or not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot access this order"})
            return
        self.send_json(200, self.enrich_order(order))

    def enrich_order(self, order: dict[str, object]) -> dict[str, object]:
        items = []
        with connect_database() as connection:
            reservation = load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = 'reservation' AND id = ?",
                    (order["reservationId"],),
                ).fetchone()
            )
            for item in order.get("orderItems", []):
                dish = load_record(
                    connection.execute(
                        "SELECT payload FROM dishes WHERE id = ?", (item.get("dishId"),)
                    ).fetchone()
                )
                if dish:
                    items.append({**item, "dish": dish})
        return {
            **order,
            "orderId": order.get("orderId", order["reservationId"]),
            "reservationAddress": self.enrich_reservation(reservation).get("locationAddress", "") if reservation else "",
            "reservationTime": reservation.get("startTime", "") if reservation else "",
            "orderItems": items,
        }

    def get_guest_session(self, session_id: str) -> None:
        session, _ = self.guest_session_from_request(session_id)
        if session is not None:
            self.send_json(200, session)

    def get_guest_menu(self, session_id: str) -> None:
        session, _ = self.guest_session_from_request(session_id)
        if session is None:
            return
        with connect_database() as connection:
            dishes = [
                json.loads(row["payload"])
                for row in connection.execute("SELECT payload FROM dishes ORDER BY rowid").fetchall()
            ]
        categories: dict[str, list[dict[str, object]]] = {}
        for dish in dishes:
            category = str(dish.get("dishType", "Other"))
            categories.setdefault(category, []).append(
                {
                    **dish,
                    "selectable": dish.get("state") == "Available",
                }
            )
        self.send_json(200, {"dishes": categories})

    def guest_session_from_request(
        self, session_id: str
    ) -> tuple[dict[str, object] | None, sqlite3.Row | None]:
        authorization = self.headers.get("Authorization", "")
        _, _, token = authorization.partition(" ")
        with connect_database() as connection:
            session = load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = 'guest-session' AND id = ?",
                    (session_id,),
                ).fetchone()
            )
        if session is None:
            self.send_json(404, {"error": "Guest session not found"})
            return None, None
        if not token or not hmac.compare_digest(token, str(session.get("token", ""))):
            self.send_json(401, {"error": "Guest session token is invalid"})
            return None, None
        if session.get("submitted"):
            self.send_json(409, {"error": "Guest session has already been submitted"})
            return None, None
        return session, None

    def get_group_sessions(self, group_id: str) -> None:
        with connect_database() as connection:
            group = load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = 'group' AND id = ?",
                    (group_id,),
                ).fetchone()
            )
            sessions = [
                session
                for session in records_of(connection, "guest-session")
                if session.get("groupReservationId") == group_id
            ]
        if group is None:
            self.send_json(404, {"error": "Group reservation not found"})
            return
        owner_order = self.get_record("order", group_id)
        owner_items = []
        if owner_order:
            for item in owner_order.get("orderItems", []):
                dish = self.get_record("dish", str(item.get("dishId")))
                if dish:
                    owner_items.append({"dish": dish, "quantity": item["quantity"]})
        participants = [
            {
                "id": None,
                "type": "Owner",
                "name": "Host",
                "items": owner_items,
                "total": sum(float(item["dish"]["price"]) * int(item["quantity"]) for item in owner_items),
                "isSubmitted": bool(owner_order and owner_order.get("status") == 1),
            }
        ]
        for session in sessions:
            items = self.guest_items(session)
            participants.append(
                {
                    "id": session["id"],
                    "type": "Guest",
                    "name": session["guestName"],
                    "items": items,
                    "total": sum(float(item["dish"]["price"]) * int(item["quantity"]) for item in items),
                    "isSubmitted": bool(session.get("submitted")),
                }
            )
        self.send_json(200, {"participants": participants, "total": len(participants)})

    @staticmethod
    def guest_items(session: dict[str, object]) -> list[dict[str, object]]:
        return [
            {"dish": item["dish"], "quantity": item["quantity"]}
            for item in session.get("items", [])
        ]

    def get_group_status(self, group_id: str) -> None:
        with connect_database() as connection:
            group = load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = 'group' AND id = ?",
                    (group_id,),
                ).fetchone()
            )
            guests = [
                session for session in records_of(connection, "guest-session")
                if session.get("groupReservationId") == group_id
            ]
        if group is None:
            self.send_json(404, {"error": "Group reservation not found"})
            return
        self.send_json(
            200,
            {
                "currentParticipants": 1 + len(guests),
                "maxCapacity": int(group.get("maxCapacity", 8)),
                "status": group.get("status", "Open"),
            },
        )

    def get_guest_invite(self, token: str) -> None:
        with connect_database() as connection:
            group = load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = 'group' AND json_extract(payload, '$.token') = ?",
                    (token,),
                ).fetchone()
            )
        if group is None or group.get("status") != "Open":
            self.send_json(404, {"error": "Invite is invalid or expired"})
            return
        reservation = self.get_record("reservation", str(group["reservationId"]))
        if reservation is None:
            self.send_json(404, {"error": "Reservation not found"})
            return
        self.send_json(
            200,
            {
                "GroupReservationId": group["id"],
                "LocationId": group["locationId"],
                "RestaurantName": self.enrich_reservation(reservation)["restaurantName"],
                "LocationAddress": self.enrich_reservation(reservation)["locationAddress"],
                "StartTime": reservation["startTime"],
                "EndTime": reservation["endTime"],
                "MaxGuestCount": group["maxCapacity"],
                "TableNumber": self.get_record("table", str(reservation["tableId"]))["tableNumber"],
                "InviterName": self.get_user_name(reservation.get("customerId")),
            },
        )

    def get_invite_token(self, reservation_id: str) -> None:
        user = self.require_user()
        if user is None:
            return
        reservation = self.get_record("reservation", reservation_id)
        if reservation is None:
            self.send_json(404, {"error": "Reservation not found"})
            return
        if not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot create an invite for this reservation"})
            return
        group = self.ensure_group(reservation_id)
        self.send_json(200, {"token": group["token"]})

    def get_owner_session(self, reservation_id: str) -> None:
        user = self.require_user()
        if user is None:
            return
        reservation = self.get_record("reservation", reservation_id)
        if reservation is None:
            self.send_json(404, {"error": "Reservation not found"})
            return
        if not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot access this reservation"})
            return
        group = self.ensure_group(reservation_id)
        self.send_json(200, {"guestSessionId": group["ownerSessionId"]})

    def get_reservation_feedback(self, reservation_id: str) -> None:
        if self.get_record("reservation", reservation_id) is None:
            self.send_json(404, {"error": "Reservation not found"})
            return
        with connect_database() as connection:
            items = [
                item for item in records_of(connection, "feedback")
                if item.get("reservationId") == reservation_id
            ]
        if not items:
            self.send_json(200, None)
            return
        response: dict[str, object] = {"reservationId": reservation_id}
        for item in items:
            response[item["type"][0].lower() + item["type"][1:]] = item
        self.send_json(200, response)

    def get_feedback(self) -> None:
        query = parse_qs(urlsplit(self.path).query)
        location_id = query.get("locationId", [""])[0]
        try:
            page = max(1, int(query.get("page", ["1"])[0]))
        except ValueError:
            self.send_json(400, {"error": "Page must be a positive integer"})
            return
        size = 10
        with connect_database() as connection:
            items = [
                item for item in records_of(connection, "feedback")
                if item.get("locationId") == location_id
            ]
        feedback_type = query.get("type", [None])[0]
        if feedback_type:
            normalized_type = normalize_feedback_type(feedback_type)
            items = [item for item in items if item.get("type") == normalized_type]
        sort = query.get("sort", ["NewestFirst"])[0]
        if sort == "TopRatedFirst":
            items.sort(key=lambda item: float(item.get("rating", 0)), reverse=True)
        elif sort == "LowRatedFirst":
            items.sort(key=lambda item: float(item.get("rating", 0)))
        else:
            items.sort(key=lambda item: item.get("createdAt", ""), reverse=sort != "OldestFirst")
        self.send_json(
            200,
            {
                "items": items[(page - 1) * size : page * size],
                "totalPages": max(1, (len(items) + size - 1) // size),
                "currentPage": page,
            },
        )

    def get_feedback_token(self) -> None:
        query = parse_qs(urlsplit(self.path).query)
        reservation_id = query.get("reservationId", [""])[0]
        if not self.get_record("reservation", reservation_id):
            self.send_json(404, {"error": "Reservation not found"})
            return
        token = secrets.token_urlsafe(32)
        self.save_record("feedback-token", reservation_id, {"token": token})
        self.send_json(200, token)

    def get_report(self, download: bool) -> None:
        if self.require_admin() is None:
            return
        query = parse_qs(urlsplit(self.path).query)
        location_id = query.get("locationId", [""])[0]
        start = query.get("startDate", [""])[0]
        end = query.get("endDate", [""])[0]
        report_type = query.get("type", ["0"])[0]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", start) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", end
        ) or start > end:
            self.send_json(400, {"error": "Valid startDate and endDate are required"})
            return
        with connect_database() as connection:
            reservations = records_of(connection, "reservation")
            orders = records_of(connection, "order")
            feedback = records_of(connection, "feedback")
        location = self.get_record("location", location_id)
        if location is None:
            self.send_json(404, {"error": "Location not found"})
            return
        location_reservations = [r for r in reservations if r.get("tableId") and self.get_table_location(r["tableId"]) == location_id and start <= str(r.get("startTime", ""))[:10] <= end]
        location_orders = [
            order
            for order in orders
            if any(
                reservation.get("id") == order.get("reservationId")
                and self.get_table_location(reservation.get("tableId")) == location_id
                for reservation in location_reservations
            )
        ]
        location_feedback = [item for item in feedback if item.get("locationId") == location_id]
        cuisine_ratings = [
            float(item["rating"])
            for item in location_feedback
            if item.get("type") == "CuisineExperience"
        ]
        if report_type == "0":
            rows = []
            with connect_database() as connection:
                waiters = records_of(connection, "waiter")
                user_rows = connection.execute(
                    "SELECT * FROM users WHERE role = 'Waiter'"
                ).fetchall()
            user_by_id = {row["id"]: public_user(row) for row in user_rows}
            location_waiters = [
                (assignment, user_by_id[assignment["userId"]])
                for assignment in waiters
                if assignment.get("locationId") == location_id
                and assignment.get("userId") in user_by_id
            ]
            if not location_waiters:
                rows.append(
                    {
                        "locationName": location["address"],
                        "locationId": location_id,
                        "waiterName": "No waiter assigned",
                        "waiterEmail": "",
                        "startDate": start,
                        "endDate": end,
                        "workingHours": 0,
                        "totalOrders": len(location_orders),
                        "ordersProcessed": len(location_orders),
                        "deltaTotalOrders": len(location_orders),
                        "ordersDelta": "0%",
                        "avgServiceFeedback": 0,
                    }
                )
            for assignment, waiter in location_waiters:
                rows.append(
                    {
                        "locationName": location["address"],
                        "locationId": location_id,
                        "waiterName": f"{waiter['firstName']} {waiter['lastName']}",
                        "waiterEmail": waiter["email"],
                        "waiterId": waiter["id"],
                        "startDate": start,
                        "endDate": end,
                        "workingHours": 0,
                        "totalOrders": len(location_orders),
                        "ordersProcessed": len(location_orders),
                        "deltaTotalOrders": len(location_orders),
                        "ordersDelta": "0%",
                        "avgServiceFeedback": self.average_rating(location_feedback, "Service"),
                    }
                )
        else:
            revenue = 0.0
            for order in location_orders:
                for item in order.get("orderItems", []):
                    dish = self.get_record("dish", str(item.get("dishId")))
                    if dish:
                        revenue += float(dish.get("price", 0)) * int(item["quantity"])
            rows = [
                {
                    "locationName": location["address"],
                    "locationId": location_id,
                    "startDate": start,
                    "endDate": end,
                    "totalOrders": len(location_orders),
                    "revenue": round(revenue, 2),
                    "avgCuisineFeedback": round(sum(cuisine_ratings) / len(cuisine_ratings), 2) if cuisine_ratings else 0,
                    "minCuisineFeedback": min(cuisine_ratings) if cuisine_ratings else 0,
                    "deltaAvgCuisineFeedback": 0,
                    "deltaRevenue": 0,
                }
            ]
        user = self.authenticated_user()
        if user:
            history_id = str(uuid.uuid4())
            self.save_record(
                "report",
                history_id,
                {
                    "id": history_id,
                    "userId": user["id"],
                    "reportType": int(report_type) if report_type.isdigit() else 0,
                    "locationId": location_id,
                    "startDate": start,
                    "endDate": end,
                    "createdAt": utc_now(),
                },
                user["id"],
            )
        if download:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            body = output.getvalue().encode("utf-8")
            file_type = query.get("format", ["csv"])[0].lower()
            if file_type == "pdf":
                body = self.render_report_pdf(rows[0])
                content_type = "application/pdf"
                extension = "pdf"
            elif file_type == "excel":
                content_type = "application/vnd.ms-excel; charset=utf-8"
                extension = "xls"
            else:
                content_type = "text/csv; charset=utf-8"
                extension = "csv"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", f'attachment; filename="report_{start}_{end}.{extension}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_json(200, rows)

    @staticmethod
    def average_rating(items: list[dict[str, object]], feedback_type: str) -> float:
        ratings = [
            float(item["rating"])
            for item in items
            if item.get("type") == feedback_type
        ]
        return round(sum(ratings) / len(ratings), 2) if ratings else 0

    def get_reports(self) -> None:
        user = self.require_admin()
        if user is None:
            return
        with connect_database() as connection:
            reports = records_of(connection, "report", user["id"])
        self.send_json(200, reports)

    @staticmethod
    def render_report_pdf(row: dict[str, object]) -> bytes:
        text = "Green Tasty report\n" + "\n".join(
            f"{key}: {value}" for key, value in row.items()
        )
        escaped = (
            text.encode("ascii", "replace")
            .decode("ascii")
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        stream = f"BT /F1 10 Tf 50 780 Td ({escaped.replace(chr(10), ') Tj 0 -14 Td (')}) Tj ET"
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream".encode("ascii"),
        ]
        output = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for index, obj in enumerate(objects, 1):
            offsets.append(len(output))
            output.extend(f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
        xref_offset = len(output)
        output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
        output.extend(
            b"".join(f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets[1:])
        )
        output.extend(
            f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("ascii")
        )
        return bytes(output)

    def get_user_name(self, user_id: object) -> str:
        if not user_id:
            return "Guest"
        with connect_database() as connection:
            user = connection.execute(
                "SELECT first_name, last_name FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return f"{user['first_name']} {user['last_name']}" if user else "Guest"

    def get_table_location(self, table_id: object) -> object:
        table = self.get_record("table", str(table_id))
        return table.get("locationId") if table else None

    def get_record(self, kind: str, record_id: str) -> dict[str, object] | None:
        with connect_database() as connection:
            if kind in {"dish", "location"}:
                table_name = "dishes" if kind == "dish" else "locations"
                row = connection.execute(
                    f"SELECT payload FROM {table_name} WHERE id = ?",
                    (record_id,),
                ).fetchone()
                return load_record(row)
            return load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = ? AND id = ?",
                    (kind, record_id),
                ).fetchone()
            )

    def save_record(
        self,
        kind: str,
        record_id: str,
        value: dict[str, object],
        owner_id: str | None = None,
    ) -> None:
        with connect_database() as connection:
            save_record(connection, kind, record_id, value, owner_id)

    def ensure_group(self, reservation_id: str) -> dict[str, object]:
        with connect_database() as connection:
            existing = load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = 'group' AND id = ?",
                    (reservation_id,),
                ).fetchone()
            )
        if existing:
            return existing
        reservation = self.get_record("reservation", reservation_id)
        table = self.get_record("table", str(reservation.get("tableId"))) if reservation else None
        group = {
            "id": reservation_id,
            "reservationId": reservation_id,
            "locationId": table.get("locationId") if table else LOCATIONS[0]["id"],
            "token": secrets.token_urlsafe(24),
            "ownerSessionId": str(uuid.uuid4()),
            "maxCapacity": int(reservation.get("guestCount", 4)) if reservation else 4,
            "status": "Open",
            "items": [],
            "submitted": False,
        }
        self.save_record("group", reservation_id, group)
        return group

    def get_dishes(self) -> None:
        query = parse_qs(urlsplit(self.path).query)
        dish_type = query.get("dishType", [None])[0]
        name = query.get("name", [None])[0]
        sort_by = query.get("sortBy", [""])[0]
        with connect_database() as connection:
            rows = connection.execute("SELECT payload FROM dishes ORDER BY rowid").fetchall()
        dishes = [json.loads(row["payload"]) for row in rows]
        if dish_type:
            dishes = [dish for dish in dishes if dish["dishType"].casefold() == dish_type.casefold()]
        if name:
            dishes = [dish for dish in dishes if name.casefold() in dish["name"].casefold()]
        if sort_by == "PriceAscending":
            dishes.sort(key=lambda dish: dish["price"])
        elif sort_by == "PriceDescending":
            dishes.sort(key=lambda dish: dish["price"], reverse=True)
        self.send_json(200, dishes)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path.rstrip("/")
        body = self.read_json()
        if body is None:
            self.send_json(400, {"error": "Invalid request body"})
            return
        try:
            if path == "/register":
                self.register(body)
            elif path == "/signin":
                self.sign_in(body)
            elif path == "/reservations":
                self.create_reservation(body)
            elif path == "/orders":
                self.create_order(body)
            elif path == "/feedback":
                self.create_feedback(body)
            elif path == "/guest/sessions":
                self.create_guest_session(body)
            elif path == "/dishes":
                self.create_dish(body)
            elif path == "/locations":
                self.create_location(body)
            elif path == "/tables":
                self.create_table(body)
            elif path == "/waiters":
                self.create_waiter(body)
            elif path.startswith("/guest/sessions/") and path.endswith("/dishes"):
                session_id = unquote(path[len("/guest/sessions/") : -len("/dishes")].strip("/"))
                self.update_guest_dishes(session_id, body, add=True)
            elif path.startswith("/guest/sessions/") and path.endswith("/submit"):
                session_id = unquote(path[len("/guest/sessions/") : -len("/submit")].strip("/"))
                self.submit_guest_session(session_id)
            elif path.startswith("/orders/") and path.endswith("/submit"):
                reservation_id = unquote(path[len("/orders/") : -len("/submit")].strip("/"))
                self.submit_order(reservation_id, submitted=True)
            elif path.startswith("/orders/") and path.endswith("/unsubmit"):
                reservation_id = unquote(path[len("/orders/") : -len("/unsubmit")].strip("/"))
                self.submit_order(reservation_id, submitted=False)
            elif path.startswith("/group-reservations/") and path.endswith("/submit"):
                group_id = unquote(path[len("/group-reservations/") : -len("/submit")].strip("/"))
                self.submit_group(group_id)
            else:
                self.send_json(404, {"error": "Not found"})
        except sqlite3.Error:
            self.log_error("Database error while handling POST %s", path)
            self.send_json(500, {"error": "Database error"})

    def register(self, body: dict[str, object]) -> None:
        first_name = body.get("firstName")
        last_name = body.get("lastName")
        email = body.get("email")
        password = body.get("password")
        confirm_password = body.get("confirmPassword")
        if not isinstance(first_name, str) or not NAME_PATTERN.fullmatch(first_name):
            self.send_json(400, {"error": "First name must contain 2 to 50 Latin letters, hyphens, or apostrophes."})
            return
        if not isinstance(last_name, str) or not NAME_PATTERN.fullmatch(last_name):
            self.send_json(400, {"error": "Last name must contain 2 to 50 Latin letters, hyphens, or apostrophes."})
            return
        if not isinstance(email, str) or len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
            self.send_json(400, {"error": "Please enter a valid email address."})
            return
        if not isinstance(password, str) or not 8 <= len(password) <= 16:
            self.send_json(400, {"error": "Password must be between 8 and 16 characters long."})
            return
        if password != confirm_password:
            self.send_json(400, {"error": "Passwords do not match."})
            return

        password_hash, password_salt = hash_password(password)
        user_id = str(uuid.uuid4())
        try:
            with connect_database() as connection:
                connection.execute(
                    """
                    INSERT INTO users (id, first_name, last_name, email, password_hash, password_salt, role)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        first_name,
                        last_name,
                        email.strip().lower(),
                        password_hash,
                        password_salt,
                        "Admin" if email.strip().lower() == os.environ.get("LOCAL_API_ADMIN_EMAIL", "").strip().lower() and os.environ.get("LOCAL_API_ADMIN_EMAIL") else "Customer",
                    ),
                )
        except sqlite3.IntegrityError:
            self.send_json(409, {"error": "An account with this email already exists."})
            return
        self.send_json(201, {"message": "User registered successfully"})

    def sign_in(self, body: dict[str, object]) -> None:
        email = body.get("email")
        password = body.get("password")
        if not isinstance(email, str) or not isinstance(password, str):
            self.send_json(400, {"error": "Email and password are required."})
            return
        with connect_database() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
            ).fetchone()
        if user is None or not verify_password(
            password, user["password_hash"], user["password_salt"]
        ):
            self.send_json(401, {"error": "Invalid email or password"})
            return
        token = create_token(user)
        self.send_json(
            200,
            {
                "message": "Sign in successful",
                "idToken": token,
                "accessToken": token,
            },
        )

    def require_admin(self) -> sqlite3.Row | None:
        user = self.require_user()
        if user is not None and user["role"] != "Admin":
            self.send_json(403, {"error": "Administrator access is required"})
            return None
        return user

    def create_reservation(self, body: dict[str, object]) -> None:
        table_id = body.get("tableId")
        start = parse_datetime(body.get("startTime"))
        end = parse_datetime(body.get("endTime"))
        try:
            guest_count = int(body.get("guestCount", 0))
        except (ValueError, TypeError):
            guest_count = 0
        if not isinstance(table_id, str) or not start or not end or end <= start or guest_count < 1:
            self.send_json(400, {"error": "A table, valid time range, and guest count are required"})
            return
        user = self.authenticated_user()
        with connect_database() as connection:
            table = load_record(
                connection.execute(
                    "SELECT payload FROM records WHERE kind = 'table' AND id = ?",
                    (table_id,),
                ).fetchone()
            )
            reservations = records_of(connection, "reservation")
            waiters = records_of(connection, "waiter")
        if table is None:
            self.send_json(404, {"error": "Table not found"})
            return
        if guest_count > int(table["capacity"]):
            self.send_json(400, {"error": "Guest count exceeds table capacity"})
            return
        if self.table_is_reserved(table_id, start, end, reservations):
            self.send_json(409, {"error": "This table is already reserved for that time"})
            return
        reservation_id = str(uuid.uuid4())
        waiter = next(
            (
                assigned
                for assigned in waiters
                if assigned.get("locationId") == table["locationId"]
            ),
            None,
        )
        reservation = {
            "id": reservation_id,
            "tableId": table_id,
            "customerId": user["id"] if user else None,
            "startTime": start.isoformat().replace("+00:00", "Z"),
            "endTime": end.isoformat().replace("+00:00", "Z"),
            "guestCount": guest_count,
            "status": 0,
            "waiterId": waiter.get("userId", "") if waiter else "",
            "createdByRole": user["role"] if user else "Guest",
            "customerEmail": body.get("customerEmail"),
        }
        self.save_record("reservation", reservation_id, reservation, user["id"] if user else None)
        if waiter:
            notification_id = str(uuid.uuid4())
            self.save_record(
                "notification",
                notification_id,
                {
                    "id": notification_id,
                    "message": "A new reservation has been created.",
                    "orderId": "",
                    "reservationId": reservation_id,
                    "createdAt": utc_now(),
                    "isRead": False,
                    "userId": waiter["userId"],
                },
                waiter["userId"],
            )
        self.send_json(201, self.enrich_reservation(reservation))

    def create_order(self, body: dict[str, object]) -> None:
        user = self.require_user()
        if user is None:
            return
        reservation_id = body.get("reservationId")
        order_items = body.get("orderItems")
        if not isinstance(reservation_id, str) or not isinstance(order_items, list):
            self.send_json(400, {"error": "reservationId and orderItems are required"})
            return
        reservation = self.get_record("reservation", reservation_id)
        if reservation is None:
            self.send_json(404, {"error": "Reservation not found"})
            return
        if not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot edit this reservation's order"})
            return
        valid_items, error = self.normalize_order_items(order_items)
        if error:
            self.send_json(400, {"error": error})
            return
        order = {
            "orderId": reservation_id,
            "reservationId": reservation_id,
            "orderItems": valid_items,
            "status": 0,
        }
        self.save_record("order", reservation_id, order, reservation.get("customerId"))
        waiter_id = reservation.get("waiterId")
        if waiter_id:
            notification_id = str(uuid.uuid4())
            self.save_record(
                "notification",
                notification_id,
                {
                    "id": notification_id,
                    "message": "A pre-order is ready for review.",
                    "orderId": reservation_id,
                    "reservationId": reservation_id,
                    "createdAt": utc_now(),
                    "isRead": False,
                    "userId": waiter_id,
                },
                waiter_id,
            )
        self.send_json(201, self.enrich_order(order))

    def normalize_order_items(
        self, items: list[object]
    ) -> tuple[list[dict[str, object]], str | None]:
        normalized = []
        for item in items:
            if not isinstance(item, dict):
                return [], "Each order item must be an object"
            dish_id = item.get("dishId")
            try:
                quantity = int(item.get("quantity", 0))
            except (TypeError, ValueError):
                return [], "Item quantity must be a positive integer"
            dish = self.get_record("dish", str(dish_id))
            if dish is None:
                return [], f"Dish {dish_id} was not found"
            if quantity < 1 or quantity > 99:
                return [], "Item quantity must be between 1 and 99"
            normalized.append(
                {"dishId": dish_id, "quantity": quantity, "state": 0}
            )
        return normalized, None

    def create_feedback(self, body: dict[str, object]) -> None:
        reservation_id = body.get("reservationId")
        user = self.authenticated_user()
        reservation = self.get_record("reservation", str(reservation_id))
        if reservation is None:
            self.send_json(404, {"error": "Reservation not found"})
            return
        token = body.get("token")
        if user is None:
            stored_token = self.get_record("feedback-token", str(reservation_id))
            if not stored_token or not isinstance(token, str) or not hmac.compare_digest(token, str(stored_token["token"])):
                self.send_json(401, {"error": "A valid feedback token is required"})
                return
        try:
            rating = int(body.get("rating", 0))
        except (TypeError, ValueError):
            rating = 0
        feedback_type = normalize_feedback_type(body.get("type"))
        if not 1 <= rating <= 5 or feedback_type is None:
            self.send_json(400, {"error": "Rating and feedback type are invalid"})
            return
        record_id = f"{reservation_id}:{feedback_type}"
        feedback = {
            "reservationId": reservation_id,
            "locationId": self.get_table_location(reservation.get("tableId")),
            "userId": user["id"] if user else None,
            "comment": body.get("comment") or None,
            "rating": rating,
            "createdAt": utc_now(),
            "type": feedback_type,
            "username": f"{user['first_name']} {user['last_name']}" if user else None,
        }
        self.save_record("feedback", record_id, feedback, user["id"] if user else None)
        self.send_json(201, feedback)

    def create_guest_session(self, body: dict[str, object]) -> None:
        group_id = body.get("groupReservationId")
        guest_name = body.get("guestName")
        if not isinstance(group_id, str) or not isinstance(guest_name, str) or not guest_name.strip():
            self.send_json(400, {"error": "A group reservation and guest name are required"})
            return
        group = self.get_record("group", group_id)
        if group is None or group.get("status") != "Open":
            self.send_json(404, {"error": "Group reservation not found or closed"})
            return
        with connect_database() as connection:
            active_sessions = [
                session for session in records_of(connection, "guest-session")
                if session.get("groupReservationId") == group_id
            ]
        if len(active_sessions) + 1 >= int(group["maxCapacity"]):
            self.send_json(409, {"error": "The guest limit for this reservation has been reached"})
            return
        session_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        session = {
            "id": session_id,
            "groupReservationId": group_id,
            "guestName": guest_name.strip()[:80],
            "token": token,
            "items": [],
            "submitted": False,
        }
        self.save_record("guest-session", session_id, session)
        self.send_json(201, {"SessionId": session_id, "SessionToken": token})

    def update_guest_dishes(
        self, session_id: str, body: dict[str, object], add: bool
    ) -> None:
        session, _ = self.guest_session_from_request(session_id)
        if session is None:
            return
        dish_id = body.get("dishId")
        try:
            quantity = int(body.get("quantity", 0))
        except (ValueError, TypeError):
            quantity = 0
        dish = self.get_record("dish", str(dish_id))
        if dish is None or quantity < 1 or quantity > 99:
            self.send_json(400, {"error": "A valid dish and quantity are required"})
            return
        existing = next((item for item in session["items"] if item.get("dish", {}).get("id") == dish_id), None)
        if add:
            if dish.get("state") != "Available":
                self.send_json(409, {"error": "Dish is not available"})
                return
            if existing:
                existing["quantity"] = int(existing["quantity"]) + quantity
            else:
                session["items"].append({"dish": dish, "quantity": quantity})
        elif existing:
            remaining = int(existing["quantity"]) - quantity
            if remaining > 0:
                existing["quantity"] = remaining
            else:
                session["items"].remove(existing)
        else:
            self.send_json(404, {"error": "Dish is not in the guest cart"})
            return
        self.save_record("guest-session", session_id, session)
        self.send_empty(204)

    def submit_guest_session(self, session_id: str) -> None:
        session, _ = self.guest_session_from_request(session_id)
        if session is None:
            return
        if not session["items"]:
            self.send_json(400, {"error": "Cannot submit an empty guest cart"})
            return
        session["submitted"] = True
        self.save_record("guest-session", session_id, session)
        self.send_empty(204)

    def submit_order(self, reservation_id: str, submitted: bool) -> None:
        user = self.require_user()
        if user is None:
            return
        order = self.get_record("order", reservation_id)
        reservation = self.get_record("reservation", reservation_id)
        if order is None or reservation is None:
            self.send_json(404, {"error": "Order not found"})
            return
        if not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot update this order"})
            return
        if submitted and not order["orderItems"]:
            self.send_json(400, {"error": "Cannot submit an empty order"})
            return
        order["status"] = 1 if submitted else 0
        self.save_record("order", reservation_id, order, reservation.get("customerId"))
        self.send_empty(204)

    def submit_group(self, group_id: str) -> None:
        user = self.require_user()
        if user is None:
            return
        group = self.get_record("group", group_id)
        if group is None:
            self.send_json(404, {"error": "Group reservation not found"})
            return
        reservation = self.get_record("reservation", str(group["reservationId"]))
        if reservation is None or not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot submit this group order"})
            return
        with connect_database() as connection:
            sessions = [
                item for item in records_of(connection, "guest-session")
                if item.get("groupReservationId") == group_id
            ]
        group["status"] = "Submitted"
        group["submitted"] = True
        self.save_record("group", group_id, group)
        for session in sessions:
            session["submitted"] = True
            self.save_record("guest-session", str(session["id"]), session)
        self.send_empty(204)

    def create_dish(self, body: dict[str, object]) -> None:
        if self.require_admin() is None:
            return
        name = body.get("name")
        location_id = body.get("locationId")
        if not isinstance(name, str) or not name.strip():
            self.send_json(400, {"error": "Dish name is required"})
            return
        requested_locations = body.get("locationIds")
        if not isinstance(location_id, str) and isinstance(requested_locations, list) and requested_locations:
            location_id = requested_locations[0]
        if not self.get_record("location", str(location_id)):
            self.send_json(400, {"error": "A valid locationId is required"})
            return
        dish_id = str(uuid.uuid4())
        image = body.get("imageBase64") or body.get("imageUrl")
        if isinstance(requested_locations, list) and requested_locations:
            location_id = requested_locations[0]
            if not all(self.get_record("location", str(item)) for item in requested_locations):
                self.send_json(400, {"error": "A valid locationId is required"})
                return
        try:
            price = float(body.get("price", 0))
        except (ValueError, TypeError):
            self.send_json(400, {"error": "Dish price must be a number"})
            return
        if price < 0:
            self.send_json(400, {"error": "Dish price cannot be negative"})
            return
        image_url_value = image_url(image, "assets/img/dish.png")
        dish = {
            "id": dish_id,
            "name": name.strip(),
            "description": body.get("description", ""),
            "dishType": body.get("dishType", "MainCourse"),
            "price": price,
            "weight": body.get("weight", ""),
            "calories": body.get("calories", ""),
            "proteins": body.get("proteins", ""),
            "fats": body.get("fats", ""),
            "carbohydrates": body.get("carbohydrates", ""),
            "vitamins": body.get("vitamins", ""),
            "imageUrl": image_url_value,
            "state": body.get("state", "Available"),
            "locationId": location_id,
            "locationIds": requested_locations or [location_id],
        }
        self.save_dish(dish)
        self.send_json(201, dish)

    def save_dish(self, dish: dict[str, object]) -> None:
        with connect_database() as connection:
            connection.execute(
                """
                INSERT INTO dishes (id, location_id, payload) VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET location_id = excluded.location_id, payload = excluded.payload
                """,
                (dish["id"], dish["locationId"], json.dumps(dish)),
            )

    def create_location(self, body: dict[str, object]) -> None:
        if self.require_admin() is None:
            return
        address = body.get("address")
        if not isinstance(address, str) or not address.strip():
            self.send_json(400, {"error": "Location address is required"})
            return
        try:
            capacity = int(body.get("totalCapacity", 0))
            rating = float(body.get("rating", 0))
        except (ValueError, TypeError):
            self.send_json(400, {"error": "Invalid location capacity or rating"})
            return
        if capacity < 0 or not 0 <= rating <= 5:
            self.send_json(400, {"error": "Location capacity or rating is out of range"})
            return
        location = {
            "id": str(uuid.uuid4()),
            "address": address.strip(),
            "description": body.get("description", ""),
            "totalCapacity": capacity,
            "averageOccupancy": body.get("averageOccupancy", "0%"),
            "imageUrl": image_url(body.get("imageBase64"), "assets/img/restaurant.png"),
            "rating": rating,
        }
        with connect_database() as connection:
            connection.execute(
                "INSERT INTO locations (id, payload) VALUES (?, ?)",
                (location["id"], json.dumps(location)),
            )
        self.send_json(201, location)

    def create_table(self, body: dict[str, object]) -> None:
        if self.require_admin() is None:
            return
        location_id = body.get("locationId") or LOCATIONS[0]["id"]
        if not self.get_record("location", str(location_id)):
            self.send_json(400, {"error": "A valid locationId is required"})
            return
        try:
            capacity = int(body.get("capacity", 0))
            number = int(body.get("tableNumber", 0))
        except (ValueError, TypeError):
            self.send_json(400, {"error": "Invalid table data"})
            return
        if capacity < 1 or number < 1:
            self.send_json(400, {"error": "Table capacity and number must be positive"})
            return
        table = {
            "id": str(uuid.uuid4()),
            "tableNumber": number,
            "locationId": location_id,
            "capacity": capacity,
        }
        self.save_record("table", table["id"], table, str(location_id))
        self.send_json(201, table)

    def create_waiter(self, body: dict[str, object]) -> None:
        if self.require_admin() is None:
            return
        email = body.get("email")
        location_id = body.get("locationId") or LOCATIONS[0]["id"]
        if not isinstance(email, str) or not EMAIL_PATTERN.fullmatch(email):
            self.send_json(400, {"error": "A valid waiter email is required"})
            return
        with connect_database() as connection:
            waiter = connection.execute(
                "SELECT * FROM users WHERE email = ?", (email.lower(),)
            ).fetchone()
            if waiter is None:
                self.send_json(404, {"error": "Register the waiter account before assigning a location"})
                return
            connection.execute(
                "UPDATE users SET role = 'Waiter' WHERE id = ?", (waiter["id"],)
            )
        self.save_record(
            "waiter", waiter["id"], {"userId": waiter["id"], "locationId": location_id}
        )
        self.send_json(200, {"userId": waiter["id"], "locationId": location_id})

    def do_PUT(self) -> None:
        path = urlsplit(self.path).path.rstrip("/")
        body = self.read_json()
        if body is None:
            self.send_json(400, {"error": "Invalid request body"})
            return
        if path == "/me/change-password":
            user = self.require_user()
            if user is None:
                return
            old_password = body.get("oldPassword")
            new_password = body.get("newPassword")
            if (
                not isinstance(old_password, str)
                or not verify_password(old_password, user["password_hash"], user["password_salt"])
            ):
                self.send_json(400, {"error": "Current password is incorrect"})
                return
            if not isinstance(new_password, str) or not 8 <= len(new_password) <= 16:
                self.send_json(400, {"error": "Password must be between 8 and 16 characters long"})
                return
            password_hash, password_salt = hash_password(new_password)
            with connect_database() as connection:
                connection.execute(
                    "UPDATE users SET password_hash = ?, password_salt = ? WHERE id = ?",
                    (password_hash, password_salt, user["id"]),
                )
            self.send_empty(204)
            return
        user = self.authenticated_user()
        if user is None:
            self.send_json(401, {"error": "Please sign in again."})
            return
        if path == "/me":
            first_name = body.get("firstName")
            last_name = body.get("lastName")
            if not isinstance(first_name, str) or not NAME_PATTERN.fullmatch(first_name):
                self.send_json(400, {"error": "Invalid first name"})
                return
            if not isinstance(last_name, str) or not NAME_PATTERN.fullmatch(last_name):
                self.send_json(400, {"error": "Invalid last name"})
                return
            with connect_database() as connection:
                connection.execute(
                    "UPDATE users SET first_name = ?, last_name = ? WHERE id = ?",
                    (first_name, last_name, user["id"]),
                )
            self.send_empty(204)
        elif path == "/me/profile-image":
            image = body.get("base64Image")
            if not isinstance(image, str) or len(image) > 10_000_000:
                self.send_json(400, {"error": "A valid profile image is required"})
                return
            with connect_database() as connection:
                connection.execute(
                    "UPDATE users SET profile_image = ? WHERE id = ?",
                    (image, user["id"]),
                )
            self.send_json(200, image)
        elif path == "/feedback":
            self.update_feedback(body, user)
        elif path == "/reservations":
            self.edit_reservation(body, user)
        elif path.startswith("/dishes/"):
            self.update_dish(unquote(path.removeprefix("/dishes/")), body, user)
        elif path.startswith("/locations/"):
            self.update_location(unquote(path.removeprefix("/locations/")), body, user)
        elif path.startswith("/tables/"):
            self.update_table(unquote(path.removeprefix("/tables/")), body, user)
        elif path.startswith("/orders/"):
            self.update_order(unquote(path.removeprefix("/orders/")), body, user)
        else:
            self.send_json(404, {"error": "Not found"})

    def edit_reservation(
        self, body: dict[str, object], user: sqlite3.Row
    ) -> None:
        reservation_id = body.get("reservationId")
        if not isinstance(reservation_id, str):
            self.send_json(400, {"error": "reservationId is required"})
            return
        reservation = self.get_record("reservation", reservation_id)
        if reservation is None:
            self.send_json(404, {"error": "Reservation not found"})
            return
        if not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot edit this reservation"})
            return
        start = parse_datetime(body.get("startTime"))
        end = parse_datetime(body.get("endTime"))
        try:
            guest_count = int(body.get("guestCount", 0))
        except (ValueError, TypeError):
            guest_count = 0
        table = self.get_record("table", str(reservation["tableId"]))
        if not start or not end or end <= start or guest_count < 1:
            self.send_json(400, {"error": "A valid time range and guest count are required"})
            return
        if not table or guest_count > int(table["capacity"]):
            self.send_json(400, {"error": "Guest count exceeds table capacity"})
            return
        if self.table_is_reserved(
            reservation["tableId"],
            start,
            end,
            self.get_records("reservation"),
            reservation_id,
        ):
            self.send_json(409, {"error": "This table is already reserved for that time"})
            return
        reservation.update(
            {
                "startTime": start.isoformat().replace("+00:00", "Z"),
                "endTime": end.isoformat().replace("+00:00", "Z"),
                "guestCount": guest_count,
            }
        )
        self.save_record("reservation", reservation_id, reservation, reservation.get("customerId"))
        self.send_json(200, self.enrich_reservation(reservation))

    def update_feedback(self, body: dict[str, object], user: sqlite3.Row) -> None:
        reservation_id = body.get("reservationId")
        feedback_type = normalize_feedback_type(body.get("type"))
        key = f"{reservation_id}:{feedback_type}"
        if feedback_type is None:
            self.send_json(400, {"error": "Feedback type is invalid"})
            return
        feedback = self.get_record("feedback", key)
        if feedback is None:
            self.send_json(404, {"error": "Feedback not found"})
            return
        if feedback.get("userId") not in (None, user["id"]):
            self.send_json(403, {"error": "You cannot edit this feedback"})
            return
        try:
            rating = int(body.get("rating", 0))
        except (ValueError, TypeError):
            rating = 0
        if not 1 <= rating <= 5:
            self.send_json(400, {"error": "Rating must be between 1 and 5"})
            return
        feedback["rating"] = rating
        feedback["comment"] = body.get("comment") or None
        self.save_record("feedback", key, feedback, user["id"])
        self.send_json(200, "Feedback updated successfully.")

    def update_dish(
        self, dish_id: str, body: dict[str, object], user: sqlite3.Row
    ) -> None:
        if user["role"] != "Admin":
            self.send_json(403, {"error": "Administrator access is required"})
            return
        existing = self.get_record("dish", dish_id)
        if existing is None:
            self.send_json(404, {"error": "Dish not found"})
            return
        updated = {**existing, **body, "id": dish_id}
        if body.get("imageBase64"):
            updated["imageUrl"] = image_url(body["imageBase64"], "assets/img/dish.png")
        updated.pop("imageBase64", None)
        if not updated.get("locationId") and updated.get("locationIds"):
            updated["locationId"] = updated["locationIds"][0]
        if "locationId" not in updated or not self.get_record("location", str(updated["locationId"])):
            self.send_json(400, {"error": "A valid locationId is required"})
            return
        self.save_dish(updated)
        self.send_json(200, updated)

    def update_location(
        self, location_id: str, body: dict[str, object], user: sqlite3.Row
    ) -> None:
        if user["role"] != "Admin":
            self.send_json(403, {"error": "Administrator access is required"})
            return
        existing = self.get_record("location", location_id)
        if existing is None:
            self.send_json(404, {"error": "Location not found"})
            return
        updated = {**existing, **body, "id": location_id}
        updated.pop("imageBase64", None)
        if body.get("imageBase64"):
            updated["imageUrl"] = body["imageBase64"]
        with connect_database() as connection:
            connection.execute(
                "UPDATE locations SET payload = ? WHERE id = ?",
                (json.dumps(updated), location_id),
            )
        self.send_json(200, updated)

    def update_table(
        self, table_id: str, body: dict[str, object], user: sqlite3.Row
    ) -> None:
        if user["role"] != "Admin":
            self.send_json(403, {"error": "Administrator access is required"})
            return
        table = self.get_record("table", table_id)
        if table is None:
            self.send_json(404, {"error": "Table not found"})
            return
        updated = {**table, **body, "id": table_id}
        self.save_record("table", table_id, updated, str(updated["locationId"]))
        self.send_json(200, updated)

    def update_order(
        self, reservation_id: str, body: dict[str, object], user: sqlite3.Row
    ) -> None:
        order = self.get_record("order", reservation_id)
        reservation = self.get_record("reservation", reservation_id)
        if order is None or reservation is None:
            self.send_json(404, {"error": "Order not found"})
            return
        if not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot update this order"})
            return
        normalized, error = self.normalize_order_items(body.get("orderItems", []))
        if error:
            self.send_json(400, {"error": error})
            return
        order["orderItems"] = normalized
        self.save_record("order", reservation_id, order, reservation.get("customerId"))
        self.send_json(200, self.enrich_order(order))

    def do_DELETE(self) -> None:
        path = urlsplit(self.path).path.rstrip("/")
        body = self.read_json() or {}
        user = self.authenticated_user()
        if path == "/reservations":
            reservation_id = body.get("id")
            reservation = self.get_record("reservation", str(reservation_id))
            if not reservation:
                self.send_json(404, {"error": "Reservation not found"})
                return
            if user is None:
                self.send_json(401, {"error": "Please sign in again."})
                return
            if not self.can_access_reservation(user, reservation):
                self.send_json(403, {"error": "You cannot cancel this reservation"})
                return
            reservation["status"] = 1
            self.save_record("reservation", str(reservation_id), reservation, reservation.get("customerId"))
            self.send_json(200, {"message": "Reservation cancelled"})
        elif path.startswith("/orders/"):
            reservation_id = unquote(path.removeprefix("/orders/"))
            self.delete_order(reservation_id, user)
        elif path.startswith("/guest/sessions/") and path.endswith("/dishes"):
            session_id = unquote(path[len("/guest/sessions/") : -len("/dishes")].strip("/"))
            self.update_guest_dishes(session_id, body, add=False)
        elif path.startswith("/guest/groups/") and "/sessions/" in path:
            parts = path.split("/")
            if len(parts) != 6:
                self.send_json(404, {"error": "Not found"})
                return
            self.delete_guest_session(parts[3], parts[5], user)
        elif path.startswith("/locations/") and "/dishes/" in path:
            _, _, location_id, _, dish_id = path.split("/", 4)
            self.remove_dish_from_location(location_id, dish_id, user)
        elif path.startswith("/locations/"):
            self.delete_location(unquote(path.removeprefix("/locations/")), user)
        elif path.startswith("/dishes/"):
            self.delete_dish(unquote(path.removeprefix("/dishes/")), user)
        elif path.startswith("/tables/"):
            self.delete_table(unquote(path.removeprefix("/tables/")), user)
        elif path == "/waiters":
            self.delete_waiter(body, user)
        else:
            self.send_json(404, {"error": "Not found"})

    def delete_order(self, reservation_id: str, user: sqlite3.Row | None) -> None:
        order = self.get_record("order", reservation_id)
        reservation = self.get_record("reservation", reservation_id)
        if order is None or reservation is None:
            self.send_json(404, {"error": "Order not found"})
            return
        if user is None:
            self.send_json(401, {"error": "Please sign in again."})
            return
        if not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot cancel this order"})
            return
        with connect_database() as connection:
            connection.execute(
                "DELETE FROM records WHERE kind = 'order' AND id = ?", (reservation_id,)
            )
        self.send_empty(204)

    def delete_guest_session(
        self, group_id: str, session_id: str, user: sqlite3.Row | None
    ) -> None:
        if user is None:
            self.send_json(401, {"error": "Please sign in again."})
            return
        session = self.get_record("guest-session", session_id)
        if session is None or session.get("groupReservationId") != group_id:
            self.send_json(404, {"error": "Guest session not found"})
            return
        if session.get("submitted"):
            self.send_json(409, {"error": "Submitted guest sessions cannot be deleted"})
            return
        with connect_database() as connection:
            connection.execute(
                "DELETE FROM records WHERE kind = 'guest-session' AND id = ?",
                (session_id,),
            )
        self.send_empty(204)

    def delete_location(self, location_id: str, user: sqlite3.Row | None) -> None:
        if user is None or user["role"] != "Admin":
            self.send_json(403 if user else 401, {"error": "Administrator access is required"})
            return
        with connect_database() as connection:
            location = load_record(
                connection.execute(
                    "SELECT payload FROM locations WHERE id = ?", (location_id,)
                ).fetchone()
            )
            if not location:
                self.send_json(404, {"error": "Location not found"})
                return
            dishes = [
                json.loads(row["payload"])
                for row in connection.execute(
                    "SELECT payload FROM dishes"
                ).fetchall()
            ]
            if any(
                location_id in dish.get("locationIds", [dish.get("locationId")])
                for dish in dishes
            ):
                self.send_json(409, {"error": "Location still has menu dishes"})
                return
            tables = records_of(connection, "table", location_id)
            if tables:
                self.send_json(409, {"error": "Location has tables; remove them first"})
                return
            connection.execute("DELETE FROM locations WHERE id = ?", (location_id,))
        self.send_empty(204)

    def delete_dish(self, dish_id: str, user: sqlite3.Row | None) -> None:
        if user is None or user["role"] != "Admin":
            self.send_json(403 if user else 401, {"error": "Administrator access is required"})
            return
        with connect_database() as connection:
            exists = connection.execute(
                "SELECT 1 FROM dishes WHERE id = ?", (dish_id,)
            ).fetchone()
            if not exists:
                self.send_json(404, {"error": "Dish not found"})
                return
            connection.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))
        self.send_empty(204)

    def remove_dish_from_location(
        self, location_id: str, dish_id: str, user: sqlite3.Row | None
    ) -> None:
        if user is None or user["role"] != "Admin":
            self.send_json(403 if user else 401, {"error": "Administrator access is required"})
            return
        dish = self.get_record("dish", dish_id)
        if dish is None or dish.get("locationId") != location_id:
            self.send_json(404, {"error": "Dish not found at this location"})
            return
        dish["locationId"] = ""
        self.save_dish(dish)
        self.send_empty(204)

    def delete_table(self, table_id: str, user: sqlite3.Row | None) -> None:
        if user is None or user["role"] != "Admin":
            self.send_json(403 if user else 401, {"error": "Administrator access is required"})
            return
        table = self.get_record("table", table_id)
        if table is None:
            self.send_json(404, {"error": "Table not found"})
            return
        reservations = self.get_records("reservation")
        if any(r.get("tableId") == table_id and r.get("status") == 0 for r in reservations):
            self.send_json(409, {"error": "Table has active reservations"})
            return
        with connect_database() as connection:
            connection.execute(
                "DELETE FROM records WHERE kind = 'table' AND id = ?", (table_id,)
            )
        self.send_empty(204)

    def get_records(self, kind: str) -> list[dict[str, object]]:
        with connect_database() as connection:
            return records_of(connection, kind)

    def delete_waiter(self, body: dict[str, object], user: sqlite3.Row | None) -> None:
        if user is None or user["role"] != "Admin":
            self.send_json(403 if user else 401, {"error": "Administrator access is required"})
            return
        waiter_id = body.get("userId") or body.get("id")
        if not isinstance(waiter_id, str) and isinstance(body.get("email"), str):
            with connect_database() as connection:
                waiter = connection.execute(
                    "SELECT id FROM users WHERE email = ?",
                    (body["email"].strip().lower(),),
                ).fetchone()
            waiter_id = waiter["id"] if waiter else None
        if not isinstance(waiter_id, str):
            self.send_json(400, {"error": "Waiter email is required"})
            return
        with connect_database() as connection:
            connection.execute("UPDATE users SET role = 'Customer' WHERE id = ?", (waiter_id,))
            connection.execute("DELETE FROM records WHERE kind = 'waiter' AND id = ?", (waiter_id,))
        self.send_empty(204)

    def do_PATCH(self) -> None:
        path = urlsplit(self.path).path.rstrip("/")
        body = self.read_json() or {}
        user = self.require_user()
        if user is None:
            return
        if path.startswith("/notifications/") and path.endswith("/read"):
            notification_id = unquote(path[len("/notifications/") : -len("/read")].strip("/"))
            notification = self.get_record("notification", notification_id)
            if notification is None or notification.get("userId") != user["id"]:
                self.send_json(404, {"error": "Notification not found"})
                return
            notification["isRead"] = True
            self.save_record("notification", notification_id, notification, user["id"])
            self.send_empty(204)
        elif path.startswith("/reservations/") and path.endswith("/status"):
            reservation_id = unquote(path[len("/reservations/") : -len("/status")].strip("/"))
            self.update_reservation_status(reservation_id, body, user)
        elif path.startswith("/reservations/") and path.endswith("/table"):
            reservation_id = unquote(path[len("/reservations/") : -len("/table")].strip("/"))
            self.update_reservation_table(reservation_id, body, user)
        elif "/order/confirmations/" in path:
            reservation_id, dish_id = path.split("/reservations/", 1)[1].split("/order/confirmations/")
            self.update_order_dish(reservation_id, dish_id, confirmed=True, user=user)
        elif "/order/cancellations/" in path:
            reservation_id, dish_id = path.split("/reservations/", 1)[1].split("/order/cancellations/")
            self.update_order_dish(reservation_id, dish_id, confirmed=False, user=user)
        else:
            self.send_json(404, {"error": "Not found"})

    def update_reservation_status(
        self, reservation_id: str, body: dict[str, object], user: sqlite3.Row
    ) -> None:
        if user["role"] not in ("Admin", "Waiter"):
            self.send_json(403, {"error": "Only staff can change reservation status"})
            return
        reservation = self.get_record("reservation", reservation_id)
        if reservation is None:
            self.send_json(404, {"error": "Reservation not found"})
            return
        if not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot update this reservation"})
            return
        try:
            status = int(body.get("newStatus"))
        except (ValueError, TypeError):
            status = -1
        if status not in (0, 1, 2, 3):
            self.send_json(400, {"error": "Invalid reservation status"})
            return
        reservation["status"] = status
        self.save_record("reservation", reservation_id, reservation, reservation.get("customerId"))
        self.send_json(200, self.enrich_reservation(reservation))

    def update_reservation_table(
        self, reservation_id: str, body: dict[str, object], user: sqlite3.Row
    ) -> None:
        if user["role"] not in ("Admin", "Waiter"):
            self.send_json(403, {"error": "Only staff can reassign a reservation table"})
            return
        reservation = self.get_record("reservation", reservation_id)
        table_id = body.get("tableId")
        table = self.get_record("table", str(table_id))
        if reservation is None or table is None:
            self.send_json(404, {"error": "Reservation or table not found"})
            return
        if not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot update this reservation"})
            return
        start = parse_datetime(reservation.get("startTime"))
        end = parse_datetime(reservation.get("endTime"))
        if start and end and self.table_is_reserved(table_id, start, end, self.get_records("reservation"), reservation_id):
            self.send_json(409, {"error": "Table is already reserved"})
            return
        reservation["tableId"] = table_id
        self.save_record("reservation", reservation_id, reservation, reservation.get("customerId"))
        self.send_json(200, self.enrich_reservation(reservation))

    def update_order_dish(
        self,
        reservation_id: str,
        dish_id: str,
        confirmed: bool,
        user: sqlite3.Row,
    ) -> None:
        if user["role"] not in ("Admin", "Waiter"):
            self.send_json(403, {"error": "Only staff can confirm or reject order items"})
            return
        reservation = self.get_record("reservation", reservation_id)
        if reservation is None:
            self.send_json(404, {"error": "Reservation not found"})
            return
        if not self.can_access_reservation(user, reservation):
            self.send_json(403, {"error": "You cannot update this order"})
            return
        order = self.get_record("order", reservation_id)
        if order is None:
            self.send_json(404, {"error": "Order not found"})
            return
        item = next((i for i in order["orderItems"] if i.get("dishId") == dish_id), None)
        if item is None:
            self.send_json(404, {"error": "Dish not found in order"})
            return
        item["state"] = 1 if confirmed else 2
        self.save_record("order", reservation_id, order)
        self.send_empty(204)


def run() -> None:
    initialize_database()
    token_secret()
    host = os.environ.get("LOCAL_API_HOST", "127.0.0.1")
    port = int(os.environ.get("LOCAL_API_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"Green Tasty local API listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local API.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
