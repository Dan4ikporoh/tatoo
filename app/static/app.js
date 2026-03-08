const tg = window.Telegram?.WebApp;

const state = {
  initData: tg?.initData || '',
  bootstrap: null,
  works: [],
  reviews: [],
  availability: null,
  selectedDate: null,
  selectedTime: null,
  currentMonth: null,
  today: new Date().toISOString().slice(0, 10),
  adminBookings: [],
  estimate: { from: 2000, to: 5000 },
};

const els = {
  toast: document.getElementById('toast'),
  pages: Array.from(document.querySelectorAll('.page')),
  navButtons: Array.from(document.querySelectorAll('.side-nav-btn')), 
  heroBookingBtn: document.getElementById('heroBookingBtn'),
  brandTitle: document.getElementById('brandTitle'),
  brandSubtitle: document.getElementById('brandSubtitle'),
  heroTitle: document.getElementById('heroTitle'),
  heroSubtitle: document.getElementById('heroSubtitle'),
  worksCount: document.getElementById('worksCount'),
  reviewsCount: document.getElementById('reviewsCount'),
  metricRating: document.getElementById('metricRating'),
  featuredWorks: document.getElementById('featuredWorks'),
  worksGrid: document.getElementById('worksGrid'),
  reviewForm: document.getElementById('reviewForm'),
  reviewsList: document.getElementById('reviewsList'),
  bookingForm: document.getElementById('bookingForm'),
  prepaymentAmountHome: document.getElementById('prepaymentAmountHome'),
  prepaymentAmountBooking: document.getElementById('prepaymentAmountBooking'),
  estimateRange: document.getElementById('estimateRange'),
  sizeInput: document.getElementById('sizeInput'),
  styleChoice: document.getElementById('styleChoice'),
  colorMode: document.getElementById('colorMode'),
  bodyPlaceInput: document.getElementById('bodyPlaceInput'),
  mapContainer: document.getElementById('mapContainer'),
  addressText: document.getElementById('addressText'),
  openYandexMapBtn: document.getElementById('openYandexMapBtn'),
  contactYandexBtn: document.getElementById('contactYandexBtn'),
  telegramLinkCard: document.getElementById('telegramLinkCard'),
  vkLinkCard: document.getElementById('vkLinkCard'),
  calendarMonthLabel: document.getElementById('calendarMonthLabel'),
  calendarGrid: document.getElementById('calendarGrid'),
  selectedSlotSummary: document.getElementById('selectedSlotSummary'),
  slotList: document.getElementById('slotList'),
  prevMonthBtn: document.getElementById('prevMonthBtn'),
  nextMonthBtn: document.getElementById('nextMonthBtn'),
  adminNavBtn: document.getElementById('adminNavBtn'),
  adminWorkForm: document.getElementById('adminWorkForm'),
  adminAddWorkEntry: document.getElementById('adminAddWorkEntry'),
  openAddWorkBtn: document.getElementById('openAddWorkBtn'),
  addWorkModal: document.getElementById('addWorkModal'),
  adminWorksList: document.getElementById('adminWorksList'),
  adminDayForm: document.getElementById('adminDayForm'),
  adminSlotForm: document.getElementById('adminSlotForm'),
  adminSlotTime: document.getElementById('adminSlotTime'),
  adminBookingsList: document.getElementById('adminBookingsList'),
  workReviewModal: document.getElementById('workReviewModal'),
  authHint: document.getElementById('authHint'),
  menuToggleBtn: document.getElementById('menuToggleBtn'),
  sideMenu: document.getElementById('sideMenu'),
  sideMenuBackdrop: document.getElementById('sideMenuBackdrop'),
  sideMenuClose: document.getElementById('sideMenuClose'),
  workReviewModalTitle: document.getElementById('workReviewModalTitle'),
  workReviewForm: document.getElementById('workReviewForm'),
  lightbox: document.getElementById('lightbox'),
  lightboxImage: document.getElementById('lightboxImage'),
  lightboxTitle: document.getElementById('lightboxTitle'),
  lightboxDesc: document.getElementById('lightboxDesc'),
};

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function stars(count) {
  return '★'.repeat(Number(count || 0)) + '☆'.repeat(Math.max(0, 5 - Number(count || 0)));
}

