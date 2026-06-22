/**
 * Плавающая кнопка поддержки (как на референсе) + бейдж непрочитанных.
 */
(function (global) {
  "use strict";

  var supportEmail = "";
  var supportPhone = "";

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function updateBadge(count) {
    var badge = document.getElementById("support-fab-badge");
    if (!badge) return;
    var value = Number(count || 0);
    if (value <= 0) {
      badge.hidden = true;
      badge.textContent = "";
      return;
    }
    badge.hidden = false;
    badge.textContent = value > 99 ? "99+" : String(value);
  }

  function loadSupportContacts() {
    if (!global.PlombirApi) return;
    global.PlombirApi.get("/content/support_contacts").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) return;
      var contacts = result.data.data.value || {};
      supportEmail = contacts.email || "";
      supportPhone = contacts.phone || "";
    });
  }

  function loadUnreadBadge() {
    if (!global.PlombirApi) return;
    global.PlombirApi.get("/notifications/?page=1&limit=1").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) return;
      var data = result.data.data || {};
      updateBadge(data.unread_count);
    });
  }

  function handleFabClick() {
    if (supportEmail) {
      window.location.href = "mailto:" + supportEmail;
      return;
    }
    if (supportPhone) {
      window.location.href = "tel:" + supportPhone.replace(/\s/g, "");
      return;
    }
    window.location.href = "/pages/notifications.html";
  }

  function mountSupportFab() {
    if (document.getElementById("support-fab")) return;
    if (document.querySelector(".auth-shell")) return;

    var fab = document.createElement("button");
    fab.type = "button";
    fab.className = "support-fab";
    fab.id = "support-fab";
    fab.setAttribute("aria-label", "Связаться с поддержкой");
    fab.innerHTML =
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2Zm0 4-8 5L4 8V6l8 5 8-5v2Z"/></svg>' +
      '<span class="support-fab__badge" id="support-fab-badge" hidden></span>';

    fab.addEventListener("click", handleFabClick);
    document.body.appendChild(fab);

    loadSupportContacts();
    loadUnreadBadge();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountSupportFab);
  } else {
    mountSupportFab();
  }

  global.PlombirSupportFab = {
    mount: mountSupportFab,
    updateBadge: updateBadge,
  };
})(window);
