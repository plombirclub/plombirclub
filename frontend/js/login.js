(function () {
  "use strict";

  var form = document.getElementById("login-form");
  var alertBox = document.getElementById("form-alert");
  var submitBtn = document.getElementById("login-submit");

  PlombirAuth.requireGuest();

  if (!form) return;

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    PlombirLayout.clearAlert(alertBox);

    var email = form.email.value.trim();
    var password = form.password.value;

    if (!email || !password) {
      PlombirLayout.showAlert(alertBox, "Заполните email и пароль", "error");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Вход…";

    PlombirApi.post("/auth/login", { email: email, password: password })
      .then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          PlombirLayout.showAlert(
            alertBox,
            PlombirApi.extractErrorMessage(result.data, "Неверный email или пароль"),
            "error"
          );
          return;
        }

        var data = result.data.data;
        if (data.first_login_required || !data.is_registration_complete) {
          PlombirAuth.redirect(PlombirAuth.FIRST_LOGIN_PAGE);
        } else if (data.role === "admin") {
          PlombirAuth.redirect(PlombirAuth.ADMIN_HOME_PAGE);
        } else {
          PlombirAuth.redirect(PlombirAuth.HOME_PAGE);
        }
      })
      .catch(function () {
        PlombirLayout.showAlert(alertBox, "Не удалось связаться с сервером", "error");
      })
      .finally(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = "Войти";
      });
  });
})();
