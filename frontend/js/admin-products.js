(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = { items: [], distributors: [], parserFields: [], page: 1, totalPages: 1 };

  function loadDistributors() {
    return PlombirApi.get("/distributors/").then(function (result) {
      state.distributors = (result.data && result.data.data) || [];
    });
  }

  function loadParserConfig() {
    return PlombirApi.get("/parser/config").then(function (result) {
      if (result.data && result.data.data) {
        state.parserFields = result.data.data.available_fields || [];
      }
    });
  }

  function loadProducts() {
    return PlombirApi.get("/products/?include_inactive=true&limit=50&page=" + state.page).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        throw new Error(PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки"));
      }
      var data = result.data.data || {};
      state.items = data.items || [];
      state.totalPages = (data.pagination && data.pagination.total_pages) || 1;
    });
  }

  function renderPage(container) {
    container.innerHTML =
      '<div id="page-alert"></div>' +
      '<div class="admin-card">' +
        '<h2 class="admin-import-block__title">Парсер omoloko.ru</h2>' +
        '<p class="admin-modal__meta">Ручной запуск обновления каталога. Ручные правки защищены полем manual_overrides.</p>' +
        '<div class="admin-checklist" id="parser-fields">' +
          state.parserFields.map(function (field) {
            return '<label><input type="checkbox" value="' + field + '" checked> ' + L.escapeHtml(field) + "</label>";
          }).join("") +
        "</div>" +
        '<label class="checkbox-inline"><input type="checkbox" id="parser-update-existing"><span>Обновлять существующие товары</span></label>' +
        '<div class="admin-modal__actions"><button type="button" class="btn btn--primary btn--sm" id="parser-run">Запустить парсер</button></div>' +
        '<div class="admin-import-result" id="parser-result" hidden></div>' +
      "</div>" +
      '<div class="admin-card" style="margin-top:1rem">' +
        '<div class="admin-toolbar"><button type="button" class="btn btn--primary btn--sm" id="product-create">Добавить товар</button></div>' +
        '<div id="products-table"><p class="admin-empty">Загрузка…</p></div>' +
        '<div class="admin-pagination" id="products-pagination" hidden></div>' +
      "</div>";

    document.getElementById("parser-run").addEventListener("click", runParser);
    document.getElementById("product-create").addEventListener("click", function () { openModal(null); });
    refreshTable();
  }

  function getParserFields() {
    var root = document.getElementById("parser-fields");
    if (!root) return [];
    return Array.prototype.slice.call(root.querySelectorAll("input:checked")).map(function (el) {
      return el.value;
    });
  }

  function runParser() {
    var resultBox = document.getElementById("parser-result");
    resultBox.hidden = false;
    resultBox.textContent = "Запуск парсера…";
    PlombirApi.post("/parser/run", {
      update_existing: document.getElementById("parser-update-existing").checked,
      fields_to_update: getParserFields(),
      max_products: 100,
    }).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        resultBox.className = "admin-import-result admin-import-result--error";
        resultBox.textContent = PlombirApi.extractErrorMessage(result.data, "Ошибка парсера");
        return;
      }
      resultBox.className = "admin-import-result";
      resultBox.textContent = JSON.stringify(result.data.data, null, 2);
      refreshTable();
    });
  }

  function refreshTable() {
    loadProducts().then(function () {
      var host = document.getElementById("products-table");
      if (!state.items.length) {
        host.innerHTML = '<p class="admin-empty">Товары не найдены</p>';
      } else {
        host.innerHTML =
          '<div class="admin-table-wrap"><table class="admin-table">' +
            "<thead><tr><th>Артикул</th><th>Название</th><th>Группа</th><th>Источник</th><th>Статус</th></tr></thead><tbody>" +
            state.items.map(function (item) {
              var status = item.is_active
                ? '<span class="admin-badge admin-badge--ok">Активен</span>'
                : '<span class="admin-badge admin-badge--muted">Скрыт</span>';
              return (
                "<tr data-product-id=\"" + item.id + "\">" +
                  "<td>" + L.escapeHtml(item.article) + "</td>" +
                  "<td>" + L.escapeHtml(item.name) + "</td>" +
                  "<td>" + L.escapeHtml(item.product_group || "—") + "</td>" +
                  "<td>" + L.escapeHtml(item.source) + "</td>" +
                  "<td>" + status + "</td>" +
                "</tr>"
              );
            }).join("") +
            "</tbody></table></div>";
        host.querySelectorAll("tr[data-product-id]").forEach(function (row) {
          row.addEventListener("click", function () {
            openModal(row.getAttribute("data-product-id"));
          });
        });
      }
      renderPagination();
    });
  }

  function renderPagination() {
    var host = document.getElementById("products-pagination");
    if (!host) return;
    if (state.totalPages <= 1) { host.hidden = true; return; }
    host.hidden = false;
    host.innerHTML =
      '<button type="button" class="btn btn--ghost btn--sm"' + (state.page <= 1 ? " disabled" : "") + ' id="products-prev">Назад</button>' +
      '<span>Стр. ' + state.page + " / " + state.totalPages + "</span>" +
      '<button type="button" class="btn btn--ghost btn--sm"' + (state.page >= state.totalPages ? " disabled" : "") + ' id="products-next">Вперёд</button>';
    document.getElementById("products-prev").addEventListener("click", function () {
      if (state.page > 1) { state.page -= 1; refreshTable(); }
    });
    document.getElementById("products-next").addEventListener("click", function () {
      if (state.page < state.totalPages) { state.page += 1; refreshTable(); }
    });
  }

  function distributorChecklist(selectedIds, fieldId) {
    return (
      '<div class="admin-checklist" id="' + fieldId + '">' +
        state.distributors.map(function (d) {
          var checked = (selectedIds || []).indexOf(d.id) !== -1 ? " checked" : "";
          return '<label><input type="checkbox" value="' + d.id + '"' + checked + ">" + L.escapeHtml(d.name) + "</label>";
        }).join("") +
      "</div>"
    );
  }

  function getCheckedIds(fieldId) {
    var root = document.getElementById(fieldId);
    if (!root) return [];
    return Array.prototype.slice.call(root.querySelectorAll("input:checked")).map(function (el) { return el.value; });
  }

  function openModal(productId) {
    var product = productId ? state.items.find(function (p) { return p.id === productId; }) : null;
    var modal = document.getElementById("product-modal");
    modal.hidden = false;
    modal.innerHTML =
      '<div class="admin-modal admin-modal--wide">' +
        '<div class="admin-modal__header"><h2>' + (product ? L.escapeHtml(product.name) : "Новый товар") + "</h2>" +
        '<button type="button" class="admin-modal__close" id="product-close">×</button></div>' +
        '<div class="admin-modal__body admin-form-grid admin-form-grid--2">' +
          '<div id="product-modal-alert" style="grid-column:1/-1"></div>' +
          field("Артикул", "product-article", product ? product.article : "", !product) +
          field("Название", "product-name", product ? product.name : "") +
          field("Группа", "product-group", product ? (product.product_group || "") : "") +
          field("Бренд", "product-brand", product ? (product.brand || "") : "") +
          field("URL изображения", "product-image", product ? (product.image_url || "") : "") +
          field("Описание", "product-description", product ? (product.description || "") : "", false, true) +
          '<div class="field" style="grid-column:1/-1"><span class="field__label">Дистрибьюторы (пусто = всем)</span>' +
            distributorChecklist(product ? product.distributor_ids : [], "product-distributors") + "</div>" +
        "</div>" +
        '<div class="admin-modal__actions">' +
          (product ? '<button type="button" class="btn btn--danger btn--sm" id="product-hide">Скрыть</button>' : "") +
          '<button type="button" class="btn btn--ghost" id="product-cancel">Отмена</button>' +
          '<button type="button" class="btn btn--primary" id="product-save">Сохранить</button>' +
        "</div></div>";

    function close() { modal.hidden = true; }
    document.getElementById("product-close").addEventListener("click", close);
    document.getElementById("product-cancel").addEventListener("click", close);

    document.getElementById("product-save").addEventListener("click", function () {
      var payload = {
        article: document.getElementById("product-article").value.trim(),
        name: document.getElementById("product-name").value.trim(),
        product_group: document.getElementById("product-group").value.trim() || null,
        brand: document.getElementById("product-brand").value.trim() || null,
        image_url: document.getElementById("product-image").value.trim() || null,
        description: document.getElementById("product-description").value.trim() || null,
        distributor_ids: getCheckedIds("product-distributors"),
      };
      var request = product
        ? PlombirApi.put("/products/" + product.id, payload).then(function (result) {
            if (!result.response.ok || !result.data || !result.data.success) return result;
            return PlombirApi.put("/products/" + product.id + "/distributors", {
              distributor_ids: payload.distributor_ids,
            });
          })
        : PlombirApi.post("/products/", payload);

      request.then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          L.showToast(document.getElementById("product-modal-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
          return;
        }
        modal.hidden = true;
        refreshTable();
      });
    });

    var hideBtn = document.getElementById("product-hide");
    if (hideBtn) {
      hideBtn.addEventListener("click", function () {
        if (!confirm("Скрыть товар?")) return;
        PlombirApi.delete("/products/" + product.id).then(function (result) {
          if (!result.response.ok || !result.data || !result.data.success) return;
          modal.hidden = true;
          refreshTable();
        });
      });
    }
  }

  function field(label, id, value, readonly, textarea) {
    if (textarea) {
      return '<label class="field" style="grid-column:1/-1"><span class="field__label">' + label +
        '</span><textarea class="admin-editor" id="' + id + '">' + L.escapeHtml(value) + "</textarea></label>";
    }
    return '<label class="field"><span class="field__label">' + label + '</span><input class="field__input" id="' + id +
      '" value="' + L.escapeHtml(value) + '"' + (readonly ? " readonly" : "") + "></label>";
  }

  function init(profile) {
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "products",
      pageTitle: "Продукция ЧИСТАЯ ЛИНИЯ",
    });
    content.innerHTML = '<div id="products-root"><p class="admin-empty">Загрузка…</p></div>';
    Promise.all([loadDistributors(), loadParserConfig()]).then(function () {
      renderPage(document.getElementById("products-root"));
    });
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (profile) init(profile);
  });
})();
