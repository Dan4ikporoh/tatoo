from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import asdict
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException, Request, status

from app.database import UserIdentity
from app.settings import get_settings

settings = get_settings()


class AuthError(Exception):
    pass


def _normalized_username(value: str | None) -> str:
    return (value or '').strip().lstrip('@').lower()


def _is_admin_identity(user_id: int | None, username: str | None) -> bool:
    if user_id and settings.admin_telegram_id and int(user_id) == settings.admin_telegram_id:
        return True
    if settings.normalized_admin_username and _normalized_username(username) == settings.normalized_admin_username:
        return True
    return False


def _dev_user() -> UserIdentity:
    return UserIdentity(
        user_id=settings.dev_user_id,
        first_name=settings.dev_first_name,
        last_name=settings.dev_last_name,
        username=settings.dev_username,
        is_admin=settings.dev_is_admin,
    )


def parse_init_data(init_data: str) -> dict[str, str]:
    return dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))


def validate_init_data(init_data: str) -> UserIdentity:
    if not init_data:
        raise AuthError('Пустые данные авторизации Telegram.')

    parsed = parse_init_data(init_data)
    received_hash = parsed.pop('hash', None)
    if not received_hash:
        raise AuthError('Не найден hash Telegram Mini App.')

    data_check_string = '\n'.join(f'{key}={value}' for key, value in sorted(parsed.items()))
    secret_key = hmac.new(b'WebAppData', settings.bot_token.encode('utf-8'), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise AuthError('Подпись Telegram Mini App не совпадает.')

    auth_date = int(parsed.get('auth_date', '0') or 0)
    if auth_date and settings.auth_max_age_seconds > 0:
        current_time = int(time.time())
        if current_time - auth_date > settings.auth_max_age_seconds:
            raise AuthError('Данные авторизации устарели, открой приложение заново.')

    user_raw = parsed.get('user')
    if not user_raw:
        raise AuthError('В initData отсутствует пользователь. Открывайте приложение через menu button или inline web_app кнопку.')

    try:
        user_data = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise AuthError('Не удалось разобрать пользователя Telegram.') from exc

    user_id = int(user_data['id'])
    username = user_data.get('username')
    return UserIdentity(
        user_id=user_id,
        first_name=user_data.get('first_name') or 'Пользователь',
        last_name=user_data.get('last_name'),
        username=username,
        is_admin=_is_admin_identity(user_id, username),
    )


async def get_current_user(
    request: Request,
    x_telegram_init_data: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> UserIdentity:
    init_data = x_telegram_init_data or request.query_params.get('tgInitData')

    if not init_data and authorization and authorization.lower().startswith('tma '):
        init_data = authorization[4:]

    if not init_data:
        if settings.allow_dev_auth:
            return _dev_user()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Нужна авторизация через Telegram Mini App.',
        )

    try:
        user = validate_init_data(init_data)
    except AuthError as exc:
        if settings.allow_dev_auth:
            return _dev_user()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    request.state.current_user = asdict(user)
    return user


async def get_admin_user(user: UserIdentity = None):
    # FastAPI injects dependency positionally when used with Depends.
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Нет доступа.')
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Только владелец может менять эти данные.')
    return user
