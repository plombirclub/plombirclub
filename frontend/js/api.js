/**
 * Общий клиент API — cookies + CSRF для POST/PUT/DELETE.
 */
(function (global) {
  "use strict";

  var API_BASE = "/api";

  function getCookie(name) {
    var match = document.cookie.match(new RegExp("(?:^|; )" + name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  function parseJsonResponse(response) {
    return response.text().then(function (text) {
      var data = null;
      if (text) {
        try {
          data = JSON.parse(text);
        } catch (_err) {
          data = { success: false, error: { message: "Некорректный ответ сервера" } };
        }
      }
      return { response: response, data: data };
    });
  }

  function extractErrorMessage(data, fallback) {
    if (!data) return fallback || "Ошибка запроса";
    if (data.error && data.error.message) return data.error.message;
    if (typeof data.detail === "string") return data.detail;
    return fallback || "Ошибка запроса";
  }

  function apiFetch(path, options) {
    options = options || {};
    var method = (options.method || "GET").toUpperCase();
    var headers = Object.assign({ Accept: "application/json" }, options.headers || {});

    if (options.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    if (method !== "GET" && method !== "HEAD") {
      var csrf = getCookie("csrf_token");
      if (csrf) {
        headers["X-CSRF-Token"] = csrf;
      }
    }

    return fetch(API_BASE + path, {
      method: method,
      credentials: "same-origin",
      headers: headers,
      body: options.body instanceof FormData
        ? options.body
        : options.body
          ? JSON.stringify(options.body)
          : undefined,
    }).then(parseJsonResponse);
  }

  global.PlombirApi = {
    get: function (path) {
      return apiFetch(path, { method: "GET" });
    },
    post: function (path, body) {
      return apiFetch(path, { method: "POST", body: body || {} });
    },
    put: function (path, body) {
      return apiFetch(path, { method: "PUT", body: body || {} });
    },
    putForm: function (path, formData) {
      return apiFetch(path, { method: "PUT", body: formData });
    },
    postForm: function (path, formData) {
      return apiFetch(path, { method: "POST", body: formData });
    },
    delete: function (path) {
      return apiFetch(path, { method: "DELETE" });
    },
    extractErrorMessage: extractErrorMessage,
    getCookie: getCookie,
    download: function (path, filename) {
      var headers = { Accept: "*/*" };
      var csrf = getCookie("csrf_token");
      if (csrf) {
        headers["X-CSRF-Token"] = csrf;
      }
      return fetch(API_BASE + path, {
        method: "GET",
        credentials: "same-origin",
        headers: headers,
      }).then(function (response) {
        if (!response.ok) {
          return response.text().then(function (text) {
            var message = "Не удалось скачать файл";
            try {
              var data = JSON.parse(text);
              message = extractErrorMessage(data, message);
            } catch (_err) {
              /* ignore */
            }
            throw new Error(message);
          });
        }
        return response.blob().then(function (blob) {
          var url = window.URL.createObjectURL(blob);
          var link = document.createElement("a");
          link.href = url;
          link.download = filename || "download";
          document.body.appendChild(link);
          link.click();
          link.remove();
          window.URL.revokeObjectURL(url);
        });
      });
    },
  };
})(window);
