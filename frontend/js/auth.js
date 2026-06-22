/**
 * Авторизация и проверка сессии.
 */
(function (global) {
  "use strict";

  var LOGIN_PAGE = "/pages/login.html";
  var FIRST_LOGIN_PAGE = "/pages/first-login.html";
  var HOME_PAGE = "/pages/home.html";
  var ADMIN_HOME_PAGE = "/admin/users.html";

  function redirect(url) {
    window.location.replace(url);
  }

  function homePageForProfile(profile) {
    if (profile && profile.role === "admin") {
      return ADMIN_HOME_PAGE;
    }
    return HOME_PAGE;
  }

  function fetchProfile() {
    return PlombirApi.get("/users/profile").then(function (result) {
      if (result.response.ok && result.data && result.data.success) {
        return result.data.data;
      }
      return null;
    });
  }

  function requireGuest() {
    return fetchProfile().then(function (profile) {
      if (!profile) return null;
      if (!profile.is_registration_complete) {
        redirect(FIRST_LOGIN_PAGE);
        return profile;
      }
      redirect(homePageForProfile(profile));
      return profile;
    });
  }

  function requireAuth(options) {
    options = options || {};
    return fetchProfile().then(function (profile) {
      if (!profile) {
        redirect(LOGIN_PAGE);
        return null;
      }
      if (!profile.is_registration_complete && !options.allowIncomplete) {
        redirect(FIRST_LOGIN_PAGE);
        return null;
      }
      if (profile.is_registration_complete && options.requireIncomplete) {
        redirect(HOME_PAGE);
        return null;
      }
      return profile;
    });
  }

  function logout() {
    return PlombirApi.post("/auth/logout").finally(function () {
      redirect(LOGIN_PAGE);
    });
  }

  function requireAdmin() {
    return fetchProfile().then(function (profile) {
      if (!profile) {
        redirect(LOGIN_PAGE);
        return null;
      }
      if (profile.role !== "admin") {
        redirect(HOME_PAGE);
        return null;
      }
      return profile;
    });
  }

  global.PlombirAuth = {
    LOGIN_PAGE: LOGIN_PAGE,
    FIRST_LOGIN_PAGE: FIRST_LOGIN_PAGE,
    HOME_PAGE: HOME_PAGE,
    ADMIN_HOME_PAGE: ADMIN_HOME_PAGE,
    homePageForProfile: homePageForProfile,
    fetchProfile: fetchProfile,
    requireGuest: requireGuest,
    requireAuth: requireAuth,
    requireAdmin: requireAdmin,
    logout: logout,
    redirect: redirect,
  };
})(window);
