from __future__ import annotations

import html
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

import requests

from app import database
from app.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

SERVICE_LOCATION_LABELS = {
    'studio': 'У мастера',
    'client_home': 'У клиента дома',
}

STYLE_LABELS = {
    'linework': 'Linework',
    'graphic': 'Graphic',
    'blackwork': 'Blackwork',
    'ornamental': 'Ornamental',
    'custom': 'Custom',
}

COLOR_LABELS = {
    'blackwork': 'Ч/Б',
    'mixed': 'С цветом',
}


class TelegramBotService:
    def __init__(self) -> None:
        self.token = settings.bot_token
        self.api_base = f'https://api.telegram.org/bot{self.token}'
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.session = requests.Session()
        self.offset: int = 0

    def start(self) -> None:
        if self.token == 'CHANGE_ME':
            logger.warning('BOT_TOKEN не задан. Бот не запущен.')
            return
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, daemon=True, name='telegram-bot-poller')
        self.thread.start()
        logger.info('Telegram bot polling started.')

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        self.session.close()

    def _call(
        self,
        method: str,
        *,
        payload: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        url = f'{self.api_base}/{method}'
        if files:
            response = self.session.post(url, data=payload or {}, files=files, timeout=timeout)
        else:
            response = self.session.post(url, json=payload or {}, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if not data.get('ok'):
            raise RuntimeError(f'Telegram API error for {method}: {data}')
        return data

    def _normalized_username(self, value: str | None) -> str:
        return (value or '').strip().lstrip('@').lower()

    def _is_admin_actor(self, actor: dict[str, Any]) -> bool:
        if not actor:
            return False
        if settings.admin_telegram_id and int(actor.get('id') or 0) == settings.admin_telegram_id:
            return True
        if settings.normalized_admin_username and self._normalized_username(actor.get('username')) == settings.normalized_admin_username:
            return True
        return False

    def _resolve_admin_chat_id(self) -> int | None:
        if settings.admin_chat_id:
            return int(settings.admin_chat_id)
        if settings.admin_telegram_id:
            return int(settings.admin_telegram_id)
        stored = database.get_admin_chat_id()
        if stored:
            return int(stored)
        return None

    def _web_app_button(self, text: str = 'Открыть приложение') -> dict[str, Any]:
        return {'text': text, 'web_app': {'url': settings.effective_public_base_url}}

    def configure_bot(self) -> None:
        try:
            self._call('deleteWebhook', payload={'drop_pending_updates': False})
        except Exception:
            logger.exception('Не удалось удалить webhook.')

        try:
            self._call(
                'setMyCommands',
                payload={
                    'commands': [
                        {'command': 'start', 'description': 'Открыть мини-приложение'},
                    ]
                },
            )
        except Exception:
            logger.exception('Не удалось задать команды бота.')

        if settings.resolved_public_base_url:
            try:
                self._call(
                    'setChatMenuButton',
                    payload={
                        'menu_button': {
                            'type': 'web_app',
                            'text': 'Danya Tattoo',
                            'web_app': {'url': settings.effective_public_base_url},
                        }
                    },
                )
            except Exception:
                logger.exception('Не удалось настроить menu button.')

        try:
            data = self._call('getUpdates', payload={'timeout': 0, 'allowed_updates': ['message', 'callback_query']})
            results = data.get('result', [])
            if results:
                self.offset = results[-1]['update_id'] + 1
        except Exception:
            logger.exception('Не удалось прочитать текущие updates.')

    def _run(self) -> None:
        self.configure_bot()
        while not self.stop_event.is_set():
            try:
                data = self._call(
                    'getUpdates',
                    payload={
                        'offset': self.offset,
                        'timeout': settings.polling_timeout_seconds,
                        'allowed_updates': ['message', 'callback_query'],
                    },
                    timeout=settings.polling_timeout_seconds + 10,
                )
                for update in data.get('result', []):
                    self.offset = update['update_id'] + 1
                    self._handle_update(update)
            except requests.RequestException:
                logger.exception('Ошибка сети при long polling Telegram.')
                time.sleep(3)
            except Exception:
                logger.exception('Ошибка обработки update Telegram.')
                time.sleep(1)

    def _handle_update(self, update: dict[str, Any]) -> None:
        if 'message' in update:
            self._handle_message(update['message'])
        elif 'callback_query' in update:
            self._handle_callback(update['callback_query'])

    def _handle_message(self, message: dict[str, Any]) -> None:
        chat = message.get('chat', {})
        from_user = message.get('from', {})
        text = (message.get('text') or '').strip()
        if chat.get('type') != 'private':
            return

        if self._is_admin_actor(from_user):
            try:
                database.set_admin_chat_id(int(chat['id']))
            except Exception:
                logger.exception('Не удалось привязать чат владельца.')

        if text.startswith('/start'):
            self.send_welcome(chat_id=chat['id'], is_admin=self._is_admin_actor(from_user))
            return
        self.send_welcome(chat_id=chat['id'], short=True, is_admin=self._is_admin_actor(from_user))

    def _handle_callback(self, callback_query: dict[str, Any]) -> None:
        callback_id = callback_query['id']
        from_user = callback_query.get('from', {})
        data = callback_query.get('data', '')
        message = callback_query.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        message_id = message.get('message_id')

        if not self._is_admin_actor(from_user):
            self.answer_callback_query(callback_id, 'Только владелец может подтверждать заявки.')
            return

        try:
            action, booking_id = self._parse_callback_data(data)
        except ValueError:
            self.answer_callback_query(callback_id, 'Неизвестное действие.')
            return

        booking = database.get_booking(booking_id)
        if not booking:
            self.answer_callback_query(callback_id, 'Заявка уже не найдена.')
            return

        if action == 'approve':
            updated = database.update_booking_status(booking_id, 'confirmed', 'Подтверждено владельцем')
            self.answer_callback_query(callback_id, 'Заявка подтверждена.')
            self.notify_user_about_status(updated, approved=True)
            new_text = self._admin_message_text(updated, approved=True)
        else:
            updated = database.update_booking_status(booking_id, 'rejected', 'Отклонено владельцем')
            self.answer_callback_query(callback_id, 'Заявка отклонена.')
            self.notify_user_about_status(updated, approved=False)
            new_text = self._admin_message_text(updated, approved=False)

        if not chat_id or not message_id:
            return

        try:
            if message.get('photo'):
                self._call(
                    'editMessageCaption',
                    payload={
                        'chat_id': chat_id,
                        'message_id': message_id,
                        'caption': new_text,
                        'parse_mode': 'HTML',
                        'reply_markup': {'inline_keyboard': []},
                    },
                )
            else:
                self._call(
                    'editMessageText',
                    payload={
                        'chat_id': chat_id,
                        'message_id': message_id,
                        'text': new_text,
                        'parse_mode': 'HTML',
                        'reply_markup': {'inline_keyboard': []},
                    },
                )
        except Exception:
            logger.exception('Не удалось обновить сообщение администратора по заявке #%s.', booking_id)

    def _parse_callback_data(self, data: str) -> tuple[str, int]:
        parts = data.split(':')
        if len(parts) != 3 or parts[0] != 'booking':
            raise ValueError('bad callback')
        return parts[1], int(parts[2])

    def answer_callback_query(self, callback_query_id: str, text: str) -> None:
        try:
            self._call('answerCallbackQuery', payload={'callback_query_id': callback_query_id, 'text': text, 'show_alert': False})
        except Exception:
            logger.exception('Не удалось ответить на callback_query.')

    def send_welcome(self, chat_id: int, short: bool = False, is_admin: bool = False) -> None:
        text = (
            'Привет! Открывай мини-приложение через кнопку меню бота: внутри работы, отзывы, запись и карта.'
            if short
            else (
                'Привет! Это <b>Danya-Tattoo-Voronezh</b>\n\n'
                'Что внутри:\n'
                '• галерея работ с отзывами;\n'
                '• красивый календарь свободных дат;\n'
                '• предварительный расчёт цены;\n'
                '• запись прямо из Telegram Mini App.\n\n'
                f'Предоплата фиксированная: <b>{settings.prepayment_amount_rub} ₽</b>.\n\n'
                'Открывай мини-приложение через кнопку меню бота.'
            )
        )
        if is_admin:
            text += '\n\n🔐 Этот чат привязан как чат владельца. Сюда будут приходить заявки.'


        self._call(
            'sendMessage',
            payload={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            },
        )

    def _booking_reply_markup(self, booking_id: int) -> dict[str, Any]:
        return {
            'inline_keyboard': [
                [
                    {'text': '✅ Подтвердить', 'callback_data': f'booking:approve:{booking_id}'},
                    {'text': '❌ Отклонить', 'callback_data': f'booking:reject:{booking_id}'},
                ]
            ]
        }

    def _booking_caption(self, booking: dict[str, Any]) -> str:
        username = f"@{booking['username']}" if booking.get('username') else 'без username'
        service_label = SERVICE_LOCATION_LABELS.get(booking['service_location'], booking['service_location'])
        style_label = STYLE_LABELS.get(booking.get('style_choice') or '', 'Custom')
        color_label = COLOR_LABELS.get(booking.get('color_mode') or 'blackwork', 'Ч/Б')
        description = html.escape(booking['tattoo_description'])
        if len(description) > 260:
            description = description[:257] + '...'
        estimate = f"{booking.get('estimated_price_from', 0)}–{booking.get('estimated_price_to', 0)} ₽"
        lines = [
            f"🆕 <b>Новая заявка #{booking['id']}</b>",
            f"👤 Telegram: {html.escape(booking['telegram_name'])} ({username})",
            f"📛 Имя в анкете: {html.escape(booking['full_name'])}",
            f"🎂 Возраст: {booking['age']}",
            f"📅 Дата: <b>{booking['slot_date']}</b>",
            f"🕛 Время: <b>{booking['slot_time']}</b> (МСК)",
            f"📍 Где бить: {service_label}",
            f"🧍 Место на теле: {html.escape(booking['body_place'])}",
            f"📏 Размер: {html.escape(booking['size_cm'])}",
            f"🎨 Стиль: {style_label} / {color_label}",
            f"💰 Предварительно: <b>{estimate}</b>",
            f"💳 Предоплата: <b>{settings.prepayment_amount_rub} ₽</b>",
            f"📝 Описание: {description}",
        ]
        return '\n'.join(lines)

    def _admin_message_text(self, booking: dict[str, Any], approved: bool) -> str:
        status_text = '✅ <b>Заявка подтверждена</b>' if approved else '❌ <b>Заявка отклонена</b>'
        return self._booking_caption(booking) + f'\n\n{status_text}'

    def notify_admin_about_booking(self, booking: dict[str, Any]) -> bool:
        admin_chat_id = self._resolve_admin_chat_id()
        if not admin_chat_id:
            logger.warning('Чат владельца ещё не привязан. Владелец должен один раз написать /start боту.')
            return False

        caption = self._booking_caption(booking)
        reply_markup = self._booking_reply_markup(int(booking['id']))
        result: dict[str, Any]
        reference_image_path = booking.get('reference_image_path')
        if reference_image_path:
            absolute_path = Path(reference_image_path)
            if absolute_path.exists():
                with absolute_path.open('rb') as photo_file:
                    result = self._call(
                        'sendPhoto',
                        payload={
                            'chat_id': admin_chat_id,
                            'caption': caption,
                            'parse_mode': 'HTML',
                            'reply_markup': json.dumps(reply_markup, ensure_ascii=False),
                        },
                        files={'photo': photo_file},
                    )
            else:
                result = self._call(
                    'sendMessage',
                    payload={
                        'chat_id': admin_chat_id,
                        'text': caption + '\n\n⚠️ Референс-файл не найден на сервере.',
                        'parse_mode': 'HTML',
                        'reply_markup': reply_markup,
                    },
                )
        else:
            result = self._call(
                'sendMessage',
                payload={
                    'chat_id': admin_chat_id,
                    'text': caption,
                    'parse_mode': 'HTML',
                    'reply_markup': reply_markup,
                },
            )

        message_id = result.get('result', {}).get('message_id')
        if message_id:
            database.set_booking_admin_message(int(booking['id']), int(message_id))
        return True

    def notify_user_about_created(self, booking: dict[str, Any]) -> None:
        estimate = f"{booking.get('estimated_price_from', 0)}–{booking.get('estimated_price_to', 0)} ₽"
        text = (
            f"🖤 Заявка принята в обработку.\n\n"
            f"Дата: {booking['slot_date']}\n"
            f"Время: {booking['slot_time']} (МСК)\n"
            f"Предварительная цена: {estimate}\n"
            f"Предоплата после подтверждения: {settings.prepayment_amount_rub} ₽\n\n"
            f"Как только владелец подтвердит запись, ты получишь уведомление здесь."
        )
        try:
            self._call(
                'sendMessage',
                payload={
                    'chat_id': int(booking['user_id']),
                    'text': text,
                },
            )
        except Exception:
            logger.exception('Не удалось уведомить пользователя о создании заявки.')

    def notify_user_about_status(self, booking: dict[str, Any] | None, approved: bool) -> None:
        if not booking:
            return
        estimate = f"{booking.get('estimated_price_from', 0)}–{booking.get('estimated_price_to', 0)} ₽"
        text = (
            f"✅ Ваша заявка на {booking['slot_date']} в {booking['slot_time']} подтверждена. "
            f"Предварительная цена: {estimate}. Мастер свяжется с вами в Telegram. "
            f"Фиксированная предоплата — {settings.prepayment_amount_rub} ₽."
            if approved
            else f"❌ Заявка на {booking['slot_date']} в {booking['slot_time']} была отклонена. Выберите другой слот в приложении."
        )
        try:
            self._call(
                'sendMessage',
                payload={
                    'chat_id': int(booking['user_id']),
                    'text': text,
                },
            )
        except Exception:
            logger.exception('Не удалось уведомить пользователя %s о статусе заявки.', booking.get('user_id'))


bot_service = TelegramBotService()
