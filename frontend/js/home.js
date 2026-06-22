(function () {
  "use strict";

  PlombirAuth.requireAuth().then(function (profile) {
    if (!profile) return;

    var contentRoot = PlombirLayout.mountLayout({
      mode: "full",
      profile: profile,
      activeMenuId: "",
      pageTitle: "Личный кабинет",
    });

    if (!contentRoot) return;

    var name = profile.full_name || profile.email || "участник";
    contentRoot.innerHTML =
      '<div class="welcome-card panel-block">' +
        '<h2 class="panel-block__title">Добро пожаловать, ' + PlombirLayout.escapeHtml(name) + "!</h2>" +
        '<p class="panel-block__text">Вы успешно вошли в промо-портал «Чистая Линия». Выберите раздел в меню слева.</p>' +
        (profile.distributor_name
          ? '<p class="panel-block__meta">Дистрибьютор: <strong>' + PlombirLayout.escapeHtml(profile.distributor_name) + "</strong></p>"
          : "") +
        '<div class="welcome-card__links">' +
          '<a class="btn btn--primary" href="/pages/profile.html">Профиль</a>' +
          '<a class="btn btn--secondary" href="/pages/catalog.html">Каталог призов</a>' +
        "</div>" +
        '<p class="welcome-card__note">Доступны профиль, каталог призов, условия акции, FAQ, инструкции и уведомления. Остальные разделы подключаются по плану.</p>' +
      "</div>";
  });
})();
