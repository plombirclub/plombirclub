(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = {
    items: [],
    distributors: [],
    parserFields: [],
    page: 1,
    totalPages: 1,
    selectedDistributorId: "",
  };
  var parserFieldLabels = {
    article: "Артикул",
    name: "Название",
    description: "Описание",
    image_url: "Изображение",
    category: "Категория",
    product_kind: "Вид",
    flavor: "Вкус",
    composition: "О товаре / состав",
    weight_volume: "Вес / объём",
    sort_order: "Порядок отображения",
    product_group: "Группа",
    brand: "Бренд",
    code: "Код",
    unit_barcode: "Штрихкод единицы",
    box_barcode: "Штрихкод коробки",
    unit_volume: "Объём единицы",
    net_weight: "Вес нетто",
    pieces_per_box: "Штук в коробке",
    shelf_life: "Срок годности",
    nutrition_facts: "Пищевая ценность (в 100 г)",
  };

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
        '<p class="admin-modal__meta">Ручной запуск обновления каталога. Снимите галочки у ненужных полей, включите «Обновлять существующие товары» — и парсер очистит эти поля в уже загруженных товарах.</p>' +
        '<div class="admin-checklist" id="parser-fields">' +
          state.parserFields.map(function (field) {
            return '<label><input type="checkbox" value="' + field + '" checked> ' + L.escapeHtml(parserFieldLabels[field] || field) + "</label>";
          }).join("") +
        "</div>" +
        '<label class="checkbox-inline"><input type="checkbox" id="parser-update-existing"><span>Обновлять существующие товары</span></label>' +
        '<div class="admin-modal__actions"><button type="button" class="btn btn--primary btn--sm" id="parser-run">Запустить парсер</button></div>' +
        '<div class="admin-import-result" id="parser-result" hidden></div>' +
      "</div>" +
      '<div class="admin-card" style="margin-top:1rem">' +
        '<div class="admin-toolbar">' +
          '<button type="button" class="btn btn--primary btn--sm" id="product-create">Добавить товар</button>' +
          '<label class="field" style="min-width:18rem; margin-left:auto;">' +
            '<span class="field__label">Проверка по дистрибьютору</span>' +
            '<select class="field__input" id="products-distributor-filter">' +
              '<option value="">Выберите дистрибьютора…</option>' +
              state.distributors.map(function (d) {
                var selected = d.id === state.selectedDistributorId ? " selected" : "";
                return '<option value="' + d.id + '"' + selected + ">" + L.escapeHtml(d.name) + "</option>";
              }).join("") +
            "</select>" +
          "</label>" +
        "</div>" +
        '<p class="admin-modal__meta">Если галочка стоит — товар виден участникам выбранного дистрибьютора. Если снять галочку — товар скрывается у него.</p>' +
        '<div id="products-table"><p class="admin-empty">Загрузка…</p></div>' +
        '<div class="admin-pagination" id="products-pagination" hidden></div>' +
      "</div>";

    document.getElementById("parser-run").addEventListener("click", runParser);
    document.getElementById("product-create").addEventListener("click", function () { openModal(null); });
    document.getElementById("products-distributor-filter").addEventListener("change", function (event) {
      state.selectedDistributorId = event.target.value || "";
      refreshTable();
    });
    refreshTable();
  }

  function getParserFields() {
    var root = document.getElementById("parser-fields");
    if (!root) return [];
    return Array.prototype.slice.call(root.querySelectorAll("input:checked")).map(function (el) {
      return el.value;
    });
  }

  function formatParserResult(data) {
    if (!data) return "Парсер завершён без данных.";
    var lines = [
      "Источник: " + (data.source_url || "—"),
      "Найдено на сайте: " + (data.parsed_count || 0),
      "Новых добавлено: " + (data.created_count || 0),
      "Обновлено: " + (data.updated_count || 0),
      "Уже были в базе: " + (data.skipped_existing_count || 0),
    ];
    if ((data.created_count || 0) === 0 && (data.updated_count || 0) === 0 && (data.skipped_existing_count || 0) > 0) {
      lines.push("");
      lines.push("Товары уже есть в базе. Чтобы обновить поля с omoloko.ru, включите «Обновлять существующие товары» и запустите снова.");
    }
    if ((data.created_count || 0) > 0 || (data.updated_count || 0) > 0) {
      lines.push("");
      lines.push("Список ниже обновлён.");
    }
    return lines.join("\n");
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
      resultBox.textContent = formatParserResult(result.data.data);
      state.page = 1;
      refreshTable();
    }).catch(function (err) {
      resultBox.className = "admin-import-result admin-import-result--error";
      resultBox.textContent = err && err.message ? err.message : "Ошибка парсера";
    });
  }

  function refreshTable() {
    var host = document.getElementById("products-table");
    if (host) {
      host.innerHTML = '<p class="admin-empty">Загрузка…</p>';
    }
    loadProducts().then(function () {
      if (!host) return;
      if (!state.items.length) {
        host.innerHTML = '<p class="admin-empty">Товары не найдены. Запустите парсер или добавьте товар вручную.</p>';
      } else {
        var hasDistributor = !!state.selectedDistributorId;
        host.innerHTML =
          '<p class="admin-modal__meta">Всего в базе: ' + state.items.length + " на этой странице (стр. " + state.page + " из " + state.totalPages + ")</p>" +
          '<div class="admin-table-wrap"><table class="admin-table">' +
            "<thead><tr><th>Артикул</th><th>Название</th><th>Группа</th><th>Источник</th><th>Виден у дистрибьютора</th><th>Статус</th></tr></thead><tbody>" +
            state.items.map(function (item) {
              var status = item.is_active
                ? '<span class="admin-badge admin-badge--ok">Активен</span>'
                : '<span class="admin-badge admin-badge--muted">Скрыт</span>';
              var checked = hasDistributor && isVisibleForDistributor(item, state.selectedDistributorId) ? " checked" : "";
              var disabled = hasDistributor ? "" : " disabled";
              return (
                "<tr data-product-id=\"" + item.id + "\">" +
                  "<td>" + L.escapeHtml(item.article) + "</td>" +
                  "<td>" + L.escapeHtml(item.name) + "</td>" +
                  "<td>" + L.escapeHtml(item.product_group || "—") + "</td>" +
                  "<td>" + L.escapeHtml(item.source) + "</td>" +
                  "<td><label><input type=\"checkbox\" class=\"product-dist-toggle\" data-product-id=\"" + item.id + "\"" + checked + disabled + "> " +
                    (hasDistributor ? "Да" : "Выберите дистрибьютора") + "</label></td>" +
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
        host.querySelectorAll(".product-dist-toggle").forEach(function (input) {
          input.addEventListener("click", function (event) {
            event.stopPropagation();
          });
          input.addEventListener("change", function (event) {
            setDistributorVisibility(event.target.getAttribute("data-product-id"), !!event.target.checked);
          });
        });
      }
      renderPagination();
    }).catch(function (err) {
      if (!host) return;
      host.innerHTML = '<p class="admin-empty admin-import-result--error">' +
        L.escapeHtml(err && err.message ? err.message : "Не удалось загрузить товары") +
        "</p>";
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

  function isVisibleForDistributor(item, distributorId) {
    if (!distributorId) return false;
    var ids = item.distributor_ids || [];
    if (!ids.length) return true;
    return ids.indexOf(distributorId) !== -1;
  }

  function allDistributorIdsExcept(distributorId) {
    return state.distributors.map(function (d) { return d.id; }).filter(function (id) {
      return id !== distributorId;
    });
  }

  function nextDistributorIds(item, distributorId, shouldBeVisible) {
    var current = (item.distributor_ids || []).slice();
    if (!current.length) {
      if (shouldBeVisible) return [];
      return allDistributorIdsExcept(distributorId);
    }
    if (shouldBeVisible) {
      if (current.indexOf(distributorId) !== -1) return current;
      current.push(distributorId);
      if (current.length >= state.distributors.length) return [];
      return current;
    }
    var next = current.filter(function (id) { return id !== distributorId; });
    if (!next.length) return allDistributorIdsExcept(distributorId);
    return next;
  }

  function setDistributorVisibility(productId, shouldBeVisible) {
    if (!state.selectedDistributorId) return;
    var item = state.items.find(function (it) { return it.id === productId; });
    if (!item) return;
    var distributorIds = nextDistributorIds(item, state.selectedDistributorId, shouldBeVisible);
    PlombirApi.put("/products/" + productId + "/distributors", { distributor_ids: distributorIds }).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        L.showToast(document.getElementById("page-alert"), PlombirApi.extractErrorMessage(result.data, "Не удалось сохранить видимость"), "error");
        refreshTable();
        return;
      }
      item.distributor_ids = (result.data.data && result.data.data.distributor_ids) || distributorIds;
      refreshTable();
    }).catch(function (err) {
      L.showToast(document.getElementById("page-alert"), err && err.message ? err.message : "Не удалось сохранить видимость", "error");
      refreshTable();
    });
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
          field("Срок годности", "product-shelf-life", product ? (product.shelf_life || "") : "") +
          field("Пищевая ценность (в 100 г)", "product-nutrition-facts", product ? (product.nutrition_facts || "") : "", false, true) +
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
        shelf_life: document.getElementById("product-shelf-life").value.trim() || null,
        nutrition_facts: document.getElementById("product-nutrition-facts").value.trim() || null,
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
