(function () {
  "use strict";

  var STATUS_LABELS = {
    verification_pending: "Ожидает подтверждения телефона",
    placed: "Создана",
    confirmed: "Подтверждена",
    processing: "В работе",
    fulfilled: "Выполнена",
    rejected: "Отклонена",
    cancelled: "Отменена",
  };

  var PRIZE_TYPE_LABELS = {
    certificate: "Электронный сертификат",
    money: "Платеж на карту (СБП)",
  };

  var state = {
    profile: null,
    legalDocs: null,
    ordersPage: 1,
    ordersTotalPages: 1,
    activeTab: "profile",
  };

  var AGREEMENT_ITEMS = [
    { key: "personal_data", fallback: "Согласие на обработку персональных данных (ФЗ-152)" },
    { key: "program_rules", fallback: "Пользовательское соглашение" },
    { key: "email_notifications", fallback: "Согласие на получение email-уведомлений" },
  ];

  function initials(profile) {
    return PlombirLayout.userInitials(profile);
  }

  function formatDate(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatMoney(value) {
    var num = Number(value);
    if (isNaN(num)) return "—";
    return num.toLocaleString("ru-RU") + " ₽";
  }

  function formatPhone(phone) {
    if (!phone) return "—";
    var digits = String(phone).replace(/\D/g, "");
    if (digits.length === 11 && digits.charAt(0) === "7") {
      return "+7 (" + digits.slice(1, 4) + ") " + digits.slice(4, 7) + "-" + digits.slice(7, 9) + "-" + digits.slice(9);
    }
    return phone;
  }

  function shortOrderId(id) {
    if (!id) return "—";
    return String(id).slice(0, 8).toUpperCase();
  }

  function innBadge(profile) {
    if (profile.inn_verified_by_admin) {
      return '<span class="field__badge field__badge--ok">ИНН подтверждён</span>';
    }
    if (profile.inn_locked && profile.inn) {
      return '<span class="field__badge field__badge--pending">ИНН на проверке</span>';
    }
    return '<span class="field__badge field__badge--muted">ИНН не указан</span>';
  }

  function selfEmployedClass(profile) {
    return profile.is_self_employed ? "profile-avatar__status profile-avatar__status--ok" : "profile-avatar__status profile-avatar__status--warn";
  }

  function resolveTabFromHash() {
    var hash = (window.location.hash || "").replace("#", "");
    return hash === "orders" ? "orders" : "profile";
  }

  function setActiveTab(tab, pushHash) {
    state.activeTab = tab;
    if (pushHash) {
      var newHash = tab === "orders" ? "#orders" : "#profile";
      if (window.location.hash !== newHash) {
        history.replaceState(null, "", window.location.pathname + newHash);
      }
    }

    document.querySelectorAll(".profile-tabs__btn").forEach(function (btn) {
      btn.classList.toggle("profile-tabs__btn--active", btn.getAttribute("data-tab") === tab);
    });
    document.querySelectorAll(".profile-panel").forEach(function (panel) {
      panel.classList.toggle("profile-panel--active", panel.getAttribute("data-panel") === tab);
    });

    if (tab === "orders") loadOrders(true);
  }

  function formatDateShort(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  function agreementTitle(key) {
    var docs = (state.legalDocs && state.legalDocs.documents) || {};
    var item = docs[key] || {};
    var found = AGREEMENT_ITEMS.find(function (entry) { return entry.key === key; });
    return item.title || (found && found.fallback) || "Документ";
  }

  function renderAgreementsSection(profile) {
    if (!profile.agreements_accepted && !profile.is_registration_complete) return "";

    var acceptedAt = formatDateShort(profile.agreements_accepted_at || profile.updated_at);
    var rows = AGREEMENT_ITEMS.map(function (entry) {
      var title = agreementTitle(entry.key);
      return (
        '<li class="profile-agreements__item">' +
          '<span class="profile-agreements__mark" aria-hidden="true">✓</span>' +
          '<div class="profile-agreements__body">' +
            '<a class="profile-agreements__link" href="/pages/agreement.html?doc=' + entry.key + '">' +
              PlombirLayout.escapeHtml(title) +
            "</a>" +
            '<p class="profile-agreements__meta">Принято: ' + PlombirLayout.escapeHtml(acceptedAt) + "</p>" +
          "</div>" +
        "</li>"
      );
    }).join("");

    return (
      '<div class="profile-agreements">' +
        '<h2 class="profile-section__title">Принятые согласия</h2>' +
        '<p class="profile-section__hint">Документы, которые вы подтвердили при первом входе в личный кабинет.</p>' +
        '<ul class="profile-agreements__list">' + rows + "</ul>" +
      "</div>"
    );
  }

  function renderProfileForm(profile) {
    var innLocked = profile.inn_locked;
    var kndLocked = profile.knd_1122035_locked;
    var nameLocked = profile.personal_name_locked;
    var innDocDone = !!profile.inn_document_path;
    var kndDocDone = !!profile.knd_1122035_document_path;

    return (
      '<div class="profile-layout">' +
        '<aside class="profile-avatar panel-block">' +
          '<div class="profile-avatar__circle" aria-hidden="true">' + PlombirLayout.escapeHtml(initials(profile)) + "</div>" +
          '<p class="' + selfEmployedClass(profile) + '">' + PlombirLayout.escapeHtml(profile.self_employed_status_label || "") + "</p>" +
          (profile.distributor_name
            ? '<p class="profile-section__hint">' + PlombirLayout.escapeHtml(profile.distributor_name) + "</p>"
            : "") +
        "</aside>" +
        '<div class="panel-block">' +
          '<div id="profile-alert"></div>' +
          '<form id="profile-form" class="profile-section" novalidate>' +
            '<h2 class="profile-section__title">Основные данные</h2>' +
            '<p class="profile-section__hint">Фамилия, имя и отчество можно сохранить только один раз. После сохранения изменить их может только администратор. Поле «Ф.И.О.» заполняется при регистрации и не редактируется.</p>' +
            '<div class="profile-form-grid profile-form-grid--2">' +
              field("last_name", "Фамилия", profile.last_name, false, "text", nameLocked) +
              field("first_name", "Имя", profile.first_name, false, "text", nameLocked) +
              field("middle_name", "Отчество", profile.middle_name, false, "text", nameLocked) +
              field("full_name", "Ф.И.О.", profile.full_name, true) +
              field("email", "Email", profile.email, true) +
              field("phone", "Телефон", formatPhone(profile.phone), true) +
              field("participant_code", "Код участника", profile.participant_code || "—", true) +
              field("participant_position", "Должность", profile.participant_position || "—", true) +
            "</div>" +
            '<div class="profile-section" style="margin-top:1rem">' +
              '<h2 class="profile-section__title">ИНН и документы</h2>' +
              '<p class="profile-section__hint">ИНН и справку КНД можно сохранить только один раз. После сохранения изменить их может только администратор.</p>' +
              '<div class="profile-form-grid profile-form-grid--2">' +
                '<div class="field">' +
                  '<label class="field__label" for="inn">ИНН (12 цифр)</label>' +
                  innBadge(profile) +
                  '<input class="field__input" id="inn" name="inn" type="text" inputmode="numeric" maxlength="12" ' +
                    'value="' + PlombirLayout.escapeHtml(profile.inn || "") + '" ' +
                    (innLocked ? "disabled" : 'placeholder="12 цифр"') + ">" +
                "</div>" +
                '<div class="field file-upload">' +
                  '<span class="field__label">Фото свидетельства ИНН</span>' +
                  (innDocDone
                    ? '<p class="file-upload__status file-upload__status--done">Файл загружен</p>'
                    : '<p class="file-upload__status">JPG, PNG или PDF до 20 МБ</p>') +
                  (innDocDone || innLocked
                    ? ""
                    : '<input class="field__input" id="inn-photo" type="file" accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf">') +
                "</div>" +
                '<div class="field">' +
                  '<label class="field__label" for="knd">Номер справки КНД 1122035</label>' +
                  '<input class="field__input" id="knd" name="knd_1122035_number" type="text" inputmode="numeric" maxlength="20" ' +
                    'value="' + PlombirLayout.escapeHtml(profile.knd_1122035_number || "") + '" ' +
                    (kndLocked ? "disabled" : 'placeholder="Только цифры"') + ">" +
                "</div>" +
                '<div class="field file-upload">' +
                  '<span class="field__label">Фото справки КНД 1122035</span>' +
                  (kndDocDone
                    ? '<p class="file-upload__status file-upload__status--done">Файл загружен</p>'
                    : '<p class="file-upload__status">JPG, PNG или PDF до 20 МБ</p>') +
                  (kndDocDone || kndLocked
                    ? ""
                    : '<input class="field__input" id="knd-photo" type="file" accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf">') +
                "</div>" +
              "</div>" +
            "</div>" +
            '<div class="profile-actions">' +
              '<button type="submit" class="btn btn--primary" id="profile-save">Сохранить</button>' +
            "</div>" +
          "</form>" +
          '<div class="password-panel">' +
            '<button type="button" class="btn btn--secondary password-panel__toggle" id="password-toggle">Сменить пароль</button>' +
            '<form id="password-form" class="password-panel__form">' +
              field("current_password", "Текущий пароль", "", false, "password") +
              field("new_password", "Новый пароль", "", false, "password") +
              field("confirm_password", "Повторите новый пароль", "", false, "password") +
              '<div class="profile-actions">' +
                '<button type="submit" class="btn btn--primary">Обновить пароль</button>' +
              "</div>" +
            "</form>" +
          "</div>" +
          renderAgreementsSection(profile) +
        "</div>" +
      "</div>"
    );
  }

  function field(name, label, value, readonly, type, disabled) {
    type = type || "text";
    var id = "field-" + name;
    var attrs = "";
    if (readonly) attrs += "readonly ";
    if (disabled) attrs += "disabled ";
    return (
      '<div class="field">' +
        '<label class="field__label" for="' + id + '">' + PlombirLayout.escapeHtml(label) + "</label>" +
        '<input class="field__input" id="' + id + '" name="' + name + '" type="' + type + '" ' +
          attrs +
          'value="' + PlombirLayout.escapeHtml(value || "") + '">' +
      "</div>"
    );
  }

  function renderOrdersPanel() {
    return (
      '<div class="panel-block">' +
        '<div id="orders-alert"></div>' +
        '<h2 class="profile-section__title">Мои заявки</h2>' +
        '<p class="profile-section__hint">История заявок на сертификаты и выплаты по СБП.</p>' +
        '<div id="orders-list" class="orders-list">' +
          '<p class="orders-empty">Загрузка заявок…</p>' +
        "</div>" +
        '<div id="orders-pagination" class="orders-pagination" hidden></div>' +
      "</div>"
    );
  }

  function renderShell(profile) {
    return (
      '<div class="profile-page">' +
        '<nav class="profile-tabs" aria-label="Разделы профиля">' +
          '<button type="button" class="profile-tabs__btn profile-tabs__btn--active" data-tab="profile">Основные данные</button>' +
          '<button type="button" class="profile-tabs__btn" data-tab="orders">Мои заявки</button>' +
        "</nav>" +
        '<section class="profile-panel profile-panel--active" data-panel="profile">' +
          renderProfileForm(profile) +
        "</section>" +
        '<section class="profile-panel" data-panel="orders">' +
          renderOrdersPanel() +
        "</section>" +
      "</div>"
    );
  }

  function renderOrderCard(order) {
    var status = order.status || "";
    var statusLabel = STATUS_LABELS[status] || status;
    var prizeType = PRIZE_TYPE_LABELS[order.prize_type] || order.prize_type || "—";
    var rows = [
      detailRow("Тип", prizeType),
      detailRow("Номинал", formatMoney(order.amount_rub)),
      detailRow("Баллы", formatMoney(order.points_spent)),
      detailRow("Создана", formatDate(order.created_at)),
      detailRow("Изменена", formatDate(order.updated_at)),
    ];

    if (order.prize_type === "money" && order.payout_phone) {
      rows.push(detailRow("Телефон СБП", formatPhone(order.payout_phone)));
    }

    if (order.admin_comment) {
      var commentLabel = status === "rejected" ? "Причина отклонения" : "Комментарий администратора";
      rows.push(detailRow(commentLabel, order.admin_comment, true));
    }

    var fulfillmentHtml = "";
    if (order.status === "fulfilled" && order.fulfillment_data) {
      fulfillmentHtml = renderFulfillment(order);
    }

    return (
      '<article class="order-card">' +
        '<div class="order-card__head">' +
          '<div>' +
            '<h3 class="order-card__title">' + PlombirLayout.escapeHtml(order.prize_name || "Приз") + "</h3>" +
            '<p class="order-card__number">Заявка № ' + PlombirLayout.escapeHtml(shortOrderId(order.id)) + "</p>" +
          "</div>" +
          '<span class="order-status order-status--' + PlombirLayout.escapeHtml(status) + '">' +
            PlombirLayout.escapeHtml(statusLabel) +
          "</span>" +
        "</div>" +
        '<div class="order-details">' + rows.join("") + "</div>" +
        fulfillmentHtml +
      "</article>"
    );
  }

  function detailRow(label, value, full) {
    return (
      '<p class="order-details__row' + (full ? " order-details__full" : "") + '">' +
        '<span class="order-details__label">' + PlombirLayout.escapeHtml(label) + ": </span>" +
        '<span class="order-details__value">' + PlombirLayout.escapeHtml(String(value)) + "</span>" +
      "</p>"
    );
  }

  function renderFulfillment(order) {
    var data = order.fulfillment_data || {};
    var lines = [];

    if (order.prize_type === "certificate") {
      if (data.certificate_code) lines.push(detailRow("Промокод", data.certificate_code, true));
      if (data.certificate_url) {
        lines.push(
          '<p class="order-details__row order-details__full">' +
            '<span class="order-details__label">Ссылка: </span>' +
            '<a class="order-fulfillment__link" href="' + PlombirLayout.escapeHtml(data.certificate_url) + '" target="_blank" rel="noopener noreferrer">' +
              PlombirLayout.escapeHtml(data.certificate_url) +
            "</a>" +
          "</p>"
        );
      }
      if (data.certificate_file_url) {
        lines.push(
          '<p class="order-details__row order-details__full">' +
            '<span class="order-details__label">Файл сертификата: </span>' +
            '<a class="order-fulfillment__link" href="' + PlombirLayout.escapeHtml(data.certificate_file_url) + '" target="_blank" rel="noopener noreferrer">Скачать</a>' +
          "</p>"
        );
      }
    } else {
      if (data.payout_operation_id) lines.push(detailRow("Номер операции", data.payout_operation_id, true));
      if (data.payout_comment) lines.push(detailRow("Комментарий о выплате", data.payout_comment, true));
    }

    if (!lines.length) return "";

    return (
      '<div class="order-fulfillment">' +
        '<p class="order-fulfillment__title">Данные выдачи</p>' +
        '<div class="order-details">' + lines.join("") + "</div>" +
      "</div>"
    );
  }

  function bindProfileEvents(profile) {
    var form = document.getElementById("profile-form");
    var alertBox = document.getElementById("profile-alert");

    document.querySelectorAll(".profile-tabs__btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setActiveTab(btn.getAttribute("data-tab"), true);
      });
    });

    if (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        saveProfile(profile, alertBox);
      });
    }

    bindDocumentUpload("inn-photo", "inn_photo", alertBox);
    bindDocumentUpload("knd-photo", "knd_1122035_photo", alertBox);

    var passwordToggle = document.getElementById("password-toggle");
    var passwordForm = document.getElementById("password-form");
    if (passwordToggle && passwordForm) {
      passwordToggle.addEventListener("click", function () {
        passwordForm.classList.toggle("password-panel__form--open");
      });
      passwordForm.addEventListener("submit", function (event) {
        event.preventDefault();
        changePassword(passwordForm, alertBox);
      });
    }
  }

  function bindDocumentUpload(inputId, documentType, alertBox) {
    var input = document.getElementById(inputId);
    if (!input) return;

    input.addEventListener("change", function () {
      if (!input.files || !input.files[0]) return;
      PlombirLayout.clearAlert(alertBox);

      var formData = new FormData();
      formData.append("document_type", documentType);
      formData.append("file", input.files[0]);

      input.disabled = true;
      PlombirApi.post("/users/upload-document", formData).then(function (result) {
        input.disabled = false;
        if (result.response.ok && result.data && result.data.success) {
          state.profile = result.data.data.profile;
          refreshProfilePanel();
          PlombirLayout.showAlert(document.getElementById("profile-alert"), "Документ успешно загружен", "success");
        } else {
          input.value = "";
          PlombirLayout.showAlert(alertBox, PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить файл"), "error");
        }
      });
    });
  }

  function saveProfile(profile, alertBox) {
    PlombirLayout.clearAlert(alertBox);

    var payload = {};

    if (!profile.personal_name_locked) {
      var lastName = val("last_name");
      var firstName = val("first_name");
      var middleName = val("middle_name");
      if (lastName || firstName || middleName) {
        payload.last_name = lastName;
        payload.first_name = firstName;
        payload.middle_name = middleName;
      }
    }

    if (!profile.inn_locked) {
      var inn = val("inn").replace(/\D/g, "");
      if (inn) payload.inn = inn;
    }
    if (!profile.knd_1122035_locked) {
      var knd = val("knd_1122035_number").replace(/\D/g, "");
      if (knd) payload.knd_1122035_number = knd;
    }

    var saveBtn = document.getElementById("profile-save");
    if (saveBtn) saveBtn.disabled = true;

    PlombirApi.put("/users/profile", payload).then(function (result) {
      if (saveBtn) saveBtn.disabled = false;
      if (result.response.ok && result.data && result.data.success) {
        state.profile = result.data.data;
        refreshProfilePanel();
        PlombirLayout.updateUserDisplay(state.profile);
        PlombirLayout.showAlert(document.getElementById("profile-alert"), "Данные профиля сохранены", "success");
      } else {
        PlombirLayout.showAlert(alertBox, PlombirApi.extractErrorMessage(result.data, "Не удалось сохранить профиль"), "error");
      }
    });
  }

  function changePassword(form, alertBox) {
    PlombirLayout.clearAlert(alertBox);
    var current = form.querySelector('[name="current_password"]').value;
    var next = form.querySelector('[name="new_password"]').value;
    var confirm = form.querySelector('[name="confirm_password"]').value;

    if (!current || !next) {
      PlombirLayout.showAlert(alertBox, "Заполните текущий и новый пароль", "error");
      return;
    }
    if (next !== confirm) {
      PlombirLayout.showAlert(alertBox, "Новый пароль и подтверждение не совпадают", "error");
      return;
    }
    if (next.length < 8) {
      PlombirLayout.showAlert(alertBox, "Новый пароль должен быть не короче 8 символов", "error");
      return;
    }

    PlombirApi.post("/auth/change_password", {
      current_password: current,
      new_password: next,
    }).then(function (result) {
      if (result.response.ok && result.data && result.data.success) {
        form.reset();
        PlombirLayout.showAlert(alertBox, "Пароль успешно изменён", "success");
      } else {
        PlombirLayout.showAlert(alertBox, PlombirApi.extractErrorMessage(result.data, "Не удалось сменить пароль"), "error");
      }
    });
  }

  function val(name) {
    var el = document.querySelector('[name="' + name + '"]');
    return el ? el.value.trim() : "";
  }

  function refreshProfilePanel() {
    var panel = document.querySelector('.profile-panel[data-panel="profile"]');
    if (!panel || !state.profile) return;
    panel.innerHTML = renderProfileForm(state.profile);
    bindProfileEvents(state.profile);
  }

  function loadOrders(reset) {
    var list = document.getElementById("orders-list");
    var pagination = document.getElementById("orders-pagination");
    var alertBox = document.getElementById("orders-alert");
    if (!list) return;

    if (reset) {
      state.ordersPage = 1;
      list.innerHTML = '<p class="orders-empty">Загрузка заявок…</p>';
      if (pagination) pagination.hidden = true;
    }

    PlombirApi.get("/orders/my?page=" + state.ordersPage + "&limit=10").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        if (alertBox) {
          PlombirLayout.showAlert(alertBox, PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить заявки"), "error");
        }
        list.innerHTML = '<p class="orders-empty">Не удалось загрузить заявки</p>';
        return;
      }

      var data = result.data.data;
      var items = data.items || [];
      var pg = data.pagination || {};
      state.ordersTotalPages = pg.total_pages || 1;

      if (reset) list.innerHTML = "";

      if (!items.length && state.ordersPage === 1) {
        list.innerHTML = '<p class="orders-empty">У вас пока нет заявок. Оформить приз можно в разделе «Каталог призов».</p>';
        if (pagination) pagination.hidden = true;
        return;
      }

      items.forEach(function (order) {
        list.insertAdjacentHTML("beforeend", renderOrderCard(order));
      });

      if (pagination) {
        if (state.ordersPage < state.ordersTotalPages) {
          pagination.hidden = false;
          pagination.innerHTML = '<button type="button" class="btn btn--secondary" id="orders-load-more">Показать ещё</button>';
          document.getElementById("orders-load-more").addEventListener("click", function () {
            state.ordersPage += 1;
            loadOrders(false);
          });
        } else {
          pagination.hidden = true;
        }
      }
    });
  }

  function loadLegalDocuments() {
    return PlombirApi.get("/content/legal_documents").then(function (result) {
      if (result.response.ok && result.data && result.data.success) {
        state.legalDocs = result.data.data.value || { documents: {} };
      }
    });
  }

  function init(profile) {
    state.profile = profile;
    state.activeTab = resolveTabFromHash();

    var contentRoot = PlombirLayout.mountLayout({
      mode: "full",
      profile: profile,
      activeMenuId: "profile",
      pageTitle: "Профиль",
    });
    if (!contentRoot) return;

    loadLegalDocuments().finally(function () {
      contentRoot.innerHTML = renderShell(state.profile);
      bindProfileEvents(state.profile);
      setActiveTab(state.activeTab, false);
    });

    window.addEventListener("hashchange", function () {
      setActiveTab(resolveTabFromHash(), false);
    });
  }

  PlombirAuth.requireAuth().then(function (profile) {
    if (profile) init(profile);
  });
})();
