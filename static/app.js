const SUPPORTED_LANGUAGES = [
  { value: "vi", label: "Tiếng Việt" },
  { value: "en", label: "English" },
  { value: "zh-Hans", label: "简体中文" },
  { value: "zh-Hant", label: "繁體中文" },
];

const TONE_OPTIONS = {
  vi: [
    { value: "gentle", label: "Nhẹ nhàng" },
    { value: "realistic", label: "Thực tế" },
  ],
  en: [
    { value: "gentle", label: "Gentle" },
    { value: "realistic", label: "Realistic" },
  ],
  "zh-Hans": [
    { value: "gentle", label: "温和" },
    { value: "realistic", label: "现实" },
  ],
  "zh-Hant": [
    { value: "gentle", label: "溫和" },
    { value: "realistic", label: "務實" },
  ],
};

const uiText = {
  vi: {
    brandTagline: "Nơi bạn là chính mình.",
    auth: {
      kicker: "Ở đây không cần phải tỏ ra ổn",
      title: "Có chuyện thì cứ kể.",
      desc: "Một cuộc trò chuyện riêng, nhớ được câu chuyện của bạn và biết lúc nào nên nghe, lúc nào nên nói thẳng.",
      bubbleUser: "Dạo này mình thấy mệt mà không biết nói với ai.",
      bubbleBot: "Ừ, kể từ đoạn làm bạn nặng đầu nhất đi.",
      loginTab: "Đăng nhập",
      registerTab: "Tạo tài khoản",
      loginTitle: "Chào mừng quay lại",
      loginDesc: "Câu chuyện cũ vẫn ở đúng chỗ.",
      loginId: "Tên đăng nhập hoặc email",
      password: "Mật khẩu",
      remember: "Giữ đăng nhập trên máy này",
      loginButton: "Vào trò chuyện",
      registerTitle: "Tạo một góc riêng",
      registerDesc: "Mỗi tài khoản có lịch sử và phần ghi nhớ riêng.",
      displayName: "Tên hiển thị",
      username: "Tên đăng nhập",
      email: "Email",
      confirmPassword: "Nhập lại mật khẩu",
      registerButton: "Tạo tài khoản",
    },
    needsLabel: { minh_ban: "Bạn đang cần gì?", tao_may: "Mày đang cần gì?" },
    hearFromLabel: { minh_ban: "Bạn muốn nghe từ ai?", tao_may: "Mày muốn nghe từ ai?" },
    personalityLabel: { minh_ban: "Tính cách của bạn", tao_may: "Tính cách của mày" },
    categoryField: "Chuyện đang kể",
    categories: { love: "Tình cảm", study: "Học hành", family: "Gia đình", career: "Công việc và tương lai", friends: "Bạn bè", other: "Chuyện khác" },
    pronouns: { minh_ban: "Mình – bạn", tao_may: "Tao – mày" },
    modeTitles: { listen: "Chỉ lắng nghe", clarify: "Cùng phân tích", advice: "Cho hướng xử lý" },
    modeCards: {
      listen: { title: "Lắng nghe", desc: { minh_ban: "Cho mình biết bạn đang cảm thấy thế nào?", tao_may: "Cho tao biết mày đang cảm thấy thế nào?" } },
      clarify: { title: "Cùng phân tích", desc: { minh_ban: "Chúng ta cùng nhau xem tại sao nó lại như vậy.", tao_may: "Tao với mày cùng xem tại sao nó lại như vậy." } },
      advice: { title: "Cho hướng xử lý", desc: { minh_ban: "Cùng mình tìm hướng giải quyết nhé.", tao_may: "Cùng tao tìm hướng giải quyết nhé." } },
    },
    styleButtonDesc: "Tùy chuyện mà mềm hay thẳng",
    styles: {
      adaptive: { name: "Lúc này lúc kia", description: "Để xem hôm nay bạn muốn gì" },
      strict: { name: "Người khó tính", description: "Thẳng, công bằng, không nuông chiều" },
      gentle: { name: "Người ôn hòa", description: "Mềm nhưng không nói cho vui" },
      rational: { name: "Người lý trí", description: "Nhìn dữ kiện trước cảm xúc" },
      practical: { name: "Người thực tế", description: "Chốt việc làm được ngay" },
      light_humor: { name: "Hài hước nhẹ", description: "Đỡ căng nhưng không đùa quá trớn" },
      luyen: { name: "Luyện", description: "Thử nhé!" },
    },
    experiencesButton: { minh_ban: "Những gì bạn đã trải qua", tao_may: "Những gì mày đã trải qua" },
    usageSuffix: "lượt miễn phí",
    welcome: {
      eyebrow: { minh_ban: "Có mình ở đây rồi", tao_may: "Có tao ở đây rồi" },
      title: { minh_ban: "Kể mình nghe, hôm nay bạn đã gặp phải chuyện gì?", tao_may: "Kể tao nghe, hôm nay mày đã gặp phải chuyện gì?" },
      starters: {
        love: { title: "Tình cảm", desc: "Có người làm mình nghĩ nhiều", message: { minh_ban: "Mình đang rối vì một chuyện tình cảm.", tao_may: "Tao đang rối vì một chuyện tình cảm." } },
        study: { title: "Học hành", desc: "Áp lực, chọn ngành, tương lai", message: { minh_ban: "Dạo này chuyện học hành làm mình khá mệt.", tao_may: "Dạo này chuyện học hành làm tao khá mệt." } },
        career: { title: "Công việc", desc: "Sếp, đồng nghiệp, tiền bạc", message: { minh_ban: "Mình đang mắc ở một chuyện công việc.", tao_may: "Tao đang mắc ở một chuyện công việc." } },
        family: { title: "Gia đình", desc: "Bố mẹ, vợ chồng, con cái", message: { minh_ban: "Mình đang có một chuyện trong gia đình muốn kể.", tao_may: "Tao đang có một chuyện trong gia đình muốn kể." } },
      },
    },
    placeholder: { minh_ban: "Kể mình nghe...", tao_may: "Kể tao nghe..." },
    send: "Gửi",
    composerNote: "Shift + Enter để xuống dòng",
    styleDialog: {
      eyebrow: "Chọn người nói chuyện",
      title: { minh_ban: "Hôm nay bạn muốn nghe từ ai?", tao_may: "Hôm nay mày muốn nghe từ ai?" },
      copy: "Cùng một câu chuyện, nhưng mỗi người sẽ nhìn theo một cách khác.",
      optionDescriptions: { adaptive: "Tùy tâm trạng nhé!", strict: "Thẳng, công bằng, không nuông chiều", gentle: "Mềm nhưng không nói cho vui", rational: "Nhìn dữ kiện trước cảm xúc", practical: "Chốt việc làm được ngay", light_humor: "Đỡ căng nhưng không đùa quá trớn", luyen: "Muốn nói chuyện với mình khum?" },
    },
    conversations: {
      eyebrow: "Những gì bạn đã trải qua",
      title: "Chuyện cũ vẫn ở đây",
      copy: "Mở lại một câu chuyện để nói tiếp, hoặc bắt đầu một chuyện mới.",
      newButton: "Cuộc trò chuyện mới",
      searchPlaceholder: "Tìm trong chuyện cũ...",
      emptyTitle: "Chưa có chuyện nào được lưu",
      emptyDesc: "Khi bạn gửi tin nhắn đầu tiên, cuộc trò chuyện sẽ tự xuất hiện ở đây.",
      loading: "Đang mở chuyện cũ...",
      untitled: "Cuộc trò chuyện",
      emptyPreview: "Chưa có nội dung xem trước",
      today: "Hôm nay",
      yesterday: "Hôm qua",
      rename: "Đổi tên",
      delete: "Xóa",
      deleteConfirm: "Xóa “{title}”? Nội dung đã xóa sẽ không thể khôi phục.",
    },
    renameDialog: { eyebrow: "Đổi tên", title: "Đặt tên cho câu chuyện này", cancel: "Hủy", save: "Lưu tên" },
    account: { eyebrow: "Tài khoản", logout: "Đăng xuất" },
    profileCardDefaultName: "Chưa làm quen",
    profileCardDefaultDesc: "20 câu ngắn về tính cách",
    userMeta: { minh_ban: "Bạn", tao_may: "Mày" },
    statuses: { saved: "Đã lưu.", languageChanged: "Đã đổi ngôn ngữ.", safetyPriority: "Mình đang ưu tiên chuyện an toàn trước.", thinking: "đang nghĩ..." },
  },
  en: {
    brandTagline: "A quiet corner where you can be yourself.",
    auth: { kicker: "You don't have to pretend you're okay here", title: "If you need to talk, talk.", desc: "A private conversation that remembers your story and knows when to listen and when to be direct.", bubbleUser: "Lately I've felt tired and I don't know who to talk to.", bubbleBot: "Yeah, start with the part that's weighing on you the most.", loginTab: "Sign in", registerTab: "Create account", loginTitle: "Welcome back", loginDesc: "Your old conversations are still here.", loginId: "Username or email", password: "Password", remember: "Keep me signed in on this device", loginButton: "Enter chat", registerTitle: "Create your own corner", registerDesc: "Each account has its own history and memory.", displayName: "Display name", username: "Username", email: "Email", confirmPassword: "Confirm password", registerButton: "Create account" },
    needsLabel: "What do you need right now?",
    hearFromLabel: "Who do you want to hear from?",
    personalityLabel: "Your personality",
    categoryField: "Current topic",
    categories: { love: "Love", study: "Study", family: "Family", career: "Work & future", friends: "Friends", other: "Something else" },
    pronouns: { minh_ban: "Gentle", tao_may: "Close-friend" },
    modeTitles: { listen: "Just listening", clarify: "Think it through", advice: "Give direction" },
    modeCards: { listen: { title: "Listen", desc: "Tell me how you're feeling." }, clarify: { title: "Think together", desc: "Let's sort out what is really going on." }, advice: { title: "Next steps", desc: "Let's find a practical way forward." } },
    styleButtonDesc: "Soft or direct, depending on the moment",
    styles: { adaptive: { name: "Whatever fits today", description: "Let's see what you need today" }, strict: { name: "Tough one", description: "Direct, fair, no sugarcoating" }, gentle: { name: "Gentle one", description: "Soft, but still honest" }, rational: { name: "Rational one", description: "Facts before feelings" }, practical: { name: "Practical one", description: "Focus on what can be done next" }, light_humor: { name: "Light humor", description: "A little lighter, not careless" }, luyen: { name: "Luyện", description: "Give it a try" } },
    experiencesButton: "What you've been through",
    usageSuffix: "free messages",
    welcome: { eyebrow: "I'm here with you", title: "Tell me, what happened to you today?", starters: { love: { title: "Love", desc: "Someone is on my mind", message: "I'm a bit tangled up in a relationship issue." }, study: { title: "Study", desc: "Pressure, major, future", message: "Lately studying has been wearing me out." }, career: { title: "Work", desc: "Boss, coworkers, money", message: "I'm stuck on something related to work." }, family: { title: "Family", desc: "Parents, partner, children", message: "There's something going on in my family that I want to talk about." } } },
    placeholder: "Tell me what happened...",
    send: "Send",
    composerNote: "Shift + Enter for a new line",
    styleDialog: { eyebrow: "Choose who speaks", title: "Who do you want to hear from today?", copy: "The same story can sound very different depending on who responds.", optionDescriptions: { adaptive: "We'll adapt to the moment", strict: "Direct, fair, no sugarcoating", gentle: "Soft, but still honest", rational: "Facts before feelings", practical: "Focus on what can be done next", light_humor: "Lighter, but not careless", luyen: "Want to chat with me?" } },
    conversations: { eyebrow: "What you've been through", title: "Your past stories are still here", copy: "Open an old conversation to continue, or start a new one.", newButton: "New conversation", searchPlaceholder: "Search old conversations...", emptyTitle: "No saved conversations yet", emptyDesc: "Once you send your first message, it will appear here.", loading: "Loading past conversations...", untitled: "Conversation", emptyPreview: "No preview yet", today: "Today", yesterday: "Yesterday", rename: "Rename", delete: "Delete", deleteConfirm: "Delete “{title}”? This cannot be undone." },
    renameDialog: { eyebrow: "Rename", title: "Name this conversation", cancel: "Cancel", save: "Save" },
    account: { eyebrow: "Account", logout: "Log out" },
    profileCardDefaultName: "Not yet introduced",
    profileCardDefaultDesc: "20 quick personality questions",
    userMeta: "You",
    statuses: { saved: "Saved.", languageChanged: "Language updated.", safetyPriority: "I'm prioritizing your safety first.", thinking: "is thinking..." },
  },
  "zh-Hans": {
    brandTagline: "一个可以做自己的小角落。",
    auth: { kicker: "在这里，你不用假装自己没事", title: "有话就说吧。", desc: "这是一个私密的对话空间，会记得你的故事，也知道什么时候该倾听，什么时候该说得直接一点。", bubbleUser: "最近我很累，但不知道该跟谁说。", bubbleBot: "嗯，那就先从最让你心烦的那部分开始说。", loginTab: "登录", registerTab: "创建账号", loginTitle: "欢迎回来", loginDesc: "你以前的对话都还在。", loginId: "用户名或邮箱", password: "密码", remember: "在这台设备上保持登录", loginButton: "进入对话", registerTitle: "创建你的专属角落", registerDesc: "每个账号都有独立的记录与记忆。", displayName: "显示名称", username: "用户名", email: "邮箱", confirmPassword: "确认密码", registerButton: "创建账号" },
    needsLabel: "你现在最需要什么？",
    hearFromLabel: "你想听谁的回应？",
    personalityLabel: "你的性格",
    categoryField: "当前话题",
    categories: { love: "感情", study: "学习", family: "家庭", career: "工作与未来", friends: "朋友", other: "其他" },
    pronouns: { minh_ban: "温和模式", tao_may: "熟络模式" },
    modeTitles: { listen: "只倾听", clarify: "一起分析", advice: "给出方向" },
    modeCards: { listen: { title: "倾听", desc: "告诉我你现在是什么感觉。" }, clarify: { title: "一起分析", desc: "我们一起看看事情为什么会这样。" }, advice: { title: "找方向", desc: "一起找一个可行的处理办法。" } },
    styleButtonDesc: "柔和一点，或直接一点，都可以",
    styles: { adaptive: { name: "看情况来", description: "先看看你今天更需要什么" }, strict: { name: "严格型", description: "直接、公平、不拐弯" }, gentle: { name: "温和型", description: "柔和，但不敷衍" }, rational: { name: "理性型", description: "先看事实，再看情绪" }, practical: { name: "务实型", description: "先做最实际的下一步" }, light_humor: { name: "轻松一点", description: "稍微轻松，但不会乱开玩笑" }, luyen: { name: "Luyện", description: "来试试看" } },
    experiencesButton: "你经历过的事",
    usageSuffix: "免费消息",
    welcome: { eyebrow: "我在这里", title: "跟我说说，你今天遇到了什么事？", starters: { love: { title: "感情", desc: "有人让我想很多", message: "我最近被一段感情的事弄得有点乱。" }, study: { title: "学习", desc: "压力、专业、未来", message: "最近学习上的事让我很累。" }, career: { title: "工作", desc: "上司、同事、钱", message: "我有件和工作有关的事卡住了。" }, family: { title: "家庭", desc: "父母、伴侣、孩子", message: "我有件家里的事想说。" } } },
    placeholder: "跟我说说吧……",
    send: "发送",
    composerNote: "Shift + Enter 换行",
    styleDialog: { eyebrow: "选择聊天对象", title: "今天你想听谁的回应？", copy: "同一件事，不同的人会有不同的看法。", optionDescriptions: { adaptive: "会按当下情况调整", strict: "直接、公平、不拐弯", gentle: "温和，但不敷衍", rational: "先看事实，再看情绪", practical: "先做最实际的下一步", light_humor: "轻松一点，但不过火", luyen: "想和我聊聊吗？" } },
    conversations: { eyebrow: "你经历过的事", title: "以前的故事还在这里", copy: "打开旧对话继续聊，或者开始一个新的话题。", newButton: "新对话", searchPlaceholder: "搜索旧对话……", emptyTitle: "还没有保存的对话", emptyDesc: "当你发出第一条消息后，它就会出现在这里。", loading: "正在加载旧对话……", untitled: "对话", emptyPreview: "暂无预览", today: "今天", yesterday: "昨天", rename: "重命名", delete: "删除", deleteConfirm: "删除“{title}”？删除后无法恢复。" },
    renameDialog: { eyebrow: "重命名", title: "给这个对话取个名字", cancel: "取消", save: "保存" },
    account: { eyebrow: "账号", logout: "退出登录" },
    profileCardDefaultName: "还没认识你",
    profileCardDefaultDesc: "20 个简短的性格问题",
    userMeta: "你",
    statuses: { saved: "已保存。", languageChanged: "语言已切换。", safetyPriority: "我会先优先处理你的安全。", thinking: "正在思考……" },
  },
  "zh-Hant": {
    brandTagline: "一個可以做自己的小角落。",
    auth: { kicker: "在這裡，你不用假裝自己沒事", title: "有話就說吧。", desc: "這是一個私密的對話空間，會記得你的故事，也知道什麼時候該傾聽，什麼時候該說得直接一點。", bubbleUser: "最近我很累，但不知道該跟誰說。", bubbleBot: "嗯，那就先從最讓你煩的那部分開始說。", loginTab: "登入", registerTab: "建立帳號", loginTitle: "歡迎回來", loginDesc: "你以前的對話都還在。", loginId: "使用者名稱或電子郵件", password: "密碼", remember: "在這台裝置上保持登入", loginButton: "進入對話", registerTitle: "建立你的專屬角落", registerDesc: "每個帳號都有自己的記錄與記憶。", displayName: "顯示名稱", username: "使用者名稱", email: "電子郵件", confirmPassword: "確認密碼", registerButton: "建立帳號" },
    needsLabel: "你現在最需要什麼？",
    hearFromLabel: "你想聽誰的回應？",
    personalityLabel: "你的性格",
    categoryField: "目前主題",
    categories: { love: "感情", study: "學習", family: "家庭", career: "工作與未來", friends: "朋友", other: "其他" },
    pronouns: { minh_ban: "溫和模式", tao_may: "熟絡模式" },
    modeTitles: { listen: "只傾聽", clarify: "一起分析", advice: "給出方向" },
    modeCards: { listen: { title: "傾聽", desc: "告訴我你現在是什麼感覺。" }, clarify: { title: "一起分析", desc: "我們一起看看事情為什麼會這樣。" }, advice: { title: "找方向", desc: "一起找一個可行的處理辦法。" } },
    styleButtonDesc: "柔和一點，或直接一點，都可以",
    styles: { adaptive: { name: "看情況來", description: "先看看你今天更需要什麼" }, strict: { name: "嚴格型", description: "直接、公平、不拐彎" }, gentle: { name: "溫和型", description: "柔和，但不敷衍" }, rational: { name: "理性型", description: "先看事實，再看情緒" }, practical: { name: "務實型", description: "先做最實際的下一步" }, light_humor: { name: "輕鬆一點", description: "稍微輕鬆，但不會亂開玩笑" }, luyen: { name: "Luyện", description: "來試試看" } },
    experiencesButton: "你經歷過的事",
    usageSuffix: "免費訊息",
    welcome: { eyebrow: "我在這裡", title: "跟我說說，你今天遇到了什麼事？", starters: { love: { title: "感情", desc: "有人讓我想很多", message: "我最近被一段感情的事弄得有點亂。" }, study: { title: "學習", desc: "壓力、科系、未來", message: "最近學習上的事讓我很累。" }, career: { title: "工作", desc: "上司、同事、錢", message: "我有件和工作有關的事卡住了。" }, family: { title: "家庭", desc: "父母、伴侶、孩子", message: "我有件家裡的事想說。" } } },
    placeholder: "跟我說說吧……",
    send: "送出",
    composerNote: "Shift + Enter 換行",
    styleDialog: { eyebrow: "選擇聊天對象", title: "今天你想聽誰的回應？", copy: "同一件事，不同的人會有不同的看法。", optionDescriptions: { adaptive: "會按當下情況調整", strict: "直接、公平、不拐彎", gentle: "溫和，但不敷衍", rational: "先看事實，再看情緒", practical: "先做最實際的下一步", light_humor: "輕鬆一點，但不過火", luyen: "想和我聊聊嗎？" } },
    conversations: { eyebrow: "你經歷過的事", title: "以前的故事還在這裡", copy: "打開舊對話繼續聊，或開始新的話題。", newButton: "新對話", searchPlaceholder: "搜尋舊對話……", emptyTitle: "還沒有儲存的對話", emptyDesc: "當你送出第一則訊息後，它就會出現在這裡。", loading: "正在載入舊對話……", untitled: "對話", emptyPreview: "暫無預覽", today: "今天", yesterday: "昨天", rename: "重新命名", delete: "刪除", deleteConfirm: "刪除「{title}」？刪除後無法復原。" },
    renameDialog: { eyebrow: "重新命名", title: "幫這段對話取個名字", cancel: "取消", save: "儲存" },
    account: { eyebrow: "帳號", logout: "登出" },
    profileCardDefaultName: "還沒認識你",
    profileCardDefaultDesc: "20 個簡短的性格問題",
    userMeta: "你",
    statuses: { saved: "已儲存。", languageChanged: "語言已切換。", safetyPriority: "我會先優先處理你的安全。", thinking: "正在思考……" },
  },
};


