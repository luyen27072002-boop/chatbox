
(() => {
  "use strict";
  const STORAGE_KEY = "mo_loi_ui_language";
  const fallback = "vi";
  const dictionaries = {
    vi: {
      "common.language": "Ngôn ngữ",
      "common.loadingQuota": "Đang tải số lượt…",
      "common.loadingAccount": "Đang tải tài khoản…",
      "common.loadingQuotaLong": "Đang kiểm tra số lượt hiện có…",
      "common.logout": "Đăng xuất",
      "common.quickChat": "Trò chuyện nhanh",
      "common.backHome": "← Trang chính",
      "common.openChat": "Mở trò chuyện",
      "common.loggedIn": "Đã đăng nhập",
      "home.meta.title": "Mở Lối — Học tập, sự nghiệp và cuộc sống",
      "home.brand.tagline": "Học tập · Sự nghiệp · Cuộc sống",
      "home.nav.language": "Ngoại ngữ",
      "home.nav.cv": "CV & phỏng vấn",
      "home.nav.jobs": "Tìm việc",
      "home.nav.astrology": "Tử vi",
      "home.nav.finance": "Chi tiêu",
      "home.nav.self": "Khám phá bản thân",
      "home.nav.life": "Trò chuyện & nhật ký",
      "home.hero.eyebrow": "Nền tảng phát triển dành cho người Việt trẻ",
      "home.hero.title": "Học tốt hơn.<br>Đi làm tự tin hơn.",
      "home.hero.start": "Bắt đầu miễn phí",
      "home.hero.tools": "Khám phá công cụ",
      "home.picture.active": "Đang hoạt động",
      "home.picture.soon": "Sắp ra mắt",
      "home.picture.language": "Ngoại ngữ nhập vai",
      "home.picture.cv": "CV & phỏng vấn",
      "home.picture.jobs": "Tìm việc phù hợp",
      "home.picture.life": "Trò chuyện & nhật ký",
      "home.products.eyebrow": "Chọn đúng công cụ",
      "home.products.title": "Hôm nay bạn muốn bắt đầu từ đâu?",
      "home.card.ready": "Đang hoạt động",
      "home.card.building": "Đang phát triển",
      "home.card.language.title": "Ngoại ngữ cho sinh viên & người đi làm",
      "home.card.language.desc": "Luyện phản xạ qua những tình huống có nhân vật, câu chuyện và phản hồi tức thì.",
      "home.card.language.cta": "Mở ngay",
      "home.card.cv.title": "CV & phỏng vấn",
      "home.card.cv.desc": "Viết hồ sơ rõ ràng hơn và chuẩn bị câu trả lời dựa trên chính kinh nghiệm của bạn.",
      "home.card.cv.meta": "Hồ sơ và luyện phỏng vấn",
      "home.card.cv.cta": "Mở ngay",
      "home.card.jobs.title": "Tìm việc phù hợp",
      "home.card.jobs.desc": "Lọc tin tuyển dụng và đối chiếu yêu cầu công việc với năng lực hiện tại.",
      "home.card.jobs.meta": "Tìm và lọc việc phù hợp",
      "home.card.jobs.cta": "Tìm việc",
      "home.dynamic.careerWaiting": "Chưa có hồ sơ nghề nghiệp",
      "home.dynamic.careerProfile": "Hồ sơ đã lưu · chưa tạo CV",
      "home.dynamic.careerReady": "Đã có bản CV gần nhất",
      "home.dynamic.jobsWaiting": "Chưa lưu việc nào",
      "home.dynamic.jobsReady": "Đã lưu {count} việc",
      "home.card.astrology.title": "Tử vi & lá số",
      "home.card.astrology.desc": "Xem lá số tóm tắt, xu hướng thời gian gần và hỏi sâu đúng điều bạn quan tâm.",
      "home.card.astrology.cta": "Xem lá số",
      "home.card.finance.title": "Quản lý chi tiêu",
      "home.card.finance.desc": "Ghi thu chi, đặt ngân sách và theo dõi mục tiêu để dành theo từng tháng.",
      "home.card.finance.cta": "Mở ví",
      "home.card.self.title": "Khám phá bản thân",
      "home.card.self.desc": "Big Five, EQ và tư duy logic trong một khu; chấm điểm bằng code, không tốn lượt AI.",
      "home.card.self.cta": "Khám phá",
      "home.card.life.title": "Trò chuyện & nhật ký",
      "home.card.life.desc": "Trò chuyện, viết lại một ngày và giữ các câu chuyện vẫn đang tiếp diễn.",
      "home.card.life.cta": "Đi vào",
      "home.dynamic.noSession": "Chưa có phiên học nào",
      "home.dynamic.activePlaying": "Đang chơi: {title} · {progress}%",
      "home.dynamic.completedCount": "Đã hoàn thành {count} cảnh",
      "home.dynamic.triedCount": "Đã thử {count} phiên",
      "home.dynamic.astrologyWaiting": "Chưa có lá số nào",
      "home.dynamic.astrologyReady": "Đã có lá số · {canChi}",
      "home.dynamic.financeWaiting": "Chưa ghi khoản nào tháng này",
      "home.dynamic.financeReady": "Đã chi {amount} tháng này",
      "home.dynamic.selfWaiting": "Chưa làm bài nào",
      "home.dynamic.selfReady": "Đã hoàn thành {count}/3 bài",
      "home.dynamic.lifeWaiting": "Góc riêng đang chờ câu đầu tiên",
      "home.dynamic.lifeStats": "{entries} trang đã viết · {threads} chuyện đang mở",
      "life.meta.title": "Trò chuyện & Nhật ký — Mở Lối",
      "life.brand.title": "Góc nhỏ cuộc sống",
      "life.brand.subtitle": "Không gian của riêng bạn",
      "life.top.openChat": "Mở trò chuyện",
      "life.hero.eyebrow": "Chậm lại một chút",
      "life.hero.title": "Hôm nay bạn muốn làm gì?",
      "life.hero.desc": "Không cần bắt đầu bằng một câu chuyện hoàn chỉnh. Chọn đúng nơi với điều đang nằm trong lòng bạn.",
      "career.cv.meta.title": "CV & phỏng vấn — Mở Lối",
      "career.jobs.meta.title": "Tìm kiếm việc làm — Mở Lối",
      "career.cv.title": "CV và luyện phỏng vấn",
      "career.jobs.title": "Tìm kiếm việc làm",
      "language.meta.title": "Ngoại ngữ nhập vai — Mở Lối",
      "language.back": "← Trang chính",
      "language.brand.subtitle": "Ngoại ngữ nhập vai",
      "language.label.language": "Ngôn ngữ",
      "language.label.level": "Trình độ",
      "language.label.humor": "Độ tấu hài"
    },
    en: {
      "common.language": "Language",
      "common.loadingQuota": "Loading credits…",
      "common.loadingAccount": "Loading account…",
      "common.loadingQuotaLong": "Checking your remaining credits…",
      "common.logout": "Log out",
      "common.quickChat": "Quick chat",
      "common.backHome": "← Home",
      "common.openChat": "Open chat",
      "common.loggedIn": "Signed in",
      "home.meta.title": "Mo Loi — Learning, career and life",
      "home.brand.tagline": "Learning · Career · Life",
      "home.nav.language": "Languages",
      "home.nav.cv": "CV & interview",
      "home.nav.jobs": "Jobs",
      "home.nav.astrology": "Astrology",
      "home.nav.finance": "Spending",
      "home.nav.self": "Self discovery",
      "home.nav.life": "Chat & journal",
      "home.hero.eyebrow": "A growth platform for young Vietnamese users",
      "home.hero.title": "Learn better.<br>Work with more confidence.",
      "home.hero.start": "Start free",
      "home.hero.tools": "Explore tools",
      "home.picture.active": "Live now",
      "home.picture.soon": "Coming soon",
      "home.picture.language": "Role-play languages",
      "home.picture.cv": "CV & interview",
      "home.picture.jobs": "Find matching jobs",
      "home.picture.life": "Chat & journal",
      "home.products.eyebrow": "Choose the right tool",
      "home.products.title": "Where do you want to begin today?",
      "home.card.ready": "Available now",
      "home.card.building": "In development",
      "home.card.language.title": "Languages for students & working adults",
      "home.card.language.desc": "Build real-life reactions through scenes, characters and instant feedback.",
      "home.card.language.cta": "Open now",
      "home.card.cv.title": "CV & interview",
      "home.card.cv.desc": "Write a clearer profile and prepare answers based on your real experience.",
      "home.card.cv.meta": "CV profile and interview practice",
      "home.card.cv.cta": "Open now",
      "home.card.jobs.title": "Find matching jobs",
      "home.card.jobs.desc": "Filter job posts and compare requirements with your current skills.",
      "home.card.jobs.meta": "Search and filter matching jobs",
      "home.card.jobs.cta": "Find jobs",
      "home.dynamic.careerWaiting": "No career profile yet",
      "home.dynamic.careerProfile": "Profile saved · no CV yet",
      "home.dynamic.careerReady": "Latest CV is ready",
      "home.dynamic.jobsWaiting": "No saved jobs",
      "home.dynamic.jobsReady": "{count} saved jobs",
      "home.card.astrology.title": "Astrology & birth chart",
      "home.card.astrology.desc": "Get a short birth-chart reading, near-future tendencies, and ask deeper questions about what matters.",
      "home.card.astrology.cta": "View chart",
      "home.card.finance.title": "Spending manager",
      "home.card.finance.desc": "Log income and expenses, set a budget, and track monthly savings goals.",
      "home.card.finance.cta": "Open wallet",
      "home.card.self.title": "Self discovery",
      "home.card.self.desc": "Big Five, emotional skills, and reasoning in one place, scored in code with no AI credits.",
      "home.card.self.cta": "Explore",
      "home.card.life.title": "Chat & journal",
      "home.card.life.desc": "Chat, rewrite your day, and keep ongoing stories alive.",
      "home.card.life.cta": "Enter",
      "home.dynamic.noSession": "No learning session yet",
      "home.dynamic.activePlaying": "Playing: {title} · {progress}%",
      "home.dynamic.completedCount": "Completed {count} scenes",
      "home.dynamic.triedCount": "Tried {count} sessions",
      "home.dynamic.astrologyWaiting": "No birth chart yet",
      "home.dynamic.astrologyReady": "Chart ready · {canChi}",
      "home.dynamic.financeWaiting": "No transactions this month",
      "home.dynamic.financeReady": "Spent {amount} this month",
      "home.dynamic.selfWaiting": "No tests completed yet",
      "home.dynamic.selfReady": "Completed {count}/3 tests",
      "home.dynamic.lifeWaiting": "Your private corner is waiting for the first line",
      "home.dynamic.lifeStats": "{entries} pages written · {threads} ongoing threads",
      "life.meta.title": "Chat & Journal — Mo Loi",
      "life.brand.title": "Life corner",
      "life.brand.subtitle": "A space that feels like yours",
      "life.top.openChat": "Open chat",
      "life.hero.eyebrow": "Slow down a little",
      "life.hero.title": "What do you want to do today?",
      "life.hero.desc": "You do not need a perfect story to begin. Choose the place that fits what is sitting in your heart.",
      "career.cv.meta.title": "CV & interview — Mo Loi",
      "career.jobs.meta.title": "Job search — Mo Loi",
      "career.cv.title": "CV and interview practice",
      "career.jobs.title": "Job search",
      "language.meta.title": "Role-play languages — Mo Loi",
      "language.back": "← Home",
      "language.brand.subtitle": "Role-play languages",
      "language.label.language": "Language",
      "language.label.level": "Level",
      "language.label.humor": "Humor mode"
    },
    zh: {
      "common.language": "語言",
      "common.loadingQuota": "正在載入點數…",
      "common.loadingAccount": "正在載入帳號…",
      "common.loadingQuotaLong": "正在檢查剩餘點數…",
      "common.logout": "登出",
      "common.quickChat": "快速聊天",
      "common.backHome": "← 首頁",
      "common.openChat": "開啟聊天",
      "common.loggedIn": "已登入",
      "home.meta.title": "Mở Lối — 學習、職涯與生活",
      "home.brand.tagline": "學習 · 職涯 · 生活",
      "home.nav.language": "語言學習",
      "home.nav.cv": "履歷與面試",
      "home.nav.jobs": "找工作",
      "home.nav.astrology": "命盤",
      "home.nav.finance": "支出",
      "home.nav.self": "探索自己",
      "home.nav.life": "聊天與日記",
      "home.hero.eyebrow": "為年輕越南使用者打造的成長平台",
      "home.hero.title": "學得更好。<br>工作更有自信。",
      "home.hero.start": "免費開始",
      "home.hero.tools": "探索工具",
      "home.picture.active": "已上線",
      "home.picture.soon": "即將推出",
      "home.picture.language": "情境語言學習",
      "home.picture.cv": "履歷與面試",
      "home.picture.jobs": "適合的工作",
      "home.picture.life": "聊天與日記",
      "home.products.eyebrow": "選擇正確工具",
      "home.products.title": "你今天想從哪裡開始？",
      "home.card.ready": "已可使用",
      "home.card.building": "開發中",
      "home.card.language.title": "給學生與上班族的外語學習",
      "home.card.language.desc": "透過情境、角色與即時回饋，訓練真實反應能力。",
      "home.card.language.cta": "立即開啟",
      "home.card.cv.title": "履歷與面試",
      "home.card.cv.desc": "把經歷寫得更清楚，並根據你的真實經驗準備面試回答。",
      "home.card.cv.meta": "履歷資料與面試練習",
      "home.card.cv.cta": "立即開啟",
      "home.card.jobs.title": "適合的工作",
      "home.card.jobs.desc": "篩選職缺並比對目前能力與職務需求。",
      "home.card.jobs.meta": "搜尋並篩選合適職缺",
      "home.card.jobs.cta": "找工作",
      "home.dynamic.careerWaiting": "尚未建立職涯資料",
      "home.dynamic.careerProfile": "資料已儲存 · 尚未建立履歷",
      "home.dynamic.careerReady": "已有最新履歷",
      "home.dynamic.jobsWaiting": "尚未儲存職缺",
      "home.dynamic.jobsReady": "已儲存 {count} 個職缺",
      "home.card.astrology.title": "命盤與運勢",
      "home.card.astrology.desc": "先看命盤摘要與近期趨勢，再針對真正關心的主題深入提問。",
      "home.card.astrology.cta": "查看命盤",
      "home.card.finance.title": "支出管理",
      "home.card.finance.desc": "記錄收支、設定預算，並追蹤每月儲蓄目標。",
      "home.card.finance.cta": "開啟錢包",
      "home.card.self.title": "探索自己",
      "home.card.self.desc": "Big Five、情緒能力與邏輯思考集中在一區，由程式計分，不消耗 AI 點數。",
      "home.card.self.cta": "開始探索",
      "home.card.life.title": "聊天與日記",
      "home.card.life.desc": "聊天、改寫你的一天，並保存仍在延續的故事。",
      "home.card.life.cta": "進入",
      "home.dynamic.noSession": "尚未開始任何學習場景",
      "home.dynamic.activePlaying": "進行中：{title} · {progress}%",
      "home.dynamic.completedCount": "已完成 {count} 個場景",
      "home.dynamic.triedCount": "已體驗 {count} 次",
      "home.dynamic.astrologyWaiting": "尚未建立命盤",
      "home.dynamic.astrologyReady": "已有命盤 · {canChi}",
      "home.dynamic.financeWaiting": "這個月還沒有交易",
      "home.dynamic.financeReady": "本月已支出 {amount}",
      "home.dynamic.selfWaiting": "尚未完成任何測驗",
      "home.dynamic.selfReady": "已完成 {count}/3 個測驗",
      "home.dynamic.lifeWaiting": "你的私人角落正在等第一句話",
      "home.dynamic.lifeStats": "已寫 {entries} 頁 · {threads} 個進行中的故事",
      "life.meta.title": "聊天與日記 — Mở Lối",
      "life.brand.title": "生活角落",
      "life.brand.subtitle": "屬於你的私人空間",
      "life.top.openChat": "開啟聊天",
      "life.hero.eyebrow": "慢一點也沒關係",
      "life.hero.title": "你今天想做什麼？",
      "life.hero.desc": "不需要先整理成完整故事。只要選擇最適合當下心情的入口。",
      "career.cv.meta.title": "履歷與面試 — Mở Lối",
      "career.jobs.meta.title": "找工作 — Mở Lối",
      "career.cv.title": "履歷與面試練習",
      "career.jobs.title": "找工作",
      "language.meta.title": "情境語言學習 — Mở Lối",
      "language.back": "← 首頁",
      "language.brand.subtitle": "情境語言學習",
      "language.label.language": "語言",
      "language.label.level": "程度",
      "language.label.humor": "搞笑程度"
    }
  };

  const getLanguage = () => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return dictionaries[stored] ? stored : fallback;
  };

  const interpolate = (text, vars = {}) => String(text).replace(/\{(\w+)\}/g, (_, key) => vars[key] ?? `{${key}}`);
  const t = (key, vars = {}) => {
    const lang = getLanguage();
    const dict = dictionaries[lang] || {};
    const base = dictionaries[fallback] || {};
    const value = dict[key] ?? base[key] ?? key;
    return interpolate(value, vars);
  };

  const applyTranslations = () => {
    const lang = getLanguage();
    document.documentElement.lang = lang === 'zh' ? 'zh-Hant' : lang;
    document.querySelectorAll('[data-i18n]').forEach((node) => {
      node.textContent = t(node.getAttribute('data-i18n'));
    });
    document.querySelectorAll('[data-i18n-html]').forEach((node) => {
      node.innerHTML = t(node.getAttribute('data-i18n-html'));
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((node) => {
      node.setAttribute('placeholder', t(node.getAttribute('data-i18n-placeholder')));
    });
    document.querySelectorAll('[data-i18n-title]').forEach((node) => {
      node.textContent = t(node.getAttribute('data-i18n-title'));
    });
    document.querySelectorAll('.global-language-select').forEach((select) => {
      if (select.value !== lang) select.value = lang;
    });
    document.dispatchEvent(new CustomEvent('moloi:languagechange', { detail: { lang } }));
  };

  const setLanguage = (lang) => {
    if (!dictionaries[lang]) lang = fallback;
    localStorage.setItem(STORAGE_KEY, lang);
    applyTranslations();
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.global-language-select').forEach((select) => {
      select.value = getLanguage();
      select.addEventListener('change', (event) => setLanguage(event.target.value));
    });
    applyTranslations();
    const sceneLangSelect = document.getElementById('languageSelect');
    if (sceneLangSelect) {
      const current = getLanguage();
      if (current === 'en' || current === 'zh') {
        sceneLangSelect.value = current;
        sceneLangSelect.dispatchEvent(new Event('change', { bubbles: true }));
      }
      document.addEventListener('moloi:languagechange', (event) => {
        const lang = event.detail?.lang;
        if (lang === 'en' || lang === 'zh') {
          sceneLangSelect.value = lang;
        } else {
          sceneLangSelect.value = 'all';
        }
        sceneLangSelect.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }
  });

  window.ML_I18N = { getLanguage, setLanguage, t };
})();
