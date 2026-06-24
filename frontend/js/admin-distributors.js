(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = { items: [] };

  function renderPage(container) {
    container.innerHTML =
      '<div id="page-alert"></div>' +
      '<div class="admin-card">' +
        '<h2 class="admin-import-block__title">Добавить дистрибьютора</h2>' +
        '<p class="admin-modal__meta">Название должно совпадать с колонкой «Дистрибьютор» в Excel при импорте пользователей и продаж.</p>' +
        '<div class="admin-toolbar">' +
          '<label class="field">' +
            '<span class="field__label">Название</span>' +
            '<input class="field__input" type="text" id="distributor-name" maxlength="255" placeholder="Например: ООО Торг-Сервис">' +
          "</label>" +
          '<button type="button" class="btn btn--primary btn--sm" id="distributor-add-btn">Добавить нового дистрибьютора</button>' +
        "</div>" +
      "</div>" +
      '<div class="admin-card">' +
        '<h2 class="admin-import-block__title">Список дистрибьюторов</h2>' +
        '<div id="distributors-table"><p class="admin-empty">Загрузка…</p></div>' +
      "</div>";

    document.getElementById("distributor-add-btn").addEventListener("click", addDistributor);
    document.getElementById("distributor-name").addEventListener("keydown", function (event) {
      if (event.key === "Enter") addDistributor();
    });

    loadDistributors();
  }

  function loadDistributors() {
    PlombirApi.get("/distributors/").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        L.showToast(
          document.getElementById("page-alert"),
          PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить список"),
          "error"
        );
        return;
      }
      state.items = (result.data.data || []).slice().sort(function (a, b) {
        return String(a.name || "").localeCompare(String(b.name || ""), "ru");
      });
      renderTable();
    }).catch(function () {
      L.showToast(document.getElementById("page-alert"), "Не удалось связаться с сервером", "error");
    });
  }

  function renderTable() {
    var host = document.getElementById("distributors-table");
    if (!state.items.length) {
      host.innerHTML = '<p class="admin-empty">Дистрибьюторов пока нет. Добавьте первого выше.</p>';
      return;
    }

    host.innerHTML =
      '<div class="admin-table-wrap">' +
        '<table class="admin-table">' +
          "<thead><tr><th>Название</th><th>Статус</th><th>Добавлен</th></tr></thead>" +
          "<tbody>" +
            state.items.map(function (item) {
              return (
                "<tr>" +
                  "<td><strong>" + L.escapeHtml(item.name) + "</strong></td>" +
                  "<td>" + (item.is_active ? "Активен" : "Неактивен") + "</td>" +
                  "<td>" + L.formatDate(item.created_at) + "</td>" +
                "</tr>"
              );
            }).join("") +
          "</tbody>" +
        "</table>" +
      "</div>";
  }

  function addDistributor() {
    var input = document.getElementById("distributor-name");
    var name = (input.value || "").trim();
    if (!name) {
      L.showToast(document.getElementById("page-alert"), "Введите название дистрибьютора", "error");
      return;
    }

    var exists = state.items.some(function (item) {
      return String(item.name || "").toLowerCase() === name.toLowerCase();
    });
    if (exists) {
      L.showToast(document.getElementById("page-alert"), "Дистрибьютор с таким названием уже есть", "error");
      return;
    }

    PlombirApi.post("/distributors/", { name: name, is_active: true }).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        L.showToast(
          document.getElementById("page-alert"),
          PlombirApi.extractErrorMessage(result.data, "Не удалось добавить дистрибьютора"),
          "error"
        );
        return;
      }
      input.value = "";
      L.showToast(document.getElementById("page-alert"), "Дистрибьютор «" + name + "» добавлен", "success");
      loadDistributors();
    }).catch(function () {
      L.showToast(document.getElementById("page-alert"), "Не удалось связаться с сервером", "error");
    });
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (!profile) return;
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "distributors",
      pageTitle: "Дистрибьюторы",
    });
    renderPage(content);
  });
})();