const billingUiText = {
  vi: {
    sidebar: "Nạp lượt và gói tháng",
    topbar: "Nạp tiền",
    title: "Chọn gói phù hợp với bạn",
    eyebrow: "Lượt trò chuyện",
    balance: "Hiện có",
    topups: "Mua lượt",
    monthly: "Gói tháng",
    buy: "Thanh toán",
    popular: "Phổ biến",
    loading: "Đang tải bảng giá...",
    checkout: "Đang tạo mã thanh toán...",
    notConfigured: "Thanh toán chưa được bật trên server.",
    returnChecking: "Đang kiểm tra kết quả thanh toán...",
    paid: "Thanh toán thành công. Lượt đã được cộng vào tài khoản.",
    pending: "Ngân hàng đã chuyển trang về nhưng webhook chưa tới. Đang kiểm tra lại...",
    cancelled: "Bạn đã hủy thanh toán. Không có lượt nào bị trừ hoặc cộng.",
    remaining: "{n} lượt còn lại",
    unlimited: "Gói không giới hạn đang hoạt động",
    permanentTest: "Tài khoản test không giới hạn",
    quotaParts: "Hôm nay {daily} · Chào mừng {welcome} · Đã mua {paid}",
  },
  en: {
    sidebar: "Messages & monthly plans", topbar: "Top up", title: "Choose a plan", eyebrow: "Chat messages",
    balance: "Available", topups: "Message packs", monthly: "Monthly plans", buy: "Pay now",
    popular: "Popular", loading: "Loading plans...", checkout: "Creating checkout...",
    notConfigured: "Payments are not enabled on this server.", returnChecking: "Checking payment...",
    paid: "Payment confirmed. Your balance has been updated.", pending: "Waiting for payment confirmation...",
    cancelled: "Payment cancelled.", remaining: "{n} messages left", unlimited: "Unlimited plan active",
    permanentTest: "Unlimited test account",
    quotaParts: "Today {daily} · Welcome {welcome} · Purchased {paid}",
  },
  "zh-Hans": {
    sidebar: "购买消息与月卡", topbar: "充值", title: "选择适合你的方案", eyebrow: "聊天消息",
    balance: "当前可用", topups: "购买次数", monthly: "月度方案", buy: "去付款",
    popular: "热门", loading: "正在加载价格...", checkout: "正在创建付款链接...",
    notConfigured: "服务器尚未启用付款。", returnChecking: "正在确认付款结果...",
    paid: "付款成功，次数已到账。", pending: "正在等待付款确认...", cancelled: "已取消付款。",
    remaining: "剩余 {n} 次", unlimited: "无限方案生效中",
    permanentTest: "永久测试账号",
    quotaParts: "今日 {daily} · 新人 {welcome} · 已购买 {paid}",
  },
  "zh-Hant": {
    sidebar: "購買訊息與月卡", topbar: "儲值", title: "選擇適合你的方案", eyebrow: "聊天訊息",
    balance: "目前可用", topups: "購買次數", monthly: "月度方案", buy: "前往付款",
    popular: "熱門", loading: "正在載入價格...", checkout: "正在建立付款連結...",
    notConfigured: "伺服器尚未啟用付款。", returnChecking: "正在確認付款結果...",
    paid: "付款成功，次數已入帳。", pending: "正在等待付款確認...", cancelled: "已取消付款。",
    remaining: "剩餘 {n} 次", unlimited: "無限方案生效中",
    permanentTest: "永久測試帳號",
    quotaParts: "今日 {daily} · 新人 {welcome} · 已購買 {paid}",
  },
};

