(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const STORAGE_KEY = "mo_loi_ui_language";
  const text = {
    vi:{back:"Trang chính",brand:"Quản lý chi tiêu",language:"Ngôn ngữ",eyebrow:"TIỀN CỦA MÌNH ĐANG ĐI ĐÂU?",title:"Nhìn tiền rõ hơn.<br>Đỡ cuối tháng mới giật mình.",month:"Tháng",plan:"Đặt kế hoạch tháng",income:"Thu vào",expense:"Đã chi",balance:"Còn lại",budgetLeft:"Ngân sách tháng còn",quickAdd:"GHI NHANH",addTitle:"Thêm một khoản",spend:"Chi",earn:"Thu",amount:"Số tiền",category:"Danh mục",date:"Ngày",note:"Ghi chú",saveTransaction:"Lưu khoản này",manualEntry:"Nhập thủ công",whereSpent:"CƠ CẤU CHI",categoryTitle:"Chi nhiều vào đâu?",noExpense:"Chưa có khoản chi nào.",history:"LỊCH SỬ",recentTitle:"Các khoản gần đây",noTransactions:"Chưa có giao dịch.",planEyebrow:"KẾ HOẠCH THÁNG",planTitle:"Đặt giới hạn trước khi tiêu",incomeTarget:"Thu nhập dự kiến",budgetLimit:"Ngân sách chi tối đa",savingTarget:"Mục tiêu để dành",planNote:"Đây là công cụ lập ngân sách cá nhân, không phải tư vấn đầu tư hay tài chính chuyên nghiệp.",savePlan:"Lưu kế hoạch",incomeGoal:"Mục tiêu thu {pct}%",budgetUse:"Đã dùng {pct}% ngân sách",savingGoal:"Đạt {pct}% mục tiêu để dành",noPlan:"Chưa đặt kế hoạch",onTrack:"Đang đúng nhịp",overBudget:"Đã vượt ngân sách",belowSaving:"Cần giữ thêm để đạt mục tiêu",saved:"Đã lưu",deleted:"Đã xóa",count:"{n} khoản"},
    en:{back:"Home",brand:"Spending manager",language:"Language",eyebrow:"WHERE IS MY MONEY GOING?",title:"See your money clearly.<br>No end-of-month surprises.",month:"Month",plan:"Set monthly plan",income:"Income",expense:"Spent",balance:"Remaining",budgetLeft:"Monthly budget left",quickAdd:"QUICK LOG",addTitle:"Add a transaction",spend:"Expense",earn:"Income",amount:"Amount",category:"Category",date:"Date",note:"Note",saveTransaction:"Save transaction",manualEntry:"Manual entry",whereSpent:"SPENDING MIX",categoryTitle:"Where is your spending going?",noExpense:"No expenses yet.",history:"HISTORY",recentTitle:"Recent transactions",noTransactions:"No transactions yet.",planEyebrow:"MONTHLY PLAN",planTitle:"Set limits before spending",incomeTarget:"Expected income",budgetLimit:"Maximum spending budget",savingTarget:"Savings target",planNote:"This is a personal budgeting tool, not professional investment or financial advice.",savePlan:"Save plan",incomeGoal:"Income goal {pct}%",budgetUse:"Used {pct}% of budget",savingGoal:"Reached {pct}% of savings target",noPlan:"No plan set",onTrack:"On track",overBudget:"Over budget",belowSaving:"Keep more to reach your goal",saved:"Saved",deleted:"Deleted",count:"{n} items"},
    zh:{back:"首頁",brand:"支出管理",language:"語言",eyebrow:"我的錢都去哪裡了？",title:"把錢看清楚。<br>月底少一點驚訝。",month:"月份",plan:"設定每月計畫",income:"收入",expense:"已支出",balance:"剩餘",budgetLeft:"本月剩餘預算",quickAdd:"快速記錄",addTitle:"新增一筆",spend:"支出",earn:"收入",amount:"金額",category:"分類",date:"日期",note:"備註",saveTransaction:"儲存這筆",manualEntry:"手動輸入",whereSpent:"支出結構",categoryTitle:"錢主要花在哪裡？",noExpense:"目前還沒有支出。",history:"紀錄",recentTitle:"最近交易",noTransactions:"目前沒有交易，先新增第一筆吧。",planEyebrow:"每月計畫",planTitle:"花錢前先設定界線",incomeTarget:"預期收入",budgetLimit:"支出預算上限",savingTarget:"儲蓄目標",planNote:"這是個人預算工具，不是專業投資或財務建議。",savePlan:"儲存計畫",incomeGoal:"收入目標 {pct}%",budgetUse:"已使用 {pct}% 預算",savingGoal:"已達成 {pct}% 儲蓄目標",noPlan:"尚未設定計畫",onTrack:"目前節奏不錯",overBudget:"已超出預算",belowSaving:"需要多保留一些才能達標",saved:"已儲存",deleted:"已刪除",count:"{n} 筆"}
  };
  const categories={
    vi:{food:"Ăn uống",housing:"Nhà ở",transport:"Đi lại",shopping:"Mua sắm",study:"Học tập",health:"Sức khỏe",entertainment:"Giải trí",bills:"Hóa đơn",family:"Gia đình",other:"Khác",salary:"Lương",freelance:"Freelance",bonus:"Thưởng",family_support:"Gia đình hỗ trợ",sale:"Bán đồ",other_income:"Thu nhập khác"},
    en:{food:"Food",housing:"Housing",transport:"Transport",shopping:"Shopping",study:"Study",health:"Health",entertainment:"Entertainment",bills:"Bills",family:"Family",other:"Other",salary:"Salary",freelance:"Freelance",bonus:"Bonus",family_support:"Family support",sale:"Selling items",other_income:"Other income"},
    zh:{food:"飲食",housing:"住房",transport:"交通",shopping:"購物",study:"學習",health:"健康",entertainment:"娛樂",bills:"帳單",family:"家庭",other:"其他",salary:"薪資",freelance:"接案",bonus:"獎金",family_support:"家庭支援",sale:"出售物品",other_income:"其他收入"}
  };
  Object.assign(categories.vi,{client_entertainment:"Tiếp khách",travel:"Công tác",office:"Văn phòng phẩm",equipment:"Thiết bị / công cụ",software:"Phần mềm / dịch vụ số",telecom:"Internet / viễn thông",rent:"Thuê văn phòng / mặt bằng",utilities:"Điện nước / tiện ích",marketing:"Marketing / quảng cáo",shipping:"Vận chuyển / logistics",maintenance:"Bảo trì / sửa chữa",payroll:"Lương nhân viên",tax:"Thuế / lệ phí",training:"Đào tạo"});
  Object.assign(categories.en,{client_entertainment:"Client entertainment",travel:"Business travel",office:"Office supplies",equipment:"Equipment / tools",software:"Software / digital services",telecom:"Internet / telecom",rent:"Office / site rent",utilities:"Utilities",marketing:"Marketing / advertising",shipping:"Shipping / logistics",maintenance:"Maintenance / repair",payroll:"Payroll",tax:"Tax / fees",training:"Training"});
  Object.assign(categories.zh,{client_entertainment:"客戶招待",travel:"出差",office:"辦公用品",equipment:"設備 / 工具",software:"軟體 / 數位服務",telecom:"網路 / 電信",rent:"辦公室 / 場地租金",utilities:"水電 / 公用費",marketing:"行銷 / 廣告",shipping:"運輸 / 物流",maintenance:"維修 / 保養",payroll:"員工薪資",tax:"稅費",training:"培訓"});

  let currentKind="expense", planMonth="", overview=null;
  const lang=()=>localStorage.getItem(STORAGE_KEY)||"vi";
  const t=(key,vars={})=>String((text[lang()]||text.vi)[key]||key).replace(/\{(\w+)\}/g,(_,k)=>vars[k]??"");
  const money=(n)=>new Intl.NumberFormat(lang()==="vi"?"vi-VN":lang()==="zh"?"zh-TW":"en-US",{style:"currency",currency:"VND",maximumFractionDigits:0}).format(Number(n||0));
  const formatInput=(value)=>String(value||"").replace(/\D/g,"").replace(/\B(?=(\d{3})+(?!\d))/g,".");
  const rawAmount=(value)=>Number(String(value||"").replace(/\D/g,""))||0;
  const toast=(msg)=>{const el=$("#toast");el.textContent=msg;el.hidden=false;clearTimeout(window.__ft);window.__ft=setTimeout(()=>el.hidden=true,2600)};
  async function api(url,options={}){const res=await fetch(url,{credentials:"same-origin",headers:{"Content-Type":"application/json",...(options.headers||{})},...options});let data={};try{data=await res.json()}catch{}if(res.status===401){location.href="/";throw new Error("auth")};if(!res.ok)throw new Error(data.error||`HTTP ${res.status}`);return data}
  function applyText(){document.documentElement.lang=lang()==="zh"?"zh-Hant":lang();$$('[data-t]').forEach(el=>{const v=t(el.dataset.t);if(el.dataset.t==="title")el.innerHTML=v;else el.textContent=v});$("#uiLanguage").value=lang();renderCategoryOptions();if(overview)render(overview)}
  function renderCategoryOptions(){const keys=currentKind==="expense"?["food","client_entertainment","transport","travel","office","equipment","software","telecom","rent","utilities","marketing","shipping","maintenance","payroll","tax","training","housing","shopping","study","health","entertainment","bills","family","other"]:["salary","freelance","bonus","family_support","sale","other_income"];const keep=$("#categorySelect").value;$("#categorySelect").innerHTML=keys.map(k=>`<option value="${k}">${categories[lang()]?.[k]||categories.vi[k]}</option>`).join("");if(keys.includes(keep))$("#categorySelect").value=keep}
  function statusLabel(s){if(!overview)return"—";if(!overview.plan.budget_limit&&!overview.plan.saving_target)return t("noPlan");if(s==="over_budget")return t("overBudget");if(s==="below_saving_target")return t("belowSaving");return t("onTrack")}
  function render(data){overview=data;if(data.month)planMonth=data.month;const s=data.summary,p=data.plan;$("#incomeValue").textContent=money(s.income);$("#expenseValue").textContent=money(s.expense);$("#balanceValue").textContent=money(s.balance);$("#budgetLeftValue").textContent=p.budget_limit?money(s.budget_remaining):"—";$("#incomeProgress").textContent=p.monthly_income_target?t("incomeGoal",{pct:Math.min(999,s.income_progress_percent)}):t("noPlan");$("#budgetProgress").textContent=p.budget_limit?t("budgetUse",{pct:Math.round(s.budget_used_percent)}):t("noPlan");$("#savingProgress").textContent=p.saving_target?t("savingGoal",{pct:Math.max(0,Math.round(s.saving_progress_percent))}):t("noPlan");$("#monthStatus").textContent=statusLabel(s.status);$("#incomeTarget").value=p.monthly_income_target?formatInput(p.monthly_income_target):"";$("#budgetLimit").value=p.budget_limit?formatInput(p.budget_limit):"";$("#savingTarget").value=p.saving_target?formatInput(p.saving_target):"";
    const cat=$("#categoryList");cat.innerHTML="";(data.categories||[]).forEach(item=>{const row=document.createElement("div");row.className="category-item";row.innerHTML=`<strong>${categories[lang()]?.[item.key]||item.label}</strong><div class="bar"><i style="width:${Math.min(100,item.share)}%"></i></div><b>${money(item.amount)} · ${item.share}%</b>`;cat.appendChild(row)});$("#emptyCategories").hidden=(data.categories||[]).length>0;
    const root=$("#transactionList");root.innerHTML="";(data.transactions||[]).forEach(item=>{const row=document.createElement("article");row.className=`transaction-item ${item.kind}`;row.innerHTML=`<span class="transaction-icon">${item.kind==="income"?"+":"−"}</span><div class="transaction-copy"><strong>${categories[lang()]?.[item.category]||item.category}</strong><small>${item.occurred_on}${item.note?` · ${escapeHtml(item.note)}`:""}</small></div><b class="transaction-amount">${item.kind==="income"?"+":"−"}${money(item.amount)}</b><button class="delete-btn" type="button" data-id="${item.id}">×</button>`;root.appendChild(row)});$("#emptyTransactions").hidden=(data.transactions||[]).length>0;$("#transactionCount").textContent=t("count",{n:(data.transactions||[]).length});$$('.delete-btn').forEach(btn=>btn.onclick=()=>removeTransaction(btn.dataset.id));
  }
  const escapeHtml=(v)=>String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
  async function load(){overview=await api("/api/finance/overview");render(overview)}
  function financeBubble(message){
    const row=document.createElement("div");row.className=`finance-chat-row ${message.role||"assistant"}`;
    const bubble=document.createElement("div");bubble.className="finance-chat-bubble";bubble.textContent=message.content||"";row.appendChild(bubble);
    const meta=message.meta||{};
    if(meta.download_url){const a=document.createElement("a");a.className="finance-download";a.href=meta.download_url;a.textContent="Tải Excel";a.setAttribute("download","");row.appendChild(a)}
    return row;
  }
  function clearFinanceCommandResult(){const root=$("#financeChatMessages");root.innerHTML="";root.hidden=true}
  function showFinanceCommandResult(message){const root=$("#financeChatMessages");root.innerHTML="";if(!message){root.hidden=true;return}root.hidden=false;root.appendChild(financeBubble(message));root.scrollTop=root.scrollHeight}
  async function loadPendingFinanceState(){
    const data=await api("/api/finance/chat");
    if(data.pending_prompt)showFinanceCommandResult({role:"assistant",content:data.pending_prompt});
    else clearFinanceCommandResult();
  }
  async function sendFinanceMessage(message){
    clearFinanceCommandResult();
    const send=$("#financeChatSend");send.disabled=true;send.textContent="Đang xử lý";
    try{
      const data=await api("/api/finance/assistant",{method:"POST",body:JSON.stringify({message})});
      if(data.overview){overview=data.overview;render(data.overview)}
      if(["created","edited","deleted"].includes(data.action)){
        clearFinanceCommandResult();
        toast(data.reply||t("saved"));
      }else{
        const assistant={role:"assistant",content:data.reply||"Xong.",meta:data.download_url?{download_url:data.download_url}:(data.assistant_message?.meta||{})};
        if(data.download_url)assistant.meta.download_url=data.download_url;
        showFinanceCommandResult(assistant);
      }
    }catch(error){showFinanceCommandResult({role:"assistant",content:`Lỗi: ${error.message}`})}
    finally{send.disabled=false;send.textContent="Gửi"}
  }
  async function removeTransaction(id){const data=await api(`/api/finance/transaction/${id}`,{method:"DELETE"});render(data.overview);toast(t("deleted"))}
  $$("[data-kind]").forEach(btn=>btn.addEventListener("click",()=>{currentKind=btn.dataset.kind;$$('[data-kind]').forEach(b=>b.classList.toggle("active",b===btn));renderCategoryOptions()}));
  $("#transactionForm").addEventListener("submit",async e=>{e.preventDefault();const data=await api("/api/finance/transaction",{method:"POST",body:JSON.stringify({kind:currentKind,amount:rawAmount($("#amountInput").value),category:$("#categorySelect").value,note:$("#noteInput").value,occurred_on:$("#transactionDate").value})});render(data.overview);$("#amountInput").value="";$("#noteInput").value="";toast(t("saved"))});
  $("#planForm").addEventListener("submit",async e=>{e.preventDefault();const data=await api("/api/finance/plan",{method:"POST",body:JSON.stringify({month:planMonth,monthly_income_target:rawAmount($("#incomeTarget").value),budget_limit:rawAmount($("#budgetLimit").value),saving_target:rawAmount($("#savingTarget").value)})});render(data.overview);$("#planDialog").close();toast(t("saved"))});
  ["#amountInput","#incomeTarget","#budgetLimit","#savingTarget"].forEach(sel=>$(sel).addEventListener("input",e=>{const pos=e.target.value.length;e.target.value=formatInput(e.target.value)}));
  const manualToggle=$("#manualEntryToggle"),manualPanel=$("#manualEntryPanel");
  manualToggle.addEventListener("click",()=>{const opening=manualPanel.hidden;manualPanel.hidden=!opening;manualToggle.setAttribute("aria-expanded",String(opening));manualToggle.classList.toggle("open",opening);if(opening)$("#amountInput").focus()});
  $("#openPlanBtn").onclick=()=>$("#planDialog").showModal();$("#closePlanBtn").onclick=()=>$("#planDialog").close();$("#uiLanguage").addEventListener("change",e=>{localStorage.setItem(STORAGE_KEY,e.target.value);applyText()});
  function speechLocale(){return lang()==="zh"?"zh-TW":lang()==="en"?"en-US":"vi-VN"}
  function setupFinanceVoice(){
    const btn=$("#financeVoiceBtn"),input=$("#financeChatInput");
    if(!btn||!input)return;
    const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!Recognition){btn.disabled=true;btn.title="Trình duyệt chưa hỗ trợ nhập giọng nói";return}
    const recognition=new Recognition();
    recognition.continuous=false;
    recognition.interimResults=true;
    recognition.maxAlternatives=1;
    let listening=false,baseText="";
    const reset=()=>{listening=false;btn.classList.remove("listening");btn.setAttribute("aria-pressed","false");btn.title="Nhập bằng giọng nói"};
    btn.addEventListener("click",()=>{
      if(listening){recognition.stop();return}
      baseText=input.value.trim();
      recognition.lang=speechLocale();
      try{recognition.start()}catch(_e){}
    });
    recognition.onstart=()=>{listening=true;btn.classList.add("listening");btn.setAttribute("aria-pressed","true");btn.title="Đang nghe — bấm để dừng"};
    recognition.onresult=(event)=>{
      let transcript="";
      for(let i=event.resultIndex;i<event.results.length;i++)transcript+=event.results[i][0]?.transcript||"";
      input.value=[baseText,transcript.trim()].filter(Boolean).join(" ");
      input.focus();
    };
    recognition.onerror=(event)=>{if(event.error!=="aborted"&&event.error!=="no-speech")toast("Không nghe rõ. Thử nói lại nhé.");reset()};
    recognition.onend=reset;
  }
  $("#financeChatForm").addEventListener("submit",async e=>{e.preventDefault();const input=$("#financeChatInput");const message=input.value.trim();if(!message)return;input.value="";await sendFinanceMessage(message)});
  $$('[data-finance-prompt]').forEach(btn=>btn.addEventListener("click",()=>{$("#financeChatInput").value=btn.dataset.financePrompt||"";$("#financeChatInput").focus()}));
  document.addEventListener("DOMContentLoaded",async()=>{const now=new Date();planMonth=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}`;$("#transactionDate").value=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}-${String(now.getDate()).padStart(2,"0")}`;applyText();setupFinanceVoice();try{await Promise.all([load(),loadPendingFinanceState()])}catch(e){if(e.message!=="auth")toast(e.message)}});
})();
