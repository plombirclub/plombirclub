(function () {
  "use strict";

  var state = {
    view: "list",
    items: [],
    groups: [],
    groupFilter: "",
    searchQuery: "",
    page: 1,
    totalPages: 1,
    activeProduct: null,
    loading: false,
  };

  function escape(value) {
    return PlombirLayout.escapeHtml(value || "");
  }

  function imageUrl(value) {
    if (!value) return "";
    if (value.indexOf("http://") === 0 || value.indexOf("https://") === 0) return value;
    if (value.indexOf("/") === 0) return value;
    return value;
  }

  function mediaHtml(product) {
    if (product.image_url) {
      return '<img src="' + escape(imageUrl(product.image_url)) + '" alt="">';
    }
    return '<p class="product-card__placeholder">ЧИСТАЯ ЛИНИЯ</p>';
  }

  function textBlock(label, value, className) {
    if (!value) return "";
    return (
      '<div class="' + className + '">' +
        '<p class="' + className + '__title">' + escape(label) + "</p>" +
        '<p class="' + className + '__text">' + escape(value) + "</p>" +
      "</div>"
    );
  }

  function groupItems(items) {
    var map = {};
    items.forEach(function (item) {
      var key = item.product_group || "Без группы";
      if (!map[key]) map[key] = [];
      map[key].push(item);
    });
    return Object.keys(map)
      .sort(function (a, b) {
        if (a === "Без группы") return 1;
        if (b === "Без группы") return -1;
        return a.localeCompare(b, "ru");
      })
      .map(function (key) {
        return { title: key, items: map[key] };
      });
  }

  function renderShell() {
    var groupOptions =
      '<option value="">Все группы</option>' +
      state.groups
        .map(function (group) {
          var selected = group === state.groupFilter ? " selected" : "";
          return '<option value="' + escape(group) + '"' + selected + ">" + escape(group) + "</option>";
        })
        .join("");

    return (
      '<section class="products-page">' +
        '<div id="products-alert"></div>' +
        '<div class="products-toolbar">' +
          '<label class="field">' +
            '<span class="field__label">Группа</span>' +
            '<select class="products-period-select" id="products-group">' + groupOptions + "</select>" +
          "</label>" +
          '<label class="field products-toolbar__search">' +
            '<span class="field__label">Поиск по названию</span>' +
            '<input class="field__input" id="products-search" type="search" placeholder="Введите название товара" value="' + escape(state.searchQuery) + '">' +
          "</label>" +
        "</div>" +
        '<div id="products-content">' +
          '<p class="content-empty">Загружаем продукцию…</p>' +
        "</div>" +
        '<div class="content-pagination" id="products-pagination"></div>' +
      "</section>"
    );
  }

  function renderList() {
    var container = document.getElementById("products-content");
    if (!container) return;

    if (!state.items.length) {
      container.innerHTML =
        '<p class="content-empty">Каталог продукции пока пуст. Товары появятся после добавления администратором или парсинга.</p>';
      return;
    }

    var query = state.searchQuery.trim().toLowerCase();
    var filteredItems = state.items.filter(function (item) {
      if (!query) return true;
      return (item.name || "").toLowerCase().indexOf(query) !== -1;
    });
    if (!filteredItems.length) {
      container.innerHTML = '<p class="content-empty">По вашему запросу товары не найдены.</p>';
      var emptyPagination = document.getElementById("products-pagination");
      if (emptyPagination) emptyPagination.innerHTML = "";
      return;
    }

    var sections = groupItems(filteredItems);
    var html = sections
      .map(function (section) {
        var cards = section.items
          .map(function (product) {
            return (
              '<article class="product-card" data-product-id="' + escape(product.id) + '">' +
                '<div class="product-card__media">' + mediaHtml(product) + "</div>" +
                '<div class="product-card__body">' +
                  '<h3 class="product-card__name">' + escape(product.name) + "</h3>" +
                  textBlock("Описание", product.description, "product-card__block") +
                  textBlock("Количество в коробке", product.pieces_per_box, "product-card__block") +
                  '<div class="product-card__footer">' +
                    '<span class="product-card__link">Подробнее</span>' +
                  "</div>" +
                "</div>" +
              "</article>"
            );
          })
          .join("");

        return (
          '<section class="products-group">' +
            '<h2 class="products-group__title">' + escape(section.title) + "</h2>" +
            '<div class="products-grid">' + cards + "</div>" +
          "</section>"
        );
      })
      .join("");

    container.innerHTML = html;

    container.querySelectorAll(".product-card").forEach(function (card) {
      card.addEventListener("click", function () {
        openDetail(card.getAttribute("data-product-id"));
      });
    });

    var pagination = document.getElementById("products-pagination");
    if (pagination) {
      if (state.page < state.totalPages) {
        pagination.innerHTML =
          '<button type="button" class="btn btn--secondary" id="products-load-more">Показать ещё</button>';
        document.getElementById("products-load-more").addEventListener("click", function () {
          loadProducts(state.page + 1, true);
        });
      } else {
        pagination.innerHTML = "";
      }
    }
  }

  function detailRow(label, value) {
    if (!value && value !== 0) return "";
    return (
      "<tr><th>" + escape(label) + "</th><td>" + escape(String(value)) + "</td></tr>"
    );
  }

  function renderDetail() {
    var container = document.getElementById("products-content");
    if (!container || !state.activeProduct) return;

    var product = state.activeProduct;
    var pagination = document.getElementById("products-pagination");
    if (pagination) pagination.innerHTML = "";
    var rows =
      detailRow("Описание", product.description) +
      detailRow("Категория", product.category) +
      detailRow("Бренд", product.brand) +
      detailRow("Код", product.code || product.article) +
      detailRow("Штрихкод единицы", product.unit_barcode) +
      detailRow("Штрихкод коробки", product.box_barcode) +
      detailRow("Объем единицы, л", product.unit_volume || product.weight_volume) +
      detailRow("Вес нетто, кг", product.net_weight) +
      detailRow("Срок годности", product.shelf_life) +
      detailRow("Количество в коробке", product.pieces_per_box);

    container.innerHTML =
      '<div class="product-detail">' +
        '<button type="button" class="product-back" id="product-back">← Назад</button>' +
        '<div class="product-detail__layout">' +
          '<div class="product-detail__image">' +
            (product.image_url
              ? '<img src="' + escape(imageUrl(product.image_url)) + '" alt="' + escape(product.name) + '">'
              : '<p class="product-card__placeholder">ЧИСТАЯ ЛИНИЯ</p>') +
          "</div>" +
          '<div class="product-detail__info">' +
            (product.product_group
              ? '<p class="product-detail__group">' + escape(product.product_group) + "</p>"
              : "") +
            '<h2 class="product-detail__title">' + escape(product.name) + "</h2>" +
            '<table class="product-detail__table"><tbody>' + rows + "</tbody></table>" +
            textBlock("О товаре", product.composition, "product-detail__block") +
            textBlock("Пищевая ценность (в 100 г)", product.nutrition_facts, "product-detail__block") +
          "</div>" +
        "</div>" +
      "</div>";

    document.getElementById("product-back").addEventListener("click", showList);
  }

  function getProductIdFromUrl() {
    return new URLSearchParams(window.location.search).get("product") || "";
  }

  function setProductUrl(productId) {
    var url = new URL(window.location.href);
    if (productId) url.searchParams.set("product", productId);
    else url.searchParams.delete("product");
    window.history.replaceState({}, "", url.pathname + url.search);
  }

  function showList() {
    state.view = "list";
    state.activeProduct = null;
    setProductUrl("");
    renderList();
  }

  function openDetail(productId) {
    if (!productId) return;
    state.view = "detail";
    setProductUrl(productId);

    var cached = state.items.find(function (item) {
      return item.id === productId;
    });
    if (cached) {
      state.activeProduct = cached;
      renderDetail();
      return;
    }

    PlombirApi.get("/products/" + encodeURIComponent(productId)).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          document.getElementById("products-alert"),
          PlombirApi.extractErrorMessage(result.data, "Не удалось открыть товар"),
          "error"
        );
        return;
      }
      state.activeProduct = result.data.data;
      renderDetail();
    });
  }

  function loadGroups() {
    PlombirApi.get("/products/groups").then(function (result) {
      if (result.response.ok && result.data && result.data.success) {
        state.groups = (result.data.data || {}).groups || [];
        var select = document.getElementById("products-group");
        if (select) {
          var current = select.value;
          select.innerHTML =
            '<option value="">Все группы</option>' +
            state.groups
              .map(function (group) {
                return '<option value="' + escape(group) + '">' + escape(group) + "</option>";
              })
              .join("");
          select.value = current;
        }
      }
    });
  }

  function loadProducts(page, append) {
    if (state.loading) return;
    state.loading = true;

    var query = "?page=" + page + "&limit=24";
    if (state.groupFilter) {
      query += "&product_group=" + encodeURIComponent(state.groupFilter);
    }

    PlombirApi.get("/products/" + query).then(function (result) {
      state.loading = false;
      var alertBox = document.getElementById("products-alert");
      PlombirLayout.clearAlert(alertBox);

      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить продукцию"),
          "error"
        );
        return;
      }

      var data = result.data.data || {};
      var items = data.items || [];
      var pagination = data.pagination || {};
      state.page = pagination.current_page || page;
      state.totalPages = pagination.total_pages || 1;

      if (append) state.items = state.items.concat(items);
      else state.items = items;

      if (state.view === "detail" && state.activeProduct) {
        var updated = state.items.find(function (item) {
          return item.id === state.activeProduct.id;
        });
        if (updated) state.activeProduct = updated;
        renderDetail();
      } else {
        renderList();
      }
    }).catch(function (error) {
      state.loading = false;
      PlombirLayout.showAlert(
        document.getElementById("products-alert"),
        error && error.message ? error.message : "Не удалось загрузить продукцию",
        "error"
      );
    });
  }

  function bindGroupSelect() {
    var select = document.getElementById("products-group");
    if (!select) return;
    select.addEventListener("change", function () {
      state.groupFilter = select.value;
      state.page = 1;
      if (state.view === "detail") showList();
      loadProducts(1, false);
    });
  }

  function bindSearchInput() {
    var input = document.getElementById("products-search");
    if (!input) return;
    input.addEventListener("input", function () {
      state.searchQuery = input.value || "";
      if (state.view === "list") {
        renderList();
      }
    });
  }

  function init(profile) {
    var root = PlombirLayout.mountLayout({
      mode: "full",
      profile: profile,
      activeMenuId: "products",
      pageTitle: "Продукция ЧИСТАЯ ЛИНИЯ",
    });
    if (!root) return;

    root.innerHTML = renderShell();
    bindGroupSelect();
    bindSearchInput();
    loadGroups();

    var productId = getProductIdFromUrl();
    if (productId) {
      state.view = "detail";
      openDetail(productId);
    }

    loadProducts(1, false);
  }

  PlombirAuth.requireAuth().then(function (profile) {
    if (profile) init(profile);
  });
})();
