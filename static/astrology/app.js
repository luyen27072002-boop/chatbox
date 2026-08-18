(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const STORAGE_KEY = "mo_loi_ui_language";
  let currentReading = null;
  let toastTimer = null;

  const texts = {
    vi: {back:"Trang chính",brandSub:"Tử vi & Lá số",language:"Ngôn ngữ",eyebrow:"TỬ VI ĐẨU SỐ · LẬP LÁ SỐ TRƯỚC, LUẬN SAU",heroTitle:"Có lá số thật trước.<br>Muốn hỏi gì thì đi sâu phần đó.",heroDesc:"Hệ thống an 12 cung, chính tinh và phụ tinh từ ngày giờ sinh. Sau đó mới tạo bản tóm tắt, xu hướng gần và phần hỏi sâu.",trust1:"12 cung + chính tinh/phụ tinh",trust2:"Đại hạn, Tiểu hạn, Tuần/Triệt",trust3:"AI chỉ luận dữ liệu đã an sao",formEyebrow:"THÔNG TIN LẬP LÁ SỐ",formTitle:"Cần ngày, giờ sinh và giới tính",birthDate:"Ngày sinh dương lịch",birthTime:"Giờ sinh",gender:"Giới tính dùng để an sao",chooseGender:"Chọn",female:"Nữ",male:"Nam",birthPlace:"Nơi sinh",create:"Lập lá số Tử Vi",formNote:"Bản hiện tại dùng múi giờ Việt Nam GMT+7. Phần an sao được tính bằng engine; phần luận giải chỉ mang tính tham khảo và giải trí.",yourChart:"LÁ SỐ TỬ VI ĐẨU SỐ",resultTitle:"Lá số truyền thống, nhưng đọc dễ hơn",newChart:"Lập lá số khác",chartHeading:"Thiên bàn & 12 cung",chartScrollHint:"Trên điện thoại có thể kéo ngang để xem rõ từng cung.",heavenBoard:"THIÊN BÀN",solarBirth:"Dương lịch",lunarBirth:"Âm lịch",birthHour:"Giờ sinh",bureau:"Cục",destinyMaster:"Mệnh chủ",bodyMaster:"Thân chủ",currentCycle:"Đại hạn hiện tại",chartNote:"Tên cung, vị trí sao, miếu/vượng/đắc/bình/hãm, Đại Hạn, Tiểu Hạn và Tuần/Triệt lấy từ engine an sao. AI không được tự chuyển sao sang cung khác.",overall:"TỔNG QUAN",personality:"NÉT TÍNH CÁCH",nearFuture:"TƯƠNG LAI GẦN",futureTitle:"Xu hướng trong khoảng thời gian tới",futureCaveat:"Phần này dùng lá số nền + bối cảnh Đại Hạn hiện tại để đưa ra xu hướng tham khảo. Muốn xem lưu niên/lưu nguyệt chi tiết hơn sẽ cần thêm engine vận hạn ở phiên bản sau.",doEyebrow:"NÊN LÀM",doTitle:"Chủ động ở những việc này",watchEyebrow:"CẨN TRỌNG",watchTitle:"Đừng để những điều này kéo lệch nhịp",bottomLine:"TÓM LẠI",askEyebrow:"MUỐN XEM KỸ HƠN?",askTitle:"Hỏi đúng cung hoặc chuyện bạn đang quan tâm",askDesc:"Có thể hỏi thẳng về Quan Lộc, Tài Bạch, Phu Thê hoặc hỏi theo tình huống thực tế. Hệ thống sẽ đọc lại đúng các sao trong lá số này.",quickCareer:"Quan Lộc",quickMoney:"Tài Bạch",quickLove:"Phu Thê",quickSelf:"Cung Mệnh",questionPlaceholder:"Ví dụ: Cung Quan Lộc của tôi có những sao gì và 2 tháng tới nên chú ý điều gì?",askBtn:"Hỏi về lá số này",loading:"Đang an sao và lập lá số…",asking:"Đang đọc kỹ cung này…",noQuota:"Bạn đã hết lượt hiện có.",daiHan:"Đại Hạn",tieuHan:"Tiểu Hạn",than:"THÂN",tuan:"TUẦN",triet:"TRIỆT",majorStars:"Chính tinh",minorStars:"Phụ tinh",noMajor:"Vô chính diệu"},
    en: {back:"Home",brandSub:"Astrology & birth chart",language:"Language",eyebrow:"TỬ VI ĐẨU SỐ · CALCULATE FIRST, INTERPRET SECOND",heroTitle:"Build the real chart first.<br>Then ask deeper questions.",heroDesc:"The system places 12 palaces, major stars and minor stars from your birth date and time, then creates a readable summary and follow-up Q&A.",trust1:"12 palaces + major/minor stars",trust2:"10-year cycle, annual labels, Tuần/Triệt",trust3:"AI interprets calculated placements only",formEyebrow:"BIRTH DETAILS",formTitle:"Birth date, time, and sex are required",birthDate:"Solar birth date",birthTime:"Birth time",gender:"Sex used for chart calculation",chooseGender:"Choose",female:"Female",male:"Male",birthPlace:"Birth place",create:"Build Tử Vi chart",formNote:"Current calculation uses Vietnam GMT+7. Star placement is deterministic; interpretation is for entertainment and self-reflection.",yourChart:"TỬ VI ĐẨU SỐ CHART",resultTitle:"Traditional chart, easier to read",newChart:"Build another chart",chartHeading:"Heaven board & 12 palaces",chartScrollHint:"On mobile, scroll horizontally to inspect each palace.",heavenBoard:"HEAVEN BOARD",solarBirth:"Solar date",lunarBirth:"Lunar date",birthHour:"Birth hour",bureau:"Bureau",destinyMaster:"Destiny master",bodyMaster:"Body master",currentCycle:"Current 10-year cycle",chartNote:"Palaces, star positions, strength labels, cycles and Tuần/Triệt come from the calculation engine. AI is not allowed to move stars between palaces.",overall:"OVERVIEW",personality:"PERSONALITY",nearFuture:"NEAR FUTURE",futureTitle:"Tendencies for the next period",futureCaveat:"This uses the natal chart plus current 10-year-cycle context as a reflective tendency. Detailed annual/monthly transit calculations require an additional vận-hạn engine in a later version.",doEyebrow:"DO MORE OF",doTitle:"Things worth taking initiative on",watchEyebrow:"WATCH OUT",watchTitle:"Do not let these throw off your rhythm",bottomLine:"BOTTOM LINE",askEyebrow:"WANT MORE DETAIL?",askTitle:"Ask about a palace or a real-life concern",askDesc:"Ask directly about Career, Wealth, Partner, Self, or describe a situation. The system will read the stars already placed in this chart.",quickCareer:"Career palace",quickMoney:"Wealth palace",quickLove:"Partner palace",quickSelf:"Self palace",questionPlaceholder:"Example: Which stars are in my Career palace and what should I watch over the next two months?",askBtn:"Ask about this chart",loading:"Calculating stars and chart…",asking:"Reading this palace…",noQuota:"You have no credits left.",daiHan:"10-year",tieuHan:"Annual",than:"BODY",tuan:"TUẦN",triet:"TRIỆT",majorStars:"Major",minorStars:"Minor",noMajor:"No major star"},
    zh: {back:"首頁",brandSub:"紫微斗數命盤",language:"語言",eyebrow:"紫微斗數 · 先安星，再解讀",heroTitle:"先建立真正的命盤。<br>想知道哪一宮，再深入問。",heroDesc:"系統依出生年月日時安十二宮、主星與輔星，再提供容易閱讀的總覽、近期趨勢與深入提問。",trust1:"十二宮 + 主星/輔星",trust2:"大限、小限、旬空/截空標記",trust3:"AI 只解讀已計算的星位",formEyebrow:"出生資料",formTitle:"需要出生日期、時間與性別",birthDate:"國曆出生日期",birthTime:"出生時間",gender:"安星使用性別",chooseGender:"請選擇",female:"女",male:"男",birthPlace:"出生地",create:"建立紫微命盤",formNote:"目前以越南 GMT+7 計算。星位由程式計算；文字解讀僅供娛樂與自我反思。",yourChart:"紫微斗數命盤",resultTitle:"傳統命盤，但更容易閱讀",newChart:"建立其他命盤",chartHeading:"天盤與十二宮",chartScrollHint:"手機可左右滑動查看每一宮。",heavenBoard:"天盤",solarBirth:"國曆",lunarBirth:"農曆",birthHour:"出生時辰",bureau:"五行局",destinyMaster:"命主",bodyMaster:"身主",currentCycle:"目前大限",chartNote:"宮位、星曜位置、廟旺得平陷、大限、小限與旬空/截空皆來自安星引擎，AI 不會自行更換星位。",overall:"總覽",personality:"性格傾向",nearFuture:"近期趨勢",futureTitle:"接下來一段時間的節奏",futureCaveat:"此處以本命盤與目前大限作為趨勢參考；若要精細到流年、流月，需要下一版加入更完整的運限引擎。",doEyebrow:"建議做",doTitle:"這些事情可以更主動",watchEyebrow:"需要注意",watchTitle:"別讓這些事情打亂你的節奏",bottomLine:"總結",askEyebrow:"想看更細？",askTitle:"直接問某一宮或你真正關心的事",askDesc:"可以直接問官祿、財帛、夫妻、命宮，也可以描述現實中的具體情況。系統會重新讀取這張命盤內已安的星。",quickCareer:"官祿宮",quickMoney:"財帛宮",quickLove:"夫妻宮",quickSelf:"命宮",questionPlaceholder:"例如：我的官祿宮有哪些星？未來兩個月工作上要注意什麼？",askBtn:"針對這份命盤提問",loading:"正在安星並建立命盤…",asking:"正在深入解讀…",noQuota:"目前沒有可用點數。",daiHan:"大限",tieuHan:"小限",than:"身",tuan:"旬空",triet:"截空",majorStars:"主星",minorStars:"輔星",noMajor:"無主星"}
  };

  const lang = () => { const v = localStorage.getItem(STORAGE_KEY) || "vi"; return v.startsWith("en") ? "en" : v.startsWith("zh") ? "zh" : "vi"; };
  const t = (k) => texts[lang()]?.[k] || texts.vi[k] || k;
  function applyText(){
    document.documentElement.lang = lang() === "zh" ? "zh-Hant" : lang();
    $$('[data-t]').forEach(el => { const value=t(el.dataset.t); if(String(value).includes('<br>')) el.innerHTML=value; else el.textContent=value; });
    $$('[data-placeholder]').forEach(el => el.placeholder=t(el.dataset.placeholder));
  }
  function toast(message,error=false){const el=$("#toast");el.textContent=message;el.classList.remove("hidden","error");if(error)el.classList.add("error");clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.add("hidden"),4200)}
  async function api(url,options={}){const res=await fetch(url,{credentials:"same-origin",headers:{"Content-Type":"application/json",...(options.headers||{})},...options});let data={};try{data=await res.json()}catch{}if(res.status===401){location.href="/";throw new Error("auth")};if(!res.ok){const e=new Error(data.error||`HTTP ${res.status}`);e.payload=data;e.status=res.status;throw e}return data}
  function quotaLabel(q={}){if(q.permanent_test)return "∞";if(q.unlimited_active)return `∞ · ${q.unlimited_daily_remaining??0}`;const n=Number(q.finite_remaining ?? ((q.daily_remaining||0)+(q.welcome_remaining||0)+(q.purchased_credits||0)+(q.subscription_remaining||0)));return Number.isFinite(n)?`${Math.max(0,n)} lượt`:"—"}
  function updateQuota(q){if(q)$("#quotaBadge").textContent=quotaLabel(q)}
  function escapeHtml(v){return String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;")}
  function val(v,fallback="—"){return (v===0||v)?String(v):fallback}

  const elementClass=(element="")=>{const e=String(element).toLowerCase();if(e.includes("mộc"))return"wood";if(e.includes("hỏa")||e.includes("hoả"))return"fire";if(e.includes("thổ"))return"earth";if(e.includes("kim"))return"metal";if(e.includes("thủy")||e.includes("thuỷ"))return"water";return"neutral"};
  const qualityClass=(q="")=>{const x=String(q).trim().toUpperCase();if(["M","V"].includes(x))return"strong";if(["Đ","D"].includes(x))return"good";if(["H"].includes(x))return"weak";return"normal"};

  function sanitizeCssToken(value=""){return String(value||"").trim().toLowerCase().replace(/[^a-z0-9_-]+/g,"-")}
  function inferMajorStars(stars=[]){
    const names=new Set(["Tử Vi","Thiên Cơ","Thái Dương","Vũ Khúc","Thiên Đồng","Liêm Trinh","Thiên Phủ","Thái Âm","Tham Lang","Cự Môn","Thiên Tướng","Thiên Lương","Thất Sát","Phá Quân"]);
    const exact=(stars||[]).filter(s=>names.has(String(s.name||"").trim()));
    if(exact.length) return exact;
    const byType=(stars||[]).filter(s=>Number(s.type||99)===1);
    if(byType.length) return byType;
    return [];
  }
  function splitColumns(items=[]){const left=[],right=[];(items||[]).forEach((item,idx)=>(idx%2===0?left:right).push(item));return [left,right]}
  function renderStarItem(s,kind="minor"){
    const classes=["star",kind,elementClass(s.element),qualityClass(s.quality)];
    const extra=sanitizeCssToken(s.css||"");
    if(extra) classes.push(`css-${extra}`);
    const name=escapeHtml(s.name||"");
    const quality=s.quality?` <em>(${escapeHtml(s.quality)})</em>`:"";
    if(kind==="major") return `<li class="${classes.join(" ")}"><b>${name}</b>${quality}</li>`;
    return `<li class="${classes.join(" ")}">${name}${quality}</li>`;
  }
  function renderPalace(p){
    const article=document.createElement("article");
    article.className=`traditional-palace ${p.grid||""}`;
    const badges=[];
    if(p.is_than)badges.push(`<span class="mark than">${t("than")}</span>`);
    if(p.tuan)badges.push(`<span class="mark tuan">${t("tuan")}</span>`);
    if(p.triet)badges.push(`<span class="mark triet">${t("triet")}</span>`);

    const stars=Array.isArray(p.stars)?p.stars:[];
    const majorList=(p.major_stars&&p.major_stars.length?p.major_stars:inferMajorStars(stars)).slice(0,3);
    const minorSeed=(p.minor_stars&&p.minor_stars.length?p.minor_stars:stars.filter(s=>!majorList.some(m=>m.name===s.name))).filter(s=>!s.trang_sinh);
    const [minorLeft,minorRight]=splitColumns(minorSeed.slice(0,20));
    const trangSinh=(stars||[]).find(s=>s.trang_sinh)?.name||p.trang_sinh||"";
    const majorHtml=majorList.length?majorList.map(s=>renderStarItem(s,"major")).join(""):`<li class="no-major">${t("noMajor")}</li>`;
    const leftHtml=minorLeft.map(s=>renderStarItem(s,"minor")).join("");
    const rightHtml=minorRight.map(s=>renderStarItem(s,"minor")).join("");
    const canChi=escapeHtml(p.can_chi||"");
    const topRight=p.dai_han!==""&&p.dai_han!=null?escapeHtml(val(p.dai_han,"")):"";
    article.innerHTML=`
      <header class="palace-head">
        <small class="palace-canchi">${canChi}</small>
        <strong>${escapeHtml(p.name||"")}</strong>
        <b class="palace-number">${topRight}</b>
      </header>
      <div class="palace-marks">${badges.join("")}</div>
      <ul class="major-stars">${majorHtml}</ul>
      <div class="minor-columns">
        <ul class="minor-stars left">${leftHtml}</ul>
        <ul class="minor-stars right">${rightHtml}</ul>
      </div>
      <div class="palace-bottom-row"><span class="branch">${escapeHtml(p.branch||"")}</span><span class="trang-sinh">${escapeHtml(trangSinh)}</span><span class="minor-age">${p.tieu_han!==""&&p.tieu_han!=null?`T.${escapeHtml(val(p.tieu_han,""))}`:""}</span></div>`;
    return article;
  }

  function renderTraditionalChart(profile, readingId){
    const chart=profile.tuvi_chart||{};
    const engineEl=$("#chartEngine"); if(engineEl)engineEl.textContent=chart.engine?`${chart.system||"Tử Vi Đẩu Số"} · ${chart.engine}`:"—";
    const img=$("#traditionalChartImage"),loading=$("#chartImageLoading"),error=$("#chartImageError");
    if(!img||!readingId)return;
    img.hidden=true;error.hidden=true;loading.hidden=false;
    const stamp=encodeURIComponent(String(currentReading?.updated_at||currentReading?.created_at||Date.now()));
    img.onload=()=>{loading.hidden=true;error.hidden=true;img.hidden=false};
    img.onerror=()=>{loading.hidden=true;img.hidden=true;error.hidden=false;error.textContent="Không dựng được ảnh lá số đầy đủ. Hãy chạy pip install -r requirements.txt rồi lập lại lá số."};
    img.src=`/api/astrology/chart-image/${encodeURIComponent(readingId)}.png?v=${stamp}`;
  }

  function renderReading(wrapper,messages=[]){
    if(!wrapper)return;currentReading=wrapper;const p=wrapper.profile||{};const r=wrapper.reading||{};
    renderTraditionalChart(p, wrapper.id);
    $("#overviewText").textContent=r.overview||"";$("#personalityText").textContent=r.personality||"";const nf=r.near_future||{};$("#futurePeriod").textContent=nf.period||"";$("#futureSummary").textContent=nf.summary||"";
    const area=$("#areaGrid");area.innerHTML="";(nf.areas||[]).forEach(item=>{const card=document.createElement("article");card.className="area-card";card.innerHTML=`<div class="area-top"><strong>${escapeHtml(item.label)}</strong><b>${Number(item.score||0)}</b></div><div class="area-bar"><i style="width:${Math.max(0,Math.min(100,Number(item.score||0)))}%"></i></div><p>${escapeHtml(item.summary)}</p>`;area.appendChild(card)});
    const fillList=(sel,items)=>{const root=$(sel);root.innerHTML="";(items||[]).forEach(text=>{const li=document.createElement("li");li.textContent=text;root.appendChild(li)})};fillList("#shouldDo",r.should_do);fillList("#watchOut",r.watch_out);$("#closingText").textContent=r.closing||"";
    $("#introPanel").classList.add("hidden");$("#resultPanel").classList.remove("hidden");renderMessages(messages);window.scrollTo({top:0,behavior:"smooth"});
  }
  function renderMessages(items){const root=$("#astroChat");root.innerHTML="";(items||[]).forEach(item=>{const bubble=document.createElement("div");bubble.className=`chat-bubble ${item.role}`;if(item.role==="assistant"){const meta=item.meta||{};bubble.innerHTML=`<div>${escapeHtml(item.content)}</div>${(meta.takeaways||[]).length?`<ul class="mini-list">${meta.takeaways.map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul>`:""}${meta.caution?`<div class="caution">${escapeHtml(meta.caution)}</div>`:""}`}else bubble.textContent=item.content;root.appendChild(bubble)});root.scrollTop=root.scrollHeight}
  function appendQA(question,answer){const root=$("#astroChat");const u=document.createElement("div");u.className="chat-bubble user";u.textContent=question;root.appendChild(u);const a=document.createElement("div");a.className="chat-bubble assistant";a.innerHTML=`<div>${escapeHtml(answer.answer||"")}</div>${(answer.takeaways||[]).length?`<ul class="mini-list">${answer.takeaways.map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul>`:""}${answer.caution?`<div class="caution">${escapeHtml(answer.caution)}</div>`:""}`;root.appendChild(a);root.scrollTop=root.scrollHeight}
  async function loadOverview(){try{const data=await api("/api/astrology/overview");updateQuota(data.quota);if(data.reading)renderReading(data.reading,data.messages||[])}catch(e){if(e.message!=="auth")toast(e.message,true)}}

  $("#birthForm").addEventListener("submit",async e=>{e.preventDefault();const btn=$("#createChartBtn");btn.disabled=true;const old=btn.textContent;btn.textContent=t("loading");try{const data=await api("/api/astrology/chart",{method:"POST",body:JSON.stringify({birth_date:$("#birthDate").value,birth_time:$("#birthTime").value,birth_place:$("#birthPlace").value,gender:$("#gender").value,ui_language:lang()})});updateQuota(data.quota);renderReading(data.reading,[])}catch(err){toast(err.status===429?t("noQuota"):err.message,true)}finally{btn.disabled=false;btn.textContent=old}});
  $("#newChartBtn").addEventListener("click",()=>{$("#resultPanel").classList.add("hidden");$("#introPanel").classList.remove("hidden");window.scrollTo({top:0,behavior:"smooth"})});
  async function ask(question){question=String(question||"").trim();if(!question||!currentReading)return;const btn=$("#askBtn");btn.disabled=true;const old=btn.textContent;btn.textContent=t("asking");try{const data=await api("/api/astrology/ask",{method:"POST",body:JSON.stringify({reading_id:currentReading.id,question,ui_language:lang()})});updateQuota(data.quota);appendQA(question,data.answer);$("#questionInput").value="";$("#questionCount").textContent="0/1200"}catch(err){toast(err.status===429?t("noQuota"):err.message,true)}finally{btn.disabled=false;btn.textContent=old}}
  $("#askForm").addEventListener("submit",e=>{e.preventDefault();ask($("#questionInput").value)});$$('[data-question]').forEach(b=>b.addEventListener("click",()=>ask(b.dataset.question)));$("#questionInput").addEventListener("input",e=>$("#questionCount").textContent=`${e.target.value.length}/1200`);
  document.addEventListener("moloi:languagechange",()=>{applyText();if(currentReading)renderTraditionalChart(currentReading.profile||{}, currentReading.id)});
  document.addEventListener("DOMContentLoaded",()=>{applyText();loadOverview()});
})();
