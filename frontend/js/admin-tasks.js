(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = { items: [], distributors: [], page: 1, totalPages: 1, period: "" };

  function currentMonthValue() {
    var d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
  }

  function loadDistributors() {
    return PlombirApi.get("/distributors/").then(function (result) {
      state.distributors = (result.data && result.data.data) || [];
    });
  }

  function loadTasks() {
    var query = "?page=" + state.page + "&limit=20";
    if (state.period) query += "&period_month=" + encodeURIComponent(state.period);
    return PlombirApi.get("/tasks" + query).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        throw new Error(PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки заданий"));
      }
      var data = result.data.data || {};
      state.items = data.items || [];
      state.totalPages = (data.pagination && data.pagination.total_pages) || 1;
    });
  }

  function renderList(container) {
    container.innerHTML =
      '<div id="page-alert"></div>' +
      '<div class="admin-card">' +
        '<div class="admin-toolbar">' +
          '<label class="field field--sm"><span class="field__label">Период</span>' +
            '<input class="field__input" type="month" id="tasks-period" value="' + L.escapeHtml(state.period) + '"></label>' +
          '<button type="button" class="btn btn--ghost btn--sm" id="tasks-period-clear">Все периоды</button>' +
          '<button type="button" class="btn btn--primary btn--sm" id="task-create-btn">Разместить задание</button>' +
        "</div>" +
        '<div id="tasks-table"><p class="admin-empty">Загрузка…</p></div>' +
        '<div class="admin-pagination" id="tasks-pagination" hidden></div>' +
      "</div>";

    document.getElementById("tasks-period").addEventListener("change", function (event) {
      state.period = event.target.value;
      state.page = 1;
      refreshTable();
    });
    document.getElementById("tasks-period-clear").addEventListener("click", function () {
      state.period = "";
      document.getElementById("tasks-period").value = "";
      state.page = 1;
      refreshTable();
    });
    document.getElementById("task-create-btn").addEventListener("click", openCreateModal);
    refreshTable();
  }

  function refreshTable() {
    loadTasks().then(function () {
      var tableHost = document.getElementById("tasks-table");
      if (!state.items.length) {
        tableHost.innerHTML = '<p class="admin-empty">Задания не найдены</p>';
      } else {
        tableHost.innerHTML =
          '<div class="admin-table-wrap"><table class="admin-table">' +
            "<thead><tr><th>Заголовок</th><th>Период</th><th>Дистрибьюторы</th><th>Опубликовано</th></tr></thead><tbody>" +
            state.items.map(function (task) {
              var dist = (task.distributors || []).map(function (d) { return d.name; }).join(", ");
              return (
                "<tr data-task-id=\"" + task.id + "\">" +
                  "<td>" + L.escapeHtml(task.title) + "</td>" +
                  "<td>" + L.escapeHtml(task.period_month) + "</td>" +
                  "<td>" + L.escapeHtml(dist || "—") + "</td>" +
                  "<td>" + L.formatDate(task.published_at || task.created_at) + "</td>" +
                "</tr>"
              );
            }).join("") +
            "</tbody></table></div>";
        tableHost.querySelectorAll("tr[data-task-id]").forEach(function (row) {
          row.addEventListener("click", function () {
            openViewModal(row.getAttribute("data-task-id"));
          });
        });
      }
      renderPagination();
    }).catch(function (err) {
      L.showToast(document.getElementById("page-alert"), err.message, "error");
    });
  }

  function renderPagination() {
    var host = document.getElementById("tasks-pagination");
    if (!host) return;
    if (state.totalPages <= 1) {
      host.hidden = true;
      return;
    }
    host.hidden = false;
    host.innerHTML =
      '<button type="button" class="btn btn--ghost btn--sm"' + (state.page <= 1 ? " disabled" : "") + ' id="tasks-prev">Назад</button>' +
      '<span>Стр. ' + state.page + " / " + state.totalPages + "</span>" +
      '<button type="button" class="btn btn--ghost btn--sm"' + (state.page >= state.totalPages ? " disabled" : "") + ' id="tasks-next">Вперёд</button>';
    document.getElementById("tasks-prev").addEventListener("click", function () {
      if (state.page > 1) { state.page -= 1; refreshTable(); }
    });
    document.getElementById("tasks-next").addEventListener("click", function () {
      if (state.page < state.totalPages) { state.page += 1; refreshTable(); }
    });
  }

  function distributorChecklist(fieldId) {
    return (
      '<div class="admin-checklist" id="' + fieldId + '">' +
        state.distributors.map(function (d) {
          return '<label><input type="checkbox" value="' + d.id + '">' + L.escapeHtml(d.name) + "</label>";
        }).join("") +
      "</div>"
    );
  }

  function getCheckedIds(fieldId) {
    var root = document.getElementById(fieldId);
    if (!root) return [];
    return Array.prototype.slice.call(root.querySelectorAll("input:checked")).map(function (el) {
      return el.value;
    });
  }

  function openCreateModal() {
    var modal = document.getElementById("task-modal");
    modal.hidden = false;
    modal.innerHTML =
      '<div class="admin-modal admin-modal--wide">' +
        '<div class="admin-modal__header"><h2>Новое задание</h2><button type="button" class="admin-modal__close" id="task-close">×</button></div>' +
        '<div class="admin-modal__body admin-form-grid">' +
          '<div id="task-modal-alert"></div>' +
          '<label class="field"><span class="field__label">Заголовок</span><input class="field__input" id="task-title"></label>' +
          '<label class="field"><span class="field__label">Период</span><input class="field__input" type="month" id="task-period" value="' + currentMonthValue() + '"></label>' +
          '<label class="field"><span class="field__label">Обложка (JPG/PNG)</span><input class="field__input" type="file" id="task-cover" accept="image/jpeg,image/png"></label>' +
          '<label class="field"><span class="field__label">HTML-контент</span><textarea class="admin-editor admin-editor--tall" id="task-content" placeholder="<p>Текст условий акции…</p>"></textarea></label>' +
          '<div class="field"><span class="field__label">Дистрибьюторы</span>' + distributorChecklist("task-distributors") + "</div>" +
        "</div>" +
        '<div class="admin-modal__actions"><button type="button" class="btn btn--ghost" id="task-cancel">Отмена</button>' +
        '<button type="button" class="btn btn--primary" id="task-save">Разместить задание</button></div>' +
      "</div>";

    function close() { modal.hidden = true; }
    document.getElementById("task-close").addEventListener("click", close);
    document.getElementById("task-cancel").addEventListener("click", close);
    document.getElementById("task-save").addEventListener("click", function () {
      var title = document.getElementById("task-title").value.trim();
      var content = document.getElementById("task-content").value.trim();
      var period = document.getElementById("task-period").value;
      var distributorIds = getCheckedIds("task-distributors");
      if (!title || !content || !period || !distributorIds.length) {
        L.showToast(document.getElementById("task-modal-alert"), "Заполните все поля и выберите дистрибьюторов", "error");
        return;
      }
      var form = new FormData();
      form.append("title", title);
      form.append("content", content);
      form.append("period_month", period);
      form.append("task_type", "participation_conditions");
      distributorIds.forEach(function (id) { form.append("distributor_ids", id); });
      var cover = document.getElementById("task-cover").files[0];
      if (cover) form.append("cover_image", cover);

      PlombirApi.postForm("/tasks/create-with-cover", form).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          L.showToast(document.getElementById("task-modal-alert"), PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
          return;
        }
        modal.hidden = true;
        refreshTable();
        L.showToast(document.getElementById("page-alert"), "Задание опубликовано", "success");
      });
    });
  }

  function openViewModal(taskId) {
    PlombirApi.get("/tasks/" + taskId).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) return;
      var task = result.data.data;
      var modal = document.getElementById("task-modal");
      modal.hidden = false;
      modal.innerHTML =
        '<div class="admin-modal admin-modal--wide">' +
          '<div class="admin-modal__header"><h2>' + L.escapeHtml(task.title) + "</h2>" +
          '<button type="button" class="admin-modal__close" id="task-close">×</button></div>' +
          '<div class="admin-modal__body">' +
            '<p class="admin-modal__meta">Период: ' + L.escapeHtml(task.period_month) + "</p>" +
            (task.cover_image_url ? '<img src="' + L.escapeHtml(task.cover_image_url) + '" alt="" style="max-width:100%;border-radius:8px;margin-bottom:0.75rem">' : "") +
            '<div class="admin-detail-preview">' + task.content + "</div>" +
          "</div>" +
          '<div class="admin-modal__actions"><button type="button" class="btn btn--ghost" id="task-cancel">Закрыть</button></div>' +
        "</div>";
      document.getElementById("task-close").addEventListener("click", function () { modal.hidden = true; });
      document.getElementById("task-cancel").addEventListener("click", function () { modal.hidden = true; });
    });
  }

  function init(profile) {
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "tasks",
      pageTitle: "Условия акции",
    });
    content.innerHTML = '<div id="tasks-root"><p class="admin-empty">Загрузка…</p></div>';
    loadDistributors().then(function () {
      renderList(document.getElementById("tasks-root"));
    });
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (profile) init(profile);
  });
})();
