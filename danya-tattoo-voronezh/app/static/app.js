const tg = window.Telegram?.WebApp;

const state = {
  bootstrap: null,
  works: [],
  reviews: [],
  availability: null,
  selectedDate: null,
  selectedTime: null,
  currentMonth: null,
  adminBookings: [],
  today: new Date().toISOString().slice(0, 10),
};

const els = {
  brandLogo: document.getElementById('brandLogo'),
  brandTitle: document.getElementById('brandTitle'),
  brandSubtitle: document.getElementById('brandSubtitle'),
  heroTitle: document.getElementById('heroTitle'),
  heroSubtitle: document.getElementById('heroSubtitle'),
  worksCount: document.getElementById('worksCount'),
  reviewsCount: document.getElementById('reviewsCount'),
  addressText: document.getElementById('addressText'),
  contactAddressText: document.getElementById('contactAddressText'),
  prepaymentAmountHome: document.getElementById('prepaymentAmountHome'),
  prepaymentAmountBooking: document.getElementById('prepaymentAmountBooking'),
  featuredWorks: document.getElementById('featuredWorks'),
  worksGrid: document.getElementById('worksGrid'),
  reviewsList: document.getElementById('reviewsList'),
  reviewForm: document.getElementById('reviewForm'),
  bookingForm: document.getElementById('bookingForm'),
  calendarGrid: document.getElementById('calendarGrid'),
  calendarMonthLabel: document.getElementById('calendarMonthLabel'),
  slotList: document.getElementById('slotList'),
  selectedSlotSummary: document.getElementById('selectedSlotSummary'),
  telegramLinkCard: document.getElementById('telegramLinkCard'),
  vkLinkCard: document.getElementById('vkLinkCard'),
  mapContainer: document.getElementById('mapContainer'),
  openYandexMapBtn: document.getElementById('openYandexMapBtn'),
  adminNavBtn: document.getElementById('adminNavBtn'),
  adminPage: document.getElementById('adminPage'),
  adminBookingsList: document.getElementById('adminBookingsList'),
  adminDayForm: document.getElementById('adminDayForm'),
  adminSlotForm: document.getElementById('adminSlotForm'),
  adminSlotTime: document.getElementById('adminSlotTime'),
  toast: document.getElementById('toast'),
};

function authHeaders(extra = {}) {
  const headers = { ...extra };
  if (tg?.initData) {
    headers['X-Telegram-Init-Data'] = tg.initData;
  }
  return headers;
}

async function api(url, options = {}) {
  const opts = { ...options };
  opts.headers = authHeaders(options.headers || {});

  const response = await fetch(url, opts);
  if (!response.ok) {
    let errorMessage = 'Не удалось выполнить запрос.';
    try {
      const data = await response.json();
      errorMessage = data.detail || errorMessage;
    } catch (error) {
      console.error(error);
    }
    throw new Error(errorMessage);
  }
  return response.json();
}

function setupTelegram() {
  if (!tg) return;
  tg.ready();
  tg.expand();
  try {
    tg.setHeaderColor?.('#0f0f12');
    tg.setBackgroundColor?.('#0f0f12');
    tg.disableVerticalSwipes?.();
  } catch (error) {
    console.warn('Telegram WebApp methods are not fully available', error);
  }
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.remove('hidden');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    els.toast.classList.add('hidden');
  }, 2600);
}

function escapeHtml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function stars(rating) {
  return '★'.repeat(Number(rating || 0)) + '☆'.repeat(5 - Number(rating || 0));
}