function formatPrice(value) {
  return new Intl.NumberFormat('ru-RU').format(Number(value || 0));
}

function formatDate(value) {
  if (!value) return '';
  try {
    return new Date(value).toLocaleDateString('ru-RU');
  } catch {
    return value;
  }
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.remove('hidden');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => els.toast.classList.add('hidden'), 2600);
}

async function api(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.initData) headers.set('X-Telegram-Init-Data', state.initData);
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let detail = 'Ошибка запроса';
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      detail = `${response.status} ${response.statusText}`;
    }
    throw new Error(detail);
  }
  const type = response.headers.get('content-type') || '';
  return type.includes('application/json') ? response.json() : response.text();
}

function switchPage(pageId) {
  els.pages.forEach((page) => page.classList.toggle('active', page.id === pageId));
  els.navButtons.forEach((button) => button.classList.toggle('active', button.dataset.navTarget === pageId));
  closeSideMenu();
  if (pageId === 'homePage' || pageId === 'contactPage') renderMap();
  if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
}

function openSideMenu() {
  els.sideMenu?.classList.remove('hidden');
  document.body.classList.add('menu-open');
}

function closeSideMenu() {
  els.sideMenu?.classList.add('hidden');
  document.body.classList.remove('menu-open');
}

function setupTelegram() {
  if (!tg) return;
  tg.ready();
  tg.expand();
  tg.setHeaderColor?.('#09090c');
  tg.setBackgroundColor?.('#09090c');
  tg.BackButton?.hide?.();
}

function bindNavigation() {
  document.querySelectorAll('[data-nav-target]').forEach((button) => {
    button.addEventListener('click', () => switchPage(button.dataset.navTarget));
  });
  els.heroBookingBtn?.addEventListener('click', () => switchPage('bookingPage'));
  els.menuToggleBtn?.addEventListener('click', openSideMenu);
  els.sideMenuBackdrop?.addEventListener('click', closeSideMenu);
  els.sideMenuClose?.addEventListener('click', closeSideMenu);
}


function initRevealAnimations() {
  const nodes = document.querySelectorAll('.reveal, .section-card, .page-heading, .work-card');
  if (!('IntersectionObserver' in window)) {
    nodes.forEach((node) => node.classList.add('is-visible'));
    return;
  }
  if (initRevealAnimations._observer) initRevealAnimations._observer.disconnect();
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add('is-visible');
    });
  }, { threshold: 0.03 });
  nodes.forEach((node, index) => {
    node.style.setProperty('--delay', `${Math.min(index * 18, 120)}ms`);
    observer.observe(node);
  });
  initRevealAnimations._observer = observer;
}


function openAddWorkModal() {
  if (!state.bootstrap?.user?.isAdmin) return;
  els.addWorkModal?.classList.remove('hidden');
}

function closeAddWorkModal() {
  els.addWorkModal?.classList.add('hidden');
}

function renderMap(force = false) {
  const app = state.bootstrap?.app;
  if (!app || !els.mapContainer) return;
  if (els.mapContainer.dataset.loaded === '1') return;
  if (!force && document.getElementById('homePage')?.classList.contains('active') === false) return;
  const mount = () => {
    els.mapContainer.innerHTML = `
      <iframe src="${escapeHtml(app.mapEmbedUrl)}" title="${escapeHtml(app.mapEmbedTitle || 'Яндекс Карта')}" loading="lazy"></iframe>
    `;
    els.mapContainer.dataset.loaded = '1';
  };
  if ('requestIdleCallback' in window) {
    requestIdleCallback(mount, { timeout: 1200 });
  } else {
    setTimeout(mount, 250);
  }
}

function openYandexMaps() {
  const app = state.bootstrap?.app;
  if (!app) return;
  try {
    window.location.href = app.yandexAppLink;
    setTimeout(() => window.open(app.yandexMapLink, '_blank', 'noopener'), 450);
  } catch {
    window.open(app.yandexMapLink, '_blank', 'noopener');
  }
}

