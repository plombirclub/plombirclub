(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var LEGAL_KEYS = [
    { id: "personal_data", label: "Согласие на обработку персональных данных (ФЗ-152)" },
    { id: "program_rules", label: "Пользовательское соглашение" },
    { id: "email_notifications", label: "Согласие на email-уведомления" },
  ];
  var state = {
    tab: "faq",
    faq: { items: [] },
    instructions: { title: "", content: "", items: [] },
    support: {},
    legal: { documents: {} },
  };

  function renderTabs(container) {
    var tabs = [
      { id: "faq", label: "FAQ" },
      { id: "instructions", label: "Инструкции" },
      { id: "legal", label: "Юридические документы" },
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
    else if (state.tab === "legal") renderLegal(panel);
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

  function ensureInstructionItems() {
    if (!state.instructions.items) state.instructions.items = [];
    if (!state.instructions.items.length) {
      state.instructions.items.push({
        id: "new-" + Date.now(),
        title: "",
        description: "",
        file_path: null,
        content_type: null,
        sort_order: 0,
        is_published: true,
      });
    }
  }

  function renderInstructions(panel) {
    ensureInstructionItems();
    panel.innerHTML =
      '<div class="admin-card admin-form-grid">' +
        '<label class="field"><span class="field__label">Заголовок страницы</span><input class="field__input" id="instr-title" value="' +
          L.escapeHtml(state.instructions.title || "") + '"></label>' +
        '<label class="field"><span class="field__label">Вводный текст (необязательно)</span><textarea class="admin-editor admin-editor--tall" id="instr-content">' +
          L.escapeHtml(state.instructions.content || "") + "</textarea></label>" +
      "</div>" +
      '<div class="admin-card admin-instructions-block">' +
        '<h3 class="admin-card__title">Материалы для участников</h3>' +
        '<p class="admin-modal__meta">Загрузите PDF или картинку (JPG, PNG, WEBP, GIF). Участник увидит просмотр с листанием страниц, как на референсе. После загрузки файла нажмите «Сохранить».</p>' +
        '<div id="instr-items"></div>' +
        '<div class="admin-toolbar">' +
          '<button type="button" class="btn btn--ghost btn--sm" id="instr-add">+ Ещё один материал</button>' +
          '<button type="button" class="btn btn--primary btn--sm" id="instr-save">Сохранить инструкции</button>' +
        "</div>" +
      "</div>";
    renderInstructionItems();
    document.getElementById("instr-add").addEventListener("click", function () {
      state.instructions.items.push({
        id: String(Date.now()),
        title: "",
        description: "",
        file_path: null,
        content_type: null,
        sort_order: state.instructions.items.length,
        is_published: true,
      });
      renderInstructionItems();
    });
    document.getElementById("instr-save").addEventListener("click", function () {
      state.instructions.title = document.getElementById("instr-title").value.trim();
      state.instructions.content = document.getElementById("instr-content").value.trim();
      var hasFile = (state.instructions.items || []).some(function (item) { return item.file_path; });
      if (!hasFile) {
        L.showToast(document.getElementById("page-alert"), "Загрузите хотя бы один файл (PDF или картинку)", "error");
        return;
      }
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
      var fileInfo = item.file_path
        ? '<p class="admin-modal__meta admin-instruction-file-info">✓ Файл загружен: ' + L.escapeHtml(item.file_path) +
          (item.content_type ? " (" + L.escapeHtml(item.content_type) + ")" : "") + "</p>"
        : '<p class="admin-modal__meta admin-instruction-file-info admin-instruction-file-info--empty">Файл пока не выбран</p>';
      return (
        '<div class="admin-card admin-instruction-item">' +
          '<p class="admin-instruction-item__num">Материал ' + (index + 1) + "</p>" +
          '<label class="field"><span class="field__label">Название для карточки</span><input class="field__input" data-instr-field="title" data-index="' + index + '" placeholder="Например: Инструкция для участников" value="' +
            L.escapeHtml(item.title) + '"></label>' +
          '<label class="field"><span class="field__label">Краткое описание (необязательно)</span><textarea class="admin-editor" data-instr-field="description" data-index="' + index + '" placeholder="Короткий текст под названием">' +
            L.escapeHtml(item.description || "") + "</textarea></label>" +
          '<label class="field admin-instruction-upload">' +
            '<span class="field__label">Файл: PDF или изображение</span>' +
            '<input class="field__input admin-instruction-upload__input" type="file" data-instr-upload="' + index + '" accept=".pdf,image/jpeg,image/png,image/webp,image/gif">' +
          "</label>" +
          fileInfo +
          (state.instructions.items.length > 1
            ? '<button type="button" class="btn btn--danger btn--sm" data-instr-remove="' + index + '">Удалить материал</button>'
            : "") +
        "</div>"
      );
    }).join("");

    host.querySelectorAll("[data-instr-field]").forEach(function (el) {
      el.addEventListener("input", function () {
        var idx = Number(el.getAttribute("data-index"));
        state.instructions.items[idx][el.getAttribute("data-instr-field")] = el.value;
      });
    });
    host.querySelectorAll("[data-instr-upload]").forEach(function (input) {
      input.addEventListener("change", function () {
        var idx = Number(input.getAttribute("data-instr-upload"));
        var file = input.files[0];
        if (!file) return;
        var form = new FormData();
        form.append("file", file);
        PlombirApi.postForm("/content/instructions/upload", form).then(function (result) {
          if (!result.response.ok || !result.data || !result.data.success) {
            L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки"), "error");
            return;
          }
          var data = result.data.data || {};
          state.instructions.items[idx].file_path = data.file_path;
          state.instructions.items[idx].content_type = data.content_type;
          renderInstructionItems();
          L.showToast(document.getElementById("page-alert"), "Файл загружен", "success");
        });
      });
    });
    host.querySelectorAll("[data-instr-remove]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.instructions.items.splice(Number(btn.getAttribute("data-instr-remove")), 1);
        renderInstructionItems();
      });
    });
  }

  function ensureLegalDocuments() {
    if (!state.legal.documents) state.legal.documents = {};
    LEGAL_KEYS.forEach(function (entry) {
      if (!state.legal.documents[entry.id]) {
        state.legal.documents[entry.id] = {
          title: entry.label,
          text: "",
          file_path: null,
          content_type: null,
        };
      }
    });
  }

  function renderLegal(panel) {
    ensureLegalDocuments();
    panel.innerHTML =
      '<div class="admin-card admin-instructions-block">' +
        '<h3 class="admin-card__title">Юридические документы</h3>' +
        '<p class="admin-modal__meta">Эти документы показываются при первом входе и в профиле участника. Загрузите PDF или картинку, при необходимости добавьте текст. После изменений нажмите «Сохранить».</p>' +
        '<div id="legal-items"></div>' +
        '<div class="admin-toolbar">' +
          '<button type="button" class="btn btn--primary btn--sm" id="legal-save">Сохранить документы</button>' +
        "</div>" +
      "</div>";
    renderLegalItems();
    document.getElementById("legal-save").addEventListener("click", function () {
      PlombirApi.put("/content/legal_documents", { value: state.legal }).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
          return;
        }
        state.legal = result.data.data.value || { documents: {} };
        ensureLegalDocuments();
        L.showToast(document.getElementById("page-alert"), "Юридические документы сохранены", "success");
        renderLegalItems();
      });
    });
  }

  function renderLegalItems() {
    var host = document.getElementById("legal-items");
    if (!host) return;
    host.innerHTML = LEGAL_KEYS.map(function (entry) {
      var item = state.legal.documents[entry.id] || {};
      var fileInfo = item.file_path
        ? '<p class="admin-modal__meta admin-instruction-file-info">✓ Файл загружен: ' + L.escapeHtml(item.file_path) + "</p>"
        : '<p class="admin-modal__meta admin-instruction-file-info admin-instruction-file-info--empty">Файл пока не выбран</p>';
      return (
        '<div class="admin-card admin-instruction-item">' +
          '<p class="admin-instruction-item__num">' + L.escapeHtml(entry.label) + "</p>" +
          '<label class="field"><span class="field__label">Название для участника</span>' +
            '<input class="field__input" data-legal-field="title" data-legal-key="' + entry.id + '" value="' +
            L.escapeHtml(item.title || entry.label) + '"></label>' +
          '<label class="field"><span class="field__label">Текст (если без файла)</span>' +
            '<textarea class="admin-editor" data-legal-field="text" data-legal-key="' + entry.id + '">' +
            L.escapeHtml(item.text || "") + "</textarea></label>" +
          '<label class="field admin-instruction-upload"><span class="field__label">Файл: PDF или изображение</span>' +
            '<input class="field__input admin-instruction-upload__input" type="file" data-legal-upload="' + entry.id + '" accept=".pdf,image/jpeg,image/png,image/webp,image/gif"></label>' +
          fileInfo +
        "</div>"
      );
    }).join("");

    host.querySelectorAll("[data-legal-field]").forEach(function (el) {
      el.addEventListener("input", function () {
        var key = el.getAttribute("data-legal-key");
        var field = el.getAttribute("data-legal-field");
        if (!state.legal.documents[key]) state.legal.documents[key] = {};
        state.legal.documents[key][field] = el.value;
      });
    });
    host.querySelectorAll("[data-legal-upload]").forEach(function (input) {
      input.addEventListener("change", function () {
        var key = input.getAttribute("data-legal-upload");
        var file = input.files[0];
        if (!file) return;
        var form = new FormData();
        form.append("file", file);
        PlombirApi.postForm("/content/legal/upload", form).then(function (result) {
          if (!result.response.ok || !result.data || !result.data.success) {
            L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки"), "error");
            return;
          }
          var data = result.data.data || {};
          if (!state.legal.documents[key]) state.legal.documents[key] = {};
          state.legal.documents[key].file_path = data.file_path;
          state.legal.documents[key].content_type = data.content_type;
          renderLegalItems();
          L.showToast(document.getElementById("page-alert"), "Файл загружен", "success");
        });
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
      PlombirApi.get("/content/legal_documents"),
      PlombirApi.get("/content/support_contacts"),
    ]).then(function (results) {
      results.forEach(function (result, index) {
        if (!result.response.ok || !result.data || !result.data.success) {
          throw new Error(PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки"));
        }
        if (index === 0) state.faq = result.data.data.value || { items: [] };
        if (index === 1) state.instructions = result.data.data.value || { title: "", content: "", items: [] };
        if (index === 2) state.legal = result.data.data.value || { documents: {} };
        if (index === 3) state.support = result.data.data.value || {};
      });
      ensureLegalDocuments();
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
