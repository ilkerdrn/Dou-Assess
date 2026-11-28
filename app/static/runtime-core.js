// DOU Assess 6.70 — shared browser runtime
// Loaded before app.js so feature files can share state, HTTP/auth helpers and safe rendering utilities.
window.state = { programs:[], courses:[], students:[], exams:[], currentExam:null, authConfig:null, currentUser:null, pilotUsers:[], users:[], academicPeriods:[], syncRuns:[], currentOutcomeData:null, currentWizardStep:1, examBankRows:[], examBankSelected:new Set(), dragQuestionId:null, qualityDashboard:null, qualityDrilldown:null, qualityLoFilter:null, pilotReadiness:null, pilotIssues:[], pilotUatRuns:[], feedbackRows:[], onboardingStep:0, feedbackSource:"dashboard", dataView:"programs", dataEnrollmentRows:[], outcomeEditLoId:null, outcomeEditPoId:null, examWorkspaceSummary:null, commandIndex:0, commandRows:[], selectedCourseId:null, courseAnalytics:null, programAnalytics:null, studentCard:null, programReviewTemplates:[], programReviewRows:[], currentProgramReview:null, evidenceHubOffset:0, evidenceHubLimit:20, evidenceHubTotal:0, evidenceHubTargetSection:null, evidenceHubCurrent:null , bankOffset:0, bankLimit:60, bankHasNext:false, studentDirectoryOffset:0, studentDirectoryLimit:100, studentDirectoryHasNext:false, directorySummary:{programs:0,courses:0,students:0,exams:0,students_by_program:{},courses_by_program:{},exams_by_program:{}} };

function msgText(payload){
  if(!payload) return 'İşlem tamamlanamadı.';
  if(typeof payload === 'string') return payload;
  if(payload.error){
    const e=payload.error;
    const raw=e.details;
    const details=Array.isArray(raw)?raw.filter(Boolean):(raw && typeof raw==='object'?(Array.isArray(raw.issues)?raw.issues:[raw.message||JSON.stringify(raw)]):[]);
    return [e.message || 'İşlem tamamlanamadı.', ...details.map(x=>typeof x==='string'?x:JSON.stringify(x))].filter(Boolean).join('\n');
  }
  if(payload.detail){
    if(typeof payload.detail==='string') return payload.detail;
    if(Array.isArray(payload.detail)) return payload.detail.map(x=>x.msg || JSON.stringify(x)).join('\n');
    if(typeof payload.detail==='object'){
      const d=payload.detail;
      return [d.message, ...(Array.isArray(d.issues)?d.issues:[])].filter(Boolean).join('\n') || JSON.stringify(d);
    }
  }
  return payload.message || JSON.stringify(payload);
}

async function api(method,path,body){
  const opts={method,headers:{}};
  if(state.authConfig?.auth_required){
    const token=sessionStorage.getItem('douEntraAccessToken');
    if(token) opts.headers['Authorization']=`Bearer ${token}`;
  }else if(state.authConfig){
    const email=localStorage.getItem('douPilotUser');
    if(email) opts.headers['X-DOU-Pilot-User']=email;
  }
  if(body instanceof FormData){ opts.body=body; }
  else if(body!==undefined && body!==null){ opts.headers['Content-Type']='application/json'; opts.body=JSON.stringify(body); }
  const r=await fetch(path,opts);
  const ct=r.headers.get('content-type')||'';
  const data=ct.includes('application/json')?await r.json():await r.text();
  if(!r.ok) throw new Error(msgText(data));
  return data;
}

function pilotAuthHeaders(){
  const headers={};
  if(state.authConfig?.auth_required){
    const token=sessionStorage.getItem('douEntraAccessToken');
    if(token) headers['Authorization']=`Bearer ${token}`;
  }else if(state.authConfig){
    const email=localStorage.getItem('douPilotUser');
    if(email) headers['X-DOU-Pilot-User']=email;
  }
  return headers;
}

async function downloadApi(path,filename,open=false){
  const r=await fetch(path,{headers:pilotAuthHeaders()});
  if(!r.ok){
    const ct=r.headers.get('content-type')||'';
    const data=ct.includes('application/json')?await r.json():await r.text();
    throw new Error(msgText(data));
  }
  const blob=await r.blob();
  const url=URL.createObjectURL(blob);
  if(open){
    window.open(url,'_blank','noopener');
    setTimeout(()=>URL.revokeObjectURL(url),60000);
    return;
  }
  const a=document.createElement('a');
  a.href=url;
  a.download=filename||'download';
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),10000);
}

function toast(text,type='ok'){
  const el=document.getElementById('toast'); el.textContent=text; el.className=`toast ${type} show`;
  clearTimeout(window.__toast); window.__toast=setTimeout(()=>el.classList.remove('show'),4500);
}
function esc(s){return String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}




/* 6.70.11.4 — Pilot login runtime hardening
   Login is owned by the small shared runtime so a later app initialization error
   cannot trap an already verified pilot user behind the login gate. */