function renderBootstrap() {
  const { app, metrics, user } = state.bootstrap;
  els.brandTitle.textContent = app.name;
  els.brandSubtitle.textContent = app.heroTitle;
  els.heroTitle.textContent = app.heroTitle;
  els.heroSubtitle.textContent = app.heroSubtitle;
  els.worksCount.textContent = metrics.works_count;
  els.reviewsCount.textContent = metrics.reviews_count;
  els.metricRating.textContent = metrics.average_rating ? metrics.average_rating.toFixed(1) : '5.0';
  els.prepaymentAmountHome.textContent = `${app.prepaymentAmountRub} ₽`;
  els.prepaymentAmountBooking.textContent = `${app.prepaymentAmountRub} ₽`;
  els.addressText.textContent = app.address;
  els.telegramLinkCard.href = app.telegramLink;
  els.vkLinkCard.href = app.vkLink;
  if (els.reviewForm && !els.reviewForm.author_name.value) {
    els.reviewForm.author_name.value = user.firstName || '';
  }
  if (els.workReviewForm && !els.workReviewForm.author_name.value) {
    els.workReviewForm.author_name.value = user.firstName || '';
  }
  if (user.isAdmin) {
    els.adminNavBtn.classList.remove('hidden');
    document.getElementById('adminPage').classList.remove('hidden');
    els.adminAddWorkEntry?.classList.remove('hidden');
  }
  renderMap();
  initRevealAnimations();
}

function renderFeaturedWorks() {
  const items = state.works.length ? state.works.slice(0, 3) : (state.bootstrap?.featuredWorks || []);
  els.featuredWorks.innerHTML = items.map((work) => `
    <button class="feature-card reveal" data-open-lightbox="${work.id}">
      <img src="${work.image_path}" alt="${escapeHtml(work.title)}" loading="lazy" decoding="async" />
      <div class="feature-overlay">
        <strong>${escapeHtml(work.title)}</strong>
        <span class="muted">${work.review_count || 0} отзыв(ов)</span>
      </div>
    </button>
  `).join('');
}

function renderWorks() {
  els.worksGrid.innerHTML = state.works.map((work) => {
    const assigned = work.allowed_reviewer_username ? `<span class="tag">отзыв может оставить @${escapeHtml(work.allowed_reviewer_username)}</span>` : `<span class="tag">открытый отзыв</span>`;
    const reviewButton = work.can_review ? `<button class="secondary-btn" data-open-work-review="${work.id}">Оставить отзыв к работе</button>` : '';
    const adminButtons = state.bootstrap?.user?.isAdmin
      ? `
        <button class="secondary-btn" data-edit-work="${work.id}">Изменить</button>
        <button class="secondary-btn danger-soft" data-delete-work="${work.id}">Удалить</button>
      `
      : '';
    const reviews = (work.reviews || []).length
      ? work.reviews.map((review) => {
          const adminReviewActions = state.bootstrap?.user?.isAdmin
            ? `
              <div class="review-actions">
                <button class="link-btn" data-edit-work-review="${review.id}">редактировать</button>
                <button class="link-btn" data-delete-work-review="${review.id}">удалить</button>
              </div>
            `
            : '';
          return `
            <div class="work-review">
              <div class="review-top">
                <strong>${escapeHtml(review.author_name)}</strong>
                <span class="stars">${stars(review.rating)}</span>
              </div>
              <p class="muted">${escapeHtml(review.text)}</p>
              ${adminReviewActions}
            </div>
          `;
        }).join('')
      : '<div class="work-review"><p class="muted">Пока отзывов к этой работе нет.</p></div>';

    return `
      <article class="work-card modern-card reveal">
        <div class="work-media">
          <img class="work-image" src="${work.image_path}" alt="${escapeHtml(work.title)}" data-open-lightbox="${work.id}" loading="lazy" decoding="async" />
        </div>
        <div class="work-body">
          <div class="section-head">
            <div>
              <h3>${escapeHtml(work.title)}</h3>
              <p class="muted">${escapeHtml(work.description)}</p>
            </div>
            <span class="rating-chip">${work.average_rating ? work.average_rating.toFixed(1) : '0.0'} / 5</span>
          </div>
          <div class="tag-row">
            <span class="tag">${work.review_count || 0} отзыв(ов)</span>
            <span class="tag">рейтинг ${work.average_rating ? work.average_rating.toFixed(1) : '0.0'}</span>
            ${assigned}
          </div>
          <div class="work-actions">
            <button class="secondary-btn" data-open-lightbox="${work.id}">Открыть фото</button>
            ${reviewButton}
            ${adminButtons}
          </div>
          <div class="review-stack">${reviews}</div>
        </div>
      </article>
    `;
  }).join('');
  initRevealAnimations();
}

