(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = { tab: "admin", page: 1, totalPages: 1 };

  function renderPage(container) {
    container.innerHTML =
      '<div id="page-alert"></div>' +
      '<div class="admin-tabs">' +
        '<button type="button" class="admin-tabs__btn admin-tabs__btn--active" data-tab="admin">Действия админа</button>' +
        '<button type="button" class="admin-tabs__btn" data-tab="system">Системные</button>' +
        '<button type="button" class="admin-tabs__btn" data-tab="user">Действия пользователей</button>' +
        '<button type="button" class="admin-tabs__btn" data-tab="parser">Парсер</button>' +
      "</div>" +
      '<div id="logs-panel"><p class="admin-empty">Загрузка…</p></div>' +
      '<div class="admin-pagination" id="logs-pagination" hidden></div>';

    container.querySelectorAll("[data-tab]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.tab = btn.getAttribute("data-tab");
        state.page = 1;
        container.querySelectorAll(".admin-tabs__btn").forEach(function (el) {
          el.classList.toggle("admin-tabs__btn--active", el.getAttribute("data-tab") === state.tab);
        });
        loadLogs();
      });
    });
    loadLogs();
  }

  function endpointForTab() {
    if (state.tab === "admin") return "/logs/admin";
    if (state.tab === "system") return "/logs/system";
    if (state.tab === "user") return "/logs/user-actions";
    return "/parser/logs";
  }

  function loadLogs() {
    var path = endpointForTab() + "?page=" + state.page + "&limit=20";
    PlombirApi.get(path).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
        return;
      }
      var data = result.data.data || {};
      var items = data.items || [];
      state.totalPages = (data.pagination && data.pagination.total_pages) || 1;
      var host = document.getElementById("logs-panel");
      if (!items.length) {
        host.innerHTML = '<p class="admin-empty">Записей нет</p>';
      } else if (state.tab === "admin") {
        host.innerHTML = renderAdminTable(items);
      } else if (state.tab === "system" || state.tab === "parser") {
        host.innerHTML = renderSystemTable(items);
      } else {
        host.innerHTML = renderUserTable(items);
      }
      renderPagination();
    });
  }

  function renderAdminTable(items) {
    return (
      '<div class="admin-table-wrap"><table class="admin-table">' +
        "<thead><tr><th>Дата</th><th>Админ</th><th>Действие</th><th>Сущность</th></tr></thead><tbody>" +
        items.map(function (item) {
          return (
            "<tr>" +
              "<td>" + L.formatDate(item.created_at) + "</td>" +
              "<td>" + L.escapeHtml(item.admin_email || item.admin_name || "—") + "</td>" +
              "<td>" + L.escapeHtml(item.action) + "</td>" +
              "<td>" + L.escapeHtml(item.entity_type) + (item.entity_id ? " · " + L.shortId(item.entity_id) : "") + "</td>" +
            "</tr>"
          );
        }).join("") +
        "</tbody></table></div>"
    );
  }

  function renderSystemTable(items) {
    return (
      '<div class="admin-table-wrap"><table class="admin-table">' +
        "<thead><tr><th>Дата</th><th>Уровень</th><th>Источник</th><th>Сообщение</th></tr></thead><tbody>" +
        items.map(function (item) {
          return (
            "<tr>" +
              "<td>" + L.formatDate(item.created_at) + "</td>" +
              "<td>" + L.escapeHtml(item.level || "—") + "</td>" +
              "<td>" + L.escapeHtml(item.source || "—") + "</td>" +
              "<td>" + L.escapeHtml(item.message || "—") + "</td>" +
            "</tr>"
          );
        }).join("") +
        "</tbody></table></div>"
    );
  }

  function renderUserTable(items) {
    return (
      '<div class="admin-table-wrap"><table class="admin-table">' +
        "<thead><tr><th>Дата</th><th>Пользователь</th><th>Действие</th><th>IP</th></tr></thead><tbody>" +
        items.map(function (item) {
          return (
            "<tr>" +
              "<td>" + L.formatDate(item.created_at) + "</td>" +
              "<td>" + L.escapeHtml(item.user_email || item.user_name || "—") + "</td>" +
              "<td>" + L.escapeHtml(item.action) + "</td>" +
              "<td>" + L.escapeHtml(item.ip_address || "—") + "</td>" +
            "</tr>"
          );
        }).join("") +
        "</tbody></table></div>"
    );
  }

  function renderPagination() {
    var host = document.getElementById("logs-pagination");
    if (!host) return;
    if (state.totalPages <= 1) { host.hidden = true; return; }
    host.hidden = false;
    host.innerHTML =
      '<button type="button" class="btn btn--ghost btn--sm"' + (state.page <= 1 ? " disabled" : "") + ' id="logs-prev">Назад</button>' +
      '<span>Стр. ' + state.page + " / " + state.totalPages + "</span>" +
      '<button type="button" class="btn btn--ghost btn--sm"' + (state.page >= state.totalPages ? " disabled" : "") + ' id="logs-next">Вперёд</button>';
    document.getElementById("logs-prev").addEventListener("click", function () {
      if (state.page > 1) { state.page -= 1; loadLogs(); }
    });
    document.getElementById("logs-next").addEventListener("click", function () {
      if (state.page < state.totalPages) { state.page += 1; loadLogs(); }
    });
  }

  function init(profile) {
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "logs",
      pageTitle: "Логи",
    });
    content.innerHTML = '<div id="logs-root"></div>';
    renderPage(document.getElementById("logs-root"));
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (profile) init(profile);
  });
})();
