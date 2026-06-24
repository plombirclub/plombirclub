(function () {
  "use strict";

  var state = {
    items: [],
    page: 1,
    totalPages: 1,
    unreadCount: 0,
    loading: false,
  };

  function escape(value) {
    return PlombirLayout.escapeHtml(value || "");
  }

  function formatDate(value) {
    if (!value) return "";
    var date = new Date(value);
    if (isNaN(date.getTime())) return "";
    return date.toLocaleDateString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function notificationLink(item) {
    if (item.event_type === "task_published") {
      return "/pages/news.html";
    }
    if (item.event_type === "points_activation") {
      return "/pages/points.html";
    }
    if (
      item.event_type === "request_created" ||
      item.event_type === "request_confirmed" ||
      item.event_type === "request_rejected" ||
      item.event_type === "request_fulfilled" ||
      item.event_type === "request_phone_verification_required"
    ) {
      return "/pages/profile.html#orders";
    }
    if (item.event_type === "inn_verified" || item.event_type === "self_employed_verified") {
      return "/pages/profile.html";
    }
    return null;
  }

  function renderShell() {
    return (
      '<section class="content-page">' +
        '<div id="notifications-alert"></div>' +
        '<div class="notifications-toolbar">' +
          '<p class="notifications-summary" id="notifications-summary">Загружаем уведомления…</p>' +
          '<button type="button" class="btn btn--ghost" id="notifications-mark-all" hidden>' +
            "Отметить все прочитанными" +
          "</button>" +
        "</div>" +
        '<div id="notifications-list" class="notifications-list"></div>' +
        '<div class="content-pagination" id="notifications-pagination" hidden></div>' +
      "</section>"
    );
  }

  function updateSummary() {
    var summary = document.getElementById("notifications-summary");
    var markAllBtn = document.getElementById("notifications-mark-all");
    if (!summary) return;

    if (!state.items.length) {
      summary.textContent = "Уведомлений нет";
      if (markAllBtn) markAllBtn.hidden = true;
      return;
    }

    summary.textContent =
      state.unreadCount > 0
        ? "Непрочитанных: " + state.unreadCount
        : "Все уведомления прочитаны";

    if (markAllBtn) {
      markAllBtn.hidden = state.unreadCount === 0;
    }
  }

  function renderList() {
    var list = document.getElementById("notifications-list");
    var pagination = document.getElementById("notifications-pagination");
    if (!list) return;

    if (!state.items.length) {
      list.innerHTML = '<p class="content-empty">У вас пока нет уведомлений.</p>';
      if (pagination) pagination.hidden = true;
      updateSummary();
      return;
    }

    list.innerHTML = state.items
      .map(function (item) {
        var unreadClass = item.is_read ? "" : " notification-card--unread";
        var link = notificationLink(item);
        var badge = link
          ? '<span class="notification-card__badge">Открыть раздел</span>'
          : "";
        return (
          '<article class="notification-card' + unreadClass + '" data-id="' + escape(item.id) + '"' +
            (link ? ' data-link="' + escape(link) + '"' : "") +
            ">" +
            '<div class="notification-card__head">' +
              '<h3 class="notification-card__title">' + escape(item.title) + "</h3>" +
              '<time class="notification-card__date">' + escape(formatDate(item.created_at)) + "</time>" +
            "</div>" +
            '<p class="notification-card__message">' + escape(item.message) + "</p>" +
            badge +
          "</article>"
        );
      })
      .join("");

    list.querySelectorAll(".notification-card").forEach(function (card) {
      card.addEventListener("click", function () {
        handleCardClick(card);
      });
    });

    if (pagination) {
      if (state.page < state.totalPages) {
        pagination.hidden = false;
        pagination.innerHTML =
          '<button type="button" class="btn btn--secondary" id="notifications-load-more">Показать ещё</button>';
        document.getElementById("notifications-load-more").addEventListener("click", function () {
          loadNotifications(state.page + 1, true);
        });
      } else {
        pagination.hidden = true;
        pagination.innerHTML = "";
      }
    }

    updateSummary();
  }

  function handleCardClick(card) {
    var id = card.getAttribute("data-id");
    var link = card.getAttribute("data-link");
    var alertBox = document.getElementById("notifications-alert");

    var markPromise = PlombirApi.post("/notifications/read", {
      notification_ids: [id],
    });

    markPromise.then(function (result) {
      if (result.response.ok && result.data && result.data.success) {
        var data = result.data.data || {};
        state.unreadCount = Number(data.unread_count || 0);
        var item = state.items.find(function (entry) {
          return entry.id === id;
        });
        if (item) item.is_read = true;
        PlombirLayout.updateNotificationBadge(state.unreadCount);
        renderList();
      } else {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось отметить уведомление"),
          "error"
        );
      }

      if (link) {
        window.location.href = link;
      }
    });
  }

  function markAllRead() {
    var alertBox = document.getElementById("notifications-alert");
    PlombirApi.post("/notifications/read", { mark_all: true }).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось отметить уведомления"),
          "error"
        );
        return;
      }

      var data = result.data.data || {};
      state.unreadCount = Number(data.unread_count || 0);
      state.items.forEach(function (item) {
        item.is_read = true;
      });
      PlombirLayout.updateNotificationBadge(state.unreadCount);
      renderList();
      PlombirLayout.showAlert(alertBox, "Все уведомления отмечены прочитанными", "success");
    });
  }

  function loadNotifications(page, append) {
    if (state.loading) return;
    state.loading = true;

    PlombirApi.get("/notifications/?page=" + page + "&limit=20").then(function (result) {
      state.loading = false;
      var alertBox = document.getElementById("notifications-alert");

      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить уведомления"),
          "error"
        );
        return;
      }

      var data = result.data.data || {};
      var items = data.items || [];
      state.unreadCount = Number(data.unread_count || 0);
      state.page = (data.pagination && data.pagination.current_page) || page;
      state.totalPages = (data.pagination && data.pagination.total_pages) || 1;

      if (append) {
        state.items = state.items.concat(items);
      } else {
        state.items = items;
      }

      PlombirLayout.updateNotificationBadge(state.unreadCount);
      renderList();
    });
  }

  function init(profile) {
    var root = PlombirLayout.mountLayout({
      mode: "full",
      profile: profile,
      activeMenuId: "notifications",
      pageTitle: "Уведомления",
    });
    if (!root) return;

    root.innerHTML = renderShell();

    var markAllBtn = document.getElementById("notifications-mark-all");
    if (markAllBtn) {
      markAllBtn.addEventListener("click", markAllRead);
    }

    loadNotifications(1, false);
  }

  PlombirAuth.requireAuth().then(function (profile) {
    if (profile) init(profile);
  });
})();