function renderReviews() {
  els.reviewsList.innerHTML = state.reviews.map((review) => {
    const adminActions = state.bootstrap?.user?.isAdmin
      ? `
        <div class="review-actions">
          <button class="link-btn" data-edit-review="${review.id}">редактировать</button>
          <button class="link-btn" data-delete-review="${review.id}">удалить</button>
        </div>
      `
      : '';
    return `
      <article class="review-card reveal">
        <div class="review-top">
          <div>
            <strong>${escapeHtml(review.author_name)}</strong>
            <p class="muted">${formatDate(review.created_at)}</p>
          </div>
          <span class="stars">${stars(review.rating)}</span>
        </div>
        <p>${escapeHtml(review.text)}</p>
        ${adminActions}
      </article>
    `;
  }).join('');
  initRevealAnimations();
}

function renderAdminWorks() {
  if (!state.bootstrap?.user?.isAdmin) return;
  els.adminWorksList.innerHTML = state.works.map((work) => `
    <article class="admin-work-card">
      <img src="${work.image_path}" alt="${escapeHtml(work.title)}" loading="lazy" decoding="async" />
      <div>
        <div class="section-head">
          <strong>${escapeHtml(work.title)}</strong>
          <span class="tag">${work.review_count || 0} отзыв(ов)</span>
        </div>
        <p class="muted">${escapeHtml(work.description)}</p>
        <div class="tag-row" style="margin-top:8px;">
          <span class="tag">username для отзыва: ${work.allowed_reviewer_username ? '@' + escapeHtml(work.allowed_reviewer_username) : 'не задан'}</span>
        </div>
        <div class="inline-actions" style="margin-top:10px;">
          <button class="secondary-btn" data-edit-work="${work.id}">Изменить</button>
          <button class="secondary-btn danger-soft" data-delete-work="${work.id}">Удалить</button>
        </div>
      </div>
    </article>
  `).join('');
}

function bookingLocationLabel(value) {
  return value === 'client_home' ? 'У клиента дома' : 'У мастера';
}

function renderAdminBookings() {
  if (!state.bootstrap?.user?.isAdmin) return;
  els.adminBookingsList.innerHTML = state.adminBookings.length ? state.adminBookings.map((booking) => `
    <article class="booking-card">
      <strong>Заявка #${booking.id} — ${escapeHtml(booking.status)}</strong>
      <div class="booking-meta">
        <span>👤 ${escapeHtml(booking.full_name)} (${booking.age})</span>
        <span>📅 ${booking.slot_date} ${booking.slot_time}</span>
        <span>📍 ${escapeHtml(bookingLocationLabel(booking.service_location))}</span>
        <span>🧍 ${escapeHtml(booking.body_place)}</span>
        <span>📏 ${escapeHtml(booking.size_cm)}</span>
        <span>💰 ${formatPrice(booking.estimated_price_from)}–${formatPrice(booking.estimated_price_to)} ₽</span>
      </div>
    </article>
  `).join('') : '<div class="booking-card">Пока заявок нет.</div>';
}

function getDayRecord(dateStr) {
  return state.availability?.days?.find((item) => item.date === dateStr) || null;
}