function switchPage(pageId) {
  document.querySelectorAll('.page').forEach((page) => {
    page.classList.toggle('active', page.id === pageId);
  });
  document.querySelectorAll('.nav-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.navTarget === pageId);
  });
  if (pageId === 'adminPage' && state.bootstrap?.user?.isAdmin) {
    loadAdminBookings().catch(handleError);
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function bindNavigation() {
  document.querySelectorAll('[data-nav-target]').forEach((btn) => {
    btn.addEventListener('click', () => switchPage(btn.dataset.navTarget));
  });

  document.getElementById('heroBookingBtn')?.addEventListener('click', () => switchPage('bookingPage'));
  document.getElementById('openWorksBtn')?.addEventListener('click', () => switchPage('worksPage'));
  document.getElementById('openContactBtn')?.addEventListener('click', () => switchPage('contactPage'));
}

function openExternalLink(url) {
  if (!url) return;
  if (tg?.openLink) {
    tg.openLink(url);
    return;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
}

function openYandexMap(appUrl, webUrl) {
  const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || '');
  if (!appUrl || !isMobile) {
    openExternalLink(webUrl);
    return;
  }

  let fallbackTimer = window.setTimeout(() => {
    openExternalLink(webUrl);
  }, 900);

  const cancelFallback = () => {
    if (fallbackTimer) {
      window.clearTimeout(fallbackTimer);
      fallbackTimer = null;
    }
  };

  window.addEventListener('pagehide', cancelFallback, { once: true });
  window.addEventListener('blur', cancelFallback, { once: true });

  try {
    window.location.href = appUrl;
  } catch (error) {
    console.warn(error);
    cancelFallback();
    openExternalLink(webUrl);
  }
}

function monthLabel(year, month) {
  return new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' }).format(new Date(year, month - 1, 1));
}

function renderBootstrap() {
  if (!state.bootstrap) return;
  const { app, user, worksCount, reviewsCount } = state.bootstrap;
  const prepaymentText = `${app.prepaymentAmountRub} ₽`;

  els.brandLogo.src = app.logoUrl || els.brandLogo.src;
  els.brandTitle.textContent = app.name;
  els.brandSubtitle.textContent = app.heroTitle || app.businessName;
  els.heroTitle.textContent = app.heroTitle;
  els.heroSubtitle.textContent = app.heroSubtitle;
  els.worksCount.textContent = worksCount;
  els.reviewsCount.textContent = reviewsCount;
  els.addressText.textContent = app.address;
  els.contactAddressText.textContent = app.address;
  els.prepaymentAmountHome.textContent = prepaymentText;
  els.prepaymentAmountBooking.textContent = prepaymentText;
  els.telegramLinkCard.href = app.telegramLink;
  els.vkLinkCard.href = app.vkLink;
  els.openYandexMapBtn.onclick = () => openYandexMap(app.yandexAppLink, app.yandexMapLink);

  if (user.isAdmin) {
    els.adminNavBtn.classList.remove('hidden');
    els.adminPage.classList.remove('hidden');
  }

  if (els.reviewForm && !els.reviewForm.author_name.value) {
    els.reviewForm.author_name.value = user.firstName || '';
  }

  renderMap();
}

function renderMap() {
  if (!state.bootstrap) return;
  const { app } = state.bootstrap;
  if (app.mapEmbedUrl) {
    els.mapContainer.innerHTML = `
      <iframe
        src="${escapeHtml(app.mapEmbedUrl)}"
        title="${escapeHtml(app.mapEmbedTitle || 'Карта')}"
        loading="lazy"
        referrerpolicy="no-referrer-when-downgrade"
      ></iframe>
    `;
    return;
  }

  els.mapContainer.innerHTML = `
    <div class="map-fallback">
      <strong>${escapeHtml(app.address)}</strong>
      <p class="muted">Нажми кнопку ниже: сначала приложение попробует открыть Яндекс Карты, а если не получится — откроется веб-версия с этим адресом.</p>
    </div>
  `;
}

function renderFeaturedWorks() {
  const items = state.works.slice(0, 2);
  els.featuredWorks.innerHTML = items
    .map(
      (item) => `
        <button class="mini-work" data-featured-work="${item.id}">
          <img src="${item.image_path}" alt="${escapeHtml(item.title)}" />
          <span>${escapeHtml(item.title)}</span>
        </button>
      `,
    )
    .join('');

  els.featuredWorks.querySelectorAll('[data-featured-work]').forEach((button) => {
    button.addEventListener('click', () => switchPage('worksPage'));
  });
}

function renderWorks() {
  els.worksCount.textContent = state.works.length;
  els.worksGrid.innerHTML = state.works
    .map(
      (item) => `
        <article class="work-card">
          <img src="${item.image_path}" alt="${escapeHtml(item.title)}" />
          <div class="work-content">
            <div class="work-title-row">
              <h3>${escapeHtml(item.title)}</h3>
              <span class="review-badge">${stars(item.review_rating)}</span>
            </div>
            <p class="muted">${escapeHtml(item.description)}</p>
            <div class="quote-box">
              <strong>${escapeHtml(item.review_author)}</strong>
              <p class="muted">${escapeHtml(item.review_text)}</p>
            </div>
          </div>
        </article>
      `,
    )
    .join('');
}

function renderReviews() {
  els.reviewsCount.textContent = state.reviews.length;
  els.reviewsList.innerHTML = state.reviews
    .map((review) => {
      const adminActions = state.bootstrap?.user?.isAdmin
        ? `
          <div class="review-actions">
            <button class="secondary-btn" data-edit-review="${review.id}">Редактировать</button>
            <button class="secondary-btn danger-soft" data-delete-review="${review.id}">Удалить</button>
          </div>
        `
        : '';
      return `
        <article class="review-card">
          <div class="review-content">
            <div class="review-title-row">
              <div>
                <strong>${escapeHtml(review.author_name)}</strong>
                <p class="muted">${new Date(review.created_at).toLocaleDateString('ru-RU')}</p>
              </div>
              <span class="stars">${stars(review.rating)}</span>
            </div>
            <p>${escapeHtml(review.text)}</p>
            ${adminActions}
          </div>
        </article>
      `;
    })
    .join('');
}

function bookingLocationLabel(value) {
  if (value === 'studio') return 'У мастера';
  if (value === 'client_home') return 'У клиента дома';
  return value;
}

function bookingStatusLabel(value) {
  if (value === 'pending') return 'ожидает';
  if (value === 'confirmed') return 'подтверждена';
  if (value === 'rejected') return 'отклонена';
  return value;
}

function renderAdminBookings() {
  if (!state.bootstrap?.user?.isAdmin) return;
  if (!state.adminBookings.length) {
    els.adminBookingsList.innerHTML = '<div class="section-card">Пока заявок нет.</div>';
    return;
  }

  els.adminBookingsList.innerHTML = state.adminBookings
    .map(
      (booking) => `
        <article class="booking-card">
          <div class="booking-content">
            <div class="work-title-row">
              <strong>Заявка #${booking.id}</strong>
              <span class="review-badge">${escapeHtml(bookingStatusLabel(booking.status))}</span>
            </div>
            <div class="booking-meta">
              <span>📅 ${booking.slot_date} ${booking.slot_time}</span>
              <span>👤 ${escapeHtml(booking.full_name)} (${booking.age})</span>
              <span>📍 ${escapeHtml(bookingLocationLabel(booking.service_location))}</span>
              <span>🧍 ${escapeHtml(booking.body_place)}</span>
              <span>📏 ${escapeHtml(booking.size_cm)}</span>
              <span>💳 Предоплата: ${escapeHtml(String(state.bootstrap.app.prepaymentAmountRub))} ₽</span>
            </div>
            <p>${escapeHtml(booking.tattoo_description)}</p>
          </div>
        </article>
      `,
    )
    .join('');
}

function firstWeekdayOffset(year, month) {
  const jsDay = new Date(year, month - 1, 1).getDay();
  return jsDay === 0 ? 6 : jsDay - 1;
}

function getDayRecord(dateStr) {
  return state.availability?.days?.find((item) => item.date === dateStr) || null;
}

function renderCalendar() {
  if (!state.availability) return;
  const { year, month, days } = state.availability;
  els.calendarMonthLabel.textContent = monthLabel(year, month);
  const offset = firstWeekdayOffset(year, month);
  const blanks = Array.from({ length: offset }, () => '<div class="day-pill empty"></div>').join('');
  const items = days
    .map((day) => {
      const isPast = day.date < state.today;
      const selected = state.selectedDate === day.date;
      return `
        <button
          class="day-pill ${day.status} ${isPast ? 'past' : ''} ${selected ? 'selected' : ''}"
          data-day="${day.date}"
          ${isPast ? 'disabled' : ''}
        >
          <span>${Number(day.date.slice(-2))}</span>
        </button>
      `;
    })
    .join('');
  els.calendarGrid.innerHTML = blanks + items;

  els.calendarGrid.querySelectorAll('[data-day]').forEach((button) => {
    button.addEventListener('click', async () => {
      const dateStr = button.dataset.day;
      state.selectedDate = dateStr;
      state.selectedTime = null;
      syncBookingFormSelection();
      renderCalendar();
      await loadDaySlots(dateStr);
    });
  });
}

function renderDaySlots(dayRecord) {
  if (!dayRecord) {
    els.slotList.innerHTML = '';
    els.selectedSlotSummary.textContent = 'Выбери дату и время.';
    return;
  }

  els.selectedSlotSummary.textContent = state.selectedTime
    ? `Выбрано: ${state.selectedDate} в ${state.selectedTime}`
    : `Дата: ${state.selectedDate}. Выбери время.`;

  els.slotList.innerHTML = dayRecord.slots
    .map((slot) => {
      const disabled = slot.status !== 'available';
      const selected = state.selectedTime === slot.time;
      return `
        <button
          class="slot-chip ${slot.status} ${selected ? 'selected' : ''}"
          data-slot="${slot.time}"
          ${disabled ? 'disabled' : ''}
        >
          ${slot.time}
        </button>
      `;
    })
    .join('');

  els.slotList.querySelectorAll('[data-slot]').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedTime = button.dataset.slot;
      syncBookingFormSelection();
      renderDaySlots(dayRecord);
    });
  });
}

