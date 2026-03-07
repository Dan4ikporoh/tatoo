from __future__ import annotations

import logging
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


def ensure_admin(user: UserIdentity) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Доступ только для владельца.')


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={'detail': str(exc)})


@app.get('/api/health')
def healthcheck() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/bootstrap')
def bootstrap(user: UserIdentity = Depends(get_current_user)) -> dict:
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
            'mapEmbedUrl': settings.map_embed_url,
            'mapEmbedTitle': settings.map_embed_title,
            'yandexMapLink': settings.yandex_map_link,
            'yandexAppLink': settings.yandex_app_link,
            'prepaymentAmountRub': settings.prepayment_amount_rub,
            'publicBaseUrl': settings.effective_public_base_url,
        },
        'user': {
            'id': user.user_id,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'username': user.username,
            'isAdmin': user.is_admin,
        },
        'worksCount': len(database.get_works()),
        'reviewsCount': len(database.get_reviews()),
    }


@app.get('/api/works')
def works(user: UserIdentity = Depends(get_current_user)) -> dict:
    return {'items': database.get_works(), 'viewer': {'isAdmin': user.is_admin}}


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
    return {'item': review, 'message': 'Отзыв сохранён и теперь виден всем.'}


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


@app.post('/api/bookings')
async def create_booking(
    full_name: str = Form(...),
    age: int = Form(...),
    service_location: str = Form(...),
    tattoo_description: str = Form(...),
    body_place: str = Form(...),
    size_cm: str = Form(...),
    slot_date: str = Form(...),
    slot_time: str = Form(...),
    prepayment_ack: str = Form(...),
    reference_photo: UploadFile | None = File(default=None),
    user: UserIdentity = Depends(get_current_user),
) -> dict:
    if service_location not in {'studio', 'client_home'}:
        raise HTTPException(status_code=400, detail='Некорректное место проведения сеанса.')
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
        safe_suffix = Path(reference_photo.filename).suffix.lower() or '.jpg'
        if safe_suffix not in {'.jpg', '.jpeg', '.png', '.webp'}:
            raise HTTPException(status_code=400, detail='Разрешены только JPG, PNG и WEBP.')
        unique_name = f'{uuid.uuid4().hex}{safe_suffix}'
        destination = settings.uploads_dir / unique_name
        with destination.open('wb') as buffer:
            shutil.copyfileobj(reference_photo.file, buffer)
        reference_path = str(destination)

    booking = database.create_booking(
        user=user,
        full_name=full_name.strip(),
        age=age,
        service_location=service_location,
        tattoo_description=tattoo_description.strip(),
        body_place=body_place.strip(),
        size_cm=size_cm.strip(),
        slot_date=slot_date,
        slot_time=slot_time,
        reference_image_path=reference_path,
    )

    delivered = False
    delivery_error = None
    try:
        if settings.bot_token != 'CHANGE_ME':
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
        'message': f'Заявка отправлена. После подтверждения нужно будет внести предоплату {settings.prepayment_amount_rub} ₽.',
    }


@app.get('/')
def index() -> FileResponse:
    return FileResponse(BASE_DIR / 'app' / 'static' / 'index.html')
