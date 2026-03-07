from __future__ import annotations

import logging
import math
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import database
from app.auth import get_current_user
from app.database import UserIdentity
from app.settings import BASE_DIR, get_settings
from app.telegram_bot import bot_service

settings = get_settings()
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger(__name__)


class ReviewCreatePayload(BaseModel):
    author_name: str = Field(min_length=2, max_length=60)
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=5, max_length=1000)


class ReviewUpdatePayload(ReviewCreatePayload):
    pass


class WorkUpdatePayload(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, min_length=5, max_length=1000)
    allowed_reviewer_username: str | None = Field(default=None, max_length=64)


class SlotStatusPayload(BaseModel):
    slot_date: str
    slot_time: str
    status: str = Field(pattern='^(available|busy)$')


class DayStatusPayload(BaseModel):
    slot_date: str
    status: str = Field(pattern='^(available|busy)$')


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.init_db()
    bot_service.start()
    yield
    bot_service.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'app' / 'static')), name='static')
app.mount('/uploaded-works', StaticFiles(directory=str(settings.public_works_dir)), name='uploaded-works')


def ensure_admin(user: UserIdentity) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Доступ только для владельца.')


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={'detail': str(exc)})


@app.get('/api/health')
def healthcheck() -> dict[str, str]:
    return {'status': 'ok'}


def _normalize_username(value: str | None) -> str:
    return (value or '').strip().lstrip('@').lower()


ALLOWED_IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


def save_upload(file: UploadFile, target_dir: Path) -> str:
    safe_suffix = Path(file.filename or '').suffix.lower() or '.jpg'
    if safe_suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise HTTPException(status_code=400, detail='Разрешены только JPG, PNG и WEBP.')
    unique_name = f'{uuid.uuid4().hex}{safe_suffix}'
    destination = target_dir / unique_name
    with destination.open('wb') as buffer:
        shutil.copyfileobj(file.file, buffer)
    return unique_name


STYLE_MULTIPLIERS = {
    'linework': 1.0,
    'graphic': 1.12,
    'blackwork': 1.18,
    'ornamental': 1.15,
    'custom': 1.25,
}

COLOR_MULTIPLIERS = {
    'blackwork': 1.0,
    'mixed': 1.22,
}

SERVICE_MULTIPLIERS = {
    'studio': 1.0,
    'client_home': 1.18,
}


def round_to_500(value: float) -> int:
    return int(math.ceil(value / 500.0) * 500)



def estimate_price(size_cm: str, style_choice: str, color_mode: str, service_location: str) -> tuple[int, int]:
    numbers = [float(item.replace(',', '.')) for item in __import__('re').findall(r'\d+(?:[\.,]\d+)?', size_cm)]
    if len(numbers) >= 2:
        area = numbers[0] * numbers[1]
    elif len(numbers) == 1:
        area = numbers[0] * numbers[0] * 0.7
    else:
        area = 36

    base = 2200 + area * 45
    base *= STYLE_MULTIPLIERS.get(style_choice, 1.1)
    base *= COLOR_MULTIPLIERS.get(color_mode, 1.0)
    base *= SERVICE_MULTIPLIERS.get(service_location, 1.0)

    estimate_from = round_to_500(max(2500, base * 0.9))
    estimate_to = round_to_500(max(estimate_from + 500, base * 1.2))
    return estimate_from, estimate_to


@app.get('/api/bootstrap')
def bootstrap(user: UserIdentity = Depends(get_current_user)) -> dict:
    metrics = database.get_dashboard_metrics()
    works = database.get_works()
    return {
        'app': {
            'name': settings.app_name,
            'businessName': settings.business_name,
            'heroTitle': settings.hero_title,
            'heroSubtitle': settings.hero_subtitle,
            'address': settings.address,
            'city': settings.city,
            'telegramLink': settings.telegram_link,
            'vkLink': settings.vk_link,
            'logoUrl': '/static/assets/logo/danya-tattoo-logo.jpeg',
            'mapEmbedUrl': settings.resolved_yandex_widget_url,
            'mapEmbedTitle': settings.map_embed_title,
            'yandexMapLink': settings.yandex_map_link,
            'yandexAppLink': settings.yandex_app_link,
            'prepaymentAmountRub': settings.prepayment_amount_rub,
            'publicBaseUrl': settings.resolved_public_base_url,
        },
        'user': {
            'id': user.user_id,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'username': user.username,
            'isAdmin': user.is_admin,
        },
        'metrics': metrics,
        'featuredWorks': works[:3],
    }


@app.get('/api/works')
def works(user: UserIdentity = Depends(get_current_user)) -> dict:
    items = database.get_works()
    for item in items:
        item['can_review'] = database.can_user_review_work(int(item['id']), user)
        item['assigned_review_username'] = item.get('allowed_reviewer_username')
    return {'items': items, 'viewer': {'isAdmin': user.is_admin, 'username': user.username}}


