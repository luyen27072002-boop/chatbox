(() => {
  "use strict";

  const page = document.body.dataset.lifePage || "";
  const $ = (id) => document.getElementById(id);
  const state = {
    entries: [],
    threads: [],
    sessions: [],
    currentEntryId: null,
    currentRehearsalId: null,
  };

  const STATUS_LABELS = {
    unsaid: "Chưa nói ra",
    waiting: "Đang chờ phản hồi",
    deciding: "Đang quyết định",
    letting_go: "Đang cố buông",
    closed: "Đã khép lại",
  };

  function excerpt(value, max = 150) {
    const clean = String(value || "").replace(/\s+/g, " ").trim();
    return clean.length > max ? `${clean.slice(0, max).trim()}…` : clean;
  }

  function formatDate(value) {
    if (!value) return "Không rõ ngày";
    const date = new Date(`${String(value).slice(0, 10)}T12:00:00`);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(date);
  }

  async function api(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    let payload = {};
    try {
      payload = await response.json();
    } catch {
      payload = {};
    }
    if (response.status === 401) {
      window.location.href = "/";
      throw new Error("Bạn cần đăng nhập trước.");
    }
    if (!response.ok) {
      throw new Error(payload.error || `Không thể xử lý yêu cầu (${response.status}).`);
    }
    return payload;
  }

  let toastTimer = null;
  function showToast(message) {
    const toast = $("toast");
    if (!toast) return;
    toast.textContent = String(message || "");
    toast.classList.add("show");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove("show"), 3200);
  }

  function setLoading(active, text = "Đang xử lý…") {
    const overlay = $("loadingOverlay");
    if (!overlay) return;
    if ($("loadingText")) $("loadingText").textContent = text;
    overlay.classList.toggle("hidden", !active);
  }

  function setCount(textareaId, countId, max) {
    const input = $(textareaId);
    const output = $(countId);
    if (!input || !output) return;
    const update = () => { output.textContent = `${input.value.length} / ${max}`; };
    input.addEventListener("input", update);
    update();
  }

  function handleUrgent(payload) {
    if (!payload?.urgent) return false;
    showToast(payload.message || "Hãy ưu tiên liên hệ một người thật đang ở gần bạn lúc này.");
    return true;
  }

  function renderTags(tags) {
    const row = $("storyTags");
    if (!row) return;
    row.replaceChildren();
    (Array.isArray(tags) ? tags : []).slice(0, 8).forEach((value) => {
      const tag = document.createElement("span");
      tag.textContent = String(value);
      row.appendChild(tag);
    });
  }

  async function createStory() {
    const rawText = $("storyRaw").value.trim();
    if (rawText.length < 20) {
      showToast("Kể thêm một chút để câu chuyện có đủ chất liệu.");
      return;
    }
    setLoading(true, "Đang viết lại thành một chương…");
    try {
      const payload = await api("/api/life/autobiography", {
        method: "POST",
        body: JSON.stringify({
          raw_text: rawText,
          style: $("storyStyle").value,
          entry_date: $("storyDate").value,
        }),
      });
      if (handleUrgent(payload)) return;
      state.currentEntryId = payload.entry.id;
      $("storyResultTitle").value = payload.entry.title;
      $("storyResultText").value = payload.entry.rewritten_text;
      renderTags(payload.entry.metadata?.tags || []);
      $("storyGuide")?.classList.add("hidden");
      $("storyResult").classList.remove("hidden");
      $("storyResult").scrollIntoView({ behavior: "smooth", block: "start" });
      showToast("Đã lưu thành một trang mới trong Dòng đời.");
    } catch (error) {
      showToast(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function saveStoryEdit() {
    if (!state.currentEntryId) return;
    const title = $("storyResultTitle").value.trim();
    const rewrittenText = $("storyResultText").value.trim();
    if (!title || !rewrittenText) {
      showToast("Tiêu đề và nội dung không được để trống.");
      return;
    }
    try {
      await api(`/api/life/entries/${state.currentEntryId}`, {
        method: "PATCH",
        body: JSON.stringify({ title, rewritten_text: rewrittenText }),
      });
      showToast("Đã lưu chỉnh sửa.");
    } catch (error) {
      showToast(error.message);
    }
  }

  async function deleteStory() {
    if (!state.currentEntryId || !window.confirm("Xóa trang vừa viết?")) return;
    try {
      await api(`/api/life/entries/${state.currentEntryId}`, { method: "DELETE" });
      state.currentEntryId = null;
      $("storyResult").classList.add("hidden");
      $("storyGuide")?.classList.remove("hidden");
      showToast("Đã xóa trang.");
    } catch (error) {
      showToast(error.message);
    }
  }

  function initStory() {
    const dateInput = $("storyDate");
    if (dateInput && !dateInput.value) dateInput.value = new Date().toISOString().slice(0, 10);
    setCount("storyRaw", "storyCount", 12000);
    $("createStoryButton")?.addEventListener("click", createStory);
    $("saveStoryEditButton")?.addEventListener("click", saveStoryEdit);
    $("deleteStoryButton")?.addEventListener("click", deleteStory);
  }

  async function createUnsent() {
    const rawText = $("unsentRaw").value.trim();
    if (rawText.length < 10) {
      showToast("Viết thêm một chút về điều bạn đang muốn nói.");
      return;
    }
    setLoading(true, "Đang biến điều khó nói thành lời…");
    try {
      const payload = await api("/api/life/unsent", {
        method: "POST",
        body: JSON.stringify({
          raw_text: rawText,
          relation: $("unsentRelation").value.trim(),
          output_type: $("unsentType").value,
        }),
      });
      if (handleUrgent(payload)) return;
      const entry = payload.entry;
      state.currentEntryId = entry.id;
      $("unsentResultTitle").textContent = entry.title;
      $("unsentResultText").textContent = entry.rewritten_text;
      const sendable = String(entry.metadata?.sendable_version || "").trim();
      $("sendableText").textContent = sendable;
      $("sendableBlock").classList.toggle("hidden", !sendable);
      const feeling = String(entry.metadata?.core_feeling || "").trim();
      $("coreFeelingBlock").textContent = feeling ? `Điều thật sự đang muốn nói: ${feeling}` : "";
      $("coreFeelingBlock").classList.toggle("hidden", !feeling);
      $("unsentGuide")?.classList.add("hidden");
      $("unsentResult").classList.remove("hidden");
      $("unsentResult").scrollIntoView({ behavior: "smooth", block: "start" });
      showToast("Đã giữ lại trong Dòng đời.");
    } catch (error) {
      showToast(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function copySendable() {
    const text = $("sendableText")?.textContent?.trim();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      showToast("Đã sao chép.");
    } catch {
      showToast("Không thể sao chép tự động trên trình duyệt này.");
    }
  }

  function initUnsent() {
    setCount("unsentRaw", "unsentCount", 8000);
    $("createUnsentButton")?.addEventListener("click", createUnsent);
    $("copySendableButton")?.addEventListener("click", copySendable);
  }

  function appendRehearsalMessage(role, content) {
    if (!content || !$("rehearsalMessages")) return;
    const bubble = document.createElement("div");
    bubble.className = `rehearsal-message ${role}`;
    bubble.textContent = content;
    $("rehearsalMessages").appendChild(bubble);
    $("rehearsalMessages").scrollTop = $("rehearsalMessages").scrollHeight;
  }

  function showCoach(result) {
    const panel = $("coachPanel");
    if (!panel) return;
    panel.replaceChildren();
    const coach = String(result?.coach_note || "").trim();
    const suggestion = String(result?.suggested_reply || "").trim();
    if (coach) {
      const note = document.createElement("div");
      note.textContent = `Nhận xét: ${coach}`;
      panel.appendChild(note);
    }
    if (suggestion) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `Dùng câu gợi ý: “${suggestion}”`;
      button.addEventListener("click", () => {
        $("rehearsalReply").value = suggestion;
        $("rehearsalReply").focus();
      });
      panel.appendChild(button);
    }
    panel.classList.toggle("hidden", !coach && !suggestion);
  }

  async function startRehearsal() {
    const otherPerson = $("rehearsalPerson").value.trim();
    const situation = $("rehearsalSituation").value.trim();
    const goal = $("rehearsalGoal").value.trim();
    const opening = $("rehearsalOpening").value.trim();
    if (!otherPerson || !situation || !opening) {
      showToast("Cần có người đối diện, tình huống và câu mở đầu.");
      return;
    }
    setLoading(true, "Đang dựng cuộc nói chuyện…");
    try {
      const payload = await api("/api/life/rehearsal/start", {
        method: "POST",
        body: JSON.stringify({ other_person: otherPerson, situation, goal, opening }),
      });
      if (handleUrgent(payload)) return;
      state.currentRehearsalId = payload.session_id;
      $("rehearsalRoomTitle").textContent = `Nói thử với ${otherPerson}`;
      $("rehearsalMessages").replaceChildren();
      appendRehearsalMessage("user", opening);
      appendRehearsalMessage("counterpart", payload.result?.counterpart_reply);
      showCoach(payload.result || {});
      $("rehearsalSetup").classList.add("hidden");
      $("rehearsalRoom").classList.remove("hidden");
      showToast("Buổi tập đã bắt đầu.");
    } catch (error) {
      showToast(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function sendRehearsalReply() {
    const message = $("rehearsalReply").value.trim();
    if (!state.currentRehearsalId || !message) return;
    $("rehearsalReply").value = "";
    appendRehearsalMessage("user", message);
    setLoading(true, "Người đối diện đang phản ứng…");
    try {
      const payload = await api(`/api/life/rehearsal/${state.currentRehearsalId}/reply`, {
        method: "POST",
        body: JSON.stringify({ message }),
      });
      appendRehearsalMessage("counterpart", payload.result?.counterpart_reply);
      showCoach(payload.result || {});
    } catch (error) {
      showToast(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function closeRehearsal() {
    if (state.currentRehearsalId) {
      try {
        await api(`/api/life/rehearsal/${state.currentRehearsalId}/close`, {
          method: "POST",
          body: "{}",
        });
      } catch (error) {
        showToast(error.message);
        return;
      }
    }
    state.currentRehearsalId = null;
    $("rehearsalRoom").classList.add("hidden");
    $("rehearsalSetup").classList.remove("hidden");
    showToast("Đã kết thúc buổi tập.");
  }

  function initRehearsal() {
    $("startRehearsalButton")?.addEventListener("click", startRehearsal);
    $("sendRehearsalReplyButton")?.addEventListener("click", sendRehearsalReply);
    $("closeRehearsalButton")?.addEventListener("click", closeRehearsal);
    $("rehearsalReply")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendRehearsalReply();
      }
    });
  }

  function renderThreadItem(thread) {
    const item = document.createElement("article");
    item.className = `thread-item${thread.status === "closed" ? " closed" : ""}`;

    const copy = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = thread.title;
    const detail = document.createElement("p");
    detail.textContent = thread.detail || "Chưa có ghi chú thêm.";
    copy.append(title, detail);

    const actions = document.createElement("div");
    actions.className = "thread-actions";
    const select = document.createElement("select");
    select.className = "thread-status";
    Object.entries(STATUS_LABELS).forEach(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      option.selected = value === thread.status;
      select.appendChild(option);
    });
    select.addEventListener("change", async () => {
      const previous = thread.status;
      try {
        const payload = await api(`/api/life/threads/${thread.id}`, {
          method: "PATCH",
          body: JSON.stringify({ status: select.value }),
        });
        Object.assign(thread, payload.thread);
        renderThreads();
        showToast("Đã cập nhật trạng thái.");
      } catch (error) {
        select.value = previous;
        showToast(error.message);
      }
    });

    const remove = document.createElement("button");
    remove.className = "icon-button";
    remove.type = "button";
    remove.textContent = "×";
    remove.title = "Xóa";
    remove.addEventListener("click", async () => {
      if (!window.confirm("Xóa chuyện này khỏi danh sách?")) return;
      try {
        await api(`/api/life/threads/${thread.id}`, { method: "DELETE" });
        state.threads = state.threads.filter((row) => row.id !== thread.id);
        renderThreads();
        showToast("Đã xóa.");
      } catch (error) {
        showToast(error.message);
      }
    });

    actions.append(select, remove);
    item.append(copy, actions);
    return item;
  }

  function renderThreads() {
    const list = $("allThreads");
    if (!list) return;
    list.replaceChildren();
    const openCount = state.threads.filter((row) => row.status !== "closed").length;
    if ($("threadOpenCount")) $("threadOpenCount").textContent = `${openCount} chuyện đang mở`;
    if (!state.threads.length) {
      list.className = "thread-list empty-state";
      list.textContent = "Chưa có chuyện nào. Bạn có thể thêm một chuyện ở bên cạnh.";
      return;
    }
    list.className = "thread-list";
    state.threads.forEach((thread) => list.appendChild(renderThreadItem(thread)));
  }

  async function loadThreads() {
    try {
      const payload = await api("/api/life/overview");
      state.threads = Array.isArray(payload.threads) ? payload.threads : [];
      renderThreads();
    } catch (error) {
      showToast(error.message);
    }
  }

  async function addThread() {
    const title = $("threadTitle").value.trim();
    if (!title) {
      showToast("Tên chuyện đang trống.");
      return;
    }
    try {
      const payload = await api("/api/life/threads", {
        method: "POST",
        body: JSON.stringify({
          title,
          detail: $("threadDetail").value.trim(),
          status: $("threadStatus").value,
        }),
      });
      state.threads.unshift(payload.thread);
      $("threadTitle").value = "";
      $("threadDetail").value = "";
      $("threadStatus").value = "unsaid";
      renderThreads();
      showToast("Đã thêm chuyện đang mở.");
    } catch (error) {
      showToast(error.message);
    }
  }

  function initThreads() {
    $("addThreadButton")?.addEventListener("click", addThread);
    loadThreads();
  }

  function openEntryModal(entry) {
    const modal = $("entryModal");
    if (!modal) return;
    $("entryModalMeta").textContent = `${formatDate(entry.entry_date)} · ${entry.entry_type === "unsent" ? "Điều chưa nói" : "Trang tự truyện"}`;
    $("entryModalTitle").textContent = entry.title || "Một trang của tôi";
    $("entryModalText").textContent = entry.rewritten_text || "";
    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeEntryModal() {
    $("entryModal")?.classList.add("hidden");
    document.body.style.overflow = "";
  }

  function renderTimelineEntries() {
    const container = $("timelineEntries");
    if (!container) return;
    container.replaceChildren();
    if ($("timelineEntryCount")) $("timelineEntryCount").textContent = `${state.entries.length} trang`;
    if (!state.entries.length) {
      container.className = "timeline-list empty-state";
      container.textContent = "Chưa có trang nào. Bạn có thể bắt đầu từ Viết lại hôm nay hoặc Điều chưa nói.";
      return;
    }
    container.className = "timeline-list";
    state.entries.forEach((entry) => {
      const item = document.createElement("article");
      item.className = "timeline-item";
      const date = document.createElement("time");
      date.className = "timeline-date";
      date.textContent = formatDate(entry.entry_date);
      const copy = document.createElement("div");
      copy.className = "timeline-copy";
      const title = document.createElement("h3");
      title.textContent = entry.title || "Một trang của tôi";
      const preview = document.createElement("p");
      preview.textContent = excerpt(entry.rewritten_text, 170);
      copy.append(title, preview);
      const open = document.createElement("button");
      open.type = "button";
      open.className = "timeline-open";
      open.textContent = entry.entry_type === "unsent" ? "Điều chưa nói →" : "Đọc trang →";
      open.addEventListener("click", () => openEntryModal(entry));
      item.append(date, copy, open);
      container.appendChild(item);
    });
  }

  function renderTimelineConversations(conversations) {
    const container = $("timelineConversations");
    if (!container) return;
    container.replaceChildren();
    if (!conversations.length) {
      container.className = "timeline-list empty-state";
      container.textContent = "Chưa có cuộc trò chuyện nào được lưu.";
      return;
    }
    container.className = "timeline-list";
    conversations.forEach((conversation) => {
      const link = document.createElement("a");
      link.className = "timeline-item timeline-conversation-link";
      link.href = `/chat?conversation=${encodeURIComponent(conversation.id)}`;
      const date = document.createElement("time");
      date.className = "timeline-date";
      date.textContent = formatDate(conversation.updated_at);
      const copy = document.createElement("div");
      copy.className = "timeline-copy";
      const title = document.createElement("h3");
      title.textContent = conversation.title || "Cuộc trò chuyện";
      const preview = document.createElement("p");
      preview.textContent = excerpt(conversation.preview || "Chưa có nội dung xem trước", 170);
      copy.append(title, preview);
      const kind = document.createElement("span");
      kind.className = "timeline-kind";
      kind.textContent = "Mở lại";
      link.append(date, copy, kind);
      container.appendChild(link);
    });
  }

  async function loadTimeline() {
    try {
      const [lifePayload, conversationPayload] = await Promise.all([
        api("/api/life/overview"),
        api("/api/conversations"),
      ]);
      state.entries = Array.isArray(lifePayload.entries) ? lifePayload.entries : [];
      renderTimelineEntries();
      renderTimelineConversations(Array.isArray(conversationPayload.conversations) ? conversationPayload.conversations : []);
    } catch (error) {
      showToast(error.message);
    }
  }

  function initTimeline() {
    document.querySelectorAll("[data-close-entry-modal]").forEach((button) => button.addEventListener("click", closeEntryModal));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeEntryModal();
    });
    loadTimeline();
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (page === "story") initStory();
    if (page === "unsent") initUnsent();
    if (page === "rehearsal") initRehearsal();
    if (page === "threads") initThreads();
    if (page === "timeline") initTimeline();
  });
})();