function renderCalendar() {
  if (!state.availability) return;
  const { year, month, days } = state.availability;
  const firstDay = new Date(year, month - 1, 1);
  const offset = (firstDay.getDay() + 6) % 7;
  els.calendarMonthLabel.textContent = firstDay.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' });

  const blanks = Array.from({ length: offset }, () => '<div class="day-pill empty"></div>').join('');
  const items = days.map((day) => {
    const isPast = day.date < state.today;
    const selected = day.date === state.selectedDate;
    return `
      <button class="day-pill ${day.status} ${selected ? 'selected' : ''} ${isPast ? 'past' : ''}" data-day="${day.date}" ${isPast ? 'disabled' : ''}>
        <span>${Number(day.date.slice(-2))}</span>
      </button>
    `;
  }).join('');
  els.calendarGrid.innerHTML = blanks + items;

  els.calendarGrid.querySelectorAll('[data-day]').forEach((button) => {
    button.addEventListener('click', async () => {
      state.selectedDate = button.dataset.day;
      state.selectedTime = null;
      syncBookingSelection();
      renderCalendar();
      await loadDaySlots(state.selectedDate);
    });
  });
}

function renderDaySlots(record) {
  if (!record) {
    els.slotList.innerHTML = '';
    els.selectedSlotSummary.textContent = 'Выбери дату и время.';
    return;
  }
  els.selectedSlotSummary.textContent = state.selectedTime
    ? `Выбрано: ${state.selectedDate} в ${state.selectedTime}`
    : `Дата: ${state.selectedDate}. Теперь выбери время.`;
  els.slotList.innerHTML = record.slots.map((slot) => `
    <button class="slot-chip ${slot.status} ${state.selectedTime === slot.time ? 'selected' : ''}" data-slot="${slot.time}" ${slot.status !== 'available' ? 'disabled' : ''}>${slot.time}</button>
  `).join('');
  els.slotList.querySelectorAll('[data-slot]').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedTime = button.dataset.slot;
      syncBookingSelection();
      renderDaySlots(record);
    });
  });
}

function syncBookingSelection() {
  els.bookingForm.slot_date.value = state.selectedDate || '';
  els.bookingForm.slot_time.value = state.selectedTime || '';
}

function populateAdminTimeSelect() {
  const times = new Set();
  (state.availability?.days || []).forEach((day) => day.slots.forEach((slot) => times.add(slot.time)));
  if (!times.size) ['10:00', '12:00', '14:00', '16:00', '18:00'].forEach((time) => times.add(time));
  els.adminSlotTime.innerHTML = Array.from(times).sort().map((time) => `<option value="${time}">${time}</option>`).join('');
}

async function loadBootstrap() {
  state.bootstrap = await api('/api/bootstrap');
  renderBootstrap();
  renderFeaturedWorks();
}

async function loadWorks() {
  const data = await api('/api/works');
  state.works = data.items || [];
  renderWorks();
  renderAdminWorks();
  renderFeaturedWorks();
}

async function loadReviews() {
  const data = await api('/api/reviews');
  state.reviews = data.items || [];
  renderReviews();
}

async function loadAvailability(year, month) {
  state.currentMonth = { year, month };
  state.availability = await api(`/api/availability?month=${year}-${String(month).padStart(2, '0')}`);
  renderCalendar();
  populateAdminTimeSelect();
  if (state.selectedDate) {
    const record = getDayRecord(state.selectedDate);
    renderDaySlots(record);
  }
}

async function loadDaySlots(dateStr) {
  const data = await api(`/api/availability/day/${dateStr}`);
  const record = getDayRecord(dateStr);
  if (record) {
    record.slots = data.slots;
    record.available_count = data.slots.filter((slot) => slot.status === 'available').length;
    record.busy_count = data.slots.filter((slot) => slot.status === 'busy').length;
    record.status = record.available_count ? 'available' : 'busy';
  }
  renderDaySlots(record || { date: dateStr, slots: data.slots });
  renderCalendar();
}

async function loadAdminBookings() {
  if (!state.bootstrap?.user?.isAdmin) return;
  const data = await api('/api/admin/bookings');
  state.adminBookings = data.items || [];
  renderAdminBookings();
}