@app.post('/api/admin/works')
async def create_work(
    title: str = Form(...),
    description: str = Form(...),
    allowed_reviewer_username: str = Form(default=''),
    image: UploadFile = File(...),
    user: UserIdentity = Depends(get_current_user),
) -> dict:
    ensure_admin(user)
    filename = save_upload(image, settings.public_works_dir)
    item = database.add_work(
        title=title.strip(),
        description=description.strip(),
        image_path=f'/uploaded-works/{filename}',
        allowed_reviewer_username=_normalize_username(allowed_reviewer_username),
    )
    return {'item': item, 'message': 'Работа добавлена в галерею.'}


@app.patch('/api/admin/works/{work_id}')
def update_work(work_id: int, payload: WorkUpdatePayload, user: UserIdentity = Depends(get_current_user)) -> dict:
    ensure_admin(user)
    item = database.update_work(
        work_id,
        title=payload.title,
        description=payload.description,
        allowed_reviewer_username=payload.allowed_reviewer_username,
    )
    if not item:
        raise HTTPException(status_code=404, detail='Работа не найдена.')
    return {'item': item, 'message': 'Работа обновлена.'}


@app.delete('/api/admin/works/{work_id}')
def delete_work(work_id: int, user: UserIdentity = Depends(get_current_user)) -> dict:
    ensure_admin(user)
    item = database.delete_work(work_id)
    if not item:
        raise HTTPException(status_code=404, detail='Работа не найдена.')
    return {'ok': True}


@app.get('/api/reviews')
def reviews(user: UserIdentity = Depends(get_current_user)) -> dict:
    return {'items': database.get_reviews(), 'viewer': {'isAdmin': user.is_admin}}


@app.post('/api/reviews')
def create_review(payload: ReviewCreatePayload, user: UserIdentity = Depends(get_current_user)) -> dict:
    review = database.add_review(
        author_name=payload.author_name.strip(),
        rating=payload.rating,
        text=payload.text.strip(),
        author_user_id=user.user_id,
    )
    return {'item': review, 'message': 'Общий отзыв опубликован.'}


@app.post('/api/works/{work_id}/reviews')
def create_work_review(work_id: int, payload: ReviewCreatePayload, user: UserIdentity = Depends(get_current_user)) -> dict:
    review = database.add_work_review(
        work_id,
        user=user,
        author_name=payload.author_name.strip(),
        rating=payload.rating,
        text=payload.text.strip(),
    )
    return {'item': review, 'message': 'Отзыв к работе опубликован.'}


@app.patch('/api/admin/reviews/{review_id}')
def update_review(review_id: int, payload: ReviewUpdatePayload, user: UserIdentity = Depends(get_current_user)) -> dict:
    ensure_admin(user)
    review = database.update_review(review_id, payload.author_name.strip(), payload.rating, payload.text.strip())
    if not review:
        raise HTTPException(status_code=404, detail='Отзыв не найден.')
    return {'item': review, 'message': 'Отзыв обновлён.'}


@app.delete('/api/admin/reviews/{review_id}')
def remove_review(review_id: int, user: UserIdentity = Depends(get_current_user)) -> dict:
    ensure_admin(user)
    deleted = database.delete_review(review_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='Отзыв не найден.')
    return {'ok': True}


@app.patch('/api/admin/work-reviews/{review_id}')
def update_work_review(review_id: int, payload: ReviewUpdatePayload, user: UserIdentity = Depends(get_current_user)) -> dict:
    ensure_admin(user)
    review = database.update_work_review(review_id, payload.author_name.strip(), payload.rating, payload.text.strip())
    if not review:
        raise HTTPException(status_code=404, detail='Отзыв к работе не найден.')
    return {'item': review, 'message': 'Отзыв к работе обновлён.'}


@app.delete('/api/admin/work-reviews/{review_id}')
def remove_work_review(review_id: int, user: UserIdentity = Depends(get_current_user)) -> dict:
    ensure_admin(user)
    deleted = database.delete_work_review(review_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='Отзыв к работе не найден.')
    return {'ok': True}


@app.get('/api/availability')
def availability(
    month: str | None = Query(default=None, description='YYYY-MM'),
    user: UserIdentity = Depends(get_current_user),
) -> dict:
    del user
    if month:
        try:
            year, month_num = [int(part) for part in month.split('-')]
        except Exception as exc:
            raise HTTPException(status_code=400, detail='Неверный формат month. Нужен YYYY-MM.') from exc
    else:
        now_local = datetime.now(ZoneInfo(settings.timezone_name))
        year, month_num = now_local.year, now_local.month

    return database.get_month_availability(year, month_num)


