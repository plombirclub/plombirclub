(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = {
    users: [],
    distributors: [],
    filtered: [],
    selected: null,
    search: "",
    filterDistributor: "",
    filterActive: "",
    filterRole: "user",
  };

  function yesNoBadge(value, yesLabel, noLabel) {
    return value
      ? '<span class="admin-badge admin-badge--ok">' + yesLabel + "</span>"
      : '<span class="admin-badge admin-badge--muted">' + noLabel + "</span>";
  }

  function activeBadge(isActive) {
    return isActive
      ? '<span class="admin-badge admin-badge--ok">Активен</span>'
      : '<span class="admin-badge admin-badge--danger">Заблокирован</span>';
  }

  function applyFilters() {
    var q = state.search.trim().toLowerCase();
    state.filtered = state.users.filter(function (user) {
      if (state.filterRole && user.role !== state.filterRole) return false;
      if (state.filterActive === "active" && !user.is_active) return false;
      if (state.filterActive === "inactive" && user.is_active) return false;
      if (state.filterDistributor && user.distributor_id !== state.filterDistributor) return false;
      if (!q) return true;
      var haystack = [
        user.email,
        user.full_name,
        user.phone,
        user.inn,
        user.participant_code,
        user.distributor_name,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.indexOf(q) !== -1;
    });
  }

  function renderTable(container) {
    applyFilters();
    if (!state.filtered.length) {
      container.innerHTML =
        '<div class="admin-card"><p class="admin-empty">Пользователи не найдены</p></div>';
      return;
    }

    var rows = state.filtered
      .map(function (user) {
        return (
          "<tr data-user-id=\"" + user.id + "\">" +
            "<td>" + L.escapeHtml(user.full_name || "—") + "</td>" +
            "<td>" + L.escapeHtml(user.email) + "</td>" +
            "<td>" + L.escapeHtml(user.participant_code || "—") + "</td>" +
            "<td>" + L.escapeHtml(user.distributor_name || "—") + "</td>" +
            "<td>" + yesNoBadge(user.inn_verified_by_admin, "Да", "Нет") + "</td>" +
            "<td>" + yesNoBadge(user.is_self_employed, "Да", "Нет") + "</td>" +
            "<td>" + activeBadge(user.is_active) + "</td>" +
            "<td>" + L.formatDate(user.created_at) + "</td>" +
          "</tr>"
        );
      })
      .join("");

    container.innerHTML =
      '<div class="admin-card">' +
        '<div class="admin-toolbar">' +
          '<label class="field">' +
            '<span class="field__label">Поиск</span>' +
            '<input class="field__input" type="search" id="users-search" placeholder="Email, ФИО, код…" value="' +
              L.escapeHtml(state.search) + '">' +
          "</label>" +
          '<label class="field field--sm">' +
            '<span class="field__label">Дистрибьютор</span>' +
            '<select class="field__input" id="users-filter-distributor">' +
              '<option value="">Все</option>' +
              state.distributors.map(function (d) {
                var sel = d.id === state.filterDistributor ? " selected" : "";
                return '<option value="' + d.id + '"' + sel + ">" + L.escapeHtml(d.name) + "</option>";
              }).join("") +
            "</select>" +
          "</label>" +
          '<label class="field field--sm">' +
            '<span class="field__label">Статус</span>' +
            '<select class="field__input" id="users-filter-active">' +
              '<option value="">Все</option>' +
              '<option value="active"' + (state.filterActive === "active" ? " selected" : "") + ">Активные</option>" +
              '<option value="inactive"' + (state.filterActive === "inactive" ? " selected" : "") + ">Заблокированные</option>" +
            "</select>" +
          "</label>" +
        "</div>" +
        '<div class="admin-table-wrap">' +
          '<table class="admin-table">' +
            "<thead><tr>" +
              "<th>ФИО</th><th>Email</th><th>Код</th><th>Дистрибьютор</th>" +
              "<th>ИНН</th><th>Самозанятый</th><th>Аккаунт</th><th>Регистрация</th>" +
            "</tr></thead>" +
            "<tbody>" + rows + "</tbody>" +
          "</table>" +
        "</div>" +
        '<p class="admin-pagination__info">Показано: ' + state.filtered.length + " из " + state.users.length + "</p>" +
      "</div>";

    bindToolbar();
    container.querySelectorAll("tbody tr").forEach(function (row) {
      row.addEventListener("click", function () {
        openUserModal(row.getAttribute("data-user-id"));
      });
    });
  }

  function bindToolbar() {
    var search = document.getElementById("users-search");
    var dist = document.getElementById("users-filter-distributor");
    var active = document.getElementById("users-filter-active");
    if (search) {
      search.addEventListener("input", function () {
        state.search = search.value;
        renderTable(document.getElementById("users-root"));
      });
    }
    if (dist) {
      dist.addEventListener("change", function () {
        state.filterDistributor = dist.value;
        renderTable(document.getElementById("users-root"));
      });
    }
    if (active) {
      active.addEventListener("change", function () {
        state.filterActive = active.value;
        renderTable(document.getElementById("users-root"));
      });
    }
  }

  function loadUsers() {
    return PlombirApi.get("/users/all").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        throw new Error(PlombirApi.extractErrorMessage(result.data, "Не удалось загрузить пользователей"));
      }
      state.users = (result.data.data || []).filter(function (u) {
        return u.role !== "admin" || state.filterRole !== "user";
      });
      if (state.filterRole === "user") {
        state.users = result.data.data.filter(function (u) { return u.role === "user"; });
      } else {
        state.users = result.data.data;
      }
    });
  }

  function loadDistributors() {
    return PlombirApi.get("/distributors/").then(function (result) {
      if (result.response.ok && result.data && result.data.success) {
        state.distributors = result.data.data || [];
      }
    });
  }

  function fetchUserProfile(userId) {
    return PlombirApi.get("/users/all").then(function (result) {
      var list = (result.data && result.data.data) || [];
      var item = list.find(function (u) { return u.id === userId; });
      if (!item) throw new Error("Пользователь не найден");
      return item;
    });
  }

  function loadFullUser(userId) {
    return PlombirApi.get("/users/all").then(function (result) {
      if (!result.response.ok) throw new Error("Ошибка загрузки");
      var item = (result.data.data || []).find(function (u) { return u.id === userId; });
      if (!item) throw new Error("Пользователь не найден");
      return PlombirApi.get("/users/profile").then(function () {
        return item;
      }).catch(function () {
        return item;
      });
    });
  }

  function getUserDetails(userId) {
    return PlombirApi.get("/users/all").then(function (result) {
      var users = (result.data && result.data.data) || [];
      return users.find(function (u) { return u.id === userId; });
    });
  }

  function docLink(path, label) {
    if (!path) return "—";
    var url = path.indexOf("/") === 0 ? path : "/uploads/" + path;
    return '<a class="admin-doc-link" href="' + L.escapeHtml(url) + '" target="_blank" rel="noopener">' +
      L.escapeHtml(label) + "</a>";
  }

  function renderUserModal(user, profile) {
    profile = profile || user;
    var modal = document.getElementById("user-modal");
    var distOptions = state.distributors.map(function (d) {
      var sel = profile.distributor_id === d.id ? " selected" : "";
      return '<option value="' + d.id + '"' + sel + ">" + L.escapeHtml(d.name) + "</option>";
    }).join("");

    modal.innerHTML =
      '<div class="admin-modal-backdrop" data-close="1"></div>' +
      '<div class="admin-modal admin-modal--wide" role="dialog" aria-modal="true">' +
        '<button type="button" class="admin-modal__close" data-close="1" aria-label="Закрыть">&times;</button>' +
        '<h2 class="admin-modal__title">' + L.escapeHtml(profile.full_name || profile.email) + "</h2>" +
        '<p class="admin-modal__meta">' + L.escapeHtml(profile.email) + "</p>" +
        '<div id="user-modal-alert"></div>' +
        '<div class="admin-detail-grid">' +
          detailItem("Телефон", profile.phone || "—") +
          detailItem("Код участника", profile.participant_code || "—") +
          detailItem("Должность", profile.participant_position || "—") +
          detailItem("ИНН", profile.inn || "—") +
          detailItem("КНД 1122035", profile.knd_1122035_number || "—") +
          detailItem("Регистрация завершена", profile.is_registration_complete ? "Да" : "Нет") +
        "</div>" +
        '<div class="admin-modal__section">' +
          '<h3 class="admin-modal__section-title">Документы</h3>' +
          '<p>ИНН: ' + docLink(profile.inn_document_path, "Открыть фото ИНН") + "</p>" +
          '<p>КНД: ' + docLink(profile.knd_1122035_document_path, "Открыть справку КНД") + "</p>" +
        "</div>" +
        '<div class="admin-modal__section">' +
          '<h3 class="admin-modal__section-title">Дистрибьютор</h3>' +
          '<label class="field">' +
            '<span class="field__label">Назначить дистрибьютора</span>' +
            '<select class="field__input" id="user-distributor-select">' +
              '<option value="">— не назначен —</option>' + distOptions +
            "</select>" +
          "</label>" +
          '<button type="button" class="btn btn--secondary btn--sm" id="user-save-distributor">Сохранить дистрибьютора</button>' +
        "</div>" +
        '<div class="admin-modal__section">' +
          '<h3 class="admin-modal__section-title">Действия</h3>' +
          '<div class="admin-modal__actions">' +
            '<button type="button" class="btn btn--primary btn--sm" id="user-verify-inn"' +
              (profile.inn_verified_by_admin ? " disabled" : "") + ">Подтверждаю ИНН</button>" +
            '<button type="button" class="btn btn--primary btn--sm" id="user-verify-se"' +
              (profile.is_self_employed ? " disabled" : "") + ">Подтверждаю статус самозанятого</button>" +
            '<button type="button" class="btn btn--secondary btn--sm" id="user-activate-points">Активировать баллы вручную</button>' +
            '<button type="button" class="btn btn--ghost btn--sm" id="user-toggle-active">' +
              (profile.is_active ? "Заблокировать" : "Разблокировать") + "</button>" +
            '<button type="button" class="btn btn--ghost btn--sm" id="user-delete">Удалить (ФЗ-152)</button>' +
          "</div>" +
        "</div>" +
        '<div class="admin-modal__section">' +
          '<h3 class="admin-modal__section-title">Изменить документы (админ)</h3>' +
          '<form id="user-docs-form" class="form-grid">' +
            '<label class="field"><span class="field__label">ИНН</span><input class="field__input" name="inn" value="' +
              L.escapeHtml(profile.inn || "") + '"></label>' +
            '<label class="field"><span class="field__label">Номер КНД</span><input class="field__input" name="knd" value="' +
              L.escapeHtml(profile.knd_1122035_number || "") + '"></label>' +
            '<label class="field"><span class="field__label">Новое фото ИНН</span><input class="field__input" type="file" name="inn_photo" accept="image/*,.pdf"></label>' +
            '<label class="field"><span class="field__label">Новая справка КНД</span><input class="field__input" type="file" name="knd_photo" accept="image/*,.pdf"></label>' +
            '<button type="submit" class="btn btn--secondary btn--sm">Сохранить документы</button>' +
          "</form>" +
        "</div>" +
      "</div>";

    modal.hidden = false;
    bindModalActions(user.id, profile);
  }

  function detailItem(label, value) {
    return (
      '<div class="admin-detail-item">' +
        '<span class="admin-detail-item__label">' + L.escapeHtml(label) + "</span>" +
        '<span class="admin-detail-item__value">' + value + "</span>" +
      "</div>"
    );
  }

  function closeModal() {
    var modal = document.getElementById("user-modal");
    modal.hidden = true;
    modal.innerHTML = "";
    state.selected = null;
  }

  function modalAlert(message, type) {
    L.showToast(document.getElementById("user-modal-alert"), message, type);
  }

  function bindModalActions(userId, profile) {
    var modal = document.getElementById("user-modal");
    modal.querySelectorAll("[data-close]").forEach(function (el) {
      el.addEventListener("click", closeModal);
    });

    document.getElementById("user-save-distributor").addEventListener("click", function () {
      var select = document.getElementById("user-distributor-select");
      var distributorId = select.value || null;
      PlombirApi.put("/users/" + userId + "/distributor", { distributor_id: distributorId })
        .then(function (result) {
          if (!result.response.ok || !result.data || !result.data.success) {
            modalAlert(PlombirApi.extractErrorMessage(result.data, "Ошибка сохранения"), "error");
            return;
          }
          modalAlert("Дистрибьютор сохранён", "success");
          refreshAfterAction();
        });
    });

    document.getElementById("user-verify-inn").addEventListener("click", function () {
      PlombirApi.put("/users/" + userId + "/verify-inn", {}).then(handleActionResult("ИНН подтверждён"));
    });

    document.getElementById("user-verify-se").addEventListener("click", function () {
      PlombirApi.put("/users/" + userId + "/verify-self-employed", {}).then(handleActionResult("Статус самозанятого подтверждён"));
    });

    document.getElementById("user-activate-points").addEventListener("click", function () {
      var comment = window.prompt("Комментарий к активации (необязательно):", "");
      if (comment === null) return;
      PlombirApi.put("/users/" + userId + "/activate-points", { comment: comment || null })
        .then(function (result) {
          if (!result.response.ok || !result.data || !result.data.success) {
            modalAlert(PlombirApi.extractErrorMessage(result.data, "Ошибка активации"), "error");
            return;
          }
          var data = result.data.data || {};
          modalAlert(
            "Активировано записей: " + (data.activated_count || 0) + ", сумма: " + (data.activated_amount || 0),
            "success"
          );
        });
    });

    document.getElementById("user-toggle-active").addEventListener("click", function () {
      var newActive = !profile.is_active;
      PlombirApi.put("/users/" + userId + "/deactivate", { is_active: newActive })
        .then(handleActionResult(newActive ? "Пользователь разблокирован" : "Пользователь заблокирован"));
    });

    document.getElementById("user-delete").addEventListener("click", function () {
      if (!window.confirm("Удалить персональные данные пользователя по ФЗ-152? История баллов и заявок сохранится.")) return;
      PlombirApi.delete("/users/" + userId).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          modalAlert(PlombirApi.extractErrorMessage(result.data, "Ошибка удаления"), "error");
          return;
        }
        closeModal();
        refreshAfterAction();
      });
    });

    document.getElementById("user-docs-form").addEventListener("submit", function (event) {
      event.preventDefault();
      var form = event.target;
      var fd = new FormData();
      if (form.inn.value.trim()) fd.append("inn", form.inn.value.trim());
      if (form.knd.value.trim()) fd.append("knd_1122035_number", form.knd.value.trim());
      if (form.inn_photo.files[0]) fd.append("inn_photo", form.inn_photo.files[0]);
      if (form.knd_photo.files[0]) fd.append("knd_1122035_photo", form.knd_photo.files[0]);
      PlombirApi.putForm("/users/" + userId + "/documents", fd).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          modalAlert(PlombirApi.extractErrorMessage(result.data, "Ошибка сохранения документов"), "error");
          return;
        }
        modalAlert("Документы обновлены", "success");
        openUserModal(userId);
        refreshAfterAction();
      });
    });

    function handleActionResult(successMessage) {
      return function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          modalAlert(PlombirApi.extractErrorMessage(result.data, "Ошибка операции"), "error");
          return;
        }
        modalAlert(successMessage, "success");
        openUserModal(userId);
        refreshAfterAction();
      };
    }
  }

  function openUserModal(userId) {
    state.selected = userId;
    PlombirApi.get("/users/all").then(function (result) {
      var users = (result.data && result.data.data) || [];
      var user = users.find(function (u) { return u.id === userId; });
      if (!user) {
        alert("Пользователь не найден");
        return;
      }
      renderUserModal(user, user);
    });
  }

  function refreshAfterAction() {
    loadUsers().then(function () {
      renderTable(document.getElementById("users-root"));
    });
  }

  function init(profile) {
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "users",
      pageTitle: "Пользователи",
    });
    content.innerHTML = '<div id="page-alert"></div><div id="users-root"><p class="admin-empty">Загрузка…</p></div>';

    Promise.all([loadUsers(), loadDistributors()])
      .then(function () {
        renderTable(document.getElementById("users-root"));
        var openUserId = sessionStorage.getItem("admin_open_user");
        if (openUserId) {
          sessionStorage.removeItem("admin_open_user");
          openUserModal(openUserId);
        }
      })
      .catch(function (err) {
        L.showToast(document.getElementById("page-alert"), err.message || "Ошибка загрузки", "error");
      });
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (profile) init(profile);
  });
})();