function openWorkReviewModal(workId) {
  const work = state.works.find((item) => Number(item.id) === Number(workId));
  if (!work) return;
  els.workReviewModalTitle.textContent = `Отзыв к работе: ${work.title}`;
  els.workReviewForm.work_id.value = work.id;
  if (!els.workReviewForm.author_name.value) {
    els.workReviewForm.author_name.value = state.bootstrap?.user?.firstName || '';
  }
  els.workReviewModal.classList.remove('hidden');
}

function closeWorkReviewModal() {
  els.workReviewModal.classList.add('hidden');
}

function openLightbox(workId) {
  const work = state.works.find((item) => Number(item.id) === Number(workId));
  if (!work) return;
  els.lightboxImage.src = work.image_path;
  els.lightboxTitle.textContent = work.title;
  els.lightboxDesc.textContent = work.description;
  els.lightbox.classList.remove('hidden');
}

function closeLightbox() {
  els.lightbox.classList.add('hidden');
}

async function submitReview(event) {
  event.preventDefault();
  const formData = new FormData(els.reviewForm);
  await api('/api/reviews', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      author_name: formData.get('author_name'),
      rating: Number(formData.get('rating')),
      text: formData.get('text'),
    }),
  });
  els.reviewForm.reset();
  els.reviewForm.author_name.value = state.bootstrap?.user?.firstName || '';
  await Promise.all([loadReviews(), loadBootstrap()]);
  showToast('Общий отзыв опубликован');
}

async function submitWorkReview(event) {
  event.preventDefault();
  const formData = new FormData(els.workReviewForm);
  await api(`/api/works/${formData.get('work_id')}/reviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      author_name: formData.get('author_name'),
      rating: Number(formData.get('rating')),
      text: formData.get('text'),
    }),
  });
  closeWorkReviewModal();
  els.workReviewForm.reset();
  els.workReviewForm.author_name.value = state.bootstrap?.user?.firstName || '';
  await Promise.all([loadWorks(), loadBootstrap()]);
  showToast('Отзыв к работе опубликован');
}

async function submitBooking(event) {
  event.preventDefault();
  if (!state.selectedDate || !state.selectedTime) {
    showToast('Сначала выбери дату и время');
    return;
  }
  const formData = new FormData(els.bookingForm);
  const result = await api('/api/bookings', { method: 'POST', body: formData });
  showToast(result.message || 'Заявка отправлена');
  els.bookingForm.reset();
  state.selectedTime = null;
  syncBookingSelection();
  await loadAvailability(state.currentMonth.year, state.currentMonth.month);
  await loadDaySlots(state.selectedDate);
  if (state.bootstrap?.user?.isAdmin) await loadAdminBookings();
}

async function submitAdminWork(event) {
  event.preventDefault();
  const formData = new FormData(els.adminWorkForm);
  await api('/api/admin/works', { method: 'POST', body: formData });
  els.adminWorkForm.reset();
  closeAddWorkModal();
  await Promise.all([loadWorks(), loadBootstrap()]);
  showToast('Работа добавлена');
}

async function updateEstimate() {
  const size = els.sizeInput.value.trim();
  if (!size) {
    state.estimate = { from: 2000, to: 5000 };
    els.estimateRange.textContent = 'от 2 000 до 5 000 ₽';
    return;
  }
  try {
    const params = new URLSearchParams({
      size_cm: size,
      style_choice: els.styleChoice.value,
      color_mode: els.colorMode.value,
      service_location: els.bookingForm.service_location.value,
      body_place: els.bodyPlaceInput.value.trim(),
    });
    const data = await api(`/api/price-estimate?${params.toString()}`);
    state.estimate = { from: data.estimateFrom, to: data.estimateTo };
    els.estimateRange.textContent = `${formatPrice(data.estimateFrom)}–${formatPrice(data.estimateTo)} ₽`;
  } catch (error) {
    console.error(error);
  }
}

function debounce(fn, delay = 250) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

async function handleReviewActions(event) {
  const editId = event.target.dataset.editReview;
  const deleteId = event.target.dataset.deleteReview;
  if (editId) {
    const review = state.reviews.find((item) => String(item.id) === editId);
    if (!review) return;
    const author_name = window.prompt('Имя автора', review.author_name);
    if (!author_name) return;
    const rating = Number(window.prompt('Оценка 1-5', review.rating));
    const text = window.prompt('Текст отзыва', review.text);
    if (!text) return;
    await api(`/api/admin/reviews/${editId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ author_name, rating, text }),
    });
    await Promise.all([loadReviews(), loadBootstrap()]);
    showToast('Отзыв обновлён');
  }
  if (deleteId) {
    if (!window.confirm('Удалить отзыв?')) return;
    await api(`/api/admin/reviews/${deleteId}`, { method: 'DELETE' });
    await Promise.all([loadReviews(), loadBootstrap()]);
    showToast('Отзыв удалён');
  }
}

