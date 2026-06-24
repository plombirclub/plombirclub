/**
 * Общий layout ЛК: шапка, боковое меню, блок поддержки.
 */
(function (global) {
  "use strict";

  var MENU_ITEMS = [
    { id: "profile", label: "Профиль", href: "/pages/profile.html", icon: "user" },
    { id: "news", label: "Условия акции", href: "/pages/news.html", icon: "news" },
    { id: "materials", label: "Материалы", href: "/pages/materials.html", icon: "materials" },
    { id: "products", label: "Продукция<br>ЧИСТАЯ&nbsp;ЛИНИЯ", href: "/pages/products.html", icon: "products" },
    { id: "points", label: "БАЛЛЫ", href: "/pages/points.html", icon: "points" },
    { id: "catalog", label: "Каталог призов", href: "/pages/catalog.html", icon: "catalog" },
    { id: "analytics", label: "Аналитика", href: "/pages/analytics.html", icon: "analytics" },
    { id: "faq", label: "Частые вопросы", href: "/pages/faq.html", icon: "faq" },
    { id: "instructions", label: "Инструкция для участников", href: "/pages/instructions.html", icon: "instructions" },
    { id: "notifications", label: "Уведомления", href: "/pages/notifications.html", icon: "bell" },
  ];

  function iconSvg(name) {
    var icons = {
      user: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 12a5 5 0 1 0-5-5 5 5 0 0 0 5 5Zm0 2c-4.4 0-8 2.2-8 5v1h16v-1c0-2.8-3.6-5-8-5Z"/></svg>',
      news: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h9l3 3v13H6V4Zm2 4h8v2H8V8Zm0 4h8v2H8v-2Zm0 4h5v2H8v-2Z"/></svg>',
      materials: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v4H4V4Zm0 6h10v10H4V10Zm12 0h4v10h-4V10Z"/></svg>',
      products: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16l-1 13H5L4 7Zm2-3h12v2H6V4Z"/></svg>',
      points: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2 4 6v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V6l-8-4Zm0 3.1 4.8 2.4L12 9.9 7.2 7.5 12 5.1Zm-6 6.3V9.4l5 2.5v7.2c-2.9-1.2-5-4.5-5-7.7Zm7 7.7v-7.2l5-2.5v2c0 3.2-2.1 6.5-5 7.7Z"/></svg>',
      catalog: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16v12H4V6Zm2 2v8h12V8H6Zm2 2h3v4H8v-4Zm5 0h3v4h-3v-4Z"/></svg>',
      analytics: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19h16v2H4v-2Zm3-4h2v3H7v-3Zm4-5h2v8h-2V10Zm4-3h2v11h-2V7Z"/></svg>',
      faq: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm1 15h-2v-2h2v2Zm0-4h-2a3 3 0 1 1 3-3h2a5 5 0 1 0-5 5Z"/></svg>',
      instructions: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h9l3 3v13H6V4Zm2 4h8v2H8V8Zm0 4h8v2H8v-2Z"/></svg>',
      bell: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 0 0-5-6.7V3a2 2 0 1 0-4 0v1.3A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2Z"/></svg>',
    };
    return icons[name] || icons.user;
  }

  function renderMenuItems(activeId, disabled) {
    return MENU_ITEMS.map(function (item) {
      var isActive = item.id === activeId;
      var cls = "menu-item" + (isActive ? " menu-item--active" : "") + (disabled ? " menu-item--disabled" : "");
      var href = disabled ? "#" : item.href;
      var badge =
        item.id === "notifications"
          ? '<span class="menu-item__badge" id="menu-notifications-badge" hidden></span>'
          : "";
      return (
        '<a class="' + cls + '" href="' + href + '" data-menu-id="' + item.id + '">' +
          '<span class="menu-item__icon">' + iconSvg(item.icon) + "</span>" +
          '<span class="menu-item__label">' + item.label + "</span>" +
          badge +
        "</a>"
      );
    }).join("");
  }

  function updateNotificationBadge(count) {
    var badge = document.getElementById("menu-notifications-badge");
    if (!badge) return;
    var value = Number(count || 0);
    if (value <= 0) {
      badge.hidden = true;
      badge.textContent = "";
    } else {
      badge.hidden = false;
      badge.textContent = value > 99 ? "99+" : String(value);
    }
    if (global.PlombirSupportFab && global.PlombirSupportFab.updateBadge) {
      global.PlombirSupportFab.updateBadge(value);
    }
  }

  function loadNotificationBadge() {
    PlombirApi.get("/notifications/?page=1&limit=1").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) return;
      var data = result.data.data || {};
      updateNotificationBadge(data.unread_count);
    });
  }

  function renderSupportBlock(contacts) {
    contacts = contacts || {};
    var phone = contacts.phone || "";
    var email = contacts.email || "";
    var workHours = contacts.work_hours || "";
    var text = contacts.text || "";

    if (!phone && !email && !text) {
      return (
        '<div class="sidebar-support">' +
          '<p class="sidebar-support__title">Техническая поддержка</p>' +
          '<p class="sidebar-support__text">Контакты будут доступны после завершения регистрации.</p>' +
        "</div>"
      );
    }

    var lines = [];
    if (text) lines.push('<p class="sidebar-support__text">' + escapeHtml(text) + "</p>");
    if (phone) lines.push('<a class="sidebar-support__link" href="tel:' + escapeHtml(phone) + '">' + escapeHtml(phone) + "</a>");
    if (email) lines.push('<a class="sidebar-support__link" href="mailto:' + escapeHtml(email) + '">' + escapeHtml(email) + "</a>");
    if (workHours) lines.push('<p class="sidebar-support__hours">' + escapeHtml(workHours) + "</p>");

    return (
      '<div class="sidebar-support">' +
        '<p class="sidebar-support__title">Техническая поддержка</p>' +
        lines.join("") +
      "</div>"
    );
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function personalNameParts(profile) {
    return [profile.last_name, profile.first_name, profile.middle_name].filter(Boolean);
  }

  function userInitials(profile) {
    var parts = personalNameParts(profile);
    if (parts.length >= 2) {
      return (parts[0].charAt(0) + parts[1].charAt(0)).toUpperCase();
    }
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    var fallback = profile.full_name || profile.email || "U";
    var tokens = String(fallback).trim().split(/\s+/);
    if (tokens.length >= 2) return (tokens[0].charAt(0) + tokens[1].charAt(0)).toUpperCase();
    return tokens[0].charAt(0).toUpperCase();
  }

  function renderSidebarUser(profile, mode) {
    if (mode === "first-login" || !profile) return "";
    var distributor = profile.distributor_name ? escapeHtml(profile.distributor_name) : "";
    var userName = escapeHtml(userDisplayName(profile));
    var initials = escapeHtml(userInitials(profile));
    return (
      '<div class="sidebar__user">' +
        '<div class="sidebar__user-avatar" aria-hidden="true">' + initials + "</div>" +
        '<div class="sidebar__user-info">' +
          '<p class="sidebar__user-name">' + userName + "</p>" +
          (distributor ? '<p class="sidebar__user-distributor">' + distributor + "</p>" : "") +
        "</div>" +
        '<button type="button" class="sidebar__logout" id="sidebar-logout" aria-label="Выйти">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h5v-2H5V5h5V3Zm11 7-4-4v3H9v2h8v3l4-4Z"/></svg>' +
        "</button>" +
      "</div>"
    );
  }

  function userDisplayName(profile) {
    var parts = personalNameParts(profile);
    if (parts.length) return parts.join(" ");
    if (profile.full_name) return profile.full_name;
    return profile.email || "Участник";
  }

  function updateUserDisplay(profile) {
    if (!profile) return;
    var name = userDisplayName(profile);
    var initials = userInitials(profile);

    var headerName = document.querySelector(".header-user__name");
    if (headerName) headerName.textContent = name;

    var sidebarName = document.querySelector(".sidebar__user-name");
    if (sidebarName) sidebarName.textContent = name;

    var avatar = document.querySelector(".sidebar__user-avatar");
    if (avatar) avatar.textContent = initials;

    var profileAvatar = document.querySelector(".profile-avatar__circle");
    if (profileAvatar) profileAvatar.textContent = initials;
  }

  function mountLayout(options) {
    options = options || {};
    var root = document.getElementById("app-layout");
    if (!root) return;

    var mode = options.mode || "full";
    var profile = options.profile || {};
    var activeId = options.activeMenuId || "";
    var pageTitle = options.pageTitle || "";
    var menuDisabled = !!options.menuDisabled;

    if (mode === "auth") {
      root.innerHTML =
        '<div class="auth-shell">' +
          '<div class="auth-shell__brand">' +
            '<div class="brand-logo" aria-hidden="true">CL</div>' +
            '<p class="brand-logo__title">ЧИСТАЯ ЛИНИЯ</p>' +
            '<p class="brand-logo__subtitle">Промо-портал</p>' +
          "</div>" +
          '<div class="auth-shell__content" id="layout-content"></div>' +
          '<p class="auth-shell__support">Поддержка пользователей</p>' +
        "</div>";
      bindMobileMenu(null);
      return document.getElementById("layout-content");
    }

    var distributor = profile.distributor_name ? escapeHtml(profile.distributor_name) : "";
    var userName = escapeHtml(userDisplayName(profile));

    var sidebarHtml =
      '<aside class="sidebar" id="sidebar" aria-label="Меню личного кабинета">' +
        renderSidebarUser(profile, mode) +
        '<a class="sidebar__brand" href="/pages/home.html" aria-label="Чистая Линия">' +
          '<img class="brand-logo-img" src="/images/logo.png" alt="Чистая Линия">' +
        "</a>" +
        '<nav class="sidebar__nav">' + renderMenuItems(activeId, menuDisabled) + "</nav>" +
        '<div id="sidebar-support">' + renderSupportBlock() + "</div>" +
      "</aside>";

    var headerRight =
      mode === "first-login"
        ? '<button type="button" class="btn btn--ghost" id="layout-logout">Выйти</button>'
        : '<div class="header-user">' +
            (profile.role === "admin"
              ? '<a class="btn btn--secondary btn--sm" href="/admin/users.html">Админ-панель</a>'
              : "") +
            (distributor ? '<span class="header-user__distributor">' + distributor + "</span>" : "") +
            '<span class="header-user__name">' + userName + "</span>" +
            '<button type="button" class="btn btn--ghost" id="layout-logout">Выйти</button>' +
          "</div>";

    root.innerHTML =
      '<div class="body-panel' + (mode === "first-login" ? " body-panel--first-login" : "") + '">' +
        sidebarHtml +
        '<div class="body-panel__main">' +
          '<header class="header">' +
            '<button type="button" class="header__burger" id="menu-toggle" aria-label="Открыть меню" aria-expanded="false">' +
              '<span></span><span></span><span></span>' +
            "</button>" +
            '<div class="header__title-wrap">' +
              (pageTitle ? '<h1 class="header__title">' + escapeHtml(pageTitle) + "</h1>" : "") +
            "</div>" +
            '<a class="header__brand" href="/pages/home.html" aria-label="Чистая Линия">' +
              '<img class="brand-logo-img" src="/images/logo.png" alt="">' +
            "</a>" +
            '<div class="header__right">' + headerRight + "</div>" +
          "</header>" +
          '<main class="panel-content">' +
            (pageTitle ? '<h1 class="panel-content__page-title">' + escapeHtml(pageTitle) + "</h1>" : "") +
            '<div id="layout-content"></div>' +
          "</main>" +
        "</div>" +
        '<div class="sidebar-overlay" id="sidebar-overlay" hidden></div>' +
      "</div>";

    bindMobileMenu(document.getElementById("sidebar"));
    bindLogout();

    if (!menuDisabled && mode === "full" && profile.is_registration_complete) {
      loadSupportContacts();
      loadNotificationBadge();
    }

    return document.getElementById("layout-content");
  }

  function bindMobileMenu(sidebar) {
    var toggle = document.getElementById("menu-toggle");
    var overlay = document.getElementById("sidebar-overlay");
    if (!toggle || !sidebar) return;

    function closeMenu() {
      sidebar.classList.remove("sidebar--open");
      toggle.setAttribute("aria-expanded", "false");
      if (overlay) overlay.hidden = true;
      document.body.classList.remove("menu-open");
    }

    function openMenu() {
      sidebar.classList.add("sidebar--open");
      toggle.setAttribute("aria-expanded", "true");
      if (overlay) overlay.hidden = false;
      document.body.classList.add("menu-open");
    }

    toggle.addEventListener("click", function () {
      if (sidebar.classList.contains("sidebar--open")) closeMenu();
      else openMenu();
    });

    if (overlay) {
      overlay.addEventListener("click", closeMenu);
    }

    sidebar.querySelectorAll(".menu-item:not(.menu-item--disabled)").forEach(function (link) {
      link.addEventListener("click", closeMenu);
    });
  }

  function bindLogout() {
    function onLogout() {
      PlombirAuth.logout();
    }
    var btn = document.getElementById("layout-logout");
    if (btn) btn.addEventListener("click", onLogout);
    var sidebarBtn = document.getElementById("sidebar-logout");
    if (sidebarBtn) sidebarBtn.addEventListener("click", onLogout);
  }

  function loadSupportContacts() {
    PlombirApi.get("/content/support_contacts").then(function (result) {
      var container = document.getElementById("sidebar-support");
      if (!container || !result.response.ok || !result.data || !result.data.success) return;
      container.innerHTML = renderSupportBlock(result.data.data.value);
    });
  }

  function showAlert(container, message, type) {
    if (!container) return;
    container.innerHTML =
      '<div class="alert alert--' + (type || "error") + '" role="alert">' +
        escapeHtml(message) +
      "</div>";
  }

  function clearAlert(container) {
    if (container) container.innerHTML = "";
  }

  global.PlombirLayout = {
    mountLayout: mountLayout,
    showAlert: showAlert,
    clearAlert: clearAlert,
    escapeHtml: escapeHtml,
    updateNotificationBadge: updateNotificationBadge,
    updateUserDisplay: updateUserDisplay,
    userDisplayName: userDisplayName,
    userInitials: userInitials,
    MENU_ITEMS: MENU_ITEMS,
  };
})(window);