const responseStyles = {
  adaptive: { icon: "icon-shuffle" },
  strict: { icon: "icon-strict" },
  gentle: { icon: "icon-leaf" },
  rational: { icon: "icon-scale" },
  practical: { icon: "icon-tool" },
  light_humor: { icon: "icon-smile" },
  luyen: { icon: "icon-spark" },
};

const traitLabels = {
  extraversion: "Hướng ngoại",
  agreeableness: "Dễ đồng cảm",
  conscientiousness: "Kỷ luật",
  emotional_stability: "Điềm tĩnh",
  openness: "Cởi mở",
};

const state = {
  userId: null,
  account: null,
  mode: localStorage.getItem("oday_mode") || "listen",
  category: localStorage.getItem("oday_category") || "other",
  pronounStyle: localStorage.getItem("oday_pronoun") || "minh_ban",
  language: localStorage.getItem("oday_language") || "vi",
  responseStyle: localStorage.getItem("oday_response_style") || "luyen",
  toneStyle: localStorage.getItem("oday_tone_style") || "gentle",
  usedTotal: 0,
  freeLimit: window.APP_CONFIG?.freeMessageLimit || 10,
  quota: null,
  paymentConfigured: false,
  pricing: null,
  billingTab: "topups",
  currentConversationId: null,
  currentConversationTitle: "",
  conversations: [],
  renameConversationId: null,
  profile: null,
  profileCompleted: false,
  profileSchema: null,
  profileStep: 1,
  quizIndex: 0,
  isSending: false,
};

const els = {
  authView: document.getElementById("authView"),
  appView: document.getElementById("appView"),
  loginForm: document.getElementById("loginForm"),
  registerForm: document.getElementById("registerForm"),
  loginStatus: document.getElementById("loginStatus"),
  registerStatus: document.getElementById("registerStatus"),
  sidebar: document.getElementById("sidebar"),
  sidebarScrim: document.getElementById("sidebarScrim"),
  menu: document.getElementById("menuButton"),
  modeTitle: document.getElementById("modeTitle"),
  activeStyleText: document.getElementById("activeStyleText"),
  topbarPersonaIcon: document.getElementById("topbarPersonaIcon"),
  category: document.getElementById("categorySelect"),
  pronoun: document.getElementById("pronounSelect"),
  language: document.getElementById("languageSelect"),
  tone: document.getElementById("toneSelect"),
  form: document.getElementById("chatForm"),
  input: document.getElementById("messageInput"),
  send: document.getElementById("sendButton"),
  messages: document.getElementById("messages"),
  welcome: document.getElementById("welcomeCard"),
  status: document.getElementById("statusLine"),
  usage: document.getElementById("usageText"),
  billingButton: document.getElementById("billingButton"),
  topbarBillingButton: document.getElementById("topbarBillingButton"),
  billingDialog: document.getElementById("billingDialog"),
  closeBillingButton: document.getElementById("closeBillingButton"),
  billingBalanceText: document.getElementById("billingBalanceText"),
  billingTopupPlans: document.getElementById("billingTopupPlans"),
  billingMonthlyPlans: document.getElementById("billingMonthlyPlans"),
  billingNotes: document.getElementById("billingNotes"),
  billingStatus: document.getElementById("billingStatus"),
  stylePickerButton: document.getElementById("stylePickerButton"),
  selectedStyleIcon: document.getElementById("selectedStyleIcon"),
  selectedStyleName: document.getElementById("selectedStyleName"),
  selectedStyleDescription: document.getElementById("selectedStyleDescription"),
  styleDialog: document.getElementById("styleDialog"),
  conversationsDialog: document.getElementById("conversationsDialog"),
  closeConversationsButton: document.getElementById("closeConversationsButton"),
  newConversationButton: document.getElementById("newConversationButton"),
  conversationSearchInput: document.getElementById("conversationSearchInput"),
  conversationList: document.getElementById("conversationList"),
  conversationEmpty: document.getElementById("conversationEmpty"),
  renameConversationDialog: document.getElementById("renameConversationDialog"),
  renameConversationInput: document.getElementById("renameConversationInput"),
  closeRenameConversationButton: document.getElementById(
    "closeRenameConversationButton",
  ),
  cancelRenameConversationButton: document.getElementById(
    "cancelRenameConversationButton",
  ),
  saveRenameConversationButton: document.getElementById(
    "saveRenameConversationButton",
  ),
  profileDialog: document.getElementById("profileDialog"),
  profileButton: document.getElementById("profileButton"),
  desktopProfileButton: document.getElementById("desktopProfileButton"),
  closeProfileButton: document.getElementById("closeProfileButton"),
  profileBackButton: document.getElementById("profileBackButton"),
  profileNextButton: document.getElementById("profileNextButton"),
  profileError: document.getElementById("profileError"),
  profileQuestionList: document.getElementById("profileQuestionList"),
  quizProgressText: document.getElementById("quizProgressText"),
  quizProgressFill: document.getElementById("quizProgressFill"),
  profileAgeGroup: document.getElementById("profileAgeGroup"),
  profileLifeStage: document.getElementById("profileLifeStage"),
  profileGender: document.getElementById("profileGender"),
  profileGenderNote: document.getElementById("profileGenderNote"),
  genderNoteField: document.getElementById("genderNoteField"),
  profileRelationshipStatus: document.getElementById(
    "profileRelationshipStatus",
  ),
  profileChildrenStatus: document.getElementById("profileChildrenStatus"),
  profileLivingContext: document.getElementById("profileLivingContext"),
  profileResultName: document.getElementById("profileResultName"),
  profileResultDescription: document.getElementById("profileResultDescription"),
  profileScoreList: document.getElementById("profileScoreList"),
  profileArchetypeName: document.getElementById("profileArchetypeName"),
  profileArchetypeDescription: document.getElementById(
    "profileArchetypeDescription",
  ),
  accountButton: document.getElementById("accountButton"),
  accountDialog: document.getElementById("accountDialog"),
  closeAccountButton: document.getElementById("closeAccountButton"),
  logoutButton: document.getElementById("logoutButton"),
  accountInitial: document.getElementById("accountInitial"),
  accountInitialLarge: document.getElementById("accountInitialLarge"),
  accountDisplayName: document.getElementById("accountDisplayName"),
  accountUsername: document.getElementById("accountUsername"),
  accountEmail: document.getElementById("accountEmail"),
  accountBillingButton: document.getElementById("accountBillingButton"),
  accountQuotaText: document.getElementById("accountQuotaText"),
};


