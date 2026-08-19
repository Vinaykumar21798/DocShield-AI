(function () {
  const AUTH_KEY = "docshield-ui-auth";

  function defaultApiBase() {
    if (window.location.protocol === "file:") {
      return "http://localhost:8001";
    }
    return window.location.origin;
  }

  function getAuth() {
    try {
      const parsed = JSON.parse(localStorage.getItem(AUTH_KEY) || "null");
      if (parsed && parsed.token && parsed.user) {
        return parsed;
      }
    } catch (error) {
      /* ignore corrupt storage */
    }
    return null;
  }

  function setAuth(token, user) {
    localStorage.setItem(AUTH_KEY, JSON.stringify({ token, user }));
  }

  function clearAuth() {
    localStorage.removeItem(AUTH_KEY);
  }

  function extractErrorMessage(payload) {
    if (!payload || typeof payload === "string") {
      return typeof payload === "string" ? payload : "";
    }
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      const messages = payload.detail
        .map(function (item) {
          if (item && typeof item === "object") {
            return item.msg || item.message || "";
          }
          return typeof item === "string" ? item : "";
        })
        .filter(Boolean);
      if (messages.length) {
        return messages.join(" ");
      }
    }
    if (typeof payload.message === "string") {
      return payload.message;
    }
    return "";
  }

  async function apiFetch(apiBase, path, options) {
    const requestOptions = options || {};
    const headers = new Headers(requestOptions.headers || {});
    const auth = getAuth();
    if (auth && auth.token) {
      headers.set("Authorization", `Bearer ${auth.token}`);
    }

    const init = Object.assign({}, requestOptions, { headers });
    if (init.body && !(init.body instanceof FormData) && typeof init.body !== "string") {
      headers.set("Content-Type", "application/json");
      init.body = JSON.stringify(init.body);
    }

    const response = await fetch(`${apiBase}${path}`, init);
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      try {
        const payload = await response.json();
        detail = extractErrorMessage(payload) || detail;
      } catch (error) {
        try {
          detail = await response.text();
        } catch (textError) {
          /* keep the HTTP status detail */
        }
      }
      const error = new Error(detail);
      error.status = response.status;
      throw error;
    }

    if (response.status === 204) {
      return null;
    }
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return response.json();
    }
    return response.text();
  }

  function showFormError(element, message) {
    if (element) {
      element.textContent = message;
      element.style.display = "block";
    }
  }

  function renderUserChip() {
    const auth = getAuth();
    const userLabel = document.getElementById("userName");
    const roleLabel = document.getElementById("userRole");
    if (auth) {
      if (userLabel) userLabel.textContent = auth.user.name || auth.user.email;
      if (roleLabel) roleLabel.textContent = auth.user.role || "USER";
    }
  }

  function setupPasswordToggles() {
    const buttons = document.querySelectorAll(".password-toggle");
    buttons.forEach(function (button) {
      const input = button.getAttribute("aria-controls")
        ? document.getElementById(button.getAttribute("aria-controls"))
        : null;
      if (!input) return;
      button.addEventListener("click", function () {
        const visible = input.type === "text";
        input.type = visible ? "password" : "text";
        button.classList.toggle("is-visible", !visible);
        button.setAttribute("aria-pressed", String(!visible));
        button.setAttribute("aria-label", visible ? "Show password" : "Hide password");
      });
    });
  }

  function setupThemeToggle() {
    const toggle = document.getElementById("themeToggle");
    const key = "docshield-ui-theme";
    function applyTheme(theme) {
      document.documentElement.setAttribute("data-theme", theme);
      localStorage.setItem(key, theme);
    }
    function preferredTheme() {
      const saved = localStorage.getItem(key);
      if (saved === "dark" || saved === "light") return saved;
      if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
        return "dark";
      }
      return "light";
    }
    applyTheme(preferredTheme());
    if (toggle) {
      toggle.addEventListener("click", () => {
        const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(next);
      });
    }
  }

  function bindLoginForm() {
    const form = document.getElementById("loginForm");
    if (!form) return;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const errorBox = document.getElementById("loginError");
      const submitButton = form.querySelector("button[type='submit']");

      const email = document.getElementById("loginEmail").value.trim();
      const password = document.getElementById("loginPassword").value;

      if (!email || !password) {
        showFormError(errorBox, "Enter your email and password.");
        return;
      }

      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showFormError(errorBox, "Please enter a valid email address.");
        return;
      }

      submitButton.disabled = true;
      submitButton.textContent = "Signing in...";
      try {
        const apiBase = (document.getElementById("apiBase").value || "").trim().replace(/\/+$/, "") || defaultApiBase();
        const result = await apiFetch(apiBase, "/auth/login", {
          method: "POST",
          body: { email, password },
        });
        setAuth(result.access_token, result.user);
        window.location.href = "index.html";
      } catch (error) {
        showFormError(errorBox, error.message || "Login failed.");
        submitButton.disabled = false;
        submitButton.textContent = "Login";
      }
    });
  }

  function bindSignupForm() {
    const form = document.getElementById("signupForm");
    if (!form) return;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const errorBox = document.getElementById("signupError");
      const submitButton = form.querySelector("button[type='submit']");

      const name = document.getElementById("signupName").value.trim();
      const email = document.getElementById("signupEmail").value.trim();
      const password = document.getElementById("signupPassword").value;
      const confirmPassword = document.getElementById("signupConfirm").value;
      const role = document.getElementById("signupRole").value;

      if (!name || !email || !password || !confirmPassword) {
        showFormError(errorBox, "Please fill in all fields.");
        return;
      }
      if (password.length < 8) {
        showFormError(errorBox, "Password must be at least 8 characters.");
        return;
      }
      if (password !== confirmPassword) {
        showFormError(errorBox, "Passwords do not match.");
        return;
      }

      submitButton.disabled = true;
      submitButton.textContent = "Creating account...";
      try {
        const apiBase = (document.getElementById("apiBase").value || "").trim().replace(/\/+$/, "") || defaultApiBase();
        const result = await apiFetch(apiBase, "/auth/signup", {
          method: "POST",
          body: { name, email, password, role },
        });
        setAuth(result.access_token, result.user);
        window.location.href = "index.html";
      } catch (error) {
        showFormError(errorBox, error.message || "Sign up failed.");
        submitButton.disabled = false;
        submitButton.textContent = "Create Account";
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    const apiBaseInput = document.getElementById("apiBase");
    if (apiBaseInput) {
      apiBaseInput.value = defaultApiBase();
    }
    setupThemeToggle();
    setupPasswordToggles();
    renderUserChip();
    bindLoginForm();
    bindSignupForm();
  });
})();