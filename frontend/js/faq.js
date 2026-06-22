(function () {
  "use strict";

  function escape(value) {
    return PlombirLayout.escapeHtml(value || "");
  }

  function renderRichContent(htmlOrText) {
    var text = String(htmlOrText || "");
    if (text.indexOf("<") >= 0) {
      return text;
    }
    return escape(text).replace(/\n/g, "<br>");
  }

  function renderShell() {
    return (
      '<section class="content-page">' +
        '<div id="faq-alert"></div>' +
        '<div id="faq-content">' +
          '<p class="content-empty">Загружаем частые вопросы…</p>' +
        "</div>" +
      "</section>"
    );
  }

  function renderItems(items) {
    var container = document.getElementById("faq-content");
    if (!container) return;

    if (!items.length) {
      container.innerHTML = '<p class="content-empty">Вопросы пока не добавлены. Загляните позже.</p>';
      return;
    }

    container.innerHTML =
      '<div class="faq-list">' +
        items.map(function (item, index) {
          return (
            '<article class="faq-item" data-faq-index="' + index + '">' +
              '<button type="button" class="faq-item__question" aria-expanded="false">' +
                '<span>' + escape(item.question) + "</span>" +
                '<svg class="faq-item__icon" viewBox="0 0 24 24" aria-hidden="true">' +
                  '<path d="M7 10l5 5 5-5z"/>' +
                "</svg>" +
              "</button>" +
              '<div class="faq-item__answer" hidden>' + renderRichContent(item.answer) + "</div>" +
            "</article>"
          );
        }).join("") +
      "</div>";

    container.querySelectorAll(".faq-item__question").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var item = btn.closest(".faq-item");
        var answer = item.querySelector(".faq-item__answer");
        var isOpen = item.classList.contains("faq-item--open");
        if (isOpen) {
          item.classList.remove("faq-item--open");
          btn.setAttribute("aria-expanded", "false");
          answer.hidden = true;
        } else {
          item.classList.add("faq-item--open");
          btn.setAttribute("aria-expanded", "true");
          answer.hidden = false;
        }
      });
    });
  }

  function loadFaq() {
    var alertBox = document.getElementById("faq-alert");
    PlombirLayout.clearAlert(alertBox);

    PlombirApi.get("/content/faq").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить FAQ"),
          "error"
        );
        return;
      }

      var value = (result.data.data && result.data.data.value) || {};
      renderItems(value.items || []);
    });
  }

  function init(profile) {
    var root = PlombirLayout.mountLayout({
      mode: "full",
      profile: profile,
      activeMenuId: "faq",
      pageTitle: "Частые вопросы",
    });
    if (!root) return;

    root.innerHTML = renderShell();
    loadFaq();
  }

  PlombirAuth.requireAuth().then(function (profile) {
    if (profile) init(profile);
  });
})();
