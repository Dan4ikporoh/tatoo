from __future__ import annotations

import calendar
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from app.settings import get_settings

settings = get_settings()


WORKS_SEED = [
    {
        'slug': 'cerberus-chest',
        'title': 'Цербер на груди',
        'description': 'Графичная композиция на груди с тремя головами, острым силуэтом и агрессивным вайбом.',
        'image_path': '/static/assets/works/cerberus-chest.jpeg',
        'review_author': 'Оксана',
        'review_text': 'Мастер крутой, всё сделал очень уверенно и аккуратно. Работа выглядит мощно, как и хотелось.',
        'review_rating': 5,
        'allowed_reviewer_username': '',
        'sort_order': 1,
    },
    {
        'slug': 'nautical-skull-leg',
        'title': 'Череп и морские детали',
        'description': 'Большая работа на голени: череп, канаты, гвозди и плотная графика в одном сюжете.',
        'image_path': '/static/assets/works/nautical-skull-leg.jpeg',
        'review_author': 'Илья',
        'review_text': 'Очень сильная детализация и читаемая композиция. Смотрится жёстко под любым углом.',
        'review_rating': 5,
        'allowed_reviewer_username': '',
        'sort_order': 2,
    },
    {
        'slug': 'liquid-black-calf',
        'title': 'Liquid Black',
        'description': 'Абстрактный blackwork с плотной заливкой, текучими контурами и эффектом движения.',
        'image_path': '/static/assets/works/liquid-black-calf.jpeg',
        'review_author': 'Кристина',
        'review_text': 'Очень красивый поток формы. Хотела смелую чёрную работу — вышло даже лучше ожиданий.',
        'review_rating': 5,
        'allowed_reviewer_username': '',
        'sort_order': 3,
    },
    {
        'slug': 'angel-wrist',
        'title': 'Минималистичный ангел',
        'description': 'Чистый минимализм на запястье: тонкая линия, аккуратный силуэт и воздушное настроение.',
        'image_path': '/static/assets/works/angel-wrist.jpeg',
        'review_author': 'София',
        'review_text': 'Очень нежно и ровно. Линия тонкая, симметрия классная, заживление прошло отлично.',
        'review_rating': 5,
        'allowed_reviewer_username': '',
        'sort_order': 4,
    },
]


REVIEWS_SEED = [
    {
        'author_name': 'Оксана',
        'rating': 5,
        'text': 'Мастер крутой, атмосфера спокойная, всё объяснил, результатом очень довольна.',
    },
    {
        'author_name': 'Даниил',
        'rating': 5,
        'text': 'Чистая работа, уверенная рука и без суеты. По записи всё удобно и понятно.',
    },
    {
        'author_name': 'Марина',
        'rating': 5,
        'text': 'Сделали эскиз под меня, по боли и уходу тоже всё объяснили. Однозначно рекомендую.',
    },
]


@dataclass
class UserIdentity:
    user_id: int
    first_name: str
    last_name: str | None
    username: str | None
    is_admin: bool = False


@contextmanager
def get_connection():
    connection = sqlite3.connect(settings.db_path)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _normalize_username(value: str | None) -> str:
    return (value or '').strip().lstrip('@').lower()


def slugify(value: str) -> str:
    ascii_value = value.lower()
    replacements = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z',
        'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
        'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }
    ascii_value = ''.join(replacements.get(ch, ch) for ch in ascii_value)
    ascii_value = re.sub(r'[^a-z0-9]+', '-', ascii_value).strip('-')
    return ascii_value or 'work'


