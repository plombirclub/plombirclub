(function () {
  "use strict";

  PlombirAuth.fetchProfile().then(function (profile) {
    if (!profile) {
      PlombirAuth.redirect(PlombirAuth.LOGIN_PAGE);
      return;
    }
    if (!profile.is_registration_complete) {
      PlombirAuth.redirect(PlombirAuth.FIRST_LOGIN_PAGE);
      return;
    }
    PlombirAuth.redirect(PlombirAuth.homePageForProfile(profile));
  });
})();
