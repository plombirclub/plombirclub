(function () {
  "use strict";

  var state = {
    view: "list",
    items: [],
    completedCount: 0,
    publishedCount: 0,
    activeMaterial: null,
    loading: false,
  };

  function escape(value) {
    return PlombirLayout.escapeHtml(value || "");
  }

  function statusClass(status) {
    if (status === "started") return "material-card__status--started";
    if (status === "completed") return "material-card__status--completed";
    return "material-card__status--not_started";
  }

  function fileUrl(path) {
    if (!path) return "";
    if (path.indexOf("http://") === 0 || path.indexOf("https://") === 0) return path;
    if (path.indexOf("/") === 0) return path;
    return "/uploads/" + path.replace(/^\/+/, "");
  }

  function isNewMaterial(item) {
    if (!item.created_at) return false;
    var created = new Date(item.created_at);
    var weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return created >= weekAgo;
  }

  function coverHtml(item) {
    if (item.content_type === "image" && item.file_path) {
      return '<img class="material-card__img" src="' + escape(fileUrl(item.file_path)) + '" alt="">';
    }
    if (item.content_type === "video" && item.file_path) {
      return (
        '<video class="material-card__img" muted playsinline preload="metadata">' +
          '<source src="' + escape(fileUrl(item.file_path)) + '">' +
        "</video>"
      );
    }
    return '<div class="material-card__placeholder" aria-hidden="true"><span>Материал</span></div>';
  }

  function renderDonut(percent, label, sub) {
    var radius = 42;
    var circumference = 2 * Math.PI * radius;
    var offset = circumference - (percent / 100) * circumference;
    return (
      '<article class="materials-stat">' +
        '<div class="materials-stat__ring">' +
          '<svg viewBox="0 0 100 100" aria-hidden="true">' +
            '<circle class="materials-stat__ring-bg" cx="50" cy="50" r="' + radius + '"></circle>' +
            '<circle class="materials-stat__ring-fill" cx="50" cy="50" r="' + radius + '" ' +
              'stroke-dasharray="' + circumference + '" stroke-dashoffset="' + offset + '"></circle>' +
          "</svg>" +
          '<span class="materials-stat__percent">' + escape(String(percent)) + "%</span>" +
        "</div>" +
        '<p class="materials-stat__label">' + escape(label) + "</p>" +
        (sub ? '<p class="materials-stat__sub">' + escape(sub) + "</p>" : "") +
      "</article>"
    );
  }

  function renderStats() {
    var studiedPercent = state.publishedCount
      ? Math.round((state.completedCount / state.publishedCount) * 100)
      : 0;
    return (
      '<div class="materials-stats">' +
        renderDonut(
          studiedPercent,
          state.completedCount + "/" + state.publishedCount + " Изучено материалов"
        ) +
        renderDonut(0, "0/0 Пройдено тестов", "Тесты не используются") +
        renderDonut(0, "Средний процент верных ответов") +
      "</div>"
    );
  }

  function renderShell() {
    return (
      '<section class="materials-page">' +
        '<div id="materials-alert"></div>' +
        '<div id="materials-stats">' + renderStats() + "</div>" +
        '<div id="materials-content">' +
          '<p class="content-empty">Загружаем материалы…</p>' +
        "</div>" +
      "</section>"
    );
  }

  function renderList() {
    var container = document.getElementById("materials-content");
    if (!container) return;

    if (!state.items.length) {
      container.innerHTML =
        '<p class="content-empty">Обучающие материалы пока не опубликованы.</p>';
      return;
    }

    var cards = state.items
      .map(function (item) {
        var progress = item.progress || {};
        var badge = isNewMaterial(item) ? '<span class="material-card__badge">Новое</span>' : "";
        return (
          '<article class="material-card" data-material-id="' + escape(item.id) + '">' +
            '<div class="material-card__media">' +
              badge +
              coverHtml(item) +
            "</div>" +
            '<div class="material-card__body">' +
              '<h3 class="material-card__title">' + escape(item.title) + "</h3>" +
              '<p class="material-card__status ' + statusClass(progress.status) + '">' +
                escape(progress.status_label || "Не начат") +
              "</p>" +
              '<div class="material-card__footer">' +
                '<button type="button" class="btn btn--primary btn--sm material-card__view" data-material-id="' +
                  escape(item.id) +
                  '">Просмотр</button>' +
              "</div>" +
            "</div>" +
          "</article>"
        );
      })
      .join("");

    container.innerHTML = '<div class="materials-grid">' + cards + "</div>";

    container.querySelectorAll(".material-card__view").forEach(function (btn) {
      btn.addEventListener("click", function (event) {
        event.stopPropagation();
        openDetail(btn.getAttribute("data-material-id"));
      });
    });

    container.querySelectorAll(".material-card").forEach(function (card) {
      card.addEventListener("click", function () {
        openDetail(card.getAttribute("data-material-id"));
      });
    });
  }

  function viewerHtml(material) {
    var url = fileUrl(material.file_path);
    if (material.content_type === "video" && url) {
      return (
        '<div class="material-detail__viewer">' +
          '<video controls playsinline id="material-video" data-material-id="' + escape(material.id) + '">' +
            '<source src="' + escape(url) + '">' +
          "</video>" +
        "</div>"
      );
    }
    if (material.content_type === "image" && url) {
      return (
        '<div class="material-detail__viewer">' +
          '<img src="' + escape(url) + '" alt="' + escape(material.title) + '">' +
        "</div>"
      );
    }
    if ((material.content_type === "pdf" || material.content_type === "pptx") && url) {
      return (
        '<div class="material-detail__viewer">' +
          '<iframe src="' + escape(url) + '" title="' + escape(material.title) + '"></iframe>' +
        "</div>"
      );
    }
    if (material.description) {
      return (
        '<div class="material-detail__viewer" style="padding:1rem">' +
          "<p>" + escape(material.description).replace(/\n/g, "<br>") + "</p>" +
        "</div>"
      );
    }
    return '<p class="material-detail__hint">Файл материала недоступен.</p>';
  }

  function renderDetail() {
    var container = document.getElementById("materials-content");
    if (!container || !state.activeMaterial) return;

    var material = state.activeMaterial;
    var progress = material.progress || {};
    var statusText = progress.status_label || "Не начат";
    var actionBlock = "";

    if (progress.status === "completed") {
      actionBlock = '<p class="material-detail__progress">Материал изучен</p>';
    } else if (progress.status === "not_started") {
      actionBlock =
        '<div class="material-detail__actions">' +
          '<p class="material-detail__hint">Приступите к изучению!</p>' +
          '<button type="button" class="btn btn--primary" id="material-start">Начать изучение</button>' +
        "</div>";
    } else {
      actionBlock =
        '<div class="material-detail__actions">' +
          '<p class="material-detail__hint">Продолжайте изучение материала</p>' +
        "</div>";
    }

    container.innerHTML =
      '<div class="material-detail">' +
        '<button type="button" class="material-back" id="material-back">← Назад</button>' +
        '<article class="content-card material-detail__card">' +
          '<h2 class="content-card__title">' + escape(material.title) + "</h2>" +
          '<p class="content-card__meta">Статус: ' + escape(statusText) + "</p>" +
          (material.description
            ? '<div class="content-card__body"><p>' + escape(material.description).replace(/\n/g, "<br>") + "</p></div>"
            : "") +
          viewerHtml(material) +
          actionBlock +
        "</article>" +
      "</div>";

    document.getElementById("material-back").addEventListener("click", showList);

    var startBtn = document.getElementById("material-start");
    if (startBtn) {
      startBtn.addEventListener("click", function () {
        trackProgress(material.id, { action: "open" });
      });
    }

    var video = document.getElementById("material-video");
    if (video) {
      video.addEventListener("timeupdate", function () {
        if (!video.duration) return;
        var percent = (video.currentTime / video.duration) * 100;
        if (percent >= 95 && !video.dataset.completed) {
          video.dataset.completed = "1";
          trackProgress(material.id, { action: "view_video", video_percent: percent });
        }
      });
    }
  }

  function getMaterialIdFromUrl() {
    return new URLSearchParams(window.location.search).get("material") || "";
  }

  function setMaterialUrl(materialId) {
    var url = new URL(window.location.href);
    if (materialId) url.searchParams.set("material", materialId);
    else url.searchParams.delete("material");
    window.history.replaceState({}, "", url.pathname + url.search);
  }

  function showList() {
    state.view = "list";
    state.activeMaterial = null;
    setMaterialUrl("");
    renderList();
  }

  function openDetail(materialId) {
    if (!materialId) return;
    state.view = "detail";
    setMaterialUrl(materialId);

    var cached = state.items.find(function (item) {
      return item.id === materialId;
    });
    if (cached) {
      state.activeMaterial = cached;
      renderDetail();
      if ((cached.progress || {}).status === "not_started") {
        trackProgress(materialId, { action: "open" }, true);
      }
      return;
    }

    PlombirApi.get("/materials/" + encodeURIComponent(materialId)).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          document.getElementById("materials-alert"),
          PlombirApi.extractErrorMessage(result.data, "Не удалось открыть материал"),
          "error"
        );
        return;
      }
      state.activeMaterial = result.data.data;
      renderDetail();
    });
  }

  function trackProgress(materialId, payload, silent) {
    PlombirApi.post("/materials/" + encodeURIComponent(materialId) + "/progress", payload).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        if (!silent) {
          PlombirLayout.showAlert(
            document.getElementById("materials-alert"),
            PlombirApi.extractErrorMessage(result.data, "Не удалось сохранить прогресс"),
            "error"
          );
        }
        return;
      }

      var progress = (result.data.data || {}).progress;
      state.items.forEach(function (item, index) {
        if (item.id === materialId) {
          state.items[index].progress = progress;
        }
      });
      if (state.activeMaterial && state.activeMaterial.id === materialId) {
        state.activeMaterial.progress = progress;
      }

      var completed = state.items.filter(function (item) {
        return item.progress && item.progress.status === "completed";
      }).length;
      state.completedCount = completed;

      var stats = document.getElementById("materials-stats");
      if (stats) stats.innerHTML = renderStats();

      if (state.view === "detail") renderDetail();
      else renderList();
    });
  }

  function loadMaterials() {
    if (state.loading) return;
    state.loading = true;

    PlombirApi.get("/materials/").then(function (result) {
      state.loading = false;
      var alertBox = document.getElementById("materials-alert");
      PlombirLayout.clearAlert(alertBox);

      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить материалы"),
          "error"
        );
        return;
      }

      var data = result.data.data || {};
      state.items = data.items || [];
      state.completedCount = data.completed_count || 0;
      state.publishedCount = data.published_count || 0;

      var stats = document.getElementById("materials-stats");
      if (stats) stats.innerHTML = renderStats();

      if (state.view === "detail" && state.activeMaterial) {
        var updated = state.items.find(function (item) {
          return item.id === state.activeMaterial.id;
        });
        if (updated) state.activeMaterial = updated;
        renderDetail();
      } else {
        renderList();
      }
    });
  }

  function init(profile) {
    var root = PlombirLayout.mountLayout({
      mode: "full",
      profile: profile,
      activeMenuId: "materials",
      pageTitle: "Материалы",
    });
    if (!root) return;

    root.innerHTML = renderShell();

    var materialId = getMaterialIdFromUrl();
    if (materialId) {
      state.view = "detail";
      openDetail(materialId);
    }

    loadMaterials();
  }

  PlombirAuth.requireAuth().then(function (profile) {
    if (profile) init(profile);
  });
})();
