(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = { templates: [], selected: null };

  function loadTemplates() {
    return PlombirApi.get("/notifications/templates").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        throw new Error(PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки"));
      }
      state.templates = (result.data.data && result.data.data.items) || [];
    });
  }

  function renderList(container) {
    if (!state.templates.length) {
      container.innerHTML = '<div class="admin-card"><p class="admin-empty">Шаблоны не найдены</p></div>';
      return;
    }

    container.innerHTML =
      '<div class="admin-card">' +
        '<div class="admin-table-wrap"><table class="admin-table">' +
          "<thead><tr><th>Событие</th><th>Текст шаблона</th><th>Обновлён</th></tr></thead><tbody>" +
          state.templates.map(function (item) {
            var preview = (item.template_text || "").slice(0, 120);
            if ((item.template_text || "").length > 120) preview += "…";
            return (
              "<tr data-template-id=\"" + item.id + "\">" +
                "<td>" + L.escapeHtml(item.event_type) + "</td>" +
                "<td>" + L.escapeHtml(preview) + "</td>" +
                "<td>" + L.formatDate(item.updated_at || item.created_at) + "</td>" +
              "</tr>"
            );
          }).join("") +
          "</tbody></table></div>" +
        '<p class="admin-modal__meta">В тексте можно использовать плейсхолдеры в фигурных скобках, например {full_name}.</p>' +
      "</div>";

    container.querySelectorAll("tr[data-template-id]").forEach(function (row) {
      row.addEventListener("click", function () {
        openEditor(row.getAttribute("data-template-id"));
      });
    });
  }

  function openEditor(templateId) {
    var template = state.templates.find(function (t) { return t.id === templateId; });
    if (!template) return;
    state.selected = template;

    var panel = document.getElementById("notifications-editor");
    panel.hidden = false;
    panel.innerHTML =
      '<div class="admin-card" style="margin-top:1rem">' +
        '<h2 class="admin-import-block__title">' + L.escapeHtml(template.event_type) + "</h2>" +
        '<div id="template-alert"></div>' +
        '<label class="field"><span class="field__label">Текст уведомления</span>' +
          '<textarea class="admin-editor admin-editor--tall" id="template-text">' +
            L.escapeHtml(template.template_text || "") +
          "</textarea></label>" +
        '<div class="admin-modal__actions">' +
          '<button type="button" class="btn btn--ghost btn--sm" id="template-cancel">Отмена</button>' +
          '<button type="button" class="btn btn--primary btn--sm" id="template-save">Сохранить шаблон</button>' +
        "</div></div>";

    document.getElementById("template-cancel").addEventListener("click", function () {
      panel.hidden = true;
    });
    document.getElementById("template-save").addEventListener("click", function () {
      var text = document.getElementById("template-text").value.trim();
      if (!text) {
        L.showToast(document.getElementById("template-alert"), "Текст не может быть пустым", "error");
        return;
      }
      PlombirApi.put("/notifications/templates/" + template.id, { template_text: text }).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          L.showToast(document.getElementById("template-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
          return;
        }
        L.showToast(document.getElementById("page-alert"), "Шаблон сохранён", "success");
        loadTemplates().then(function () {
          renderList(document.getElementById("notifications-root"));
          panel.hidden = true;
        });
      });
    });
  }

  function init(profile) {
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "notifications",
      pageTitle: "Уведомления",
    });
    content.innerHTML =
      '<div id="page-alert"></div>' +
      '<div id="notifications-root"><p class="admin-empty">Загрузка…</p></div>' +
      '<div id="notifications-editor" hidden></div>';

    loadTemplates().then(function () {
      renderList(document.getElementById("notifications-root"));
    }).catch(function (err) {
      L.showToast(document.getElementById("page-alert"), err.message, "error");
    });
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (profile) init(profile);
  });
})();