(function installPilotLoginRuntime(){
  const SESSION_KEY='douPilotSession';
  const USER_KEY='douPilotUser';

  function loginError(message=''){
    const err=document.getElementById('pilotLoginError');
    if(!err)return;
    err.textContent=String(message||'');
    err.classList.toggle('show',!!message);
  }
  function loginBusy(busy){
    const box=document.getElementById('pilotLoginBox');
    const btn=document.getElementById('loginPilotBtn');
    box?.classList.toggle('is-busy',!!busy);
    if(btn){
      btn.disabled=!!busy;
      const label=busy?'Giriş yapılıyor… ':'Sisteme giriş yap ';
      if(btn.firstChild)btn.firstChild.textContent=label;
    }
  }
  async function readResponse(r){
    const ct=r.headers.get('content-type')||'';
    const data=ct.includes('application/json')?await r.json():await r.text();
    if(r.ok)return data;
    throw new Error(typeof window.msgText==='function'?window.msgText(data):(data?.error?.message||data?.detail||data?.message||`HTTP ${r.status}`));
  }
  async function verifyPilot(email){
    const chosen=String(email||'').trim().toLowerCase();
    if(!chosen)throw new Error('Lütfen bir akademik kullanıcı seçin.');
    const r=await fetch('/api/auth/me',{
      method:'GET',
      cache:'no-store',
      headers:{'X-DOU-Pilot-User':chosen,'Cache-Control':'no-cache'}
    });
    const user=await readResponse(r);
    if(!user?.email)throw new Error('Kullanıcı oturumu doğrulanamadı.');
    return {chosen,user};
  }
  function paintVerifiedUser(chosen,user){
    window.state=window.state||{};
    window.state.currentUser=user;
    const n=document.getElementById('currentUserName');
    if(n)n.textContent=user.display_name||user.email;
    const roles=document.getElementById('currentUserRoles');
    if(roles)roles.textContent=(user.roles||[]).map(x=>x.role_label||x.role).join(' · ')||'Rol atanmamış';
    const side=document.getElementById('pilotUserSelect');
    if(side&&[...side.options].some(o=>o.value===chosen))side.value=chosen;
    document.body.classList.remove('login-active');
    document.getElementById('loginGate')?.classList.add('hidden');
    document.querySelector('.shell')?.classList.remove('app-shell-hidden');
    document.getElementById('onboardingModal')?.classList.add('hidden');
  }
  async function finishApplication(chosen,user){
    paintVerifiedUser(chosen,user);
    try{ if(typeof window.renderCurrentUserScope==='function')window.renderCurrentUserScope(); }catch(e){console.warn('renderCurrentUserScope',e);}
    try{ if(typeof window.applyRoleUI==='function')window.applyRoleUI(); }catch(e){console.warn('applyRoleUI',e);}
    try{ if(typeof window.enterApplication==='function')window.enterApplication(); }catch(e){console.warn('enterApplication',e);}
    try{ if(typeof window.checkReady==='function')await window.checkReady(); }catch(e){console.warn('checkReady',e);}
    try{ if(typeof window.refreshCore==='function')await window.refreshCore(); }catch(e){console.warn('refreshCore',e);}
    try{ if(typeof window.refreshNotificationBadge==='function')await window.refreshNotificationBadge(); }catch(e){console.warn('refreshNotificationBadge',e);}
    try{
      if(typeof window.showPage==='function'){
        const names=new Set(user.role_names||[]);
        const qualityOnly=names.has('quality')&&!names.has('admin');
        window.showPage(qualityOnly?'quality360':'dashboard');
      }
    }catch(e){console.warn('showPage',e);}
  }
  async function robustPilotLogin(email){
    loginError('');
    loginBusy(true);
    try{
      const {chosen,user}=await verifyPilot(email);
      localStorage.setItem(USER_KEY,chosen);
      localStorage.setItem(SESSION_KEY,'1');
      await finishApplication(chosen,user);
      return true;
    }catch(err){
      localStorage.removeItem(SESSION_KEY);
      loginError(err?.message||'Pilot kullanıcı girişi başarısız.');
      document.body.classList.add('login-active');
      document.getElementById('loginGate')?.classList.remove('hidden');
      document.querySelector('.shell')?.classList.add('app-shell-hidden');
      return false;
    }finally{loginBusy(false);}
  }
  window.robustPilotLogin=robustPilotLogin;

  document.addEventListener('click',event=>{
    const btn=event.target?.closest?.('#loginPilotBtn');
    if(!btn)return;
    event.preventDefault();
    event.stopImmediatePropagation();
    robustPilotLogin(document.getElementById('loginPilotUser')?.value);
  },true);

  document.addEventListener('keydown',event=>{
    if(event.key!=='Enter'||event.target?.id!=='loginPilotUser')return;
    event.preventDefault();
    event.stopImmediatePropagation();
    robustPilotLogin(event.target.value);
  },true);

  // In a fresh/incognito window populate the pilot selector independently from app.js.
  setTimeout(async()=>{
    try{
      const cfg=await readResponse(await fetch('/api/auth/config',{cache:'no-store'}));
      window.state=window.state||{};window.state.authConfig=cfg;
      if(cfg.auth_required)return;
      const select=document.getElementById('loginPilotUser');
      if(select&&!select.options.length){
        const saved=localStorage.getItem(USER_KEY)||'pilot-admin@local';
        const users=await readResponse(await fetch('/api/auth/pilot-users',{cache:'no-store',headers:{'X-DOU-Pilot-User':saved}}));
        if(Array.isArray(users)){
          select.innerHTML=users.map(x=>`<option value="${String(x.email||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}">${String(x.display_name||x.email||'Kullanıcı').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))} · ${String(x.email||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}</option>`).join('');
          if([...select.options].some(o=>o.value===saved))select.value=saved;
        }
      }
      // If a verified pilot session already exists, never let later page-init errors re-gate it.
      const remembered=localStorage.getItem(USER_KEY);
      if(localStorage.getItem(SESSION_KEY)==='1'&&remembered){
        const {chosen,user}=await verifyPilot(remembered);
        await finishApplication(chosen,user);
      }
    }catch(err){
      console.warn('Pilot login runtime bootstrap',err);
    }
  },0);
})();
