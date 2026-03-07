from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / '.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    app_name: str = 'Danya-Tattoo-Voronezh'
    business_name: str = 'Danya Tattoo'
    hero_title: str = 'Татуировки в Воронеже'
    hero_subtitle: str = 'Стильный Telegram Mini App: галерея, запись, отзывы и управление работами'

    bot_token: str = 'CHANGE_ME'
    bot_username: str = ''
    admin_telegram_id: int = 0
    admin_chat_id: int = 0
    admin_username: str = ''
    public_base_url: str = ''

    city: str = 'Воронеж'
    address: str = 'Воронеж, Московский проспект, 15'
    timezone_name: str = 'Europe/Moscow'

    telegram_link: str = 'https://t.me/your_username'
    vk_link: str = 'https://vk.com/your_username'

    yandex_widget_url: str = ''
    map_embed_title: str = 'Карта студии'

    default_slot_times: str = '10:00,12:00,14:00,16:00,18:00'
    auth_max_age_seconds: int = 60 * 60 * 24
    prepayment_amount_rub: int = 500

    allow_dev_auth: bool = False
    dev_user_id: int = 100000001
    dev_first_name: str = 'Dev'
    dev_last_name: str = 'User'
    dev_username: str = 'dev_user'
    dev_is_admin: bool = True

    polling_timeout_seconds: int = 25
    booking_caption_limit: int = 900

    persistent_root: str = ''

    @property
    def effective_public_base_url(self) -> str:
        explicit = (self.public_base_url or '').strip().rstrip('/')
        if explicit and explicit not in {'https://example.com', 'https://your-domain.example'}:
            return explicit

        render_url = os.getenv('RENDER_EXTERNAL_URL', '').strip().rstrip('/')
        if render_url:
            return render_url

        render_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
        if render_hostname:
            return f'https://{render_hostname}'.rstrip('/')

        return 'http://localhost:8000'

    @property
    def persistence_dir(self) -> Path:
        custom_root = (self.persistent_root or '').strip()
        if custom_root:
            return Path(custom_root)
        return BASE_DIR / 'app' / 'data'

    @property
    def db_path(self) -> Path:
        return self.persistence_dir / 'app.db'

    @property
    def uploads_dir(self) -> Path:
        return self.persistence_dir / 'uploads'

    @property
    def booking_uploads_dir(self) -> Path:
        return self.uploads_dir / 'booking_refs'

    @property
    def public_works_dir(self) -> Path:
        return self.uploads_dir / 'works'

    @property
    def works_dir(self) -> Path:
        return BASE_DIR / 'app' / 'static' / 'assets' / 'works'

    @property
    def logo_path(self) -> Path:
        return BASE_DIR / 'app' / 'static' / 'assets' / 'logo' / 'danya-tattoo-logo.jpeg'

    @property
    def default_times(self) -> list[str]:
        return [item.strip() for item in self.default_slot_times.split(',') if item.strip()]

    @property
    def resolved_public_base_url(self) -> str:
        return self.effective_public_base_url

    @property
    def normalized_admin_username(self) -> str:
        return self.admin_username.strip().lstrip('@').lower()

    @property
    def yandex_map_link(self) -> str:
        return f'https://yandex.ru/maps/?text={quote(self.address)}'

    @property
    def yandex_app_link(self) -> str:
        return f'yandexmaps://maps.yandex.ru/?text={quote(self.address)}'

    @property
    def resolved_yandex_widget_url(self) -> str:
        explicit = (self.yandex_widget_url or '').strip()
        if explicit:
            return explicit
        return f'https://yandex.ru/map-widget/v1/?text={quote(self.address)}'


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.persistence_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.booking_uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.public_works_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
