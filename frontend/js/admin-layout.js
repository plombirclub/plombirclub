/**
 * Общий layout админ-панели.
 */
(function (global) {
  "use strict";

  var MENU_ITEMS = [
    { id: "users", label: "Пользователи", href: "/admin/users.html" },
    { id: "distributors", label: "Дистрибьюторы", href: "/admin/distributors.html" },
    { id: "import", label: "Импорт Excel", href: "/admin/import.html" },
    { id: "points", label: "Баллы", href: "/admin/points.html" },
    { id: "orders", label: "Заявки", href: "/admin/orders.html" },
    { id: "prizes", label: "Каталог призов", href: "/admin/prizes.html" },
    { id: "tasks", label: "Условия акции", href: "/admin/tasks.html" },
    { id: "materials", label: "Материалы", href: "/admin/materials.html" },
    { id: "content", label: "Контент", href: "/admin/content.html" },
    { id: "products", label: "Продукция", href: "/admin/products.html" },
    { id: "reports", label: "Отчёты", href: "/admin/reports.html" },
    { id: "logs", label: "Логи", href: "/admin/logs.html" },
    { id: "notifications", label: "Уведомления", href: "/admin/notifications.html" },
  ];

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderMenu(activeId) {
    return MENU_ITEMS.map(function (item) {
      var cls = "admin-menu__link" + (item.id === activeId ? " admin-menu__link--active" : "");
      return '<a class="' + cls + '" href="' + item.href + '">' + escapeHtml(item.label) + "</a>";
    }).join("");
  }

  function mountAdminLayout(options) {
    options = options || {};
    var root = document.getElementById("admin-layout");
    if (!root) return null;

    var profile = options.profile || {};
    var activeId = options.activeMenuId || "";
    var pageTitle = options.pageTitle || "Админ-панель";
    var adminName = escapeHtml(profile.full_name || profile.email || "Администратор");

    root.innerHTML =
      '<div class="admin-shell">' +
        '<aside class="admin-sidebar" id="admin-sidebar">' +
          '<div class="admin-sidebar__brand">' +
            '<img class="brand-logo-img" src="/images/logo.png" alt="Чистая Линия">' +
            '<p class="admin-sidebar__subtitle">Админ-панель</p>' +
          "</div>" +
          '<nav class="admin-menu" aria-label="Меню админки">' + renderMenu(activeId) + "</nav>" +
        "</aside>" +
        '<div class="admin-main">' +
          '<header class="admin-header">' +
            '<button type="button" class="admin-header__burger" id="admin-menu-toggle" aria-label="Меню">' +
              "<span></span><span></span><span></span>" +
            "</button>" +
            '<h1 class="admin-header__title">' + escapeHtml(pageTitle) + "</h1>" +
            '<div class="admin-header__actions">' +
              '<span class="admin-header__user">' + adminName + "</span>" +
              '<button type="button" class="btn btn--ghost btn--sm" id="admin-logout">Выйти</button>' +
            "</div>" +
          "</header>" +
          '<main class="admin-content" id="admin-content"></main>' +
        "</div>" +
        '<div class="admin-overlay" id="admin-overlay" hidden></div>' +
      "</div>";

    bindMobileMenu();
    document.getElementById("admin-logout").addEventListener("click", function () {
      PlombirAuth.logout();
    });

    return document.getElementById("admin-content");
  }

  function bindMobileMenu() {
    var sidebar = document.getElementById("admin-sidebar");
    var toggle = document.getElementById("admin-menu-toggle");
    var overlay = document.getElementById("admin-overlay");
    if (!sidebar || !toggle) return;

    function closeMenu() {
      sidebar.classList.remove("admin-sidebar--open");
      if (overlay) overlay.hidden = true;
      document.body.classList.remove("menu-open");
    }

    function openMenu() {
      sidebar.classList.add("admin-sidebar--open");
      if (overlay) overlay.hidden = false;
      document.body.classList.add("menu-open");
    }

    toggle.addEventListener("click", function () {
      if (sidebar.classList.contains("admin-sidebar--open")) closeMenu();
      else openMenu();
    });
    if (overlay) overlay.addEventListener("click", closeMenu);
    sidebar.querySelectorAll(".admin-menu__link").forEach(function (link) {
      link.addEventListener("click", closeMenu);
    });
  }

  function showToast(container, message, type) {
    if (!container) return;
    container.innerHTML =
      '<div class="alert alert--' + (type || "info") + '" role="status">' +
        escapeHtml(message) +
      "</div>";
  }

  function clearToast(container) {
    if (container) container.innerHTML = "";
  }

  function formatDate(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatMoney(value) {
    var num = Number(value);
    if (isNaN(num)) return "—";
    return num.toLocaleString("ru-RU") + " ₽";
  }

  function shortId(id) {
    if (!id) return "—";
    return String(id).slice(0, 8).toUpperCase();
  }

  global.PlombirAdminLayout = {
    mountAdminLayout: mountAdminLayout,
    escapeHtml: escapeHtml,
    showToast: showToast,
    clearToast: clearToast,
    formatDate: formatDate,
    formatMoney: formatMoney,
    shortId: shortId,
    MENU_ITEMS: MENU_ITEMS,
  };
})(window);
