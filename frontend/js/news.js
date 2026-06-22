(function () {
  "use strict";

  var MONTH_NAMES = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
  ];

  var state = {
    profile: null,
    view: "list",
    periodFilter: "all",
    tasks: [],
    activeTask: null,
    page: 1,
    totalPages: 1,
    loading: false,
    accepting: false,
  };

  function escape(value) {
    return PlombirLayout.escapeHtml(value || "");
  }

  function formatPeriodLabel(periodMonth) {
    var parts = String(periodMonth || "").split("-");
    if (parts.length !== 2) return periodMonth;
    var monthIndex = parseInt(parts[1], 10) - 1;
    if (monthIndex < 0 || monthIndex > 11) return periodMonth;
    return MONTH_NAMES[monthIndex] + " " + parts[0];
  }

  function formatPeriodUpper(periodMonth) {
    var label = formatPeriodLabel(periodMonth);
    var parts = label.split(" ");
    if (parts.length === 2) {
      return parts[0].toUpperCase() + " " + parts[1];
    }
    return label.toUpperCase();
  }

  function formatDate(value) {
    if (!value) return "";
    var date = new Date(value);
    if (isNaN(date.getTime())) return "";
    return date.toLocaleDateString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  }

  function buildPeriodOptions() {
    var options = [{ value: "all", label: "Все периоды" }];
    var now = new Date();
    for (var i = 0; i < 24; i += 1) {
      var date = new Date(now.getFullYear(), now.getMonth() - i, 1);
      var month = String(date.getMonth() + 1).padStart(2, "0");
      var value = date.getFullYear() + "-" + month;
      options.push({ value: value, label: formatPeriodLabel(value) });
    }
    return options;
  }

  function renderRichContent(htmlOrText) {
    var text = String(htmlOrText || "");
    if (text.indexOf("<") >= 0) {
      return text;
    }
    return "<p>" + escape(text).replace(/\n/g, "<br>") + "</p>";
  }

  function mediaHtml(task) {
    if (task.cover_image_url) {
      return '<img src="' + escape(task.cover_image_url) + '" alt="" class="news-card__img">';
    }
    return '<div class="news-card__placeholder" aria-hidden="true"><span>ЧИСТАЯ ЛИНИЯ</span></div>';
  }

  function getTaskIdFromUrl() {
    var params = new URLSearchParams(window.location.search);
    return params.get("task") || "";
  }

  function setTaskUrl(taskId) {
    var url = new URL(window.location.href);
    if (taskId) {
      url.searchParams.set("task", taskId);
    } else {
      url.searchParams.delete("task");
    }
    window.history.replaceState({}, "", url.pathname + url.search);
  }

  function renderShell() {
    var options = buildPeriodOptions();
    var selectHtml = options.map(function (opt) {
      var selected = opt.value === state.periodFilter ? " selected" : "";
      return '<option value="' + escape(opt.value) + '"' + selected + ">" + escape(opt.label) + "</option>";
    }).join("");

    return (
      '<section class="content-page news-page">' +
        '<div id="news-alert"></div>' +
        '<div class="news-toolbar">' +
          '<label class="field">' +
            '<span class="field__label">Период</span>' +
            '<select class="news-period-select" id="news-period">' + selectHtml + "</select>" +
          "</label>" +
        "</div>" +
        '<div id="news-content">' +
          '<p class="content-empty">Загружаем условия акции…</p>' +
        "</div>" +
      "</section>"
    );
  }

  function renderList() {
    var container = document.getElementById("news-content");
    if (!container) return;

    if (!state.tasks.length) {
      container.innerHTML =
        '<p class="content-empty">Условия акции для вашего дистрибьютора ещё не опубликованы.</p>';
      return;
    }

    var cards = state.tasks
      .map(function (task) {
        return (
          '<article class="news-card" data-task-id="' + escape(task.id) + '">' +
            '<div class="news-card__media">' + mediaHtml(task) + "</div>" +
            '<div class="news-card__body">' +
              '<h3 class="news-card__title">' + escape(task.title) + "</h3>" +
              '<p class="news-card__period">' + escape(formatPeriodUpper(task.period_month)) + "</p>" +
              '<div class="news-card__footer">' +
                '<button type="button" class="btn btn--primary btn--sm news-card__read" data-task-id="' +
                  escape(task.id) +
                  '">Читать</button>' +
                '<time class="news-card__date">' + escape(formatDate(task.published_at)) + "</time>" +
              "</div>" +
            "</div>" +
          "</article>"
        );
      })
      .join("");

    var pagination =
      state.page < state.totalPages
        ? '<div class="content-pagination"><button type="button" class="btn btn--secondary" id="news-load-more">Показать ещё</button></div>'
        : "";

    container.innerHTML = '<div class="news-grid">' + cards + "</div>" + pagination;

    container.querySelectorAll(".news-card__read").forEach(function (btn) {
      btn.addEventListener("click", function (event) {
        event.stopPropagation();
        openDetail(btn.getAttribute("data-task-id"));
      });
    });

    container.querySelectorAll(".news-card").forEach(function (card) {
      card.addEventListener("click", function () {
        openDetail(card.getAttribute("data-task-id"));
      });
    });

    var loadMore = document.getElementById("news-load-more");
    if (loadMore) {
      loadMore.addEventListener("click", function () {
        loadTasks(state.page + 1, true);
      });
    }
  }

  function renderDetail() {
    var container = document.getElementById("news-content");
    if (!container || !state.activeTask) return;

    var task = state.activeTask;
    var published = formatDate(task.published_at);
    var acceptBlock = "";

    if (task.is_accepted) {
      acceptBlock =
        '<div class="news-accept">' +
          '<p class="news-accept__status news-accept__status--done">' +
            "Вы уже приняли участие в акции" +
            (task.accepted_at ? " (" + escape(formatDate(task.accepted_at)) + ")" : "") +
          "</p>" +
        "</div>";
    } else {
      acceptBlock =
        '<div class="news-accept">' +
          '<button type="button" class="btn btn--primary" id="news-accept-btn"' +
            (state.accepting ? " disabled" : "") +
            ">Согласен, хочу участвовать</button>" +
        "</div>";
    }

    container.innerHTML =
      '<div class="news-detail">' +
        '<button type="button" class="news-back" id="news-back">← Назад</button>' +
        '<article class="content-card news-detail__card">' +
          (task.cover_image_url
            ? '<div class="news-detail__cover"><img src="' + escape(task.cover_image_url) + '" alt=""></div>'
            : "") +
          '<h2 class="content-card__title">' + escape(task.title) + "</h2>" +
          '<p class="content-card__meta">' +
            escape(formatPeriodUpper(task.period_month)) +
            (published ? " · " + escape(published) : "") +
          "</p>" +
          '<div class="content-card__body">' + renderRichContent(task.content) + "</div>" +
          acceptBlock +
        "</article>" +
      "</div>";

    document.getElementById("news-back").addEventListener("click", showList);
    var acceptBtn = document.getElementById("news-accept-btn");
    if (acceptBtn) {
      acceptBtn.addEventListener("click", acceptTask);
    }
  }

  function showList() {
    state.view = "list";
    state.activeTask = null;
    setTaskUrl("");
    renderList();
  }

  function openDetail(taskId) {
    if (!taskId) return;

    var cached = state.tasks.find(function (item) {
      return item.id === taskId;
    });

    state.view = "detail";
    setTaskUrl(taskId);

    if (cached) {
      state.activeTask = cached;
      renderDetail();
      return;
    }

    PlombirApi.get("/tasks/" + encodeURIComponent(taskId)).then(function (result) {
      var alertBox = document.getElementById("news-alert");
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось открыть условия акции"),
          "error"
        );
        return;
      }
      var payload = result.data.data || {};
      state.activeTask = payload.task;
      renderDetail();
    });
  }

  function loadTasks(page, append) {
    if (state.loading) return;
    state.loading = true;

    var query = "?page=" + page + "&limit=12";
    if (state.periodFilter !== "all") {
      query += "&period_month=" + encodeURIComponent(state.periodFilter);
    }

    PlombirApi.get("/tasks" + query).then(function (result) {
      state.loading = false;
      var alertBox = document.getElementById("news-alert");
      PlombirLayout.clearAlert(alertBox);

      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить условия акции"),
          "error"
        );
        return;
      }

      var data = result.data.data || {};
      var items = data.items || [];
      var pagination = data.pagination || {};
      state.page = pagination.current_page || page;
      state.totalPages = pagination.total_pages || 1;

      if (append) {
        state.tasks = state.tasks.concat(items);
      } else {
        state.tasks = items;
      }

      if (state.view === "detail" && state.activeTask) {
        var updated = state.tasks.find(function (item) {
          return item.id === state.activeTask.id;
        });
        if (updated) state.activeTask = updated;
        renderDetail();
      } else {
        renderList();
      }
    });
  }

  function acceptTask() {
    if (!state.activeTask || state.accepting) return;

    state.accepting = true;
    renderDetail();

    PlombirApi.post("/tasks/" + state.activeTask.id + "/accept").then(function (result) {
      state.accepting = false;
      var alertBox = document.getElementById("news-alert");

      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось принять участие"),
          "error"
        );
        renderDetail();
        return;
      }

      state.activeTask.is_accepted = true;
      var payload = result.data.data || {};
      state.activeTask.accepted_at = payload.accepted_at || new Date().toISOString();

      state.tasks.forEach(function (item) {
        if (item.id === state.activeTask.id) {
          item.is_accepted = true;
          item.accepted_at = state.activeTask.accepted_at;
        }
      });

      PlombirLayout.showAlert(alertBox, "Вы успешно приняли участие в акции", "success");
      renderDetail();
    });
  }

  function bindPeriodSelect() {
    var select = document.getElementById("news-period");
    if (!select) return;
    select.addEventListener("change", function () {
      state.periodFilter = select.value;
      state.page = 1;
      if (state.view === "detail") {
        showList();
      }
      loadTasks(1, false);
    });
  }

  function init(profile) {
    state.profile = profile;
    state.periodFilter = "all";

    var root = PlombirLayout.mountLayout({
      mode: "full",
      profile: profile,
      activeMenuId: "news",
      pageTitle: "Условия акции",
    });
    if (!root) return;

    root.innerHTML = renderShell();
    bindPeriodSelect();

    var taskId = getTaskIdFromUrl();
    if (taskId) {
      state.view = "detail";
      openDetail(taskId);
    }

    loadTasks(1, false);
  }

  PlombirAuth.requireAuth().then(function (profile) {
    if (profile) init(profile);
  });
})();
