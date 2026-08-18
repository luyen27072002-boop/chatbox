(() => {
"use strict";
const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
let profile={}, latestCv=null, interview=null, lastManualJob=null;
let toastTimer;

async function api(url,options={}){
  const res=await fetch(url,{credentials:"same-origin",headers:{"Content-Type":"application/json",...(options.headers||{})},...options});
  let data={};try{data=await res.json()}catch{}
  if(res.status===401){location.href="/";throw new Error("auth")}
  if(!res.ok)throw new Error(data.error||`HTTP ${res.status}`);
  return data;
}
function toast(msg,error=false){const el=$("#toast");el.textContent=msg;el.hidden=false;el.classList.toggle("error",error);clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.hidden=true,3600)}
function esc(v){return String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;")}
function quota(q={}){if(q.permanent_test)return"∞";if(q.unlimited_active)return"∞";const n=Number(q.finite_remaining??((q.daily_remaining||0)+(q.welcome_remaining||0)+(q.purchased_credits||0)+(q.subscription_remaining||0)));return Number.isFinite(n)?`${Math.max(0,n)} lượt`:"—"}
function val(id){return $(id)?.value||""}
function currentJobQuery(){const selected=val("#jobCategory");return selected==="other"?val("#jobQuery").trim():selected.trim()}
function currentJobLocation(){const selected=val("#jobLocationSelect");return selected==="other"?val("#jobLocation").trim():selected.trim()}
function syncConditionalFilters(){
  const jobOther=val("#jobCategory")==="other", locationOther=val("#jobLocationSelect")==="other";
  if($("#jobQuery")){$("#jobQuery").hidden=!jobOther;if(!jobOther)$("#jobQuery").value=""}
  if($("#jobLocation")){$("#jobLocation").hidden=!locationOther;if(!locationOther)$("#jobLocation").value=""}
}
function payload(){
  return {desired_role:val("#desiredRole"),location:val("#careerLocation"),work_type:val("#workType"),seniority:val("#seniority"),skills:val("#skills"),summary:val("#summary"),experience:val("#experience"),education:val("#education"),projects:val("#projects"),languages:val("#languages")};
}

function slugifyVi(value){
  return String(value||"")
    .normalize("NFD").replace(/[\u0300-\u036f]/g,"")
    .replace(/đ/g,"d").replace(/Đ/g,"D")
    .toLowerCase().trim()
    .replace(/[^a-z0-9+#.]+/g,"-")
    .replace(/^-+|-+$/g,"");
}
function siteSearch(domain,q,location){
  const terms=[q,location].filter(Boolean).map(x=>`"${String(x).trim()}"`).join(" ");
  return `https://www.google.com/search?q=${encodeURIComponent(`site:${domain} ${terms}`)}`;
}
function nativeOrSite(domain,nativeBuilder,q,location){
  try{
    const url=nativeBuilder?nativeBuilder(q,location):"";
    if(url && /^https:\/\/[a-z0-9.-]+\//i.test(url)) return url;
  }catch{}
  return siteSearch(domain,q,location);
}
const JOB_SOURCES=[
  {
    id:"topcv",name:"TopCV",domain:"topcv.vn",group:"Việt Nam",note:"Việc làm đa ngành",
    home:"https://www.topcv.vn/",
    search:(q,l)=>q?`https://www.topcv.vn/tim-viec-lam-${slugifyVi(q)}`:"https://www.topcv.vn/"
  },
  {
    id:"vietnamworks",name:"VietnamWorks",domain:"vietnamworks.com",group:"Việt Nam",note:"Việc làm chuyên môn & doanh nghiệp",
    home:"https://www.vietnamworks.com/",
    search:(q,l)=>`https://www.vietnamworks.com/viec-lam?q=${encodeURIComponent([q,l].filter(Boolean).join(" "))}`
  },
  {
    id:"careerviet",name:"CareerViet",domain:"careerviet.vn",group:"Việt Nam",note:"Việc làm đa ngành",
    home:"https://careerviet.vn/",
    search:null
  },
  {
    id:"vieclam24h",name:"Việc Làm 24h",domain:"vieclam24h.vn",group:"Việt Nam",note:"Việc làm phổ thông & chuyên môn",
    home:"https://vieclam24h.vn/",
    search:null
  },
  {
    id:"jobsgo",name:"JobsGO",domain:"jobsgo.vn",group:"Việt Nam",note:"Nhiều tỉnh thành & ngành nghề",
    home:"https://jobsgo.vn/viec-lam.html",
    search:null
  },
  {
    id:"joboko",name:"JobOKO",domain:"vn.joboko.com",group:"Việt Nam",note:"Job search engine Việt Nam",
    home:"https://vn.joboko.com/",
    search:null
  },
  {
    id:"careerlink",name:"CareerLink",domain:"careerlink.vn",group:"Việt Nam",note:"Việc làm đa ngành",
    home:"https://www.careerlink.vn/",
    search:(q,l)=>q?`https://www.careerlink.vn/viec-lam/${slugifyVi(q)}`:"https://www.careerlink.vn/"
  },
  {
    id:"glints",name:"Glints",domain:"glints.com",group:"Việt Nam",note:"Full-time, intern, freelance",
    home:"https://glints.com/vn/viec-lam",
    search:null
  },
  {
    id:"indeed",name:"Indeed Việt Nam",domain:"vn.indeed.com",group:"Việt Nam / quốc tế",note:"Nguồn việc làm rộng",
    home:"https://vn.indeed.com/",
    search:(q,l)=>`https://vn.indeed.com/jobs?q=${encodeURIComponent(q||"")}&l=${encodeURIComponent(l||"Vietnam")}`
  },
  {
    id:"linkedin",name:"LinkedIn Jobs",domain:"linkedin.com",group:"Chuyên nghiệp",note:"Doanh nghiệp Việt Nam & quốc tế",
    home:"https://www.linkedin.com/jobs/",
    search:(q,l)=>`https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(q||"")}&location=${encodeURIComponent(l||"Vietnam")}`
  },
  {
    id:"itviec",name:"ITviec",domain:"itviec.com",group:"Công nghệ",note:"Chuyên việc IT",
    home:"https://itviec.com/it-jobs",
    search:(q,l)=>{
      if(!q)return"https://itviec.com/it-jobs";
      const k=slugifyVi(q);
      const loc=slugifyVi(l);
      const supported={"ha-noi":"ha-noi","hanoi":"ha-noi","ho-chi-minh":"ho-chi-minh","tp-hcm":"ho-chi-minh","hcm":"ho-chi-minh","da-nang":"da-nang"};
      return supported[loc]?`https://itviec.com/it-jobs/${k}/${supported[loc]}`:`https://itviec.com/it-jobs/${k}`;
    }
  },
  {
    id:"topdev",name:"TopDev",domain:"topdev.vn",group:"Công nghệ",note:"Công nghệ & nhiều nhóm nghề",
    home:"https://topdev.vn/",
    search:null
  },
  {
    id:"jobstreet",name:"JobStreet",domain:"jobstreet.vn",group:"Việt Nam / khu vực",note:"Việc làm Việt Nam & khu vực",
    home:"https://www.jobstreet.vn/",
    search:null
  }
];
function renderJobSources(){
  const q=currentJobQuery();
  const location=currentJobLocation();
  const title=q||"Việc làm";
  const where=location||"Toàn Việt Nam";
  const root=$("#jobSourceGrid");
  if(!root)return;
  $("#sourceCount").textContent=`${JOB_SOURCES.length} nguồn`;
  $("#sourceSearchSummary").textContent=`“${title}” · ${where}`;
  root.innerHTML=JOB_SOURCES.map((s,idx)=>{
    const quick=nativeOrSite(s.domain,s.search,q,location);
    const quickLabel=s.search?"Mở kết quả":"Tìm nhanh";
    return `<article class="source-card">
      <div class="source-card-top">
        <span class="source-index">${String(idx+1).padStart(2,"0")}</span>
        <span class="source-group">${esc(s.group)}</span>
      </div>
      <strong class="source-name">${esc(s.name)}</strong>
      <h3>${esc(title)}${location?` · ${esc(location)}`:""}</h3>
      <p>${esc(s.note)}</p>
      <div class="source-domain">${esc(s.domain)}</div>
      <div class="source-actions">
        <a href="${esc(quick)}" target="_blank" rel="noopener noreferrer">${quickLabel}</a>
        <a class="source-home" href="${esc(s.home)}" target="_blank" rel="noopener noreferrer">Mở nguồn</a>
      </div>
    </article>`;
  }).join("");
}
function fillProfile(p={}){
  profile=p;$("#desiredRole").value=p.desired_role||"";$("#careerLocation").value=p.location||"";$("#workType").value=p.work_type||"";$("#seniority").value=p.seniority||"";$("#skills").value=(p.skills||[]).join(", ");$("#summary").value=p.summary||"";$("#experience").value=p.experience||"";$("#education").value=p.education||"";$("#projects").value=p.projects||"";$("#languages").value=p.languages||"";$("#interviewRole").value=p.desired_role||"";
  if($("#jobCategory") && p.desired_role){
    const exact=Array.from($("#jobCategory").options).find(o=>o.value===p.desired_role);
    if(exact)$("#jobCategory").value=p.desired_role;else{$("#jobCategory").value="other";$("#jobQuery").value=p.desired_role}
  }
  if($("#jobLocationSelect") && p.location){
    const exact=Array.from($("#jobLocationSelect").options).find(o=>o.value===p.location);
    if(exact)$("#jobLocationSelect").value=p.location;else{$("#jobLocationSelect").value="other";$("#jobLocation").value=p.location}
  }
  syncConditionalFilters();
  if($("#jobCategory").value==="other" && p.desired_role)$("#jobQuery").value=p.desired_role;
  if($("#jobLocationSelect").value==="other" && p.location)$("#jobLocation").value=p.location;
  renderJobSources();
}
function renderCv(cv){
  latestCv=cv;if(!cv)return;
  const c=cv.content||cv;
  $("#cvPreview").classList.remove("empty");
  $("#cvPreview").innerHTML=`<h1>${esc(c.headline||profile.desired_role||"CV")}</h1>${c.summary?`<p>${esc(c.summary)}</p>`:""}${(c.skills||[]).length?`<h3>Kỹ năng</h3><div class="skill-chips">${c.skills.map(x=>`<span>${esc(x)}</span>`).join("")}</div>`:""}${(c.experience_bullets||[]).length?`<h3>Kinh nghiệm</h3><ul>${c.experience_bullets.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:""}${(c.project_bullets||[]).length?`<h3>Dự án</h3><ul>${c.project_bullets.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:""}${c.education?`<h3>Học vấn</h3><p>${esc(c.education).replaceAll("\n","<br>")}</p>`:""}${c.languages?`<h3>Ngôn ngữ / chứng chỉ</h3><p>${esc(c.languages).replaceAll("\n","<br>")}</p>`:""}${(c.missing_for_target||[]).length?`<div class="result-box"><b>JD còn nhắc tới:</b> ${c.missing_for_target.map(esc).join(", ")}</div>`:""}`;
}
function scoreBox(missing,match){
  const s=Number(match?.score||0);
  return `<div class="score-line"><b>Độ khớp</b><b>${s}%</b></div><div class="meter"><i style="width:${s}%"></i></div><p>${esc(match?.reason||"")}</p>${(match?.matched_skills||[]).length?`<p><b>Khớp:</b> ${match.matched_skills.map(esc).join(", ")}</p>`:""}${(missing||[]).length?`<p><b>Từ khóa nên kiểm tra:</b> ${missing.map(esc).join(", ")}</p>`:""}`;
}
async function loadOverview(){
  try{
    const d=await api("/api/career/overview");fillProfile(d.profile||{});if(d.latest_cv)renderCv(d.latest_cv);
    $("#quotaBadge").textContent=quota(d.quota);$("#profileState").textContent=d.profile_ready?"Đã có hồ sơ":"Chưa hoàn thiện";$("#savedState").textContent=`${d.saved_jobs_count||0} việc đã lưu`;
    await loadSaved();
  }catch(e){if(e.message!=="auth")toast(e.message,true)}
}
function switchTab(name){
  $$("[data-tab]").forEach(b=>b.classList.toggle("active",b.dataset.tab===name));
  $$("[data-panel]").forEach(p=>p.hidden=p.dataset.panel!==name);
  history.replaceState(null,"",name==="jobs"?"/career/jobs":"/career/cv");
}
$$("[data-tab]").forEach(b=>b.addEventListener("click",()=>switchTab(b.dataset.tab)));

$("#profileForm").addEventListener("submit",async e=>{e.preventDefault();try{const d=await api("/api/career/profile",{method:"POST",body:JSON.stringify(payload())});profile=d.profile;$("#profileSaveState").textContent="Đã lưu";$("#profileState").textContent="Đã có hồ sơ";toast("Đã lưu hồ sơ nghề nghiệp.")}catch(e){toast(e.message,true)}});

$("#analyzeCvBtn").addEventListener("click",async()=>{const b=$("#analyzeCvBtn");b.disabled=true;try{const d=await api("/api/career/cv/analyze",{method:"POST",body:JSON.stringify({profile:payload(),job_description:val("#cvJobDescription")})});const el=$("#cvAnalysis");el.innerHTML=scoreBox(d.possible_missing_keywords,d.match);el.classList.remove("hidden")}catch(e){toast(e.message,true)}finally{b.disabled=false}});

$("#improveCvBtn").addEventListener("click",async()=>{const b=$("#improveCvBtn");b.disabled=true;b.textContent="Đang tạo...";try{const d=await api("/api/career/cv/improve",{method:"POST",body:JSON.stringify({profile:payload(),job_description:val("#cvJobDescription")})});profile=payload();renderCv({content:d.content});$("#quotaBadge").textContent=quota(d.quota);toast("Đã tạo bản CV mới.")}catch(e){toast(e.message,true)}finally{b.disabled=false;b.textContent="Viết lại CV bằng AI"}});
$("#printCvBtn").addEventListener("click",()=>window.print());

$("#startInterviewBtn").addEventListener("click",async()=>{const b=$("#startInterviewBtn");b.disabled=true;try{interview=await api("/api/career/interview/start",{method:"POST",body:JSON.stringify({role:val("#interviewRole"),job_description:val("#interviewJd")})});$("#interviewEmpty").hidden=true;$("#interviewLive").hidden=false;$("#questionRole").textContent=interview.role;showQuestion()}catch(e){toast(e.message,true)}finally{b.disabled=false}});
function showQuestion(){if(!interview)return;const i=interview.current_index||0;$("#questionNumber").textContent=`Câu ${i+1}/${interview.questions.length}`;$("#questionText").textContent=interview.questions[i]||"Đã hoàn thành";$("#interviewAnswer").value="";$("#interviewFeedback").classList.add("hidden")}
$("#submitInterviewBtn").addEventListener("click",async()=>{if(!interview)return;const b=$("#submitInterviewBtn");b.disabled=true;b.textContent="Đang đánh giá...";try{const d=await api("/api/career/interview/answer",{method:"POST",body:JSON.stringify({session_id:interview.id,answer:val("#interviewAnswer")})});$("#quotaBadge").textContent=quota(d.quota);const f=d.feedback||{}, el=$("#interviewFeedback");el.innerHTML=`<div class="feedback-score">${Number(f.score||0)}/100</div>${(f.what_worked||[]).length?`<h4>Điểm tốt</h4><ul>${f.what_worked.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:""}${(f.improve||[]).length?`<h4>Cần cải thiện</h4><ul>${f.improve.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:""}${f.better_structure?`<p><b>Cấu trúc gợi ý:</b> ${esc(f.better_structure)}</p>`:""}<button id="nextQuestionBtn" class="secondary" type="button">${d.completed?"Hoàn thành":"Câu tiếp theo"}</button>`;el.classList.remove("hidden");interview.current_index=d.current_index;$("#nextQuestionBtn").addEventListener("click",()=>{if(d.completed){toast("Đã hoàn thành phiên phỏng vấn.");$("#interviewLive").hidden=true;$("#interviewEmpty").hidden=false;$("#interviewEmpty").innerHTML="<h3>Đã hoàn thành</h3><p>Bạn có thể bắt đầu một phiên mới để luyện tiếp.</p>"}else showQuestion()})}catch(e){toast(e.message,true)}finally{b.disabled=false;b.textContent="Gửi để nhận phản hồi"}});

function jobCard(j){
  const m=j.match||{}, url=j.url?`<a href="${esc(j.url)}" target="_blank" rel="noopener noreferrer">Xem tin / ứng tuyển</a>`:"";
  const source=esc(j.source||j.provider||"Nguồn tuyển dụng");
  const sourceTypeLabel={
    government:"Nguồn nhà nước",
    recruiter:"Headhunter",
    ats:"Career site",
    company_career:"Website công ty",
    social:"Bài đăng công khai",
    professional_network:"Mạng nghề nghiệp",
    job_board:"Job board"
  }[j.source_type]||"Nguồn tuyển dụng";
  return `<article class="job-card real-job-card"><div class="job-top"><div><div class="real-source">${source} · ${esc(sourceTypeLabel)}</div><h3>${esc(j.title)}</h3><div class="company">${esc(j.company||j.source||"Nguồn tuyển dụng")}</div></div><div class="job-match">${Number(m.score||0)}%</div></div><div class="job-meta">${j.location?`<span>${esc(j.location)}${j.location_fallback?" · kết quả toàn Việt Nam":""}</span>`:""}${j.job_type?`<span>${esc(j.job_type)}</span>`:""}${j.salary?`<span>${esc(j.salary)}</span>`:""}${j.publication_date?`<span>${esc(j.publication_date)}</span>`:""}</div><div class="job-snippet">${esc(j.description||"")}</div>${(m.matched_skills||[]).length?`<div class="matched-skills"><b>Khớp hồ sơ:</b> ${m.matched_skills.map(esc).join(", ")}</div>`:""}<div class="job-actions">${url}<button class="save-job" type="button">Lưu việc</button></div></article>`;
}
$("#searchJobsBtn").addEventListener("click",()=>{renderJobSources();searchJobs()});
["#jobCategory","#jobLocationSelect"].forEach(sel=>$(sel)?.addEventListener("change",()=>{syncConditionalFilters();renderJobSources()}));
["#jobQuery","#jobLocation"].forEach(sel=>$(sel)?.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();renderJobSources();searchJobs()}}));
["#jobTypeFilter","#jobLevelFilter","#postedDaysFilter","#radiusFilter","#sortFilter","#salaryOnlyFilter"].forEach(sel=>{
  $(sel)?.addEventListener("change",()=>{
    document.body.dataset.jobFiltersDirty="1";
  });
});
async function searchJobs(){
  const b=$("#searchJobsBtn"), q=currentJobQuery(), location=currentJobLocation();
  if(!q){toast("Hãy chọn công việc hoặc nhập từ khóa.",true);return}
  b.disabled=true;$("#jobResults").innerHTML='<div class="empty-state">Đang tìm việc tại Việt Nam...</div>';
  try{
    const params=new URLSearchParams({q,location,job_type:val("#jobTypeFilter"),level:val("#jobLevelFilter"),posted_days:val("#postedDaysFilter")||"0",radius:val("#radiusFilter"),salary_only:$("#salaryOnlyFilter")?.checked?"1":"0",sort:val("#sortFilter")||"match",limit:"30"});
    const d=await api(`/api/career/jobs/search?${params.toString()}`);
    const cachedProviders=[
      d.providers?.jooble?.cached?"Jooble":"",
      d.providers?.brave?.cached?"multi-source":""
    ].filter(Boolean);
    const cacheHint=cachedProviders.length?` Đang dùng cache: ${cachedProviders.join(", ")}.`:"";
    $("#providerNotice").textContent=(d.provider_notice||d.attribution||"")+cacheHint;
    document.body.dataset.jobFiltersDirty="0";
    const jobs=d.jobs||[];
    $("#jobResults").innerHTML=jobs.length?jobs.map(jobCard).join(""):`<div class="empty-state"><div><h3>Chưa thấy việc Việt Nam cụ thể</h3><p>${d.providers?.jooble?.configured===false?"Nguồn việc Việt Nam chưa được kết nối trên máy chủ này. Các bộ lọc đã sẵn sàng; cần kết nối provider để tải title job thật.":"Không phải do không có việc. Hãy xem thông báo nguồn ngay phía trên; nếu Brave/Jooble báo lỗi, chạy diagnose_job_sources.py để kiểm tra kết nối."}</p></div></div>`;
    $$(".save-job").forEach((btn,i)=>btn.addEventListener("click",()=>saveJob(jobs[i])));
  }catch(e){$("#jobResults").innerHTML='<div class="empty-state">Không tải được nguồn việc làm.</div>';toast(e.message,true)}
  finally{b.disabled=false}
}

async function saveJob(job){try{await api("/api/career/jobs/save",{method:"POST",body:JSON.stringify({job})});toast("Đã lưu việc.");await loadSaved()}catch(e){toast(e.message,true)}}
async function loadSaved(){try{const d=await api("/api/career/jobs/saved"), root=$("#savedJobs");const jobs=d.jobs||[];root.innerHTML=jobs.length?jobs.map(j=>`<div class="saved-item" data-id="${esc(j.id)}"><strong>${esc(j.title)}</strong><small>${esc(j.company||j.source||"")}</small><div><span>${Number(j.match?.score||j.match_score||0)}% phù hợp</span><button type="button">Xóa</button></div></div>`).join(""):'<p class="disclaimer">Chưa lưu việc nào.</p>';$$(".saved-item button").forEach(btn=>btn.addEventListener("click",async()=>{const item=btn.closest(".saved-item");try{await api(`/api/career/jobs/saved/${encodeURIComponent(item.dataset.id)}`,{method:"DELETE"});await loadSaved()}catch(e){toast(e.message,true)}}))}catch{}}

$("#analyzeJobBtn").addEventListener("click",async()=>{const b=$("#analyzeJobBtn");b.disabled=true;try{const d=await api("/api/career/jobs/analyze",{method:"POST",body:JSON.stringify({title:val("#manualJobTitle"),company:val("#manualJobCompany"),url:val("#manualJobUrl"),description:val("#manualJobDescription"),source:"Tin bạn nhập"})});lastManualJob=d.job;const el=$("#manualJobResult");el.innerHTML=scoreBox([],d.job.match)+`<button id="saveManualJobBtn" class="primary" type="button">Lưu việc này</button>`;el.classList.remove("hidden");$("#saveManualJobBtn").addEventListener("click",()=>saveJob(lastManualJob))}catch(e){toast(e.message,true)}finally{b.disabled=false}});

document.addEventListener("DOMContentLoaded",()=>{switchTab(window.__CAREER_INITIAL_MODE__==="jobs"?"jobs":"cv");syncConditionalFilters();renderJobSources();loadOverview()});
})();