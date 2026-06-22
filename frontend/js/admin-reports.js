(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = { layout: [], reportPage: 1, reportTotalPages: 1, errorsPage: 1, errorsTotalPages: 1, tab: "crm" };

  function renderPage(container) {
    container.innerHTML =
      '<div id="page-alert"></div>' +
      '<div class="admin-tabs">' +
        '<button type="button" class="admin-tabs__btn admin-tabs__btn--active" data-tab="crm">CRM-отчёт</button>' +
        '<button type="button" class="admin-tabs__btn" data-tab="layout">Конструктор колонок</button>' +
        '<button type="button" class="admin-tabs__btn" data-tab="errors">Ошибки импорта</button>' +
      "</div>" +
      '<div id="reports-panel"></div>';

    container.querySelectorAll("[data-tab]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.tab = btn.getAttribute("data-tab");
        container.querySelectorAll(".admin-tabs__btn").forEach(function (el) {
          el.classList.toggle("admin-tabs__btn--active", el.getAttribute("data-tab") === state.tab);
        });
        renderPanel();
      });
    });
    renderPanel();
  }

  function renderPanel() {
    if (state.tab === "crm") renderCrm(document.getElementById("reports-panel"));
    else if (state.tab === "layout") renderLayout(document.getElementById("reports-panel"));
    else renderErrors(document.getElementById("reports-panel"));
  }

  function renderCrm(panel) {
    panel.innerHTML =
      '<div class="admin-card">' +
        '<div class="admin-toolbar">' +
          '<button type="button" class="btn btn--primary btn--sm" id="crm-download">Скачать Excel</button>' +
        "</div>" +
        '<div id="crm-table"><p class="admin-empty">Загрузка…</p></div>' +
        '<div class="admin-pagination" id="crm-pagination" hidden></div>' +
      "</div>";
    document.getElementById("crm-download").addEventListener("click", function () {
      PlombirApi.download("/reports/users/download", "crm-users-report.xlsx");
    });
    loadCrmReport();
  }

  function loadCrmReport() {
    PlombirApi.get("/reports/users?page=" + state.reportPage + "&limit=20").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
        return;
      }
      var data = result.data.data || {};
      var columns = data.columns || [];
      var items = data.items || [];
      state.reportTotalPages = (data.pagination && data.pagination.total_pages) || 1;
      var host = document.getElementById("crm-table");
      if (!items.length) {
        host.innerHTML = '<p class="admin-empty">Нет данных</p>';
        return;
      }
      host.innerHTML =
        '<div class="admin-table-wrap"><table class="admin-table"><thead><tr>' +
          columns.map(function (col) { return "<th>" + L.escapeHtml(col.label) + "</th>"; }).join("") +
          "</tr></thead><tbody>" +
          items.map(function (row) {
            return "<tr>" + columns.map(function (col) {
              return "<td>" + L.escapeHtml(row[col.id] != null ? String(row[col.id]) : "—") + "</td>";
            }).join("") + "</tr>";
          }).join("") +
          "</tbody></table></div>";
      renderCrmPagination();
    });
  }

  function renderCrmPagination() {
    var host = document.getElementById("crm-pagination");
    if (!host || state.reportTotalPages <= 1) { if (host) host.hidden = true; return; }
    host.hidden = false;
    host.innerHTML =
      '<button type="button" class="btn btn--ghost btn--sm"' + (state.reportPage <= 1 ? " disabled" : "") + ' id="crm-prev">Назад</button>' +
      '<span>Стр. ' + state.reportPage + " / " + state.reportTotalPages + "</span>" +
      '<button type="button" class="btn btn--ghost btn--sm"' + (state.reportPage >= state.reportTotalPages ? " disabled" : "") + ' id="crm-next">Вперёд</button>';
    document.getElementById("crm-prev").addEventListener("click", function () {
      if (state.reportPage > 1) { state.reportPage -= 1; loadCrmReport(); }
    });
    document.getElementById("crm-next").addEventListener("click", function () {
      if (state.reportPage < state.reportTotalPages) { state.reportPage += 1; loadCrmReport(); }
    });
  }

  function renderLayout(panel) {
    panel.innerHTML =
      '<div class="admin-card">' +
        '<p class="admin-modal__meta">Выберите колонки CRM-отчёта пользователей.</p>' +
        '<div class="admin-checklist" id="crm-layout-list"></div>' +
        '<div class="admin-modal__actions"><button type="button" class="btn btn--primary btn--sm" id="layout-save">Сохранить</button></div>' +
      "</div>";
    document.getElementById("crm-layout-list").innerHTML = state.layout.map(function (col, index) {
      return '<label><input type="checkbox" data-layout-index="' + index + '"' +
        (col.visible ? " checked" : "") + "> " + L.escapeHtml(col.label) + " (" + L.escapeHtml(col.id) + ")</label>";
    }).join("");
    document.getElementById("layout-save").addEventListener("click", function () {
      var updated = state.layout.map(function (col, index) {
        var checkbox = document.querySelector('[data-layout-index="' + index + '"]');
        return { id: col.id, label: col.label, visible: checkbox ? checkbox.checked : col.visible };
      });
      PlombirApi.put("/reports/layout", { layout: updated }).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
          return;
        }
        state.layout = result.data.data.layout || updated;
        L.showToast(document.getElementById("page-alert"), "Конструктор сохранён", "success");
      });
    });
  }

  function renderErrors(panel) {
    panel.innerHTML =
      '<div class="admin-card">' +
        '<div class="admin-toolbar"><button type="button" class="btn btn--primary btn--sm" id="errors-download">Скачать Excel</button></div>' +
        '<div id="errors-table"><p class="admin-empty">Загрузка…</p></div>' +
        '<div class="admin-pagination" id="errors-pagination" hidden></div>' +
      "</div>";
    document.getElementById("errors-download").addEventListener("click", function () {
      PlombirApi.download("/reports/sync-errors/download", "sync-errors.xlsx");
    });
    loadErrors();
  }

  function loadErrors() {
    PlombirApi.get("/reports/sync-errors?page=" + state.errorsPage + "&limit=20").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) return;
      var data = result.data.data || {};
      var items = data.items || [];
      state.errorsTotalPages = (data.pagination && data.pagination.total_pages) || 1;
      var host = document.getElementById("errors-table");
      if (!items.length) {
        host.innerHTML = '<p class="admin-empty">Ошибок импорта нет</p>';
        return;
      }
      host.innerHTML =
        '<div class="admin-table-wrap"><table class="admin-table">' +
          "<thead><tr><th>Тип</th><th>Строка</th><th>Ошибка</th><th>Дата</th></tr></thead><tbody>" +
          items.map(function (item) {
            return (
              "<tr>" +
                "<td>" + L.escapeHtml(item.import_type || "—") + "</td>" +
                "<td>" + L.escapeHtml(item.row_number != null ? String(item.row_number) : "—") + "</td>" +
                "<td>" + L.escapeHtml(item.error_message || "—") + "</td>" +
                "<td>" + L.formatDate(item.created_at) + "</td>" +
              "</tr>"
            );
          }).join("") +
          "</tbody></table></div>";
      renderErrorsPagination();
    });
  }

  function renderErrorsPagination() {
    var host = document.getElementById("errors-pagination");
    if (!host || state.errorsTotalPages <= 1) { if (host) host.hidden = true; return; }
    host.hidden = false;
    host.innerHTML =
      '<button type="button" class="btn btn--ghost btn--sm"' + (state.errorsPage <= 1 ? " disabled" : "") + ' id="errors-prev">Назад</button>' +
      '<span>Стр. ' + state.errorsPage + " / " + state.errorsTotalPages + "</span>" +
      '<button type="button" class="btn btn--ghost btn--sm"' + (state.errorsPage >= state.errorsTotalPages ? " disabled" : "") + ' id="errors-next">Вперёд</button>';
    document.getElementById("errors-prev").addEventListener("click", function () {
      if (state.errorsPage > 1) { state.errorsPage -= 1; loadErrors(); }
    });
    document.getElementById("errors-next").addEventListener("click", function () {
      if (state.errorsPage < state.errorsTotalPages) { state.errorsPage += 1; loadErrors(); }
    });
  }

  function init(profile) {
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "reports",
      pageTitle: "Отчёты",
    });
    content.innerHTML = '<div id="reports-root"><p class="admin-empty">Загрузка…</p></div>';
    PlombirApi.get("/reports/layout").then(function (result) {
      state.layout = (result.data && result.data.data && result.data.data.layout) || [];
      renderPage(document.getElementById("reports-root"));
    });
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (profile) init(profile);
  });
})();
