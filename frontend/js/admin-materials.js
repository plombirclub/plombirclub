(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var CONTENT_TYPES = [
    { id: "pdf", label: "PDF" },
    { id: "pptx", label: "PPTX" },
    { id: "video", label: "Видео" },
    { id: "image", label: "Изображение" },
    { id: "text", label: "Текст" },
  ];
  var state = { items: [] };

  function typeLabel(value) {
    var found = CONTENT_TYPES.find(function (t) { return t.id === value; });
    return found ? found.label : value;
  }

  function loadMaterials() {
    return PlombirApi.get("/materials/?include_unpublished=true").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        throw new Error(PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки"));
      }
      state.items = (result.data.data && result.data.data.items) || [];
    });
  }

  function renderStats(stats) {
    if (!stats) return "—";
    return [
      "Не начат: " + (stats.not_started || 0),
      "Начат: " + (stats.started || 0),
      "Изучен: " + (stats.completed || 0),
    ].join(" · ");
  }

  function renderList(container) {
    if (!state.items.length) {
      container.innerHTML =
        '<div class="admin-card"><p class="admin-empty">Материалы не найдены</p>' +
        '<button type="button" class="btn btn--primary btn--sm" id="material-create-btn">Добавить материал</button></div>';
      document.getElementById("material-create-btn").addEventListener("click", function () { openModal(null); });
      return;
    }

    container.innerHTML =
      '<div class="admin-card">' +
        '<div class="admin-toolbar"><button type="button" class="btn btn--primary btn--sm" id="material-create-btn">Добавить материал</button></div>' +
        '<div class="admin-table-wrap"><table class="admin-table">' +
          "<thead><tr><th>Название</th><th>Тип</th><th>Статус</th><th>Статистика</th></tr></thead><tbody>" +
          state.items.map(function (item) {
            var status = item.is_published
              ? '<span class="admin-badge admin-badge--ok">Опубликован</span>'
              : '<span class="admin-badge admin-badge--muted">Скрыт</span>';
            return (
              "<tr data-material-id=\"" + item.id + "\">" +
                "<td>" + L.escapeHtml(item.title) + "</td>" +
                "<td>" + L.escapeHtml(typeLabel(item.content_type)) + "</td>" +
                "<td>" + status + "</td>" +
                "<td>" + L.escapeHtml(renderStats(item.stats)) + "</td>" +
              "</tr>"
            );
          }).join("") +
          "</tbody></table></div></div>";

    document.getElementById("material-create-btn").addEventListener("click", function () { openModal(null); });
    container.querySelectorAll("tr[data-material-id]").forEach(function (row) {
      row.addEventListener("click", function () {
        openModal(row.getAttribute("data-material-id"));
      });
    });
  }

  function openModal(materialId) {
    var material = materialId ? state.items.find(function (m) { return m.id === materialId; }) : null;
    var modal = document.getElementById("material-modal");
    modal.hidden = false;
    modal.innerHTML =
      '<div class="admin-modal admin-modal--wide">' +
        '<div class="admin-modal__header"><h2>' + (material ? L.escapeHtml(material.title) : "Новый материал") + "</h2>" +
        '<button type="button" class="admin-modal__close" id="material-close">×</button></div>' +
        '<div class="admin-modal__body admin-form-grid">' +
          '<div id="material-modal-alert"></div>' +
          '<label class="field"><span class="field__label">Название</span><input class="field__input" id="material-title" value="' +
            L.escapeHtml(material ? material.title : "") + '"></label>' +
          '<label class="field"><span class="field__label">Описание</span><textarea class="admin-editor" id="material-description">' +
            L.escapeHtml(material ? (material.description || "") : "") + "</textarea></label>" +
          '<label class="field field--sm"><span class="field__label">Тип</span><select class="field__input" id="material-type">' +
            CONTENT_TYPES.map(function (t) {
              var sel = material && material.content_type === t.id ? " selected" : "";
              return '<option value="' + t.id + '"' + sel + ">" + t.label + "</option>";
            }).join("") +
          "</select></label>" +
          '<label class="field field--sm"><span class="field__label">Страниц/слайдов</span><input class="field__input" type="number" min="1" id="material-pages" value="' +
            L.escapeHtml(material && material.total_pages ? material.total_pages : "") + '"></label>' +
          '<label class="field field--sm"><span class="field__label">Порядок</span><input class="field__input" type="number" id="material-sort" value="' +
            L.escapeHtml(material ? material.sort_order : 0) + '"></label>' +
          '<label class="checkbox-inline"><input type="checkbox" id="material-published"' +
            ((material ? material.is_published : true) ? " checked" : "") + "><span>Опубликован</span></label>" +
          '<label class="field"><span class="field__label">Файл</span><input class="field__input" type="file" id="material-file"></label>' +
          (material && material.file_path
            ? '<p class="admin-modal__meta">Текущий файл: ' + L.escapeHtml(material.file_path) + "</p>"
            : "") +
        "</div>" +
        '<div class="admin-modal__actions">' +
          (material ? '<button type="button" class="btn btn--danger btn--sm" id="material-hide">Скрыть</button>' : "") +
          '<button type="button" class="btn btn--ghost" id="material-cancel">Отмена</button>' +
          '<button type="button" class="btn btn--primary" id="material-save">Сохранить</button>' +
        "</div></div>";

    function close() { modal.hidden = true; }
    document.getElementById("material-close").addEventListener("click", close);
    document.getElementById("material-cancel").addEventListener("click", close);

    document.getElementById("material-save").addEventListener("click", function () {
      var form = new FormData();
      form.append("title", document.getElementById("material-title").value.trim());
      form.append("description", document.getElementById("material-description").value.trim());
      form.append("content_type", document.getElementById("material-type").value);
      var pages = document.getElementById("material-pages").value;
      if (pages) form.append("total_pages", pages);
      form.append("sort_order", document.getElementById("material-sort").value || "0");
      form.append("is_published", document.getElementById("material-published").checked ? "true" : "false");
      var file = document.getElementById("material-file").files[0];
      if (file) form.append("file", file);

      var request = material
        ? PlombirApi.putForm("/materials/" + material.id, form)
        : PlombirApi.postForm("/materials/", form);

      request.then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          L.showToast(document.getElementById("material-modal-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
          return;
        }
        modal.hidden = true;
        refresh();
      });
    });

    var hideBtn = document.getElementById("material-hide");
    if (hideBtn) {
      hideBtn.addEventListener("click", function () {
        if (!confirm("Скрыть материал?")) return;
        PlombirApi.delete("/materials/" + material.id).then(function (result) {
          if (!result.response.ok || !result.data || !result.data.success) {
            L.showToast(document.getElementById("material-modal-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
            return;
          }
          modal.hidden = true;
          refresh();
        });
      });
    }
  }

  function refresh() {
    loadMaterials().then(function () {
      renderList(document.getElementById("materials-root"));
    }).catch(function (err) {
      L.showToast(document.getElementById("page-alert"), err.message, "error");
    });
  }

  function init(profile) {
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "materials",
      pageTitle: "Материалы",
    });
    content.innerHTML = '<div id="page-alert"></div><div id="materials-root"><p class="admin-empty">Загрузка…</p></div>';
    refresh();
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (profile) init(profile);
  });
})();