function localeText() {
  return uiText[state.language] || uiText.vi;
}

function billingText() {
  return billingUiText[state.language] || billingUiText.vi;
}

function toneOptions() {
  return TONE_OPTIONS[state.language] || TONE_OPTIONS.vi;
}

function toneLabel(value = state.toneStyle) {
  return toneOptions().find((item) => item.value === value)?.label || value;
}

function pickText(value) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    if (state.language === "vi") return value[state.pronounStyle] || value.minh_ban || value.tao_may || "";
    return value.default || value.minh_ban || value.tao_may || Object.values(value)[0] || "";
  }
  return value || "";
}

function styleMeta(styleKey) {
  const local = localeText();
  const fallback = uiText.vi.styles[styleKey] || { name: styleKey, description: "" };
  return {
    name: local.styles?.[styleKey]?.name || fallback.name,
    description: local.styles?.[styleKey]?.description || fallback.description,
    icon: responseStyles[styleKey]?.icon || "icon-shuffle",
  };
}

function modeMeta(modeKey) {
  const local = localeText();
  const item = local.modeCards?.[modeKey] || uiText.vi.modeCards[modeKey];
  return {
    title: item?.title || modeKey,
    desc: pickText(item?.desc),
    topbar: local.modeTitles?.[modeKey] || uiText.vi.modeTitles[modeKey] || modeKey,
  };
}

function userMetaLabel() {
  const local = localeText();
  const value = local.userMeta;
  if (typeof value === "string") return value;
  return pickText(value) || "You";
}

function setText(selector, text) {
  const el = typeof selector === "string" ? document.querySelector(selector) : selector;
  if (el) el.textContent = text;
}

function setPlaceholder(selector, text) {
  const el = typeof selector === "string" ? document.querySelector(selector) : selector;
  if (el) el.placeholder = text;
}

function fillSimpleSelect(select, options, currentValue) {
  if (!select) return;
  const keep = String(currentValue || "");
  select.replaceChildren();
  options.forEach(({ value, label }) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
  select.value = keep;
}

function applyUIText() {
  const t = localeText();
  document.documentElement.lang = state.language;
  setText('#sidebarBrandTagline', t.brandTagline || window.APP_CONFIG.brandTagline);
  setText('#authBrandTagline', t.brandTagline || window.APP_CONFIG.brandTagline);

  setText('.auth-kicker', t.auth.kicker);
  setText('.auth-copy h1', t.auth.title);
  setText('.auth-copy p:last-of-type', t.auth.desc);
  const authBubbles = document.querySelectorAll('.auth-bubble');
  if (authBubbles[0]) authBubbles[0].textContent = t.auth.bubbleUser;
  if (authBubbles[1]) authBubbles[1].textContent = t.auth.bubbleBot;
  const authTabs = document.querySelectorAll('[data-auth-tab]');
  if (authTabs[0]) authTabs[0].textContent = t.auth.loginTab;
  if (authTabs[1]) authTabs[1].textContent = t.auth.registerTab;
  setText('#loginForm .auth-form-heading h2', t.auth.loginTitle);
  setText('#loginForm .auth-form-heading p', t.auth.loginDesc);
  setText('#registerForm .auth-form-heading h2', t.auth.registerTitle);
  setText('#registerForm .auth-form-heading p', t.auth.registerDesc);
  setText('#loginForm label:nth-of-type(1) span', t.auth.loginId);
  setText('#loginForm label:nth-of-type(2) span', t.auth.password);
  setText('#loginForm .remember-row span', t.auth.remember);
  setText('#loginForm button[type="submit"]', t.auth.loginButton);
  setText('#registerForm .auth-two-columns label:nth-of-type(1) span', t.auth.displayName);
  setText('#registerForm .auth-two-columns label:nth-of-type(2) span', t.auth.username);
  setText('#registerForm > label span', t.auth.email);
  const registerPwSpans = document.querySelectorAll('#registerForm .auth-two-columns:last-of-type label span');
  if (registerPwSpans[0]) registerPwSpans[0].textContent = t.auth.password;
  if (registerPwSpans[1]) registerPwSpans[1].textContent = t.auth.confirmPassword;
  setText('#registerForm .remember-row span', t.auth.remember);
  setText('#registerForm button[type="submit"]', t.auth.registerButton);

  const sectionLabels = document.querySelectorAll('.panel-section .section-label');
  if (sectionLabels[0]) sectionLabels[0].textContent = pickText(t.needsLabel);
  if (sectionLabels[1]) sectionLabels[1].textContent = pickText(t.hearFromLabel);
  if (sectionLabels[2]) sectionLabels[2].textContent = pickText(t.personalityLabel);
  setText('#categoryFieldLabel', t.categoryField);

  fillSimpleSelect(els.language, SUPPORTED_LANGUAGES.map((item) => ({ value: item.value, label: item.label })), state.language);
  fillSimpleSelect(els.tone, toneOptions(), state.toneStyle);
  fillSimpleSelect(els.pronoun, [
    { value: 'minh_ban', label: t.pronouns.minh_ban },
    { value: 'tao_may', label: t.pronouns.tao_may },
  ], state.pronounStyle);
  fillSimpleSelect(els.category, Object.entries(t.categories).map(([value, label]) => ({ value, label })), state.category);

  document.querySelectorAll('[data-mode]').forEach((button) => {
    const info = modeMeta(button.dataset.mode);
    const strong = button.querySelector('strong');
    const small = button.querySelector('small');
    if (strong) strong.textContent = info.title;
    if (small) small.textContent = info.desc;
  });

  setText('#usageSuffix', t.usageSuffix);
  setText('#modeTitle', modeMeta(state.mode).topbar);
  const currentStyle = styleMeta(state.responseStyle);
  setText('#activeStyleText', currentStyle.name);
  setText('#selectedStyleName', currentStyle.name);
  setText('#selectedStyleDescription', currentStyle.description || t.styleButtonDesc);
  setText('#styleDialog .dialog-header .eyebrow', t.styleDialog.eyebrow);
  setText('#styleDialog .dialog-header h3', pickText(t.styleDialog.title));
  setText('#styleDialog .dialog-copy', t.styleDialog.copy);
  document.querySelectorAll('[data-response-style]').forEach((button) => {
    const key = button.dataset.responseStyle;
    const meta = styleMeta(key);
    const strong = button.querySelector('strong');
    const small = button.querySelector('small');
    if (strong) strong.textContent = meta.name;
    if (small) small.textContent = t.styleDialog.optionDescriptions[key] || meta.description;
  });

  setText('#experiencesButton span', pickText(t.experiencesButton));
  const bt = billingText();
  setText('#billingButton span', bt.sidebar);
  setText('#topbarBillingButton span', bt.topbar);
  if (els.topbarBillingButton) els.topbarBillingButton.setAttribute('aria-label', bt.topbar);
  setText('#billingEyebrow', bt.eyebrow);
  setText('#billingTitle', bt.title);
  const billingTabs = document.querySelectorAll('[data-billing-tab]');
  if (billingTabs[0]) billingTabs[0].textContent = bt.topups;
  if (billingTabs[1]) billingTabs[1].textContent = bt.monthly;
  if (!state.profileCompleted || !state.profile) {
    els.profileArchetypeName.textContent = t.profileCardDefaultName;
    els.profileArchetypeDescription.textContent = t.profileCardDefaultDesc;
  }

  setText('#welcomeCard .eyebrow', pickText(t.welcome.eyebrow));
  setText('#welcomeCard h3', pickText(t.welcome.title));
  const starterButtons = document.querySelectorAll('.starter-grid button');
  const starterKeys = ['love', 'study', 'career', 'family'];
  starterButtons.forEach((button, index) => {
    const key = starterKeys[index];
    const data = t.welcome.starters[key];
    if (!data) return;
    button.dataset.starter = pickText(data.message);
    button.dataset.category = key;
    const strong = button.querySelector('strong');
    const small = button.querySelector('small');
    if (strong) strong.textContent = data.title;
    if (small) small.textContent = data.desc;
  });

  setPlaceholder(els.input, pickText(t.placeholder));
  setText('#sendButtonText', t.send);
  setText('#composerNote', t.composerNote);

  setText('#conversationsDialog .dialog-header .eyebrow', t.conversations.eyebrow);
  setText('#conversationsDialog .dialog-header h3', t.conversations.title);
  setText('#conversationsDialog .dialog-copy', t.conversations.copy);
  setText('#newConversationButton span', t.conversations.newButton);
  setPlaceholder('#conversationSearchInput', t.conversations.searchPlaceholder);
  setText('#conversationEmpty strong', t.conversations.emptyTitle);
  setText('#conversationEmpty p', t.conversations.emptyDesc);
  setText('#renameConversationDialog .dialog-header .eyebrow', t.renameDialog.eyebrow);
  setText('#renameConversationDialog .dialog-header h3', t.renameDialog.title);
  setText('#cancelRenameConversationButton', t.renameDialog.cancel);
  setText('#saveRenameConversationButton', t.renameDialog.save);
  setText('#accountDialog .dialog-header .eyebrow', t.account.eyebrow);
  setText('#logoutButton', t.account.logout);

  // applyUIText có thể chạy sau khi quota/bảng giá đã tải. Vẽ lại để bản dịch
  // không ghi đè số lượt còn lại hoặc nội dung gói hiện tại.
  if (state.quota) updateUsage(state.usedTotal, state.freeLimit, state.quota);
  if (state.pricing) renderBillingPlans();
}

async function init() {
  normalizeSavedState();
  bindAuthEvents();
  applyUIText();
  const auth = await api("/api/auth/status");
  if (!auth.authenticated) {
    showAuth();
    return;
  }
  state.account = auth.account;
  state.userId = auth.account.user_id;
  await startApp();
}

async function startApp() {
  normalizeSavedState();
  bindAppEvents();
  showApp();
  applySavedControls();
  renderAccount();
  await loadProfileSchema();
  await openSession();
  startNewConversation(false);
  await handlePaymentReturn();
  if (!state.profileCompleted) setTimeout(() => openProfile(true), 500);
  if ("serviceWorker" in navigator && window.isSecureContext) {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  }
}

function showAuth() {
  els.authView.hidden = false;
  els.appView.hidden = true;
  document.body.classList.add("auth-mode");
}

function showApp() {
  els.authView.hidden = true;
  els.appView.hidden = false;
  document.body.classList.remove("auth-mode");
}

function bindAuthEvents() {
  document.querySelectorAll("[data-auth-tab]").forEach((button) => {
    button.addEventListener("click", () => setAuthTab(button.dataset.authTab));
  });

  els.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = els.loginForm.querySelector("button[type='submit']");
    setAuthStatus(els.loginStatus, "");
    setBusy(button, true, "Đang vào...");
    try {
      await api("/api/auth/login", {
        method: "POST",
        body: {
          identifier: document.getElementById("loginIdentifier").value.trim(),
          password: document.getElementById("loginPassword").value,
          remember: document.getElementById("loginRemember").checked,
        },
      });
      window.location.reload();
    } catch (error) {
      setAuthStatus(els.loginStatus, error.message, true);
      setBusy(button, false, "Vào trò chuyện");
    }
  });

  els.registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = els.registerForm.querySelector("button[type='submit']");
    const password = document.getElementById("registerPassword").value;
    const confirm = document.getElementById("registerPasswordConfirm").value;
    setAuthStatus(els.registerStatus, "");
    if (password !== confirm) {
      setAuthStatus(els.registerStatus, "Hai mật khẩu chưa giống nhau.", true);
      return;
    }
    setBusy(button, true, "Đang tạo...");
    try {
      await api("/api/auth/register", {
        method: "POST",
        body: {
          display_name: document
            .getElementById("registerDisplayName")
            .value.trim(),
          username: document.getElementById("registerUsername").value.trim(),
          email: document.getElementById("registerEmail").value.trim(),
          password,
          remember: document.getElementById("registerRemember").checked,
        },
      });
      window.location.reload();
    } catch (error) {
      setAuthStatus(els.registerStatus, error.message, true);
      setBusy(button, false, "Tạo tài khoản");
    }
  });
}