def _column_exists(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = connection.execute(f'PRAGMA table_info({table_name})').fetchall()
    return any(row['name'] == column_name for row in rows)


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if not _column_exists(connection, table_name, column_name):
        connection.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}')


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
                review_author TEXT,
                review_text TEXT,
                review_rating INTEGER,
                allowed_reviewer_username TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_name TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                text TEXT NOT NULL,
                author_user_id INTEGER,
                is_seed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS work_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                author_username TEXT,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                text TEXT NOT NULL,
                author_user_id INTEGER,
                created_at TEXT NOT NULL,
                UNIQUE(work_id, author_user_id),
                FOREIGN KEY(work_id) REFERENCES works(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS availability (
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
                style_choice TEXT NOT NULL DEFAULT '',
                color_mode TEXT NOT NULL DEFAULT 'blackwork',
                estimated_price_from INTEGER NOT NULL DEFAULT 0,
                estimated_price_to INTEGER NOT NULL DEFAULT 0,
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

        _ensure_column(connection, 'works', 'allowed_reviewer_username', "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, 'works', 'created_at', f"TEXT NOT NULL DEFAULT '{now_iso()}'")
        _ensure_column(connection, 'bookings', 'style_choice', "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, 'bookings', 'color_mode', "TEXT NOT NULL DEFAULT 'blackwork'")
        _ensure_column(connection, 'bookings', 'estimated_price_from', 'INTEGER NOT NULL DEFAULT 0')
        _ensure_column(connection, 'bookings', 'estimated_price_to', 'INTEGER NOT NULL DEFAULT 0')

        works_count = connection.execute('SELECT COUNT(*) FROM works').fetchone()[0]
        if works_count == 0:
            for item in WORKS_SEED:
                connection.execute(
                    '''
                    INSERT INTO works (
                        slug, title, description, image_path,
                        review_author, review_text, review_rating,
                        allowed_reviewer_username, sort_order, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        item['slug'],
                        item['title'],
                        item['description'],
                        item['image_path'],
                        item['review_author'],
                        item['review_text'],
                        item['review_rating'],
                        item['allowed_reviewer_username'],
                        item['sort_order'],
                        now_iso(),
                    ),
                )

        reviews_count = connection.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
        if reviews_count == 0:
            for item in REVIEWS_SEED:
                connection.execute(
                    '''
                    INSERT INTO reviews (author_name, rating, text, author_user_id, is_seed, created_at)
                    VALUES (?, ?, ?, NULL, 1, ?)
                    ''',
                    (item['author_name'], item['rating'], item['text'], now_iso()),
                )

        work_reviews_count = connection.execute('SELECT COUNT(*) FROM work_reviews').fetchone()[0]
        if work_reviews_count == 0:
            works_rows = connection.execute('SELECT id, sort_order, review_author, review_text, review_rating FROM works ORDER BY sort_order, id').fetchall()
            for row in works_rows:
                if row['review_author'] and row['review_text'] and row['review_rating']:
                    connection.execute(
                        '''
                        INSERT INTO work_reviews (work_id, author_name, author_username, rating, text, author_user_id, created_at)
                        VALUES (?, ?, NULL, ?, ?, NULL, ?)
                        ''',
                        (row['id'], row['review_author'], row['review_rating'], row['review_text'], now_iso()),
                    )


def set_meta(meta_key: str, meta_value: str) -> None:
    with get_connection() as connection:
        connection.execute(
            '''
            INSERT INTO app_meta (meta_key, meta_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(meta_key) DO UPDATE SET
                meta_value = excluded.meta_value,
                updated_at = excluded.updated_at
            ''',
            (meta_key, meta_value, now_iso()),
        )


def get_meta(meta_key: str) -> str | None:
    with get_connection() as connection:
        row = connection.execute('SELECT meta_value FROM app_meta WHERE meta_key = ?', (meta_key,)).fetchone()
    return row['meta_value'] if row else None


def set_admin_chat_id(chat_id: int) -> None:
    set_meta('admin_chat_id', str(chat_id))


def get_admin_chat_id() -> int | None:
    value = get_meta('admin_chat_id')
    return int(value) if value else None


def _work_reviews_map(connection: sqlite3.Connection) -> dict[int, list[dict[str, Any]]]:
    rows = connection.execute(
        '''
        SELECT id, work_id, author_name, author_username, rating, text, author_user_id, created_at
        FROM work_reviews
        ORDER BY datetime(created_at) DESC, id DESC
        '''
    ).fetchall()
    mapping: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        mapping.setdefault(int(row['work_id']), []).append(_row_to_dict(row) or {})
    return mapping


def get_works() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            '''
            SELECT id, slug, title, description, image_path, review_author, review_text,
                   review_rating, allowed_reviewer_username, sort_order, created_at
            FROM works
            ORDER BY sort_order ASC, id ASC
            '''
        ).fetchall()
        reviews_map = _work_reviews_map(connection)

    items: list[dict[str, Any]] = []
    for row in rows:
        item = _row_to_dict(row) or {}
        work_reviews = reviews_map.get(int(row['id']), [])
        item['reviews'] = work_reviews
        item['review_count'] = len(work_reviews)
        item['average_rating'] = round(sum(r['rating'] for r in work_reviews) / len(work_reviews), 1) if work_reviews else 0
        items.append(item)
    return items


def get_work(work_id: int) -> dict[str, Any] | None:
    return next((item for item in get_works() if int(item['id']) == int(work_id)), None)


def add_work(*, title: str, description: str, image_path: str, allowed_reviewer_username: str = '') -> dict[str, Any]:
    with get_connection() as connection:
        max_sort = connection.execute('SELECT COALESCE(MAX(sort_order), 0) FROM works').fetchone()[0]
        slug_base = slugify(title)
        slug = slug_base
        suffix = 2
        while connection.execute('SELECT 1 FROM works WHERE slug = ?', (slug,)).fetchone():
            slug = f'{slug_base}-{suffix}'
            suffix += 1

        cursor = connection.execute(
            '''
            INSERT INTO works (
                slug, title, description, image_path, review_author, review_text,
                review_rating, allowed_reviewer_username, sort_order, created_at
            ) VALUES (?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?)
            ''',
            (slug, title, description, image_path, _normalize_username(allowed_reviewer_username), max_sort + 1, now_iso()),
        )
        row = connection.execute('SELECT * FROM works WHERE id = ?', (cursor.lastrowid,)).fetchone()
    return get_work(int(row['id'])) or {}


def update_work(work_id: int, *, title: str | None = None, description: str | None = None, allowed_reviewer_username: str | None = None) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute('SELECT * FROM works WHERE id = ?', (work_id,)).fetchone()
        if not row:
            return None
        next_title = title.strip() if title is not None else row['title']
        next_description = description.strip() if description is not None else row['description']
        next_allowed = _normalize_username(allowed_reviewer_username) if allowed_reviewer_username is not None else row['allowed_reviewer_username']
        connection.execute(
            'UPDATE works SET title = ?, description = ?, allowed_reviewer_username = ? WHERE id = ?',
            (next_title, next_description, next_allowed, work_id),
        )
    return get_work(work_id)


def delete_work(work_id: int) -> dict[str, Any] | None:
    work = get_work(work_id)
    if not work:
        return None
    with get_connection() as connection:
        connection.execute('DELETE FROM works WHERE id = ?', (work_id,))
    image_path = work.get('image_path') or ''
    if image_path.startswith('/uploaded-works/'):
        try:
            filename = image_path.rsplit('/', 1)[-1]
            file_path = settings.public_works_dir / filename
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass
    return work


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
    with get_connection() as connection:
        cursor = connection.execute(
            '''
            INSERT INTO reviews (author_name, rating, text, author_user_id, is_seed, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            ''',
            (author_name, rating, text, author_user_id, now_iso()),
        )
        row = connection.execute('SELECT * FROM reviews WHERE id = ?', (cursor.lastrowid,)).fetchone()
    return _row_to_dict(row) or {}


def update_review(review_id: int, author_name: str, rating: int, text: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        connection.execute(
            'UPDATE reviews SET author_name = ?, rating = ?, text = ? WHERE id = ?',
            (author_name, rating, text, review_id),
        )
        row = connection.execute('SELECT * FROM reviews WHERE id = ?', (review_id,)).fetchone()
    return _row_to_dict(row)


def delete_review(review_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
    return cursor.rowcount > 0


def can_user_review_work(work_id: int, user: UserIdentity) -> bool:
    if user.is_admin:
        return True
    work = get_work(work_id)
    if not work:
        return False
    allowed = _normalize_username(work.get('allowed_reviewer_username'))
    if not allowed:
        return True
    return _normalize_username(user.username) == allowed


def add_work_review(work_id: int, *, user: UserIdentity, author_name: str, rating: int, text: str) -> dict[str, Any]:
    if not can_user_review_work(work_id, user):
        raise ValueError('Оставить отзыв на эту работу может только пользователь, которого назначил владелец.')

    with get_connection() as connection:
        work_exists = connection.execute('SELECT 1 FROM works WHERE id = ?', (work_id,)).fetchone()
        if not work_exists:
            raise ValueError('Работа не найдена.')

        existing = connection.execute(
            'SELECT id FROM work_reviews WHERE work_id = ? AND author_user_id = ?',
            (work_id, user.user_id),
        ).fetchone()
        if existing:
            connection.execute(
                '''
                UPDATE work_reviews
                SET author_name = ?, author_username = ?, rating = ?, text = ?, created_at = ?
                WHERE id = ?
                ''',
                (author_name, _normalize_username(user.username), rating, text, now_iso(), existing['id']),
            )
            row = connection.execute('SELECT * FROM work_reviews WHERE id = ?', (existing['id'],)).fetchone()
        else:
            cursor = connection.execute(
                '''
                INSERT INTO work_reviews (
                    work_id, author_name, author_username, rating, text, author_user_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (work_id, author_name, _normalize_username(user.username), rating, text, user.user_id, now_iso()),
            )
            row = connection.execute('SELECT * FROM work_reviews WHERE id = ?', (cursor.lastrowid,)).fetchone()
    return _row_to_dict(row) or {}


def update_work_review(review_id: int, author_name: str, rating: int, text: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        connection.execute(
            'UPDATE work_reviews SET author_name = ?, rating = ?, text = ? WHERE id = ?',
            (author_name, rating, text, review_id),
        )
        row = connection.execute('SELECT * FROM work_reviews WHERE id = ?', (review_id,)).fetchone()
    return _row_to_dict(row)


def delete_work_review(review_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute('DELETE FROM work_reviews WHERE id = ?', (review_id,))
    return cursor.rowcount > 0


def get_dashboard_metrics() -> dict[str, Any]:
    with get_connection() as connection:
        works_count = connection.execute('SELECT COUNT(*) FROM works').fetchone()[0]
        global_reviews = connection.execute('SELECT COUNT(*), COALESCE(AVG(rating), 0) FROM reviews').fetchone()
        work_reviews = connection.execute('SELECT COUNT(*), COALESCE(AVG(rating), 0) FROM work_reviews').fetchone()
        bookings_count = connection.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]
        confirmed_count = connection.execute("SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'").fetchone()[0]

    total_review_count = int(global_reviews[0]) + int(work_reviews[0])
    rating_sum = float(global_reviews[1]) * int(global_reviews[0]) + float(work_reviews[1]) * int(work_reviews[0])
    average = round(rating_sum / total_review_count, 1) if total_review_count else 0
    return {
        'works_count': works_count,
        'reviews_count': total_review_count,
        'average_rating': average,
        'bookings_count': bookings_count,
        'confirmed_count': confirmed_count,
    }


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
        day_record['slots'].append({'time': row['slot_time'], 'status': status})
        if status == 'available':
            day_record['available_count'] += 1
        else:
            day_record['busy_count'] += 1

    for day_record in days.values():
        day_record['status'] = 'available' if day_record['available_count'] > 0 else 'busy'

    return {
        'year': year,
        'month': month,
        'days': [
            days.get(
                date(year, month, day).isoformat(),
                {
                    'date': date(year, month, day).isoformat(),
                    'slots': [],
                    'available_count': 0,
                    'busy_count': 0,
                    'status': 'busy',
                },
            )
            for day in range(1, days_in_month + 1)
        ],
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
    return [set_slot_status(slot_date, slot_time, status) for slot_time in settings.default_times]


def create_booking(
    *,
    user: UserIdentity,
    full_name: str,
    age: int,
    service_location: str,
    tattoo_description: str,
    body_place: str,
    size_cm: str,
    style_choice: str,
    color_mode: str,
    estimated_price_from: int,
    estimated_price_to: int,
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

        connection.execute('UPDATE availability SET status = ? WHERE slot_date = ? AND slot_time = ?', ('busy', slot_date, slot_time))
        telegram_name = ' '.join(part for part in [user.first_name, user.last_name or ''] if part).strip()
        cursor = connection.execute(
            '''
            INSERT INTO bookings (
                user_id, username, telegram_name, full_name, age, service_location,
                tattoo_description, body_place, size_cm, style_choice, color_mode,
                estimated_price_from, estimated_price_to, slot_date, slot_time,
                status, reference_image_path, created_at, admin_message_id, admin_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, NULL, NULL)
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
                style_choice,
                color_mode,
                estimated_price_from,
                estimated_price_to,
                slot_date,
                slot_time,
                reference_image_path,
                now_iso(),
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

        connection.execute(
            'UPDATE bookings SET status = ?, admin_note = ? WHERE id = ?',
            (status, admin_note, booking_id),
        )
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
        connection.execute('COMMIT')
        row = connection.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    return _row_to_dict(row)


def list_bookings(limit: int = 100) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            '''
            SELECT *
            FROM bookings
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            ''',
            (limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]
