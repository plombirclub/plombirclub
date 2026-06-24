(function () {
  "use strict";

  var DOC_KEYS = {
    personal_data: "Согласие на обработку персональных данных (ФЗ-152)",
    program_rules: "Пользовательское соглашение",
    email_notifications: "Согласие на получение email-уведомлений",
  };

  function getDocKey() {
    var params = new URLSearchParams(window.location.search);
    return params.get("doc") || "";
  }

  function renderShell(title) {
    return (
      '<section class="content-page agreement-page">' +
        '<div id="agreement-alert"></div>' +
        '<article class="content-card agreement-page__card">' +
          '<div id="agreement-viewer-host"><p class="content-empty">Загружаем документ…</p></div>' +
          '<div class="agreement-page__actions">' +
            '<button type="button" class="btn btn--ghost" id="agreement-back">← Назад</button>' +
          "</div>" +
        "</article>" +
      "</section>"
    );
  }

  function loadDocument(docKey, profile) {
    var fallbackTitle = DOC_KEYS[docKey] || "Документ";
    PlombirApi.get("/content/legal_documents").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          document.getElementById("agreement-alert"),
          PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить документ"),
          "error"
        );
        return;
      }

      var documents = (result.data.data && result.data.data.value && result.data.data.value.documents) || {};
      var item = documents[docKey];
      if (!item) {
        document.getElementById("agreement-viewer-host").innerHTML =
          '<p class="content-empty">Документ не найден.</p>';
        return;
      }

      var title = item.title || fallbackTitle;
      document.title = title + " — ЧИСТАЯ ЛИНИЯ";
      PlombirDocumentViewer.mount(document.getElementById("agreement-viewer-host"), item);
    });
  }

  function init(profile) {
    var docKey = getDocKey();
    if (!DOC_KEYS[docKey]) {
      window.location.href = PlombirAuth.HOME_PAGE;
      return;
    }

    var root = PlombirLayout.mountLayout({
      mode: profile && profile.is_registration_complete ? "full" : "first-login",
      profile: profile,
      activeMenuId: profile && profile.is_registration_complete ? "profile" : null,
      pageTitle: DOC_KEYS[docKey],
      menuDisabled: !(profile && profile.is_registration_complete),
    });
    if (!root) return;

    root.innerHTML = renderShell(DOC_KEYS[docKey]);
    document.getElementById("agreement-back").addEventListener("click", function () {
      if (window.history.length > 1) window.history.back();
      else window.location.href = profile && profile.is_registration_complete
        ? "/pages/profile.html"
        : "/pages/first-login.html";
    });

    loadDocument(docKey, profile);
  }

  PlombirAuth.requireAuth({ allowIncomplete: true }).then(function (profile) {
    if (profile) init(profile);
  });
})();
