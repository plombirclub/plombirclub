(function () {
  "use strict";

  var state = {
    rows: [],
    dateFrom: "",
    dateTo: "",
    periodMonth: "",
    granularity: "day",
    page: 1,
    totalPages: 1,
    loading: false,
    exporting: false,
    chartPoints: [],
    hoveredIndex: -1,
  };

  function escape(value) {
    return PlombirLayout.escapeHtml(value || "");
  }

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function formatInputDate(date) {
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate());
  }

  function formatDisplayDate(value) {
    if (!value) return "";
    var parts = value.split("-");
    if (parts.length !== 3) return value;
    return parts[2] + "." + parts[1] + "." + parts[0];
  }

  function formatBoxes(value) {
    var num = Number(value || 0);
    if (Math.abs(num - Math.round(num)) < 0.001) {
      return String(Math.round(num));
    }
    return num.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
  }

  function monthStartEnd() {
    var now = new Date();
    var start = new Date(now.getFullYear(), now.getMonth(), 1);
    var end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    return { start: formatInputDate(start), end: formatInputDate(end) };
  }

  function buildPeriodOptions() {
    var options = [{ value: "", label: "Все периоды" }];
    var now = new Date();
    for (var i = 0; i < 24; i += 1) {
      var date = new Date(now.getFullYear(), now.getMonth() - i, 1);
      var month = pad(date.getMonth() + 1);
      var value = date.getFullYear() + "-" + month;
      var monthNames = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
      ];
      options.push({ value: value, label: monthNames[date.getMonth()] + " " + date.getFullYear() });
    }
    return options;
  }

  function parseRowDate(row) {
    if (row.document_date) {
      var docDate = new Date(row.document_date + "T00:00:00");
      if (!isNaN(docDate.getTime())) return docDate;
    }
    if (row.created_at) {
      var created = new Date(row.created_at);
      if (!isNaN(created.getTime())) return created;
    }
    return null;
  }

  function rowDateIso(row) {
    var date = parseRowDate(row);
    return date ? formatInputDate(date) : "";
  }

  function inDateRange(row) {
    var iso = rowDateIso(row);
    if (iso) {
      if (state.dateFrom && iso < state.dateFrom) return false;
      if (state.dateTo && iso > state.dateTo) return false;
    }
    if (state.periodMonth && row.period_month !== state.periodMonth) return false;
    return true;
  }

  function bucketKey(date) {
    if (state.granularity === "month") {
      return date.getFullYear() + "-" + pad(date.getMonth() + 1);
    }
    if (state.granularity === "week") {
      var day = new Date(date);
      day.setHours(0, 0, 0, 0);
      day.setDate(day.getDate() + 4 - (day.getDay() || 7));
      var yearStart = new Date(day.getFullYear(), 0, 1);
      var week = Math.ceil(((day - yearStart) / 86400000 + 1) / 7);
      return day.getFullYear() + "-W" + pad(week);
    }
    return formatInputDate(date);
  }

  function formatBucketLabel(key) {
    if (state.granularity === "month") {
      var parts = key.split("-");
      if (parts.length === 2) return parts[1] + "." + parts[0];
    }
    if (state.granularity === "week") {
      return "Нед. " + key.split("-W")[1];
    }
    return formatDisplayDate(key);
  }

  function aggregateChartData() {
    var filtered = state.rows.filter(inDateRange);
    var buckets = {};

    filtered.forEach(function (row) {
      var date = parseRowDate(row);
      var key = date ? bucketKey(date) : row.period_month || "unknown";
      if (!buckets[key]) buckets[key] = 0;
      buckets[key] += Number(row.boxes_count || 0);
    });

    var keys = Object.keys(buckets).sort();
    return keys.map(function (key) {
      return { key: key, label: formatBucketLabel(key), value: buckets[key] };
    });
  }

  function renderShell() {
    var range = monthStartEnd();
    state.dateFrom = range.start;
    state.dateTo = range.end;

    var periodOptions = buildPeriodOptions()
      .map(function (opt) {
        return '<option value="' + escape(opt.value) + '">' + escape(opt.label) + "</option>";
      })
      .join("");

    return (
      '<section class="analytics-page">' +
        '<div id="analytics-alert"></div>' +
        '<div class="analytics-toolbar">' +
          '<div class="analytics-toolbar__filters">' +
            '<label class="analytics-field">' +
              '<span class="analytics-field__label">С</span>' +
              '<input class="analytics-field__input" type="date" id="analytics-date-from" value="' +
                escape(state.dateFrom) +
                '">' +
            "</label>" +
            '<label class="analytics-field">' +
              '<span class="analytics-field__label">По</span>' +
              '<input class="analytics-field__input" type="date" id="analytics-date-to" value="' +
                escape(state.dateTo) +
                '">' +
            "</label>" +
            '<label class="analytics-field">' +
              '<span class="analytics-field__label">Период</span>' +
              '<select class="analytics-field__select" id="analytics-period">' +
                periodOptions +
              "</select>" +
            "</label>" +
          "</div>" +
          '<div class="analytics-toolbar__actions">' +
            '<select class="analytics-field__select" id="analytics-granularity">' +
              '<option value="day">День</option>' +
              '<option value="week">Неделя</option>' +
              '<option value="month">Месяц</option>' +
            "</select>" +
            '<button type="button" class="btn btn--primary" id="analytics-export">Экспорт</button>' +
          "</div>" +
        "</div>" +
        '<div class="analytics-chart-wrap" id="analytics-chart-wrap">' +
          '<canvas id="analytics-chart" height="320" aria-label="График продаж"></canvas>' +
          '<div class="analytics-tooltip" id="analytics-tooltip"></div>' +
        "</div>" +
        '<div class="analytics-table-wrap">' +
          '<table class="analytics-table">' +
            "<thead><tr>" +
              "<th>Дата</th><th>Клиент</th><th>Товар</th><th>Кол-во кор</th><th>Роль</th><th>Баллы</th>" +
            "</tr></thead>" +
            '<tbody id="analytics-table-body">' +
              '<tr><td colspan="6">Загружаем данные…</td></tr>' +
            "</tbody>" +
          "</table>" +
        "</div>" +
        '<div class="content-pagination" id="analytics-pagination"></div>' +
      "</section>"
    );
  }

  function renderTable() {
    var tbody = document.getElementById("analytics-table-body");
    if (!tbody) return;

    var filtered = state.rows.filter(inDateRange);
    var start = (state.page - 1) * 20;
    var pageRows = filtered.slice(start, start + 20);
    state.totalPages = Math.max(Math.ceil(filtered.length / 20), 1);

    if (!pageRows.length) {
      tbody.innerHTML = '<tr><td colspan="6">Нет данных за выбранный период</td></tr>';
    } else {
      tbody.innerHTML = pageRows
        .map(function (row) {
          var iso = rowDateIso(row);
          return (
            "<tr>" +
              "<td>" + escape(iso ? formatDisplayDate(iso) : row.period_month || "—") + "</td>" +
              "<td>" + escape(row.client_name || "—") + "</td>" +
              "<td>" + escape(row.product_name || "—") + "</td>" +
              "<td>" + escape(row.boxes_count != null ? formatBoxes(row.boxes_count) : "—") + "</td>" +
              "<td>" + escape(row.role || "—") + "</td>" +
              '<td class="analytics-table__points">' + escape(Number(row.amount || 0).toLocaleString("ru-RU")) + "</td>" +
            "</tr>"
          );
        })
        .join("");
    }

    var pagination = document.getElementById("analytics-pagination");
    if (!pagination) return;
    if (state.page < state.totalPages) {
      pagination.innerHTML =
        '<button type="button" class="btn btn--secondary" id="analytics-load-more">Показать ещё</button>';
      document.getElementById("analytics-load-more").addEventListener("click", function () {
        state.page += 1;
        renderTable();
      });
    } else {
      pagination.innerHTML = "";
    }
  }

  function drawChart() {
    var canvas = document.getElementById("analytics-chart");
    var wrap = document.getElementById("analytics-chart-wrap");
    if (!canvas || !wrap) return;

    state.chartPoints = aggregateChartData();
    var points = state.chartPoints;

    var dpr = window.devicePixelRatio || 1;
    var width = Math.max(wrap.clientWidth - 32, 240);
    var height = 320;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";

    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    if (!points.length) {
      ctx.fillStyle = "#5a6d78";
      ctx.font = "14px Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Нет данных для графика", width / 2, height / 2);
      return;
    }

    var padding = { top: 24, right: 16, bottom: 48, left: 48 };
    var chartW = width - padding.left - padding.right;
    var chartH = height - padding.top - padding.bottom;
    var maxVal = Math.max.apply(null, points.map(function (p) { return p.value; })) || 1;
    var step = maxVal <= 10 ? 1 : maxVal <= 50 ? 5 : 10;
    var niceMax = Math.ceil(maxVal / step) * step || step;
    var barGap = 4;
    var barW = Math.max((chartW - barGap * (points.length - 1)) / points.length, 6);

    ctx.strokeStyle = "rgba(138, 159, 180, 0.35)";
    ctx.fillStyle = "#8a9fb4";
    ctx.font = "11px Segoe UI, sans-serif";
    ctx.textAlign = "right";

    for (var i = 0; i <= 5; i += 1) {
      var yVal = (niceMax / 5) * i;
      var y = padding.top + chartH - (chartH * i) / 5;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
      ctx.fillText(formatBoxes(yVal), padding.left - 8, y + 4);
    }

    points.forEach(function (point, index) {
      var barH = niceMax > 0 ? (point.value / niceMax) * chartH : 0;
      var x = padding.left + index * (barW + barGap);
      var y = padding.top + chartH - barH;
      var isHovered = index === state.hoveredIndex;

      ctx.fillStyle = isHovered ? "#f08090" : "#f9a8b1";
      ctx.fillRect(x, y, barW, barH);

      if (points.length <= 20 || index % Math.ceil(points.length / 12) === 0) {
        ctx.save();
        ctx.translate(x + barW / 2, height - padding.bottom + 14);
        ctx.rotate(-0.5);
        ctx.fillStyle = "#5a6d78";
        ctx.textAlign = "right";
        ctx.font = "10px Segoe UI, sans-serif";
        ctx.fillText(point.label, 0, 0);
        ctx.restore();
      }

      point._x = x;
      point._y = y;
      point._w = barW;
      point._h = barH;
    });

    canvas._chartPoints = points;
  }

  function bindChartHover() {
    var canvas = document.getElementById("analytics-chart");
    var tooltip = document.getElementById("analytics-tooltip");
    var wrap = document.getElementById("analytics-chart-wrap");
    if (!canvas || !tooltip || !wrap) return;

    canvas.addEventListener("mousemove", function (event) {
      var rect = canvas.getBoundingClientRect();
      var x = event.clientX - rect.left;
      var y = event.clientY - rect.top;
      var points = canvas._chartPoints || [];
      var found = -1;

      points.forEach(function (point, index) {
        if (x >= point._x && x <= point._x + point._w && y >= point._y && y <= point._y + point._h) {
          found = index;
        }
      });

      state.hoveredIndex = found;
      drawChart();

      if (found >= 0) {
        var item = points[found];
        tooltip.innerHTML =
          '<span class="analytics-tooltip__dot"></span>' +
          escape(item.label) +
          "<br>" +
          escape(formatBoxes(item.value)) +
          " коробок";
        tooltip.classList.add("analytics-tooltip--visible");
        tooltip.style.left = event.clientX - wrap.getBoundingClientRect().left + "px";
        tooltip.style.top = event.clientY - wrap.getBoundingClientRect().top + "px";
      } else {
        tooltip.classList.remove("analytics-tooltip--visible");
      }
    });

    canvas.addEventListener("mouseleave", function () {
      state.hoveredIndex = -1;
      drawChart();
      tooltip.classList.remove("analytics-tooltip--visible");
    });
  }

  function refreshView() {
    try {
      drawChart();
    } catch (_chartErr) {
      /* график не должен блокировать таблицу */
    }
    renderTable();
  }

  function loadData() {
    if (state.loading) return;
    state.loading = true;

    var query = "?page=1&limit=100";
    if (state.periodMonth) {
      query += "&period_month=" + encodeURIComponent(state.periodMonth);
    }

    PlombirApi.get("/analytics/my-raw" + query).then(function (result) {
      state.loading = false;
      var alertBox = document.getElementById("analytics-alert");
      PlombirLayout.clearAlert(alertBox);

      if (!result.response.ok || !result.data || !result.data.success) {
        PlombirLayout.showAlert(
          alertBox,
          PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить аналитику"),
          "error"
        );
        return;
      }

      var rawData = result.data.data || {};
      state.rows = rawData.items || [];

      if (rawData.pagination && rawData.pagination.total_count > 100) {
        var totalPages = Number(rawData.pagination.total_pages);
        if (totalPages > 1) {
          loadAllRawPages(2, totalPages);
        } else {
          refreshView();
        }
      } else {
        refreshView();
      }
    }).catch(function () {
      state.loading = false;
      PlombirLayout.showAlert(
        document.getElementById("analytics-alert"),
        "Не удалось связаться с сервером",
        "error"
      );
    });
  }

  function loadAllRawPages(page, totalPages) {
    if (page > totalPages) {
      refreshView();
      return;
    }
    var query = "?page=" + page + "&limit=100";
    if (state.periodMonth) {
      query += "&period_month=" + encodeURIComponent(state.periodMonth);
    }
    PlombirApi.get("/analytics/my-raw" + query).then(function (result) {
      if (result.response.ok && result.data && result.data.success) {
        var items = (result.data.data || {}).items || [];
        state.rows = state.rows.concat(items);
      }
      loadAllRawPages(page + 1, totalPages);
    });
  }

  function exportData() {
    if (state.exporting) return;
    state.exporting = true;
    var btn = document.getElementById("analytics-export");
    if (btn) btn.disabled = true;

    var query = state.periodMonth ? "?period_month=" + encodeURIComponent(state.periodMonth) : "";
    PlombirApi.download("/analytics/export" + query, "analytics.xlsx")
      .catch(function (err) {
        PlombirLayout.showAlert(document.getElementById("analytics-alert"), err.message || "Ошибка экспорта", "error");
      })
      .finally(function () {
        state.exporting = false;
        if (btn) btn.disabled = false;
      });
  }

  function bindControls() {
    var dateFrom = document.getElementById("analytics-date-from");
    var dateTo = document.getElementById("analytics-date-to");
    var period = document.getElementById("analytics-period");
    var granularity = document.getElementById("analytics-granularity");
    var exportBtn = document.getElementById("analytics-export");
    if (!dateFrom || !dateTo || !period || !granularity || !exportBtn) return;

    dateFrom.addEventListener("change", function (event) {
      state.dateFrom = event.target.value;
      state.page = 1;
      refreshView();
    });
    dateTo.addEventListener("change", function (event) {
      state.dateTo = event.target.value;
      state.page = 1;
      refreshView();
    });
    period.addEventListener("change", function (event) {
      state.periodMonth = event.target.value;
      state.page = 1;
      loadData();
    });
    granularity.addEventListener("change", function (event) {
      state.granularity = event.target.value;
      refreshView();
    });
    exportBtn.addEventListener("click", exportData);

    window.addEventListener("resize", function () {
      drawChart();
    });
  }

  function init(profile) {
    var root = PlombirLayout.mountLayout({
      mode: "full",
      profile: profile,
      activeMenuId: "analytics",
      pageTitle: "Аналитика",
    });
    if (!root) return;

    root.innerHTML = renderShell();
    bindControls();
    bindChartHover();
    loadData();
  }

  PlombirAuth.requireAuth().then(function (profile) {
    if (profile) init(profile);
  });
})();