function setAuthTab(tab) {
  document.querySelectorAll("[data-auth-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.authTab === tab);
  });
  document.querySelectorAll("[data-auth-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.authPanel === tab);
  });
}

function setAuthStatus(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle("error", isError);
}

function setBusy(button, busy, text) {
  button.disabled = busy;
  button.textContent = text;
}

function normalizeSavedState() {
  if (!uiText.vi.modeTitles[state.mode]) {
    state.mode = "listen";
    localStorage.setItem("oday_mode", state.mode);
  }
  if (!responseStyles[state.responseStyle]) {
    state.responseStyle = "luyen";
  }
  localStorage.setItem("oday_response_style", state.responseStyle);
  localStorage.setItem("oday_tone_style", state.toneStyle);
  if (!TONE_OPTIONS.vi.some((item) => item.value === state.toneStyle)) {
    state.toneStyle = "gentle";
    localStorage.setItem("oday_tone_style", state.toneStyle);
  }
  if (!SUPPORTED_LANGUAGES.some((item) => item.value === state.language)) {
    state.language = "vi";
    localStorage.setItem("oday_language", state.language);
  }
}

function setIcon(svg, symbolId) {
  if (!svg) return;
  let use = svg.querySelector("use");
  if (!use) {
    use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    svg.replaceChildren(use);
  }
  use.setAttribute("href", `#${symbolId}`);
}

function makeIcon(symbolId) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#${symbolId}`);
  svg.appendChild(use);
  return svg;
}

function applySavedControls() {
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state.mode);
  });
  document.querySelectorAll("[data-response-style]").forEach((button) => {
    button.classList.toggle(
      "active",
      button.dataset.responseStyle === state.responseStyle,
    );
  });
  const style = styleMeta(state.responseStyle);
  document.body.dataset.persona = state.responseStyle;
  document.body.dataset.tone = state.toneStyle;
  setIcon(els.selectedStyleIcon, style.icon);
  setIcon(els.topbarPersonaIcon, style.icon);
  applyUIText();
  updateProfileCard();
}

let appEventsBound = false;
function bindAppEvents() {
  if (appEventsBound) return;
  appEventsBound = true;

  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      state.mode = button.dataset.mode;
      localStorage.setItem("oday_mode", state.mode);
      applySavedControls();
      closeSidebar();
      els.input.focus();
    });
  });

  els.stylePickerButton.addEventListener("click", () =>
    openDialog(els.styleDialog),
  );
  document.querySelectorAll("[data-response-style]").forEach((button) => {
    button.addEventListener("click", async () => {
      const selected = button.dataset.responseStyle;
      if (!responseStyles[selected]) return;
      state.responseStyle = selected;
      localStorage.setItem("oday_response_style", state.responseStyle);
      applySavedControls();
      closeDialog(els.styleDialog);
      await saveSettings(`${localeText().statuses.saved} ${styleMeta(selected).name}.`);
      els.input.focus();
    });
  });

  document.querySelectorAll("[data-starter]").forEach((button) => {
    button.addEventListener("click", () => {
      els.input.value = button.dataset.starter;

      if (button.dataset.category) {
        state.category = button.dataset.category;
        els.category.value = state.category;
        localStorage.setItem("oday_category", state.category);
      }

      resizeInput();
      els.input.focus();
    });
  });

  els.category.addEventListener("change", () => {
    state.category = els.category.value;
    localStorage.setItem("oday_category", state.category);
  });
  els.pronoun.addEventListener("change", async () => {
    state.pronounStyle = els.pronoun.value;
    localStorage.setItem("oday_pronoun", state.pronounStyle);
    applySavedControls();
    await saveSettings();
  });
  els.tone.addEventListener("change", async () => {
    state.toneStyle = els.tone.value;
    localStorage.setItem("oday_tone_style", state.toneStyle);
    applySavedControls();
    await saveSettings(`${localeText().statuses.saved} ${toneLabel()}.`);
  });
  els.language.addEventListener("change", () => {
    state.language = els.language.value;
    localStorage.setItem("oday_language", state.language);
    applySavedControls();
    setStatus(localeText().statuses.languageChanged);
    setTimeout(() => setStatus(""), 1400);
  });

  els.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await sendMessage();
  });
  els.input.addEventListener("input", resizeInput);
  els.input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      els.form.requestSubmit();
    }
  });

  els.menu.addEventListener("click", toggleSidebar);
  els.sidebarScrim.addEventListener("click", closeSidebar);
  document
    .getElementById("experiencesButton")
    .addEventListener("click", openConversations);
  document
    .getElementById("desktopExperiencesButton")
    .addEventListener("click", openConversations);
  els.billingButton.addEventListener("click", openBilling);
  els.topbarBillingButton?.addEventListener("click", openBilling);
  els.accountBillingButton.addEventListener("click", async () => {
    closeDialog(els.accountDialog);
    await openBilling();
  });
  els.closeBillingButton.addEventListener("click", () => closeDialog(els.billingDialog));
  document.querySelectorAll("[data-billing-tab]").forEach((button) => {
    button.addEventListener("click", () => selectBillingTab(button.dataset.billingTab));
  });
  els.closeConversationsButton.addEventListener("click", () =>
    closeDialog(els.conversationsDialog),
  );
  els.newConversationButton.addEventListener("click", () =>
    startNewConversation(true),
  );
  els.conversationSearchInput.addEventListener("input", () =>
    renderConversationList(els.conversationSearchInput.value),
  );
  els.closeRenameConversationButton.addEventListener(
    "click",
    closeRenameConversation,
  );
  els.cancelRenameConversationButton.addEventListener(
    "click",
    closeRenameConversation,
  );
  els.saveRenameConversationButton.addEventListener(
    "click",
    saveConversationRename,
  );
  els.renameConversationInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      saveConversationRename();
    }
  });

  els.profileButton.addEventListener("click", () => openProfile(false));
  els.desktopProfileButton.addEventListener("click", () => openProfile(false));
  els.closeProfileButton.addEventListener("click", () =>
    closeDialog(els.profileDialog),
  );
  els.profileBackButton.addEventListener("click", profileBack);
  els.profileNextButton.addEventListener("click", profileNext);
  els.profileGender.addEventListener("change", toggleGenderNote);

  els.accountButton.addEventListener("click", () =>
    openDialog(els.accountDialog),
  );
  els.closeAccountButton.addEventListener("click", () =>
    closeDialog(els.accountDialog),
  );
  els.logoutButton.addEventListener("click", async () => {
    els.logoutButton.disabled = true;
    try {
      await api("/api/auth/logout", { method: "POST" });
      window.location.reload();
    } finally {
      els.logoutButton.disabled = false;
    }
  });
}

