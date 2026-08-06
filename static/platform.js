
(() => {
  "use strict";

  const firstNumber = (...values) => {
    for (const value of values) {
      const number = Number(value);
      if (Number.isFinite(number)) return number;
    }
    return null;
  };

  const t = (key, vars = {}) => window.ML_I18N?.t ? window.ML_I18N.t(key, vars) : key;

  const quotaText = (payload) => {
    const account = payload?.account || {};
    const quota = payload?.quota || {};
    if (account.permanent_test || quota.permanent_test) return "Tài khoản test không giới hạn";
    if (quota.unlimited_active) return `Gói không giới hạn · hôm nay còn ${quota.unlimited_daily_remaining ?? 0}`;
    const daily = firstNumber(quota.daily_remaining);
    const welcome = firstNumber(quota.welcome_remaining);
    const paid = firstNumber(quota.purchased_credits);
    const monthly = firstNumber(quota.subscription_remaining);
    const parts = [];
    if (daily !== null) parts.push(`Hôm nay ${Math.max(0, daily)}`);
    if (welcome && welcome > 0) parts.push(`Chào mừng ${welcome}`);
    if (monthly && monthly > 0) parts.push(`Gói tháng ${monthly}`);
    if (paid && paid > 0) parts.push(`Đã mua ${paid}`);
    return parts.length ? `${parts.join(" · ")} lượt` : "Hiện không còn lượt";
  };

  async function api(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (response.status === 401) {
      window.location.href = "/";
      return null;
    }
    if (!response.ok) throw new Error(`Request failed: ${response.status}`);
    return response.json();
  }

  async function loadAccount() {
    try {
      const payload = await api("/api/session", { method: "POST", body: "{}" });
      if (!payload) return;
      const account = payload.account || {};
      const name = String(account.display_name || "Bạn").trim() || "Bạn";
      const identity = account.username ? `@${account.username}` : String(account.email || t("common.loggedIn"));
      const status = quotaText(payload);
      document.getElementById("platformAccountName").textContent = name;
      document.getElementById("platformAccountInitial").textContent = name.slice(0, 1).toUpperCase();
      document.getElementById("platformAccountStatus").textContent = status;
      document.getElementById("platformMenuName").textContent = name;
      document.getElementById("platformMenuIdentity").textContent = identity;
      document.getElementById("platformMenuQuota").textContent = status;
    } catch {
      document.getElementById("platformAccountStatus").textContent = t("common.loggedIn");
    }
  }

  async function loadProgress() {
    try {
      const [language, life] = await Promise.all([
        api("/api/language/overview"),
        api("/api/life/overview"),
      ]);
      if (language) {
        const sessions = Array.isArray(language.sessions) ? language.sessions : [];
        const completed = Number(language.completed_count || 0);
        const active = language.active_session;
        const text = active
          ? t("home.dynamic.activePlaying", { title: active.scene?.title || "một cảnh", progress: active.progress ?? 0 })
          : completed
            ? t("home.dynamic.completedCount", { count: completed })
            : sessions.length
              ? t("home.dynamic.triedCount", { count: sessions.length })
              : t("home.dynamic.noSession");
        document.getElementById("languageProgressText").textContent = text;
      }
      if (life) {
        const entries = Array.isArray(life.entries) ? life.entries.length : 0;
        const threads = Array.isArray(life.threads) ? life.threads.filter((item) => item.status !== "closed").length : 0;
        document.getElementById("lifeProgressText").textContent = entries || threads
          ? t("home.dynamic.lifeStats", { entries, threads })
          : t("home.dynamic.lifeWaiting");
      }
    } catch {
      // Still usable if stats fail.
    }
  }

  function setupAccountMenu() {
    const button = document.getElementById("platformAccountButton");
    const menu = document.getElementById("platformAccountMenu");
    const logout = document.getElementById("platformLogoutButton");
    const close = () => {
      menu.hidden = true;
      button.setAttribute("aria-expanded", "false");
    };
    button?.addEventListener("click", (event) => {
      event.stopPropagation();
      const open = menu.hidden;
      menu.hidden = !open;
      button.setAttribute("aria-expanded", String(open));
    });
    menu?.addEventListener("click", (event) => event.stopPropagation());
    document.addEventListener("click", close);
    document.addEventListener("keydown", (event) => event.key === "Escape" && close());
    logout?.addEventListener("click", async () => {
      logout.disabled = true;
      try {
        await api("/api/auth/logout", { method: "POST", body: "{}" });
        window.location.href = "/";
      } catch {
        logout.disabled = false;
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupAccountMenu();
    loadAccount();
    loadProgress();
    document.addEventListener("moloi:languagechange", loadProgress);
  });
})();