@app.get('/api/availability/day/{slot_date}')
def availability_day(slot_date: str, user: UserIdentity = Depends(get_current_user)) -> dict:
    del user
    return {'date': slot_date, 'slots': database.get_slots_for_date(slot_date)}


@app.post('/api/admin/availability/slot')
def admin_set_slot(payload: SlotStatusPayload, user: UserIdentity = Depends(get_current_user)) -> dict:
    ensure_admin(user)
    item = database.set_slot_status(payload.slot_date, payload.slot_time, payload.status)
    return {'item': item}


@app.post('/api/admin/availability/day')
def admin_set_day(payload: DayStatusPayload, user: UserIdentity = Depends(get_current_user)) -> dict:
    ensure_admin(user)
    items = database.set_day_status(payload.slot_date, payload.status)
    return {'items': items}


@app.get('/api/admin/bookings')
def admin_bookings(user: UserIdentity = Depends(get_current_user)) -> dict:
    ensure_admin(user)
    return {'items': database.list_bookings(limit=200)}


@app.get('/api/price-estimate')
def price_estimate(
    size_cm: str,
    style_choice: str = 'custom',
    color_mode: str = 'blackwork',
    service_location: str = 'studio',
    user: UserIdentity = Depends(get_current_user),
) -> dict:
    del user
    estimate_from, estimate_to = estimate_price(size_cm, style_choice, color_mode, service_location)
    return {'estimateFrom': estimate_from, 'estimateTo': estimate_to}


@app.post('/api/bookings')
async def create_booking(
    full_name: str = Form(...),
    age: int = Form(...),
    service_location: str = Form(...),
    tattoo_description: str = Form(...),
    body_place: str = Form(...),
    size_cm: str = Form(...),
    style_choice: str = Form(default='custom'),
    color_mode: str = Form(default='blackwork'),
    slot_date: str = Form(...),
    slot_time: str = Form(...),
    prepayment_ack: str = Form(...),
    reference_photo: UploadFile | None = File(default=None),
    user: UserIdentity = Depends(get_current_user),
) -> dict:
    if service_location not in {'studio', 'client_home'}:
        raise HTTPException(status_code=400, detail='Некорректное место проведения сеанса.')
    if color_mode not in {'blackwork', 'mixed'}:
        raise HTTPException(status_code=400, detail='Некорректный режим цвета.')
    if not (0 < age < 120):
        raise HTTPException(status_code=400, detail='Возраст должен быть указан корректно.')
    if str(prepayment_ack).strip().lower() not in {'on', 'true', '1', 'yes'}:
        raise HTTPException(
            status_code=400,
            detail=f'Нужно подтвердить, что фиксированная предоплата {settings.prepayment_amount_rub} ₽ понятна.',
        )

    now_local = datetime.now(ZoneInfo(settings.timezone_name)).date().isoformat()
    if slot_date < now_local:
        raise HTTPException(status_code=400, detail='Нельзя записаться на прошедшую дату.')

    reference_path: str | None = None
    if reference_photo and reference_photo.filename:
        filename = save_upload(reference_photo, settings.booking_uploads_dir)
        reference_path = str(settings.booking_uploads_dir / filename)

    estimate_from, estimate_to = estimate_price(size_cm.strip(), style_choice, color_mode, service_location)
    booking = database.create_booking(
        user=user,
        full_name=full_name.strip(),
        age=age,
        service_location=service_location,
        tattoo_description=tattoo_description.strip(),
        body_place=body_place.strip(),
        size_cm=size_cm.strip(),
        style_choice=style_choice.strip(),
        color_mode=color_mode.strip(),
        estimated_price_from=estimate_from,
        estimated_price_to=estimate_to,
        slot_date=slot_date,
        slot_time=slot_time,
        reference_image_path=reference_path,
    )

    delivered = False
    delivery_error = None
    try:
        if settings.bot_token != 'CHANGE_ME':
            bot_service.notify_user_about_created(booking)
            delivered = bot_service.notify_admin_about_booking(booking)
            if not delivered:
                delivery_error = 'Чат владельца ещё не привязан к боту.'
    except Exception as exc:
        logger.exception('Не удалось отправить заявку владельцу в Telegram.')
        delivery_error = str(exc)

    return {
        'item': booking,
        'telegramDelivered': delivered,
        'deliveryError': delivery_error,
        'estimateFrom': estimate_from,
        'estimateTo': estimate_to,
        'message': (
            f'Заявка отправлена. Предварительная цена: {estimate_from}–{estimate_to} ₽. '
            f'После подтверждения нужно будет внести предоплату {settings.prepayment_amount_rub} ₽.'
        ),
    }


@app.get('/')
def index() -> FileResponse:
    return FileResponse(BASE_DIR / 'app' / 'static' / 'index.html')
