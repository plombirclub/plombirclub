(function () {
  "use strict";

  var L = PlombirAdminLayout;

  var STATUS_LABELS = {
    verification_pending: "Ожидает подтверждения",
    placed: "Создана",
    confirmed: "Подтверждена",
    processing: "В работе",
    fulfilled: "Выполнена",
    rejected: "Отклонена",
    cancelled: "Отменена",
  };

  var NEXT_STATUSES = {
    verification_pending: ["placed", "cancelled"],
    placed: ["confirmed", "rejected"],
    confirmed: ["processing", "rejected"],
    processing: ["rejected"],
  };

  var state = { page: 1, totalPages: 1, status: "", selected: null };

  function statusBadge(status) {
    var cls = "admin-badge admin-badge--muted";
    if (status === "fulfilled") cls = "admin-badge admin-badge--ok";
    if (status === "rejected" || status === "cancelled") cls = "admin-badge admin-badge--danger";
    if (status === "processing" || status === "confirmed") cls = "admin-badge admin-badge--warn";
    return '<span class="' + cls + '">' + L.escapeHtml(STATUS_LABELS[status] || status) + "</span>";
  }

  function renderList(container) {
    container.innerHTML =
      '<div id="page-alert"></div>' +
      '<div class="admin-card">' +
        '<div class="admin-toolbar">' +
          '<label class="field field--sm">' +
            '<span class="field__label">Статус</span>' +
            '<select class="field__input" id="orders-status-filter">' +
              '<option value="">Все</option>' +
              Object.keys(STATUS_LABELS).map(function (key) {
                return '<option value="' + key + '"' + (state.status === key ? " selected" : "") + ">" +
                  L.escapeHtml(STATUS_LABELS[key]) + "</option>";
              }).join("") +
            "</select>" +
          "</label>" +
        "</div>" +
        '<div id="orders-table"><p class="admin-empty">Загрузка…</p></div>' +
        '<div class="admin-pagination" id="orders-pagination" hidden></div>' +
      "</div>";

    document.getElementById("orders-status-filter").addEventListener("change", function (event) {
      state.status = event.target.value;
      state.page = 1;
      loadOrders(container);
    });

    loadOrders(container);
  }

  function loadOrders(rootContainer) {
    var query = "?page=" + state.page + "&limit=20";
    if (state.status) query += "&status=" + encodeURIComponent(state.status);

    PlombirApi.get("/orders/all" + query).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки"), "error");
        return;
      }
      var data = result.data.data || {};
      var items = data.items || [];
      var pagination = data.pagination || {};
      state.totalPages = pagination.total_pages || 1;
      state.page = pagination.current_page || 1;

      var tableHost = document.getElementById("orders-table");
      if (!items.length) {
        tableHost.innerHTML = '<p class="admin-empty">Заявки не найдены</p>';
      } else {
        var rows = items.map(function (order) {
          return (
            "<tr data-order-id=\"" + order.id + "\">" +
              "<td>" + L.shortId(order.id) + "</td>" +
              "<td>" + L.formatDate(order.created_at) + "</td>" +
              "<td>" + L.escapeHtml(order.user_full_name || "—") + "<br><small>" + L.escapeHtml(order.user_email || "") + "</small></td>" +
              "<td>" + L.escapeHtml(order.prize_name || "—") + "</td>" +
              "<td>" + L.formatMoney(order.amount_rub) + "</td>" +
              "<td>" + statusBadge(order.status) + "</td>" +
            "</tr>"
          );
        }).join("");
        tableHost.innerHTML =
          '<div class="admin-table-wrap">' +
            '<table class="admin-table">' +
              "<thead><tr><th>№</th><th>Дата</th><th>Участник</th><th>Приз</th><th>Номинал</th><th>Статус</th></tr></thead>" +
              "<tbody>" + rows + "</tbody>" +
            "</table>" +
          "</div>";
        tableHost.querySelectorAll("tbody tr").forEach(function (row) {
          row.addEventListener("click", function () {
            openOrderModal(items.find(function (o) { return o.id === row.getAttribute("data-order-id"); }));
          });
        });
      }
      renderPagination(rootContainer);
    });
  }

  function renderPagination(rootContainer) {
    var pag = document.getElementById("orders-pagination");
    if (!pag) return;
    if (state.totalPages <= 1) {
      pag.hidden = true;
      return;
    }
    pag.hidden = false;
    pag.innerHTML =
      '<span class="admin-pagination__info">Страница ' + state.page + " из " + state.totalPages + "</span>" +
      '<div class="admin-pagination__actions">' +
        '<button type="button" class="btn btn--ghost btn--sm" id="orders-prev"' +
          (state.page <= 1 ? " disabled" : "") + ">Назад</button>" +
        '<button type="button" class="btn btn--ghost btn--sm" id="orders-next"' +
          (state.page >= state.totalPages ? " disabled" : "") + ">Вперёд</button>" +
      "</div>";
    document.getElementById("orders-prev").addEventListener("click", function () {
      if (state.page > 1) { state.page -= 1; loadOrders(rootContainer); }
    });
    document.getElementById("orders-next").addEventListener("click", function () {
      if (state.page < state.totalPages) { state.page += 1; loadOrders(rootContainer); }
    });
  }

  function openOrderModal(order) {
    if (!order) return;
    state.selected = order;
    var modal = document.getElementById("order-modal");
    var nextOptions = (NEXT_STATUSES[order.status] || []).map(function (st) {
      return '<option value="' + st + '">' + L.escapeHtml(STATUS_LABELS[st]) + "</option>";
    }).join("");

    var fulfillBlock = "";
    if (order.status === "processing") {
      if (order.prize_type === "certificate") {
        fulfillBlock =
          '<div class="admin-modal__section">' +
            '<h3 class="admin-modal__section-title">Выдача сертификата</h3>' +
            '<form id="order-fulfill-form" class="form-grid">' +
              '<label class="field"><span class="field__label">Промокод</span><input class="field__input" name="certificate_code"></label>' +
              '<label class="field"><span class="field__label">Ссылка</span><input class="field__input" name="certificate_url"></label>' +
              '<label class="field"><span class="field__label">URL файла</span><input class="field__input" name="certificate_file_url"></label>' +
              '<button type="submit" class="btn btn--primary btn--sm">Отметить выполненной</button>' +
            "</form>" +
          "</div>";
      } else {
        fulfillBlock =
          '<div class="admin-modal__section">' +
            '<h3 class="admin-modal__section-title">Фиксация СБП-выплаты</h3>' +
            '<form id="order-fulfill-form" class="form-grid">' +
              '<label class="field"><span class="field__label">Комментарий о выплате</span><input class="field__input" name="payout_comment"></label>' +
              '<label class="field"><span class="field__label">Номер операции</span><input class="field__input" name="payout_operation_id"></label>' +
              '<button type="submit" class="btn btn--primary btn--sm">Отметить выполненной</button>' +
            "</form>" +
          "</div>";
      }
    }

    modal.innerHTML =
      '<div class="admin-modal-backdrop" data-close="1"></div>' +
      '<div class="admin-modal admin-modal--wide" role="dialog" aria-modal="true">' +
        '<button type="button" class="admin-modal__close" data-close="1">&times;</button>' +
        '<h2 class="admin-modal__title">Заявка ' + L.shortId(order.id) + "</h2>" +
        '<p class="admin-modal__meta">' + L.escapeHtml(order.prize_name || "") + " · " + statusBadge(order.status) + "</p>" +
        '<div id="order-modal-alert"></div>' +
        '<div class="admin-detail-grid">' +
          detail("Участник", L.escapeHtml(order.user_full_name || "—") + " (" + L.escapeHtml(order.user_email || "") + ")") +
          detail("Номинал", L.formatMoney(order.amount_rub)) +
          detail("Баллы", String(order.points_spent)) +
          detail("ИНН", L.escapeHtml(order.inn || "—")) +
          detail("Телефон СБП", L.escapeHtml(order.payout_phone || "—")) +
          detail("Создана", L.formatDate(order.created_at)) +
        "</div>" +
        (order.admin_comment ? '<p class="admin-modal__meta"><strong>Комментарий:</strong> ' + L.escapeHtml(order.admin_comment) + "</p>" : "") +
        (order.fulfillment_data
          ? '<pre class="admin-import-result">' + L.escapeHtml(JSON.stringify(order.fulfillment_data, null, 2)) + "</pre>"
          : "") +
        (nextOptions
          ? '<div class="admin-modal__section">' +
              '<h3 class="admin-modal__section-title">Изменить статус</h3>' +
              '<form id="order-status-form" class="form-grid">' +
                '<label class="field"><span class="field__label">Новый статус</span><select class="field__input" name="status">' + nextOptions + "</select></label>" +
                '<label class="field"><span class="field__label">Комментарий</span><textarea class="field__input" name="comment" rows="2"></textarea></label>' +
                '<button type="submit" class="btn btn--secondary btn--sm">Сохранить статус</button>' +
              "</form>" +
            "</div>"
          : "") +
        fulfillBlock +
      "</div>";
    modal.hidden = false;
    bindOrderModal(order);
  }

  function detail(label, value) {
    return (
      '<div class="admin-detail-item">' +
        '<span class="admin-detail-item__label">' + label + "</span>" +
        '<span class="admin-detail-item__value">' + value + "</span>" +
      "</div>"
    );
  }

  function closeOrderModal() {
    var modal = document.getElementById("order-modal");
    modal.hidden = true;
    modal.innerHTML = "";
    state.selected = null;
  }

  function orderAlert(msg, type) {
    L.showToast(document.getElementById("order-modal-alert"), msg, type);
  }

  function bindOrderModal(order) {
    var modal = document.getElementById("order-modal");
    modal.querySelectorAll("[data-close]").forEach(function (el) {
      el.addEventListener("click", closeOrderModal);
    });

    var statusForm = document.getElementById("order-status-form");
    if (statusForm) {
      statusForm.addEventListener("submit", function (event) {
        event.preventDefault();
        var status = statusForm.status.value;
        var comment = statusForm.comment.value.trim() || null;
        if (status === "rejected" && !comment) {
          orderAlert("Укажите причину отклонения в комментарии", "error");
          return;
        }
        PlombirApi.put("/orders/" + order.id + "/status", { status: status, admin_comment: comment })
          .then(function (result) {
            if (!result.response.ok || !result.data || !result.data.success) {
              orderAlert(PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
              return;
            }
            closeOrderModal();
            loadOrders(document.getElementById("admin-content"));
          });
      });
    }

    var fulfillForm = document.getElementById("order-fulfill-form");
    if (fulfillForm) {
      fulfillForm.addEventListener("submit", function (event) {
        event.preventDefault();
        var body = {};
        if (order.prize_type === "certificate") {
          body.certificate_code = fulfillForm.certificate_code.value.trim() || null;
          body.certificate_url = fulfillForm.certificate_url.value.trim() || null;
          body.certificate_file_url = fulfillForm.certificate_file_url.value.trim() || null;
          if (!body.certificate_code && !body.certificate_url && !body.certificate_file_url) {
            orderAlert("Укажите промокод, ссылку или файл сертификата", "error");
            return;
          }
        } else {
          body.payout_comment = fulfillForm.payout_comment.value.trim() || null;
          body.payout_operation_id = fulfillForm.payout_operation_id.value.trim() || null;
          if (!body.payout_comment && !body.payout_operation_id) {
            orderAlert("Укажите комментарий или номер операции СБП", "error");
            return;
          }
        }
        PlombirApi.put("/orders/" + order.id + "/fulfill", body).then(function (result) {
          if (!result.response.ok || !result.data || !result.data.success) {
            orderAlert(PlombirApi.extractErrorMessage(result.data, "Ошибка выдачи"), "error");
            return;
          }
          closeOrderModal();
          loadOrders(document.getElementById("admin-content"));
        });
      });
    }
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (!profile) return;
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "orders",
      pageTitle: "Заявки",
    });
    renderList(content);
  });
})();