function syncBookingFormSelection() {
  if (!els.bookingForm) return;
  els.bookingForm.slot_date.value = state.selectedDate || '';
  els.bookingForm.slot_time.value = state.selectedTime || '';
}

function populateAdminTimeSelect() {
  const times = new Set();
  (state.availability?.days || []).forEach((day) => {
    day.slots.forEach((slot) => times.add(slot.time));
  });
  if (!times.size) {
    ['10:00', '12:00', '14:00', '16:00', '18:00'].forEach((time) => times.add(time));
  }
  els.adminSlotTime.innerHTML = Array.from(times)
    .sort()
    .map((time) => `<option value="${time}">${time}</option>`)
    .join('');
}

async function loadBootstrap() {
  state.bootstrap = await api('/api/bootstrap');
  renderBootstrap();
}

async function loadWorks() {
  const data = await api('/api/works');
  state.works = data.items || [];
  renderWorks();
  renderFeaturedWorks();
}

async function loadReviews() {
  const data = await api('/api/reviews');
  state.reviews = data.items || [];
  renderReviews();
}

async function loadAvailability(year, month) {
  state.currentMonth = { year, month };
  const data = await api(`/api/availability?month=${year}-${String(month).padStart(2, '0')}`);
  state.availability = data;
  renderCalendar();
  populateAdminTimeSelect();

  if (state.selectedDate) {
    const refreshedDay = getDayRecord(state.selectedDate);
    if (!refreshedDay || refreshedDay.status === 'busy') {
      state.selectedTime = null;
      syncBookingFormSelection();
    }
    renderDaySlots(refreshedDay);
  }
}