function toggleSidebar() {
  els.sidebar.classList.toggle("open");
  els.sidebarScrim.classList.toggle(
    "visible",
    els.sidebar.classList.contains("open"),
  );
}
function closeSidebar() {
  els.sidebar.classList.remove("open");
  els.sidebarScrim.classList.remove("visible");
}

function openDialog(dialog) {
  if (!dialog) return;
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}
function closeDialog(dialog) {
  if (!dialog) return;
  if (typeof dialog.close === "function") dialog.close();
  else dialog.removeAttribute("open");
}

function renderAccount() {
  const account = state.account || {};
  const displayName = account.display_name || userMetaLabel();
  const initial = displayName.trim().charAt(0).toUpperCase() || "B";
  els.accountInitial.textContent = initial;
  els.accountInitialLarge.textContent = initial;
  els.accountDisplayName.textContent = displayName;
  els.accountUsername.textContent = account.username
    ? `@${account.username}`
    : "";
  els.accountEmail.textContent = account.email || "";
}

async function loadProfileSchema() {
  state.profileSchema = await api("/api/profile-schema");
  populateProfileSelects();
  renderQuestionnaire();
}

function populateProfileSelects() {
  const options = state.profileSchema.options;
  fillSelect(els.profileAgeGroup, options.age_group);
  fillSelect(els.profileLifeStage, options.life_stage);
  fillSelect(els.profileGender, options.gender);
  fillSelect(els.profileRelationshipStatus, options.relationship_status);
  fillSelect(els.profileChildrenStatus, options.children_status);
  fillSelect(els.profileLivingContext, options.living_context);
}

function fillSelect(select, values) {
  select.replaceChildren();
  Object.entries(values).forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
}

function renderQuestionnaire() {
  els.profileQuestionList.replaceChildren();
  state.profileSchema.questionnaire.forEach((question, index) => {
    const fieldset = document.createElement("fieldset");
    fieldset.className = "profile-question";
    fieldset.dataset.questionIndex = String(index);
    const legend = document.createElement("legend");
    legend.textContent = question.text;
    fieldset.appendChild(legend);
    const options = document.createElement("div");
    options.className = "question-options";
    question.options.forEach((option) => {
      const label = document.createElement("label");
      label.className = "question-option";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = `profile_${question.id}`;
      input.value = option.id;
      input.addEventListener("change", clearProfileError);
      const text = document.createElement("span");
      text.textContent = option.label;
      label.append(input, text);
      options.appendChild(label);
    });
    fieldset.appendChild(options);
    els.profileQuestionList.appendChild(fieldset);
  });
  updateQuizView();
}

async function openSession() {
  const data = await api("/api/session", { method: "POST" });
  state.userId = data.user.id;
  state.account = data.account || state.account;
  state.pronounStyle = data.user.pronoun_style || state.pronounStyle;
  state.responseStyle = data.user.response_style || state.responseStyle;
  state.toneStyle = data.user.tone_style || state.toneStyle;
  state.profile = data.user.profile || null;
  state.profileCompleted = Boolean(data.user.profile_completed);
  normalizeSavedState();
  localStorage.setItem("oday_pronoun", state.pronounStyle);
  localStorage.setItem("oday_response_style", state.responseStyle);
  localStorage.setItem("oday_tone_style", state.toneStyle);
  applySavedControls();
  renderAccount();
  state.paymentConfigured = Boolean(data.payment_configured);
  updateUsage(data.used_total, data.free_limit, data.quota);
}

function clearRenderedMessages() {
  els.messages.querySelectorAll(".message-row").forEach((row) => row.remove());
}

function startNewConversation(closePanels = true) {
  state.currentConversationId = null;
  state.currentConversationTitle = "";
  clearRenderedMessages();
  if (els.welcome) els.welcome.hidden = false;
  els.input.value = "";
  resizeInput();
  setStatus("");
  if (closePanels) {
    closeDialog(els.conversationsDialog);
    closeSidebar();
  }
  setTimeout(() => els.input.focus(), 30);
}

async function openConversations() {
  closeSidebar();
  els.conversationSearchInput.value = "";
  openDialog(els.conversationsDialog);
  await loadConversations();
}

async function loadConversations() {
  els.conversationList.innerHTML =
    `<div class="conversation-loading">${escapeHtml(localeText().conversations.loading)}</div>`;
  els.conversationEmpty.hidden = true;
  try {
    const data = await api("/api/conversations");
    state.conversations = data.conversations || [];
    renderConversationList("");
  } catch (error) {
    els.conversationList.innerHTML = `<div class="conversation-loading error">${escapeHtml(error.message)}</div>`;
  }
}

function renderConversationList(searchText = "") {
  const query = String(searchText || "")
    .trim()
    .toLowerCase();
  const items = state.conversations.filter((conversation) => {
    if (!query) return true;
    return (
      String(conversation.title || "")
        .toLowerCase()
        .includes(query) ||
      String(conversation.preview || "")
        .toLowerCase()
        .includes(query)
    );
  });
  els.conversationList.replaceChildren();
  els.conversationEmpty.hidden = items.length > 0;
  if (!items.length) return;

  items.forEach((conversation) => {
    const item = document.createElement("article");
    item.className = "conversation-item";
    if (conversation.id === state.currentConversationId)
      item.classList.add("active");

    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "conversation-open-button";
    openButton.addEventListener("click", () =>
      loadConversation(conversation.id),
    );

    const copy = document.createElement("span");
    copy.className = "conversation-item-copy";
    const t = localeText();
    const title = document.createElement("strong");
    title.textContent = conversation.title || t.conversations.untitled;
    const preview = document.createElement("small");
    preview.textContent = conversation.preview || t.conversations.emptyPreview;
    const time = document.createElement("time");
    time.dateTime = conversation.updated_at || "";
    time.textContent = formatConversationTime(conversation.updated_at);
    copy.append(title, preview, time);
    openButton.appendChild(copy);

    const menuWrap = document.createElement("div");
    menuWrap.className = "conversation-menu-wrap";
    const menuButton = document.createElement("button");
    menuButton.type = "button";
    menuButton.className = "conversation-menu-button";
    menuButton.setAttribute("aria-label", localeText().conversations.rename);
    menuButton.appendChild(makeIcon("icon-more"));
    const menu = document.createElement("div");
    menu.className = "conversation-item-menu";
    menu.hidden = true;

    const renameButton = document.createElement("button");
    renameButton.type = "button";
    renameButton.append(
      makeIcon("icon-edit"),
      document.createTextNode(localeText().conversations.rename),
    );
    renameButton.addEventListener("click", () =>
      openRenameConversation(conversation),
    );

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "danger";
    deleteButton.append(makeIcon("icon-trash"), document.createTextNode(localeText().conversations.delete));
    deleteButton.addEventListener("click", () =>
      deleteConversationItem(conversation),
    );

    menu.append(renameButton, deleteButton);
    menuButton.addEventListener("click", (event) => {
      event.stopPropagation();
      const willOpen = menu.hidden;
      document.querySelectorAll(".conversation-item-menu").forEach((other) => {
        if (other !== menu) other.hidden = true;
      });
      document.querySelectorAll(".conversation-item.menu-open").forEach((otherItem) => {
        if (otherItem !== item) otherItem.classList.remove("menu-open");
      });
      menu.hidden = !willOpen;
      item.classList.toggle("menu-open", willOpen);
    });
    menuWrap.append(menuButton, menu);
    item.append(openButton, menuWrap);
    els.conversationList.appendChild(item);
  });
}

async function loadConversation(conversationId) {
  setStatus("Đang mở lại câu chuyện...");
  try {
    const data = await api(
      `/api/conversations/${encodeURIComponent(conversationId)}`,
    );
    state.currentConversationId = data.conversation.id;
    state.currentConversationTitle = data.conversation.title || "";
    clearRenderedMessages();
    if (els.welcome) els.welcome.hidden = true;
    (data.messages || []).forEach((message) =>
      renderMessage(
        message.role,
        message.content,
        false,
        message.response_style || state.responseStyle,
      ),
    );
    closeDialog(els.conversationsDialog);
    closeSidebar();
    setStatus("");
    scrollToBottom();
    els.input.focus();
  } catch (error) {
    setStatus(error.message, true);
  }
}

function openRenameConversation(conversation) {
  state.renameConversationId = conversation.id;
  els.renameConversationInput.value = conversation.title || "";
  document.querySelectorAll(".conversation-item-menu").forEach((menu) => {
    menu.hidden = true;
  });
  document.querySelectorAll(".conversation-item.menu-open").forEach((item) => {
    item.classList.remove("menu-open");
  });
  openDialog(els.renameConversationDialog);
  setTimeout(() => {
    els.renameConversationInput.focus();
    els.renameConversationInput.select();
  }, 30);
}

function closeRenameConversation() {
  state.renameConversationId = null;
  closeDialog(els.renameConversationDialog);
}

async function saveConversationRename() {
  const conversationId = state.renameConversationId;
  const title = els.renameConversationInput.value.trim();
  if (!conversationId || !title) return;
  els.saveRenameConversationButton.disabled = true;
  try {
    const data = await api(
      `/api/conversations/${encodeURIComponent(conversationId)}`,
      {
        method: "PATCH",
        body: { title },
      },
    );
    state.conversations = state.conversations.map((item) =>
      item.id === conversationId ? { ...item, ...data.conversation } : item,
    );
    if (state.currentConversationId === conversationId) {
      state.currentConversationTitle = data.conversation.title;
    }
    closeRenameConversation();
    renderConversationList(els.conversationSearchInput.value);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    els.saveRenameConversationButton.disabled = false;
  }
}

