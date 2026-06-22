(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = { tab: "faq", faq: { items: [] }, instructions: { title: "", content: "", items: [] }, support: {} };

  function renderTabs(container) {
    var tabs = [
      { id: "faq", label: "FAQ" },
      { id: "instructions", label: "Инструкции" },
      { id: "support", label: "Контакты поддержки" },
    ];
    container.innerHTML =
      '<div id="page-alert"></div>' +
      '<div class="admin-tabs">' +
        tabs.map(function (tab) {
          var cls = "admin-tabs__btn" + (state.tab === tab.id ? " admin-tabs__btn--active" : "");
          return '<button type="button" class="' + cls + '" data-tab="' + tab.id + '">' + tab.label + "</button>";
        }).join("") +
      "</div>" +
      '<div id="content-panel"></div>';

    container.querySelectorAll("[data-tab]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.tab = btn.getAttribute("data-tab");
        renderTabs(container);
        renderPanel();
      });
    });
    renderPanel();
  }

  function renderPanel() {
    var panel = document.getElementById("content-panel");
    if (state.tab === "faq") renderFaq(panel);
    else if (state.tab === "instructions") renderInstructions(panel);
    else renderSupport(panel);
  }

  function renderFaq(panel) {
    panel.innerHTML =
      '<div class="admin-card">' +
        '<div class="admin-toolbar"><button type="button" class="btn btn--primary btn--sm" id="faq-add">Добавить вопрос</button>' +
        '<button type="button" class="btn btn--primary btn--sm" id="faq-save">Сохранить FAQ</button></div>' +
        '<div id="faq-items"></div></div>';
    renderFaqItems();
    document.getElementById("faq-add").addEventListener("click", function () {
      state.faq.items.push({ id: String(Date.now()), question: "", answer: "", sort_order: state.faq.items.length, is_published: true });
      renderFaqItems();
    });
    document.getElementById("faq-save").addEventListener("click", saveFaq);
  }

  function renderFaqItems() {
    var host = document.getElementById("faq-items");
    if (!host) return;
    if (!state.faq.items.length) {
      host.innerHTML = '<p class="admin-empty">Вопросов пока нет</p>';
      return;
    }
    host.innerHTML = state.faq.items.map(function (item, index) {
      return (
        '<div class="admin-card" style="margin-top:0.75rem">' +
          '<label class="field"><span class="field__label">Вопрос</span><input class="field__input" data-faq-field="question" data-index="' + index + '" value="' +
            L.escapeHtml(item.question) + '"></label>' +
          '<label class="field"><span class="field__label">Ответ</span><textarea class="admin-editor" data-faq-field="answer" data-index="' + index + '">' +
            L.escapeHtml(item.answer) + "</textarea></label>" +
          '<button type="button" class="btn btn--danger btn--sm" data-faq-remove="' + index + '">Удалить</button>' +
        "</div>"
      );
    }).join("");

    host.querySelectorAll("[data-faq-field]").forEach(function (el) {
      el.addEventListener("input", function () {
        var idx = Number(el.getAttribute("data-index"));
        state.faq.items[idx][el.getAttribute("data-faq-field")] = el.value;
      });
    });
    host.querySelectorAll("[data-faq-remove]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.faq.items.splice(Number(btn.getAttribute("data-faq-remove")), 1);
        renderFaqItems();
      });
    });
  }

  function saveFaq() {
    PlombirApi.put("/content/faq", { value: state.faq }).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
        return;
      }
      state.faq = result.data.data.value;
      L.showToast(document.getElementById("page-alert"), "FAQ сохранён", "success");
    });
  }

  function renderInstructions(panel) {
    panel.innerHTML =
      '<div class="admin-card admin-form-grid">' +
        '<label class="field"><span class="field__label">Заголовок</span><input class="field__input" id="instr-title" value="' +
          L.escapeHtml(state.instructions.title || "") + '"></label>' +
        '<label class="field"><span class="field__label">Вводный текст</span><textarea class="admin-editor admin-editor--tall" id="instr-content">' +
          L.escapeHtml(state.instructions.content || "") + "</textarea></label>" +
        '<div class="admin-toolbar"><button type="button" class="btn btn--primary btn--sm" id="instr-add">Добавить пункт</button>' +
        '<button type="button" class="btn btn--primary btn--sm" id="instr-save">Сохранить</button></div>' +
        '<div id="instr-items"></div></div>';
    renderInstructionItems();
    document.getElementById("instr-add").addEventListener("click", function () {
      state.instructions.items.push({ id: String(Date.now()), title: "", description: "", sort_order: state.instructions.items.length, is_published: true });
      renderInstructionItems();
    });
    document.getElementById("instr-save").addEventListener("click", function () {
      state.instructions.title = document.getElementById("instr-title").value.trim();
      state.instructions.content = document.getElementById("instr-content").value.trim();
      PlombirApi.put("/content/instructions", { value: state.instructions }).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
          return;
        }
        state.instructions = result.data.data.value;
        L.showToast(document.getElementById("page-alert"), "Инструкции сохранены", "success");
      });
    });
  }

  function renderInstructionItems() {
    var host = document.getElementById("instr-items");
    if (!host) return;
    host.innerHTML = (state.instructions.items || []).map(function (item, index) {
      return (
        '<div class="admin-card" style="margin-top:0.75rem">' +
          '<label class="field"><span class="field__label">Заголовок</span><input class="field__input" data-instr-field="title" data-index="' + index + '" value="' +
            L.escapeHtml(item.title) + '"></label>' +
          '<label class="field"><span class="field__label">Описание</span><textarea class="admin-editor" data-instr-field="description" data-index="' + index + '">' +
            L.escapeHtml(item.description || "") + "</textarea></label>" +
          '<button type="button" class="btn btn--danger btn--sm" data-instr-remove="' + index + '">Удалить</button>' +
        "</div>"
      );
    }).join("") || '<p class="admin-empty">Пункты не добавлены</p>';

    host.querySelectorAll("[data-instr-field]").forEach(function (el) {
      el.addEventListener("input", function () {
        var idx = Number(el.getAttribute("data-index"));
        state.instructions.items[idx][el.getAttribute("data-instr-field")] = el.value;
      });
    });
    host.querySelectorAll("[data-instr-remove]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.instructions.items.splice(Number(btn.getAttribute("data-instr-remove")), 1);
        renderInstructionItems();
      });
    });
  }

  function renderSupport(panel) {
    var s = state.support;
    panel.innerHTML =
      '<div class="admin-card admin-form-grid admin-form-grid--2">' +
        '<label class="field"><span class="field__label">Телефон</span><input class="field__input" id="support-phone" value="' + L.escapeHtml(s.phone || "") + '"></label>' +
        '<label class="field"><span class="field__label">Email</span><input class="field__input" id="support-email" value="' + L.escapeHtml(s.email || "") + '"></label>' +
        '<label class="field"><span class="field__label">Время работы</span><input class="field__input" id="support-hours" value="' + L.escapeHtml(s.work_hours || "") + '"></label>' +
        '<label class="field"><span class="field__label">Текст блока поддержки</span><textarea class="admin-editor" id="support-text">' + L.escapeHtml(s.text || "") + "</textarea></label>" +
        '<div class="admin-toolbar"><button type="button" class="btn btn--primary btn--sm" id="support-save">Сохранить контакты</button></div>' +
      "</div>";
    document.getElementById("support-save").addEventListener("click", function () {
      var value = {
        phone: document.getElementById("support-phone").value.trim(),
        email: document.getElementById("support-email").value.trim(),
        work_hours: document.getElementById("support-hours").value.trim(),
        text: document.getElementById("support-text").value.trim(),
      };
      PlombirApi.put("/content/support_contacts", { value: value }).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
          return;
        }
        state.support = result.data.data.value;
        L.showToast(document.getElementById("page-alert"), "Контакты сохранены", "success");
      });
    });
  }

  function loadAll() {
    return Promise.all([
      PlombirApi.get("/content/faq"),
      PlombirApi.get("/content/instructions"),
      PlombirApi.get("/content/support_contacts"),
    ]).then(function (results) {
      results.forEach(function (result, index) {
        if (!result.response.ok || !result.data || !result.data.success) {
          throw new Error(PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки"));
        }
        if (index === 0) state.faq = result.data.data.value || { items: [] };
        if (index === 1) state.instructions = result.data.data.value || { title: "", content: "", items: [] };
        if (index === 2) state.support = result.data.data.value || {};
      });
    });
  }

  function init(profile) {
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "content",
      pageTitle: "Контент",
    });
    content.innerHTML = '<div id="content-root"><p class="admin-empty">Загрузка…</p></div>';
    loadAll().then(function () {
      renderTabs(document.getElementById("content-root"));
    }).catch(function (err) {
      document.getElementById("content-root").innerHTML = '<div id="page-alert"></div>';
      L.showToast(document.getElementById("page-alert"), err.message, "error");
    });
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (profile) init(profile);
  });
})();
