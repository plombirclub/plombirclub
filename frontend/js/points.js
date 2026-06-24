(function () {
  "use strict";

  var state = {
    loading: false,
    activating: false,
    statusRows: [],
    activationTask: null,
  };

  function escape(value) {
    return PlombirLayout.escapeHtml(value || "");
  }

  function formatAmount(value) {
    var num = Number(value || 0);
    return num.toLocaleString("ru-RU", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function formatPeriodLabel(periodMonth) {
    if (!periodMonth) return "—";
    var parts = String(periodMonth).split("-");
    if (parts.length !== 2) return periodMonth;
    var monthIndex = Number(parts[1]) - 1;
    var monthNames = [
      "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
      "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ];
    if (monthIndex < 0 || monthIndex > 11) return periodMonth;
    return monthNames[monthIndex] + " " + parts[0];
  }

  function formatDeadline(value) {
    if (!value) return "—";
    var date = new Date(value);
    if (isNaN(date.getTime())) return "—";
    return date.toLocaleDateString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  }

  function renderShell() {
    return (
      '<section class="points-page">' +
        '<div id="points-alert"></div>' +
        '<section class="points-activation" id="points-activation-block"></section>' +
        '<section class="points-table-wrap">' +
          '<table class="points-table">' +
            "<thead><tr>" +
              "<th>Количество баллов</th>" +
              "<th></th>" +
              "<th></th>" +
            "</tr></thead>" +
            '<tbody id="points-table-body">' +
              '<tr><td colspan="3">Загружаем данные…</td></tr>' +
            "</tbody>" +
          "</table>" +
        "</section>" +
      "</section>"
    );
  }

  function renderActivationBlock() {
    var container = document.getElementById("points-activation-block");
    if (!container) return;

    if (!state.activationTask) {
      container.innerHTML =
        '<div class="points-activation__inner">' +
          '<h2 class="points-activation__title">Активация баллов</h2>' +
          '<p class="points-activation__empty">Сейчас нет баллов, которые нужно активировать.</p>' +
        "</div>";
      return;
    }

    var task = state.activationTask;
    var disabled = state.activating ? " disabled" : "";
    var deadline = formatDeadline(task.deadline_at);

    container.innerHTML =
      '<div class="points-activation__inner">' +
        '<div class="points-activation__meta">' +
          '<h2 class="points-activation__title">Активация баллов</h2>' +
          '<p class="points-activation__line"><strong>Количество начисленных баллов:</strong> ' + escape(formatAmount(task.amount)) + "</p>" +
          '<p class="points-activation__line"><strong>Период:</strong> ' + escape(formatPeriodLabel(task.period_month)) + "</p>" +
          '<p class="points-activation__line points-activation__line--accent">Необходимо активировать баллы до ' + escape(deadline) + ".</p>" +
        "</div>" +
        '<button type="button" class="btn btn--primary points-activation__btn" id="points-activate-btn"' + disabled + ">Активировать</button>" +
      "</div>";

    var activateBtn = document.getElementById("points-activate-btn");
    if (activateBtn) activateBtn.addEventListener("click", activatePoints);
  }

  function renderTable() {
    var body = document.getElementById("points-table-body");
    if (!body) return;

    if (!state.statusRows.length) {
      body.innerHTML = '<tr><td colspan="3">Данные по баллам пока отсутствуют.</td></tr>';
      return;
    }

    body.innerHTML = state.statusRows
      .map(function (row) {
        return (
          '<tr class="points-table__row">' +
            '<td class="points-table__amount">' + escape(formatAmount(row.amount)) + "</td>" +
            "<td>" + escape(row.status_label || row.status) + "</td>" +
            '<td class="points-table__comment">' + escape(row.comment || "") + "</td>" +
          "</tr>"
        );
      })
      .join("");
  }

  function loadOverview() {
    if (state.loading) return;
    state.loading = true;

    PlombirApi.get("/points/overview").then(function (result) {
      state.loading = false;
      var alertBox = document.getElementById("points-alert");
      PlombirLayout.clearAlert(alertBox);

      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить данные по баллам"),
          "error"
        );
        return;
      }

      var data = result.data.data || {};
      state.statusRows = data.status_rows || [];
      state.activationTask = data.activation_task || null;
      renderActivationBlock();
      renderTable();
    }).catch(function () {
      state.loading = false;
      PlombirLayout.showAlert(
        document.getElementById("points-alert"),
        "Не удалось связаться с сервером",
        "error"
      );
    });
  }

  function activatePoints() {
    if (state.activating || !state.activationTask) return;
    state.activating = true;
    renderActivationBlock();

    var body = {};
    if (state.activationTask.period_month) {
      body.period_month = state.activationTask.period_month;
    }

    PlombirApi.post("/points/activate", body).then(function (result) {
      state.activating = false;
      var alertBox = document.getElementById("points-alert");
      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось активировать баллы"),
          "error"
        );
        renderActivationBlock();
        return;
      }

      PlombirLayout.showAlert(alertBox, "Баллы успешно активированы", "success");
      loadOverview();
    }).catch(function () {
      state.activating = false;
      renderActivationBlock();
      PlombirLayout.showAlert(
        document.getElementById("points-alert"),
        "Не удалось связаться с сервером",
        "error"
      );
    });
  }

  function init(profile) {
    var root = PlombirLayout.mountLayout({
      mode: "full",
      profile: profile,
      activeMenuId: "points",
      pageTitle: "БАЛЛЫ",
    });
    if (!root) return;

    root.innerHTML = renderShell();
    loadOverview();
  }

  PlombirAuth.requireAuth().then(function (profile) {
    if (profile) init(profile);
  });
})();
