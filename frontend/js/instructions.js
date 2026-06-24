(function () {
  "use strict";

  var PDFJS_WORKER = "/js/pdf.worker.min.js";
  var resizeTimer = null;

  var state = {
    data: { title: "", content: "", items: [] },
    activeItem: null,
    pdfDoc: null,
    pdfPage: 1,
    pdfTotal: 1,
    pdfReady: false,
  };

  function escape(value) {
    return PlombirLayout.escapeHtml(value || "");
  }

  function fileUrl(path) {
    if (!path) return "";
    if (path.indexOf("http://") === 0 || path.indexOf("https://") === 0) return path;
    if (path.indexOf("/") === 0) return path;
    return "/uploads/" + path.replace(/^\/+/, "");
  }

  function renderRichContent(htmlOrText) {
    var text = String(htmlOrText || "");
    if (!text) return "";
    if (text.indexOf("<") >= 0) return text;
    return "<p>" + escape(text).replace(/\n/g, "<br>") + "</p>";
  }

  function getPublishedItems() {
    return (state.data.items || []).filter(function (item) {
      return item.is_published !== false && item.file_path;
    });
  }

  function initPdfJs() {
    if (typeof pdfjsLib === "undefined") return false;
    pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER;
    return true;
  }

  function renderShell() {
    return (
      '<section class="content-page instructions-page">' +
        '<div id="instructions-alert"></div>' +
        '<div id="instructions-content"><p class="content-empty">Загружаем инструкцию…</p></div>' +
      "</section>"
    );
  }

  function itemSelectorHtml(items, activeId) {
    if (items.length <= 1) return "";
    return (
      '<div class="instructions-tabs" role="tablist">' +
        items.map(function (item) {
          var active = item.id === activeId ? " instructions-tabs__btn--active" : "";
          return (
            '<button type="button" class="instructions-tabs__btn' + active + '" data-item-id="' + escape(item.id) + '" role="tab">' +
              escape(item.title || "Инструкция") +
            "</button>"
          );
        }).join("") +
      "</div>"
    );
  }

  function viewerHtml(item) {
    var isPdf = item.content_type === "pdf";
    return (
      '<div class="instruction-viewer" id="instruction-viewer">' +
        '<div class="instruction-viewer__stage" id="instruction-stage">' +
          '<p class="instruction-viewer__loading" id="instruction-loading">Загружаем документ…</p>' +
          '<canvas id="instruction-canvas" hidden></canvas>' +
          '<img id="instruction-image" hidden alt="' + escape(item.title || "Инструкция") + '">' +
        "</div>" +
        '<div class="instruction-viewer__toolbar" id="instruction-toolbar"' + (isPdf ? "" : ' hidden') + ">" +
          '<button type="button" class="instruction-viewer__nav" id="instruction-prev" aria-label="Предыдущая страница">‹</button>' +
          '<div class="instruction-viewer__progress"><div class="instruction-viewer__progress-fill" id="instruction-progress"></div></div>' +
          '<span class="instruction-viewer__counter" id="instruction-counter">1 / 1</span>' +
          '<button type="button" class="instruction-viewer__nav" id="instruction-next" aria-label="Следующая страница">›</button>' +
          '<button type="button" class="instruction-viewer__fullscreen" id="instruction-fullscreen" aria-label="На весь экран">⛶</button>' +
        "</div>" +
      "</div>"
    );
  }

  function renderPage() {
    var container = document.getElementById("instructions-content");
    if (!container) return;

    var title = state.data.title || "Инструкция для участников";
    var intro = state.data.content || "";
    var items = getPublishedItems();

    if (!items.length && !intro) {
      container.innerHTML = '<p class="content-empty">Инструкция пока не добавлена. Загляните позже.</p>';
      return;
    }

    if (!items.length) {
      container.innerHTML =
        '<article class="content-card">' +
          '<h2 class="content-card__title">' + escape(title) + "</h2>" +
          '<div class="instructions-intro content-card__body">' + renderRichContent(intro) + "</div>" +
        "</article>";
      return;
    }

    if (!state.activeItem || !items.some(function (i) { return i.id === state.activeItem.id; })) {
      state.activeItem = items[0];
    }

    var introHtml = intro
      ? '<div class="instructions-intro content-card__body">' + renderRichContent(intro) + "</div>"
      : "";

    container.innerHTML =
      '<article class="content-card instructions-page__card">' +
        '<h2 class="content-card__title">' + escape(title) + "</h2>" +
        introHtml +
        itemSelectorHtml(items, state.activeItem.id) +
        '<div id="instruction-viewer-host">' + viewerHtml(state.activeItem) + "</div>" +
      "</article>";

    container.querySelectorAll(".instructions-tabs__btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-item-id");
        var next = items.find(function (i) { return i.id === id; });
        if (!next || (state.activeItem && state.activeItem.id === next.id)) return;
        state.activeItem = next;
        state.pdfDoc = null;
        state.pdfPage = 1;
        state.pdfTotal = 1;
        state.pdfReady = false;
        renderPage();
      });
    });

    mountViewerContent(state.activeItem);
  }

  function onResize() {
    if (!state.pdfReady || !state.pdfDoc) return;
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      renderPdfPage(state.pdfPage);
    }, 150);
  }

  function hideLoading() {
    var loading = document.getElementById("instruction-loading");
    if (loading) loading.hidden = true;
  }

  function showViewerError(message) {
    hideLoading();
    var stage = document.getElementById("instruction-stage");
    if (stage) {
      stage.innerHTML = '<p class="content-empty">' + escape(message) + "</p>";
    }
  }

  function bindPdfControls() {
    var prev = document.getElementById("instruction-prev");
    var next = document.getElementById("instruction-next");
    var fullscreen = document.getElementById("instruction-fullscreen");
    if (prev) {
      prev.addEventListener("click", function () {
        if (state.pdfPage > 1) renderPdfPage(state.pdfPage - 1);
      });
    }
    if (next) {
      next.addEventListener("click", function () {
        if (state.pdfPage < state.pdfTotal) renderPdfPage(state.pdfPage + 1);
      });
    }
    if (fullscreen) {
      fullscreen.addEventListener("click", function () {
        var el = document.getElementById("instruction-viewer");
        if (el && el.requestFullscreen) el.requestFullscreen();
      });
    }
  }

  function updateToolbar(page, total) {
    var counter = document.getElementById("instruction-counter");
    if (counter) counter.textContent = page + " / " + total;
    var fill = document.getElementById("instruction-progress");
    if (fill) fill.style.width = total ? Math.round((page / total) * 100) + "%" : "0%";
    var prev = document.getElementById("instruction-prev");
    var next = document.getElementById("instruction-next");
    if (prev) prev.disabled = page <= 1;
    if (next) next.disabled = page >= total;
  }

  function renderPdfPage(pageNum) {
    if (!state.pdfDoc) return;
    state.pdfPage = pageNum;
    state.pdfDoc.getPage(pageNum).then(function (page) {
      var canvas = document.getElementById("instruction-canvas");
      var stage = document.getElementById("instruction-stage");
      if (!canvas || !stage) return;
      canvas.hidden = false;
      hideLoading();
      var viewport = page.getViewport({ scale: 1 });
      var maxWidth = Math.max(stage.clientWidth - 16, 280);
      var scale = Math.min(maxWidth / viewport.width, 2.5);
      viewport = page.getViewport({ scale: scale });
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      canvas.style.width = "100%";
      canvas.style.height = "auto";
      return page.render({ canvasContext: canvas.getContext("2d"), viewport: viewport }).promise;
    }).then(function () {
      updateToolbar(state.pdfPage, state.pdfTotal);
    }).catch(function () {
      showViewerError("Не удалось показать страницу PDF.");
    });
  }

  function mountViewerContent(item) {
    state.pdfDoc = null;
    state.pdfPage = 1;
    state.pdfTotal = 1;
    state.pdfReady = false;

    var url = fileUrl(item.file_path);
    bindPdfControls();
    updateToolbar(1, 1);

    if (item.content_type === "image") {
      var img = document.getElementById("instruction-image");
      if (!img) return;
      img.onload = function () {
        hideLoading();
        img.hidden = false;
      };
      img.onerror = function () {
        showViewerError("Не удалось загрузить изображение.");
      };
      img.src = url;
      return;
    }

    if (item.content_type === "pdf" && initPdfJs()) {
      pdfjsLib.getDocument({ url: url, withCredentials: true }).promise.then(function (pdf) {
        state.pdfDoc = pdf;
        state.pdfTotal = pdf.numPages;
        state.pdfReady = true;
        updateToolbar(1, state.pdfTotal);
        requestAnimationFrame(function () {
          renderPdfPage(1);
        });
      }).catch(function () {
        showViewerError("Не удалось открыть PDF. Попробуйте обновить страницу.");
      });
      return;
    }

    showViewerError("Формат файла не поддерживается для просмотра.");
  }

  function loadInstructions() {
    PlombirApi.get("/content/instructions").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          document.getElementById("instructions-alert"),
          PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить инструкцию"),
          "error"
        );
        return;
      }
      state.data = (result.data.data && result.data.data.value) || { title: "", content: "", items: [] };
      renderPage();
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
    window.addEventListener("resize", onResize);
    loadInstructions();
  }

  PlombirAuth.requireAuth().then(function (profile) {
    if (profile) init(profile);
  });
})();