async function loadDaySlots(dateStr) {
  const data = await api(`/api/availability/day/${dateStr}`);
  const record = getDayRecord(dateStr);
  if (record) {
    record.slots = data.slots;
    record.available_count = data.slots.filter((slot) => slot.status === 'available').length;
    record.busy_count = data.slots.filter((slot) => slot.status === 'busy').length;
    record.status = record.available_count > 0 ? 'available' : 'busy';
  }
  renderDaySlots({ date: dateStr, slots: data.slots });
  renderCalendar();
}

async function loadAdminBookings() {
  if (!state.bootstrap?.user?.isAdmin) return;
  const data = await api('/api/admin/bookings');
  state.adminBookings = data.items || [];
  renderAdminBookings();
}

async function submitReview(event) {
  event.preventDefault();
  const formData = new FormData(els.reviewForm);
  const payload = {
    author_name: formData.get('author_name'),
    rating: Number(formData.get('rating')),
    text: formData.get('text'),
  };
  await api('/api/reviews', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  els.reviewForm.reset();
  if (state.bootstrap?.user?.firstName) {
    els.reviewForm.author_name.value = state.bootstrap.user.firstName;
  }
  await loadReviews();
  showToast('Отзыв опубликован');
}

async function submitBooking(event) {
  event.preventDefault();
  if (!state.selectedDate || !state.selectedTime) {
    showToast('Сначала выбери дату и время');
    switchPage('bookingPage');
    return;
  }
  const formData = new FormData(els.bookingForm);
  const data = await api('/api/bookings', {
    method: 'POST',
    body: formData,
  });
  showToast(data.message || 'Заявка отправлена');
  els.bookingForm.reset();
  state.selectedTime = null;
  syncBookingFormSelection();
  await loadAvailability(state.currentMonth.year, state.currentMonth.month);
  await loadDaySlots(state.selectedDate);
  if (state.bootstrap?.user?.isAdmin) {
    await loadAdminBookings();
  }
}

async function handleReviewAction(event) {
  const editId = event.target.dataset.editReview;
  const deleteId = event.target.dataset.deleteReview;

  if (editId) {
    const review = state.reviews.find((item) => String(item.id) === editId);
    if (!review) return;
    const author_name = window.prompt('Имя автора', review.author_name);
    if (!author_name) return;
    const rating = Number(window.prompt('Оценка от 1 до 5', review.rating));
    if (!rating || rating < 1 || rating > 5) {
      showToast('Оценка должна быть от 1 до 5');
      return;
    }
    const text = window.prompt('Текст отзыва', review.text);
    if (!text) return;
    await api(`/api/admin/reviews/${editId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ author_name, rating, text }),
    });
    await loadReviews();
    showToast('Отзыв обновлён');
  }

  if (deleteId) {
    const confirmed = window.confirm('Удалить этот отзыв?');
    if (!confirmed) return;
    await api(`/api/admin/reviews/${deleteId}`, { method: 'DELETE' });
    await loadReviews();
    showToast('Отзыв удалён');
  }
}

async function handleAdminDayAction(status) {
  const slot_date = new FormData(els.adminDayForm).get('slot_date');
  if (!slot_date) {
    showToast('Выбери дату');
    return;
  }
  await api('/api/admin/availability/day', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slot_date, status }),
  });
  await loadAvailability(state.currentMonth.year, state.currentMonth.month);
  if (state.selectedDate === slot_date) {
    await loadDaySlots(slot_date);
  }
  showToast(status === 'available' ? 'День открыт' : 'День закрыт');
}

async function handleAdminSlotAction(status) {
  const formData = new FormData(els.adminSlotForm);
  const slot_date = formData.get('slot_date');
  const slot_time = formData.get('slot_time');
  if (!slot_date || !slot_time) {
    showToast('Выбери дату и время');
    return;
  }
  await api('/api/admin/availability/slot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slot_date, slot_time, status }),
  });
  await loadAvailability(state.currentMonth.year, state.currentMonth.month);
  if (state.selectedDate === slot_date) {
    await loadDaySlots(slot_date);
  }
  showToast(status === 'available' ? 'Слот открыт' : 'Слот закрыт');
}

function handleError(error) {
  console.error(error);
  showToast(error.message || 'Что-то пошло не так');
}

function bindForms() {
  els.reviewForm.addEventListener('submit', (event) => submitReview(event).catch(handleError));
  els.bookingForm.addEventListener('submit', (event) => submitBooking(event).catch(handleError));
  els.reviewsList.addEventListener('click', (event) => handleReviewAction(event).catch(handleError));

  els.adminDayForm.querySelectorAll('[data-day-action]').forEach((button) => {
    button.addEventListener('click', () => handleAdminDayAction(button.dataset.dayAction).catch(handleError));
  });

  els.adminSlotForm.querySelectorAll('[data-slot-action]').forEach((button) => {
    button.addEventListener('click', () => handleAdminSlotAction(button.dataset.slotAction).catch(handleError));
  });
}

function bindCalendarControls() {
  document.getElementById('prevMonthBtn')?.addEventListener('click', async () => {
    const month = state.currentMonth.month === 1 ? 12 : state.currentMonth.month - 1;
    const year = state.currentMonth.month === 1 ? state.currentMonth.year - 1 : state.currentMonth.year;
    try {
      await loadAvailability(year, month);
    } catch (error) {
      handleError(error);
    }
  });

  document.getElementById('nextMonthBtn')?.addEventListener('click', async () => {
    const month = state.currentMonth.month === 12 ? 1 : state.currentMonth.month + 1;
    const year = state.currentMonth.month === 12 ? state.currentMonth.year + 1 : state.currentMonth.year;
    try {
      await loadAvailability(year, month);
    } catch (error) {
      handleError(error);
    }
  });
}

async function init() {
  setupTelegram();
  bindNavigation();
  bindForms();
  bindCalendarControls();

  const now = new Date();
  state.currentMonth = { year: now.getFullYear(), month: now.getMonth() + 1 };

  try {
    await loadBootstrap();
    await Promise.all([loadWorks(), loadReviews()]);
    await loadAvailability(state.currentMonth.year, state.currentMonth.month);
  } catch (error) {
    handleError(error);
  }
}

init();
