(function () {
  "use strict";

  var state = {
    profile: null,
    rewards: [],
    balanceAvailable: 0,
    activeReward: null,
    pendingOrder: null,
    selectedVerificationMethod: null,
  };

  var ERROR_TEXT = {
    amount: "Введите сумму от 1 до 10 тыс. руб. кратно 1 тыс. руб.",
    innCertificate: "Пожалуйста, укажите свой ИНН в профиле личного кабинета, загрузите фото свидетельства ИНН и дождитесь проверки документов администратором",
    innMoney: "Пожалуйста, укажите ИНН в профиле, загрузите фото свидетельства ИНН и дождитесь подтверждения администратором",
    kndNumber: "Пожалуйста, укажите номер справки КНД 1122035 в профиле",
    kndDoc: "Пожалуйста, загрузите фото справки КНД 1122035 в профиле",
    selfEmployed: "Пожалуйста, дождитесь подтверждения статуса самозанятого администратором",
  };

  function formatRub(value) {
    var num = Number(value || 0);
    if (isNaN(num)) num = 0;
    return num.toLocaleString("ru-RU") + " ₽";
  }

  function escape(value) {
    return PlombirLayout.escapeHtml(value || "");
  }

  function normalizePhone(phone) {
    var digits = String(phone || "").replace(/\D/g, "");
    if (digits.length === 11 && digits.charAt(0) === "8") {
      digits = "7" + digits.slice(1);
    }
    return digits;
  }

  function isValidAmount(amount) {
    if (!amount || amount < 1000 || amount > 10000) return false;
    return amount % 1000 === 0;
  }

  function parseAmount(value) {
    var normalized = String(value || "").replace(/[^\d]/g, "");
    if (!normalized) return 0;
    return Number(normalized);
  }

  function renderShell() {
    return (
      '<section class="catalog-page">' +
        '<div id="catalog-alert"></div>' +
        '<div class="catalog-summary">' +
          '<article class="summary-card">' +
            '<p class="summary-card__label">Доступно для обмена</p>' +
            '<p class="summary-card__value" id="summary-balance">0 ₽</p>' +
          "</article>" +
          '<article class="summary-card">' +
            '<p class="summary-card__label">Курс обмена</p>' +
            '<p class="summary-card__value">1 балл = 1 рубль</p>' +
          "</article>" +
        "</div>" +
        '<div id="catalog-grid" class="catalog-grid">' +
          '<p class="catalog-empty">Загружаем каталог призов…</p>' +
        "</div>" +
      "</section>" +
      '<div id="modal-root" class="modal-root" hidden></div>'
    );
  }

  function renderCards() {
    var grid = document.getElementById("catalog-grid");
    if (!grid) return;

    if (!state.rewards.length) {
      grid.innerHTML = '<p class="catalog-empty">Пока нет доступных призов.</p>';
      return;
    }

    grid.innerHTML = state.rewards
      .map(function (reward) {
        var isMoney = reward.type === "money";
        var badge = isMoney ? "Получение по СБП" : "Электронный сертификат";
        var button = isMoney ? "Получить по СБП" : "Получить";
        var imageHtml = reward.image_url
          ? '<img src="' + escape(reward.image_url) + '" alt="' + escape(reward.name) + '">'
          : '<p class="reward-card__placeholder">Изображение будет добавлено администратором</p>';

        return (
          '<article class="reward-card">' +
            '<div class="reward-card__media">' +
              imageHtml +
              '<span class="reward-card__badge' + (isMoney ? " reward-card__badge--money" : "") + '">' + badge + "</span>" +
            "</div>" +
            '<div class="reward-card__body">' +
              '<h2 class="reward-card__title">' + escape(reward.name) + "</h2>" +
              '<p class="reward-card__description">' + escape(reward.description || "Обменяйте баллы на приз из каталога.") + "</p>" +
              '<div class="reward-card__footer">' +
                '<button type="button" class="btn btn--primary reward-action" data-reward-id="' + escape(reward.id) + '">' + button + "</button>" +
              "</div>" +
            "</div>" +
          "</article>"
        );
      })
      .join("");

    grid.querySelectorAll(".reward-action").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var rewardId = btn.getAttribute("data-reward-id");
        var reward = state.rewards.find(function (item) {
          return item.id === rewardId;
        });
        if (reward) openRequestModal(reward);
      });
    });
  }

  function renderRequestForm(reward) {
    var isMoney = reward.type === "money";
    var title = isMoney ? "Получить по СБП" : "Получить сертификат";
    var submitLabel = isMoney ? "Получить на банковскую карту" : "Получить сертификат";
    var imageHtml = reward.image_url
      ? '<div class="modal__image-wrap"><img src="' + escape(reward.image_url) + '" alt="' + escape(reward.name) + '"></div>'
      : "";

    return (
      '<div class="modal-backdrop" data-close-modal="1"></div>' +
      '<section class="modal" role="dialog" aria-modal="true" aria-label="' + escape(title) + '">' +
        '<div class="modal__content">' +
          '<h2 class="modal__title">' + escape(reward.name) + "</h2>" +
          imageHtml +
          '<p class="modal__desc">' + escape(reward.description || "") + "</p>" +
          '<p class="modal__balance">Доступно баллов: ' + escape(formatRub(state.balanceAvailable)) + "</p>" +
          '<div id="modal-alert"></div>' +
          '<label class="field">' +
            '<span class="field__label">Номинал, руб.</span>' +
            '<input id="request-amount" class="field__input" type="number" min="1000" max="10000" step="1000" placeholder="Например, 3000">' +
          "</label>" +
          '<p class="modal__hint">Введите сумму от 1 до 10 тыс. руб. кратно 1 тыс. руб.</p>' +
          (isMoney
            ? '<label class="field">' +
                '<span class="field__label">Телефон СБП</span>' +
                '<input id="request-phone" class="field__input" type="tel" inputmode="tel" placeholder="+7 (___) ___-__-__">' +
              "</label>" +
              '<p class="modal__hint">Введите свой номер телефона, привязанный к банковской карте СБП</p>'
            : "") +
          '<div class="modal__actions">' +
            '<button type="button" class="btn btn--secondary" data-close-modal="1">Отмена</button>' +
            '<button type="button" class="btn btn--primary" id="modal-continue">' + submitLabel + "</button>" +
          "</div>" +
        "</div>" +
      "</section>"
    );
  }

  function renderConfirmStep(amount) {
    return (
      '<div class="modal-backdrop" data-close-modal="1"></div>' +
      '<section class="modal" role="dialog" aria-modal="true" aria-label="Подтверждение заявки">' +
        '<div class="modal__content">' +
          '<h2 class="modal__title">Подтверждение заявки</h2>' +
          '<p class="modal__desc">Вы создаете заявку на обмен ' + escape(formatRub(amount)) + ". Вы уверены?</p>" +
          '<div id="modal-alert"></div>' +
          '<div class="modal__actions">' +
            '<button type="button" class="btn btn--secondary" id="confirm-no">Нет</button>' +
            '<button type="button" class="btn btn--primary" id="confirm-yes">Да</button>' +
          "</div>" +
        "</div>" +
      "</section>"
    );
  }

  function renderVerificationStep() {
    return (
      '<div class="modal-backdrop" data-close-modal="1"></div>' +
      '<section class="modal" role="dialog" aria-modal="true" aria-label="Подтверждение телефона">' +
        '<div class="modal__content">' +
          '<h2 class="modal__title">Подтверждение телефона СБП</h2>' +
          '<p class="modal__desc">Телефон выплаты отличается от телефона в профиле. Подтвердите новый номер через SMS или email.</p>' +
          '<div id="modal-alert"></div>' +
          '<div class="modal__actions">' +
            '<button type="button" class="btn btn--secondary" id="send-sms-code">Отправить код по SMS</button>' +
            '<button type="button" class="btn btn--secondary" id="send-email-code">Отправить код на email</button>' +
          "</div>" +
          '<div class="modal__divider"></div>' +
          '<label class="field">' +
            '<span class="field__label">Код подтверждения</span>' +
            '<input id="verification-code" class="field__input" type="text" inputmode="numeric" maxlength="6" placeholder="6 цифр">' +
          "</label>" +
          '<button type="button" class="btn btn--primary" id="verify-code">Подтвердить код</button>' +
          '<button type="button" class="btn btn--secondary" data-close-modal="1">Закрыть</button>' +
        "</div>" +
      "</section>"
    );
  }

  function modalRoot() {
    return document.getElementById("modal-root");
  }

  function bindModalClose() {
    var root = modalRoot();
    if (!root) return;
    root.querySelectorAll("[data-close-modal]").forEach(function (el) {
      el.addEventListener("click", function () {
        closeModal();
      });
    });
  }

  function openModal(html) {
    var root = modalRoot();
    if (!root) return;
    root.hidden = false;
    root.innerHTML = html;
    bindModalClose();
  }

  function closeModal() {
    var root = modalRoot();
    if (!root) return;
    root.hidden = true;
    root.innerHTML = "";
    state.activeReward = null;
    state.pendingOrder = null;
    state.selectedVerificationMethod = null;
  }

  function openRequestModal(reward) {
    state.activeReward = reward;
    openModal(renderRequestForm(reward));
    var nextBtn = document.getElementById("modal-continue");
    if (!nextBtn) return;
    nextBtn.addEventListener("click", function () {
      var amountInput = document.getElementById("request-amount");
      var phoneInput = document.getElementById("request-phone");
      var amount = parseAmount(amountInput ? amountInput.value : 0);
      var payoutPhone = phoneInput ? String(phoneInput.value || "") : "";
      var validationError = validateBeforeConfirm(reward, amount, payoutPhone);
      if (validationError) {
        PlombirLayout.showAlert(document.getElementById("modal-alert"), validationError, "error");
        return;
      }

      state.pendingOrder = {
        amount: amount,
        payoutPhone: payoutPhone,
      };
      openConfirmModal();
    });
  }

  function validateBeforeConfirm(reward, amount, payoutPhone) {
    if (!isValidAmount(amount)) return ERROR_TEXT.amount;
    if (!reward || !reward.is_active) return "Выбранный сертификат временно недоступен";
    if (amount > state.balanceAvailable) {
      return "Недостаточно баллов. Доступно: " + formatRub(state.balanceAvailable) + ", требуется: " + formatRub(amount);
    }

    if (!state.profile || !state.profile.inn_verified_by_admin) {
      return reward.type === "money" ? ERROR_TEXT.innMoney : ERROR_TEXT.innCertificate;
    }

    if (reward.type !== "money") return null;

    if (!payoutPhone.trim()) return "Введите свой номер телефона, привязанный к банковской карте СБП";
    var normalized = normalizePhone(payoutPhone);
    if (normalized.length !== 11 || normalized.charAt(0) !== "7") {
      return "Введите корректный номер телефона СБП";
    }
    if (!state.profile.knd_1122035_number) return ERROR_TEXT.kndNumber;
    if (!state.profile.knd_1122035_document_path) return ERROR_TEXT.kndDoc;
    if (!state.profile.is_self_employed) return ERROR_TEXT.selfEmployed;
    return null;
  }

  function openConfirmModal() {
    if (!state.pendingOrder) return;
    openModal(renderConfirmStep(state.pendingOrder.amount));
    var yes = document.getElementById("confirm-yes");
    var no = document.getElementById("confirm-no");
    if (no) {
      no.addEventListener("click", function () {
        if (state.activeReward) openRequestModal(state.activeReward);
      });
    }
    if (yes) {
      yes.addEventListener("click", submitOrder);
    }
  }

  function submitOrder() {
    if (!state.activeReward || !state.pendingOrder) return;
    var payload = {
      prize_id: state.activeReward.id,
      amount_rub: state.pendingOrder.amount,
    };
    if (state.activeReward.type === "money") {
      payload.payout_phone = state.pendingOrder.payoutPhone;
    }

    var yes = document.getElementById("confirm-yes");
    if (yes) yes.disabled = true;

    PlombirApi.post("/orders", payload).then(function (result) {
      if (yes) yes.disabled = false;
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          document.getElementById("modal-alert"),
          PlombirApi.extractErrorMessage(result.data, "Не удалось создать заявку"),
          "error"
        );
        return;
      }

      var order = result.data.data || {};
      if (order.status === "verification_pending" || order.requires_phone_verification) {
        state.pendingOrder = { requestId: order.id };
        openVerificationModal();
        return;
      }

      closeModal();
      showPageAlert("Заявка успешно создана. Она уже доступна в разделе «Профиль → Мои заявки».", "success");
      loadBalance();
    });
  }

  function openVerificationModal() {
    openModal(renderVerificationStep());

    var smsBtn = document.getElementById("send-sms-code");
    var emailBtn = document.getElementById("send-email-code");
    var verifyBtn = document.getElementById("verify-code");

    if (smsBtn) {
      smsBtn.addEventListener("click", function () {
        sendVerificationCode("sms");
      });
    }
    if (emailBtn) {
      emailBtn.addEventListener("click", function () {
        sendVerificationCode("email");
      });
    }
    if (verifyBtn) {
      verifyBtn.addEventListener("click", verifyCode);
    }
  }

  function sendVerificationCode(method) {
    if (!state.pendingOrder || !state.pendingOrder.requestId) return;
    state.selectedVerificationMethod = method;
    PlombirApi.post("/orders/confirm-code", {
      request_id: state.pendingOrder.requestId,
      method: method,
      code: null,
    }).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          document.getElementById("modal-alert"),
          PlombirApi.extractErrorMessage(result.data, "Не удалось отправить код"),
          "error"
        );
        return;
      }

      var responseData = result.data.data || {};
      var successMessage = "Код отправлен. Введите 6 цифр для подтверждения.";
      if (responseData.debug_code) {
        successMessage += " Тестовый код: " + responseData.debug_code;
      }
      PlombirLayout.showAlert(document.getElementById("modal-alert"), successMessage, "success");
    });
  }

  function verifyCode() {
    if (!state.pendingOrder || !state.pendingOrder.requestId) return;
    if (!state.selectedVerificationMethod) {
      PlombirLayout.showAlert(document.getElementById("modal-alert"), "Сначала выберите способ отправки кода", "error");
      return;
    }

    var codeInput = document.getElementById("verification-code");
    var code = codeInput ? String(codeInput.value || "").replace(/\D/g, "") : "";
    if (code.length !== 6) {
      PlombirLayout.showAlert(document.getElementById("modal-alert"), "Введите код из 6 цифр", "error");
      return;
    }

    PlombirApi.post("/orders/confirm-code", {
      request_id: state.pendingOrder.requestId,
      method: state.selectedVerificationMethod,
      code: code,
    }).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          document.getElementById("modal-alert"),
          PlombirApi.extractErrorMessage(result.data, "Не удалось подтвердить код"),
          "error"
        );
        return;
      }

      closeModal();
      showPageAlert("Телефон подтвержден. Заявка создана и отправлена в обработку.", "success");
      loadBalance();
    });
  }

  function showPageAlert(message, type) {
    PlombirLayout.showAlert(document.getElementById("catalog-alert"), message, type || "info");
  }

  function fetchRewardsPage(page, acc, done) {
    PlombirApi.get("/rewards/?page=" + page + "&limit=20").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        done(new Error(PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить каталог")));
        return;
      }

      var data = result.data.data || {};
      var items = data.items || [];
      var pagination = data.pagination || {};
      var totalPages = pagination.total_pages || 1;
      var merged = acc.concat(items);

      if (page >= totalPages) {
        done(null, merged);
        return;
      }

      fetchRewardsPage(page + 1, merged, done);
    });
  }

  function loadRewards() {
    fetchRewardsPage(1, [], function (error, items) {
      if (error) {
        showPageAlert(error.message || "Не удалось загрузить каталог призов", "error");
        var grid = document.getElementById("catalog-grid");
        if (grid) grid.innerHTML = '<p class="catalog-empty">Не удалось загрузить каталог призов.</p>';
        return;
      }
      state.rewards = items || [];
      renderCards();
    });
  }

  function loadBalance() {
    PlombirApi.get("/points/balance").then(function (result) {
      var summary = document.getElementById("summary-balance");
      if (!summary) return;
      if (!result.response.ok || !result.data || !result.data.success) {
        summary.textContent = "—";
        return;
      }
      var balance = result.data.data || {};
      state.balanceAvailable = Number(balance.available || 0);
      summary.textContent = formatRub(state.balanceAvailable);
    });
  }

  function init(profile) {
    state.profile = profile;
    var root = PlombirLayout.mountLayout({
      mode: "full",
      profile: profile,
      activeMenuId: "catalog",
      pageTitle: "Каталог призов",
    });
    if (!root) return;
    root.innerHTML = renderShell();
    loadBalance();
    loadRewards();
  }

  PlombirAuth.requireAuth().then(function (profile) {
    if (profile) init(profile);
  });
})();
