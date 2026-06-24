(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = { page: 1, totalPages: 1, period: "" };

  function previousMonth() {
    var now = new Date();
    var d = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    var month = String(d.getMonth() + 1).padStart(2, "0");
    return d.getFullYear() + "-" + month;
  }

  function periodLabel(period) {
    var parts = String(period || "").split("-");
    if (parts.length !== 2) return period || "";
    var monthNames = [
      "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
      "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ];
    var idx = Number(parts[1]) - 1;
    if (idx < 0 || idx > 11) return period;
    return monthNames[idx] + " " + parts[0];
  }

  function renderPage(container) {
    if (!state.period) state.period = previousMonth();
    container.innerHTML =
      '<div id="page-alert"></div>' +
      '<div class="admin-card">' +
        '<p class="admin-modal__meta">Участники с pending-баллами за предыдущий месяц. Задача и уведомление отправляются только после нажатия кнопки админом.</p>' +
        '<div class="admin-toolbar">' +
          '<p class="admin-modal__meta"><strong>Период:</strong> ' + L.escapeHtml(periodLabel(state.period)) + "</p>" +
        "</div>" +
        '<div id="points-table"><p class="admin-empty">Загрузка…</p></div>' +
        '<div class="admin-pagination" id="points-pagination" hidden></div>' +
      "</div>";

    loadData(container);
  }

  function loadData(rootContainer) {
    var query = "?page=" + state.page + "&limit=20&sort_by=pending_amount&sort_order=desc";
    if (state.period) query += "&period_month=" + encodeURIComponent(state.period);

    PlombirApi.get("/points/pending-activation" + query).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки"), "error");
        return;
      }
      var data = result.data.data || {};
      var items = data.items || [];
      var pagination = data.pagination || {};
      state.totalPages = pagination.total_pages || 1;
      state.page = pagination.current_page || 1;

      var tableHost = document.getElementById("points-table");
      if (!items.length) {
        tableHost.innerHTML = '<p class="admin-empty">Нет участников с ожидающими активацией баллами</p>';
      } else {
        var rows = items.map(function (item) {
          var sendDisabled = item.activation_task_sent ? " disabled" : "";
          var sendLabel = item.activation_task_sent ? "Уже отправлено" : "Отправить задачу на активацию";
          var sentMeta = item.activation_task_sent_at
            ? '<div class="admin-micro">' + L.escapeHtml("Отправлено: " + L.formatDate(item.activation_task_sent_at)) + "</div>"
            : "";
          return (
            "<tr>" +
              "<td>" + L.escapeHtml(item.full_name || "—") + "</td>" +
              "<td>" + L.escapeHtml(item.email) + "</td>" +
              "<td>" + L.escapeHtml(item.distributor_name || "—") + "</td>" +
              "<td><strong>" + Number(item.pending_amount).toLocaleString("ru-RU") + "</strong></td>" +
              "<td>" + item.pending_records + "</td>" +
              "<td>" +
                '<button type="button" class="btn btn--secondary btn--sm points-send-task" data-user-id="' +
                  item.user_id + '"' + sendDisabled + ">" + sendLabel + "</button>" +
                sentMeta +
              "</td>" +
            "</tr>"
          );
        }).join("");
        tableHost.innerHTML =
          '<div class="admin-table-wrap">' +
            '<table class="admin-table">' +
              "<thead><tr><th>ФИО</th><th>Email</th><th>Дистрибьютор</th><th>Сумма pending</th><th>Записей</th><th>Действие</th></tr></thead>" +
              "<tbody>" + rows + "</tbody>" +
            "</table>" +
          "</div>";
        tableHost.querySelectorAll(".points-send-task").forEach(function (btn) {
          btn.addEventListener("click", function () {
            sendActivationTask(btn.getAttribute("data-user-id"), rootContainer);
          });
        });
      }

      renderPagination(rootContainer);
    });
  }

  function renderPagination(rootContainer) {
    var pag = document.getElementById("points-pagination");
    if (!pag) return;
    if (state.totalPages <= 1) {
      pag.hidden = true;
      return;
    }
    pag.hidden = false;
    pag.innerHTML =
      '<span class="admin-pagination__info">Страница ' + state.page + " из " + state.totalPages + "</span>" +
      '<div class="admin-pagination__actions">' +
        '<button type="button" class="btn btn--ghost btn--sm" id="points-prev"' +
          (state.page <= 1 ? " disabled" : "") + ">Назад</button>" +
        '<button type="button" class="btn btn--ghost btn--sm" id="points-next"' +
          (state.page >= state.totalPages ? " disabled" : "") + ">Вперёд</button>" +
      "</div>";

    document.getElementById("points-prev").addEventListener("click", function () {
      if (state.page > 1) {
        state.page -= 1;
        loadData(rootContainer);
      }
    });
    document.getElementById("points-next").addEventListener("click", function () {
      if (state.page < state.totalPages) {
        state.page += 1;
        loadData(rootContainer);
      }
    });
  }

  function sendActivationTask(userId, rootContainer) {
    var alertBox = document.getElementById("page-alert");
    PlombirApi.post("/users/" + userId + "/send-activation-task", { period_month: state.period })
      .then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          L.showToast(
            alertBox,
            PlombirApi.extractErrorMessage(result.data, "Не удалось отправить задачу"),
            "error"
          );
          return;
        }
        var data = result.data.data || {};
        var msg = data.already_sent
          ? "Задача уже была отправлена ранее"
          : "Задача и уведомление успешно отправлены";
        L.showToast(alertBox, msg, "success");
        loadData(rootContainer);
      });
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (!profile) return;
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "points",
      pageTitle: "Баллы",
    });
    renderPage(content);

    var openUserId = sessionStorage.getItem("admin_open_user");
    if (openUserId) {
      sessionStorage.removeItem("admin_open_user");
    }
  });
})();