async function handleWorksActions(event) {
  const openReviewId = event.target.dataset.openWorkReview;
  const openLightboxId = event.target.dataset.openLightbox;
  const deleteWorkId = event.target.dataset.deleteWork;
  const editWorkId = event.target.dataset.editWork;
  const editWorkReviewId = event.target.dataset.editWorkReview;
  const deleteWorkReviewId = event.target.dataset.deleteWorkReview;

  if (openReviewId) openWorkReviewModal(openReviewId);
  if (openLightboxId) openLightbox(openLightboxId);

  if (deleteWorkId) {
    if (!window.confirm('Удалить работу из галереи?')) return;
    await api(`/api/admin/works/${deleteWorkId}`, { method: 'DELETE' });
    await Promise.all([loadWorks(), loadBootstrap()]);
    showToast('Работа удалена');
  }

  if (editWorkId) {
    const work = state.works.find((item) => String(item.id) === String(editWorkId));
    if (!work) return;
    const title = window.prompt('Название', work.title);
    if (!title) return;
    const description = window.prompt('Описание', work.description);
    if (!description) return;
    const allowed_reviewer_username = window.prompt('Username, который может оставить отзыв (без @)', work.allowed_reviewer_username || '');
    await api(`/api/admin/works/${editWorkId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description, allowed_reviewer_username }),
    });
    await loadWorks();
    showToast('Работа обновлена');
  }

  if (editWorkReviewId) {
    const review = state.works.flatMap((work) => work.reviews || []).find((item) => String(item.id) === editWorkReviewId);
    if (!review) return;
    const author_name = window.prompt('Имя автора', review.author_name);
    if (!author_name) return;
    const rating = Number(window.prompt('Оценка 1-5', review.rating));
    const text = window.prompt('Текст', review.text);
    if (!text) return;
    await api(`/api/admin/work-reviews/${editWorkReviewId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ author_name, rating, text }),
    });
    await Promise.all([loadWorks(), loadBootstrap()]);
    showToast('Отзыв к работе обновлён');
  }

  if (deleteWorkReviewId) {
    if (!window.confirm('Удалить отзыв к работе?')) return;
    await api(`/api/admin/work-reviews/${deleteWorkReviewId}`, { method: 'DELETE' });
    await Promise.all([loadWorks(), loadBootstrap()]);
    showToast('Отзыв к работе удалён');
  }
}

async function handleAdminDayAction(status) {
  const slot_date = new FormData(els.adminDayForm).get('slot_date');
  if (!slot_date) return showToast('Выбери дату');
  await api('/api/admin/availability/day', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slot_date, status }),
  });
  await loadAvailability(state.currentMonth.year, state.currentMonth.month);
  if (state.selectedDate === slot_date) await loadDaySlots(slot_date);
  showToast(status === 'available' ? 'День открыт' : 'День закрыт');
}

async function handleAdminSlotAction(status) {
  const formData = new FormData(els.adminSlotForm);
  const slot_date = formData.get('slot_date');
  const slot_time = formData.get('slot_time');
  if (!slot_date || !slot_time) return showToast('Выбери дату и время');
  await api('/api/admin/availability/slot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slot_date, slot_time, status }),
  });
  await loadAvailability(state.currentMonth.year, state.currentMonth.month);
  if (state.selectedDate === slot_date) await loadDaySlots(slot_date);
  showToast(status === 'available' ? 'Слот открыт' : 'Слот закрыт');
}

