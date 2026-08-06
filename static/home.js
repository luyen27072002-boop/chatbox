(() => {
  "use strict";

  const t = (key, vars = {}) => window.ML_I18N?.t ? window.ML_I18N.t(key, vars) : key;

  const excerpt = (value, max = 120) => {
    const clean = String(value || "").replace(/\s+/g, " ").trim();
    return clean.length > max ? `${clean.slice(0, max).trim()}…` : clean;
  };

  const firstNumber = (...values) => {
    for (const value of values) {
      const number = Number(value);
      if (Number.isFinite(number)) return number;
    }
    return null;
  };

  const formatAccountStatus = (payload) => {
    const account = payload?.account || {};
    const quota = payload?.quota || {};
    const subscription = quota.subscription || quota.active_subscription || {};

    if (
      account.permanent_test ||
      quota.permanent_test ||
      quota.is_permanent_test ||
      quota.unlimited ||
      quota.is_unlimited ||
      subscription.unlimited
    ) {
      return account.permanent_test || quota.permanent_test || quota.is_permanent_test
        ? "Tài khoản test không giới hạn"
        : "Gói không giới hạn đang hoạt động";
    }

    const dailyRemaining = firstNumber(
      quota.daily_remaining,
      quota.free_daily_remaining,
      quota.today_remaining,
    );
    const welcomeRemaining = firstNumber(
      quota.welcome_remaining,
      quota.free_welcome_remaining,
    );
    const purchased = firstNumber(
      quota.purchased_credits,
      quota.credits_remaining,
      quota.paid_remaining,
    );

    const parts = [];
    if (dailyRemaining !== null) parts.push(`Hôm nay còn ${Math.max(0, dailyRemaining)}`);
    if (welcomeRemaining !== null && welcomeRemaining > 0) parts.push(`Chào mừng ${welcomeRemaining}`);
    if (purchased !== null && purchased > 0) parts.push(`Đã mua ${purchased}`);
    return parts.length ? parts.join(" · ") : "Đã đăng nhập";
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
      const username = String(account.username || "").trim();
      const email = String(account.email || "").trim();
      const initial = name.slice(0, 1).toUpperCase() || "B";
      const status = formatAccountStatus(payload);

      document.getElementById("homeAccountName").textContent = name;
      document.getElementById("homeAccountStatus").textContent = status;
      document.getElementById("homeAccountInitial").textContent = initial;
      document.getElementById("homeAccountInitialLarge").textContent = initial;
      document.getElementById("homeMenuName").textContent = name;
      document.getElementById("homeMenuUsername").textContent = username ? `@${username}` : t("common.loggedIn");
      document.getElementById("homeMenuEmail").textContent = email;
      document.getElementById("homeAccountQuota").textContent = status;
    } catch {
      document.getElementById("homeAccountStatus").textContent = t("common.loggedIn");
      document.getElementById("homeAccountQuota").textContent = t("common.loadingQuotaLong");
    }
  }

  async function loadSnapshot() {
    if (!document.getElementById("homeEntries")) return;
    try {
      const payload = await api("/api/life/overview");
      if (!payload) return;
      const entries = Array.isArray(payload.entries) ? payload.entries : [];
      const threads = Array.isArray(payload.threads) ? payload.threads : [];
      const sessions = Array.isArray(payload.sessions) ? payload.sessions : [];
      const openThreads = threads.filter((row) => row.status !== "closed");

      document.getElementById("homeEntries").textContent = String(entries.length);
      document.getElementById("homeThreads").textContent = String(openThreads.length);
      document.getElementById("homeRehearsals").textContent = String(sessions.length);

      const note = document.getElementById("homeRecentNote");
      if (openThreads[0]) {
        note.textContent = `Đang tiếp diễn: ${openThreads[0].title}. ${excerpt(openThreads[0].detail, 90)}`;
      } else if (entries[0]) {
        note.textContent = `Trang gần nhất: ${entries[0].title}. ${excerpt(entries[0].rewritten_text, 90)}`;
      }
    } catch {
      // Trang chủ vẫn dùng được khi phần thống kê chưa tải xong.
    }
  }

  function setupAccountMenu() {
    const button = document.getElementById("homeAccountButton");
    const menu = document.getElementById("homeAccountMenu");
    const logout = document.getElementById("homeLogoutButton");
    if (!button || !menu || !logout) return;

    const closeMenu = () => {
      menu.hidden = true;
      button.setAttribute("aria-expanded", "false");
    };

    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const willOpen = menu.hidden;
      menu.hidden = !willOpen;
      button.setAttribute("aria-expanded", String(willOpen));
    });

    menu.addEventListener("click", (event) => event.stopPropagation());
    document.addEventListener("click", closeMenu);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeMenu();
    });

    logout.addEventListener("click", async () => {
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
    loadSnapshot();
  });
})();
