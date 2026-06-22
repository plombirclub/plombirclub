(function () {
  "use strict";

  function escape(value) {
    return PlombirLayout.escapeHtml(value || "");
  }

  function renderRichContent(htmlOrText) {
    var text = String(htmlOrText || "");
    if (!text) return "";
    if (text.indexOf("<") >= 0) {
      return text;
    }
    return "<p>" + escape(text).replace(/\n/g, "<br>") + "</p>";
  }

  function fileUrl(path) {
    if (!path) return "";
    if (path.indexOf("http") === 0 || path.indexOf("/") === 0) return path;
    return "/uploads/" + path;
  }

  function renderShell() {
    return (
      '<section class="content-page">' +
        '<div id="instructions-alert"></div>' +
        '<div id="instructions-content">' +
          '<p class="content-empty">Загружаем инструкцию…</p>' +
        "</div>" +
      "</section>"
    );
  }

  function renderContent(value) {
    var container = document.getElementById("instructions-content");
    if (!container) return;

    var title = value.title || "Инструкция для участников";
    var intro = value.content || "";
    var items = value.items || [];

    var introHtml = intro
      ? '<div class="instructions-intro content-card__body">' + renderRichContent(intro) + "</div>"
      : "";

    var listHtml = "";
    if (items.length) {
      listHtml =
        '<div class="instructions-list">' +
          items.map(function (item) {
            var linkHtml = "";
            if (item.file_path) {
              linkHtml =
                '<a class="instruction-item__link" href="' +
                escape(fileUrl(item.file_path)) +
                '" target="_blank" rel="noopener noreferrer">Скачать материал</a>';
            }
            return (
              '<article class="instruction-item">' +
                '<h3 class="instruction-item__title">' + escape(item.title) + "</h3>" +
                (item.description
                  ? '<p class="instruction-item__desc">' + escape(item.description) + "</p>"
                  : "") +
                linkHtml +
              "</article>"
            );
          }).join("") +
        "</div>";
    } else if (!intro) {
      container.innerHTML = '<p class="content-empty">Инструкция пока не добавлена. Загляните позже.</p>';
      return;
    }

    container.innerHTML =
      '<article class="content-card">' +
        '<h2 class="content-card__title">' + escape(title) + "</h2>" +
        introHtml +
        listHtml +
      "</article>";
  }

  function loadInstructions() {
    var alertBox = document.getElementById("instructions-alert");
    PlombirLayout.clearAlert(alertBox);

    PlombirApi.get("/content/instructions").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить инструкцию"),
          "error"
        );
        return;
      }

      var value = (result.data.data && result.data.data.value) || {};
      renderContent(value);
    });
  }

  function init(profile) {
    var root = PlombirLayout.mountLayout({
      mode: "full",
      profile: profile,
      activeMenuId: "instructions",
      pageTitle: "Инструкция для участников",
    });
    if (!root) return;

    root.innerHTML = renderShell();
    loadInstructions();
  }

  PlombirAuth.requireAuth().then(function (profile) {
    if (profile) init(profile);
  });
})();