function bindForms() {
  els.reviewForm.addEventListener('submit', (event) => submitReview(event).catch(handleError));
  els.workReviewForm.addEventListener('submit', (event) => submitWorkReview(event).catch(handleError));
  els.bookingForm.addEventListener('submit', (event) => submitBooking(event).catch(handleError));
  els.adminWorkForm.addEventListener('submit', (event) => submitAdminWork(event).catch(handleError));

  const debouncedEstimate = debounce(() => updateEstimate(), 300);
  ['input', 'change'].forEach((eventName) => {
    els.sizeInput.addEventListener(eventName, debouncedEstimate);
    els.styleChoice.addEventListener(eventName, debouncedEstimate);
    els.colorMode.addEventListener(eventName, debouncedEstimate);
    els.bookingForm.service_location.addEventListener(eventName, debouncedEstimate);
    els.bodyPlaceInput.addEventListener(eventName, debouncedEstimate);
  });

  els.reviewsList.addEventListener('click', (event) => handleReviewActions(event).catch(handleError));
  els.worksGrid.addEventListener('click', (event) => handleWorksActions(event).catch(handleError));
  els.adminWorksList.addEventListener('click', (event) => handleWorksActions(event).catch(handleError));
  els.featuredWorks.addEventListener('click', (event) => handleWorksActions(event).catch(handleError));

  els.adminDayForm.querySelectorAll('[data-day-action]').forEach((button) => {
    button.addEventListener('click', () => handleAdminDayAction(button.dataset.dayAction).catch(handleError));
  });
  els.adminSlotForm.querySelectorAll('[data-slot-action]').forEach((button) => {
    button.addEventListener('click', () => handleAdminSlotAction(button.dataset.slotAction).catch(handleError));
  });
}

function bindCalendarControls() {
  els.prevMonthBtn?.addEventListener('click', async () => {
    const month = state.currentMonth.month === 1 ? 12 : state.currentMonth.month - 1;
    const year = state.currentMonth.month === 1 ? state.currentMonth.year - 1 : state.currentMonth.year;
    await loadAvailability(year, month).catch(handleError);
  });
  els.nextMonthBtn?.addEventListener('click', async () => {
    const month = state.currentMonth.month === 12 ? 1 : state.currentMonth.month + 1;
    const year = state.currentMonth.month === 12 ? state.currentMonth.year + 1 : state.currentMonth.year;
    await loadAvailability(year, month).catch(handleError);
  });
}

function bindMapButtons() {
  els.openYandexMapBtn?.addEventListener('click', openYandexMaps);
  els.contactYandexBtn?.addEventListener('click', openYandexMaps);
}

function bindModals() {
  document.querySelectorAll('[data-close-modal]').forEach((node) => node.addEventListener('click', closeWorkReviewModal));
  document.querySelectorAll('[data-close-lightbox]').forEach((node) => node.addEventListener('click', closeLightbox));
  document.querySelectorAll('[data-close-add-work]').forEach((node) => node.addEventListener('click', closeAddWorkModal));
  els.openAddWorkBtn?.addEventListener('click', openAddWorkModal);
}

function handleError(error) {
  console.error(error);
  showToast(error.message || 'Что-то пошло не так');
}

async function init() {
  setupTelegram();
  bindNavigation();
  bindForms();
  bindCalendarControls();
  bindMapButtons();
  bindModals();

  const now = new Date();
  state.currentMonth = { year: now.getFullYear(), month: now.getMonth() + 1 };

  try {
    await loadBootstrap();
    await Promise.all([loadWorks(), loadReviews()]);
    await loadAvailability(state.currentMonth.year, state.currentMonth.month);
    await updateEstimate();
    if (state.bootstrap?.user?.isAdmin) await loadAdminBookings();
  } catch (error) {
    handleError(error);
    const message = String(error?.message || '');
    if (message.toLowerCase().includes('авторизац')) {
      els.authHint?.classList.remove('hidden');
      switchPage('homePage');
    }
  }
}

init();
