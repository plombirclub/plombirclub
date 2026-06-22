(function () {
  "use strict";

  var form = document.getElementById("forgot-form");
  var alertBox = document.getElementById("form-alert");
  var submitBtn = document.getElementById("forgot-submit");
  var successBox = document.getElementById("forgot-success");

  PlombirAuth.requireGuest();

  if (!form) return;

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    PlombirLayout.clearAlert(alertBox);
    if (successBox) successBox.hidden = true;

    var email = form.email.value.trim();
    if (!email) {
      PlombirLayout.showAlert(alertBox, "Введите email, указанный при регистрации", "error");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Отправка…";

    PlombirApi.post("/auth/forgot-password", { email: email })
      .then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          PlombirLayout.showAlert(
            alertBox,
            PlombirApi.extractErrorMessage(result.data, "Не удалось отправить запрос"),
            "error"
          );
          return;
        }

        var message = (result.data.data && result.data.data.message) ||
          "Если аккаунт существует, временный пароль отправлен на email";

        if (successBox) {
          successBox.hidden = false;
          successBox.textContent = message;
        } else {
          PlombirLayout.showAlert(alertBox, message, "success");
        }

        if (result.data.data && result.data.data.debug_temporary_password) {
          PlombirLayout.showAlert(
            alertBox,
            "Режим разработки: временный пароль — " + result.data.data.debug_temporary_password,
            "info"
          );
        }

        form.reset();
      })
      .catch(function () {
        PlombirLayout.showAlert(alertBox, "Не удалось связаться с сервером", "error");
      })
      .finally(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = "Восстановить";
      });
  });
})();
