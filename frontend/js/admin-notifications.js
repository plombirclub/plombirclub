(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = {
    templates: [],
    emailTemplates: [],
    selected: null,
    selectedEmail: null,
  };

  function loadTemplates() {
    return PlombirApi.get("/notifications/templates").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        throw new Error(PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки"));
      }
      state.templates = (result.data.data && result.data.data.items) || [];
    });
  }

  function loadEmailTemplates() {
    return PlombirApi.get("/notifications/email-templates").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        throw new Error(PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки email-шаблонов"));
      }
      state.emailTemplates = (result.data.data && result.data.data.items) || [];
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

  function renderEmailList(container) {
    if (!state.emailTemplates.length) {
      container.innerHTML = '<div class="admin-card"><p class="admin-empty">Email-шаблоны не найдены</p></div>';
      return;
    }

    container.innerHTML =
      '<div class="admin-card">' +
        '<div class="admin-table-wrap"><table class="admin-table">' +
          "<thead><tr><th>Письмо</th><th>Тема</th><th>Текст</th><th>Обновлён</th></tr></thead><tbody>" +
          state.emailTemplates.map(function (item) {
            var preview = (item.template_text || "").slice(0, 100);
            if ((item.template_text || "").length > 100) preview += "…";
            return (
              "<tr data-email-template-id=\"" + item.id + "\">" +
                "<td>" + L.escapeHtml(item.event_label || item.event_type) + "</td>" +
                "<td>" + L.escapeHtml(item.subject || "") + "</td>" +
                "<td>" + L.escapeHtml(preview) + "</td>" +
                "<td>" + L.formatDate(item.updated_at) + "</td>" +
              "</tr>"
            );
          }).join("") +
          "</tbody></table></div>" +
        '<p class="admin-modal__meta">Плейсхолдеры подставляются автоматически при отправке письма.</p>' +
      "</div>";

    container.querySelectorAll("tr[data-email-template-id]").forEach(function (row) {
      row.addEventListener("click", function () {
        openEmailEditor(row.getAttribute("data-email-template-id"));
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

  function openEmailEditor(templateId) {
    var template = state.emailTemplates.find(function (t) { return t.id === templateId; });
    if (!template) return;
    state.selectedEmail = template;

    var panel = document.getElementById("email-editor");
    panel.hidden = false;
    panel.innerHTML =
      '<div class="admin-card" style="margin-top:1rem">' +
        '<h2 class="admin-import-block__title">' + L.escapeHtml(template.event_label || template.event_type) + "</h2>" +
        '<p class="admin-modal__meta">Доступные плейсхолдеры: ' + L.escapeHtml(template.placeholders || "") + "</p>" +
        '<div id="email-template-alert"></div>' +
        '<label class="field"><span class="field__label">Тема письма</span>' +
          '<input class="field__input" id="email-template-subject" value="' +
            L.escapeHtml(template.subject || "") +
          '"></label>' +
        '<label class="field"><span class="field__label">Текст письма</span>' +
          '<textarea class="admin-editor admin-editor--tall" id="email-template-text">' +
            L.escapeHtml(template.template_text || "") +
          "</textarea></label>" +
        '<div class="admin-modal__actions">' +
          '<button type="button" class="btn btn--ghost btn--sm" id="email-template-cancel">Отмена</button>' +
          '<button type="button" class="btn btn--primary btn--sm" id="email-template-save">Сохранить письмо</button>' +
        "</div></div>";

    document.getElementById("email-template-cancel").addEventListener("click", function () {
      panel.hidden = true;
    });
    document.getElementById("email-template-save").addEventListener("click", function () {
      var subject = document.getElementById("email-template-subject").value.trim();
      var text = document.getElementById("email-template-text").value.trim();
      if (!subject || !text) {
        L.showToast(document.getElementById("email-template-alert"), "Заполните тему и текст", "error");
        return;
      }
      PlombirApi.put("/notifications/email-templates/" + template.id, {
        subject: subject,
        template_text: text,
      }).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          L.showToast(document.getElementById("email-template-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
          return;
        }
        L.showToast(document.getElementById("page-alert"), "Email-шаблон сохранён", "success");
        loadEmailTemplates().then(function () {
          renderEmailList(document.getElementById("email-templates-root"));
          panel.hidden = true;
        });
      });
    });
  }

  function init(profile) {
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "notifications",
      pageTitle: "Уведомления и email",
    });
    content.innerHTML =
      '<div id="page-alert"></div>' +
      '<h2 class="admin-import-block__title">Уведомления в личном кабинете</h2>' +
      '<div id="notifications-root"><p class="admin-empty">Загрузка…</p></div>' +
      '<div id="notifications-editor" hidden></div>' +
      '<h2 class="admin-import-block__title" style="margin-top:2rem">Email-письма участникам</h2>' +
      '<p class="admin-modal__meta">Эти тексты уходят на почту: импорт, коды, восстановление пароля, СБП.</p>' +
      '<div id="email-templates-root"><p class="admin-empty">Загрузка…</p></div>' +
      '<div id="email-editor" hidden></div>';

    Promise.all([loadTemplates(), loadEmailTemplates()]).then(function () {
      renderList(document.getElementById("notifications-root"));
      renderEmailList(document.getElementById("email-templates-root"));
    }).catch(function (err) {
      L.showToast(document.getElementById("page-alert"), err.message, "error");
    });
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (profile) init(profile);
  });
})();
