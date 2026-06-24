(function (global) {
  "use strict";

  var PDFJS_WORKER = "/js/pdf.worker.min.js";

  function escape(value) {
    if (global.PlombirLayout && global.PlombirLayout.escapeHtml) {
      return global.PlombirLayout.escapeHtml(value || "");
    }
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fileUrl(path) {
    if (!path) return "";
    if (path.indexOf("http://") === 0 || path.indexOf("https://") === 0) return path;
    if (path.indexOf("/") === 0) return path;
    return "/uploads/" + path.replace(/^\/+/, "");
  }

  function initPdfJs() {
    if (typeof pdfjsLib === "undefined") return false;
    pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER;
    return true;
  }

  function getStageWidth(stage) {
    if (!stage) return Math.min(global.innerWidth - 32, 800);
    var rect = stage.getBoundingClientRect();
    var width = rect.width || stage.clientWidth || stage.offsetWidth;
    if (!width || width < 50) {
      width = Math.min(global.innerWidth - 32, 800);
    }
    return Math.max(width - 16, 240);
  }

  function viewerHtml(item) {
    var isPdf = item.content_type === "pdf";
    return (
      '<div class="instruction-viewer document-viewer" data-document-viewer>' +
        '<div class="instruction-viewer__stage" data-viewer-stage>' +
          '<p class="instruction-viewer__loading" data-viewer-loading>Загружаем документ…</p>' +
          '<div class="instruction-viewer__page" data-viewer-page hidden>' +
            '<canvas data-viewer-canvas hidden></canvas>' +
            '<img data-viewer-image hidden alt="">' +
          "</div>" +
          '<div class="document-viewer__text" data-viewer-text hidden></div>' +
        "</div>" +
        '<div class="instruction-viewer__toolbar" data-viewer-toolbar"' + (isPdf ? "" : ' hidden') + ">" +
          '<button type="button" class="instruction-viewer__nav" data-viewer-prev aria-label="Предыдущая страница">‹</button>' +
          '<div class="instruction-viewer__progress"><div class="instruction-viewer__progress-fill" data-viewer-progress></div></div>' +
          '<span class="instruction-viewer__counter" data-viewer-counter">1 / 1</span>' +
          '<button type="button" class="instruction-viewer__nav" data-viewer-next aria-label="Следующая страница">›</button>' +
          '<button type="button" class="instruction-viewer__fullscreen" data-viewer-fullscreen aria-label="На весь экран">⛶</button>' +
        "</div>" +
      "</div>"
    );
  }

  function mount(host, item) {
    if (!host || !item) return null;

    host.innerHTML = viewerHtml(item);
    host.style.width = "100%";
    host.style.maxWidth = "100%";

    var root = host.querySelector("[data-document-viewer]");
    var state = {
      pdfDoc: null,
      pdfPage: 1,
      pdfTotal: 1,
      item: item,
      root: root,
      resizeTimer: null,
    };

    function hideLoading() {
      var loading = root.querySelector("[data-viewer-loading]");
      if (loading) loading.hidden = true;
    }

    function showError(message) {
      hideLoading();
      var stage = root.querySelector("[data-viewer-stage]");
      if (stage) stage.innerHTML = '<p class="content-empty">' + escape(message) + "</p>";
    }

    function updateToolbar(page, total) {
      var counter = root.querySelector("[data-viewer-counter]");
      if (counter) counter.textContent = page + " / " + total;
      var fill = root.querySelector("[data-viewer-progress]");
      if (fill) fill.style.width = total ? Math.round((page / total) * 100) + "%" : "0%";
      var prev = root.querySelector("[data-viewer-prev]");
      var next = root.querySelector("[data-viewer-next]");
      if (prev) prev.disabled = page <= 1;
      if (next) next.disabled = page >= total;
    }

    function renderPdfPage(pageNum) {
      if (!state.pdfDoc) return;
      state.pdfPage = pageNum;
      state.pdfDoc.getPage(pageNum).then(function (page) {
        var canvas = root.querySelector("[data-viewer-canvas]");
        var pageWrap = root.querySelector("[data-viewer-page]");
        var img = root.querySelector("[data-viewer-image]");
        var stage = root.querySelector("[data-viewer-stage]");
        if (!canvas || !stage || !pageWrap) return;

        if (img) {
          img.hidden = true;
          img.style.display = "none";
        }

        pageWrap.hidden = false;
        canvas.hidden = false;
        canvas.style.display = "block";
        hideLoading();

        var baseViewport = page.getViewport({ scale: 1 });
        var maxWidth = getStageWidth(stage);
        var scale = Math.min(maxWidth / baseViewport.width, 2.5);
        var viewport = page.getViewport({ scale: scale });

        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);
        canvas.style.width = "100%";
        canvas.style.maxWidth = "100%";
        canvas.style.height = "auto";

        return page.render({ canvasContext: canvas.getContext("2d"), viewport: viewport }).promise;
      }).then(function () {
        updateToolbar(state.pdfPage, state.pdfTotal);
      }).catch(function () {
        showError("Не удалось показать страницу PDF.");
      });
    }

    function onResize() {
      if (!state.pdfDoc) return;
      clearTimeout(state.resizeTimer);
      state.resizeTimer = setTimeout(function () {
        renderPdfPage(state.pdfPage);
      }, 150);
    }

    function bindPdfControls() {
      var prev = root.querySelector("[data-viewer-prev]");
      var next = root.querySelector("[data-viewer-next]");
      var fullscreen = root.querySelector("[data-viewer-fullscreen]");
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
          if (root.requestFullscreen) root.requestFullscreen();
        });
      }
    }

    bindPdfControls();
    updateToolbar(1, 1);
    global.addEventListener("resize", onResize);

    if (item.text && !item.file_path) {
      hideLoading();
      var textHost = root.querySelector("[data-viewer-text]");
      if (textHost) {
        textHost.hidden = false;
        textHost.innerHTML = item.text.indexOf("<") >= 0
          ? item.text
          : "<p>" + escape(item.text).replace(/\n/g, "<br>") + "</p>";
      }
      return state;
    }

    var url = fileUrl(item.file_path);
    if (!url) {
      showError("Документ пока не добавлен администратором.");
      return state;
    }

    if (item.content_type === "image") {
      var imgEl = root.querySelector("[data-viewer-image]");
      var pageWrapImg = root.querySelector("[data-viewer-page]");
      var canvasEl = root.querySelector("[data-viewer-canvas]");
      if (!imgEl || !pageWrapImg) return state;
      if (canvasEl) {
        canvasEl.hidden = true;
        canvasEl.style.display = "none";
      }
      pageWrapImg.hidden = false;
      imgEl.onload = function () {
        hideLoading();
        imgEl.hidden = false;
        imgEl.style.display = "block";
      };
      imgEl.onerror = function () {
        showError("Не удалось загрузить изображение.");
      };
      imgEl.src = url;
      return state;
    }

    if (item.content_type === "pdf" && initPdfJs()) {
      pdfjsLib.getDocument({ url: url, withCredentials: true }).promise.then(function (pdf) {
        state.pdfDoc = pdf;
        state.pdfTotal = pdf.numPages;
        updateToolbar(1, state.pdfTotal);
        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            renderPdfPage(1);
          });
        });
      }).catch(function () {
        showError("Не удалось открыть PDF. Попробуйте обновить страницу.");
      });
      return state;
    }

    showError("Формат документа не поддерживается.");
    return state;
  }

  global.PlombirDocumentViewer = {
    mount: mount,
    fileUrl: fileUrl,
  };
})(window);
