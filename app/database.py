from __future__ import annotations

import calendar
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Iterable

from app.settings import get_settings

settings = get_settings()


WORKS_SEED = [
    {
        'slug': 'cerberus-chest',
        'title': 'Цербер на груди',
        'description': 'Графичная композиция на груди с тремя головами и жёстким характером линий.',
        'image_path': '/static/assets/works/cerberus-chest.jpeg',
        'review_author': 'Артём',
        'review_text': 'Сделали мощно и ровно. Эскиз лёг по груди идеально, заживление прошло спокойно.',
        'review_rating': 5,
        'sort_order': 1,
    },
    {
        'slug': 'nautical-skull-leg',
        'title': 'Череп и морские детали',
        'description': 'Высокая работа на голени: череп, канаты, гвозди и морская фактура в одном сюжете.',
        'image_path': '/static/assets/works/nautical-skull-leg.jpeg',
        'review_author': 'Никита',
        'review_text': 'Очень сильная детализация. Смотрится жёстко и читается с любого ракурса.',
        'review_rating': 5,
        'sort_order': 2,
    },
    {
        'slug': 'liquid-black-calf',
        'title': 'Liquid Black',
        'description': 'Абстрактная блэкворк-композиция с плотной заливкой и органичными переливами формы.',
        'image_path': '/static/assets/works/liquid-black-calf.jpeg',
        'review_author': 'Марина',
        'review_text': 'Люблю чистый графичный стиль, и здесь всё получилось именно так, как хотела.',
        'review_rating': 5,
        'sort_order': 3,
    },
    {
        'slug': 'angel-wrist',
        'title': 'Ангел на запястье',
        'description': 'Минималистичный ангел с тонкой линией — аккуратная маленькая работа для запястья.',
        'image_path': '/static/assets/works/angel-wrist.jpeg',
        'review_author': 'Алина',
        'review_text': 'Очень аккуратная тонкая линия. Нежно, чисто и без перегруза — именно то, что я хотела.',
        'review_rating': 5,
        'sort_order': 4,
    },
]

REVIEWS_SEED = [
    {
        'author_name': 'Оксана',
        'rating': 5,
        'text': 'Мастер крутой, всё подробно объяснил, помог доработать идею и сделал очень чисто. Однозначно рекомендую.',
    },
    {
        'author_name': 'Артём',
        'rating': 5,
        'text': 'Цербер получился именно таким, каким я его представлял. Сильная работа, всё чётко по форме.',
    },
    {
        'author_name': 'Никита',
        'rating': 5,
        'text': 'Голень забили отлично, несмотря на сложный сюжет. Доволен линиями и общей композицией.',
    },
    {
        'author_name': 'Марина',
        'rating': 5,
        'text': 'Абстракция смотрится очень дорого. Спасибо за спокойную атмосферу и крутой результат.',
    },
    {
        'author_name': 'Алина',
        'rating': 5,
        'text': 'Минимализм на запястье вышел супер-аккуратным. Всё зажило красиво, без сюрпризов.',
    },
]


@dataclass(slots=True)
class UserIdentity:
    user_id: int
    first_name: str
    last_name: str | None
    username: str | None
    is_admin: bool = False