async function deleteConversationItem(conversation) {
  document.querySelectorAll(".conversation-item-menu").forEach((menu) => {
    menu.hidden = true;
  });
  document.querySelectorAll(".conversation-item.menu-open").forEach((item) => {
    item.classList.remove("menu-open");
  });
  const t = localeText().conversations;
  const confirmed = window.confirm(
    t.deleteConfirm.replace('{title}', conversation.title || t.untitled.toLowerCase()),
  );
  if (!confirmed) return;
  try {
    await api(`/api/conversations/${encodeURIComponent(conversation.id)}`, {
      method: "DELETE",
    });
    state.conversations = state.conversations.filter(
      (item) => item.id !== conversation.id,
    );
    if (state.currentConversationId === conversation.id)
      startNewConversation(false);
    renderConversationList(els.conversationSearchInput.value);
  } catch (error) {
    setStatus(error.message, true);
  }
}

function formatConversationTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const now = new Date();
  const t = localeText().conversations;
  const localeMap = { vi: 'vi-VN', en: 'en-US', 'zh-Hans': 'zh-CN', 'zh-Hant': 'zh-TW' };
  const locale = localeMap[state.language] || 'en-US';
  const sameDay = date.toDateString() === now.toDateString();
  if (sameDay)
    return `${t.today} · ${date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })}`;
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return t.yesterday;
  return date.toLocaleDateString(locale, {
    day: '2-digit',
    month: '2-digit',
    year: date.getFullYear() === now.getFullYear() ? undefined : 'numeric',
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function openProfile(isOnboarding = false) {
  state.profileStep = 1;
  state.quizIndex = 0;
  els.closeProfileButton.title = isOnboarding ? "Để sau" : "Đóng";
  populateProfileValues();
  updateProfileStep();
  openDialog(els.profileDialog);
}

function populateProfileValues() {
  const profile = state.profile || {};
  els.profileAgeGroup.value = profile.age_group || "prefer_not_say";
  els.profileLifeStage.value = profile.life_stage || "other";
  els.profileGender.value = profile.gender || "prefer_not_say";
  els.profileGenderNote.value = profile.gender_note || "";
  els.profileRelationshipStatus.value =
    profile.relationship_status || "prefer_not_say";
  els.profileChildrenStatus.value = profile.children_status || "prefer_not_say";
  els.profileLivingContext.value = profile.living_context || "prefer_not_say";
  toggleGenderNote();
  const answers = profile.quiz_answers || {};
  state.profileSchema.questionnaire.forEach((question) => {
    document
      .querySelectorAll(`input[name="profile_${question.id}"]`)
      .forEach((input) => {
        input.checked = input.value === answers[question.id];
      });
  });
}

function toggleGenderNote() {
  els.genderNoteField.classList.toggle(
    "hidden",
    els.profileGender.value !== "self_described",
  );
}

async function profileNext() {
  clearProfileError();
  if (state.profileStep === 1) {
    state.profileStep = 2;
    state.quizIndex = 0;
    updateProfileStep();
    return;
  }
  if (state.profileStep === 2) {
    const question = state.profileSchema.questionnaire[state.quizIndex];
    const selected = document.querySelector(
      `input[name="profile_${question.id}"]:checked`,
    );
    if (!selected) {
      showProfileError("Chọn một phương án đã.");
      return;
    }
    if (state.quizIndex < state.profileSchema.questionnaire.length - 1) {
      state.quizIndex += 1;
      updateProfileStep();
      return;
    }
    const profile = collectProfilePayload();
    if (!profile) return;
    els.profileNextButton.disabled = true;
    els.profileNextButton.textContent = "Đang ghép kết quả...";
    try {
      const data = await api("/api/profile", {
        method: "POST",
        body: { profile },
      });
      state.profile = data.profile;
      state.profileCompleted = true;
      state.profileStep = 3;
      renderProfileResult();
      updateProfileCard();
      updateProfileStep();
      setStatus("Đã hiểu thêm về bạn.");
      setTimeout(() => setStatus(""), 1600);
    } catch (error) {
      showProfileError(error.message);
    } finally {
      els.profileNextButton.disabled = false;
      if (state.profileStep === 2)
        els.profileNextButton.textContent = "Xem kết quả";
    }
    return;
  }
  closeDialog(els.profileDialog);
}

function profileBack() {
  clearProfileError();
  if (state.profileStep === 1) {
    closeDialog(els.profileDialog);
    return;
  }
  if (state.profileStep === 2) {
    if (state.quizIndex > 0) state.quizIndex -= 1;
    else state.profileStep = 1;
    updateProfileStep();
    return;
  }
  state.profileStep = 2;
  state.quizIndex = state.profileSchema.questionnaire.length - 1;
  updateProfileStep();
}

function updateProfileStep() {
  document.querySelectorAll("[data-profile-step]").forEach((section) => {
    section.classList.toggle(
      "active",
      Number(section.dataset.profileStep) === state.profileStep,
    );
  });
  document.querySelectorAll("[data-profile-dot]").forEach((dot) => {
    dot.classList.toggle(
      "active",
      Number(dot.dataset.profileDot) <= state.profileStep,
    );
  });
  if (state.profileStep === 1) {
    els.profileBackButton.textContent = "Để sau";
    els.profileNextButton.textContent = "Bắt đầu 20 câu";
  } else if (state.profileStep === 2) {
    els.profileBackButton.textContent =
      state.quizIndex > 0 ? "Câu trước" : "Quay lại";
    els.profileNextButton.textContent =
      state.quizIndex < state.profileSchema.questionnaire.length - 1
        ? "Tiếp"
        : "Xem kết quả";
    updateQuizView();
  } else {
    els.profileBackButton.textContent = "Xem lại";
    els.profileNextButton.textContent = "Xong";
  }
}

function updateQuizView() {
  const questions = state.profileSchema?.questionnaire || [];
  document.querySelectorAll("[data-question-index]").forEach((fieldset) => {
    fieldset.classList.toggle(
      "active",
      Number(fieldset.dataset.questionIndex) === state.quizIndex,
    );
  });
  if (!questions.length) return;
  els.quizProgressText.textContent = `Câu ${state.quizIndex + 1}/${questions.length}`;
  els.quizProgressFill.style.width = `${((state.quizIndex + 1) / questions.length) * 100}%`;
}

function collectProfilePayload() {
  const quizAnswers = {};
  const missing = [];
  state.profileSchema.questionnaire.forEach((question, index) => {
    const selected = document.querySelector(
      `input[name="profile_${question.id}"]:checked`,
    );
    if (!selected) missing.push(index + 1);
    else quizAnswers[question.id] = selected.value;
  });
  if (missing.length) {
    state.quizIndex = missing[0] - 1;
    updateProfileStep();
    showProfileError(`Còn thiếu câu ${missing[0]}.`);
    return null;
  }
  return {
    age_group: els.profileAgeGroup.value,
    life_stage: els.profileLifeStage.value,
    gender: els.profileGender.value,
    gender_note: els.profileGenderNote.value.trim(),
    relationship_status: els.profileRelationshipStatus.value,
    children_status: els.profileChildrenStatus.value,
    living_context: els.profileLivingContext.value,
    quiz_answers: quizAnswers,
  };
}

function renderProfileResult() {
  if (!state.profile) return;
  els.profileResultName.textContent = state.profile.archetype_label;
  els.profileResultDescription.textContent =
    state.profile.archetype_description;
  els.profileScoreList.replaceChildren();
  Object.entries(state.profile.personality_traits || {}).forEach(
    ([key, value]) => {
      const row = document.createElement("div");
      row.className = "profile-score-row";
      const label = document.createElement("span");
      label.textContent = traitLabels[key] || key;
      const bar = document.createElement("div");
      bar.className = "profile-score-bar";
      const fill = document.createElement("i");
      fill.style.width = `${Math.max(0, Math.min(100, Number(value) || 0))}%`;
      bar.appendChild(fill);
      const score = document.createElement("strong");
      score.textContent = String(value);
      row.append(label, bar, score);
      els.profileScoreList.appendChild(row);
    },
  );
}

function updateProfileCard() {
  if (!state.profileCompleted || !state.profile) {
    const t = localeText();
    els.profileArchetypeName.textContent = t.profileCardDefaultName;
    els.profileArchetypeDescription.textContent = t.profileCardDefaultDesc;
    return;
  }
  els.profileArchetypeName.textContent =
    state.profile.archetype_label || "Đã làm quen";
  els.profileArchetypeDescription.textContent =
    state.profile.archetype_description || "Bấm để xem lại";
}
function showProfileError(message) {
  els.profileError.textContent = message;
}
function clearProfileError() {
  els.profileError.textContent = "";
}

async function sendMessage() {
  const message = els.input.value.trim();
  if (!message || state.isSending) return;
  state.isSending = true;
  els.send.disabled = true;
  els.input.disabled = true;
  const style = styleMeta(state.responseStyle);
  const t = localeText();
  setStatus(`${style.name} · ${toneLabel()} ${t.statuses.thinking}`);
  if (els.welcome) els.welcome.hidden = true;
  renderMessage("user", message, true, state.responseStyle);
  els.input.value = "";
  resizeInput();
  const loading = renderLoading(state.responseStyle);
  try {
    const chatBody = {
      message,
      mode: state.mode,
      category: state.category,
      pronoun_style: state.pronounStyle,
      response_style: state.responseStyle,
      tone_style: state.toneStyle,
      language: state.language,
      conversation_id: state.currentConversationId,
    };

    let data;
    try {
      data = await api("/api/chat", {
        method: "POST",
        body: chatBody,
      });
    } catch (error) {
      const staleConversation =
        error.status === 404 &&
        error.code === "not_found" &&
        Boolean(state.currentConversationId);

      if (!staleConversation) throw error;

      // Database may have been replaced while the browser still keeps an old
      // conversation id. Reset it and resend the same message as a new chat.
      state.currentConversationId = null;
      state.currentConversationTitle = "";
      data = await api("/api/chat", {
        method: "POST",
        body: { ...chatBody, conversation_id: null },
      });
      setStatus("Đoạn chat cũ không còn trong dữ liệu. Đã mở một đoạn chat mới.");
      setTimeout(() => setStatus(""), 2200);
    }
    state.currentConversationId =
      data.conversation_id || state.currentConversationId;
    state.currentConversationTitle =
      data.conversation?.title || state.currentConversationTitle;
    if (data.mode && data.mode !== state.mode) {
      state.mode = data.mode;
      localStorage.setItem("oday_mode", state.mode);
      applySavedControls();
    }
    loading.remove();
    renderMessage(
      "assistant",
      data.reply,
      true,
      data.response_style || state.responseStyle,
    );
    updateUsage(data.used_total, data.free_limit, data.quota);
    setStatus(
      data.safety_route ? localeText().statuses.safetyPriority : "",
    );
  } catch (error) {
    loading.remove();
    if (error.quota) updateUsage(state.usedTotal, state.freeLimit, error.quota);
    renderMessage("assistant", `Có lỗi: ${error.message}`, true, state.responseStyle);
    setStatus(error.message, true);
    if (error.code === "quota_exhausted") setTimeout(() => openBilling(), 250);
  } finally {
    state.isSending = false;
    els.send.disabled = false;
    els.input.disabled = false;
    els.input.focus();
  }
}

function formatVnd(value) {
  return `${Number(value || 0).toLocaleString('vi-VN')}đ`;
}

function formatQuota(quota = state.quota) {
  if (!quota) return billingText().loading;
  if (quota.permanent_test) return billingText().permanentTest;
  if (quota.unlimited_active && Number(quota.unlimited_daily_remaining || 0) > 0) {
    return `${billingText().unlimited} · ${quota.unlimited_daily_remaining} lượt hôm nay`;
  }
  return billingText().quotaParts
    .replace('{daily}', String(quota.daily_remaining || 0))
    .replace('{welcome}', String(quota.welcome_remaining || 0))
    .replace('{paid}', String((quota.purchased_credits || 0) + (quota.subscription_remaining || 0)));
}

function selectBillingTab(tab) {
  state.billingTab = tab === 'monthly' ? 'monthly' : 'topups';
  document.querySelectorAll('[data-billing-tab]').forEach((button) => {
    button.classList.toggle('active', button.dataset.billingTab === state.billingTab);
  });
  document.querySelectorAll('[data-billing-panel]').forEach((panel) => {
    panel.hidden = panel.dataset.billingPanel !== state.billingTab;
  });
}

async function openBilling() {
  closeSidebar();
  openDialog(els.billingDialog);
  els.billingStatus.textContent = billingText().loading;
  els.billingStatus.classList.remove('error');
  try {
    const data = await api('/api/billing/plans');
    state.pricing = data.plans;
    state.paymentConfigured = Boolean(data.payment_configured);
    updateUsage(state.usedTotal, state.freeLimit, data.quota);
    renderBillingPlans();
    els.billingStatus.textContent = state.paymentConfigured ? '' : billingText().notConfigured;
    els.billingStatus.classList.toggle('error', !state.paymentConfigured);
  } catch (error) {
    els.billingStatus.textContent = error.message;
    els.billingStatus.classList.add('error');
  }
}

function renderBillingPlans() {
  if (!state.pricing) return;
  renderBillingPlanGroup(els.billingTopupPlans, state.pricing.topups || []);
  renderBillingPlanGroup(els.billingMonthlyPlans, state.pricing.monthly || []);
  els.billingNotes.replaceChildren();
  (state.pricing.notes || []).forEach((note) => {
    const p = document.createElement('p');
    p.textContent = note;
    els.billingNotes.appendChild(p);
  });
  selectBillingTab(state.billingTab);
}

function renderBillingPlanGroup(container, plans) {
  container.replaceChildren();
  plans.forEach((plan) => {
    const card = document.createElement('article');
    card.className = `billing-plan-card${plan.popular ? ' popular' : ''}`;
    if (plan.popular) {
      const badge = document.createElement('span');
      badge.className = 'billing-plan-badge';
      badge.textContent = billingText().popular;
      card.appendChild(badge);
    }
    const title = document.createElement('h4');
    title.textContent = plan.name;
    const price = document.createElement('div');
    price.className = 'billing-plan-price';
    price.textContent = formatVnd(plan.price_vnd);
    const desc = document.createElement('p');
    desc.textContent = plan.description || '';
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = billingText().buy;
    button.disabled = !state.paymentConfigured;
    button.addEventListener('click', () => startCheckout(plan, button));
    card.append(title, price, desc, button);
    container.appendChild(card);
  });
}

async function startCheckout(plan, button) {
  const oldText = button.textContent;
  button.disabled = true;
  button.textContent = billingText().checkout;
  els.billingStatus.textContent = '';
  try {
    const data = await api('/api/billing/checkout', {
      method: 'POST',
      body: { plan_id: plan.id },
    });
    window.location.href = data.checkout_url;
  } catch (error) {
    button.disabled = false;
    button.textContent = oldText;
    els.billingStatus.textContent = error.message;
    els.billingStatus.classList.add('error');
  }
}

async function handlePaymentReturn() {
  const params = new URLSearchParams(window.location.search);
  const paymentState = params.get('payment');
  const orderId = params.get('order_id');
  if (!paymentState) return;
  history.replaceState({}, document.title, window.location.pathname);
  await openBilling();
  if (paymentState === 'cancel') {
    els.billingStatus.textContent = billingText().cancelled;
    return;
  }
  if (!orderId) return;
  els.billingStatus.textContent = billingText().returnChecking;
  for (let attempt = 0; attempt < 8; attempt += 1) {
    try {
      const data = await api(`/api/billing/orders/${encodeURIComponent(orderId)}`);
      updateUsage(state.usedTotal, state.freeLimit, data.quota);
      if (data.order.status === 'paid') {
        els.billingStatus.textContent = billingText().paid;
        els.billingStatus.classList.remove('error');
        return;
      }
    } catch (error) {
      els.billingStatus.textContent = error.message;
      els.billingStatus.classList.add('error');
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  els.billingStatus.textContent = billingText().pending;
}

function renderMessage(
  role,
  content,
  animate = true,
  responseStyle = "luyen",
) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;
  if (animate) row.style.opacity = "0";
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.appendChild(
    makeIcon(
      role === "user"
        ? "icon-user"
        : responseStyles[responseStyle]?.icon || "icon-shuffle",
    ),
  );
  const wrap = document.createElement("div");
  wrap.className = "message-wrap";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;
  wrap.appendChild(bubble);
  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent =
    role === "user"
      ? userMetaLabel()
      : styleMeta(responseStyle).name || window.APP_CONFIG.brandName;
  wrap.appendChild(meta);
  row.append(avatar, wrap);
  els.messages.appendChild(row);
  if (animate)
    requestAnimationFrame(() => {
      row.style.transition = "opacity .18s ease, transform .18s ease";
      row.style.opacity = "1";
    });
  scrollToBottom();
  return row;
}

function renderLoading(responseStyle = "luyen") {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.appendChild(
    makeIcon(responseStyles[responseStyle]?.icon || "icon-shuffle"),
  );
  const wrap = document.createElement("div");
  wrap.className = "message-wrap";
  wrap.innerHTML =
    '<div class="bubble loading-bubble"><span></span><span></span><span></span></div>';
  row.append(avatar, wrap);
  els.messages.appendChild(row);
  scrollToBottom();
  return row;
}

function resizeInput() {
  els.input.style.height = "auto";
  els.input.style.height = `${Math.min(els.input.scrollHeight, 170)}px`;
}
function scrollToBottom() {
  requestAnimationFrame(() => {
    els.messages.scrollTop = els.messages.scrollHeight;
  });
}
function updateUsage(used, limit, quota = null) {
  state.usedTotal = Number(used || 0);
  state.freeLimit = Number(limit || 10);
  if (quota) state.quota = quota;
  const activeQuota = state.quota;
  if (!activeQuota) {
    els.usage.textContent = `${used}/${limit}`;
    setText('#usageSuffix', localeText().usageSuffix);
    return;
  }
  const total = Number(activeQuota.finite_remaining || 0) + Number(activeQuota.unlimited_daily_remaining || 0);
  els.usage.textContent = activeQuota.permanent_test
    ? billingText().permanentTest
    : activeQuota.unlimited_active
      ? billingText().unlimited
      : billingText().remaining.replace('{n}', String(total));
  setText('#usageSuffix', '');
  const detail = formatQuota(activeQuota);
  if (els.billingBalanceText) els.billingBalanceText.textContent = detail;
  if (els.accountQuotaText) els.accountQuotaText.textContent = detail;
}
function setStatus(text, isError = false) {
  els.status.textContent = text || "";
  els.status.classList.toggle("error", isError);
}
async function saveSettings(message = localeText().statuses.saved) {
  await api("/api/settings", {
    method: "POST",
    body: {
      pronoun_style: state.pronounStyle,
      response_style: state.responseStyle,
      tone_style: state.toneStyle,
      language: state.language,
    },
  });
  setStatus(message);
  setTimeout(() => setStatus(""), 1400);
}

async function api(url, options = {}) {
  const init = { ...options, credentials: "same-origin" };
  init.headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (options.body && typeof options.body !== "string")
    init.body = JSON.stringify(options.body);
  const response = await fetch(url, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && !url.startsWith("/api/auth/")) {
      setTimeout(() => window.location.reload(), 300);
    }
    const error = new Error(data.error || `Lỗi HTTP ${response.status}`);
    error.status = response.status;
    error.code = data.code || "";
    error.payload = data;
    error.quota = data.quota || null;
    throw error;
  }
  return data;
}

init().catch((error) => {
  showAuth();
  setAuthStatus(els.loginStatus, error.message, true);
});
