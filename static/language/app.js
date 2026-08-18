(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  let current = null;
  let sessionId = null;
  let currentMode = "mission";
  let suggestion = "";
  let toastTimer = null;
  let latestOverview = null;
  let selectedGender = "";
  let selectedLifeRole = "";
  let objectiveState = [];
  let returnTab = "games";
  let pendingStart = null;
  let currentChallenge = { required: false };
  let tutorialSteps = [];
  let tutorialIndex = 0;
  let gameCardsCache = [];
  let activeGameFilter = "all";
  let lessonItems = [];
  let lessonIndex = 0;
  let lessonModule = "";
  let lessonMode = "new";
  let lessonAnswerLocked = false;
  let speechRecognition = null;
  let experienceFeed = [];
  let experienceTimers = new Map();
  let experienceSelectedTerms = new Map();
  let curriculumData = null;
  let selectedGoalTrackId = "";
  let activeUnitState = null;
  let activeCheckpointStage = null;
  let curriculumActivityContext = null;
  let appearanceState = {
    skin_tone: "light",
    hair_style: "short",
    hair_color: "black",
    outfit_style: "casual",
    face_style: "smile",
  };

  const landing = $("#landing");
  const game = $("#game");

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function showToast(message, isError = false) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.remove("hidden", "error");
    if (isError) toast.classList.add("error");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.add("hidden"), 3400);
  }

  async function api(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    let data = {};
    try { data = await response.json(); } catch { data = {}; }
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
    return `CÒN ${Math.max(0, Number(quota.finite_remaining || 0))} LƯỢT`;
  }

  function updateQuota(quota) {
    if (quota) $("#quotaBadge").textContent = quotaLabel(quota);
  }

  function stars(value) {
    const n = Math.max(0, Math.min(3, Number(value || 0)));
    return `${"★".repeat(n)}${"☆".repeat(3 - n)}`;
  }

  function formatSkill(value) {
    return String(value || "")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function lifeRoleText(role) {
    return role === "worker" ? "Người đi làm" : role === "student" ? "Sinh viên" : "Chưa chọn cuộc sống";
  }

  function setActorDataset(node, appearance = {}, gender = "female", pose = "chat") {
    if (!node) return;
    node.dataset.gender = gender || "female";
    node.dataset.skin = appearance.skin_tone || "light";
    node.dataset.hairStyle = appearance.hair_style || "short";
    node.dataset.hairColor = appearance.hair_color || "black";
    node.dataset.outfit = appearance.outfit_style || "casual";
    node.dataset.face = appearance.face_style || "smile";
    node.dataset.pose = pose || "chat";
  }

  function refreshProfilePreview() {
    const preview = $("#profilePreview");
    if (!preview) return;
    const appearance = {
      skin_tone: $("#skinToneSelect")?.value || appearanceState.skin_tone,
      hair_style: $("#hairStyleSelect")?.value || appearanceState.hair_style,
      hair_color: $("#hairColorSelect")?.value || appearanceState.hair_color,
      outfit_style: $("#outfitStyleSelect")?.value || appearanceState.outfit_style,
      face_style: $("#faceStyleSelect")?.value || appearanceState.face_style,
    };
    appearanceState = { ...appearanceState, ...appearance };
    setActorDataset(preview, appearance, selectedGender || "female", "chat");
  }

  function sceneTheme(scene = {}) {
    const key = `${scene.id || ""} ${scene.location || ""} ${scene.title || ""}`.toLowerCase();
    if (key.includes("cafe") || key.includes("coffee") || key.includes("barista")) return "cafe";
    if (key.includes("store") || key.includes("shop") || key.includes("siêu thị") || key.includes("trash")) return "store";
    if (key.includes("class") || key.includes("lớp") || key.includes("school") || key.includes("campus") || key.includes("project")) return "school";
    if (key.includes("office") || key.includes("meeting") || key.includes("công ty") || key.includes("boss")) return "office";
    if (key.includes("gym")) return "gym";
    if (key.includes("date")) return "date";
    if (key.includes("room") || key.includes("home") || key.includes("nhà") || key.includes("ktx")) return "home";
    if (key.includes("alien") || key.includes("customs")) return "scan";
    return "street";
  }

  function playerPose(scene = {}) {
    const key = `${scene.id || ""} ${scene.location || ""} ${scene.title || ""}`.toLowerCase();
    if (key.includes("coffee") || key.includes("cafe") || key.includes("store") || key.includes("order")) return "order";
    if (key.includes("class") || key.includes("meeting") || key.includes("interview") || key.includes("project")) return "listen";
    if (key.includes("date") || key.includes("friend") || key.includes("wrong number")) return "chat";
    if (key.includes("trash") || key.includes("sell")) return "point";
    if (key.includes("gym")) return "wave";
    return "chat";
  }

  function npcPreset(scene = {}) {
    const theme = sceneTheme(scene);
    if (theme === "cafe") return { gender: "female", appearance: { skin_tone: "tan", hair_style: "bob", hair_color: "brown", outfit_style: "office", face_style: "calm" }, pose: "serve" };
    if (theme === "store") return { gender: "male", appearance: { skin_tone: "brown", hair_style: "short", hair_color: "black", outfit_style: "office", face_style: "cool" }, pose: "serve" };
    if (theme === "school") return { gender: "female", appearance: { skin_tone: "light", hair_style: "bun", hair_color: "black", outfit_style: "student", face_style: "calm" }, pose: "teach" };
    if (theme === "office") return { gender: "male", appearance: { skin_tone: "tan", hair_style: "short", hair_color: "brown", outfit_style: "office", face_style: "cool" }, pose: "teach" };
    if (theme === "date") return { gender: "female", appearance: { skin_tone: "light", hair_style: "long", hair_color: "brown", outfit_style: "casual", face_style: "cute" }, pose: "chat" };
    return { gender: "female", appearance: { skin_tone: "tan", hair_style: "bob", hair_color: "black", outfit_style: "casual", face_style: "smile" }, pose: "chat" };
  }

  function renderProfile(profile) {
    const gender = profile.character_gender || "";
    const role = profile.life_role || "";
    const appearance = profile.appearance || appearanceState;
    const fallbackName = gender === "male" ? "Nhân vật nam" : gender === "female" ? "Nhân vật nữ" : "Chưa tạo";
    $("#playerName").textContent = profile.character_name || fallbackName;
    $("#playerRoleBadge").textContent = lifeRoleText(role);
    $("#playerLevel").textContent = `Lv.${Number(profile.player_level || 1)}`;
    $("#playerXp").textContent = Number(profile.xp || 0).toLocaleString("vi-VN");
    $("#playerStreak").textContent = `${Number(profile.streak || 0)} ngày`;
    $("#xpBar").style.width = `${Math.min(100, (Number(profile.xp_into_level || 0) / Math.max(1, Number(profile.xp_to_next_level || 500))) * 100)}%`;
    const cefr = profile.cefr_level || "A1-A2";
    const goalLabels = { comprehensive: "Toàn diện", daily: "Giao tiếp hàng ngày", travel: "Du lịch", work: "Công việc", study: "Học tập", exam: "Thi cử" };
    if ($("#learnerCefr")) $("#learnerCefr").textContent = cefr;
    if ($("#learningGoalText")) $("#learningGoalText").textContent = goalLabels[profile.learning_goal || "comprehensive"] || "Toàn diện";
    if ($("#dailyMinutesText")) $("#dailyMinutesText").textContent = `${Number(profile.daily_minutes || 20)} phút/ngày`;

    setActorDataset($("#avatarMini"), appearance, gender || "female", "chat");
    appearanceState = { ...appearanceState, ...appearance };

    if (profile.target_language && $("#languageSelect").value !== profile.target_language && !latestOverview) {
      $("#languageSelect").value = profile.target_language;
    }

    selectedGender = gender;
    selectedLifeRole = role;
    $("#characterNameInput").value = profile.character_name || "";
    $("#profileLanguage").value = profile.target_language || "en";
    $("#skinToneSelect").value = appearance.skin_tone || "light";
    $("#hairStyleSelect").value = appearance.hair_style || "short";
    $("#hairColorSelect").value = appearance.hair_color || "black";
    $("#outfitStyleSelect").value = appearance.outfit_style || "casual";
    $("#faceStyleSelect").value = appearance.face_style || "smile";
    if ($("#learningGoalSelect")) $("#learningGoalSelect").value = profile.learning_goal || "comprehensive";
    if ($("#dailyMinutesSelect")) $("#dailyMinutesSelect").value = String(profile.daily_minutes || 20);
    if ($("#cefrLevelSelect")) $("#cefrLevelSelect").value = profile.cefr_level || "A1-A2";
    if ($("#levelSelect")) $("#levelSelect").value = profile.cefr_level || "A1-A2";
    setGenderChoice(gender);
    setLifeRoleChoice(role);
    refreshProfilePreview();
  }

  async function loadStatus() {
    try {
      const data = await api("/api/language/status");
      $("#modeBadge").textContent = data.mode === "online-ai" ? "TRỰC TUYẾN" : "DEMO DỰ PHÒNG";
      updateQuota(data.quota);
      renderProfile(data.profile || {});
      if (!data.profile?.profile_ready) openProfileDialog(true);
    } catch (error) {
      $("#modeBadge").textContent = "CHƯA KẾT NỐI";
      showToast(error.message, true);
    }
  }

  async function loadOverview() {
    const lang = $("#languageSelect").value || "en";
    try {
      const data = await api(`/api/language/overview?language=${encodeURIComponent(lang)}`);
      latestOverview = data;
      updateQuota(data.quota);
      renderProfile(data.profile || {});
      renderGames(data.cards || []);
      renderVocabulary(data.vocabulary || {});
      renderSkills(data.skills || []);
      renderLeaderboard(data.leaderboard || {});
      renderLearning(data.learning || {});
      renderCurriculum(data.curriculum || null);
      if (!data.curriculum?.selection && data.curriculum?.available && data.profile?.profile_ready) openGoalDialog(true);
      if ($("#forYouPanel")?.classList.contains("active")) await loadExperienceFeed();
    } catch (error) {
      showToast(error.message, true);
    }
  }


  function experienceFormatLabel(format) {
    return { video: "MICRO VIDEO", chat: "CHAT", audio: "LISTEN", comic: "COMIC", reply: "QUICK REPLY" }[format] || "EXPERIENCE";
  }

  function experienceSettingLabel(setting) {
    return { bedroom: "Phòng ngủ", cafe: "Café", phone: "Tin nhắn", bus: "Xe buýt", office: "Công việc", elevator: "Thang máy", street: "Đời sống", metro: "MRT" }[setting] || "Đời sống";
  }

  async function loadExperienceFeed() {
    const root = $("#experienceFeed");
    if (!root) return;
    const lang = $("#languageSelect")?.value || "en";
    const level = $("#levelSelect")?.value || latestOverview?.profile?.cefr_level || "A1-A2";
    try {
      const data = await api(`/api/language/learning/feed?language=${encodeURIComponent(lang)}&level=${encodeURIComponent(level)}&limit=10`);
      experienceFeed = data.items || [];
      renderExperienceFeed();
    } catch (error) {
      root.innerHTML = `<div class="empty-recent">Chưa tải được For You: ${escapeHtml(error.message)}</div>`;
    }
  }

  function renderExperienceFeed() {
    const root = $("#experienceFeed");
    if (!root) return;
    root.innerHTML = "";
    if (!experienceFeed.length) {
      root.innerHTML = `<div class="empty-recent">Chưa có trải nghiệm cho trình độ này.</div>`;
      return;
    }
    experienceFeed.forEach((item, index) => root.appendChild(buildExperienceCard(item, index)));
  }

  function buildExperienceCard(item, index) {
    const card = document.createElement("article");
    card.className = `experience-card format-${escapeHtml(item.format || "video")}`;
    card.dataset.experienceId = item.id;
    const selected = new Set((item.selected_terms || []).map((x) => String(x).toLowerCase()));
    experienceSelectedTerms.set(item.id, selected);
    const wordButtons = (item.terms || []).map((term) => {
      const picked = selected.has(String(term.term || "").toLowerCase());
      return `<button class="experience-term ${picked ? "picked" : ""}" type="button" data-term="${escapeHtml(term.term)}">${escapeHtml(term.term)}</button>`;
    }).join("");
    card.innerHTML = `
      <header class="experience-card-head">
        <div><small>${experienceFormatLabel(item.format)} · ${escapeHtml(item.level || "")}</small><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.hook || "")}</p></div>
        <span>${Number(item.duration || 30)}s</span>
      </header>
      <div class="experience-stage" data-setting="${escapeHtml(item.setting || "street")}">
        <div class="experience-stage-top"><span>${experienceSettingLabel(item.setting)}</span><b>${String(index + 1).padStart(2, "0")}</b></div>
        <div class="experience-visual"><i></i><i></i><i></i></div>
        <div class="experience-subtitle"><small id="expSpeaker-${escapeHtml(item.id)}">BẤM PLAY</small><strong id="expLine-${escapeHtml(item.id)}">Xem/nghe tình huống trước. Chưa cần học từ nào.</strong></div>
        <div class="experience-progress"><i id="expProgress-${escapeHtml(item.id)}"></i></div>
      </div>
      <div class="experience-actions">
        <button class="exp-play primary" type="button">Play trải nghiệm</button>
        <button class="exp-listen" type="button">Nghe lại</button>
      </div>
      <section class="word-pick-zone">
        <div><small>SAU KHI TRẢI NGHIỆM</small><h4>Từ/cụm nào mày chưa biết?</h4><p>Chỉ chọn thứ mày thật sự chưa chắc. Không chọn cũng được.</p></div>
        <div class="experience-terms">${wordButtons}</div>
        <div class="word-pick-actions"><button class="exp-know-all" type="button">Tao biết hết</button><button class="exp-save-terms" type="button">Học từ đã chọn</button></div>
      </section>
      <div class="experience-wordlabs"></div>
    `;
    card.querySelector(".exp-play").addEventListener("click", () => playExperience(item, card));
    card.querySelector(".exp-listen").addEventListener("click", () => speakExperience(item));
    card.querySelectorAll(".experience-term").forEach((button) => {
      button.addEventListener("click", () => {
        const set = experienceSelectedTerms.get(item.id) || new Set();
        const key = String(button.dataset.term || "").toLowerCase();
        if (set.has(key)) set.delete(key); else set.add(key);
        experienceSelectedTerms.set(item.id, set);
        button.classList.toggle("picked", set.has(key));
      });
    });
    card.querySelector(".exp-know-all").addEventListener("click", () => {
      experienceSelectedTerms.set(item.id, new Set());
      card.querySelectorAll(".experience-term").forEach((button) => button.classList.remove("picked"));
      showToast("Ok. Không có từ mới thì bỏ qua, không cần học giả vờ.");
    });
    card.querySelector(".exp-save-terms").addEventListener("click", () => saveExperienceTerms(item, card));
    renderWordLabs(item, card);
    return card;
  }

  async function markExperienceView(item) {
    try {
      await api("/api/language/learning/experience/view", { method: "POST", body: JSON.stringify({ experience_id: item.id }) });
    } catch { /* non-blocking */ }
  }

  function clearExperienceTimer(id) {
    const timers = experienceTimers.get(id) || [];
    timers.forEach((timer) => clearTimeout(timer));
    experienceTimers.delete(id);
  }

  function playExperience(item, card) {
    clearExperienceTimer(item.id);
    markExperienceView(item);
    const lines = item.lines || [];
    if (!lines.length) return;
    const speaker = card.querySelector(`#expSpeaker-${CSS.escape(item.id)}`);
    const line = card.querySelector(`#expLine-${CSS.escape(item.id)}`);
    const progress = card.querySelector(`#expProgress-${CSS.escape(item.id)}`);
    const timers = [];
    lines.forEach((entry, idx) => {
      const timer = setTimeout(() => {
        speaker.textContent = entry.speaker || "";
        line.textContent = entry.text || "";
        progress.style.width = `${((idx + 1) / lines.length) * 100}%`;
        if (item.format === "audio" || item.format === "video") speakText(entry.text || "");
      }, idx * 2200);
      timers.push(timer);
    });
    const doneTimer = setTimeout(async () => {
      if (curriculumActivityContext?.type === "experience") {
        const context = curriculumActivityContext;
        curriculumActivityContext = null;
        await completeCurriculumActivity(context, 100);
      }
    }, Math.max(1200, lines.length * 2200));
    timers.push(doneTimer);
    experienceTimers.set(item.id, timers);
  }

  function speakExperience(item) {
    const text = (item.lines || []).map((x) => x.text || "").join(". ");
    speakText(text);
  }

  async function saveExperienceTerms(item, card) {
    const selected = experienceSelectedTerms.get(item.id) || new Set();
    const byKey = new Map((item.terms || []).map((term) => [String(term.term || "").toLowerCase(), term.term]));
    const terms = [...selected].map((key) => byKey.get(key)).filter(Boolean);
    if (!terms.length) {
      showToast("Chọn ít nhất một từ/cụm mày chưa biết.", true);
      return;
    }
    const button = card.querySelector(".exp-save-terms");
    button.disabled = true;
    button.textContent = "Đang mở Word Lab…";
    try {
      const data = await api("/api/language/learning/experience/select-words", {
        method: "POST", body: JSON.stringify({ experience_id: item.id, terms }),
      });
      const updated = data.experience || item;
      const idx = experienceFeed.findIndex((x) => x.id === item.id);
      if (idx >= 0) experienceFeed[idx] = updated;
      Object.assign(item, updated);
      renderProfile(data.profile || latestOverview?.profile || {});
      renderWordLabs(item, card);
      showToast(`Đã nhặt ${terms.length} từ/cụm vào WordDex.`);
      await loadOverviewAfterExperience();
    } catch (error) {
      showToast(error.message, true);
    } finally {
      button.disabled = false;
      button.textContent = "Học từ đã chọn";
    }
  }

  async function loadOverviewAfterExperience() {
    const lang = $("#languageSelect").value || "en";
    try {
      const data = await api(`/api/language/overview?language=${encodeURIComponent(lang)}`);
      latestOverview = data;
      renderProfile(data.profile || {});
      renderVocabulary(data.vocabulary || {});
      renderSkills(data.skills || []);
      renderLearning(data.learning || {});
      updateQuota(data.quota);
    } catch { /* keep current screen */ }
  }

  function renderWordLabs(item, card) {
    const root = card.querySelector(".experience-wordlabs");
    if (!root) return;
    const selectedKeys = new Set((item.selected_terms || []).map((x) => String(x).toLowerCase()));
    const terms = (item.terms || []).filter((term) => selectedKeys.has(String(term.term || "").toLowerCase()) && term.meaning);
    root.innerHTML = "";
    if (!terms.length) return;
    terms.forEach((term) => root.appendChild(buildWordLab(item, term)));
  }

  function buildWordLab(item, term) {
    const lab = document.createElement("section");
    lab.className = "word-lab";
    const contexts = term.contexts || [];
    lab.innerHTML = `
      <div class="word-lab-head"><div><small>WORD LAB</small><h4>${escapeHtml(term.term)}</h4><b>${escapeHtml(term.meaning || "")}</b></div><button class="word-hear" type="button">Nghe 3 context</button></div>
      <div class="word-contexts">${contexts.map((ctx, i) => `<article><span>0${i + 1}</span><div><strong>${escapeHtml(ctx.text || "")}</strong><small>${escapeHtml(ctx.translation || "")}</small></div></article>`).join("")}</div>
      <div class="word-mode-tabs">
        <button type="button" data-word-mode="listening">Nghe</button>
        <button type="button" data-word-mode="reading">Đọc</button>
        <button type="button" data-word-mode="speaking">Nói</button>
        <button type="button" data-word-mode="writing">Viết</button>
      </div>
      <div class="word-practice-area"><p>Chọn một mode để dùng lại từ này trong ngữ cảnh khác.</p></div>
    `;
    lab.querySelector(".word-hear").addEventListener("click", () => contexts.forEach((ctx, idx) => setTimeout(() => speakText(ctx.text || ""), idx * 2100)));
    lab.querySelectorAll("[data-word-mode]").forEach((btn) => btn.addEventListener("click", () => renderWordPractice(item, term, btn.dataset.wordMode, lab)));
    return lab;
  }

  function renderWordPractice(item, term, mode, lab) {
    const area = lab.querySelector(".word-practice-area");
    lab.querySelectorAll("[data-word-mode]").forEach((button) => button.classList.toggle("active", button.dataset.wordMode === mode));
    if (mode === "listening") {
      const contexts = term.contexts || [];
      area.innerHTML = `<div class="word-mode-task"><small>LISTENING</small><h5>Nghe lại mà đừng nhìn nghĩa.</h5><p>Bấm phát. Khi mày bắt được từ trong câu, ghi nhận lượt nghe này.</p><div class="word-task-actions"><button class="listen-context" type="button">Phát câu</button><button class="submit-word-practice" type="button">Tôi nghe ra rồi</button></div></div>`;
      area.querySelector(".listen-context").addEventListener("click", () => speakText((contexts[0] || {}).text || term.term));
      area.querySelector(".submit-word-practice").addEventListener("click", () => submitExperiencePractice(item, term, mode, "heard", area));
    } else if (mode === "reading") {
      const check = term.read_check || {};
      area.innerHTML = `<div class="word-mode-task"><small>READING</small><h5>${escapeHtml(check.prompt || "Hiểu từ này trong câu mới")}</h5><div class="word-read-options">${(check.options || []).map((opt) => `<button type="button" data-answer="${escapeHtml(opt)}">${escapeHtml(opt)}</button>`).join("")}</div></div>`;
      area.querySelectorAll("[data-answer]").forEach((button) => button.addEventListener("click", () => submitExperiencePractice(item, term, mode, button.dataset.answer || "", area)));
    } else if (mode === "speaking") {
      area.innerHTML = `<div class="word-mode-task"><small>SPEAKING</small><h5>${escapeHtml(term.speak_prompt || `Nói một câu với ${term.term}.`)}</h5><textarea class="word-practice-input" rows="3" placeholder="Bấm Nói hoặc nhập transcript…"></textarea><div class="word-task-actions"><button class="word-voice" type="button">Nói</button><button class="submit-word-practice" type="button">Chấm câu này</button></div></div>`;
      area.querySelector(".word-voice").addEventListener("click", () => startExperienceSpeech(area.querySelector(".word-practice-input")));
      area.querySelector(".submit-word-practice").addEventListener("click", () => submitExperiencePractice(item, term, mode, area.querySelector(".word-practice-input").value.trim(), area));
    } else {
      area.innerHTML = `<div class="word-mode-task"><small>WRITING</small><h5>${escapeHtml(term.write_prompt || `Viết một câu với ${term.term}.`)}</h5><textarea class="word-practice-input" rows="3" placeholder="Viết câu của mày…"></textarea><div class="word-task-actions"><button class="submit-word-practice" type="button">Chấm câu này</button></div></div>`;
      area.querySelector(".submit-word-practice").addEventListener("click", () => submitExperiencePractice(item, term, mode, area.querySelector(".word-practice-input").value.trim(), area));
    }
  }

  function startExperienceSpeech(input) {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      showToast("Trình duyệt này chưa hỗ trợ nhận dạng giọng nói.", true);
      return;
    }
    const recognition = new Recognition();
    recognition.lang = ($("#languageSelect").value || "en") === "zh" ? "zh-TW" : "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => { input.value = event.results?.[0]?.[0]?.transcript || ""; };
    recognition.onerror = () => showToast("Chưa nghe rõ. Thử nói lại.", true);
    recognition.start();
  }

  async function submitExperiencePractice(item, term, mode, answer, area) {
    if (!answer && mode !== "listening") {
      showToast("Làm thử trước rồi chấm.", true);
      return;
    }
    const buttons = area.querySelectorAll("button");
    buttons.forEach((button) => button.disabled = true);
    try {
      const data = await api("/api/language/learning/experience/practice", {
        method: "POST",
        body: JSON.stringify({ experience_id: item.id, term: term.term, mode, answer }),
      });
      const result = document.createElement("div");
      result.className = `word-practice-result ${Number(data.score || 0) >= 65 ? "good" : "retry"}`;
      result.innerHTML = `<b>${Number(data.score || 0)}/100 · +${Number(data.xp_earned || 0)} XP</b><p>${escapeHtml(data.feedback || "")}</p>${data.correction ? `<blockquote>${escapeHtml(data.correction)}</blockquote>` : ""}`;
      area.appendChild(result);
      renderProfile(data.profile || latestOverview?.profile || {});
      updateQuota(data.quota);
      await loadOverviewAfterExperience();
    } catch (error) {
      showToast(error.message, true);
    } finally {
      buttons.forEach((button) => button.disabled = false);
    }
  }

  function renderGames(cards) {
    gameCardsCache = Array.isArray(cards) ? cards : gameCardsCache;
    const source = gameCardsCache || [];
    const visible = activeGameFilter === "all" ? source : source.filter((item) => (item.difficulty_group || "fun") === activeGameFilter);
    const root = $("#gamesGrid");
    root.innerHTML = "";
    if (!visible.length) {
      root.innerHTML = `<div class="empty-recent">Chưa có game.</div>`;
      return;
    }
    visible.forEach((item) => {
      const card = document.createElement("article");
      card.dataset.gameGroup = item.difficulty_group || "fun";
      card.className = `game-card ${item.kind === "life" ? "game-life" : "game-arcade"} visual-${escapeHtml(item.visual || "chaos")} ${item.unlocked ? "" : "locked"}`;
      card.innerHTML = `
        <div class="game-card-top">
          <small>${escapeHtml(item.tag || "GAME")}</small>
          <span>${escapeHtml(item.duration || "")}</span>
        </div>
        <div class="game-difficulty"><b>${item.difficulty_group === "hardcore" ? "HARDCORE" : item.difficulty_group === "everyday" ? "ĐỜI SỐNG" : "VUI & LẠ"}</b><span>${escapeHtml(item.recommended_level || "A1-A2")}</span></div>
        <div class="game-card-art"><span></span><i></i><b></b></div>
        <h3>${escapeHtml(item.title || "Game")}</h3>
        <strong class="game-subtitle">${escapeHtml(item.subtitle || item.location || "")}</strong>
        <p>${escapeHtml(item.hook || "")}</p>
        <div class="game-meta">
          <span>${escapeHtml(item.progress_text || `${item.attempts || 0} lượt`)}</span>
          <span>${item.best_stars ? stars(item.best_stars) : (item.kind === "arcade" ? "☆☆☆" : "")}</span>
        </div>
        <button type="button" ${item.unlocked ? "" : "disabled"}>${item.unlocked ? (item.kind === "life" ? "Vào game" : (item.completed ? "Chơi lại" : "Bắt đầu")) : "Chưa mở"}</button>
      `;
      const btn = card.querySelector("button");
      if (item.unlocked && item.scene_id) {
        btn.addEventListener("click", () => start(item, "mission", "games"));
      }
      root.appendChild(card);
    });
  }

  function renderVocabulary(vocab) {
    $("#vocabDiscovered").textContent = Number(vocab.discovered || 0).toLocaleString("vi-VN");
    $("#vocabActive").textContent = Number(vocab.active || 0).toLocaleString("vi-VN");
    $("#vocabMastered").textContent = Number(vocab.mastered || 0).toLocaleString("vi-VN");
    $("#vocabEncounters").textContent = Number(vocab.total_encounters || 0).toLocaleString("vi-VN");

    const root = $("#vocabList");
    root.innerHTML = "";
    const terms = vocab.terms || [];
    if (!terms.length) {
      root.innerHTML = `<div class="empty-recent">Chơi vài lượt để hệ thống bắt đầu ghi nhận.</div>`;
      return;
    }
    terms.forEach((item) => {
      const row = document.createElement("article");
      row.className = "vocab-row";
      const importance = Number(item.importance_score || 0);
      const label = importance >= 80 ? "RẤT QUAN TRỌNG" : importance >= 60 ? "QUAN TRỌNG" : "ĐANG HỌC";
      row.innerHTML = `
        <div class="vocab-main">
          <div><strong>${escapeHtml(item.term)}</strong>${item.meaning ? `<small>${escapeHtml(item.meaning)}</small>` : ""}</div>
          <span class="importance ${importance >= 80 ? "critical" : ""}">${label}</span>
        </div>
        <div class="vocab-metrics">
          <span>Gặp <b>${Number(item.encounters || 0)}</b> lần</span>
          <span>Tự dùng <b>${Number(item.player_uses || 0)}</b></span>
          <span>Mastery <b>${Math.round(Number(item.mastery || 0))}%</b></span>
        </div>
        <div class="mastery-track"><i style="width:${Math.min(100, Number(item.mastery || 0))}%"></i></div>
      `;
      root.appendChild(row);
    });
  }

  function renderSkills(items) {
    const root = $("#skillList");
    root.innerHTML = "";
    if (!items.length) {
      root.innerHTML = `<div class="empty-recent">Chưa đủ dữ liệu.</div>`;
      return;
    }
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "skill-row";
      row.innerHTML = `
        <div><strong>${escapeHtml(formatSkill(item.skill))}</strong><small>${Number(item.attempts || 0)} lần thực hành</small></div>
        <b>${Math.round(Number(item.mastery || 0))}</b>
        <div class="skill-track"><i style="width:${Math.min(100, Number(item.mastery || 0))}%"></i></div>
      `;
      root.appendChild(row);
    });
  }

  function renderLeaderboard(data) {
    $("#myRank").textContent = data.my_rank ? `#${data.my_rank}` : "—";
    $("#rankWeek").textContent = data.week_start ? `Tuần từ ${data.week_start}` : "Tuần hiện tại";
    const root = $("#leaderboard");
    root.innerHTML = "";
    const items = data.items || [];
    if (!items.length) {
      root.innerHTML = `<div class="empty-recent">Chưa có dữ liệu.</div>`;
      return;
    }
    items.forEach((item, index) => {
      const row = document.createElement("div");
      row.className = `rank-row ${item.is_me ? "me" : ""}`;
      row.innerHTML = `<b class="rank-pos">#${index + 1}</b><strong>${escapeHtml(item.name)}</strong><span>${Number(item.weekly_xp || 0)} XP</span><small>streak ${Number(item.streak || 0)}</small>`;
      root.appendChild(row);
    });
  }



  function curriculumTrackById(id) {
    return (curriculumData?.tracks || []).find((track) => track.id === id) || null;
  }

  function currentCurriculumStage() {
    const road = curriculumData?.roadmap;
    if (!road) return null;
    return (road.stages || []).find((stage) => stage.id === road.current_stage_id) || null;
  }

  function renderCurriculum(data) {
    curriculumData = data || { tracks: [], selection: null, roadmap: null };
    const road = curriculumData.roadmap;
    const selection = curriculumData.selection;
    if (!road || !selection) {
      $("#currentTrackTitle").textContent = "Chọn mục tiêu học trước";
      $("#currentTrackOutcome").textContent = "Roadmap sẽ chia mục tiêu thành stage, unit và checkpoint lên level.";
      $("#currentTrackTarget").textContent = "—";
      $("#currentStageLabel").textContent = "Chưa bắt đầu";
      $("#currentStageControl").textContent = "—";
      $("#roadmapTrackTitle").textContent = "Chọn một mục tiêu để bắt đầu";
      $("#roadmapTrackDescription").textContent = "Mỗi stage chỉ mở sau khi vượt checkpoint của stage trước.";
      $("#roadmapProgressText").textContent = "0%";
      $("#roadmapProgressBar").style.width = "0%";
      $("#roadmapStages").innerHTML = `<div class="roadmap-empty"><b>Chưa có roadmap</b><p>Chọn Giao tiếp & Đời sống, Work English, IELTS hoặc TOEIC.</p><button type="button" id="emptyChooseTrackBtn">Chọn mục tiêu</button></div>`;
      $("#emptyChooseTrackBtn")?.addEventListener("click", () => openGoalDialog(false));
      return;
    }
    const stage = currentCurriculumStage();
    $("#currentTrackTitle").textContent = road.track_title || "Lộ trình";
    $("#currentTrackOutcome").textContent = stage?.outcome || "Tiếp tục roadmap hiện tại.";
    $("#currentTrackTarget").textContent = selection.target || "—";
    $("#currentStageLabel").textContent = stage ? `${stage.label} · ${stage.level}` : "Đã hoàn tất";
    $("#currentStageControl").textContent = stage ? `${stage.level} · ${stage.title}` : "Hoàn tất";
    $("#roadmapTrackTitle").textContent = road.track_title || "Lộ trình";
    const track = curriculumTrackById(selection.track_id);
    $("#roadmapTrackDescription").textContent = track?.description || "Hoàn thành từng unit rồi vượt checkpoint.";
    $("#roadmapProgressText").textContent = `${Number(road.activity_progress || 0)}%`;
    $("#roadmapProgressBar").style.width = `${Math.min(100, Number(road.activity_progress || 0))}%`;
    renderRoadmapStages(road.stages || []);
  }

  function renderRoadmapStages(stages) {
    const root = $("#roadmapStages");
    if (!root) return;
    root.innerHTML = "";
    stages.forEach((stage, stageIndex) => {
      const card = document.createElement("section");
      const current = curriculumData?.roadmap?.current_stage_id === stage.id;
      card.className = `roadmap-stage ${stage.unlocked ? "unlocked" : "locked"} ${stage.passed ? "passed" : ""} ${current ? "current" : ""} ${stage.is_target ? "target-stage" : ""}`;
      const unitsHtml = (stage.units || []).map((unit, unitIndex) => {
        const pct = unit.required_total ? Math.round(Number(unit.required_done || 0) / unit.required_total * 100) : 0;
        return `<article class="roadmap-unit ${unit.completed ? "completed" : ""} ${unit.unlocked ? "" : "locked"}">
          <div class="unit-number">${stageIndex + 1}.${unitIndex + 1}</div>
          <div class="unit-copy"><small>${unit.minutes || 15} PHÚT · ${unit.required_done || 0}/${unit.required_total || 0} BẮT BUỘC</small><h4>${escapeHtml(unit.title)}</h4><p>${escapeHtml(unit.outcome || "")}</p><div class="unit-mini-progress"><i style="width:${pct}%"></i></div></div>
          <button type="button" data-unit-id="${escapeHtml(unit.id)}" ${unit.unlocked ? "" : "disabled"}>${unit.completed ? "Xem lại" : unit.unlocked ? "Mở unit" : "Đang khóa"}</button>
        </article>`;
      }).join("");
      const cp = stage.checkpoint || {};
      card.innerHTML = `<header class="roadmap-stage-head"><div><small>${escapeHtml(stage.label || "STAGE")} · ${escapeHtml(stage.level || "")}</small><h3>${escapeHtml(stage.title || "")}</h3><p>${escapeHtml(stage.outcome || "")}</p></div><div class="stage-badges">${stage.is_target ? "<span>MỤC TIÊU</span>" : ""}${stage.passed ? "<b>ĐÃ VƯỢT</b>" : current ? "<b>ĐANG HỌC</b>" : !stage.unlocked ? "<b>KHÓA</b>" : ""}</div></header>
        <div class="roadmap-units">${unitsHtml}</div>
        <div class="checkpoint-card ${cp.passed ? "passed" : ""} ${cp.available ? "available" : "locked"}">
          <div><small>LEVEL GATE</small><h4>${escapeHtml(cp.title || "Checkpoint")}</h4><p>${cp.passed ? `Đã vượt · Best ${Number(cp.best_score || 0)}` : cp.stage_complete ? `Các unit đã xong · cần ${Number(cp.pass_score || 70)} điểm để lên stage tiếp` : "Hoàn thành toàn bộ unit bắt buộc để mở bài test."}</p></div>
          <button type="button" data-checkpoint-stage="${escapeHtml(stage.id)}" ${cp.available ? "" : "disabled"}>${cp.passed ? "Làm lại" : cp.available ? "Làm checkpoint" : "Chưa mở"}</button>
        </div>`;
      root.appendChild(card);
      card.querySelectorAll("[data-unit-id]").forEach((button) => button.addEventListener("click", () => openUnitDialog(stage.id, button.dataset.unitId)));
      card.querySelector("[data-checkpoint-stage]")?.addEventListener("click", () => openCheckpoint(stage.id));
    });
  }

  function openGoalDialog(force = false) {
    const dialog = $("#goalDialog");
    renderGoalTracks();
    dialog.dataset.force = force ? "1" : "0";
    if (!dialog.open) dialog.showModal();
  }

  function renderGoalTracks() {
    const root = $("#goalTrackGrid");
    root.innerHTML = "";
    const currentId = curriculumData?.selection?.track_id || "";
    (curriculumData?.tracks || []).forEach((track) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = `goal-track-card accent-${escapeHtml(track.accent || "green")} ${track.id === currentId ? "current" : ""} ${track.id === selectedGoalTrackId ? "selected" : ""}`;
      card.innerHTML = `<small>${escapeHtml(track.short_title || track.title)}</small><h3>${escapeHtml(track.title)}</h3><p>${escapeHtml(track.description || "")}</p><div>${(track.best_for || []).slice(0,3).map((x) => `<span>${escapeHtml(x)}</span>`).join("")}</div>`;
      card.addEventListener("click", () => chooseGoalTrack(track.id));
      root.appendChild(card);
    });
    if (!selectedGoalTrackId && currentId) chooseGoalTrack(currentId, false);
  }

  function chooseGoalTrack(trackId, rerender = true) {
    selectedGoalTrackId = trackId;
    const track = curriculumTrackById(trackId);
    if (!track) return;
    if (rerender) renderGoalTracks();
    $("#goalTargetSection").classList.remove("hidden");
    $("#goalSelectedTitle").textContent = track.title || "";
    $("#goalSelectedDescription").textContent = track.description || "";
    const select = $("#goalTargetSelect");
    select.innerHTML = (track.target_options || []).map((x) => `<option value="${escapeHtml(x.value)}">${escapeHtml(x.label)}</option>`).join("");
    const saved = curriculumData?.selection?.track_id === trackId ? curriculumData.selection.target : "";
    if (saved && [...select.options].some((o) => o.value === saved)) select.value = saved;
  }

  async function confirmGoalTrack() {
    if (!selectedGoalTrackId) {
      showToast("Chọn một lộ trình trước.", true);
      return;
    }
    const button = $("#confirmTrackBtn");
    button.disabled = true;
    button.textContent = "Đang tạo roadmap…";
    try {
      const data = await api("/api/language/curriculum/select", {
        method: "POST",
        body: JSON.stringify({ language: "en", track_id: selectedGoalTrackId, target: $("#goalTargetSelect").value }),
      });
      renderCurriculum(data.curriculum || null);
      if ($("#goalDialog").open) $("#goalDialog").close();
      switchLearningTab("roadmap");
      showToast("Đã tạo roadmap. Bắt đầu từ unit đầu tiên.");
      await loadOverview();
    } catch (error) {
      showToast(error.message, true);
    } finally {
      button.disabled = false;
      button.textContent = "Tạo roadmap";
    }
  }

  function findRoadmapUnit(unitId) {
    for (const stage of curriculumData?.roadmap?.stages || []) {
      const unit = (stage.units || []).find((item) => item.id === unitId);
      if (unit) return { stage, unit };
    }
    return null;
  }

  function openUnitDialog(stageId, unitId) {
    const found = findRoadmapUnit(unitId);
    if (!found || !found.unit.unlocked) return;
    activeUnitState = found;
    const { stage, unit } = found;
    $("#unitStageLabel").textContent = `${stage.label} · ${stage.level}`;
    $("#unitDialogTitle").textContent = unit.title || "Unit";
    $("#unitDialogOutcome").textContent = unit.outcome || "";
    $("#unitProgressText").textContent = `${unit.required_done || 0}/${unit.required_total || 0} hoạt động bắt buộc`;
    const pct = unit.required_total ? Math.round(unit.required_done / unit.required_total * 100) : 0;
    $("#unitProgressBar").style.width = `${pct}%`;
    const root = $("#unitActivities");
    root.innerHTML = "";
    (unit.activities || []).forEach((activity, index) => {
      const row = document.createElement("article");
      row.className = `unit-activity type-${escapeHtml(activity.type || "learn")} ${activity.completed ? "completed" : ""}`;
      row.innerHTML = `<div class="activity-index">${String(index + 1).padStart(2, "0")}</div><div><small>${activity.required === false ? "TỰ CHỌN" : "BẮT BUỘC"}</small><h4>${escapeHtml(activity.label || activity.type)}</h4><p>${escapeHtml(activity.description || "")}</p></div><button type="button" ${activity.completed ? "disabled" : ""}>${activity.completed ? "Đã xong" : "Bắt đầu"}</button>`;
      row.querySelector("button").addEventListener("click", () => startCurriculumActivity(unit, activity));
      root.appendChild(row);
    });
    $("#unitDialog").showModal();
  }

  async function completeCurriculumActivity(context, score = 100) {
    if (!context?.unit_id || !context?.activity_id) return;
    try {
      const data = await api("/api/language/curriculum/activity/complete", {
        method: "POST",
        body: JSON.stringify({ language: "en", unit_id: context.unit_id, activity_id: context.activity_id, score }),
      });
      renderCurriculum(data.curriculum || null);
      renderProfile(data.profile || latestOverview?.profile || {});
      showToast("Đã ghi nhận hoạt động trong roadmap.");
      if ($("#unitDialog").open) {
        const found = findRoadmapUnit(context.unit_id);
        if (found) openUnitDialog(found.stage.id, context.unit_id);
      }
    } catch (error) {
      showToast(error.message, true);
    }
  }

  function startCurriculumActivity(unit, activity) {
    curriculumActivityContext = { unit_id: unit.id, activity_id: activity.id, type: activity.type, module: activity.module || "" };
    if ($("#unitDialog").open) $("#unitDialog").close();
    if (activity.type === "experience") {
      switchLearningTab("foryou");
      loadExperienceFeed().then(() => {
        document.querySelector(".experience-card")?.scrollIntoView({ behavior: "smooth", block: "start" });
        showToast("Play một trải nghiệm. Xem hết là roadmap tự ghi nhận.");
      });
      return;
    }
    if (activity.type === "game") {
      switchLearningTab("stories");
      showToast("Hoàn thành một game/mô phỏng để cover hoạt động này.");
      return;
    }
    const module = activity.module || (activity.type === "review" ? "review" : activity.type);
    openLesson(module, activity.type === "review" ? "review" : "new");
  }

  async function completeGameCurriculumIfNeeded() {
    if (curriculumActivityContext?.type !== "game") return;
    const context = curriculumActivityContext;
    curriculumActivityContext = null;
    await completeCurriculumActivity(context, 100);
  }

  function openCheckpoint(stageId) {
    const stage = (curriculumData?.roadmap?.stages || []).find((x) => x.id === stageId);
    if (!stage?.checkpoint?.available) return;
    activeCheckpointStage = stage;
    const cp = stage.checkpoint;
    $("#checkpointTitle").textContent = cp.title || "Checkpoint";
    $("#checkpointDescription").textContent = cp.description || "";
    const hasSpeaking = (cp.questions || []).some((q) => q.type === "speaking");
    const hasWriting = (cp.questions || []).some((q) => q.type === "writing");
    const freeRule = hasSpeaking || hasWriting ? ` · ${hasSpeaking ? "Speaking" : ""}${hasSpeaking && hasWriting ? "/" : ""}${hasWriting ? "Writing" : ""} tối thiểu 50` : " · checkpoint L&R";
    $("#checkpointPassRule").textContent = `Cần ${Number(cp.pass_score || 70)} điểm${freeRule}`;
    const skills = [...new Set((cp.questions || []).map((q) => q.skill || q.type))].map((x) => String(x).replace("language", "Language use"));
    $("#checkpointSkillRule").textContent = skills.join(" + ");
    const form = $("#checkpointForm");
    form.innerHTML = "";
    (cp.questions || []).forEach((question, index) => form.appendChild(buildCheckpointQuestion(question, index)));
    $("#checkpointDialog").showModal();
  }

  function buildCheckpointQuestion(question, index) {
    const section = document.createElement("section");
    section.className = `checkpoint-question type-${escapeHtml(question.type || "mcq")}`;
    let body = "";
    if (["mcq", "listening", "reading"].includes(question.type)) {
      body = `<div class="checkpoint-options">${(question.options || []).map((option) => `<label><input type="radio" name="cp-${escapeHtml(question.id)}" value="${escapeHtml(option)}"><span>${escapeHtml(option)}</span></label>`).join("")}</div>`;
    } else {
      body = `<textarea id="cp-${escapeHtml(question.id)}" rows="${question.type === "writing" ? 6 : 4}" placeholder="${question.type === "speaking" ? "Bấm mic hoặc nhập transcript câu mày nói…" : "Viết câu trả lời…"}"></textarea>${question.type === "speaking" ? `<button class="checkpoint-mic" type="button" data-cp-mic="${escapeHtml(question.id)}">Dùng mic</button>` : ""}`;
    }
    section.innerHTML = `<header><small>${String(index + 1).padStart(2, "0")} · ${escapeHtml(String(question.skill || question.type).toUpperCase())}</small><h4>${escapeHtml(question.prompt || "")}</h4>${question.type === "listening" ? `<button class="checkpoint-audio" type="button" data-audio="${escapeHtml(question.audio_text || "")}">Nghe audio</button>` : ""}</header>${body}`;
    section.querySelector(".checkpoint-audio")?.addEventListener("click", (event) => speakText(event.currentTarget.dataset.audio || ""));
    section.querySelector(".checkpoint-mic")?.addEventListener("click", () => startCheckpointSpeech(question.id));
    return section;
  }

  function startCheckpointSpeech(questionId) {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      showToast("Trình duyệt chưa hỗ trợ speech recognition. Mày có thể tự nhập transcript.", true);
      return;
    }
    const target = document.getElementById(`cp-${questionId}`);
    const recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => { target.value = event.results?.[0]?.[0]?.transcript || ""; };
    recognition.onerror = () => showToast("Không nghe rõ. Thử lại hoặc nhập bằng bàn phím.", true);
    recognition.start();
  }

  function checkpointAnswers() {
    const result = {};
    for (const question of activeCheckpointStage?.checkpoint?.questions || []) {
      if (["mcq", "listening", "reading"].includes(question.type)) {
        result[question.id] = document.querySelector(`input[name="cp-${CSS.escape(question.id)}"]:checked`)?.value || "";
      } else {
        result[question.id] = document.getElementById(`cp-${question.id}`)?.value.trim() || "";
      }
    }
    return result;
  }

  async function submitCheckpoint() {
    if (!activeCheckpointStage) return;
    const answers = checkpointAnswers();
    const missing = (activeCheckpointStage.checkpoint.questions || []).find((q) => !String(answers[q.id] || "").trim());
    if (missing) {
      showToast("Làm đủ tất cả phần của checkpoint trước.", true);
      return;
    }
    const button = $("#submitCheckpointBtn");
    button.disabled = true;
    button.textContent = "Đang chấm level…";
    try {
      const data = await api("/api/language/curriculum/checkpoint", {
        method: "POST",
        body: JSON.stringify({ language: "en", stage_id: activeCheckpointStage.id, answers }),
      });
      renderCurriculum(data.curriculum || null);
      renderProfile(data.profile || latestOverview?.profile || {});
      updateQuota(data.quota);
      if (data.passed) {
        showToast(`Qua level · ${data.score}/100 · stage tiếp theo đã mở`);
        $("#checkpointDialog").close();
      } else {
        showToast(`Chưa qua · ${data.score}/100. ${data.feedback || "Ôn lại rồi thử tiếp."}`, true);
      }
      await loadOverview();
    } catch (error) {
      showToast(error.message, true);
    } finally {
      button.disabled = false;
      button.textContent = "Nộp bài & chấm level";
    }
  }

  function moduleLabel(module) {
    return {
      vocabulary: "Từ vựng", phrases: "Câu giao tiếp", grammar: "Ngữ pháp",
      listening: "Listening", speaking: "Speaking", reading: "Reading",
      writing: "Writing", pronunciation: "Phát âm", review: "Ôn tập",
    }[module] || module;
  }

  function renderLearning(learning = {}) {
    const dashboard = learning.dashboard || {};
    const progress = learning.progress || {};
    if ($("#todayProgress")) $("#todayProgress").textContent = `${Number(dashboard.today_progress || 0)}%`;
    if ($("#todayPlanMeta")) $("#todayPlanMeta").textContent = `${Number(dashboard.attempts_today || 0)}/${Number(dashboard.target_steps || 0)} hoạt động`;
    renderTodayPlan(dashboard.plan || []);
    renderReviewModules(dashboard.module_counts || {});
    renderLearningProgress(progress);

    const attempted = (progress.modules || []).filter((item) => Number(item.attempts || 0) > 0);
    const weak = attempted.sort((a, b) => Number(a.mastery || 0) - Number(b.mastery || 0))[0];
    if ($("#weakestSkill")) $("#weakestSkill").textContent = weak ? `${weak.label} · ${Math.round(Number(weak.mastery || 0))}%` : "Chưa đủ dữ liệu";
    if ($("#weakestSkillText")) $("#weakestSkillText").textContent = weak ? `Hệ thống sẽ ưu tiên thêm ${weak.label.toLowerCase()} trong các lượt tới.` : "Học vài lượt để hệ thống cá nhân hóa.";
  }

  function renderTodayPlan(plan) {
    const root = $("#todayPlan");
    if (!root) return;
    root.innerHTML = "";
    plan.forEach((item, index) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "today-task";
      card.innerHTML = `<span class="today-task-index">${String(index + 1).padStart(2, "0")}</span><div><small>${Number(item.minutes || 3)} PHÚT</small><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.subtitle || "")}</p></div><b>→</b>`;
      card.addEventListener("click", () => {
        if (item.module === "games") switchLearningTab("games");
        else if (item.module === "review") openLesson("review", "review");
        else openLesson(item.module, item.action || "new");
      });
      root.appendChild(card);
    });
  }

  function renderReviewModules(counts) {
    const root = $("#reviewModules");
    if (!root) return;
    const order = ["phrases", "grammar", "listening", "reading", "pronunciation"];
    root.innerHTML = "";
    order.forEach((module) => {
      const data = counts[module] || { due: 0, seen: 0, mastered: 0 };
      const row = document.createElement("button");
      row.type = "button";
      row.className = "review-row";
      row.innerHTML = `<div><strong>${moduleLabel(module)}</strong><span>${Number(data.due || 0)} đến hạn · ${Number(data.mastered || 0)} mastered</span></div><b>${Number(data.due || 0) ? "Ôn →" : "Xem →"}</b>`;
      row.addEventListener("click", () => openLesson(module, "review"));
      root.appendChild(row);
    });
  }

  function renderLearningProgress(progress) {
    if ($("#learningCoverage")) $("#learningCoverage").textContent = `${Number(progress.coverage || 0)}%`;
    if ($("#learningSeenTotal")) $("#learningSeenTotal").textContent = `${Number(progress.seen_total || 0)} mục`;
    if ($("#learningMasteredTotal")) $("#learningMasteredTotal").textContent = Number(progress.mastered_total || 0);
    const root = $("#learningModuleProgress");
    if (!root) return;
    root.innerHTML = "";
    (progress.modules || []).forEach((item) => {
      const row = document.createElement("div");
      row.className = "learning-progress-row";
      row.innerHTML = `<div><strong>${escapeHtml(item.label)}</strong><span>${Number(item.attempts || 0)} lượt · ${Number(item.due || 0)} cần ôn</span></div><b>${Math.round(Number(item.mastery || 0))}%</b><div class="learning-progress-track"><i style="width:${Math.min(100, Number(item.mastery || 0))}%"></i></div>`;
      root.appendChild(row);
    });
  }

  function switchLearningTab(name) {
    const alias = { today: "roadmap", learn: "roadmap", skills: "train", games: "stories", review: "train" };
    name = alias[name] || name;
    $$(".learning-tab").forEach((button) => button.classList.toggle("active", button.dataset.learningTab === name));
    $$(".learning-panel").forEach((panel) => panel.classList.remove("active"));
    const map = { roadmap: "#roadmapPanel", foryou: "#forYouPanel", stories: "#storiesPanel", train: "#trainPanel", progress: "#progressPanel" };
    const target = $(map[name] || "#roadmapPanel");
    if (target) target.classList.add("active");
    returnTab = name === "stories" ? "games" : name;
    if (name === "foryou") loadExperienceFeed();
  }

  function currentLessonItem() {
    return lessonItems[lessonIndex] || null;
  }

  function speakText(text) {
    if (!text || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = ($("#languageSelect").value || "en") === "zh" ? "zh-TW" : "en-US";
    utter.rate = 0.9;
    window.speechSynthesis.speak(utter);
  }

  function startSpeechRecognition() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      showToast("Trình duyệt này chưa hỗ trợ nhận giọng nói. Mày có thể nhập câu bằng bàn phím.", true);
      return;
    }
    if (speechRecognition) try { speechRecognition.abort(); } catch {}
    const recognition = new Recognition();
    speechRecognition = recognition;
    recognition.lang = ($("#languageSelect").value || "en") === "zh" ? "zh-TW" : "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    $("#lessonVoiceBtn").textContent = "Đang nghe…";
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript || "";
      const input = $("#lessonFreeAnswer");
      if (input) input.value = transcript;
    };
    recognition.onerror = () => showToast("Không nghe rõ. Thử nói lại hoặc nhập bằng bàn phím.", true);
    recognition.onend = () => { $("#lessonVoiceBtn").textContent = "Nói thử"; speechRecognition = null; };
    recognition.start();
  }

  async function openLesson(module, mode = "new") {
    const lang = $("#languageSelect").value || "en";
    const level = $("#levelSelect").value || "A1-A2";
    try {
      const curriculumLimit = curriculumActivityContext ? 4 : 10;
      const data = await api(`/api/language/learning/items?language=${encodeURIComponent(lang)}&level=${encodeURIComponent(level)}&module=${encodeURIComponent(module)}&mode=${encodeURIComponent(mode)}&limit=${curriculumLimit}`);
      lessonItems = data.items || [];
      lessonIndex = 0;
      lessonModule = module;
      lessonMode = mode;
      if (!lessonItems.length) {
        showToast(mode === "review" ? "Hiện chưa có mục nào đến hạn ôn trong phần này." : "Chưa có nội dung phù hợp ở trình độ này.");
        return;
      }
      $("#lessonDialog").showModal();
      renderLessonItem();
    } catch (error) {
      showToast(error.message, true);
    }
  }

  function lessonChoiceMarkup(options = []) {
    return `<div class="lesson-options">${options.map((option, index) => `<label><input type="radio" name="lessonChoice" value="${escapeHtml(option)}"><span><i>${String.fromCharCode(65 + index)}</i>${escapeHtml(option)}</span></label>`).join("")}</div>`;
  }

  function renderLessonItem() {
    const item = currentLessonItem();
    if (!item) return;
    lessonAnswerLocked = false;
    const module = item.module || lessonModule;
    $("#lessonModuleLabel").textContent = `${moduleLabel(module).toUpperCase()} · ${item.level || ""}`;
    $("#lessonTitle").textContent = item.title || item.term || item.phrase || "Bài luyện";
    $("#lessonSubline").textContent = `${lessonIndex + 1} / ${lessonItems.length} · Mastery ${Math.round(Number(item.mastery || 0))}%`;
    $("#lessonProgressBar").style.width = `${((lessonIndex + 1) / lessonItems.length) * 100}%`;
    $("#lessonFeedback").classList.add("hidden");
    $("#lessonFeedback").innerHTML = "";
    $("#lessonSubmitBtn").classList.remove("hidden");
    $("#lessonNextBtn").classList.add("hidden");
    $("#lessonSubmitBtn").disabled = false;
    $("#lessonAudioBtn").classList.add("hidden");
    $("#lessonVoiceBtn").classList.add("hidden");

    let html = "";
    if (module === "vocabulary") {
      html = `<div class="lesson-kicker">ĐOÁN TỪ TỪ NGỮ CẢNH</div><div class="context-first-card"><small>ĐỪNG XEM NGHĨA TRƯỚC</small><p>${escapeHtml(item.example || "")}</p></div><div class="lesson-question"><h3>${escapeHtml(item.question || `Theo ngữ cảnh, “${item.term}” có nghĩa gì?`)}</h3>${lessonChoiceMarkup(item.options || [])}</div>`;
      $("#lessonAudioBtn").classList.remove("hidden");
    } else if (module === "phrases") {
      html = `<div class="lesson-kicker">CHỌN CÂU CHO TÌNH HUỐNG</div><div class="context-first-card"><small>TÌNH HUỐNG</small><p>${escapeHtml(item.use || "")}</p></div><div class="lesson-question"><h3>${escapeHtml(item.question || "Mày sẽ nói câu nào?")}</h3>${lessonChoiceMarkup(item.options || [])}</div>`;
      $("#lessonAudioBtn").classList.remove("hidden");
    } else if (module === "grammar") {
      html = `<div class="lesson-kicker">GRAMMAR IN CONTEXT</div><div class="context-first-card"><small>DÙNG TRƯỚC · GIẢI THÍCH SAU</small><p>${escapeHtml(item.example || "")}</p></div><div class="lesson-question"><h3>${escapeHtml(item.question || "Chọn câu tự nhiên nhất")}</h3>${lessonChoiceMarkup(item.options || [])}</div>`;
    } else if (module === "listening") {
      html = `<div class="lesson-kicker">NGHE MÀ KHÔNG NHÌN SCRIPT</div><div class="listening-card"><button id="inlineAudioBtn" type="button">Phát đoạn nghe</button><p>Nghe 1–2 lần rồi trả lời.</p></div><div class="lesson-question"><h3>${escapeHtml(item.question)}</h3>${lessonChoiceMarkup(item.options || [])}</div>`;
      $("#lessonAudioBtn").classList.remove("hidden");
    } else if (module === "reading") {
      html = `<div class="lesson-kicker">READING ĐỜI THẬT</div><article class="reading-passage">${escapeHtml(item.passage || "")}</article><div class="lesson-question"><h3>${escapeHtml(item.question)}</h3>${lessonChoiceMarkup(item.options || [])}</div>`;
    } else if (module === "writing") {
      html = `<div class="lesson-kicker">VIẾT ĐỂ GIAO TIẾP</div><div class="free-task"><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.prompt || "")}</p><div class="focus-chips">${(item.focus || []).map((x) => `<span>${escapeHtml(x)}</span>`).join("")}</div><textarea id="lessonFreeAnswer" rows="7" placeholder="Viết câu trả lời của mày…"></textarea></div>`;
    } else if (module === "speaking") {
      html = `<div class="lesson-kicker">SPEAKING</div><div class="free-task"><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.prompt || "")}</p><div class="focus-chips">${(item.focus || []).map((x) => `<span>${escapeHtml(x)}</span>`).join("")}</div><textarea id="lessonFreeAnswer" rows="5" placeholder="Bấm Nói thử hoặc nhập lại điều mày vừa nói…"></textarea></div>`;
      $("#lessonVoiceBtn").classList.remove("hidden");
    } else if (module === "pronunciation") {
      html = `<div class="lesson-kicker">PHÁT ÂM</div><div class="pronunciation-target"><strong>${escapeHtml(item.target || item.title)}</strong>${item.contrast ? `<span>so với ${escapeHtml(item.contrast)}</span>` : ""}<p>${escapeHtml(item.tip || "")}</p><code>${escapeHtml(item.example || "")}</code></div><textarea id="lessonFreeAnswer" rows="3" placeholder="Bấm Nói thử; transcript sẽ hiện ở đây."></textarea>`;
      $("#lessonAudioBtn").classList.remove("hidden");
      $("#lessonVoiceBtn").classList.remove("hidden");
    }
    $("#lessonBody").innerHTML = html;
    $("#inlineAudioBtn")?.addEventListener("click", () => speakLessonItem());
  }

  function speakLessonItem() {
    const item = currentLessonItem();
    if (!item) return;
    const module = item.module || lessonModule;
    const text = module === "listening" ? item.audio_text : module === "vocabulary" ? `${item.term}. ${item.example || ""}` : module === "phrases" ? item.phrase : module === "pronunciation" ? `${item.target}. ${item.example || ""}` : item.model || "";
    speakText(text);
  }

  function lessonAnswer() {
    const free = $("#lessonFreeAnswer");
    if (free) return String(free.value || "").trim();
    return String(document.querySelector('input[name="lessonChoice"]:checked')?.value || "").trim();
  }

  async function submitLesson() {
    if (lessonAnswerLocked) return;
    const item = currentLessonItem();
    if (!item) return;
    const answer = lessonAnswer();
    if (!answer) {
      showToast("Trả lời trước đã.", true);
      return;
    }
    lessonAnswerLocked = true;
    $("#lessonSubmitBtn").disabled = true;
    $("#lessonSubmitBtn").textContent = "Đang chấm…";
    try {
      const data = await api("/api/language/learning/submit", { method: "POST", body: JSON.stringify({ item_id: item.id, answer }) });
      const good = Number(data.score || 0) >= 65;
      $("#lessonFeedback").classList.remove("hidden");
      $("#lessonFeedback").classList.toggle("good", good);
      const reveal = module === "vocabulary" ? `<div class="lesson-reveal"><strong>${escapeHtml(item.term || "")}</strong><span>${escapeHtml(item.meaning || "")}</span>${item.translation ? `<small>${escapeHtml(item.translation)}</small>` : ""}</div>` : module === "phrases" ? `<div class="lesson-reveal"><strong>${escapeHtml(item.phrase || "")}</strong><span>${escapeHtml(item.meaning || "")}</span></div>` : module === "grammar" ? `<div class="lesson-reveal"><strong>Vì sao?</strong><span>${escapeHtml(item.rule || "")}</span></div>` : "";
      $("#lessonFeedback").innerHTML = `<div><small>${good ? "ỔN" : "CẦN ÔN LẠI"}</small><b>${Number(data.score || 0)}/100 · +${Number(data.xp_earned || 0)} XP</b></div><p>${escapeHtml(data.feedback || "")}</p>${data.correction ? `<blockquote>${escapeHtml(data.correction)}</blockquote>` : ""}${reveal}<span>Mastery ${Math.round(Number(data.mastery || 0))}% · ôn lại ${escapeHtml(data.due_date || "")}</span>`;
      $("#lessonSubmitBtn").classList.add("hidden");
      $("#lessonNextBtn").classList.remove("hidden");
      updateQuota(data.quota);
      renderProfile(data.profile || {});
      if (data.learning) renderLearning(data.learning);
      await loadOverview();
    } catch (error) {
      lessonAnswerLocked = false;
      $("#lessonSubmitBtn").disabled = false;
      showToast(error.message, true);
    } finally {
      $("#lessonSubmitBtn").textContent = "Kiểm tra";
    }
  }

  async function nextLesson() {
    lessonIndex += 1;
    if (lessonIndex >= lessonItems.length) {
      $("#lessonDialog").close();
      const context = curriculumActivityContext;
      curriculumActivityContext = null;
      if (context && !["experience", "game"].includes(context.type)) {
        await completeCurriculumActivity(context, 100);
      } else {
        showToast("Xong lượt học. Tiến độ đã được lưu.");
      }
      await loadOverview();
      return;
    }
    renderLessonItem();
  }

  function stats(score, progress, communication = null) {
    $("#scoreText").textContent = String(score);
    $("#progressBar").style.width = `${Math.max(0, Math.min(100, Number(progress || 0)))}%`;
    $("#communicationText").textContent = communication == null ? "—" : String(communication);
  }

  function renderTurnScores(data) {
    const hasData = [data.task_success, data.communication, data.language_quality, data.independence].some((x) => x !== undefined && x !== null);
    $("#turnScores").classList.toggle("hidden", !hasData);
    if (!hasData) return;
    $("#taskScore").textContent = data.task_success ?? "—";
    $("#commScore").textContent = data.communication ?? "—";
    $("#langScore").textContent = data.language_quality ?? "—";
    $("#indScore").textContent = data.independence ?? "—";
  }

  function setMood(name) {
    $("#moodLabel").textContent = {
      happy: "ỔN ÁP",
      confused: "ĐANG XỬ LÝ",
      shocked: "LỆCH NHỊP",
    }[name] || "KHÓ ĐOÁN";
    $("#npcActor").dataset.face = name === "shocked" ? "cute" : name === "confused" ? "cool" : $("#npcActor").dataset.face || "calm";
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
    input.value = text;
    input.focus();
    count();
  }

  function effect(name) {
    const layer = $("#effectLayer");
    layer.innerHTML = "";
    if (name === "boom") {
      const node = document.createElement("div");
      node.className = "boom";
      node.textContent = "!?";
      layer.appendChild(node);
      $("#stage").classList.add("wiggle");
      setTimeout(() => $("#stage").classList.remove("wiggle"), 500);
    } else if (name === "spark") {
      for (let index = 0; index < 16; index += 1) {
        const node = document.createElement("i");
        node.className = "confetti";
        node.style.left = `${Math.random() * 100}%`;
        node.style.top = `${-20 - Math.random() * 100}px`;
        layer.appendChild(node);
      }
    } else {
      $("#playerActor").classList.add("wiggle");
      setTimeout(() => $("#playerActor").classList.remove("wiggle"), 500);
    }
    setTimeout(() => { layer.innerHTML = ""; }, 1100);
  }

  function showFeedback(item = {}) {
    suggestion = String(item.suggestion || "").trim();
    if (!suggestion) {
      $("#feedbackBox").classList.add("hidden");
      return;
    }
    $("#useSuggestionBtn").textContent = `Cách tự nhiên hơn: “${suggestion}”`;
    $("#useSuggestionBtn").disabled = false;
    $("#feedbackBox").classList.remove("hidden");
  }

  function dictionarySourceUrl(term) {
    const query = encodeURIComponent(String(term || "").trim());
    const lang = $("#languageSelect").value || "en";
    if (!query) return "";
    if (lang === "zh") {
      return `https://www.mdbg.net/chinese/dictionary?page=worddict&wdrst=0&wdqb=${query}`;
    }
    return `https://dictionary.cambridge.org/dictionary/english/${query}`;
  }

  function appendDictionaryMessage(role, text, term = "") {
    const log = $("#dictionaryChatLog");
    const node = document.createElement("div");
    node.className = `dict-message ${role}`;
    const body = document.createElement("div");
    body.className = "dict-message-text";
    body.textContent = String(text || "");
    node.appendChild(body);
    if (role === "bot" && term) {
      const actions = document.createElement("div");
      actions.className = "dict-message-actions";
      const save = document.createElement("button");
      save.type = "button";
      save.textContent = "+ Thêm vào từ của tao";
      save.addEventListener("click", async () => {
        try {
          await api("/api/language/learning/save-term", { method: "POST", body: JSON.stringify({ term, language: $("#languageSelect").value || "en" }) });
          save.textContent = "Đã lưu";
          save.disabled = true;
          await loadOverview();
        } catch (error) { showToast(error.message, true); }
      });
      const link = document.createElement("a");
      link.className = "dict-source-link";
      link.href = dictionarySourceUrl(term);
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = ($("#languageSelect").value || "en") === "zh" ? "Mở MDBG" : "Mở Cambridge";
      actions.append(save, link);
      node.appendChild(actions);
    }
    log.appendChild(node);
    log.scrollTop = log.scrollHeight;
  }

  function setDictionaryOpen(open) {
    $("#dictionaryPopup").classList.toggle("hidden", !open);
    $("#dictionaryFab").classList.toggle("active", open);
    if (open) {
      setTimeout(() => $("#dictionaryChatInput")?.focus(), 30);
    }
  }

  async function lookupDictionary() {
    const input = $("#dictionaryChatInput");
    const term = String(input.value || "").trim();
    if (!term) return;
    appendDictionaryMessage("user", term);
    input.value = "";
    input.disabled = true;
    $("#dictionaryChatSend").disabled = true;
    $("#dictionaryTyping").classList.remove("hidden");
    try {
      const data = await api("/api/language/dictionary", {
        method: "POST",
        body: JSON.stringify({
          term,
          language: $("#languageSelect").value || "en",
        }),
      });
      appendDictionaryMessage("bot", data.answer || "Chưa tra được từ này.", term);
    } catch (error) {
      appendDictionaryMessage("bot", `Chưa tra được từ này: ${error.message}`, term);
    } finally {
      $("#dictionaryTyping").classList.add("hidden");
      input.disabled = false;
      $("#dictionaryChatSend").disabled = false;
      input.focus();
    }
  }

  function buildTutorialSteps(briefing = {}) {
    const objectives = Array.isArray(briefing.objectives) ? briefing.objectives : [];
    const terms = Array.isArray(briefing.useful_terms) ? briefing.useful_terms : [];
    const questionIdeas = Array.isArray(briefing.question_ideas) ? briefing.question_ideas : [];
    const who = [
      `Mày: ${briefing.player_role || "người chơi trong tình huống này"}`,
      `${briefing.npc_name || "NPC"}: ${briefing.npc_role || "người đang nói chuyện với mày"}`,
    ].join("\n\n");
    const objectiveText = objectives.length
      ? objectives.map((item, index) => `${index + 1}. ${item}`).join("\n")
      : (briefing.goal || "Hoàn thành mục tiêu của tình huống.");
    const startParts = [];
    if (briefing.first_clue) startParts.push(`Tin nhắn đầu tiên: “${briefing.first_clue}”`);
    if (terms.length) startParts.push(`Từ/cụm có thể hữu ích: ${terms.join(", ")}`);
    if (questionIdeas.length) startParts.push(`Có thể bắt đầu hỏi:
${questionIdeas.map((item) => `• ${item}`).join("\n")}`);
    const rule = briefing.requires_final_answer
      ? `LUẬT CHƠI: Chat chỉ để hỏi và lấy manh mối. Khi nghĩ ra ${briefing.target_label || "đáp án cuối"}, nhập nó vào ô ĐÁP ÁN CUỐI bên dưới. Không cần chờ NPC hỏi đáp án.`
      : (briefing.pass_rule || "Hoàn thành mục tiêu bằng cách giao tiếp tự nhiên.");
    const why = briefing.motivation
      ? briefing.motivation
      : "Mục tiêu này gắn trực tiếp với tình huống của nhân vật; hoàn thành nó để câu chuyện tiếp tục.";
    return [
      { title: `Chuyện gì đang xảy ra? — ${briefing.title || "Tình huống"}`, body: briefing.situation || briefing.goal || "Đọc tình huống và tìm cách xử lý." },
      { title: "Ai là ai?", body: who },
      { title: "Tại sao mày phải quan tâm?", body: why },
      { title: "Mục tiêu cuối cùng", body: `${briefing.goal || "Hoàn thành tình huống."}\n\n${objectiveText}` },
      { title: "Hỏi thế nào để lấy dữ kiện?", body: startParts.join("\n\n") || "Hãy hỏi trực tiếp về người, đồ vật, địa điểm hoặc chi tiết liên quan. Câu hỏi đúng trọng tâm sẽ mở manh mối." },
      { title: "Cách qua màn", body: rule },
    ];
  }

  function updateTutorialStep() {
    const step = tutorialSteps[tutorialIndex] || tutorialSteps[0] || { title: "Hướng dẫn", body: "Đọc mục tiêu rồi bắt đầu." };
    $("#tutorialStepIndex").textContent = `BƯỚC ${tutorialIndex + 1} / ${tutorialSteps.length}`;
    $("#tutorialStepTitle").textContent = step.title;
    $("#tutorialStepBody").textContent = step.body;
    $("#tutorialPrevBtn").disabled = tutorialIndex === 0;
    $("#tutorialNextBtn").classList.toggle("hidden", tutorialIndex >= tutorialSteps.length - 1);
    $("#tutorialStartBtn").classList.toggle("hidden", tutorialIndex < tutorialSteps.length - 1);
  }

  function openTutorial(briefing = {}) {
    tutorialSteps = buildTutorialSteps(briefing);
    tutorialIndex = 0;
    updateTutorialStep();
    $("#tutorialDialog").showModal();
  }

  async function startCore(sceneId, mode = "mission", sourceTab = "games") {
    const data = await api("/api/language/start", {
      method: "POST",
      body: JSON.stringify({
        scene_id: sceneId,
        level: $("#levelSelect").value,
        humor: $("#humorSelect").value,
        mode,
      }),
    });
    returnTab = sourceTab;
    openGame(data.scene, { ...data, id: data.session_id }, [{ role: "npc", text: data.opening }]);
    renderProfile(data.profile || {});
    await loadOverview();
  }

  function renderChallenge(challenge = {}) {
    currentChallenge = challenge && challenge.required ? challenge : { required: false };
    const box = $("#finalAnswerBox");
    box.classList.toggle("hidden", !currentChallenge.required);
    if (!currentChallenge.required) return;
    $("#finalAnswerLabel").textContent = `Tìm ${currentChallenge.label || "đáp án cuối"}`;
    $("#finalAnswerInput").placeholder = currentChallenge.placeholder || "Nhập đáp án";
    $("#clueCount").textContent = `${Number(currentChallenge.clues_revealed || 0)}/${Number(currentChallenge.clue_total || 0)} manh mối`;
    const root = $("#revealedClues");
    root.innerHTML = "";
    const clues = Array.isArray(currentChallenge.revealed_clues) ? currentChallenge.revealed_clues : [];
    if (!clues.length) {
      root.innerHTML = `<div class="no-clue-yet">Chưa có manh mối. Hãy hỏi NPC đúng trọng tâm.</div>`;
    } else {
      clues.forEach((clue, index) => {
        const item = document.createElement("div");
        item.className = "revealed-clue";
        item.innerHTML = `<b>${index + 1}</b><span>${escapeHtml(clue)}</span>`;
        root.appendChild(item);
      });
    }
  }

  async function submitFinalAnswer(event) {
    event.preventDefault();
    if (!sessionId || !currentChallenge.required) return;
    const input = $("#finalAnswerInput");
    const answer = String(input.value || "").trim();
    if (!answer) {
      showToast("Nhập đáp án trước đã.", true);
      return;
    }
    $("#finalAnswerSubmit").disabled = true;
    $("#finalAnswerMessage").textContent = "Đang kiểm tra đáp án…";
    try {
      const data = await api("/api/language/answer", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, answer }),
      });
      if (!data.correct) {
        $("#finalAnswerMessage").textContent = data.message || "Chưa đúng. Hỏi thêm manh mối rồi thử lại.";
        renderChallenge(data.challenge || currentChallenge);
        input.select();
        return;
      }
      $("#finalAnswerMessage").textContent = `Đúng. +${Number(data.xp_earned || 0)} XP`;
      renderProfile(data.profile || {});
      stats(data.score || 100, 100, null);
      setCompleted(true, Number(data.stars || 1));
      showToast(`Đúng đáp án · +${Number(data.xp_earned || 0)} XP`);
      await completeGameCurriculumIfNeeded();
      await loadOverview();
    } catch (error) {
      $("#finalAnswerMessage").textContent = error.message;
      showToast(error.message, true);
    } finally {
      $("#finalAnswerSubmit").disabled = false;
    }
  }

  function renderObjectives(scene, completed = []) {
    objectiveState = Array.isArray(completed) ? completed : [];
    const objectives = currentMode === "free_roam" ? [] : (scene.objectives || []);
    const root = $("#objectiveList");
    root.innerHTML = "";
    objectives.forEach((objective) => {
      const done = objectiveState.includes(objective);
      const item = document.createElement("div");
      item.className = `objective ${done ? "done" : ""}`;
      item.innerHTML = `<span>${done ? "✓" : ""}</span><p>${escapeHtml(objective)}</p>`;
      root.appendChild(item);
    });
  }

  function setCompleted(completed, starCount = 0) {
    $("#replyInput").disabled = completed;
    $("#sendBtn").disabled = completed;
    $("#sendBtn").textContent = completed ? "Đã xong" : "Gửi";
    $("#completionBox").classList.toggle("hidden", !completed);
    $("#starResult").textContent = stars(starCount || 1);
  }

  function renderArcadeOverlay(scene) {
    const overlay = $("#arcadeOverlay");
    const visual = scene.visual || "";
    overlay.classList.toggle("hidden", !(scene.game_group === "arcade"));
    if (scene.game_group !== "arcade") {
      overlay.innerHTML = "";
      return;
    }
    const blocks = {
      phone: `<div class="phone-shell"><small>INCOMING CHAT</small><strong>UNKNOWN NUMBER</strong><div class="phone-lines"><i></i><i></i><i></i></div><b>?</b></div>`,
      sales: `<div class="product-stage"><small>RIDICULOUS PRODUCT</small><div class="spoon-shape"></div><strong>SELL THIS</strong><span>Convince the buyer</span></div>`,
      grandma: `<div class="grandma-stage"><small>DON'T MAKE HER MAD</small><div class="cone-shape"></div><strong>EXPLAIN THIS</strong><span>Keep it calm</span></div>`,
      taboo: `<div class="taboo-stage"><small>TABOO</small><strong>SECRET WORD</strong><div><span>NO EASY WORD #1</span><span>NO EASY WORD #2</span><span>NO EASY WORD #3</span></div></div>`,
      detective: `<div class="detective-board"><small>CASE BOARD</small><div class="suspects"><span>A</span><span>B</span><span>C</span></div><strong>ONE STORY DOESN'T MATCH</strong></div>`,
      alien: `<div class="alien-scan"><small>CUSTOMS SCAN</small><div class="scan-bag"></div><strong>DECLARE YOUR BAG</strong><span>Explain the weird noise</span></div>`,
      excuse: `<div class="late-clock"><small>LATE BY</small><strong>04:00</strong><span>Explain yourself</span></div>`,
      date: `<div class="date-stage"><small>DATE STATUS</small><strong>AWKWARD EVENT</strong><div class="drama-meter"><i></i></div><span>Keep it alive</span></div>`,
      roast: `<div class="versus-stage"><span>YOU</span><b>VS</b><span>AI</span><small>SMART COMEBACKS ONLY</small></div>`,
      literal: `<div class="literal-terminal"><small>NPC COMMAND INTERPRETER</small><strong>INPUT TOO LITERAL</strong><code>take a seat → carry chair?</code><span>Clarify the command</span></div>`,
    };
    overlay.innerHTML = blocks[visual] || `<div class="product-stage"><small>WEIRD GAME</small><strong>${escapeHtml(scene.title || "GAME")}</strong></div>`;
  }

  function openGame(scene, sessionData, messages) {
    current = scene;
    sessionId = sessionData.id || sessionData.session_id;
    currentMode = sessionData.mode || "mission";
    returnTab = "games";
    landing.classList.add("hidden");
    game.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });

    $("#gameKind").textContent = scene.tag || (scene.game_group === "arcade" ? "GAME" : "LIFE RPG");
    $("#gameLocation").textContent = scene.location || scene.title || "—";
    $("#sceneTimeLabel").textContent = scene.time ? `${scene.time} · ${scene.location || ""}` : (scene.tag || "TÌNH HUỐNG");
    $("#missionTitle").textContent = scene.title || "Tình huống";
    $("#missionText").textContent = scene.mission || "";
    $("#speakerName").textContent = scene.npc_name || "NPC";
    $("#chatCharacter").textContent = scene.npc_name || "NPC";
    $("#stage").dataset.theme = sceneTheme(scene);
    $("#stage").dataset.group = scene.game_group || "life";
    $("#stage").dataset.visual = scene.visual || "";

    const playerProfile = latestOverview?.profile || {};
    const playerAppearance = playerProfile.appearance || appearanceState;
    setActorDataset($("#playerActor"), playerAppearance, playerProfile.character_gender || selectedGender || "female", playerPose(scene));
    $("#playerActor").classList.remove("scene-enter");
    void $("#playerActor").offsetWidth;
    $("#playerActor").classList.add("scene-enter");
    setTimeout(() => $("#playerActor")?.classList.remove("scene-enter"), 1500);
    const npc = npcPreset(scene);
    setActorDataset($("#npcActor"), npc.appearance, npc.gender, npc.pose);

    renderArcadeOverlay(scene);
    renderChallenge(sessionData.challenge || { required: false });
    $("#finalAnswerInput").value = "";
    $("#finalAnswerMessage").textContent = currentChallenge.required
      ? "Chat phía trên để hỏi và lấy manh mối. Đáp án chỉ nhập ở đây."
      : "";
    setDictionaryOpen(false);
    $("#chatLog").innerHTML = "";
    $("#feedbackBox").classList.add("hidden");
    $("#hintBox").classList.add("hidden");
    $("#narratorBox").classList.add("hidden");
    $("#turnScores").classList.add("hidden");
    $("#objectiveWrap").classList.add("hidden");
    $("#toggleObjectivesBtn").textContent = "Xem mục tiêu ẩn";
    $("#replyInput").value = "";
    count();

    const history = Array.isArray(messages) ? messages : [];
    history.forEach((item) => bubble(item.role === "player" ? "player" : "npc", item.text));
    const lastNpc = [...history].reverse().find((item) => item.role === "npc") || { text: scene.opening };
    $("#dialogueText").textContent = lastNpc.text || scene.opening || "";
    $("#narratorBox").textContent = lastNpc.narrator || "";
    $("#narratorBox").classList.toggle("hidden", !lastNpc.narrator);
    showFeedback(lastNpc);
    setMood(lastNpc.mood || "happy");
    renderObjectives(scene, sessionData.objectives_completed || []);
    stats(Number(sessionData.score ?? 50), Number(sessionData.progress ?? 0), sessionData.communication || null);
    renderTurnScores(sessionData);
    setCompleted(sessionData.status === "completed" || Boolean(sessionData.completed), Number(sessionData.stars || 0));
    $("#hintBtn").classList.toggle("hidden", currentMode === "free_roam");
    if (!$("#replyInput").disabled) $("#replyInput").focus();
  }

  async function start(itemOrSceneId, mode = "mission", sourceTab = "games") {
    try {
      const item = typeof itemOrSceneId === "string"
        ? { scene_id: itemOrSceneId, briefing: {} }
        : (itemOrSceneId || {});
      const sceneId = item.scene_id || item.id;
      pendingStart = { sceneId, mode, sourceTab, briefing: item.briefing || {} };
      openTutorial(item.briefing || {});
    } catch (error) {
      showToast(error.message, true);
    }
  }

  async function requestLeave() {
    if (!sessionId) {
      returnToHub();
      return;
    }
    try {
      const summary = await api(`/api/language/sessions/${encodeURIComponent(sessionId)}/summary`);
      renderSummary(summary);
      $("#summaryDialog").showModal();
    } catch (error) {
      showToast(error.message, true);
      await confirmLeave();
    }
  }

  function renderSummary(data) {
    const s = data.session || {};
    $("#summaryStats").innerHTML = `
      <article><small>LƯỢT NÓI</small><b>${Number(data.turns || 0)}</b></article>
      <article><small>TỔNG ĐIỂM</small><b>${Number(s.score || 0)}</b></article>
      <article><small>GIAO TIẾP</small><b>${Number(s.communication || 0)}</b></article>
      <article><small>XP KIẾM ĐƯỢC</small><b>+${Number(s.xp_earned || 0)}</b></article>
    `;
    const root = $("#summaryTerms");
    root.innerHTML = "";
    const terms = data.terms || [];
    if (!terms.length) {
      root.innerHTML = `<div class="empty-recent">Phiên này chưa có đủ dữ liệu từ/cụm để tổng hợp.</div>`;
      return;
    }
    terms.forEach((item) => {
      const chip = document.createElement("div");
      chip.className = "summary-term";
      chip.innerHTML = `<strong>${escapeHtml(item.term)}</strong><span>gặp ${Number(item.encounters || 0)} · tự dùng ${Number(item.used || 0)}</span>`;
      root.appendChild(chip);
    });
  }

  async function confirmLeave() {
    const oldSession = sessionId;
    if (oldSession) {
      try {
        await api("/api/language/reset", { method: "POST", body: JSON.stringify({ session_id: oldSession }) });
      } catch {
        // ignore
      }
    }
    if ($("#summaryDialog").open) $("#summaryDialog").close();
    returnToHub();
    await loadOverview();
  }

  function returnToHub() {
    sessionId = null;
    current = null;
    currentMode = "mission";
    setCompleted(false, 0);
    game.classList.add("hidden");
    setDictionaryOpen(false);
    landing.classList.remove("hidden");
    switchTab(returnTab || "games");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function requestHint() {
    if (!sessionId || currentMode === "free_roam") return;
    try {
      const data = await api("/api/language/hint", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId }),
      });
      $("#hintLevel").textContent = String(data.hint_level || 1);
      $("#hintText").textContent = data.hint || "";
      $("#hintBox").classList.remove("hidden");
    } catch (error) {
      showToast(error.message, true);
    }
  }

  function setGenderChoice(gender) {
    selectedGender = gender || "";
    $$(".gender-choice").forEach((button) => button.classList.toggle("selected", button.dataset.gender === selectedGender));
    refreshProfilePreview();
  }

  function setLifeRoleChoice(role) {
    selectedLifeRole = role || "";
    $$(".life-role-choice").forEach((button) => button.classList.toggle("selected", button.dataset.role === selectedLifeRole));
  }

  function openProfileDialog(force = false) {
    const dialog = $("#profileDialog");
    refreshProfilePreview();
    if (!dialog.open) dialog.showModal();
    dialog.dataset.force = force ? "1" : "0";
  }

  async function savePlayerProfile(closeDialog = true) {
    if (!selectedGender) {
      showToast("Chọn nhân vật nam hoặc nữ trước.", true);
      return false;
    }
    if (!selectedLifeRole) {
      showToast("Chọn cuộc sống Sinh viên hoặc Người đi làm trước.", true);
      return false;
    }
    try {
      const data = await api("/api/language/profile", {
        method: "POST",
        body: JSON.stringify({
          character_gender: selectedGender,
          character_name: $("#characterNameInput").value.trim(),
          target_language: $("#profileLanguage").value,
          life_role: selectedLifeRole,
          skin_tone: $("#skinToneSelect").value,
          hair_style: $("#hairStyleSelect").value,
          hair_color: $("#hairColorSelect").value,
          outfit_style: $("#outfitStyleSelect").value,
          face_style: $("#faceStyleSelect").value,
          learning_goal: latestOverview?.profile?.learning_goal || "comprehensive",
          daily_minutes: Number($("#dailyMinutesSelect")?.value || latestOverview?.profile?.daily_minutes || 20),
          cefr_level: latestOverview?.profile?.cefr_level || $("#levelSelect")?.value || "A1-A2",
        }),
      });
      latestOverview = null;
      renderProfile(data.profile || {});
      $("#languageSelect").value = data.profile?.target_language || "en";
      if (closeDialog && $("#profileDialog").open) $("#profileDialog").close();
      await loadOverview();
      return true;
    } catch (error) {
      showToast(error.message, true);
      return false;
    }
  }

  async function updateLanguageFromHub() {
    const profile = latestOverview?.profile;
    if (!profile?.profile_ready) return;
    $("#profileLanguage").value = $("#languageSelect").value;
    await savePlayerProfile(false);
  }

  function switchTab(name) {
    if (name === "games") switchLearningTab("stories");
    else if (["roadmap", "foryou", "stories", "train", "progress"].includes(name)) switchLearningTab(name);
    else switchLearningTab("roadmap");
  }

  $$(".learning-tab").forEach((button) => button.addEventListener("click", () => switchLearningTab(button.dataset.learningTab)));
  $("#changeTrackBtn")?.addEventListener("click", () => openGoalDialog(false));
  $("#goalQuickBtn")?.addEventListener("click", () => { switchLearningTab("roadmap"); if (!curriculumData?.selection) openGoalDialog(false); });
  $("#confirmTrackBtn")?.addEventListener("click", confirmGoalTrack);
  $("#submitCheckpointBtn")?.addEventListener("click", submitCheckpoint);
  $$(".module-card[data-module]").forEach((button) => button.addEventListener("click", () => openLesson(button.dataset.module, "new")));
  $("#wordDexBtn")?.addEventListener("click", () => switchLearningTab("progress"));
  $$(".game-filter").forEach((button) => button.addEventListener("click", () => {
    activeGameFilter = button.dataset.gameFilter || "all";
    $$(".game-filter").forEach((item) => item.classList.toggle("active", item === button));
    renderGames(gameCardsCache);
  }));
  $("#startReviewBtn")?.addEventListener("click", () => switchLearningTab("progress"));
  $("#lessonSubmitBtn")?.addEventListener("click", submitLesson);
  $("#lessonNextBtn")?.addEventListener("click", nextLesson);
  $("#lessonAudioBtn")?.addEventListener("click", speakLessonItem);
  $("#lessonVoiceBtn")?.addEventListener("click", startSpeechRecognition);

  $("#replyForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = $("#replyInput");
    const message = input.value.trim();
    if (!message || !sessionId) return;
    if (currentChallenge.required && currentChallenge.answer_type === "code" && /^\d{6}$/.test(message.replace(/\s/g, ""))) {
      $("#finalAnswerInput").value = message.replace(/\s/g, "");
      $("#finalAnswerMessage").textContent = "Mã 6 số phải chốt ở ô ĐÁP ÁN CUỐI, không cần gửi trong chat.";
      $("#finalAnswerInput").focus();
      return;
    }

    bubble("player", message);
    input.value = "";
    count();
    input.disabled = true;
    $("#sendBtn").disabled = true;
    $("#sendBtn").textContent = "NPC đang phản ứng…";
    $("#liveLabel").textContent = "ĐANG XỬ LÝ";

    try {
      const data = await api("/api/language/respond", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, message, input_mode: "text" }),
      });
      bubble("npc", data.reply);
      $("#dialogueText").textContent = data.reply;
      $("#narratorBox").textContent = data.narrator || "";
      $("#narratorBox").classList.toggle("hidden", !data.narrator);
      showFeedback(data);
      stats(data.score, data.progress, data.communication);
      renderTurnScores(data);
      renderObjectives(current, data.objectives_completed_all || objectiveState);
      if (data.challenge) renderChallenge(data.challenge);
      if (data.new_clue) {
        $("#finalAnswerMessage").textContent = "Có manh mối mới. Nếu đã đoán ra đáp án, nhập ngay bên dưới.";
      }
      setMood(data.mood);
      effect(data.effect);
      updateQuota(data.quota);
      renderProfile(data.profile || {});
      setCompleted(Boolean(data.completed), Number(data.stars || 0));
      if (data.used_demo) showToast("Lượt này dùng chế độ dự phòng; tiến độ vẫn được lưu.");
      if (data.completed) {
        showToast(`Hoàn thành · +${Number(data.xp_earned || 0)} XP`);
        await completeGameCurriculumIfNeeded();
        await loadOverview();
      }
    } catch (error) {
      bubble("npc", `Hệ thống chưa xử lý được lượt này: ${error.message}`);
      showToast(error.message, true);
      if (error.payload?.quota) updateQuota(error.payload.quota);
    } finally {
      $("#liveLabel").textContent = "SẴN SÀNG";
      if (!$("#completionBox").classList.contains("hidden")) return;
      input.disabled = false;
      $("#sendBtn").disabled = false;
      $("#sendBtn").textContent = "Gửi";
      input.focus();
    }
  });

  $("#finalAnswerForm").addEventListener("submit", submitFinalAnswer);
  $("#useSuggestionBtn").addEventListener("click", () => { if (suggestion) insert(suggestion); });
  $("#hintBtn").addEventListener("click", requestHint);
  $("#toggleObjectivesBtn").addEventListener("click", () => {
    const wrap = $("#objectiveWrap");
    const hidden = wrap.classList.toggle("hidden");
    $("#toggleObjectivesBtn").textContent = hidden ? "Xem mục tiêu ẩn" : "Ẩn mục tiêu";
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

  $("#backBtn").addEventListener("click", requestLeave);
  $("#newSceneBtn").addEventListener("click", requestLeave);
  $("#confirmLeaveBtn").addEventListener("click", confirmLeave);
  $("#stayBtn").addEventListener("click", () => $("#summaryDialog").close());

  $("#profileBtn").addEventListener("click", () => openProfileDialog(false));
  $$(".gender-choice").forEach((button) => button.addEventListener("click", () => setGenderChoice(button.dataset.gender)));
  $$(".life-role-choice").forEach((button) => button.addEventListener("click", () => setLifeRoleChoice(button.dataset.role)));
  $("#saveProfileBtn").addEventListener("click", () => savePlayerProfile(true));
  ["skinToneSelect", "hairStyleSelect", "hairColorSelect", "outfitStyleSelect", "faceStyleSelect"].forEach((id) => {
    $("#" + id)?.addEventListener("change", refreshProfilePreview);
  });
  $("#languageSelect").addEventListener("change", updateLanguageFromHub);
  $("#levelSelect")?.addEventListener("change", async () => {
    const profile = latestOverview?.profile;
    if (!profile?.profile_ready) return;
    if ($("#cefrLevelSelect")) $("#cefrLevelSelect").value = $("#levelSelect").value;
  });

  const howDialog = $("#howDialog");
  $("#howBtn").addEventListener("click", () => howDialog.showModal());
  $("#goalDialog")?.addEventListener("cancel", (event) => {
    if ($("#goalDialog").dataset.force === "1" && !curriculumData?.selection) event.preventDefault();
  });
  $("#dictionaryFab").addEventListener("click", () => {
    const shouldOpen = $("#dictionaryPopup").classList.contains("hidden");
    setDictionaryOpen(shouldOpen);
  });
  $("#dictionaryPopupClose").addEventListener("click", () => setDictionaryOpen(false));
  $("#dictionaryChatForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    await lookupDictionary();
  });
  $("#tutorialPrevBtn").addEventListener("click", () => {
    tutorialIndex = Math.max(0, tutorialIndex - 1);
    updateTutorialStep();
  });
  $("#tutorialNextBtn").addEventListener("click", () => {
    tutorialIndex = Math.min(tutorialSteps.length - 1, tutorialIndex + 1);
    updateTutorialStep();
  });
  $("#tutorialSkipBtn").addEventListener("click", async () => {
    if ($("#tutorialDialog").open) $("#tutorialDialog").close();
    if (pendingStart) {
      const { sceneId, mode, sourceTab } = pendingStart;
      pendingStart = null;
      try { await startCore(sceneId, mode, sourceTab); } catch (error) { showToast(error.message, true); }
    }
  });
  $("#tutorialStartBtn").addEventListener("click", async () => {
    if ($("#tutorialDialog").open) $("#tutorialDialog").close();
    if (pendingStart) {
      const { sceneId, mode, sourceTab } = pendingStart;
      pendingStart = null;
      try { await startCore(sceneId, mode, sourceTab); } catch (error) { showToast(error.message, true); }
    }
  });
  $$('[data-close]').forEach((button) => {
    button.addEventListener("click", () => {
      const dialog = document.getElementById(button.dataset.close);
      if (!dialog) return;
      if (dialog.id === "profileDialog" && dialog.dataset.force === "1" && (!selectedGender || !selectedLifeRole)) return;
      if (dialog.id === "goalDialog" && dialog.dataset.force === "1" && !curriculumData?.selection) return;
      if (dialog.id === "lessonDialog") curriculumActivityContext = null;
      if (dialog.id === "tutorialDialog") pendingStart = null;
      dialog.close();
    });
  });

  document.addEventListener("DOMContentLoaded", async () => {
    await loadStatus();
    await loadOverview();
  });
})();
