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



/* Institution wording for "learning outcome": OUTCOME_TERM = Öğrenim | Öğrenme | Kazanım (default Öğrenim).
   Applied to static text and to dynamically rendered content; no per-string edits needed. */
(function(){
  let term='Öğrenim';
  const rx=/Öğrenim|Öğrenme(?= Çıktı)/g;
  function fix(node){
    if(term==='Öğrenim')return;
    const w=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);let n;const todo=[];
    while((n=w.nextNode())){if(n.nodeValue&&(n.nodeValue.includes('Öğrenim')||n.nodeValue.includes('ÖĞRENİM')||n.nodeValue.includes('Öğrenme Çıktı')))todo.push(n)}
    todo.forEach(t=>{t.nodeValue=t.nodeValue.replace(/Öğren(?:im|me) Çıktı(ları|sı)?/g,(m,suf)=>term==='Kazanım'?(suf==='ları'?'Kazanımlar':suf==='sı'?'Kazanımı':'Kazanım'):`${term} Çıktı${suf||''}`).replace(/Öğrenim(?! Çıktı)/g,term).replace(/ÖĞRENİM/g,term.toLocaleUpperCase('tr'))});
  }
  window.applyOutcomeTerm=function(t){term=['Öğrenim','Öğrenme','Kazanım'].includes(t)?t:'Öğrenim';fix(document.body)};
  let busy=false;
  new MutationObserver(ms=>{if(busy||term==='Öğrenim')return;busy=true;try{ms.forEach(m=>m.addedNodes.forEach(a=>{if(a.nodeType===1)fix(a);else if(a.nodeType===3&&a.parentNode)fix(a.parentNode)}))}finally{busy=false}}).observe(document.documentElement,{childList:true,subtree:true});
  fetch('/api/auth/config').then(r=>r.ok?r.json():null).then(c=>{if(c&&c.outcome_term)window.applyOutcomeTerm(c.outcome_term)}).catch(()=>{});
})();
