(function () {
  "use strict";

  var L = PlombirAdminLayout;

  function renderImportPage(container) {
    container.innerHTML =
      '<div id="page-alert"></div>' +
      '<div class="admin-import-grid">' +
        importBlock(
          "users",
          "Импорт пользователей",
          "Загрузите Excel с участниками. Email — уникальный идентификатор. Импорт не перезаписывает ИНН, КНД и подтверждения.",
          "template-users",
          "import-users-file",
          "import-users-btn",
          "import-users-result",
          true
        ) +
        importBlock(
          "sales",
          "Импорт продаж и баллов",
          "Начисление баллов ТП и СВ по кодам участников. Повторная загрузка той же строки не дублирует баллы.",
          "template-sales",
          "import-sales-file",
          "import-sales-btn",
          "import-sales-result",
          true
        ) +
      "</div>";
    bindImportActions();
  }

  function importBlock(id, title, desc, templatePath, fileId, btnId, resultId, showCelery) {
    return (
      '<div class="admin-card admin-import-block">' +
        '<h2 class="admin-import-block__title">' + L.escapeHtml(title) + "</h2>" +
        '<p class="admin-modal__meta">' + L.escapeHtml(desc) + "</p>" +
        '<div class="admin-modal__actions">' +
          '<button type="button" class="btn btn--ghost btn--sm" data-template="' + templatePath + '">Скачать шаблон</button>' +
        "</div>" +
        '<label class="field">' +
          '<span class="field__label">Файл .xlsx</span>' +
          '<input class="field__input" type="file" id="' + fileId + '" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet">' +
        "</label>" +
        (showCelery
          ? '<label class="checkbox-inline"><input type="checkbox" id="import-' + id + '-celery"><span>Отправить в фоновую очередь (Celery)</span></label>'
          : "") +
        '<button type="button" class="btn btn--primary btn--sm" id="' + btnId + '">Загрузить</button>' +
        '<div class="admin-import-result" id="' + resultId + '" hidden></div>' +
      "</div>"
    );
  }

  function formatImportResult(data) {
    if (!data) return "Готово";
    var lines = [];
    Object.keys(data).forEach(function (key) {
      if (data[key] !== null && data[key] !== undefined) {
        lines.push(key + ": " + data[key]);
      }
    });
    return lines.join("\n");
  }

  function bindImportActions() {
    document.querySelectorAll("[data-template]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var name = btn.getAttribute("data-template") === "template-users"
          ? "template-users.xlsx"
          : "template-sales.xlsx";
        PlombirApi.download("/import/" + btn.getAttribute("data-template"), name).catch(function (err) {
          L.showToast(document.getElementById("page-alert"), err.message, "error");
        });
      });
    });

    document.getElementById("import-users-btn").addEventListener("click", function () {
      uploadImport("users");
    });
    document.getElementById("import-sales-btn").addEventListener("click", function () {
      uploadImport("sales");
    });
  }

  function uploadImport(type) {
    var fileInput = document.getElementById(type === "users" ? "import-users-file" : "import-sales-file");
    var resultBox = document.getElementById(type === "users" ? "import-users-result" : "import-sales-result");
    var file = fileInput.files[0];
    if (!file) {
      L.showToast(document.getElementById("page-alert"), "Выберите файл .xlsx", "error");
      return;
    }

    var fd = new FormData();
    fd.append("file", file);
    var path = type === "users" ? "/import/users" : "/import/sales";
    var useCelery = document.getElementById("import-" + type + "-celery");
    if (useCelery && useCelery.checked) {
      path += "?use_celery=true";
    }

    resultBox.hidden = false;
    resultBox.className = "admin-import-result";
    resultBox.textContent = "Импорт выполняется…";

    PlombirApi.postForm(path, fd).then(function (result) {
      if (!result.response.ok || !result.data || !result.data.success) {
        resultBox.className = "admin-import-result admin-import-result--error";
        resultBox.textContent = PlombirApi.extractErrorMessage(result.data, "Ошибка импорта");
        return;
      }
      var data = result.data.data || {};
      if (data.queued && data.task_id) {
        resultBox.textContent = "Задача в очереди: " + data.task_id + "\nОжидание…";
        pollCeleryTask(type, data.task_id, resultBox);
        return;
      }
      resultBox.textContent = formatImportResult(data);
    }).catch(function () {
      resultBox.className = "admin-import-result admin-import-result--error";
      resultBox.textContent = "Не удалось связаться с сервером";
    });
  }

  function pollCeleryTask(type, taskId, resultBox) {
    var attempts = 0;
    var maxAttempts = 60;
    function tick() {
      attempts += 1;
      PlombirApi.get("/import/" + type + "/tasks/" + taskId).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          resultBox.className = "admin-import-result admin-import-result--error";
          resultBox.textContent = "Ошибка проверки статуса задачи";
          return;
        }
        var data = result.data.data || {};
        if (data.ready) {
          if (data.successful && data.result) {
            resultBox.textContent = formatImportResult(data.result);
          } else {
            resultBox.className = "admin-import-result admin-import-result--error";
            resultBox.textContent = data.error || "Импорт завершился с ошибкой";
          }
          return;
        }
        if (attempts >= maxAttempts) {
          resultBox.textContent = "Задача ещё выполняется. ID: " + taskId;
          return;
        }
        setTimeout(tick, 2000);
      });
    }
    tick();
  }

  PlombirAuth.requireAdmin().then(function (profile) {
    if (!profile) return;
    var content = L.mountAdminLayout({
      profile: profile,
      activeMenuId: "import",
      pageTitle: "Импорт Excel",
    });
    renderImportPage(content);
  });
})();