@contextmanager
def get_connection() -> Iterable[sqlite3.Connection]:
    connection = sqlite3.connect(settings.db_path, timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA journal_mode=WAL;')
    connection.execute('PRAGMA foreign_keys=ON;')
    try:
        yield connection
    finally:
        connection.close()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            '''
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                image_path TEXT NOT NULL,
                review_author TEXT NOT NULL,
                review_text TEXT NOT NULL,
                review_rating INTEGER NOT NULL DEFAULT 5,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_name TEXT NOT NULL,
                rating INTEGER NOT NULL,
                text TEXT NOT NULL,
                author_user_id INTEGER,
                is_seed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_date TEXT NOT NULL,
                slot_time TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('available', 'busy')),
                note TEXT,
                UNIQUE(slot_date, slot_time)
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                telegram_name TEXT NOT NULL,
                full_name TEXT NOT NULL,
                age INTEGER NOT NULL,
                service_location TEXT NOT NULL,
                tattoo_description TEXT NOT NULL,
                body_place TEXT NOT NULL,
                size_cm TEXT NOT NULL,
                slot_date TEXT NOT NULL,
                slot_time TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending', 'confirmed', 'rejected')),
                reference_image_path TEXT,
                created_at TEXT NOT NULL,
                admin_message_id INTEGER,
                admin_note TEXT,
                FOREIGN KEY(slot_date, slot_time) REFERENCES availability(slot_date, slot_time)
            );

            CREATE TABLE IF NOT EXISTS app_meta (
                meta_key TEXT PRIMARY KEY,
                meta_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            '''
        )

        works_count = connection.execute('SELECT COUNT(*) FROM works').fetchone()[0]
        if works_count == 0:
            for item in WORKS_SEED:
                connection.execute(
                    '''
                    INSERT INTO works (
                        slug, title, description, image_path,
                        review_author, review_text, review_rating,
                        sort_order, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        item['slug'],
                        item['title'],
                        item['description'],
                        item['image_path'],
                        item['review_author'],
                        item['review_text'],
                        item['review_rating'],
                        item['sort_order'],
                        now_iso(),
                    ),
                )

        reviews_count = connection.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
        if reviews_count == 0:
            for item in REVIEWS_SEED:
                connection.execute(
                    '''
                    INSERT INTO reviews (
                        author_name, rating, text, author_user_id, is_seed, created_at
                    ) VALUES (?, ?, ?, NULL, 1, ?)
                    ''',
                    (item['author_name'], item['rating'], item['text'], now_iso()),
                )


def ensure_month_slots(year: int, month: int) -> None:
    _, days_in_month = calendar.monthrange(year, month)
    with get_connection() as connection:
        for day in range(1, days_in_month + 1):
            slot_date = date(year, month, day).isoformat()
            for slot_time in settings.default_times:
                connection.execute(
                    '''
                    INSERT OR IGNORE INTO availability (slot_date, slot_time, status, note)
                    VALUES (?, ?, 'available', NULL)
                    ''',
                    (slot_date, slot_time),
                )


def get_works() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            '''
            SELECT id, slug, title, description, image_path,
                   review_author, review_text, review_rating, sort_order
            FROM works
            ORDER BY sort_order ASC, id ASC
            '''
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_reviews() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            '''
            SELECT id, author_name, rating, text, author_user_id, is_seed, created_at
            FROM reviews
            ORDER BY datetime(created_at) DESC, id DESC
            '''
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def add_review(author_name: str, rating: int, text: str, author_user_id: int | None = None) -> dict[str, Any]:
    created_at = now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            '''
            INSERT INTO reviews (author_name, rating, text, author_user_id, is_seed, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            ''',
            (author_name, rating, text, author_user_id, created_at),
        )
        review_id = cursor.lastrowid
        row = connection.execute(
            'SELECT id, author_name, rating, text, author_user_id, is_seed, created_at FROM reviews WHERE id = ?',
            (review_id,),
        ).fetchone()
    return _row_to_dict(row) or {}


def update_review(review_id: int, author_name: str, rating: int, text: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        connection.execute(
            'UPDATE reviews SET author_name = ?, rating = ?, text = ? WHERE id = ?',
            (author_name, rating, text, review_id),
        )
        row = connection.execute(
            'SELECT id, author_name, rating, text, author_user_id, is_seed, created_at FROM reviews WHERE id = ?',
            (review_id,),
        ).fetchone()
    return _row_to_dict(row)


def delete_review(review_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
    return cursor.rowcount > 0


def get_month_availability(year: int, month: int) -> dict[str, Any]:
    ensure_month_slots(year, month)
    start_date = date(year, month, 1)
    _, days_in_month = calendar.monthrange(year, month)
    end_date = date(year, month, days_in_month)

    with get_connection() as connection:
        rows = connection.execute(
            '''
            SELECT slot_date, slot_time, status
            FROM availability
            WHERE slot_date BETWEEN ? AND ?
            ORDER BY slot_date ASC, slot_time ASC
            ''',
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()

    days: dict[str, dict[str, Any]] = {}
    for row in rows:
        slot_date = row['slot_date']
        slot_time = row['slot_time']
        status = row['status']
        day_record = days.setdefault(
            slot_date,
            {
                'date': slot_date,
                'slots': [],
                'available_count': 0,
                'busy_count': 0,
                'status': 'busy',
            },
        )
        day_record['slots'].append({'time': slot_time, 'status': status})
        if status == 'available':
            day_record['available_count'] += 1
        else:
            day_record['busy_count'] += 1

    for day_record in days.values():
        day_record['status'] = 'available' if day_record['available_count'] > 0 else 'busy'

    return {
        'year': year,
        'month': month,
        'days': [days.get(date(year, month, day).isoformat(), {
            'date': date(year, month, day).isoformat(),
            'slots': [],
            'available_count': 0,
            'busy_count': 0,
            'status': 'busy',
        }) for day in range(1, days_in_month + 1)],
    }


def get_slots_for_date(slot_date: str) -> list[dict[str, Any]]:
    year, month, _ = [int(part) for part in slot_date.split('-')]
    ensure_month_slots(year, month)
    with get_connection() as connection:
        rows = connection.execute(
            '''
            SELECT slot_time, status
            FROM availability
            WHERE slot_date = ?
            ORDER BY slot_time ASC
            ''',
            (slot_date,),
        ).fetchall()
    return [{'time': row['slot_time'], 'status': row['status']} for row in rows]


def set_slot_status(slot_date: str, slot_time: str, status: str) -> dict[str, Any]:
    with get_connection() as connection:
        connection.execute(
            '''
            INSERT INTO availability (slot_date, slot_time, status, note)
            VALUES (?, ?, ?, NULL)
            ON CONFLICT(slot_date, slot_time) DO UPDATE SET status = excluded.status
            ''',
            (slot_date, slot_time, status),
        )
        row = connection.execute(
            'SELECT slot_date, slot_time, status FROM availability WHERE slot_date = ? AND slot_time = ?',
            (slot_date, slot_time),
        ).fetchone()
    return _row_to_dict(row) or {'slot_date': slot_date, 'slot_time': slot_time, 'status': status}


def set_day_status(slot_date: str, status: str) -> list[dict[str, Any]]:
    year, month, _ = [int(part) for part in slot_date.split('-')]
    ensure_month_slots(year, month)
    updated_rows: list[dict[str, Any]] = []
    for slot_time in settings.default_times:
        updated_rows.append(set_slot_status(slot_date, slot_time, status))
    return updated_rows


def create_booking(
    *,
    user: UserIdentity,
    full_name: str,
    age: int,
    service_location: str,
    tattoo_description: str,
    body_place: str,
    size_cm: str,
    slot_date: str,
    slot_time: str,
    reference_image_path: str | None,
) -> dict[str, Any]:
    year, month, _ = [int(part) for part in slot_date.split('-')]
    ensure_month_slots(year, month)

    with get_connection() as connection:
        connection.execute('BEGIN IMMEDIATE')
        slot_row = connection.execute(
            'SELECT slot_date, slot_time, status FROM availability WHERE slot_date = ? AND slot_time = ?',
            (slot_date, slot_time),
        ).fetchone()
        if slot_row is None:
            connection.execute(
                'INSERT INTO availability (slot_date, slot_time, status, note) VALUES (?, ?, ?, NULL)',
                (slot_date, slot_time, 'available'),
            )
            slot_status = 'available'
        else:
            slot_status = slot_row['status']

        if slot_status != 'available':
            connection.execute('ROLLBACK')
            raise ValueError('Этот слот уже недоступен.')

        connection.execute(
            'UPDATE availability SET status = ? WHERE slot_date = ? AND slot_time = ?',
            ('busy', slot_date, slot_time),
        )
        telegram_name = ' '.join(part for part in [user.first_name, user.last_name or ''] if part).strip()
        created_at = now_iso()
        cursor = connection.execute(
            '''
            INSERT INTO bookings (
                user_id, username, telegram_name, full_name, age, service_location,
                tattoo_description, body_place, size_cm, slot_date, slot_time,
                status, reference_image_path, created_at, admin_message_id, admin_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, NULL, NULL)
            ''',
            (
                user.user_id,
                user.username,
                telegram_name or user.first_name,
                full_name,
                age,
                service_location,
                tattoo_description,
                body_place,
                size_cm,
                slot_date,
                slot_time,
                reference_image_path,
                created_at,
            ),
        )
        booking_id = cursor.lastrowid
        connection.execute('COMMIT')
        row = connection.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    return _row_to_dict(row) or {}


def get_booking(booking_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    return _row_to_dict(row)


def set_booking_admin_message(booking_id: int, message_id: int) -> None:
    with get_connection() as connection:
        connection.execute('UPDATE bookings SET admin_message_id = ? WHERE id = ?', (message_id, booking_id))


def update_booking_status(booking_id: int, status: str, admin_note: str | None = None) -> dict[str, Any] | None:
    with get_connection() as connection:
        connection.execute('BEGIN IMMEDIATE')
        booking_row = connection.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
        if booking_row is None:
            connection.execute('ROLLBACK')
            return None

        if booking_row['status'] == status:
            connection.execute('COMMIT')
            return _row_to_dict(booking_row)

        if status == 'rejected':
            connection.execute(
                'UPDATE availability SET status = ? WHERE slot_date = ? AND slot_time = ?',
                ('available', booking_row['slot_date'], booking_row['slot_time']),
            )
        elif status == 'confirmed':
            connection.execute(
                'UPDATE availability SET status = ? WHERE slot_date = ? AND slot_time = ?',
                ('busy', booking_row['slot_date'], booking_row['slot_time']),
            )

        connection.execute(
            'UPDATE bookings SET status = ?, admin_note = ? WHERE id = ?',
            (status, admin_note, booking_id),
        )
        connection.execute('COMMIT')
        row = connection.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    return _row_to_dict(row)


def list_bookings(limit: int = 100) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            'SELECT * FROM bookings ORDER BY datetime(created_at) DESC, id DESC LIMIT ?',
            (limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def set_meta(meta_key: str, meta_value: str) -> None:
    updated_at = now_iso()
    with get_connection() as connection:
        connection.execute(
            '''
            INSERT INTO app_meta (meta_key, meta_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(meta_key) DO UPDATE SET
                meta_value = excluded.meta_value,
                updated_at = excluded.updated_at
            ''',
            (meta_key, meta_value, updated_at),
        )


def get_meta(meta_key: str) -> str | None:
    with get_connection() as connection:
        row = connection.execute(
            'SELECT meta_value FROM app_meta WHERE meta_key = ?',
            (meta_key,),
        ).fetchone()
    if not row:
        return None
    return str(row['meta_value'])


def set_admin_chat_id(chat_id: int) -> None:
    set_meta('admin_chat_id', str(chat_id))


def get_admin_chat_id() -> int | None:
    value = get_meta('admin_chat_id')
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
