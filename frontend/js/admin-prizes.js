(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = { items: [], distributors: [], selected: null, page: 1, totalPages: 1 };

  function typeLabel(type) {
    return type === "money" ? "СБП" : "Сертификат";
  }

  function loadDistributors() {
    return PlombirApi.get("/distributors/").then(function (result) {
      state.distributors = (result.data && result.data.data) || [];
    });
  }

  function loadPrizes() {
    return PlombirApi.get("/rewards/?include_inactive=true&limit=100").then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        throw new Error(PlombirApi.extractErrorMessage(result.data, "Ошибка загрузки призов"));
      }
      state.items = (result.data.data && result.data.data.items) || [];
    });
  }

  function renderList(container) {
    if (!state.items.length) {
      container.innerHTML = '<div class="admin-card"><p class="admin-empty">Призы не найдены</p></div>';
      return;
    }

    var rows = state.items.map(function (item) {
      var badges = item.is_active
        ? '<span class="admin-badge admin-badge--ok">Активен</span>'
        : '<span class="admin-badge admin-badge--muted">Скрыт</span>';
      if (item.is_system) badges += ' <span class="admin-badge admin-badge--warn">Системный</span>';
      return (
        "<tr data-prize-id=\"" + item.id + "\">" +
          "<td>" + L.escapeHtml(item.name) + "</td>" +
          "<td>" + L.escapeHtml(typeLabel(item.type)) + "</td>" +
          "<td>" + badges + "</td>" +
          "<td>" + L.formatDate(item.updated_at || item.created_at) + "</td>" +
        "</tr>"
      );
    }).join("");

    container.innerHTML =
      '<div class="admin-card">' +
        '<div class="admin-toolbar">' +
          '<button type="button" class="btn btn--primary btn--sm" id="prize-create-btn">Добавить приз</button>' +
        "</div>" +
        '<div class="admin-table-wrap"><table class="admin-table">' +
          "<thead><tr><th>Название</th><th>Тип</th><th>Статус</th><th>Обновлён</th></tr></thead>" +
          "<tbody>" + rows + "</tbody>" +
        "</table></div>" +
      "</div>";

    document.getElementById("prize-create-btn").addEventListener("click", function () {
      openPrizeModal(null);
    });
    container.querySelectorAll("tr[data-prize-id]").forEach(function (row) {
      row.addEventListener("click", function () {
        openPrizeModal(row.getAttribute("data-prize-id"));
      });
    });
  }

  function distributorChecklist(selectedIds, fieldId) {
    var selected = selectedIds || [];
    return (
      '<div class="admin-checklist" id="' + fieldId + '">' +
        state.distributors.map(function (d) {
          var checked = selected.indexOf(d.id) !== -1 ? " checked" : "";
          return (
            '<label><input type="checkbox" value="' + d.id + '"' + checked + ">" +
            L.escapeHtml(d.name) + "</label>"
          );
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

  function openPrizeModal(prizeId) {
    var modal = document.getElementById("prize-modal");
    var prize = prizeId ? state.items.find(function (p) { return p.id === prizeId; }) : null;
    state.selected = prize;

    if (!prize) {
      modal.hidden = false;
      modal.innerHTML =
        '<div class="admin-modal">' +
          '<div class="admin-modal__header"><h2>Новый приз</h2><button type="button" class="admin-modal__close" id="prize-close">×</button></div>' +
          '<div class="admin-modal__body admin-form-grid">' +
            '<div id="prize-modal-alert"></div>' +
            '<label class="field"><span class="field__label">Название</span><input class="field__input" id="prize-name"></label>' +
            '<label class="field"><span class="field__label">Описание</span><textarea class="admin-editor" id="prize-description"></textarea></label>' +
            '<label class="field"><span class="field__label">URL изображения</span><input class="field__input" id="prize-image"></label>' +
          "</div>" +
          '<div class="admin-modal__actions"><button type="button" class="btn btn--ghost" id="prize-cancel">Отмена</button>' +
          '<button type="button" class="btn btn--primary" id="prize-save">Сохранить</button></div>' +
        "</div>";
      bindModalClose();
      document.getElementById("prize-save").addEventListener("click", function () {
        PlombirApi.post("/rewards/", {
          name: document.getElementById("prize-name").value.trim(),
          description: document.getElementById("prize-description").value.trim() || null,
          image_url: document.getElementById("prize-image").value.trim() || null,
          type: "certificate",
          is_active: true,
        }).then(handleSaveResponse);
      });
      return;
    }

    var visibilityPromise = prize.is_system && prize.type === "money"
      ? PlombirApi.get("/rewards/" + prize.id + "/visibility")
      : Promise.resolve({ data: { success: true, data: { visible_distributor_ids: [] } } });

    visibilityPromise.then(function (visResult) {
      var visibleIds = (visResult.data && visResult.data.data && visResult.data.data.visible_distributor_ids) || [];
      modal.hidden = false;
      modal.innerHTML =
        '<div class="admin-modal admin-modal--wide">' +
          '<div class="admin-modal__header"><h2>' + L.escapeHtml(prize.name) + "</h2>" +
          '<button type="button" class="admin-modal__close" id="prize-close">×</button></div>' +
          '<div class="admin-modal__body admin-form-grid">' +
            '<div id="prize-modal-alert"></div>' +
            '<label class="field"><span class="field__label">Название</span><input class="field__input" id="prize-name" value="' +
              L.escapeHtml(prize.name) + '"' + (prize.is_system ? " readonly" : "") + "></label>" +
            '<label class="field"><span class="field__label">Описание</span><textarea class="admin-editor" id="prize-description">' +
              L.escapeHtml(prize.description || "") + "</textarea></label>" +
            '<label class="field"><span class="field__label">URL изображения</span><input class="field__input" id="prize-image" value="' +
              L.escapeHtml(prize.image_url || "") + '"></label>' +
            (prize.is_system && prize.type === "money"
              ? '<div class="field"><span class="field__label">Видимость СБП по дистрибьюторам</span>' +
                distributorChecklist(visibleIds, "prize-distributors") + "</div>"
              : "") +
          "</div>" +
          '<div class="admin-modal__actions">' +
            (prize.is_system ? "" : '<button type="button" class="btn btn--danger btn--sm" id="prize-hide">Скрыть</button>') +
            '<button type="button" class="btn btn--ghost" id="prize-cancel">Отмена</button>' +
            '<button type="button" class="btn btn--primary" id="prize-save">Сохранить</button>' +
          "</div>" +
        "</div>";
      bindModalClose();

      document.getElementById("prize-save").addEventListener("click", function () {
        var updates = {
          description: document.getElementById("prize-description").value.trim() || null,
          image_url: document.getElementById("prize-image").value.trim() || null,
        };
        if (!prize.is_system) {
          updates.name = document.getElementById("prize-name").value.trim();
        }
        PlombirApi.put("/rewards/" + prize.id, updates).then(function (result) {
          if (!result.response.ok || !result.data || !result.data.success) {
            modalAlert(PlombirApi.extractErrorMessage(result.data, "Ошибка сохранения"), "error");
            return;
          }
          if (prize.is_system && prize.type === "money") {
            return PlombirApi.put("/rewards/" + prize.id + "/visibility", {
              distributor_ids: getCheckedIds("prize-distributors"),
            }).then(handleSaveResponse);
          }
          handleSaveResponse(result);
        });
      });

      var hideBtn = document.getElementById("prize-hide");
      if (hideBtn) {
        hideBtn.addEventListener("click", function () {
          if (!confirm("Скрыть этот приз?")) return;
          PlombirApi.delete("/rewards/" + prize.id).then(handleSaveResponse);
        });
      }
    });
  }

  function modalAlert(message, type) {
    L.showToast(document.getElementById("prize-modal-alert"), message, type);
  }

  function bindModalClose() {
    function close() {
      document.getElementById("prize-modal").hidden = true;
    }
    document.getElementById("prize-close").addEventListener("click", close);
    document.getElementById("prize-cancel").addEventListener("click", close);
  }

  function handleSaveResponse(result) {
    if (!result.response.ok || !result.data || !result.data.success) {
      modalAlert(PlombirApi.extractErrorMessage(result.data, "Ошибка операции"), "error");
      return;
    }
    document.getElementById("prize-modal").hidden = true;
    refresh();
  }

  function refresh() {
    loadPrizes().then(function () {
      renderList(document.getElementById("prizes-root"));
    }).catch(function (err) {
      L.showToast(document.getElementById("page-alert"), err.message, "error");
    });
  }

  function init(profile) {
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "prizes",
      pageTitle: "Каталог призов",
    });
    content.innerHTML = '<div id="page-alert"></div><div id="prizes-root"><p class="admin-empty">Загрузка…</p></div>';
    Promise.all([loadDistributors(), loadPrizes()]).then(function () {
      renderList(document.getElementById("prizes-root"));
    }).catch(function (err) {
      L.showToast(document.getElementById("page-alert"), err.message, "error");
    });
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (profile) init(profile);
  });
})();
