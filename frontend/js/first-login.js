(function () {
  "use strict";

  var profile = null;
  var contentRoot = null;
  var alertBox = null;

  PlombirAuth.requireAuth({ allowIncomplete: true, requireIncomplete: true }).then(function (p) {
    if (!p) return;
    profile = p;
    contentRoot = PlombirLayout.mountLayout({
      mode: "first-login",
      profile: profile,
      pageTitle: "Завершение регистрации",
      menuDisabled: true,
    });
    renderWizard();
  });

  function renderWizard() {
    if (!contentRoot) return;

    var steps = buildSteps();
    var currentStep = steps.find(function (s) { return !s.done; }) || steps[steps.length - 1];

    contentRoot.innerHTML =
      '<div class="first-login">' +
        '<p class="first-login__intro">Для доступа к личному кабинету завершите регистрацию. До этого разделы с баллами, призами и заданиями недоступны.</p>' +
        '<ol class="stepper">' +
          steps.map(function (step, index) {
            var cls = "stepper__item";
            if (step.done) cls += " stepper__item--done";
            if (step.id === currentStep.id) cls += " stepper__item--active";
            return (
              '<li class="' + cls + '">' +
                '<span class="stepper__num">' + (step.done ? "✓" : index + 1) + "</span>" +
                '<span class="stepper__label">' + step.label + "</span>" +
              "</li>"
            );
          }).join("") +
        "</ol>" +
        '<div id="wizard-alert"></div>' +
        '<div class="panel-block" id="wizard-panel"></div>' +
      "</div>";

    alertBox = document.getElementById("wizard-alert");
    var panel = document.getElementById("wizard-panel");

    if (currentStep.id === "phone") renderPhoneStep(panel);
    else if (currentStep.id === "password") renderPasswordStep(panel);
    else if (currentStep.id === "agreements") renderAgreementsStep(panel);
    else renderCompleteStep(panel);
  }

  function buildSteps() {
    return [
      { id: "phone", label: "Телефон", done: !!profile.phone_verified },
      { id: "password", label: "Новый пароль", done: !!profile.temporary_password_changed },
      { id: "agreements", label: "Согласия", done: !!profile.agreements_accepted },
      { id: "done", label: "Готово", done: !!profile.is_registration_complete },
    ];
  }

  function refreshProfile() {
    return PlombirAuth.fetchProfile().then(function (p) {
      if (p) profile = p;
      return profile;
    });
  }

  function renderPhoneStep(panel) {
    panel.innerHTML =
      '<h2 class="panel-block__title">Подтверждение телефона</h2>' +
      '<p class="panel-block__text">Укажите номер мобильного телефона и подтвердите его кодом из SMS или email.</p>' +
      '<form id="phone-form" class="form-grid">' +
        '<label class="field"><span class="field__label">Телефон</span>' +
          '<input class="field__input" type="tel" name="phone" placeholder="+7 (999) 123-45-67" required autocomplete="tel">' +
        "</label>" +
        '<div class="verify-tabs">' +
          '<button type="button" class="verify-tabs__btn verify-tabs__btn--active" data-method="sms">Код по SMS</button>' +
          '<button type="button" class="verify-tabs__btn" data-method="email">Код на email</button>' +
        "</div>" +
        '<div class="form-actions">' +
          '<button type="button" class="btn btn--primary" id="send-code-btn">Отправить код</button>' +
        "</div>" +
        '<label class="field"><span class="field__label">Код подтверждения</span>' +
          '<input class="field__input" type="text" name="code" inputmode="numeric" maxlength="6" placeholder="6 цифр" autocomplete="one-time-code">' +
        "</label>" +
        '<div class="form-actions">' +
          '<button type="submit" class="btn btn--primary">Подтвердить телефон</button>' +
        "</div>" +
      "</form>";

    var form = document.getElementById("phone-form");
    var method = "sms";
    var tabs = panel.querySelectorAll(".verify-tabs__btn");

    tabs.forEach(function (btn) {
      btn.addEventListener("click", function () {
        tabs.forEach(function (b) { b.classList.remove("verify-tabs__btn--active"); });
        btn.classList.add("verify-tabs__btn--active");
        method = btn.getAttribute("data-method");
      });
    });

    document.getElementById("send-code-btn").addEventListener("click", function () {
      PlombirLayout.clearAlert(alertBox);
      var phone = form.phone.value.trim();
      if (!phone) {
        PlombirLayout.showAlert(alertBox, "Введите номер телефона", "error");
        return;
      }

      var sendPromise = method === "sms"
        ? PlombirApi.post("/auth/send-sms-code", { phone: phone })
        : sendEmailCodeWithPhone(phone);

      sendPromise.then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          PlombirLayout.showAlert(alertBox, PlombirApi.extractErrorMessage(result.data), "error");
          return;
        }
        var msg = method === "sms"
          ? "Код отправлен по SMS"
          : "Код отправлен на " + (profile.email || "email");
        if (result.data.data && result.data.data.debug_code) {
          msg += ". Режим разработки: код — " + result.data.data.debug_code;
        }
        PlombirLayout.showAlert(alertBox, msg, "success");
      });
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      PlombirLayout.clearAlert(alertBox);
      var phone = form.phone.value.trim();
      var code = form.code.value.trim();
      if (!phone || !code) {
        PlombirLayout.showAlert(alertBox, "Введите телефон и код", "error");
        return;
      }

      var verifyPromise = method === "sms"
        ? PlombirApi.post("/auth/verify-sms-code", { phone: phone, code: code })
        : PlombirApi.post("/auth/verify-email-code", { code: code });

      verifyPromise.then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          PlombirLayout.showAlert(alertBox, PlombirApi.extractErrorMessage(result.data), "error");
          return;
        }
        refreshProfile().then(renderWizard);
      });
    });
  }

  function sendEmailCodeWithPhone(phone) {
    return PlombirApi.post("/auth/send-sms-code", { phone: phone }).then(function (smsResult) {
      if (!smsResult.response.ok) return smsResult;
      return PlombirApi.post("/auth/send-email-code");
    });
  }

  function renderPasswordStep(panel) {
    panel.innerHTML =
      '<h2 class="panel-block__title">Смена временного пароля</h2>' +
      '<p class="panel-block__text">Придумайте постоянный пароль не короче 8 символов.</p>' +
      '<form id="password-form" class="form-grid">' +
        '<label class="field"><span class="field__label">Текущий пароль</span>' +
          '<input class="field__input" type="password" name="current_password" required autocomplete="current-password">' +
        "</label>" +
        '<label class="field"><span class="field__label">Новый пароль</span>' +
          '<input class="field__input" type="password" name="new_password" minlength="8" required autocomplete="new-password">' +
        "</label>" +
        '<label class="field"><span class="field__label">Повторите новый пароль</span>' +
          '<input class="field__input" type="password" name="new_password_confirm" minlength="8" required autocomplete="new-password">' +
        "</label>" +
        '<div class="form-actions">' +
          '<button type="submit" class="btn btn--primary">Сохранить пароль</button>' +
        "</div>" +
      "</form>";

    document.getElementById("password-form").addEventListener("submit", function (event) {
      event.preventDefault();
      PlombirLayout.clearAlert(alertBox);
      var form = event.target;
      if (form.new_password.value !== form.new_password_confirm.value) {
        PlombirLayout.showAlert(alertBox, "Новые пароли не совпадают", "error");
        return;
      }

      PlombirApi.post("/auth/change_password", {
        current_password: form.current_password.value,
        new_password: form.new_password.value,
      }).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          PlombirLayout.showAlert(alertBox, PlombirApi.extractErrorMessage(result.data), "error");
          return;
        }
        refreshProfile().then(renderWizard);
      });
    });
  }

  function agreementLink(docKey) {
    return (
      ' <a class="agreement-link" href="/pages/agreement.html?doc=' + docKey + '" target="_blank" rel="noopener noreferrer">Прочитать</a>'
    );
  }

  function renderAgreementsStep(panel) {
    panel.innerHTML =
      '<h2 class="panel-block__title">Согласия</h2>' +
      '<p class="panel-block__text">Для участия в программе необходимо принять все согласия. Перед этим можно открыть и прочитать каждый документ.</p>' +
      '<form id="agreements-form" class="form-grid">' +
        '<label class="checkbox-field">' +
          '<input type="checkbox" name="personal_data_accepted" required>' +
          '<span>Согласие на обработку персональных данных (ФЗ-152)' + agreementLink("personal_data") + "</span>" +
        "</label>" +
        '<label class="checkbox-field">' +
          '<input type="checkbox" name="program_rules_accepted" required>' +
          '<span>Пользовательское соглашение' + agreementLink("program_rules") + "</span>" +
        "</label>" +
        '<label class="checkbox-field">' +
          '<input type="checkbox" name="email_notifications_accepted" required>' +
          '<span>Согласие на получение email-уведомлений' + agreementLink("email_notifications") + "</span>" +
        "</label>" +
        '<div class="form-actions">' +
          '<button type="submit" class="btn btn--primary">Принять и продолжить</button>' +
        "</div>" +
      "</form>";

    document.getElementById("agreements-form").addEventListener("submit", function (event) {
      event.preventDefault();
      PlombirLayout.clearAlert(alertBox);
      var form = event.target;

      PlombirApi.post("/auth/accept_agreements", {
        personal_data_accepted: form.personal_data_accepted.checked,
        program_rules_accepted: form.program_rules_accepted.checked,
        email_notifications_accepted: form.email_notifications_accepted.checked,
      }).then(function (result) {
        if (!result.response.ok || !result.data || !result.data.success) {
          PlombirLayout.showAlert(alertBox, PlombirApi.extractErrorMessage(result.data), "error");
          return;
        }
        refreshProfile().then(renderWizard);
      });
    });
  }

  function renderCompleteStep(panel) {
    panel.innerHTML =
      '<div class="first-login__done">' +
        '<h2 class="panel-block__title">Регистрация завершена</h2>' +
        '<p class="panel-block__text">Теперь вам доступны все разделы личного кабинета.</p>' +
        '<a class="btn btn--primary" href="' + PlombirAuth.HOME_PAGE + '">Перейти в личный кабинет</a>' +
      "</div>";
  }
})();
