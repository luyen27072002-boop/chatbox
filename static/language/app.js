(() => {
  "use strict";

  const scenes = window.LANGUAGE_SCENES || [];
  const imageBase = window.LANGUAGE_IMAGE_BASE || "/static/language/images/";
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  let current = null;
  let sessionId = null;
  let suggestion = "";
  let toastTimer = null;

  const landing = $("#landing");
  const game = $("#game");

  function image(name) {
    return `${imageBase}${name}`;
  }

  function showToast(message, isError = false) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.remove("hidden", "error");
    if (isError) toast.classList.add("error");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.add("hidden"), 3200);
  }

  async function api(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    let data = {};
    try {
      data = await response.json();
    } catch {
      data = {};
    }
    if (response.status === 401) {
      window.location.href = "/";
      throw new Error("Bạn cần đăng nhập lại.");
    }
    if (!response.ok) {
      const error = new Error(data.error || `Request failed: ${response.status}`);
      error.code = data.code || "request_failed";
      error.payload = data;
      throw error;
    }
    return data;
  }

  function quotaLabel(quota = {}) {
    if (quota.permanent_test) return "KHÔNG GIỚI HẠN";
    if (quota.unlimited_active) return `HÔM NAY CÒN ${quota.unlimited_daily_remaining || 0}`;
    const remaining = Number(quota.finite_remaining || 0);
    return `CÒN ${Math.max(0, remaining)} LƯỢT`;
  }

  function updateQuota(quota) {
    if (quota) $("#quotaBadge").textContent = quotaLabel(quota);
  }

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
  }

  async function loadStatus() {
    try {
      const data = await api("/api/language/status");
      $("#modeBadge").textContent = data.mode === "online-ai" ? "TRỰC TUYẾN" : "DEMO DỰ PHÒNG";
      updateQuota(data.quota);
    } catch (error) {
      $("#modeBadge").textContent = "CHƯA KẾT NỐI";
      showToast(error.message, true);
    }
  }

  async function loadOverview() {
    try {
      const data = await api("/api/language/overview");
      updateQuota(data.quota);
      renderRecent(data.sessions || []);
    } catch (error) {
      $("#recentSessions").innerHTML = `<div class="empty-recent">Không tải được lịch sử lúc này.</div>`;
    }
  }

  function renderRecent(items) {
    const root = $("#recentSessions");
    root.innerHTML = "";
    if (!items.length) {
      root.innerHTML = `<div class="empty-recent">Chưa có phiên nào. Chọn một cảnh phía trên để bắt đầu.</div>`;
      return;
    }
    items.slice(0, 6).forEach((item) => {
      const card = document.createElement("article");
      card.className = "recent-card";
      const stateLabel = item.status === "completed" ? "Đã hoàn thành" : item.status === "active" ? "Đang chơi" : "Đã dừng";
      card.innerHTML = `
        <div><strong>${escapeHtml(item.scene?.title || "Cảnh đã lưu")}</strong><small>${escapeHtml(stateLabel)}</small></div>
        <p>${Number(item.progress || 0)}% nhiệm vụ · ${Number(item.score || 0)} điểm · ${Number(item.turns_used || 0)} lượt</p>
        <small>${escapeHtml(formatDate(item.updated_at))}</small>
        <button type="button" ${item.status !== "active" ? "disabled" : ""}>${item.status === "active" ? "Chơi tiếp →" : "Đã khép lại"}</button>
      `;
      const button = card.querySelector("button");
      if (item.status === "active") button.addEventListener("click", () => resume(item.id));
      root.appendChild(card);
    });
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function stats(score, progress) {
    $("#scoreText").textContent = String(score);
    $("#progressBar").style.width = `${progress}%`;
  }

  function setMood(name) {
    if (!current) return;
    $("#characterImage").src = image(current.character[name] || current.character.confused);
    $("#moodLabel").textContent = {
      happy: "HÀI LÒNG BẤT NGỜ",
      confused: "NÃO ĐANG BUFFER",
      shocked: "TINH THẦN BAY MÀU",
    }[name] || "KHÓ ĐOÁN";
  }

  function bubble(type, text) {
    const node = document.createElement("div");
    node.className = `bubble ${type}`;
    node.textContent = text;
    $("#chatLog").appendChild(node);
    $("#chatLog").scrollTop = $("#chatLog").scrollHeight;
  }

  function insert(text) {
    const input = $("#replyInput");
    const position = input.selectionStart;
    const before = input.value.slice(0, position);
    const after = input.value.slice(input.selectionEnd);
    const space = before && !before.endsWith(" ") ? " " : "";
    input.value = before + space + text + after;
    input.selectionStart = input.selectionEnd = (before + space + text).length;
    input.focus();
    count();
  }

  function effect(name) {
    const layer = $("#effectLayer");
    layer.innerHTML = "";
    if (name === "boom") {
      const node = document.createElement("div");
      node.className = "boom";
      node.textContent = "BOÀNG!";
      layer.appendChild(node);
      $("#stage").classList.add("wiggle");
      setTimeout(() => $("#stage").classList.remove("wiggle"), 500);
    } else if (name === "spark") {
      for (let index = 0; index < 22; index += 1) {
        const node = document.createElement("i");
        node.className = "confetti";
        node.style.left = `${Math.random() * 100}%`;
        node.style.top = `${-20 - Math.random() * 100}px`;
        layer.appendChild(node);
      }
    } else {
      $("#characterImage").classList.add("wiggle");
      setTimeout(() => $("#characterImage").classList.remove("wiggle"), 500);
    }
    setTimeout(() => { layer.innerHTML = ""; }, 1100);
  }

  function buildVocab(scene) {
    const root = $("#vocabChips");
    root.innerHTML = "";
    (scene.vocab || []).forEach((value) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = value;
      button.addEventListener("click", () => insert(value));
      root.appendChild(button);
    });
  }

  function showFeedback(item = {}) {
    const feedback = String(item.feedback || "").trim();
    suggestion = String(item.suggestion || "").trim();
    if (!feedback && !suggestion) {
      $("#feedbackBox").classList.add("hidden");
      return;
    }
    $("#feedbackText").textContent = feedback;
    $("#useSuggestionBtn").textContent = suggestion ? `Thử câu hay hơn: “${suggestion}”` : "Không có gợi ý";
    $("#feedbackBox").classList.remove("hidden");
  }

  function setCompleted(completed) {
    $("#replyInput").disabled = completed;
    $("#sendBtn").disabled = completed;
    $("#sendBtn").textContent = completed ? "Cảnh đã hoàn thành" : "Nói câu này";
    $("#completionBox").classList.toggle("hidden", !completed);
  }

  function openGame(scene, sessionData, messages) {
    current = scene;
    sessionId = sessionData.id || sessionData.session_id;
    landing.classList.add("hidden");
    game.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });

    $("#missionTitle").textContent = current.title;
    $("#missionText").textContent = current.mission;
    $("#playerRole").textContent = current.player_role;
    $("#speakerName").textContent = current.npc_name;
    $("#chatCharacter").textContent = current.npc_name;
    $("#sceneBackground").src = image(current.background);
    $("#characterImage").src = image(current.character.happy);
    $("#chatLog").innerHTML = "";
    $("#feedbackBox").classList.add("hidden");
    $("#narratorBox").classList.add("hidden");
    $("#replyInput").value = "";
    count();
    buildVocab(current);

    const history = Array.isArray(messages) ? messages : [];
    history.forEach((item) => bubble(item.role === "player" ? "player" : "npc", item.text));
    const lastNpc = [...history].reverse().find((item) => item.role === "npc") || { text: current.opening };
    $("#dialogueText").textContent = lastNpc.text || current.opening;
    $("#narratorBox").textContent = lastNpc.narrator || "";
    $("#narratorBox").classList.toggle("hidden", !lastNpc.narrator);
    showFeedback(lastNpc);
    setMood(lastNpc.mood || "happy");
    stats(Number(sessionData.score ?? 50), Number(sessionData.progress ?? 0));
    setCompleted(sessionData.status === "completed" || Boolean(sessionData.completed));
    if (!$("#replyInput").disabled) $("#replyInput").focus();
  }

  async function start(sceneId) {
    const scene = scenes.find((item) => item.id === sceneId);
    if (!scene) return;
    try {
      const data = await api("/api/language/start", {
        method: "POST",
        body: JSON.stringify({
          scene_id: sceneId,
          level: $("#levelSelect").value,
          humor: $("#humorSelect").value,
        }),
      });
      openGame(scene, { ...data, id: data.session_id }, [{ role: "npc", text: data.opening }]);
      loadOverview();
    } catch (error) {
      showToast(error.message, true);
    }
  }

  async function resume(id) {
    try {
      const data = await api(`/api/language/sessions/${encodeURIComponent(id)}`);
      openGame(data.scene, data.session, data.messages || []);
    } catch (error) {
      showToast(error.message, true);
      loadOverview();
    }
  }

  async function leaveGame() {
    const oldSession = sessionId;
    sessionId = null;
    current = null;
    setCompleted(false);
    game.classList.add("hidden");
    landing.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (oldSession) {
      try {
        await api("/api/language/reset", { method: "POST", body: JSON.stringify({ session_id: oldSession }) });
      } catch {
        // Phiên vẫn có thể được tải lại nếu request dừng không thành công.
      }
    }
    loadOverview();
  }

  $("#languageSelect").addEventListener("change", (event) => {
    $$(".scene-card").forEach((card) => {
      card.classList.toggle("hidden", event.target.value !== "all" && card.dataset.language !== event.target.value);
    });
  });

  $$(".playBtn").forEach((button) => button.addEventListener("click", () => start(button.dataset.scene)));

  $("#replyForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = $("#replyInput");
    const message = input.value.trim();
    if (!message || !sessionId) return;

    bubble("player", message);
    input.value = "";
    count();
    input.disabled = true;
    $("#sendBtn").disabled = true;
    $("#sendBtn").textContent = "NPC đang nghĩ…";
    $("#liveLabel").textContent = "● ĐANG XỬ LÝ";

    try {
      const data = await api("/api/language/respond", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, message }),
      });
      bubble("npc", data.reply);
      $("#dialogueText").textContent = data.reply;
      $("#narratorBox").textContent = data.narrator || "";
      $("#narratorBox").classList.toggle("hidden", !data.narrator);
      showFeedback(data);
      stats(data.score, data.progress);
      setMood(data.mood);
      effect(data.effect);
      updateQuota(data.quota);
      setCompleted(Boolean(data.completed));
      if (data.used_demo) showToast("Lượt này dùng chế độ dự phòng nhưng tiến độ vẫn đã được lưu.");
      if (data.completed) loadOverview();
    } catch (error) {
      bubble("npc", `Hệ thống chưa xử lý được lượt này: ${error.message}`);
      showToast(error.message, true);
      if (error.payload?.quota) updateQuota(error.payload.quota);
    } finally {
      $("#liveLabel").textContent = "● SẴN SÀNG";
      if (!$("#completionBox").classList.contains("hidden")) return;
      input.disabled = false;
      $("#sendBtn").disabled = false;
      $("#sendBtn").textContent = "Nói câu này";
      input.focus();
    }
  });

  $("#useSuggestionBtn").addEventListener("click", () => {
    if (!suggestion) return;
    $("#replyInput").value = suggestion;
    count();
    $("#replyInput").focus();
  });

  $("#hintBtn").addEventListener("click", () => {
    if (!current) return;
    const items = current.suggestions || [];
    suggestion = items[Math.floor(Math.random() * items.length)] || "";
    $("#feedbackText").textContent = "Phao cứu sinh vừa rơi từ trên trời xuống.";
    $("#useSuggestionBtn").textContent = suggestion ? `Gợi ý: “${suggestion}”` : "Chưa có gợi ý";
    $("#feedbackBox").classList.remove("hidden");
  });

  function count() {
    $("#charCount").textContent = `${$("#replyInput").value.length}/500`;
  }

  $("#replyInput").addEventListener("input", count);
  $("#replyInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      $("#replyForm").requestSubmit();
    }
  });
  $("#backBtn").addEventListener("click", leaveGame);
  $("#newSceneBtn").addEventListener("click", leaveGame);

  const dialog = $("#howDialog");
  $("#howBtn").addEventListener("click", () => dialog.showModal());
  $("#closeHowBtn").addEventListener("click", () => dialog.close());

  document.addEventListener("DOMContentLoaded", () => {
    loadStatus();
    loadOverview();
  });
})();
