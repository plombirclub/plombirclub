(function () {
  "use strict";

  var L = PlombirAdminLayout;
  var state = { items: [], distributors: [], editing: null };

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

  function distributorChecklist(selectedIds, fieldId) {
    return (
      '<div class="admin-checklist" id="' + fieldId + '">' +
        state.distributors.map(function (d) {
          var checked = (selectedIds || []).indexOf(d.id) !== -1 ? " checked" : "";
          return '<label><input type="checkbox" value="' + d.id + '"' + checked + ">" + L.escapeHtml(d.name) + "</label>";
        }).join("") +
      "</div>"
    );
  }

  function getCheckedIds(fieldId) {
    var root = document.getElementById(fieldId);
    if (!root) return [];
    return Array.prototype.slice.call(root.querySelectorAll("input:checked")).map(function (el) { return el.value; });
  }

  function prizeFormFields(prize, visibleIds) {
    var preview = "";
    if (prize && prize.image_file_url) {
      preview =
        '<p class="admin-modal__meta">Текущая картинка: <img src="' + L.escapeHtml(prize.image_file_url) +
        '" alt="" style="max-width:120px;max-height:80px;border-radius:8px;vertical-align:middle"></p>';
    }
    return (
      preview +
      '<label class="field"><span class="field__label">Название</span><input class="field__input" id="prize-name" value="' +
        L.escapeHtml(prize ? prize.name : "") + '"' + (prize && prize.is_system ? " readonly" : "") + "></label>" +
      '<label class="field"><span class="field__label">Описание</span><textarea class="admin-editor" id="prize-description">' +
        L.escapeHtml(prize ? (prize.description || "") : "") + "</textarea></label>" +
      '<label class="field"><span class="field__label">Картинка (JPG, PNG, WEBP, GIF)</span>' +
        '<input class="field__input" type="file" id="prize-image-file" accept="image/jpeg,image/png,image/webp,image/gif"></label>' +
      '<label class="field"><span class="field__label">Ссылка (URL)</span>' +
        '<input class="field__input" id="prize-link" placeholder="https://…" value="' +
        L.escapeHtml(prize ? (prize.image_url || "") : "") + '"></label>' +
      '<p class="admin-modal__meta">Если указаны и картинка, и ссылка — у участника ссылка будет под изображением.</p>' +
      '<div class="field"><span class="field__label">Видимость по дистрибьюторам</span>' +
        '<p class="admin-modal__meta">Отметьте дистрибьюторов, которым виден приз. Пустой список = виден всем.</p>' +
        distributorChecklist(visibleIds || [], "prize-distributors") +
      "</div>"
    );
  }

  function renderList(container) {
    if (!state.items.length) {
      container.innerHTML =
        '<div class="admin-card"><p class="admin-empty">Призы не найдены</p>' +
        '<button type="button" class="btn btn--primary btn--sm" id="prize-create-btn">Добавить приз</button></div>';
      document.getElementById("prize-create-btn").addEventListener("click", function () { openPrizeModal(null); });
      return;
    }

    container.innerHTML =
      '<div class="admin-card">' +
        '<div class="admin-toolbar"><button type="button" class="btn btn--primary btn--sm" id="prize-create-btn">Добавить приз</button></div>' +
        '<div class="admin-table-wrap"><table class="admin-table">' +
          "<thead><tr><th>Название</th><th>Тип</th><th>Статус</th><th>Обновлён</th></tr></thead><tbody>" +
          state.items.map(function (item) {
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
          }).join("") +
          "</tbody></table></div></div>";

    document.getElementById("prize-create-btn").addEventListener("click", function () { openPrizeModal(null); });
    container.querySelectorAll("tr[data-prize-id]").forEach(function (row) {
      row.addEventListener("click", function () { openPrizeModal(row.getAttribute("data-prize-id")); });
    });
  }

  function modalAlert(message, type) {
    L.showToast(document.getElementById("prize-modal-alert"), message, type);
  }

  function bindModalClose() {
    function close() { document.getElementById("prize-modal").hidden = true; }
    document.getElementById("prize-close").addEventListener("click", close);
    document.getElementById("prize-cancel").addEventListener("click", close);
  }

  function handleSaveResponse(result) {
    if (result && (!result.response.ok || !result.data || !result.data.success)) {
      modalAlert(PlombirApi.extractErrorMessage(result.data, "Ошибка операции"), "error");
      return;
    }
    document.getElementById("prize-modal").hidden = true;
    loadPrizes().then(function () {
      renderList(document.getElementById("prizes-root"));
    });
  }

  function openPrizeModal(prizeId) {
    state.editing = prizeId ? state.items.find(function (p) { return p.id === prizeId; }) : null;
    var modal = document.getElementById("prize-modal");
    var prize = state.editing;

    function showModal(visibleIds) {
      modal.hidden = false;
      modal.innerHTML =
        '<div class="admin-modal admin-modal--wide">' +
          '<div class="admin-modal__header"><h2>' + (prize ? L.escapeHtml(prize.name) : "Новый приз") + "</h2>" +
          '<button type="button" class="admin-modal__close" id="prize-close">×</button></div>' +
          '<div class="admin-modal__body admin-form-grid"><div id="prize-modal-alert"></div>' +
            prizeFormFields(prize, visibleIds) +
          "</div>" +
          '<div class="admin-modal__actions">' +
            (prize && !prize.is_system ? '<button type="button" class="btn btn--danger btn--sm" id="prize-hide">Скрыть</button>' : "") +
            '<button type="button" class="btn btn--ghost" id="prize-cancel">Отмена</button>' +
            '<button type="button" class="btn btn--primary" id="prize-save">Сохранить</button>' +
          "</div></div>";
      bindModalClose();

      document.getElementById("prize-save").addEventListener("click", function () {
        var form = new FormData();
        form.append("name", document.getElementById("prize-name").value.trim());
        form.append("description", document.getElementById("prize-description").value.trim());
        form.append("image_url", document.getElementById("prize-link").value.trim());
        form.append("is_active", prize ? (prize.is_active ? "true" : "false") : "true");
        var fileInput = document.getElementById("prize-image-file");
        if (fileInput.files[0]) form.append("image", fileInput.files[0]);

        var req = prize
          ? PlombirApi.putForm("/rewards/" + prize.id + "/update-with-image", form)
          : PlombirApi.postForm("/rewards/create-with-image", form);

        req.then(function (result) {
          if (!result.response.ok || !result.data || !result.data.success) {
            modalAlert(PlombirApi.extractErrorMessage(result.data, "Ошибка"), "error");
            return;
          }
          var id = prize ? prize.id : result.data.data.id;
          return PlombirApi.put("/rewards/" + id + "/visibility", {
            distributor_ids: getCheckedIds("prize-distributors"),
          });
        }).then(handleSaveResponse);
      });

      var hideBtn = document.getElementById("prize-hide");
      if (hideBtn) {
        hideBtn.addEventListener("click", function () {
          if (!confirm("Скрыть этот приз?")) return;
          PlombirApi.delete("/rewards/" + prize.id).then(handleSaveResponse);
        });
      }
    }

    if (prize) {
      PlombirApi.get("/rewards/" + prize.id + "/visibility").then(function (result) {
        showModal((result.data && result.data.data && result.data.data.visible_distributor_ids) || []);
      });
    } else {
      showModal([]);
    }
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
