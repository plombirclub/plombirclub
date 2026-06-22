(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = { page: 1, totalPages: 1, period: "" };

  function renderPage(container) {
    container.innerHTML =
      '<div id="page-alert"></div>' +
      '<div class="admin-card">' +
        '<p class="admin-modal__meta">Участники с баллами в статусе «ожидают активации». Пользователь активирует их сам в ЛК; администратор может активировать вручную в карточке пользователя.</p>' +
        '<div class="admin-toolbar">' +
          '<label class="field field--sm">' +
            '<span class="field__label">Период (YYYY-MM)</span>' +
            '<input class="field__input" type="text" id="points-period" placeholder="2026-06" value="' +
              L.escapeHtml(state.period) + '" pattern="\\d{4}-\\d{2}">' +
          "</label>" +
          '<button type="button" class="btn btn--secondary btn--sm" id="points-filter-btn">Применить</button>' +
          '<button type="button" class="btn btn--ghost btn--sm" id="points-reset-btn">Сбросить</button>' +
        "</div>" +
        '<div id="points-table"><p class="admin-empty">Загрузка…</p></div>' +
        '<div class="admin-pagination" id="points-pagination" hidden></div>' +
      "</div>";

    document.getElementById("points-filter-btn").addEventListener("click", function () {
      state.period = document.getElementById("points-period").value.trim();
      state.page = 1;
      loadData(container);
    });
    document.getElementById("points-reset-btn").addEventListener("click", function () {
      state.period = "";
      state.page = 1;
      document.getElementById("points-period").value = "";
      loadData(container);
    });

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
          return (
            "<tr>" +
              "<td>" + L.escapeHtml(item.full_name || "—") + "</td>" +
              "<td>" + L.escapeHtml(item.email) + "</td>" +
              "<td>" + L.escapeHtml(item.distributor_name || "—") + "</td>" +
              "<td><strong>" + Number(item.pending_amount).toLocaleString("ru-RU") + "</strong></td>" +
              "<td>" + item.pending_records + "</td>" +
              '<td><a class="admin-doc-link" href="/admin/users.html" onclick="sessionStorage.setItem(\'admin_open_user\',\'' +
                item.user_id + '\')">Открыть</a></td>' +
            "</tr>"
          );
        }).join("");
        tableHost.innerHTML =
          '<div class="admin-table-wrap">' +
            '<table class="admin-table">' +
              "<thead><tr><th>ФИО</th><th>Email</th><th>Дистрибьютор</th><th>Сумма pending</th><th>Записей</th><th></th></tr></thead>" +
              "<tbody>" + rows + "</tbody>" +
            "</table>" +
          "</div>";
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
