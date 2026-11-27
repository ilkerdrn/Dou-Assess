const state = window.state;

// CSP (style-src 'self', no unsafe-inline) blocks inline style="" attributes rendered
// via innerHTML, which silently breaks every dynamic width/height/left/custom-property
// bar and gauge in the UI. CSSOM writes (el.style.x=...) are not affected by style-src,
// so dynamic styling is deferred to data-style and applied here instead of in markup.
function hydrateDeferredStyles(root){
  const apply=el=>{ el.style.cssText+=(el.style.cssText?';':'')+el.getAttribute('data-style'); el.removeAttribute('data-style'); };
  if(root.nodeType===1&&root.hasAttribute('data-style'))apply(root);
  if(root.querySelectorAll)root.querySelectorAll('[data-style]').forEach(apply);
}
new MutationObserver(muts=>{muts.forEach(m=>m.addedNodes.forEach(n=>{if(n.nodeType===1)hydrateDeferredStyles(n);}));}).observe(document.body,{childList:true,subtree:true});
hydrateDeferredStyles(document.body);

const pageMeta = {
  mycourses:['Derslerim','Dersinizi seçin; sınav, soru, değerlendirme, analiz ve iyileştirme işlemlerini aynı bağlamda yönetin.','Çalışma Alanım'],
  coursestudents:['Ders Öğrencileri','Seçili dersin öğrenci kapsamını sade bir listede görüntüleyin.','Benim Çalışma Alanım'],
  courseanalytics:['Ders Analizi','Dersin dönem ve yıllar arası başarı, Öğrenim Çıktısı ve risk eğilimlerini inceleyin.','Analiz'],
  programanalytics:['Program Analizi','Program çıktıları, riskli dersler ve dönem trendlerini tek ekranda izleyin.','Analiz'],
  studentcards:['Öğrenci Karneleri','Her öğrenci için bireysel ÖÇ, PÇ, ders gelişimi ve doğrulanabilir PDF karnesini görüntüleyin.','Analiz'],
  programs:['Programlar','Akademik program kapsamını yönetin.','Yönetim'],
  courses:['Dersler','Ders ve öğretim elemanı kapsamını yönetin.','Yönetim'],
  exams:['Sınavlarım','Derslerinizde sınav oluşturun, uygulayın ve sonuçlandırın.','Çalışma Alanım'],
  students:['Öğrenciler','Akademik öğrenci kapsamını yönetin.','Yönetim'],
  dashboard:['Genel Bakış','Bugünkü akademik işleri ve sistem durumunu izleyin.','İzleme'],
  import:['Kurumsal Pilot & UAT','OBS, dönem, kurulum, backup ve kullanıcı kabul sürecini yönetin.','Sistem'],
  data:['Akademik Veri','Program, ders, öğretim elemanı ve öğrenci kayıtlarını yönetin.','Akademik Yapı'],
  outcomes:['Öğrenim ve Program Çıktıları','Ders öğrenim çıktıları, program çıktıları ve 1–5 katkı matrisini yönetin.','Akademik Yapı'],
  curriculummap:['Müfredat Haritası','Derslerin Program Çıktılarını I/R/M düzeyinde nasıl kapsadığını ve müfredat boşluklarını yönetin.','Akademik Yapı'],
  assessmentmeasures:['Ölçme Planı & Rubrikler','Sınav, proje, ödev, sunum ve uygulama ölçmelerini rubrik ve Öğrenim Çıktılarıyla yönetin.','Akademik Yapı'],
  surveys:['Anket & Dolaylı Ölçüm','Öğrenci, mezun, işveren ve paydaş görüşlerini Program Çıktılarıyla kanıt temelli izleyin.','Akademik Yapı'],
  assessmentassurance:['Ölçme Güvence Planı','Her Program Çıktısını yıllık doğrudan/dolaylı ölçme planı, hedef ve review snapshot ile güvence altına alın.','Kalite'],
  bank:['Soru Havuzu','Ders bazlı, çoklu Öğrenim Çıktısı destekli yeniden kullanılabilir soru kütüphanesi.','Sınav Yönetimi'],
  print:['Basım','Kâğıtları indirin, yoklama listesini alın ve basımı onaylayın.','Sınav Yönetimi'],
  scan:['Optik & Kontrol','Toplu tarama, otomatik eşleştirme ve şüpheli işaret kontrolü.','Sınav Yönetimi'],
  grade:['Puanlama','Klasik ve öğrenci bazlı değerlendirmeyi tamamlayın.','Sınav Yönetimi'],
  analytics:['Sınav Analizi','Snapshot üzerinden öğrenci, soru, Öğrenim Çıktısı ve Program Çıktısı performansını analiz edin.','Analiz & Akreditasyon'],
  quality:['Kalite Dashboard','Program performansını Program Çıktısı heatmap ve kök neden drill-down ile izleyin.','Analiz & Akreditasyon'],
  institutionalreadiness:['Kurumsal Hazırlık','Program ve akreditasyon kuruluşu bazında hazırlık, kanıt, açık ve sorumlulukları kurum çapında izleyin.','Kalite'],
  programreview:['Program Review','Periyodik program değerlendirmesini contributor, reviewer, kanıt ve final snapshot zinciriyle yönetin.','Kalite'],
  evidencehub:['Kanıt Merkezi','Sınav, Quality360 ve kontrollü doküman kanıtlarını tek arama, etiket ve yeniden kullanım yüzeyinde yönetin.','Kalite'],
  acceptance:['Canlı Kabul','Production release için kurum bağımlı kabul kapılarını kanıtla kapatın.','Sistem'],
  quality360:['Kalite & Akreditasyon','MEDEK, YÖKAK, PUKÖ, paydaş, mezun, kadro, altyapı ve ÖDR merkezini yönetin.','Analiz & Akreditasyon'],
  accreditation:['Akreditasyon','Dönem matrisi, iyileştirme, temsilî kanıt ve paket sürecini yönetin.','Analiz & Akreditasyon'],
  evidence:['Kanıt Yönetimi','Sınav ve akreditasyon kanıt dosyalarını yönetin.','Analiz & Akreditasyon'],
  users:['Kullanıcı & Yetki','Kurumsal kimlik, rol ve akademik kapsam atamalarını yönetin.','Sistem'],
  feedback:['Geri Bildirim','Pilot kullanıcı geri bildirimlerini izleyin ve sonuçlandırın.','Sistem'],
  security:['Sistem & Güvenlik','Sağlık, production güvenliği ve güvenlik olaylarını izleyin.','Sistem']
};

const DELEGATED_ACTIONS=new Set([
  'showPage','downloadObsGrades','continueExamFromDashboard','editCourse','downloadCourseGradebook','openEnrollmentForCourse','removeCourse','editProgram','removeProgram','editStudent','removeStudent','removeAcademicEnrollment','pilotGoAction','setAcademicPeriodStatus','openExam','moveExamQuestion','editQuestion','removeQuestion','editBank','archiveBank','openQualityCourse','setQualityLoFilter','openAccredExam','openEvidenceExam','freezeRepresentatives','saveImprovement','addImprovement','reviewFeedback','resolveFeedback','removeUserRole','toggleUserActive','closeOnboarding','hideQualityDrilldown','editLearningOutcome','cancelLearningOutcomeEdit','saveLearningOutcomeEdit','deleteLearningOutcome','editProgramOutcome','cancelProgramOutcomeEdit','saveProgramOutcomeEdit','deleteProgramOutcome','goExamNextAction','syncExamStudentsNow','openExamStudentManager','normalizeExamPointsFromReadiness','openExamCourseEnrollment'
]);
function splitDelegatedActionParts(raw,separator){
  const out=[];let buf='',quote='',depth=0;
  for(let i=0;i<raw.length;i++){
    const ch=raw[i];
    if(quote){buf+=ch;if(ch===quote&&raw[i-1]!=='\\')quote='';continue;}
    if(ch==="'"||ch==='"'){quote=ch;buf+=ch;continue;}
    if(ch==='('){depth++;buf+=ch;continue;}
    if(ch===')'){depth=Math.max(0,depth-1);buf+=ch;continue;}
    if(ch===separator&&depth===0){if(buf.trim())out.push(buf.trim());buf='';continue;}
    buf+=ch;
  }
  if(buf.trim())out.push(buf.trim());return out;
}
function parseDelegatedArg(raw){
  const v=raw.trim();
  if(!v)return undefined;
  if(v==='true')return true;if(v==='false')return false;if(v==='null')return null;
  if(/^-?\d+(?:\.\d+)?$/.test(v))return Number(v);
  if((v.startsWith("'")&&v.endsWith("'"))||(v.startsWith('"')&&v.endsWith('"'))){
    return v.slice(1,-1).replace(/\\(['"\\])/g,'$1');
  }
  throw new Error(`Geçersiz buton argümanı: ${v}`);
}
function runDelegatedAction(raw){
  for(const cmd of splitDelegatedActionParts(String(raw||''),';')){
    const match=cmd.match(/^([A-Za-z_$][\w$]*)\((.*)\)$/s);
    if(!match||!DELEGATED_ACTIONS.has(match[1]))throw new Error(`İzin verilmeyen buton eylemi: ${cmd}`);
    const fn=window[match[1]];
    if(typeof fn!=='function')throw new Error(`Buton eylemi bulunamadı: ${match[1]}`);
    const argText=match[2].trim();
    const args=argText?splitDelegatedActionParts(argText,',').map(parseDelegatedArg):[];
    fn(...args);
  }
}
window.hideQualityDrilldown=function(){document.getElementById('qualityDrilldown')?.classList.add('hidden');};
document.addEventListener('click',event=>{
  const trigger=event.target.closest?.('[data-action-call]');
  if(!trigger)return;
  event.preventDefault();
  try{runDelegatedAction(trigger.dataset.actionCall);}catch(err){console.error(err);toast(err.message||'Buton işlemi çalıştırılamadı.','error');}
});


let workflowModalResolve=null;
function closeWorkflowModal(result=null){
  const modal=document.getElementById('workflowModal');
  if(!modal)return;
  modal.classList.add('hidden');
  document.body.classList.remove('modal-open');
  const resolve=workflowModalResolve;workflowModalResolve=null;
  if(resolve)resolve(result);
}
function workflowForm({eyebrow='İŞLEM',title='İşlemi tamamla',description='',submitLabel='Kaydet',fields=[]}={}){
  const modal=document.getElementById('workflowModal'),box=document.getElementById('workflowModalFields');
  if(!modal||!box)return Promise.resolve(null);
  document.getElementById('workflowModalEyebrow').textContent=eyebrow;
  document.getElementById('workflowModalTitle').textContent=title;
  document.getElementById('workflowModalDescription').textContent=description;
  document.getElementById('workflowModalSubmit').textContent=submitLabel;
  box.innerHTML=fields.map((f,i)=>{
    const id=`workflowField${i}`; const req=f.required?'required':''; const value=esc(f.value??'');
    if(f.type==='textarea')return `<label>${esc(f.label)}<textarea id="${id}" data-workflow-name="${esc(f.name)}" rows="${f.rows||4}" ${req} placeholder="${esc(f.placeholder||'')}">${value}</textarea></label>`;
    if(f.type==='select')return `<label>${esc(f.label)}<select id="${id}" data-workflow-name="${esc(f.name)}" ${req}>${(f.options||[]).map(o=>{const v=typeof o==='string'?o:o.value,l=typeof o==='string'?o:o.label;return `<option value="${esc(v)}" ${String(v)===String(f.value??'')?'selected':''}>${esc(l)}</option>`}).join('')}</select></label>`;
    return `<label>${esc(f.label)}<input id="${id}" data-workflow-name="${esc(f.name)}" type="${esc(f.type||'text')}" value="${value}" ${req} placeholder="${esc(f.placeholder||'')}" ${f.readonly?'readonly':''}></label>`;
  }).join('');
  modal.classList.remove('hidden');document.body.classList.add('modal-open');
  setTimeout(()=>box.querySelector('input:not([readonly]),textarea,select')?.focus(),30);
  return new Promise(resolve=>{if(workflowModalResolve)workflowModalResolve(null);workflowModalResolve=resolve;});
}
document.getElementById('workflowModalClose')?.addEventListener('click',()=>closeWorkflowModal(null));
document.getElementById('workflowModalCancel')?.addEventListener('click',()=>closeWorkflowModal(null));
document.getElementById('workflowModal')?.addEventListener('click',e=>{if(e.target.id==='workflowModal')closeWorkflowModal(null);});
document.getElementById('workflowModalForm')?.addEventListener('submit',e=>{e.preventDefault();const out={};document.querySelectorAll('#workflowModalFields [data-workflow-name]').forEach(el=>out[el.dataset.workflowName]=el.value);closeWorkflowModal(out);});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!document.getElementById('workflowModal')?.classList.contains('hidden'))closeWorkflowModal(null);});

function roleNames(){return new Set(state.currentUser?.role_names||[]);}
function hasAnyRole(...roles){const names=roleNames();return roles.some(r=>names.has(r));}
function isAdmin(){return hasAnyRole('admin');}
function canAcademicMaster(){return hasAnyRole('admin','program_head');}
function canAccreditation(){return hasAnyRole('admin','quality','program_head');}
function isQualityOnly(){const n=roleNames();return n.has('quality')&&!n.has('admin');}

function initials(name){return String(name||'DA').trim().split(/\s+/).slice(0,2).map(x=>x[0]||'').join('').toUpperCase()||'DA';}
function renderCurrentUserScope(){
  if(!state.currentUser)return;
  const avatar=document.getElementById('identityAvatar');if(avatar)avatar.textContent=initials(state.currentUser.display_name||state.currentUser.email);
  const scope=document.getElementById('currentUserScope');if(!scope)return;
  const courseCount=state.courses?.length||0, programCount=state.programs?.length||0;
  if(hasAnyRole('admin'))scope.textContent=`Tüm kurum · ${programCount} program · ${courseCount} ders`;
  else if(hasAnyRole('quality'))scope.textContent=`Akreditasyon görünümü · ${programCount} program · ${courseCount} ders`;
  else if(hasAnyRole('program_head'))scope.textContent=`Akademik kapsam · ${programCount} program · ${courseCount} ders`;
  else scope.textContent=`Öğretim elemanı · ${courseCount} yetkili ders`;
}
function showLoginGate(){
  document.getElementById('loginGate')?.classList.remove('hidden');
  document.querySelector('.shell')?.classList.add('app-shell-hidden');
}
function enterApplication(){
  document.getElementById('loginGate')?.classList.add('hidden');
  document.querySelector('.shell')?.classList.remove('app-shell-hidden');
}

function table(headers,rows){
  if(!rows.length) return '<p class="muted">Henüz veri yok.</p>';
  return `<table class="table"><thead><tr>${headers.map(h=>`<th>${esc(h[0])}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${headers.map(h=>`<td>${esc(r[h[1]])}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}

function choiceObject(prefix){
  const out={};
  ['A','B','C','D','E'].forEach(k=>{const el=document.getElementById(`${prefix}Choice${k}`);const v=el?.value.trim();if(v)out[k]=v;});
  return Object.keys(out).length?out:null;
}
function fillChoices(prefix,choices){
  ['A','B','C','D','E'].forEach(k=>{const el=document.getElementById(`${prefix}Choice${k}`);if(el)el.value=choices?.[k]||'';});
}
function fileToDataUrl(file){return new Promise((resolve,reject)=>{if(!file)return resolve(null);if(!['image/png','image/jpeg'].includes(file.type))return reject(new Error('Soru görseli PNG veya JPG olmalıdır.'));if(file.size>5*1024*1024)return reject(new Error('Soru görseli en fazla 5 MB olabilir.'));const r=new FileReader();r.onload=()=>resolve(String(r.result||''));r.onerror=()=>reject(new Error('Görsel okunamadı.'));r.readAsDataURL(file);});}
function setQuestionImagePreview(id,data){const box=document.getElementById(id);if(!box)return;box.dataset.imageData=data||'';box.innerHTML=data?`<img src="${data}" alt="Soru görseli"><button type="button" class="ghost small" data-clear-question-image="${id}">Görseli kaldır</button>`:'';}
const assessmentEngine=window.DOUAssessmentEngine||{};
const parseRubricText=assessmentEngine.parseRubricText||function(){throw new Error('Assessment Engine modülü yüklenemedi.');};
const formatRubric=assessmentEngine.formatRubric||function(){return '';};
document.addEventListener('click',ev=>{const b=ev.target.closest('[data-clear-question-image]');if(!b)return;setQuestionImagePreview(b.dataset.clearQuestionImage,'');const input=b.dataset.clearQuestionImage==='qImagePreview'?document.getElementById('qImage'):document.getElementById('bankImage');if(input)input.value='';});
function renderChoices(choices){
  if(!choices) return '';
  return `<div class="option-list">${Object.entries(choices).map(([k,v])=>`<div><b>${esc(k)})</b> ${esc(v)}</div>`).join('')}</div>`;
}
function syncQuestionTypeUI(){
  const mcq=document.getElementById('qType').value==='mcq';
  document.getElementById('correctWrap').classList.toggle('hidden',!mcq);
  document.getElementById('qChoices').classList.toggle('hidden',!mcq);
  document.getElementById('qAnswerLinesWrap').classList.toggle('hidden',mcq);
  document.getElementById('qRubricWrap')?.classList.toggle('hidden',mcq);
}
function syncBankTypeUI(){
  const mcq=document.getElementById('bankType').value==='mcq';
  document.getElementById('bankCorrectWrap').classList.toggle('hidden',!mcq);
  document.getElementById('bankChoices').classList.toggle('hidden',!mcq);
  document.getElementById('bankAnswerLinesWrap').classList.toggle('hidden',mcq);
  document.getElementById('bankRubricWrap')?.classList.toggle('hidden',mcq);
}

const pageAliases={
  programs:{target:'data',view:'programs',form:'program'},
  courses:{target:'data',view:'courses',form:'course'},
  students:{target:'data',view:'students',form:'student'}
};

function showPage(name){
  const alias=pageAliases[name]||null;
  const target=alias?.target||name;
  if(alias?.view)state.dataView=alias.view;
  const before=document.querySelector('.page.active')?.id?.replace('page-','');if(name==='feedback'&&before&&before!=='feedback')state.feedbackSource=before;
  document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.sidebar nav button[data-page]').forEach(x=>x.classList.toggle('active',x.dataset.page===name));
  const activeNav=document.querySelector(`.sidebar nav button[data-page="${name}"]`);const group=activeNav?.closest('.nav-group');if(group)setNavGroupOpen(group,true);
  document.getElementById(`page-${target}`).classList.add('active');
  document.getElementById('pageTitle').textContent=pageMeta[name][0];
  document.getElementById('pageSub').textContent=pageMeta[name][1];
  const breadcrumb=document.getElementById('pageBreadcrumb');if(breadcrumb)breadcrumb.textContent=`DOU Assess / ${pageMeta[name][2]||pageMeta[name][0]}${pageMeta[name][2]&&pageMeta[name][2]!==pageMeta[name][0]?` / ${pageMeta[name][0]}`:''}`;
  if(name==='mycourses') prepareMyCourses();
  if(name==='coursestudents') prepareCourseStudents();
  if(name==='courseanalytics') prepareCourseAnalytics();
  if(name==='programanalytics') prepareProgramAnalytics();
  if(name==='studentcards') prepareStudentCards();
  if(name==='dashboard') loadDashboard();
  if(name==='import') preparePilotOps();
  if(target==='data') loadData().then(()=>{if(alias?.form)openAcademicForm(alias.form);});
  if(name==='outcomes') prepareOutcomes();
  if(name==='curriculummap') prepareCurriculumMap();
  if(name==='assessmentmeasures') prepareAssessmentMeasures();
  if(name==='surveys') prepareSurveys();
  if(name==='assessmentassurance') prepareAssessmentAssurance();
  if(name==='institutionalreadiness') prepareInstitutionalReadiness();
  if(name==='programreview') prepareProgramReview();
  if(name==='evidencehub') prepareEvidenceHub();
  if(name==='acceptance') prepareProductionAcceptance();
  if(name==='exams') loadExams();
  if(name==='bank') prepareBank();
  if(name==='print') preparePrint();
  if(name==='scan') prepareScan();
  if(name==='grade') prepareGrade();
  if(name==='analytics') prepareAnalytics();
  if(name==='quality') prepareQuality();
  if(name==='quality360') prepareQuality360();
  if(name==='accreditation') prepareAccreditation();
  if(name==='evidence') prepareEvidence();
  if(name==='users') prepareUsers();
  if(name==='feedback') prepareFeedback();
  if(name==='security') prepareSecurity();
}

document.querySelectorAll('.sidebar nav button[data-page]').forEach(b=>b.addEventListener('click',()=>{showPage(b.dataset.page);closeMobileNav();}));

function setMobileNav(open){
  const shell=document.querySelector('.shell');const btn=document.getElementById('mobileMenuBtn');
  if(!shell)return;shell.classList.toggle('mobile-nav-open',!!open);document.body.classList.toggle('nav-lock',!!open);
  btn?.setAttribute('aria-expanded',open?'true':'false');
}
function closeMobileNav(){setMobileNav(false)}
document.getElementById('mobileMenuBtn')?.addEventListener('click',()=>setMobileNav(!document.querySelector('.shell')?.classList.contains('mobile-nav-open')));
document.getElementById('mobileNavBackdrop')?.addEventListener('click',closeMobileNav);
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMobileNav();});
window.addEventListener('resize',()=>{if(window.innerWidth>900)closeMobileNav();});
function setNavGroupOpen(group,open,{exclusive=true}={}){
  if(!group)return;
  if(open&&exclusive){
    document.querySelectorAll('.nav-group.open').forEach(other=>{
      if(other===group)return;
      other.classList.remove('open');
      other.querySelector('.nav-group-toggle')?.setAttribute('aria-expanded','false');
    });
  }
  group.classList.toggle('open',!!open);
  group.querySelector('.nav-group-toggle')?.setAttribute('aria-expanded',String(!!open));
}
document.querySelectorAll('.nav-group-toggle').forEach(b=>b.addEventListener('click',()=>{
  const group=b.closest('.nav-group');
  setNavGroupOpen(group,!group?.classList.contains('open'));
}));
function refreshNavGroups(){
  let activeGroup=null;
  document.querySelectorAll('.nav-group').forEach(group=>{
    const pages=[...group.querySelectorAll('button[data-page]')];const visible=pages.some(x=>!x.classList.contains('hidden'));
    group.classList.toggle('hidden',!visible);
    if(visible&&pages.some(x=>x.classList.contains('active')))activeGroup=group;
  });
  if(activeGroup)setNavGroupOpen(activeGroup,true);
}

function commandItems(){
  const rows=[];
  document.querySelectorAll('.sidebar button[data-page]').forEach(b=>{if(b.classList.contains('hidden'))return;const meta=pageMeta[b.dataset.page]||[b.textContent.trim(),'',''];rows.push({group:meta[2]||'Modül',title:meta[0],sub:meta[1],run:()=>showPage(b.dataset.page)});});
  if(!isQualityOnly()){rows.push({group:'Hızlı İşlem',title:'Yeni sınav oluştur',sub:'Sınav Merkezi oluşturma formuna git',run:()=>{showPage('exams');setTimeout(()=>document.getElementById('examCreateCard')?.scrollIntoView({behavior:'smooth'}),60);}});rows.push({group:'Hızlı İşlem',title:'Yeni soru oluştur',sub:'Soru Havuzu editörünü aç',run:()=>{showPage('bank');setTimeout(()=>openNewBankQuestion().catch(e=>toast(e.message,'error')),120);}});}
  rows.push({group:'Hızlı İşlem',title:'Öğrenim ve Program Çıktıları',sub:'Kazanım kataloğu ve katkı matrisi',run:()=>showPage('outcomes')});
  rows.push({group:'Hızlı İşlem',title:'Optik & Kontrol',sub:'Toplu tarama ve istisna kuyruğu',run:()=>showPage('scan')});
  (state.exams||[]).slice(0,8).forEach(exam=>rows.push({group:'Son Sınavlar',title:exam.title,sub:`${exam.exam_type} · ${examStatusLabel(exam.status)} · #${exam.id}`,run:()=>{showPage('exams');setTimeout(()=>openExam(exam.id),60);}}));
  return rows;
}
function renderCommandPalette(){
  const q=(document.getElementById('commandSearch')?.value||'').trim().toLocaleLowerCase('tr-TR');const items=commandItems().filter(x=>!q||`${x.title} ${x.sub} ${x.group}`.toLocaleLowerCase('tr-TR').includes(q));state.commandRows=items;state.commandIndex=Math.min(state.commandIndex,Math.max(0,items.length-1));
  const list=document.getElementById('commandList');if(!list)return;list.innerHTML=items.length?items.map((x,i)=>`<button type="button" class="command-item ${i===state.commandIndex?'active':''}" data-command-index="${i}"><span>${esc(x.group)}</span><div><b>${esc(x.title)}</b><small>${esc(x.sub)}</small></div><i>↵</i></button>`).join(''):'<div class="empty-state"><b>Sonuç bulunamadı</b><span>Başka bir ifade deneyin.</span></div>';
}
function openCommandPalette(){state.commandIndex=0;document.getElementById('commandPalette')?.classList.remove('hidden');const input=document.getElementById('commandSearch');if(input){input.value='';renderCommandPalette();setTimeout(()=>input.focus(),30);}}
function closeCommandPalette(){document.getElementById('commandPalette')?.classList.add('hidden');}
function runCommand(index){const item=state.commandRows[index];if(!item)return;closeCommandPalette();item.run();}
document.getElementById('commandBtn')?.addEventListener('click',openCommandPalette);
document.getElementById('commandClose')?.addEventListener('click',closeCommandPalette);
document.getElementById('commandSearch')?.addEventListener('input',()=>{state.commandIndex=0;renderCommandPalette();});
document.getElementById('commandList')?.addEventListener('click',e=>{const b=e.target.closest('[data-command-index]');if(b)runCommand(Number(b.dataset.commandIndex));});
document.getElementById('commandPalette')?.addEventListener('click',e=>{if(e.target.id==='commandPalette')closeCommandPalette();});
document.addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCommandPalette();return;}
  const open=!document.getElementById('commandPalette')?.classList.contains('hidden');if(!open)return;
  if(e.key==='Escape'){e.preventDefault();closeCommandPalette();}else if(e.key==='ArrowDown'){e.preventDefault();state.commandIndex=Math.min(state.commandIndex+1,Math.max(0,state.commandRows.length-1));renderCommandPalette();}else if(e.key==='ArrowUp'){e.preventDefault();state.commandIndex=Math.max(0,state.commandIndex-1);renderCommandPalette();}else if(e.key==='Enter'){e.preventDefault();runCommand(state.commandIndex);}
});

document.getElementById('refreshBtn').addEventListener('click',()=>showPage(document.querySelector('.page.active').id.replace('page-','')));

async function checkReady(){
  try{
    const r=await api('GET','/api/ready');
    document.getElementById('readyDot').classList.add('ok');
    const dbLabel=r.database_dialect||'bağlı'; const versionLabel=r.version||'production';
    document.getElementById('readyText').textContent=r.status==='ready'?'Sistem hazır':'Sistem kontrol ediliyor';
    document.getElementById('readyBox').innerHTML=`API: <b>${esc(r.status)}</b><br>Veritabanı: <b>${esc(dbLabel)}</b><br>Sürüm: <b>${esc(versionLabel)}</b>`;
    const authText=document.getElementById('authModeText');
    if(authText&&state.authConfig){authText.textContent=state.authConfig.auth_required?'Kimlik doğrulama: Microsoft Entra access token zorunlu.':'Kimlik doğrulama: pilot kullanıcı seçimi açık; RBAC sunucu tarafında uygulanıyor.';}
  }catch(e){document.getElementById('readyText').textContent='API erişilemiyor'; document.getElementById('readyBox').textContent=e.message;}
}

function statusLabel(status){return ({draft:'Taslak',ready:'Hazır',grading:'Değerlendirme',approved:'Onaylı',archived:'Arşiv'})[status]||status||'—';}
function statusClass(status){return `status-${status||'draft'}`;}
function dashboardPersona(){
  if(isAdmin())return {badge:'Sistem Yöneticisi',title:'Pilotun işletim ve kullanıcı akışını kontrol edin.',copy:'Kurumsal hazırlık, kullanıcılar, geri bildirimler ve kalite göstergeleri bugün sizin çalışma kuyruğunuz.',primary:'Kurumsal Pilot'};
  if(isQualityOnly())return {badge:'Kalite Müdürü',title:'Ölçüm açıklarını ve kanıt zincirini tamamlayın.',copy:'Riskli Öğrenim ve Program Çıktıları sonuçlarını, açık aksiyonları ve akreditasyon kanıtlarını tek yerden takip edin.',primary:'Yönetim & Kalite'};
  if(hasAnyRole('program_head'))return {badge:'Program Başkanı',title:'Programınızın ölçme kalitesini izleyin.',copy:'Ölçülmeyen dersleri, riskli çıktıları ve devam eden sınavları öncelik sırasına göre görün.',primary:'Yönetim & Kalite'};
  return {badge:'Öğretim Elemanı',title:'Bugün ne yapmak istiyorsunuz?',copy:'Ders, soru, sınav ve değerlendirme işlemleriniz tek sırada. İhtiyacınız olmayan yönetim ekranları gizlidir.',primary:'Derslerim'};
}
function renderDashboardPersona(d){
  const p=dashboardPersona();document.getElementById('dashboardRoleBadge').textContent=p.badge;document.getElementById('dashboardGreeting').textContent=p.title;document.getElementById('dashboardRoleCopy').textContent=p.copy;
  const instructor=!canAccreditation()&&!isAdmin();
  document.getElementById('dashNewExam')?.classList.toggle('hidden',!instructor&&isQualityOnly());
  document.getElementById('dashOpenBank')?.classList.toggle('hidden',isQualityOnly());
  document.getElementById('dashOpenScan')?.classList.toggle('hidden',isQualityOnly());
  document.getElementById('dashOpenQuality')?.classList.toggle('hidden',!canAccreditation());
  document.getElementById('dashOpenAccred')?.classList.toggle('hidden',!canAccreditation());
  const draft=state.exams.filter(e=>e.status==='draft').length, grading=state.exams.filter(e=>e.status==='grading').length, ready=state.exams.filter(e=>e.status==='ready').length;
  let tasks=[];
  if(instructor){tasks=[
    {n:'01',label:'Derslerim',text:'Dersinizi seçin ve çalışma alanını açın.',page:'mycourses',cta:'Dersleri aç'},
    {n:'02',label:'Soru Bankası',text:`${d.bank_questions||0} aktif soru · yeni soru ekleyin veya mevcut soruyu kullanın.`,page:'bank',cta:'Soruları aç'},
    {n:'03',label:'Sınavlar',text:draft?`${draft} taslak sınavınız devam ediyor.`:'Yeni sınav oluşturabilir veya eski sınava devam edebilirsiniz.',page:'exams',cta:draft?'Devam et':'Sınavları aç'},
    {n:'04',label:'Değerlendirme',text:grading?`${grading} sınav puanlama bekliyor.`:'Puanlama bekleyen sınavınız yok.',page:'grade',cta:'Değerlendirmeyi aç'}
  ];}else if(canAccreditation()){
    tasks=[
      {n:d.open_improvements||0,label:'Açık iyileştirme',text:'Hedef altı çıktılar için aksiyonları tamamla.',page:'accreditation',cta:'Aksiyonları aç'},
      {n:d.open_reviews||0,label:'Tarama incelemesi',text:'Belirsiz optik işaretlerini doğrula.',page:'scan',cta:'İncele'},
      {n:d.official_exams||0,label:'Resmî sınav',text:'Kalite hesaplamasına giren onaylı/arşiv sınavlar.',page:'quality',cta:'Kaliteyi aç'},
      {n:d.feedback_open||0,label:'Pilot geri bildirim',text:'Açık kullanıcı notlarını gözden geçir.',page:'feedback',cta:'Geri bildirimler'}
    ];}
  document.getElementById('dashboardTaskGrid').innerHTML=tasks.map(x=>`<button class="dashboard-task-card" data-action-call="showPage('${x.page}')"><span>${esc(x.n)}</span><div><b>${esc(x.label)}</b><small>${esc(x.text)}</small></div><strong>${esc(x.cta)} →</strong></button>`).join('');
}
function actionCenterYear(){
  const years=(state.courses||[]).map(x=>x.academic_year).filter(Boolean).sort();
  return years[years.length-1]||'2026-2027';
}
function actionPriorityLabel(priority){return priority==='critical'?'Kritik':priority==='high'?'Yüksek':priority==='medium'?'Orta':'Bilgi';}
async function renderActionCenter(d){
  const rows=[];const qualityMode=canAccreditation()||isAdmin();
  if(!qualityMode){
    (state.exams||[]).filter(x=>['draft','ready','grading'].includes(x.status)).forEach(exam=>{
      const cfg=exam.status==='draft'?['high','Sınav taslağını tamamla','Sorular, çıktı eşleştirmeleri ve kağıt kontrolünü bitir.','exams']:exam.status==='ready'?['medium','Optik / uygulama bekliyor','Sınav hazır; uygulama ve tarama adımına geç.','scan']:['critical','Değerlendirme bekliyor','Öğrenci puanlamasını tamamla ve onay sürecine gönder.','grade'];
      rows.push({priority:cfg[0],title:`${exam.course_code||''} · ${exam.title}`,text:cfg[2],page:cfg[3],exam_id:exam.id});
    });
    if(!rows.length)rows.push({priority:'info',title:'Akademik iş kuyruğu temiz',text:'Taslak, okutma veya değerlendirme bekleyen sınav bulunmuyor.',page:'mycourses'});
  }else{
    const year=actionCenterYear();
    for(const program of (state.programs||[]).slice(0,4)){
      try{
        const data=await api('GET',`/api/quality360/programs/${program.id}/action-recommendations?academic_year=${encodeURIComponent(year)}`);
        (data.proposals||[]).slice(0,4).forEach(x=>rows.push({priority:x.severity==='critical'?'critical':x.severity==='high'?'high':'medium',title:`${program.code} · ${x.criterion_code} · ${x.criterion_name}`,text:(x.gap_signals||[]).slice(0,2).join(' · ')||x.why,page:'quality360'}));
      }catch(_e){}
    }
    if(Number(d.open_improvements||0)>0)rows.unshift({priority:'critical',title:`${d.open_improvements} açık iyileştirme aksiyonu`,text:'Termin, sorumlu ve etkililik kontrolü bekleyen PUKÖ/iyileştirme kayıtları var.',page:'accreditation'});
    if(!rows.length)rows.push({priority:'info',title:'Kalite iş kuyruğu temiz',text:'Mevcut görünümde kritik kalite açığı veya açık iyileştirme görünmüyor.',page:'quality360'});
  }
  const order={critical:0,high:1,medium:2,info:3};rows.sort((a,b)=>(order[a.priority]??9)-(order[b.priority]??9));
  const list=document.getElementById('dashboardActionCenter');const badge=document.getElementById('actionCenterCount');
  const actionable=rows.filter(x=>x.priority!=='info').length;if(badge)badge.textContent=`${actionable} iş`;
  if(list)list.innerHTML=rows.slice(0,10).map(x=>`<button class="action-center-row priority-${x.priority}" type="button" data-action-call="${x.exam_id?`continueExamFromDashboard(${x.exam_id})`:`showPage('${x.page}')`}"><span class="action-priority">${actionPriorityLabel(x.priority)}</span><div><b>${esc(x.title)}</b><small>${esc(x.text)}</small></div><i>→</i></button>`).join('');
}

async function loadDashboard(){
  await checkReady();
  try{
    const d=await api('GET','/api/dashboard');
    await refreshCore();renderDashboardPersona(d);await renderActionCenter(d);
    const instructor=!canAccreditation()&&!isAdmin();
    const items=instructor?[
      ['Ders',d.courses,'Aktif dersiniz'],['Soru',d.bank_questions||0,'Soru bankanız'],['Sınav',d.exams,'Toplam sınav'],['Bekleyen',Number(d.open_reviews||0)+state.exams.filter(e=>e.status==='grading').length,'İşlem gereken']
    ]:[
      ['Program',d.programs,'Akademik kapsam'],['Ders',d.courses,'Ders'],['Öğrenci',d.students,'Öğrenci'],['Resmî sınav',d.official_exams||0,'Kalite verisi'],['Açık aksiyon',d.open_improvements||0,'İyileştirme'],['Geri bildirim',d.feedback_open||0,'Açık kayıt']
    ];
    document.getElementById('stats').innerHTML=items.map((x,i)=>`<div class="stat modern-stat"><span class="stat-index">${String(i+1).padStart(2,'0')}</span><b>${x[1]}</b><span>${x[0]}</span><small>${x[2]}</small></div>`).join('');
    const recent=[...state.exams].sort((a,b)=>Number(b.id)-Number(a.id)).slice(0,6);
    document.getElementById('dashboardExamList').innerHTML=recent.length?recent.map(e=>`<button class="dashboard-exam-row" data-action-call="continueExamFromDashboard(${e.id})"><span class="exam-row-code">#${e.id}</span><span class="exam-row-main"><b>${esc(e.title)}</b><small>${esc(e.course_code||'')} ${esc(e.exam_type||'')}</small></span><span class="badge ${statusClass(e.status)}">${esc(statusLabel(e.status))}</span><span class="exam-row-arrow">→</span></button>`).join(''):'<div class="empty-state"><b>Henüz sınav yok.</b><span>Yeni sınav oluşturarak başlayın.</span></div>';
    const draft=state.exams.filter(e=>e.status==='draft').length,grading=state.exams.filter(e=>e.status==='grading').length,ready=state.exams.filter(e=>e.status==='ready').length;
    const attention=instructor?[
      {n:draft,title:'Taslak sınav',text:draft?'Soruları veya son kontrolü tamamlayın.':'Bekleyen taslak yok.',page:'exams'},
      {n:grading,title:'Değerlendirme bekliyor',text:grading?'Not girişine devam edin.':'Puanlama kuyruğu boş.',page:'grade'},
      {n:ready,title:'Okutmaya hazır',text:ready?'Optik tarama için hazır sınavlar.':'Hazır sınav yok.',page:'scan'}
    ]:[
      {n:d.open_improvements||0,title:'İyileştirme aksiyonu',text:'Açık kalite aksiyonlarını takip edin.',page:'accreditation'},
      {n:d.open_reviews||0,title:'Tarama incelemesi',text:'Karar bekleyen optik kayıtlar.',page:'scan'},
      {n:d.feedback_open||0,title:'Pilot geri bildirim',text:'Kullanıcı deneyimi kayıtları.',page:'feedback'}
    ];
    document.getElementById('dashboardAttention').innerHTML=attention.map(x=>`<button class="attention-row ${x.n?'has-work':''}" data-action-call="showPage('${x.page}')"><span>${x.n}</span><div><b>${x.title}</b><small>${x.text}</small></div><i>→</i></button>`).join('');
    const hb=document.getElementById('dashboardHealthBadge');if(hb){hb.textContent='Çalışıyor';hb.className='badge status-approved';}
  }catch(e){toast(e.message,'error');}
}
window.continueExamFromDashboard=async function(id){showPage('exams');await loadExams();await openExam(id);};
document.getElementById('dashNewExam')?.addEventListener('click',()=>{if(!state.programs.length){toast('Önce program adımını tamamlayın.','error');showPage('programs');return;}if(!state.courses.length){toast('Önce ders adımını tamamlayın.','error');showPage('courses');return;}showPage('exams');});
document.getElementById('dashOpenBank')?.addEventListener('click',()=>showPage('bank'));
document.getElementById('dashOpenQuality')?.addEventListener('click',()=>showPage('quality'));
document.getElementById('dashOpenScan')?.addEventListener('click',()=>showPage('scan'));
document.getElementById('dashOpenAccred')?.addEventListener('click',()=>showPage('accreditation'));
document.getElementById('dashAllExams')?.addEventListener('click',()=>showPage('exams'));

async function refreshCore(includeStudents=false){
  const [programs,courses,exams,summary]=await Promise.all([
    api('GET','/api/programs?limit=500&offset=0'),
    api('GET','/api/courses?limit=2000&offset=0'),
    api('GET','/api/exams?limit=1000&offset=0'),
    api('GET','/api/directory/summary')
  ]);
  state.programs=programs;state.courses=courses;state.exams=exams;state.directorySummary=summary||state.directorySummary;
  if(includeStudents) await loadAcademicStudentsPage(false);
  fillSelects();
}
function fillSelects(){
  const courseOpts=state.courses.map(c=>`<option value="${c.id}">${esc(c.code)} · ${esc(c.name)} · ${esc(c.academic_year)} ${esc(c.term)}</option>`).join('');
  const obsResultsCourse=document.getElementById('obsResultsCourse');if(obsResultsCourse){const keep=obsResultsCourse.value;obsResultsCourse.innerHTML=courseOpts||'<option value="">Ders yok</option>';if([...obsResultsCourse.options].some(o=>o.value===keep))obsResultsCourse.value=keep;}
  document.getElementById('examCourse').innerHTML=courseOpts || '<option value="">Önce ders yükleyin</option>';
  const bankCourse=document.getElementById('bankCourse');if(bankCourse)bankCourse.innerHTML=courseOpts||'<option value="">Yetkili ders bulunamadı</option>';const blueprintCourse=document.getElementById('blueprintCourse');if(blueprintCourse)blueprintCourse.innerHTML=courseOpts||'<option value="">Yetkili ders bulunamadı</option>';
  const bankFilterCourse=document.getElementById('bankFilterCourse');if(bankFilterCourse){const keep=bankFilterCourse.value;bankFilterCourse.innerHTML='<option value="">Tüm yetkili dersler</option>'+courseOpts;if([...bankFilterCourse.options].some(o=>o.value===keep))bankFilterCourse.value=keep;}
  const bankFilterProgram=document.getElementById('bankFilterProgram');if(bankFilterProgram){const keep=bankFilterProgram.value;bankFilterProgram.innerHTML='<option value="">Tüm programlar</option>'+state.programs.map(x=>`<option value="${x.id}">${esc(x.code)} · ${esc(x.name)}</option>`).join('');if([...bankFilterProgram.options].some(o=>o.value===keep))bankFilterProgram.value=keep;}
  const outcomeCourse=document.getElementById('outcomeCourse');if(outcomeCourse) outcomeCourse.innerHTML=courseOpts||'<option value="">Ders yok</option>';
  const courseAnalyticsCourse=document.getElementById('courseAnalyticsCourse');if(courseAnalyticsCourse){const keep=String(state.selectedCourseId||courseAnalyticsCourse.value||'');courseAnalyticsCourse.innerHTML=courseOpts||'<option value="">Yetkili ders yok</option>';if([...courseAnalyticsCourse.options].some(o=>o.value===keep))courseAnalyticsCourse.value=keep;}
  const courseStudentsCourse=document.getElementById('courseStudentsCourse');if(courseStudentsCourse){const keep=String(state.selectedCourseId||courseStudentsCourse.value||'');courseStudentsCourse.innerHTML=courseOpts||'<option value="">Yetkili ders yok</option>';if([...courseStudentsCourse.options].some(o=>o.value===keep))courseStudentsCourse.value=keep;}
  const programAnalyticsProgram=document.getElementById('programAnalyticsProgram');if(programAnalyticsProgram){const keep=programAnalyticsProgram.value;programAnalyticsProgram.innerHTML=state.programs.map(x=>`<option value="${x.id}">${esc(x.code)} · ${esc(x.name)}</option>`).join('')||'<option value="">Program yok</option>';if([...programAnalyticsProgram.options].some(o=>o.value===keep))programAnalyticsProgram.value=keep;}
  const examCourseFilter=document.getElementById('examCourseFilter');if(examCourseFilter){const keep=examCourseFilter.value;examCourseFilter.innerHTML='<option value="">Tüm dersler</option>'+courseOpts;if([...examCourseFilter.options].some(o=>o.value===keep))examCourseFilter.value=keep;}
  const examOpts=state.exams.map(e=>`<option value="${e.id}">${esc(e.title)} (#${e.id})</option>`).join('');
  ['gradeExam','analyticsExam','evidenceExam','scanExam'].forEach(id=>document.getElementById(id).innerHTML=examOpts || '<option value="">Sınav yok</option>');
  renderCurrentUserScope();
}



async function prepareCourseStudents(){await refreshCore();const sel=document.getElementById('courseStudentsCourse');if(state.selectedCourseId&&sel)sel.value=String(state.selectedCourseId);if(sel?.value)await loadCourseStudents();}
async function loadCourseStudents(){const id=Number(document.getElementById('courseStudentsCourse')?.value||0);if(!id)return;state.selectedCourseId=id;const box=document.getElementById('courseStudentsResult');if(box)box.innerHTML='<div class="loading-state">Öğrenciler yükleniyor…</div>';try{const rows=await api('GET',`/api/courses/${id}/enrollments`);box.innerHTML=rows.length?`<div class="simple-student-list"><div class="simple-student-head"><span>Öğrenci No</span><span>Ad Soyad</span><span>Sınıf</span></div>${rows.map(x=>`<div><span>${esc(x.student_no||'')}</span><b>${esc(x.full_name||'')}</b><span>${esc(x.class_name||'—')}</span></div>`).join('')}</div>`:'<div class="empty-state"><b>Bu derste öğrenci yok.</b><span>OBS senkronu veya ders kaydı tamamlandığında burada görünür.</span></div>';}catch(e){box.innerHTML=`<div class="empty-state"><b>Öğrenciler yüklenemedi.</b><span>${esc(e.message)}</span></div>`;}}
document.getElementById('loadCourseStudents')?.addEventListener('click',loadCourseStudents);document.getElementById('courseStudentsCourse')?.addEventListener('change',e=>{state.selectedCourseId=Number(e.target.value||0);});

function courseWorkspaceMeta(course){const p=state.programs.find(x=>x.id===course.program_id);return `${p?`${p.code} · `:''}${course.academic_year||''} ${course.term||''}`.trim();}
async function loadObsSyncInfo(){
  const info=document.getElementById('obsSyncInfo'),btn=document.getElementById('obsResyncBtn');if(!info||!btn)return;
  try{const s=await api('GET','/api/auth/obs-sync-status');btn.classList.toggle('hidden',!s.enabled);
    info.textContent=s.last_sync_at?`Son OBS senkronu: ${new Date(s.last_sync_at).toLocaleString('tr-TR')}${s.summary?` · ${s.summary.courses||0} yeni ders, ${s.summary.students||0} yeni öğrenci`:''}`:(s.enabled?'Henüz OBS senkronu yok; "OBS\'den getir" ile dersleri çekin.':'OBS bağlandığında ders atamaları otomatik güncellenir.');
  }catch{}
}
document.getElementById('obsResyncBtn')?.addEventListener('click',async()=>{
  const d=await workflowForm({eyebrow:'OBS',title:"OBS'den getir",description:'Derslerinizi ve öğrenci listelerinizi OBS\'den yeniden çeker. Şifreniz saklanmaz.',submitLabel:'Getir',fields:[{name:'u',label:'Sicil no',required:true},{name:'p',label:'OBS şifresi',type:'password',required:true}]});if(!d)return;
  try{const r=await api('POST','/api/integrations/obs/resync',{username:d.u,password:d.p});toast(`OBS senkronu tamam: ${r.sync.courses||0} yeni ders, ${r.sync.students||0} yeni öğrenci.`);await prepareMyCourses();}catch(e){toast(e.message,'error');}
});

async function prepareMyCourses(){
  await refreshCore();loadObsSyncInfo();
  const grid=document.getElementById('myCoursesGrid'),count=document.getElementById('myCoursesCount');if(!grid)return;
  if(count)count.textContent=`${state.courses.length} ders`;
  grid.innerHTML=state.courses.length?state.courses.map(c=>`<button type="button" class="course-workspace-card ${Number(state.selectedCourseId)===c.id?'active':''}" data-workspace-course="${c.id}"><span class="course-code">${esc(c.code)}</span><div><b>${esc(c.name)}</b><small>${esc(courseWorkspaceMeta(c))}</small></div><i>Dersi aç →</i></button>`).join(''):'<div class="empty-state"><b>Yetkili ders bulunamadı.</b><span>OBS veya akademik kapsam ataması tamamlandığında dersleriniz burada görünür.</span></div>';
  if(state.selectedCourseId)openCourseActionPanel(state.selectedCourseId,false);
}
function openCourseActionPanel(courseId,scroll=true){const c=state.courses.find(x=>x.id===Number(courseId));if(!c)return;state.selectedCourseId=c.id;const panel=document.getElementById('courseActionPanel');panel?.classList.remove('hidden');document.getElementById('courseActionTitle').textContent=`${c.code} · ${c.name}`;document.getElementById('courseActionMeta').textContent=courseWorkspaceMeta(c);document.querySelectorAll('[data-workspace-course]').forEach(x=>x.classList.toggle('active',Number(x.dataset.workspaceCourse)===c.id));if(scroll)panel?.scrollIntoView({behavior:'smooth',block:'nearest'});}
function closeCourseActionPanel(){document.getElementById('courseActionPanel')?.classList.add('hidden');}
document.getElementById('myCoursesGrid')?.addEventListener('click',e=>{const b=e.target.closest('[data-workspace-course]');if(b)openCourseActionPanel(Number(b.dataset.workspaceCourse));});
document.getElementById('courseActionClose')?.addEventListener('click',closeCourseActionPanel);
document.getElementById('courseActionPanel')?.addEventListener('click',e=>{const b=e.target.closest('[data-course-action]');if(!b||!state.selectedCourseId)return;const action=b.dataset.courseAction;document.querySelectorAll('#courseActionPanel [data-course-action]').forEach(x=>x.classList.toggle('active',x===b));if(action==='overview')return;if(action==='courseanalytics'){showPage('courseanalytics');setTimeout(()=>{const sel=document.getElementById('courseAnalyticsCourse');if(sel){sel.value=String(state.selectedCourseId);document.getElementById('loadCourseAnalytics')?.click();}},80);return;}if(action==='bank'){showPage('bank');setTimeout(()=>{const f=document.getElementById('bankFilterCourse');if(f){f.value=String(state.selectedCourseId);f.dispatchEvent(new Event('change'));}},80);return;}if(action==='exams'){showPage('exams');setTimeout(()=>{const f=document.getElementById('examCourseFilter');if(f){f.value=String(state.selectedCourseId);f.dispatchEvent(new Event('change'));}},80);return;}if(action==='grade'){showPage('grade');return;}if(action==='outcomes'){showPage('outcomes');return;}if(action==='improvement'){if(canAccreditation())showPage('quality360');else{showPage('courseanalytics');toast('İyileştirme önerileri ders analizi içinde gösterilir.');}return;}});

function pctBar(value,target=70){const v=Math.max(0,Math.min(100,Number(value||0)));const cls=v>=target?'good':v>=target-10?'watch':'bad';return `<div class="metric-bar ${cls}"><span data-style="width:${v}%"></span></div>`;}
function renderCourseAnalytics(d){state.courseAnalytics=d;const box=document.getElementById('courseAnalyticsResult');if(!box)return;const s=d.summary||{},c=d.course||{},los=d.learning_outcomes||[],trend=d.trend||[],exams=d.exams||[];const risk=los.filter(x=>x.status!=='achieved');const delta=s.class_average_change_points;box.innerHTML=`<div class="analysis-kpi-grid"><article><span>Sınıf ortalaması</span><b>${Number(s.class_average||0).toFixed(1)}</b><small>${delta==null?'Karşılaştırma için geçmiş dönem yok':`${delta>=0?'+':''}${delta} puan dönem değişimi`}</small></article><article><span>Geçme oranı</span><b>%${Number(s.pass_rate_percent||0).toFixed(1)}</b><small>${s.student_count||0} öğrenci</small></article><article><span>Öğrenim Çıktısı hedef karşılama</span><b>%${Number(s.learning_outcome_achievement_percent||0).toFixed(1)}</b><small>${risk.length} riskli çıktı</small></article><article><span>Resmî sınav</span><b>${s.official_exam_count||0}</b><small>${s.question_risk_count||0} riskli soru</small></article></div><div class="analysis-two-col"><section class="card"><div class="section-head"><div><span class="eyebrow">Öğrenim Çıktısı PERFORMANSI</span><h3>Hangi kazanımlar zorlanıyor?</h3></div></div><div class="outcome-analysis-list">${los.length?los.map(x=>`<div class="outcome-analysis-row ${x.status==='achieved'?'good':'risk'}"><div><b>${esc(x.code)}</b><small>${esc(x.description||'')}</small></div><strong>%${Number(x.attainment_percent).toFixed(1)}</strong>${pctBar(x.attainment_percent,x.target_percent)}<span>Hedef %${Number(x.target_percent).toFixed(0)}</span></div>`).join(''):'<div class="empty-state"><span>Onaylı sınavlardan Öğrenim Çıktısı verisi henüz oluşmadı.</span></div>'}</div></section><section class="card"><div class="section-head"><div><span class="eyebrow">DÖNEM TRENDİ</span><h3>Ders yıllar içinde nasıl gidiyor?</h3></div></div><div class="trend-list">${trend.length?trend.map(x=>`<div><span>${esc(x.label)}</span><b>${Number(x.class_average||0).toFixed(1)}</b>${pctBar(x.class_average,70)}<small>Öğrenim Çıktısı %${Number(x.learning_outcome_achievement_percent||0).toFixed(0)} · Geçme %${Number(x.pass_rate_percent||0).toFixed(0)}</small></div>`).join(''):'<div class="empty-state"><span>Trend için geçmiş dönem bulunamadı.</span></div>'}</div></section></div><section class="card"><div class="section-head"><div><span class="eyebrow">SINAVLAR</span><h3>${esc(c.code||'')} · dönem içi ölçümler</h3></div></div><div class="exam-analysis-strip">${exams.length?exams.map(x=>`<button type="button" data-open-analysis-exam="${x.exam_id}"><span>${esc(x.exam_type||'Sınav')}</span><b>${esc(x.title)}</b><small>Ort. ${Number(x.class_average||0).toFixed(1)} · Öğrenim Çıktısı %${Number(x.learning_outcome_achievement_percent||0).toFixed(0)}</small></button>`).join(''):'<div class="empty-state"><span>Resmî sınav yok.</span></div>'}</div></section>`;}
async function prepareCourseAnalytics(){await refreshCore();const sel=document.getElementById('courseAnalyticsCourse');if(state.selectedCourseId&&sel)sel.value=String(state.selectedCourseId);if(sel?.value)await loadCourseAnalytics();}
async function loadCourseAnalytics(){const id=Number(document.getElementById('courseAnalyticsCourse')?.value||0);if(!id)return;state.selectedCourseId=id;const box=document.getElementById('courseAnalyticsResult');if(box)box.innerHTML='<div class="loading-state">Ders analizi hazırlanıyor…</div>';try{renderCourseAnalytics(await api('GET',`/api/courses/${id}/analytics-overview`));}catch(e){if(box)box.innerHTML=`<div class="empty-state"><b>Analiz hazırlanamadı.</b><span>${esc(e.message)}</span></div>`;}}
document.getElementById('loadCourseAnalytics')?.addEventListener('click',loadCourseAnalytics);document.getElementById('courseAnalyticsCourse')?.addEventListener('change',e=>{state.selectedCourseId=Number(e.target.value||0);});document.getElementById('courseAnalyticsResult')?.addEventListener('click',e=>{const b=e.target.closest('[data-open-analysis-exam]');if(!b)return;showPage('analytics');setTimeout(()=>{const sel=document.getElementById('analyticsExam');if(sel){sel.value=b.dataset.openAnalysisExam;document.getElementById('loadAnalytics')?.click();}},80);});

function renderProgramAnalytics(d){state.programAnalytics=d;const box=document.getElementById('programAnalyticsResult');if(!box)return;const s=d.summary||{},program=(d.programs||[])[0]||{},po=program.program_outcomes||[],risks=(d.risk_courses||[]).slice(0,8),trend=d.trend||[];box.innerHTML=`<div class="analysis-kpi-grid program"><article><span>Ders</span><b>${s.course_count||0}</b><small>${s.measured_course_count||0} ölçülen ders</small></article><article><span>Ölçüm kapsamı</span><b>%${Number(s.measurement_percent||0).toFixed(0)}</b><small>${s.critical_course_count||0} dikkat isteyen ders</small></article><article><span>Program Çıktısı ortalaması</span><b>%${Number(s.program_outcome_average||0).toFixed(1)}</b><small>Hedef %${Number(s.program_outcome_target_average||0).toFixed(1)}</small></article><article><span>Açık PUKÖ</span><b>${s.open_action_count||0}</b><small>${s.uncovered_gap_count||0} aksiyonsuz açık</small></article></div><div class="analysis-two-col"><section class="card"><div class="section-head"><div><span class="eyebrow">PROGRAM ÇIKTILARI</span><h3>Program Çıktısı hedef karşılama</h3></div></div><div class="outcome-analysis-list">${po.length?po.map(x=>`<div class="outcome-analysis-row ${x.status==='achieved'?'good':'risk'}"><div><b>${esc(x.code)}</b><small>${esc(x.description||'')}</small></div><strong>%${Number(x.attainment_percent||0).toFixed(1)}</strong>${pctBar(x.attainment_percent,x.target_percent)}<span>${x.course_count||0} ders · hedef %${Number(x.target_percent||0).toFixed(0)}</span></div>`).join(''):'<div class="empty-state"><span>Program çıktısı ölçümü henüz yok.</span></div>'}</div></section><section class="card"><div class="section-head"><div><span class="eyebrow">PROGRAM TRENDİ</span><h3>Dönemler arası gelişim</h3></div></div><div class="trend-list">${trend.length?trend.map(x=>`<div><span>${esc(x.label)}</span><b>%${Number(x.program_outcome_average||0).toFixed(1)}</b>${pctBar(x.program_outcome_average,70)}<small>Ölçüm %${Number(x.measurement_percent||0).toFixed(0)} · Öğrenim Çıktısı %${Number(x.learning_outcome_achievement_percent||0).toFixed(0)}</small></div>`).join(''):'<div class="empty-state"><span>Trend verisi bulunamadı.</span></div>'}</div></section></div><section class="card"><div class="section-head"><div><span class="eyebrow">ÖNCELİKLİ DERSLER</span><h3>Nereden başlamalıyız?</h3></div></div><div class="risk-course-list">${risks.length?risks.map(x=>`<button type="button" data-program-risk-course="${x.course_id}"><span class="risk-dot ${esc(x.risk_level)}"></span><div><b>${esc(x.course_code)} · ${esc(x.course_name)}</b><small>${x.official_exam_count||0} resmî sınav · ${x.gap_count||0} çıktı açığı</small></div><strong>${x.risk_level==='no_data'?'Ölçülmedi':`${Number(x.max_gap_points||0).toFixed(0)} puan açık`}</strong></button>`).join(''):'<div class="empty-state"><span>Riskli ders bulunmuyor.</span></div>'}</div></section>`;}
async function prepareProgramAnalytics(){if(!hasAnyRole('admin','quality','program_head','department_head','faculty_admin')){toast('Program analizi yönetim rolü gerektirir.','error');showPage('mycourses');return;}await refreshCore();if(document.getElementById('programAnalyticsProgram')?.value)await loadProgramAnalytics();}
async function loadProgramAnalytics(){const id=Number(document.getElementById('programAnalyticsProgram')?.value||0);if(!id)return;const box=document.getElementById('programAnalyticsResult');if(box)box.innerHTML='<div class="loading-state">Program analizi hazırlanıyor…</div>';try{renderProgramAnalytics(await api('GET',`/api/programs/${id}/analytics-overview`));}catch(e){if(box)box.innerHTML=`<div class="empty-state"><b>Program analizi hazırlanamadı.</b><span>${esc(e.message)}</span></div>`;}}
document.getElementById('loadProgramAnalytics')?.addEventListener('click',loadProgramAnalytics);document.getElementById('programAnalyticsResult')?.addEventListener('click',e=>{const b=e.target.closest('[data-program-risk-course]');if(!b)return;state.selectedCourseId=Number(b.dataset.programRiskCourse);showPage('courseanalytics');setTimeout(()=>{const sel=document.getElementById('courseAnalyticsCourse');if(sel){sel.value=String(state.selectedCourseId);document.getElementById('loadCourseAnalytics')?.click();}},80);});

function academicProgramName(programId){const p=state.programs.find(x=>x.id===Number(programId));return p?`${p.code} · ${p.name}`:'Program';}
function academicDefaultYear(){const first=state.courses[0]?.academic_year;if(first)return first;const y=new Date().getFullYear();return `${y}-${y+1}`;}
function academicProgramOptions(selected=''){return state.programs.map(x=>`<option value="${x.id}" ${String(x.id)===String(selected)?'selected':''}>${esc(x.code)} · ${esc(x.name)}</option>`).join('');}
function academicCourseOptions(selected=''){return state.courses.map(x=>`<option value="${x.id}" ${String(x.id)===String(selected)?'selected':''}>${esc(x.code)} · ${esc(x.name)} · ${esc(x.academic_year)} ${esc(x.term)}</option>`).join('');}
function academicCanManage(){return canAcademicMaster();}

function renderAcademicDataStats(){
  const instructorKeys=new Set(state.courses.map(x=>(x.instructor_email||x.instructor_name||'').trim().toLocaleLowerCase('tr-TR')).filter(Boolean));
  const assigned=state.courses.filter(x=>(x.instructor_email||x.instructor_name||'').trim()).length;
  const stats=[
    ['Program',state.directorySummary?.programs??state.programs.length,'Akademik kapsam'],
    ['Ders',state.directorySummary?.courses??state.courses.length,`${assigned}/${state.courses.length||0} öğretim elemanı atanmış`],
    ['Öğrenci',state.directorySummary?.students??state.students.length,'Aktif öğrenci kaydı'],
    ['Öğretim elemanı',instructorKeys.size,'Ders üzerinde tanımlı']
  ];
  document.getElementById('academicDataStats').innerHTML=stats.map(([label,value,sub],i)=>`<div class="academic-data-stat ${i===1?'accent':''}"><span>${esc(label)}</span><b>${esc(value)}</b><small>${esc(sub)}</small></div>`).join('');
}

function academicFlowModel(){
  const manage=academicCanManage();
  const hasProgram=state.programs.length>0;
  const hasCourse=state.courses.length>0;
  const hasExam=state.exams.length>0;
  const studentTotal=Number(state.directorySummary?.students??state.students.length);
  const hasStudent=studentTotal>0;
  return [
    {n:1,title:'Program',done:hasProgram,desc:hasProgram?`${state.programs.length} yetkili program hazır`:(isAdmin()?'Önce akademik programı oluşturun':'Yetkili program ataması bekleniyor'),action:isAdmin()?()=>showPage('programs'):null,cta:isAdmin()?'Program oluştur':'Program kapsamını bekle'},
    {n:2,title:'Ders',done:hasCourse,desc:hasCourse?`${state.courses.length} ders kapsamınızda`:(manage?'Program içinde dersi tanımlayın':'Size atanmış ders bekleniyor'),action:manage&&hasProgram?()=>showPage('courses'):null,cta:manage?'Ders oluştur':'Ders kapsamını bekle'},
    {n:3,title:'Sınav',done:hasExam,desc:hasExam?`${state.exams.length} sınav mevcut`:(hasCourse?'Dersi seçip sınav taslağını oluşturun':'Önce ders gerekli'),action:hasCourse?()=>showPage('exams'):null,cta:'Sınav oluştur'},
    {n:4,title:'Öğrenci',done:hasStudent,desc:hasStudent?`${studentTotal} öğrenci kapsamda`:(hasExam?(manage?'Öğrenciyi ekleyip derse atayın':'Ders öğrenci listesi/OBS senkronu bekleniyor'):'Önce sınav adımını tamamlayın'),action:hasExam&&manage?()=>showPage('students'):null,cta:manage?'Öğrenci ekle':'Öğrenci listesini görüntüle'}
  ];
}
function renderAcademicFlow(){
  const box=document.getElementById('academicFlowSteps'), next=document.getElementById('academicFlowNext'), badge=document.getElementById('academicFlowStatus');if(!box||!next)return;
  const steps=academicFlowModel();let current=steps.find(x=>!x.done)||steps[steps.length-1];
  const firstOpen=steps.findIndex(x=>!x.done);const currentIndex=firstOpen<0?3:firstOpen;
  box.innerHTML=steps.map((x,i)=>{const locked=i>currentIndex&&!steps.slice(0,i).every(v=>v.done);return `<button type="button" class="academic-flow-step ${x.done?'done':''} ${i===currentIndex?'current':''} ${locked?'locked':''}" data-flow-step="${x.n}" ${locked||!x.action?'disabled':''}><span class="num">${x.done?'✓':x.n}</span><span><b>${esc(x.title)}</b><small>${esc(x.desc)}</small></span></button>`;}).join('');
  const completed=steps.filter(x=>x.done).length;if(badge)badge.textContent=completed===4?'Hazır':`${Math.min(currentIndex+1,4)} / 4`;
  if(completed===4){next.innerHTML='<div><b>Akademik temel hazır.</b><span>Artık soru bankası, sınav, optik ve değerlendirme akışına geçebilirsiniz.</span></div><button class="primary" type="button" data-flow-next="bank">Soru bankasına geç →</button>';}
  else{next.innerHTML=`<div><b>Sıradaki mikro adım: ${esc(current.title)}</b><span>${esc(current.desc)}</span></div>${current.action?`<button class="primary" type="button" data-flow-next="${current.n}">${esc(current.cta)} →</button>`:'<button class="ghost" type="button" disabled>Yetki / atama bekleniyor</button>'}`;}
  box.querySelectorAll('[data-flow-step]').forEach(b=>b.addEventListener('click',()=>{const step=steps.find(x=>x.n===Number(b.dataset.flowStep));step?.action?.();}));
  next.querySelector('[data-flow-next]')?.addEventListener('click',e=>{if(e.currentTarget.dataset.flowNext==='bank')return showPage('bank');current?.action?.();});
}

function syncAcademicDataControls(){
  const programOptions=academicProgramOptions();
  ['dataCourseProgram','dataStudentProgram'].forEach(id=>{const el=document.getElementById(id);if(!el)return;const keep=el.value;el.innerHTML=programOptions||'<option value="">Önce program oluşturun</option>';if([...el.options].some(o=>o.value===keep))el.value=keep;});
  const filter=document.getElementById('academicProgramFilter');if(filter){const keep=filter.value;filter.innerHTML='<option value="">Tüm programlar</option>'+programOptions;if([...filter.options].some(o=>o.value===keep))filter.value=keep;}
  const course=document.getElementById('dataEnrollCourse');if(course){const keep=course.value;course.innerHTML=academicCourseOptions()||'<option value="">Önce ders oluşturun</option>';if([...course.options].some(o=>o.value===keep))course.value=keep;}
}

function resetAcademicCourseForm(){
  const f=document.getElementById('courseCreateForm');f.reset();f.dataset.editId='';
  document.getElementById('dataCourseProgram').disabled=false;
  document.getElementById('dataCourseYear').value=academicDefaultYear();
  document.getElementById('dataCourseTerm').value='Güz';
  document.getElementById('dataCourseSubmit').textContent='Dersi oluştur';
  document.getElementById('dataCourseCancel').classList.add('hidden');
}
function resetAcademicStudentForm(){const f=document.getElementById('studentCreateForm');f.reset();f.dataset.editId='';document.getElementById('dataStudentProgram').disabled=false;document.getElementById('dataStudentSubmit').textContent='Öğrenciyi ekle';document.getElementById('dataStudentCancel').classList.add('hidden');}
function resetAcademicProgramForm(){const f=document.getElementById('programCreateForm');f.reset();f.dataset.editId='';document.getElementById('dataProgramSubmit').textContent='Programı oluştur';document.getElementById('dataProgramCancel').classList.add('hidden');}

function academicFormMeta(type,editing=false){
  const meta={
    course:['Ders','Ders oluştur','Program, dönem ve öğretim elemanı bilgisini tanımlayın.'],
    student:['Öğrenci','Öğrenci ekle','Öğrenciyi akademik programıyla birlikte kaydedin.'],
    enroll:['Derse ata','Ders öğrenci kaydı','Aynı programdaki öğrencileri seçili derse toplu olarak atayın.'],
    program:['Program','Program oluştur','Akademik birim ve program ana bilgisini tanımlayın.']
  }[type]||['Kayıt','Yeni kayıt',''];
  return [meta[0],editing?`${meta[1].replace(' oluştur','').replace(' ekle','')} düzenle`:meta[1],meta[2]];
}

function openAcademicForm(type,editId=null){
  const manage=academicCanManage();
  if(type==='program'&&!isAdmin()){toast('Program oluşturma yalnız sistem yöneticisine açıktır.','error');return;}
  if(type!=='program'&&!manage){toast('Bu işlem için akademik yönetim yetkisi gerekir.','error');return;}
  const editing=Boolean(editId);
  document.getElementById('academicCreatePanel')?.classList.add('drawer-open');
  document.getElementById('academicDrawerBackdrop')?.classList.remove('hidden');
  document.body.classList.add('academic-drawer-active');
  document.querySelectorAll('[data-form-panel]').forEach(x=>x.classList.toggle('hidden',x.dataset.formPanel!==type));
  document.querySelectorAll('#academicCreateTabs button[data-data-form]').forEach(x=>x.classList.toggle('active',x.dataset.dataForm===type));
  const [,title,help]=academicFormMeta(type,editing);document.getElementById('academicCreateTitle').textContent=title;document.getElementById('academicCreateHelp').textContent=help;document.getElementById('academicCreateMode').textContent=editing?'Düzenle':'Yeni';
  if(type==='course'){
    resetAcademicCourseForm();
    if(editId){const x=state.courses.find(v=>v.id===Number(editId));if(!x)return;const f=document.getElementById('courseCreateForm');f.dataset.editId=String(x.id);document.getElementById('dataCourseProgram').value=String(x.program_id);document.getElementById('dataCourseProgram').disabled=true;document.getElementById('dataCourseCode').value=x.code||'';document.getElementById('dataCourseName').value=x.name||'';document.getElementById('dataCourseYear').value=x.academic_year||'';document.getElementById('dataCourseTerm').value=x.term||'Güz';document.getElementById('dataCoursePassThreshold').value=x.pass_threshold_percent??50;document.getElementById('dataCourseInstructor').value=x.instructor_name||'';document.getElementById('dataCourseEmail').value=x.instructor_email||'';document.getElementById('dataCourseSubmit').textContent='Dersi güncelle';document.getElementById('dataCourseCancel').classList.remove('hidden');}
  }else if(type==='student'){
    resetAcademicStudentForm();
    if(editId){const x=state.students.find(v=>v.id===Number(editId));if(!x)return;const f=document.getElementById('studentCreateForm');f.dataset.editId=String(x.id);document.getElementById('dataStudentProgram').value=String(x.program_id);document.getElementById('dataStudentProgram').disabled=true;document.getElementById('dataStudentNo').value=x.student_no||'';document.getElementById('dataStudentName').value=x.full_name||'';document.getElementById('dataStudentClass').value=x.class_name||'';document.getElementById('dataStudentSubmit').textContent='Öğrenciyi güncelle';document.getElementById('dataStudentCancel').classList.remove('hidden');}
  }else if(type==='program'){
    resetAcademicProgramForm();
    if(editId){const x=state.programs.find(v=>v.id===Number(editId));if(!x)return;const f=document.getElementById('programCreateForm');f.dataset.editId=String(x.id);document.getElementById('dataProgramCode').value=x.code||'';document.getElementById('dataProgramName').value=x.name||'';document.getElementById('dataProgramFaculty').value=x.faculty||'';document.getElementById('dataProgramDepartment').value=x.department||'';document.getElementById('dataProgramSubmit').textContent='Programı güncelle';document.getElementById('dataProgramCancel').classList.remove('hidden');}
  }else if(type==='enroll') loadAcademicEnrollments();
  document.getElementById('academicCreatePanel')?.scrollIntoView({behavior:'smooth',block:'start'});
}

async function loadAcademicStudentsPage(reset=false){
  if(reset) state.studentDirectoryOffset=0;
  const q=(document.getElementById('academicDataSearch')?.value||'').trim();
  const programId=Number(document.getElementById('academicProgramFilter')?.value||0);
  const params=new URLSearchParams({limit:String(state.studentDirectoryLimit),offset:String(state.studentDirectoryOffset)});
  if(q) params.set('q',q);
  if(programId) params.set('program_id',String(programId));
  const rows=await api('GET',`/api/students?${params.toString()}`);
  state.students=rows;
  state.studentDirectoryHasNext=rows.length===state.studentDirectoryLimit;
  return rows;
}

function syncAcademicStudentPagination(){
  const box=document.getElementById('academicStudentPagination');if(!box)return;
  const active=(state.dataView||'courses')==='students';box.classList.toggle('hidden',!active);
  if(!active)return;
  const page=Math.floor(state.studentDirectoryOffset/state.studentDirectoryLimit)+1;
  const label=document.getElementById('academicStudentPageLabel');if(label)label.textContent=`Sayfa ${page} · ${state.students.length} kayıt`;
  const prev=document.getElementById('academicStudentPrev');if(prev)prev.disabled=state.studentDirectoryOffset<=0;
  const next=document.getElementById('academicStudentNext');if(next)next.disabled=!state.studentDirectoryHasNext;
}

function renderAcademicDirectory(){
  const view=state.dataView||'courses';const search=(document.getElementById('academicDataSearch')?.value||'').trim().toLocaleLowerCase('tr-TR');const programId=Number(document.getElementById('academicProgramFilter')?.value||0);const manage=academicCanManage();let rows=[];
  if(view==='courses'){
    rows=state.courses.filter(x=>(!programId||x.program_id===programId)&&(!search||`${x.code} ${x.name} ${x.academic_year} ${x.term} ${x.instructor_name||''} ${x.instructor_email||''} ${academicProgramName(x.program_id)}`.toLocaleLowerCase('tr-TR').includes(search)));
    document.getElementById('academicDirectoryList').innerHTML=rows.length?rows.map(x=>`<article class="academic-entity-card course-card"><div class="academic-entity-icon">D</div><div class="academic-entity-main"><div class="academic-entity-title"><span class="entity-code">${esc(x.code)}</span><b>${esc(x.name)}</b></div><div class="academic-entity-tags"><span>${esc(academicProgramName(x.program_id))}</span><span>${esc(x.academic_year)} · ${esc(x.term)}</span><span>Geçme %${Number(x.pass_threshold_percent??50).toFixed(0)}</span></div><div class="academic-entity-sub"><b>${esc(x.instructor_name||'Öğretim elemanı atanmadı')}</b>${x.instructor_email?`<span>${esc(x.instructor_email)}</span>`:''}</div></div><div class="academic-entity-actions"><button class="ghost small" data-action-call="downloadCourseGradebook(${x.id})">Ağırlıklı not defteri</button><button class="ghost small" type="button" data-action-call="downloadObsGrades(${x.id})">OBS aktarım dosyası</button>${manage?`<button class="ghost small" data-action-call="editCourse(${x.id})">Düzenle</button><button class="ghost small" data-action-call="openEnrollmentForCourse(${x.id})">Öğrenci ata</button><button class="danger small" data-action-call="removeCourse(${x.id})">Sil</button>`:''}</div></article>`).join(''):'<div class="empty-state"><b>Ders bulunamadı.</b><span>Filtreyi temizleyin veya soldan yeni ders oluşturun.</span></div>';
  }else if(view==='programs'){
    rows=state.programs.filter(x=>(!programId||x.id===programId)&&(!search||`${x.code} ${x.name} ${x.faculty||''} ${x.department||''}`.toLocaleLowerCase('tr-TR').includes(search)));
    document.getElementById('academicDirectoryList').innerHTML=rows.length?rows.map(x=>{const cc=Number(state.directorySummary?.courses_by_program?.[String(x.id)]??state.courses.filter(c=>c.program_id===x.id).length),sc=Number(state.directorySummary?.students_by_program?.[String(x.id)]??0),examCount=Number(state.directorySummary?.exams_by_program?.[String(x.id)]??0);return `<article class="academic-entity-card program-card premium-program-card"><div class="program-card-top"><div class="academic-entity-icon">${esc((x.code||'P').slice(0,2))}</div><div class="academic-entity-main"><div class="academic-entity-title"><span class="entity-code">${esc(x.code)}</span><b>${esc(x.name)}</b></div><div class="academic-entity-tags"><span>${esc(x.faculty||'Akademik birim tanımsız')}</span>${x.department?`<span>${esc(x.department)}</span>`:''}</div></div><button class="more-button" type="button" data-action-call="editProgram(${x.id})" title="Programı düzenle">•••</button></div><div class="program-card-metrics"><span><b>${cc}</b><small>Ders</small></span><span><b>${sc}</b><small>Öğrenci</small></span><span><b>${examCount}</b><small>Sınav</small></span></div><div class="program-card-footer"><span class="program-health"><i></i> Akademik kapsam aktif</span><button class="program-enter" type="button" data-action-call="openProgramWorkspace(${x.id})">Programa gir <b>→</b></button></div></article>`}).join(''):`<div class="empty-state premium-empty"><div class="empty-visual">P</div><b>Henüz program görünmüyor</b><span>İlk programı oluşturduğunuzda ders, öğrenci ve sınav kapsamı bu alanda toplanır.</span>${isAdmin()?'<button class="primary small" data-action-call="openAcademicForm(&quot;program&quot;)">+ Program oluştur</button>':''}</div>`;
  }else{
    rows=state.students;
    document.getElementById('academicDirectoryList').innerHTML=rows.length?rows.map(x=>`<article class="academic-entity-card student-card"><div class="academic-entity-icon">Ö</div><div class="academic-entity-main"><div class="academic-entity-title"><span class="entity-code">${esc(x.student_no)}</span><b>${esc(x.full_name)}</b>${x.anonymized_at?'<span class="pill-ok">Anonim</span>':''}</div><div class="academic-entity-tags"><span>${esc(academicProgramName(x.program_id))}</span>${x.class_name?`<span>${esc(x.class_name)}</span>`:''}</div></div>${manage?`<div class="academic-entity-actions"><button class="ghost small" data-action-call="editStudent(${x.id})">Düzenle</button>${isAdmin()&&!x.anonymized_at?`<button class="ghost small danger-lite" data-action-call="anonymizeStudent(${x.id})">Anonimleştir</button>`:''}<button class="danger small" data-action-call="removeStudent(${x.id})">Sil</button></div>`:''}</article>`).join(''):'<div class="empty-state"><b>Öğrenci bulunamadı.</b><span>Filtreyi temizleyin veya soldan öğrenci ekleyin.</span></div>';
  }
  document.getElementById('academicDirectoryCount').textContent=`${rows.length} kayıt`;
  document.querySelectorAll('.academic-view-tabs button').forEach(x=>x.classList.toggle('active',x.dataset.dataView===view));
  syncAcademicStudentPagination();
}

async function loadAcademicEnrollments(){
  const sel=document.getElementById('dataEnrollCourse');const courseId=Number(sel?.value||0);const list=document.getElementById('dataEnrollmentList');const picker=document.getElementById('dataEnrollmentStudents');
  if(!courseId){if(list)list.innerHTML='<div class="empty-state compact-empty"><b>Ders seçin.</b><span>Öğrenci kayıtları burada görünecek.</span></div>';if(picker)picker.innerHTML='';return;}
  const course=state.courses.find(x=>x.id===courseId);if(!course)return;
  try{
    const enrolled=await api('GET',`/api/courses/${courseId}/enrollments`);state.dataEnrollmentRows=enrolled;
    const enrollmentQ=(document.getElementById('dataEnrollmentSearch')?.value||'').trim();
    const studentParams=new URLSearchParams({program_id:String(course.program_id),limit:'200',offset:'0'});if(enrollmentQ)studentParams.set('q',enrollmentQ);
    const pool=await api('GET',`/api/students?${studentParams.toString()}`);
    const enrolledIds=new Set(enrolled.map(x=>x.id));const candidates=pool.filter(x=>!enrolledIds.has(x.id));
    picker.innerHTML=candidates.map(x=>`<option value="${x.id}">${esc(x.student_no)} · ${esc(x.full_name)}${x.class_name?` · ${esc(x.class_name)}`:''}</option>`).join('');
    document.getElementById('dataEnrollCourseContext').innerHTML=`<b>${esc(course.code)} · ${esc(course.name)}</b><span>${esc(academicProgramName(course.program_id))} · ${enrolled.length} kayıtlı · ${candidates.length} eşleşen atanabilir öğrenci</span>`;
    list.innerHTML=enrolled.length?`<div class="enrollment-list-head"><b>Dersteki öğrenciler</b><span>${enrolled.length}</span></div>${enrolled.slice(0,100).map(x=>`<div class="enrollment-row"><div><b>${esc(x.student_no)} · ${esc(x.full_name)}</b><small>${esc(x.class_name||'')}</small></div>${academicCanManage()?`<button class="ghost tiny" data-action-call="removeAcademicEnrollment(${courseId},${x.id})">Çıkar</button>`:''}</div>`).join('')}`:'<div class="empty-state compact-empty"><b>Bu derste öğrenci yok.</b><span>Yukarıdan öğrencileri seçip toplu atayın.</span></div>';
  }catch(e){list.innerHTML=`<div class="data-context-note error">${esc(e.message)}</div>`;}
}

async function loadData(){
  try{
    await refreshCore(false);if((state.dataView||'courses')==='students')await loadAcademicStudentsPage(false);syncAcademicDataControls();renderAcademicDataStats();renderAcademicFlow();
    const manage=academicCanManage();document.getElementById('dataNewCourse').classList.toggle('hidden',!manage);document.getElementById('dataNewStudent').classList.toggle('hidden',!manage);document.getElementById('dataNewProgram').classList.toggle('hidden',!isAdmin());document.getElementById('academicProgramTab').classList.toggle('hidden',!isAdmin());document.getElementById('academicReadOnlyNote').classList.toggle('hidden',manage);document.getElementById('academicCreateTabs').classList.toggle('hidden',!manage);document.querySelectorAll('[data-form-panel]').forEach(x=>{if(!manage)x.classList.add('hidden');});
    if(manage&&!document.querySelector('[data-form-panel]:not(.hidden)'))openAcademicForm('course');
    if(manage&&document.getElementById('courseCreateForm').dataset.editId==='')document.getElementById('dataCourseYear').value=document.getElementById('dataCourseYear').value||academicDefaultYear();
    renderAcademicDirectory();
    if(manage&&document.querySelector('[data-form-panel="enroll"]:not(.hidden)'))await loadAcademicEnrollments();
  }catch(e){toast(e.message,'error');}
}

window.editProgram=function(id){openAcademicForm('program',id);};
window.editCourse=function(id){openAcademicForm('course',id);};
window.editStudent=function(id){openAcademicForm('student',id);};
window.downloadCourseGradebook=async function(id){try{await downloadApi(`/api/courses/${Number(id)}/gradebook.xlsx`,`DOU-Assess-Ders-${Number(id)}-Agirlikli-Not-Defteri.xlsx`);toast('Ağırlıklı not defteri hazırlandı.');}catch(e){toast(e.message,'error');}};
window.openEnrollmentForCourse=function(id){openAcademicForm('enroll');document.getElementById('dataEnrollCourse').value=String(id);loadAcademicEnrollments();};
window.removeProgram=async function(id){if(!confirm('Programı silmek istediğinize emin misiniz? Bağlı kayıt varsa sistem silmeyi engeller.'))return;try{await api('DELETE',`/api/programs/${id}`);toast('Program silindi.');await loadData();}catch(e){toast(e.message,'error');}};
window.removeCourse=async function(id){if(!confirm('Dersi silmek istediğinize emin misiniz? Bağlı kayıt varsa sistem silmeyi engeller.'))return;try{await api('DELETE',`/api/courses/${id}`);toast('Ders silindi.');await loadData();}catch(e){toast(e.message,'error');}};
window.removeStudent=async function(id){if(!confirm('Öğrenciyi silmek istediğinize emin misiniz? Bağlı kayıt varsa sistem silmeyi engeller.'))return;try{await api('DELETE',`/api/students/${id}`);toast('Öğrenci silindi.');await loadData();}catch(e){toast(e.message,'error');}};
window.anonymizeStudent=async function(id){if(!confirm('Bu işlem öğrenci kimlik bilgilerini geri döndürülemez biçimde anonimleştirir; akademik analiz ilişkileri korunur. Devam edilsin mi?'))return;try{await api('POST',`/api/students/${id}/anonymize`,{confirm:true,reason:'KVKK / kurumsal veri yaşam döngüsü'});toast('Öğrenci anonimleştirildi.');await loadData();}catch(e){toast(e.message,'error');}};
window.removeAcademicEnrollment=async function(courseId,studentId){if(!confirm('Öğrenciyi bu dersten çıkarmak istiyor musunuz?'))return;try{await api('DELETE',`/api/courses/${courseId}/enrollments/${studentId}`);toast('Ders kaydı kaldırıldı.');await loadAcademicEnrollments();}catch(e){toast(e.message,'error');}};

document.getElementById('dataNewCourse')?.addEventListener('click',()=>openAcademicForm('course'));
document.getElementById('dataNewExam')?.addEventListener('click',()=>showPage('exams'));
document.getElementById('dataNewStudent')?.addEventListener('click',()=>openAcademicForm('student'));
document.getElementById('dataNewProgram')?.addEventListener('click',()=>openAcademicForm('program'));
document.getElementById('dataOpenObs')?.addEventListener('click',()=>showPage('import'));
document.getElementById('academicTemplateDownload')?.addEventListener('click',async()=>{try{await downloadApi('/api/import/academic-workbook/template','DOU-Assess-Akademik-Veri-Sablonu.xlsx');}catch(e){toast(e.message,'error');}});
async function runAcademicWorkbook(validateOnly=false){
  const file=document.getElementById('academicWorkbookFile')?.files?.[0];const out=document.getElementById('academicWorkbookResult');
  if(!file){toast('Önce doldurulmuş Excel dosyasını seçin.','error');return;}
  const fd=new FormData();fd.append('file',file);if(out)out.textContent=validateOnly?'Excel doğrulanıyor…':'Excel içe aktarılıyor…';
  try{const r=await api('POST',validateOnly?'/api/import/academic-workbook/validate':'/api/import/academic-workbook',fd);if(out)out.textContent=JSON.stringify(r,null,2);toast(validateOnly?'Excel doğrulaması başarılı.':'Akademik Excel içe aktarıldı.');if(!validateOnly)await loadData();}catch(e){if(out)out.textContent=e.message;toast(e.message,'error');}
}
document.getElementById('academicWorkbookValidate')?.addEventListener('click',()=>runAcademicWorkbook(true));
document.getElementById('academicWorkbookImport')?.addEventListener('click',()=>runAcademicWorkbook(false));
document.getElementById('academicWorkbookFile')?.addEventListener('change',ev=>{const f=ev.target.files?.[0];const out=document.getElementById('academicWorkbookResult');if(out)out.textContent=f?`${f.name}\n${Math.round(f.size/1024)} KB · Doğrulamaya hazır`:'Henüz dosya seçilmedi.';});
document.querySelectorAll('#academicCreateTabs button[data-data-form]').forEach(b=>b.addEventListener('click',()=>openAcademicForm(b.dataset.dataForm)));
function closeAcademicDrawer(){document.getElementById('academicCreatePanel')?.classList.remove('drawer-open');document.getElementById('academicDrawerBackdrop')?.classList.add('hidden');document.body.classList.remove('academic-drawer-active');}
function openProgramWorkspace(programId){const filter=document.getElementById('academicProgramFilter');if(filter)filter.value=String(programId);state.dataView='courses';renderAcademicDirectory();document.querySelector('.academic-directory-card')?.scrollIntoView({behavior:'smooth',block:'start'});toast('Program açıldı. Şimdi dersleri yönetebilirsiniz.');}
document.getElementById('academicDrawerClose')?.addEventListener('click',closeAcademicDrawer);
document.getElementById('academicDrawerBackdrop')?.addEventListener('click',closeAcademicDrawer);
document.getElementById('academicNewRecord')?.addEventListener('click',()=>openAcademicForm(state.dataView==='courses'?'course':state.dataView==='students'?'student':'program'));
document.addEventListener('click',ev=>{const b=ev.target.closest('[data-page-jump]');if(b)showPage(b.dataset.pageJump);});

document.querySelectorAll('.academic-view-tabs button[data-data-view]').forEach(b=>b.addEventListener('click',async()=>{state.dataView=b.dataset.dataView;if(state.dataView==='students')await loadAcademicStudentsPage(true);renderAcademicDirectory();}));
let academicSearchTimer=null;document.getElementById('academicDataSearch')?.addEventListener('input',()=>{clearTimeout(academicSearchTimer);academicSearchTimer=setTimeout(async()=>{if((state.dataView||'courses')==='students')await loadAcademicStudentsPage(true);renderAcademicDirectory();},250);});
document.getElementById('academicProgramFilter')?.addEventListener('change',async()=>{if((state.dataView||'courses')==='students')await loadAcademicStudentsPage(true);renderAcademicDirectory();});
document.getElementById('academicStudentPrev')?.addEventListener('click',async()=>{state.studentDirectoryOffset=Math.max(0,state.studentDirectoryOffset-state.studentDirectoryLimit);await loadAcademicStudentsPage(false);renderAcademicDirectory();});
document.getElementById('academicStudentNext')?.addEventListener('click',async()=>{if(!state.studentDirectoryHasNext)return;state.studentDirectoryOffset+=state.studentDirectoryLimit;await loadAcademicStudentsPage(false);renderAcademicDirectory();});
let enrollmentSearchTimer=null;document.getElementById('dataEnrollmentSearch')?.addEventListener('input',()=>{clearTimeout(enrollmentSearchTimer);enrollmentSearchTimer=setTimeout(loadAcademicEnrollments,250);});
document.getElementById('dataEnrollCourse')?.addEventListener('change',loadAcademicEnrollments);
document.getElementById('dataEnrollSelectAll')?.addEventListener('click',()=>{[...document.getElementById('dataEnrollmentStudents').options].forEach(o=>o.selected=true);});
document.getElementById('dataEnrollSubmit')?.addEventListener('click',async()=>{const courseId=Number(document.getElementById('dataEnrollCourse').value||0);const ids=[...document.getElementById('dataEnrollmentStudents').selectedOptions].map(o=>Number(o.value));if(!courseId){toast('Önce ders seçin.','error');return;}if(!ids.length){toast('En az bir öğrenci seçin.','error');return;}try{const r=await api('POST',`/api/courses/${courseId}/enrollments/bulk`,{student_ids:ids});toast(`${r.created} öğrenci derse atandı.`);await loadAcademicEnrollments();}catch(e){toast(e.message,'error');}});

document.getElementById('courseCreateForm')?.addEventListener('submit',async ev=>{ev.preventDefault();const f=ev.currentTarget;const editId=Number(f.dataset.editId||0);const common={code:document.getElementById('dataCourseCode').value.trim(),name:document.getElementById('dataCourseName').value.trim(),academic_year:document.getElementById('dataCourseYear').value.trim(),term:document.getElementById('dataCourseTerm').value,pass_threshold_percent:Number(document.getElementById('dataCoursePassThreshold').value||50),instructor_name:document.getElementById('dataCourseInstructor').value.trim(),instructor_email:document.getElementById('dataCourseEmail').value.trim()};try{let row;if(editId)row=await api('PATCH',`/api/courses/${editId}`,common);else row=await api('POST','/api/courses',{program_id:Number(document.getElementById('dataCourseProgram').value),...common});toast(editId?'Ders güncellendi.':'Ders oluşturuldu.');state.dataView='courses';await loadData();openAcademicForm('course');if(row?.id&&document.getElementById('dataEnrollCourse'))document.getElementById('dataEnrollCourse').value=String(row.id);}catch(e){toast(e.message,'error');}});
document.getElementById('studentCreateForm')?.addEventListener('submit',async ev=>{ev.preventDefault();const f=ev.currentTarget;const editId=Number(f.dataset.editId||0);const common={student_no:document.getElementById('dataStudentNo').value.trim(),full_name:document.getElementById('dataStudentName').value.trim(),class_name:document.getElementById('dataStudentClass').value.trim()};try{if(editId)await api('PATCH',`/api/students/${editId}`,common);else await api('POST','/api/students',{program_id:Number(document.getElementById('dataStudentProgram').value),...common});toast(editId?'Öğrenci güncellendi.':'Öğrenci eklendi.');state.dataView='students';await loadData();openAcademicForm('student');}catch(e){toast(e.message,'error');}});
document.getElementById('programCreateForm')?.addEventListener('submit',async ev=>{ev.preventDefault();const f=ev.currentTarget;const editId=Number(f.dataset.editId||0);const body={code:document.getElementById('dataProgramCode').value.trim(),name:document.getElementById('dataProgramName').value.trim(),faculty:document.getElementById('dataProgramFaculty').value.trim(),department:document.getElementById('dataProgramDepartment').value.trim()};try{if(editId)await api('PATCH',`/api/programs/${editId}`,body);else await api('POST','/api/programs',body);toast(editId?'Program güncellendi.':'Program oluşturuldu.');state.dataView='programs';await loadData();openAcademicForm('program');}catch(e){toast(e.message,'error');}});
document.getElementById('dataCourseCancel')?.addEventListener('click',()=>openAcademicForm('course'));
document.getElementById('dataStudentCancel')?.addEventListener('click',()=>openAcademicForm('student'));
document.getElementById('dataProgramCancel')?.addEventListener('click',()=>openAcademicForm('program'));


function contributionLabel(v){const n=Number(v);return ({1:'Çok düşük',2:'Düşük',3:'Orta',4:'Yüksek',5:'Çok yüksek'})[n]||'Eşleştirilmemiş';}
function mappingFor(data,loId,poId){return (data?.mappings||[]).find(x=>x.learning_outcome_id===loId&&x.program_outcome_id===poId);}
function mappedProgramsForLo(data,loId){
  return (data?.mappings||[]).filter(x=>x.learning_outcome_id===loId&&x.contribution>0).map(mp=>{const po=(data.program_outcomes||[]).find(x=>x.id===mp.program_outcome_id);return po?{...po,contribution:mp.contribution}:null;}).filter(Boolean);
}
async function prepareOutcomes(){
  try{await refreshCore();const manage=canAcademicMaster();document.getElementById('loQuickForm').closest('.card').classList.toggle('hidden',!manage);document.getElementById('poQuickForm').closest('.card').classList.toggle('hidden',!manage);const grid=document.querySelector('.outcome-quick-grid');if(grid)grid.classList.toggle('hidden',!manage);document.getElementById('outcomeBackToExam').classList.toggle('hidden',!state.currentExam);const sel=document.getElementById('outcomeCourse');if(sel&&sel.value)await loadOutcomeMap();}catch(e){toast(e.message,'error');}
}
async function loadThresholds(){
  const box=document.getElementById('thresholdList');if(!box)return;
  const course=(state.courses||[]).find(x=>x.id===Number(document.getElementById('outcomeCourse')?.value));
  try{const rows=await api('GET',`/api/outcome-thresholds${course?`?program_id=${course.program_id}`:''}`);
    box.innerHTML=rows.length?`<div class="tw"><table class="rt"><thead><tr><th>Tür</th><th>Kapsam</th><th>Yıl</th><th>Hedef</th><th>Sürüm</th><th>Durum</th><th>Not</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.kind==='lo'?'ÖÇ varsayılanı':'PÇ eşiği'}</td><td>${r.program_id?'Program':'Kurum'}</td><td>${esc(r.academic_year||'Tümü')}</td><td>%${r.target_percent}</td><td>v${r.version_no}</td><td>${r.is_active?'<span class="chip">geçerli</span>':'eski'}</td><td>${esc(r.note||'')}</td></tr>`).join('')}</tbody></table></div>`:'<p class="muted">Tanımlı eşik yok; ÖÇ hedefleri tek tek belirlenir.</p>';
  }catch(e){box.innerHTML=`<p class="muted">${esc(e.message)}</p>`}
}
document.getElementById('thresholdCard')?.addEventListener('toggle',e=>{if(e.target.open)loadThresholds()});
document.getElementById('thresholdAdd')?.addEventListener('click',async()=>{
  const course=(state.courses||[]).find(x=>x.id===Number(document.getElementById('outcomeCourse')?.value));
  const d=await workflowForm({eyebrow:'BAŞARI EŞİĞİ',title:'Yeni eşik sürümü',description:'Aynı kapsam ve türdeki geçerli sürüm kapatılır; geçmiş saklanır.',submitLabel:'Sürümü kaydet',fields:[
    {name:'kind',label:'Tür',type:'select',options:[{value:'lo',label:'ÖÇ varsayılan hedefi (yeni çıktılar)'},{value:'po',label:'PÇ başarı eşiği (analizler)'}]},
    {name:'scope',label:'Kapsam',type:'select',options:[...(course?[{value:'program',label:`Bu program (${course.program_name||course.program_id})`}]:[]),{value:'institution',label:'Tüm kurum (kalite/yönetici)'}]},
    {name:'year',label:'Akademik yıl (boş = tümü)',placeholder:'2026-2027'},
    {name:'target',label:'Hedef %',type:'number',required:true,value:60},{name:'note',label:'Gerekçe / yönerge',type:'textarea',rows:2}]});
  if(!d)return;
  try{await api('POST','/api/outcome-thresholds',{program_id:d.scope==='program'&&course?course.program_id:null,academic_year:(d.year||'').trim(),kind:d.kind,target_percent:Number(d.target),note:d.note||''});toast('Eşik sürümü kaydedildi.');await loadThresholds()}catch(e){toast(e.message,'error')}
});

async function loadOutcomeMap(){
  const courseId=Number(document.getElementById('outcomeCourse').value);if(!courseId)return;
  const [data,summary]=await Promise.all([api('GET',`/api/courses/${courseId}/outcomes`),api('GET',`/api/courses/${courseId}/outcome-summary`)]);state.currentOutcomeData=data;state.currentOutcomeSummary=summary;
  const course=state.courses.find(x=>x.id===courseId);document.getElementById('poYear').value=course?.academic_year||'';
  const linked=new Set((data.mappings||[]).filter(x=>x.contribution>0).map(x=>x.learning_outcome_id));const missing=(data.learning_outcomes||[]).filter(x=>!linked.has(x.id));
  document.getElementById('outcomeCoverage').innerHTML=`<div class="coverage-card"><div><b>${data.learning_outcomes.length}</b><span>Öğrenim Çıktısı</span></div><div><b>${data.program_outcomes.length}</b><span>Program Çıktısı</span></div><div class="${missing.length?'warn':'ok'}"><b>${data.learning_outcomes.length-missing.length}/${data.learning_outcomes.length}</b><span>Program Çıktısı bağlantılı Öğrenim Çıktısı</span></div><div class="coverage-note">${missing.length?`<b>${missing.map(x=>esc(x.code)).join(', ')}</b> henüz hiçbir Program Çıktısı ile eşleşmemiş.`:'Tüm Öğrenim Çıktısı’lerin en az bir Program Çıktısı bağlantısı var.'}</div></div>`;
  renderOutcomeCenterKpis(summary);renderOutcomeEntities(data);renderOutcomeMatrix(data);
}
function renderOutcomeCenterKpis(x){const box=document.getElementById('outcomeCenterKpis');if(!box)return;const bankRate=Number(x.bank_mapping_percent??(x.bank_question_count?Math.round(x.bank_mapped_question_count/x.bank_question_count*100):0));const rows=[['Öğrenim Çıktısı',x.learning_outcome_count,'ders çıktısı',''],['Program Çıktısı',x.program_outcome_count,'program çıktısı',''],['Eşleşme',x.mapping_count,'aktif katkı',x.ready_for_exam_snapshot?'ok':'warn'],['Ort. hedef',`%${x.average_target_percent}`,'Öğrenim Çıktısı başarı hedefi',''],['Soru kapsamı',`%${bankRate}`,`${x.bank_mapped_question_count}/${x.bank_question_count} soru`,bankRate===100&&x.bank_question_count?'ok':''],['Snapshot',x.ready_for_exam_snapshot?'Hazır':'Eksik',x.ready_for_exam_snapshot?'sınava aktarılabilir':`${(x.readiness_issues||[]).length} kontrol gerekli`,x.ready_for_exam_snapshot?'ok':'warn']];box.innerHTML=rows.map(r=>`<div class="outcome-kpi ${r[3]}"><b>${esc(r[1])}</b><span>${esc(r[0])}</span><small>${esc(r[2])}</small></div>`).join('');}
function renderOutcomeEntities(data){
  document.getElementById('loEntityCount').textContent=`${data.learning_outcomes.length} Öğrenim Çıktısı`;document.getElementById('poEntityCount').textContent=`${data.program_outcomes.length} Program Çıktısı`;
  const can=canAcademicMaster();
  document.getElementById('loEntityList').innerHTML=data.learning_outcomes.length?data.learning_outcomes.map(lo=>state.outcomeEditLoId===lo.id?`<div class="outcome-entity-item"><form class="outcome-inline-form"><label>Kod<input id="loEditCode-${lo.id}" value="${esc(lo.code)}"></label><label>Hedef %<input id="loEditTarget-${lo.id}" type="number" min="0" max="100" value="${lo.target_percent}"></label><label>Açıklama<textarea id="loEditDesc-${lo.id}" rows="2">${esc(lo.description)}</textarea></label><div class="actions"><button type="button" class="primary small" data-action-call="saveLearningOutcomeEdit(${lo.id})">Kaydet</button><button type="button" class="ghost small" data-action-call="cancelLearningOutcomeEdit()">İptal</button></div></form></div>`:`<div class="outcome-entity-item"><div class="outcome-code-block"><b>${esc(lo.code)}</b><small>Hedef %${lo.target_percent}</small><small class="source-tag">${({obs:'OBS\'den geldi',assess:'Assess\'te eklendi',obs_modified:'OBS\'den geldi, değiştirildi'})[lo.source]||''}${lo.is_active===false?' · Pasif':''}</small></div><div class="outcome-entity-copy"><b>${esc(lo.description)}</b><small>${mappedProgramsForLo(data,lo.id).map(x=>`${x.code} · ${x.contribution}/5`).join(' · ')||'Program Çıktısı bağlantısı yok'}</small></div>${can?`<div class="outcome-entity-actions"><button class="ghost small" data-action-call="editLearningOutcome(${lo.id})">Düzenle</button><button class="danger small" data-action-call="deleteLearningOutcome(${lo.id})">Sil</button></div>`:''}</div>`).join(''):'<div class="empty-state"><b>Öğrenim Çıktısı yok</b><span>Bu ders için ilk öğrenme çıktısını oluşturun.</span></div>';
  document.getElementById('poEntityList').innerHTML=data.program_outcomes.length?data.program_outcomes.map(po=>state.outcomeEditPoId===po.id?`<div class="outcome-entity-item"><form class="outcome-inline-form"><label>Kod<input id="poEditCode-${po.id}" value="${esc(po.code)}"></label><label>Yıl<input id="poEditYear-${po.id}" value="${esc(po.academic_year||'')}"></label><label>Açıklama<textarea id="poEditDesc-${po.id}" rows="2">${esc(po.description)}</textarea></label><div class="actions"><button type="button" class="primary small" data-action-call="saveProgramOutcomeEdit(${po.id})">Kaydet</button><button type="button" class="ghost small" data-action-call="cancelProgramOutcomeEdit()">İptal</button></div></form></div>`:`<div class="outcome-entity-item"><div class="outcome-code-block po"><b>${esc(po.code)}</b><small>${esc(po.academic_year||'Program Çıktısı')}</small></div><div class="outcome-entity-copy"><b>${esc(po.description)}</b><small>${(data.mappings||[]).filter(x=>x.program_outcome_id===po.id&&x.contribution>0).length} Öğrenim Çıktısı bağlantısı</small></div>${can?`<div class="outcome-entity-actions"><button class="ghost small" data-action-call="editProgramOutcome(${po.id})">Düzenle</button><button class="danger small" data-action-call="deleteProgramOutcome(${po.id})">Sil</button></div>`:''}</div>`).join(''):'<div class="empty-state"><b>Program Çıktısı yok</b><span>Program çıktısını oluşturun ve matriste eşleyin.</span></div>';
}
window.editLearningOutcome=id=>{state.outcomeEditLoId=id;renderOutcomeEntities(state.currentOutcomeData);};window.cancelLearningOutcomeEdit=()=>{state.outcomeEditLoId=null;renderOutcomeEntities(state.currentOutcomeData);};
window.saveLearningOutcomeEdit=async id=>{try{await api('PATCH',`/api/learning-outcomes/${id}`,{code:document.getElementById(`loEditCode-${id}`).value.trim(),target_percent:Number(document.getElementById(`loEditTarget-${id}`).value),description:document.getElementById(`loEditDesc-${id}`).value.trim()});state.outcomeEditLoId=null;toast('Öğrenim Çıktısı güncellendi.');await loadOutcomeMap();}catch(e){toast(e.message,'error');}};
window.deleteLearningOutcome=async id=>{if(!confirm('Bu Öğrenim Çıktısı silinsin mi? Bağlı soru veya sınav varsa silinmez, pasife alınır.'))return;try{const r=await api('DELETE',`/api/learning-outcomes/${id}`);toast(r.deactivated?r.message:'Öğrenim Çıktısı silindi.');await loadOutcomeMap();}catch(e){toast(e.message,'error');}};
window.editProgramOutcome=id=>{state.outcomeEditPoId=id;renderOutcomeEntities(state.currentOutcomeData);};window.cancelProgramOutcomeEdit=()=>{state.outcomeEditPoId=null;renderOutcomeEntities(state.currentOutcomeData);};
window.saveProgramOutcomeEdit=async id=>{try{await api('PATCH',`/api/program-outcomes/${id}`,{code:document.getElementById(`poEditCode-${id}`).value.trim(),academic_year:document.getElementById(`poEditYear-${id}`).value.trim(),description:document.getElementById(`poEditDesc-${id}`).value.trim()});state.outcomeEditPoId=null;toast('Program Çıktısı güncellendi.');await loadOutcomeMap();}catch(e){toast(e.message,'error');}};
window.deleteProgramOutcome=async id=>{if(!confirm('Bu Program Çıktısı silinsin mi? Eşleşme veya sınav snapshot’ı varsa sistem işlemi engeller.'))return;try{await api('DELETE',`/api/program-outcomes/${id}`);toast('Program Çıktısı silindi.');await loadOutcomeMap();}catch(e){toast(e.message,'error');}};
function renderOutcomeMatrix(data){
  const box=document.getElementById('outcomeMatrix');if(!data.learning_outcomes.length||!data.program_outcomes.length){box.innerHTML='<div class="empty-state"><b>Matris için Öğrenim Çıktısı ve Program Çıktısı gerekli.</b><span>Yukarıdaki formlarla eksik kazanımları ekleyin.</span></div>';return;}
  const head=data.program_outcomes.map(po=>`<th><span class="matrix-code">${esc(po.code)}</span><span title="${esc(po.description)}">${esc(po.description)}</span></th>`).join('');
  const rows=data.learning_outcomes.map(lo=>`<tr><th class="lo-head"><span class="matrix-code">${esc(lo.code)}</span><b>${esc(lo.description)}</b><small>Hedef %${lo.target_percent}</small></th>${data.program_outcomes.map(po=>{const mp=mappingFor(data,lo.id,po.id);const v=mp?.contribution??null;return `<td><select class="matrix-select ${v?`level-${v}`:'level-unmapped'}" data-lo="${lo.id}" data-po="${po.id}" title="${contributionLabel(v)}" ${canAcademicMaster()?'':'disabled'}><option value="" ${v==null?'selected':''} disabled>—</option>${[1,2,3,4,5].map(n=>`<option value="${n}" ${n===v?'selected':''}>${n}</option>`).join('')}</select></td>`}).join('')}</tr>`).join('');
  box.innerHTML=`<table class="outcome-matrix"><thead><tr><th>Öğrenim ve Program Çıktıları</th>${head}</tr></thead><tbody>${rows}</tbody></table>`;
  box.querySelectorAll('.matrix-select').forEach(sel=>sel.addEventListener('change',async ev=>{const el=ev.currentTarget;const contribution=Number(el.value);if(!Number.isInteger(contribution)||contribution<1||contribution>5){toast('Katkı düzeyi 1–5 arasında olmalıdır.','error');await loadOutcomeMap();return;}const oldClass=[...el.classList].find(x=>x.startsWith('level-'));if(oldClass)el.classList.remove(oldClass);el.classList.add(`level-${contribution}`);document.getElementById('outcomeSaveState').textContent='Kaydediliyor…';try{await api('PUT','/api/outcome-mappings',{learning_outcome_id:Number(el.dataset.lo),program_outcome_id:Number(el.dataset.po),contribution});document.getElementById('outcomeSaveState').textContent='Kaydedildi ✓';await loadOutcomeMap();setTimeout(()=>{const x=document.getElementById('outcomeSaveState');if(x)x.textContent='Hazır';},1300);}catch(e){toast(e.message,'error');document.getElementById('outcomeSaveState').textContent='Hata';await loadOutcomeMap();}}));
}
document.getElementById('outcomeCourse').addEventListener('change',loadOutcomeMap);
document.getElementById('loQuickForm').addEventListener('submit',async ev=>{ev.preventDefault();const courseId=Number(document.getElementById('outcomeCourse').value);if(!courseId)return;try{await api('POST',`/api/courses/${courseId}/learning-outcomes`,{code:document.getElementById('loCode').value.trim(),description:document.getElementById('loDescription').value.trim(),target_percent:Number(document.getElementById('loTarget').value)});ev.currentTarget.reset();document.getElementById('loTarget').value=60;toast('Öğrenim Çıktısı eklendi.');await loadOutcomeMap();}catch(e){toast(e.message,'error');}});
document.getElementById('poQuickForm').addEventListener('submit',async ev=>{ev.preventDefault();const courseId=Number(document.getElementById('outcomeCourse').value);const course=state.courses.find(x=>x.id===courseId);if(!course)return;try{await api('POST',`/api/programs/${course.program_id}/program-outcomes`,{academic_year:course.academic_year,code:document.getElementById('poCode').value.trim(),description:document.getElementById('poDescription').value.trim()});document.getElementById('poCode').value='';document.getElementById('poDescription').value='';toast('Program Çıktısı eklendi.');await loadOutcomeMap();}catch(e){toast(e.message,'error');}});

async function uploadImport(validateOnly){
  const f=document.getElementById('pilotFile').files[0];
  if(!f){toast('Önce Excel dosyasını seçin.','error');return;}
  const fd=new FormData();fd.append('file',f);
  const out=document.getElementById('importResult'); out.textContent='İşleniyor...';
  try{
    const path=validateOnly?'/api/integrations/obs/workbook/validate':'/api/integrations/obs/workbook/sync';
    const r=await api('POST',path,fd); out.textContent=JSON.stringify(r,null,2);
    toast(validateOnly?'Excel doğrulandı.':'Excel başarıyla PostgreSQL’e aktarıldı.');
    if(!validateOnly){await refreshCore();await loadDashboard();await preparePilotOps();}
  }catch(e){out.textContent=e.message;toast(e.message,'error');}
}
document.getElementById('validateImport').addEventListener('click',()=>uploadImport(true));
document.getElementById('runImport').addEventListener('click',()=>uploadImport(false));

function periodStatusLabel(status){return ({planned:'Planlandı',active:'Aktif',locked:'Kilitli',archived:'Arşiv'})[status]||status;}
function pilotKpi(label,value,sub,cls='') { return `<div class="pilot-kpi ${cls}"><span>${esc(label)}</span><b>${esc(value)}</b><small>${esc(sub||'')}</small></div>`; }
async function preparePilotOps(){
  if(!hasAnyRole('admin','quality')){toast('Kurumsal Pilot ekranı sistem yöneticisi ve kalite ekibine açıktır.','error');showPage('dashboard');return;}
  try{
    await refreshCore();
    const requests=[api('GET','/api/pilot/status'),api('GET','/api/academic-periods'),api('GET','/api/integrations/sync-runs?limit=25'),api('GET','/api/audit-logs?limit=40'),api('GET','/api/pilot/readiness'),api('GET','/api/pilot/issues'),api('GET','/api/pilot/uat/runs?limit=8')];
    const [status,periods,runs,audits,readiness,issues,uatRuns]=await Promise.all(requests);
    state.academicPeriods=periods;state.syncRuns=runs;state.pilotReadiness=readiness;state.pilotIssues=issues;state.pilotUatRuns=uatRuns;
    const active=status.active_period;const badge=document.getElementById('pilotOpsStatusBadge');
    badge.textContent=active?`${active.academic_year} ${active.term} · aktif`:'Aktif dönem seçilmedi';
    badge.className=`badge ${active?'status-approved':'status-ready'}`;
    document.getElementById('pilotOpsKpis').innerHTML=[
      pilotKpi('Program',status.programs,'yetkili kapsam'),pilotKpi('Ders',status.courses,active?'aktif döneme hazır':'toplam görünür'),
      pilotKpi('Öğrenci',status.students,'akademik kayıt'),pilotKpi('Sınav',status.exams,`${status.exam_status?.approved||0} onaylı`),
      pilotKpi('Okunan sayfa',status.scan_pages,`${status.open_scan_reviews} inceleme bekliyor`,status.open_scan_reviews?'warn':''),
      pilotKpi('İyileştirme',status.open_improvements,'açık / devam eden',status.open_improvements?'warn':''),
    ].join('');
    renderAcademicPeriods(periods);renderSyncRuns(runs);renderPilotAudits(audits);renderPilotReadiness(readiness);renderPilotIssues(issues);renderPilotUatRuns(uatRuns);renderPilotBackup(readiness);await loadPilotBenchmark();
    const admin=isAdmin();
    document.getElementById('academicPeriodForm')?.classList.toggle('readonly-form',!admin);
    document.querySelectorAll('#academicPeriodForm input,#academicPeriodForm select,#academicPeriodForm button,#bootstrapPeriods,#runImport,#validateImport,#pilotFile').forEach(el=>el.disabled=!admin);
  }catch(e){toast(e.message,'error');}
}
function pilotCheckIcon(status){return status==='pass'?'✓':status==='fail'?'!':'•';}
function pilotActionPage(action){return ({'Kurumsal Pilot':'import','Kullanıcı & Yetki':'users','Öğrenim Çıktısı ↔ Program Çıktısı Haritası':'outcomes','Optik Okuma':'scan','Sınav Hazırla':'exams','Değerlendirme':'grade','Kanıt Yönetimi':'evidence','Akreditasyon Merkezi':'accreditation','Sistem & Güvenlik':'security'})[action]||'';}
window.pilotGoAction=function(action){const page=pilotActionPage(action);if(page)showPage(page);};
function renderPilotReadiness(data){
  const score=document.getElementById('pilotReadinessScore');if(!score)return;
  score.textContent=`%${data.score||0}`;score.className=`readiness-score ${data.status||'attention'}`;
  const box=document.getElementById('pilotSetupChecklist');
  box.innerHTML=(data.checks||[]).map(x=>`<div class="pilot-check ${esc(x.status)}"><span class="pilot-check-icon">${pilotCheckIcon(x.status)}</span><div><b>${esc(x.label)}${x.required?' <em>Zorunlu</em>':''}</b><small>${esc(x.detail)}</small></div><span class="pilot-check-action">${pilotActionPage(x.action)?`<button class="ghost tiny" type="button" data-action-call="pilotGoAction('${esc(x.action)}')">${esc(x.action)} →</button>`:esc(x.action||'')}</span></div>`).join('');
}
function renderPilotIssues(rows){
  const badge=document.getElementById('pilotIssueCount');if(badge)badge.textContent=`${rows.length} sorun`;
  const box=document.getElementById('pilotIssueCenter');if(!box)return;
  box.innerHTML=rows.length?rows.slice(0,15).map(x=>`<div class="pilot-issue ${esc(x.severity)}"><span></span><div><b>${esc(x.title)}</b><small>${esc(x.message)}</small></div><em>${esc(x.action||x.source||'')}</em></div>`).join(''):'<div class="empty-state"><b>Açık operasyonel sorun yok.</b><span>Pilot hazırlık kontrolleri temiz.</span></div>';
}
function renderPilotUatRuns(rows){
  const box=document.getElementById('pilotUatHistory');if(!box)return;
  box.innerHTML=rows.length?`<div class="uat-run-list">${rows.map(x=>`<div class="uat-run"><span class="uat-dot ${esc(x.status)}"></span><div><b>UAT #${x.id} · %${x.score}</b><small>${esc((x.created_at||'').replace('T',' ').slice(0,19))} · ${esc(x.created_by||'system')}</small></div><em>${esc(({passed:'Geçti',warning:'Uyarı',failed:'Başarısız'})[x.status]||x.status)}</em></div>`).join('')}</div>`:'<p class="muted">Henüz UAT koşusu yok.</p>';
  const first=rows[0];const summary=document.getElementById('pilotUatSummary');if(summary)summary.innerHTML=first?`<div class="uat-score"><b>%${first.score}</b><span>Son UAT</span></div><div class="uat-check-mini">${(first.checks||[]).map(c=>`<span class="${esc(c.status)}">${pilotCheckIcon(c.status)} ${esc(c.label)}</span>`).join('')}</div>`:'<div class="empty-state"><b>İlk UAT&apos;ı çalıştırın.</b><span>Sistem mevcut veriyi değiştirmeden tüm pilot zincirini kontrol eder.</span></div>';
}
function renderPilotBackup(readiness){
  const box=document.getElementById('pilotBackupStatus');if(!box)return;const b=readiness.backup,r=readiness.restore;
  box.innerHTML=`<div class="backup-state ${b?'ok':'warn'}"><span>BACKUP</span><b>${b?esc((b.created_at||'').replace('T',' ').slice(0,19)):'Henüz yok'}</b><small>${b?esc(b.backup_zip||'Doğrulandı'):'Backup-Pilot.ps1 çalıştırın'}</small></div><div class="backup-state ${r?'ok':'warn'}"><span>RESTORE TESTİ</span><b>${r?esc((r.created_at||'').replace('T',' ').slice(0,19)):'Henüz yok'}</b><small>${r?'SHA256 doğrulandı':'Restore-Pilot.ps1 ile test edin'}</small></div>`;
}
async function loadPilotBenchmark(){
  const box=document.getElementById('pilotBenchmark');if(!box||!isAdmin()){if(box)box.innerHTML='<p class="muted">Benchmark yalnız sistem yöneticisine açıktır.</p>';return;}
  try{const r=await api('GET','/api/pilot/performance');const q=r.query_ms||{};box.innerHTML=`<div class="benchmark-grid"><span><small>Program sorgusu</small><b>${Number(q.program_count||0).toFixed(2)} ms</b></span><span><small>Ders sorgusu</small><b>${Number(q.course_count||0).toFixed(2)} ms</b></span><span><small>Öğrenci sorgusu</small><b>${Number(q.student_count||0).toFixed(2)} ms</b></span><span><small>Cevap sorgusu</small><b>${Number(q.response_count||0).toFixed(2)} ms</b></span></div>`;}catch(e){box.textContent=e.message;}
}
document.getElementById('runPilotUat')?.addEventListener('click',async()=>{if(!isAdmin()){toast('UAT koşusunu yalnız sistem yöneticisi başlatabilir.','error');return;}const btn=document.getElementById('runPilotUat');btn.disabled=true;btn.textContent='Kontrol ediliyor...';try{const r=await api('POST','/api/pilot/uat/run',{});toast(`UAT tamamlandı: %${r.score}`,(r.status==='failed'?'error':'ok'));await preparePilotOps();}catch(e){toast(e.message,'error');}finally{btn.disabled=false;btn.textContent='UAT çalıştır';}});
document.getElementById('refreshPilotBenchmark')?.addEventListener('click',loadPilotBenchmark);

function renderAcademicPeriods(rows){
  const box=document.getElementById('academicPeriodList');
  box.innerHTML=rows.length?rows.map(x=>{const locked=x.status==='locked'||x.status==='archived';const actions=isAdmin()?`<div class="period-actions">${x.status!=='active'&&x.status!=='archived'?`<button class="ghost small" data-action-call="setAcademicPeriodStatus(${x.id},'active')">Aktif yap</button>`:''}${x.status==='active'||x.status==='planned'?`<button class="ghost small danger-lite" data-action-call="setAcademicPeriodStatus(${x.id},'locked')">Kilitle</button>`:''}${x.status==='locked'?`<button class="ghost small" data-action-call="setAcademicPeriodStatus(${x.id},'planned')">Kilidi aç</button><button class="ghost small" data-action-call="setAcademicPeriodStatus(${x.id},'archived')">Arşivle</button>`:''}</div>`:'';return `<div class="period-row ${locked?'period-locked':''}"><div><b>${esc(x.title)}</b><span>${esc(x.academic_year)} · ${esc(x.term)} · ${x.course_count} ders · ${x.exam_count} sınav</span></div><div><span class="badge status-${x.status==='active'?'approved':x.status==='locked'||x.status==='archived'?'draft':'ready'}">${esc(periodStatusLabel(x.status))}</span>${actions}</div></div>`}).join(''):'<div class="empty-state"><b>Akademik dönem yok.</b><span>Derslerden otomatik oluşturabilir veya yeni dönem açabilirsiniz.</span></div>';
}
window.setAcademicPeriodStatus=async function(id,status){const labels={active:'aktif yapmak',planned:'kilidini açmak',locked:'kilitlemek',archived:'arşivlemek'};if((status==='locked'||status==='archived')&&!confirm(`Bu dönemi ${labels[status]} istiyor musunuz? Akademik/operasyonel veri değişiklikleri duracaktır.`))return;try{await api('POST',`/api/academic-periods/${id}/status`,{status});toast(`Dönem durumu: ${periodStatusLabel(status)}.`);await preparePilotOps();}catch(e){toast(e.message,'error');}};
function renderSyncRuns(rows){const box=document.getElementById('pilotSyncHistory');box.innerHTML=rows.length?`<table class="table compact-table"><thead><tr><th>Zaman</th><th>Kaynak</th><th>Dosya</th><th>Durum</th><th>Özet</th></tr></thead><tbody>${rows.map(x=>`<tr><td>${esc((x.created_at||'').replace('T',' ').slice(0,19))}</td><td>${esc(x.provider)}</td><td>${esc(x.filename)}</td><td><span class="${x.status==='success'?'pill-ok':'pill-warn'}">${esc(x.status)}</span></td><td>${esc(Object.entries(x.summary||{}).filter(([,v])=>typeof v==='number').slice(0,4).map(([k,v])=>`${k}:${v}`).join(' · '))}</td></tr>`).join('')}</tbody></table>`:'<p class="muted">Henüz OBS senkron kaydı yok.</p>';}
function renderPilotAudits(rows){const box=document.getElementById('pilotAuditLog');box.innerHTML=rows.length?`<div class="audit-timeline">${rows.map(x=>`<div class="audit-item"><span class="audit-dot"></span><div><b>${esc(x.actor_email||'system')}</b><span>${esc(x.action)} · ${esc(x.entity_type)}${x.entity_id?` #${x.entity_id}`:''}</span><small>${esc((x.created_at||'').replace('T',' ').slice(0,19))}</small></div></div>`).join('')}</div>`:'<p class="muted">Audit kaydı yok.</p>';}
document.getElementById('academicPeriodForm')?.addEventListener('submit',async ev=>{ev.preventDefault();const body={academic_year:document.getElementById('periodYear').value.trim(),term:document.getElementById('periodTerm').value,title:document.getElementById('periodTitle').value.trim(),starts_on:document.getElementById('periodStart').value||null,ends_on:document.getElementById('periodEnd').value||null};try{await api('POST','/api/academic-periods',body);toast('Akademik dönem oluşturuldu.');await preparePilotOps();}catch(e){toast(e.message,'error');}});
document.getElementById('bootstrapPeriods')?.addEventListener('click',async()=>{try{const r=await api('POST','/api/academic-periods/bootstrap',{});toast(`${r.created} akademik dönem oluşturuldu.`);await preparePilotOps();}catch(e){toast(e.message,'error');}});

function applyObsIntegrationPolicy(){
  const obs=state.authConfig?.integrations?.obs||{};
  const push=document.getElementById('obsResultsPush');
  const chip=document.getElementById('obsModeChip');
  const note=document.getElementById('obsWritebackNote');
  const enabled=obs.writeback_enabled===true;
  if(push){push.hidden=!enabled;push.disabled=!enabled;}
  if(chip){chip.textContent=enabled?'OBS write-back onaylı':'OBS read-only';}
  if(note){note.textContent=enabled?(obs.endpoint_configured?'Kurumsal onaylı write-back etkin; gönderimler audit log ve senkron geçmişine kaydedilir.':'Write-back onaylı ancak OBS endpoint yapılandırması bekleniyor.'):'Read-only güvenli mod aktif. OBS write-back kurumsal onay olmadan kullanılamaz.';}
}

document.getElementById('obsResultsExport')?.addEventListener('click',async()=>{const id=Number(document.getElementById('obsResultsCourse')?.value||0);if(!id)return toast('Ders seçin.','error');try{await downloadApi(`/api/courses/${id}/obs-results.xlsx`,`DOU-Assess-OBS-Ders-${id}.xlsx`);toast('OBS sonuç Excel’i hazırlandı.');}catch(e){toast(e.message,'error');}});
document.getElementById('obsResultsPush')?.addEventListener('click',async()=>{const id=Number(document.getElementById('obsResultsCourse')?.value||0);if(!id)return toast('Ders seçin.','error');if(!confirm('Bu dersin ağırlıklı sonuçları yapılandırılmış OBS API uç noktasına gönderilsin mi?'))return;const btn=document.getElementById('obsResultsPush');btn.disabled=true;try{const r=await api('POST',`/api/courses/${id}/obs-results/push`,{});toast(`${r.record_count||0} sonuç OBS’ye gönderildi.`);await preparePilotOps();}catch(e){toast(e.message,'error');}finally{btn.disabled=false;}});
document.getElementById('refreshPilotOps')?.addEventListener('click',preparePilotOps);
document.getElementById('periodTerm')?.addEventListener('change',()=>{const y=document.getElementById('periodYear').value.trim();document.getElementById('periodTitle').value=`${y} ${document.getElementById('periodTerm').value}`.trim();});
document.getElementById('periodYear')?.addEventListener('input',()=>{document.getElementById('periodTitle').value=`${document.getElementById('periodYear').value.trim()} ${document.getElementById('periodTerm').value}`.trim();});

async function updateExamCourseSummary(){
  const courseId=Number(document.getElementById('examCourse').value);const box=document.getElementById('examCourseSummary');if(!courseId||!box)return;
  const course=state.courses.find(x=>x.id===courseId);if(!course)return;
  try{const [summary,enrollments]=await Promise.all([api('GET',`/api/courses/${courseId}/outcome-summary`),api('GET',`/api/courses/${courseId}/enrollments`)]);const studentState=enrollments.length?`<div class="course-summary-status ok"><b>✓ ${enrollments.length} öğrenci hazır</b><span>Yeni sınav oluşturulunca ders kayıtları otomatik sınava aktarılır.</span></div>`:`<div class="course-summary-status warn"><div><b>Bu derste kayıtlı öğrenci yok</b><span>Kişiselleştirilmiş kağıt ve optik için önce öğrenci / ders kaydı ekleyin.</span></div><button type="button" class="ghost small" data-action-call="openEnrollmentForCourse(${courseId})">Öğrenci ata →</button></div>`;box.innerHTML=`<div class="course-summary-grid"><span><small>Ders</small><b>${esc(course.code)} · ${esc(course.name)}</b></span><span><small>Öğrenci</small><b class="${enrollments.length?'text-ok':'text-warn'}">${enrollments.length}</b></span><span><small>Öğrenim ve Program Çıktıları</small><b>${summary.learning_outcome_count} / ${summary.program_outcome_count}</b></span><span><small>Öğrenim Çıktısı → Program Çıktısı hazır</small><b class="${summary.mapped_learning_outcome_count===summary.learning_outcome_count?'text-ok':'text-warn'}">${summary.mapped_learning_outcome_count}/${summary.learning_outcome_count}</b></span></div>${studentState}`;}catch(e){box.textContent='Ders özeti yüklenemedi.';}
}
function applyExamPreset(preset){document.getElementById('examType').value=preset;document.getElementById('examTitle').value=`${preset} Sınavı`;const rec={'Vize':60,'Final':60,'Bütünleme':60,'Mazeret':60,'Tek Ders':60,'Muafiyet':60,'Kısa Sınav':20,'Uygulama':60};if(rec[preset])document.getElementById('examDuration').value=String(rec[preset]);document.querySelectorAll('#examPresetButtons button').forEach(x=>x.classList.toggle('active',x.dataset.preset===preset));}
function examStatusLabel(s){return ({draft:'Taslak',ready:'Hazır',grading:'Puanlama',approved:'Onaylı',archived:'Arşiv'})[s]||s;}
function renderExamStateBar(exam){
  const box=document.getElementById('examStateBar');if(!box||!exam)return;
  const steps=[['draft','Taslak'],['ready','Hazır'],['printed','Basıldı'],['grading','Puanlama'],['approved','Onaylı']];
  const cur=exam.status==='ready'&&exam.printed_at?'printed':exam.status;const idx=Math.max(0,steps.findIndex(x=>x[0]===cur));
  const rule=({draft:'Sorular, puanlar ve kâğıt düzeni serbestçe düzenlenebilir. Puan girişi kapalıdır.',ready:'Sorular kilitli. Basıma geçebilir ya da taslağa dönüp düzenleyebilirsiniz.',printed:'Kâğıtlar basıldı: sorular kilitli. Değişiklik için sınavı kopyalayıp yeni sürüm oluşturun.',grading:'Optik okuma ve puan girişi açık. Sorular kilitli.',approved:'Sonuçlar onaylandı. Puan değişikliği yalnızca itiraz/yeniden değerlendirme akışıyla yapılır.',archived:'Arşivlenmiş sınav yalnızca okunur.'})[cur]||'';
  const lock=exam.grade_locked_at?` · Puanlar kilitli (${esc(exam.grade_locked_by||'')})`:'';
  box.innerHTML=`<ol class="state-steps">${steps.map((x,i)=>`<li class="${i<idx?'done':i===idx?'current':''}">${esc(x[1])}</li>`).join('')}</ol><p class="state-rule"><b>${esc(steps[idx]?.[1]||examStatusLabel(exam.status))}</b> — ${esc(rule)}${lock}</p>`;
}
function renderExamCenterKpis(rows){const box=document.getElementById('examCenterKpis');if(!box)return;const total=state.exams.length;const counts={draft:0,ready:0,grading:0,approved:0,archived:0};state.exams.forEach(x=>counts[x.status]=(counts[x.status]||0)+1);box.innerHTML=[['Toplam',total,'erişilebilir sınav'],['Taslak',counts.draft,'hazırlık sürüyor'],['Uygulamaya hazır',counts.ready,'çıktı alınabilir'],['Puanlama',counts.grading,'değerlendirme açık'],['Onaylı',counts.approved,'resmî sonuç'],['Arşiv',counts.archived,'kanıt kilitli']].map(x=>`<div class="exam-center-kpi"><b>${x[1]}</b><span>${x[0]}</span><small>${x[2]}</small></div>`).join('');}
function examCardSchedule(e){const parts=[];if(e.exam_date)parts.push(e.exam_date);if(e.start_time)parts.push(e.start_time);if(e.location)parts.push(e.location);return parts.join(' · ')||'Plan bilgisi bekliyor';}
async function loadExams(){
  try{
    await refreshCore();await updateExamCourseSummary();
    const q=(document.getElementById('examSearch')?.value||'').trim().toLocaleLowerCase('tr-TR'),status=document.getElementById('examStatusFilter')?.value||'',courseId=Number(document.getElementById('examCourseFilter')?.value||0),type=document.getElementById('examTypeFilter')?.value||'';
    const rows=state.exams.filter(e=>(!status||e.status===status)&&(!courseId||e.course_id===courseId)&&(!type||e.exam_type===type)&&(!q||`${e.title} ${e.exam_type} ${e.id}`.toLocaleLowerCase('tr-TR').includes(q)));
    renderExamCenterKpis(rows);document.getElementById('examResultCount').textContent=`${rows.length} sınav`;
    document.getElementById('examList').innerHTML=rows.length?rows.map(e=>{const c=state.courses.find(x=>x.id===e.course_id);return `<button class="exam-file-card" data-action-call="openExam(${e.id})"><div class="exam-file-top"><span class="exam-file-id">#${e.id}</span><span class="badge status-${e.status}">${esc(examStatusLabel(e.status))}</span></div><div class="exam-file-copy"><b>${esc(e.title)}</b><span>${c?`${esc(c.code)} · ${esc(c.name)}`:`Sınav #${e.id}`} · ${esc(e.exam_type)}</span><small>${esc(examCardSchedule(e))}</small></div><div class="exam-file-bottom"><span>${e.duration_minutes} dk${e.assessment_weight_percent!=null?` · ders notu %${e.assessment_weight_percent}`:''}</span><strong>${e.booklet_count||4} kitapçık</strong></div></button>`}).join(''):'<div class="empty-state"><b>Eşleşen sınav yok.</b><span>Filtreleri değiştirin veya yeni sınav taslağı oluşturun.</span></div>';
  }catch(e){toast(e.message,'error');}
}
document.getElementById('examCourse').addEventListener('change',updateExamCourseSummary);
document.querySelectorAll('#examPresetButtons button').forEach(b=>b.addEventListener('click',()=>applyExamPreset(b.dataset.preset)));
['examSearch','examStatusFilter','examCourseFilter','examTypeFilter'].forEach(id=>document.getElementById(id)?.addEventListener(id==='examSearch'?'input':'change',loadExams));
document.getElementById('examFocusCreate')?.addEventListener('click',()=>document.getElementById('examCreateCard')?.scrollIntoView({behavior:'smooth',block:'start'}));

document.getElementById('examForm').addEventListener('submit',async ev=>{
  ev.preventDefault();const weightRaw=document.getElementById('examWeight').value;
  const body={course_id:Number(document.getElementById('examCourse').value),title:document.getElementById('examTitle').value.trim(),exam_type:document.getElementById('examType').value.trim()||'Sınav',exam_date:document.getElementById('examDate').value||null,start_time:document.getElementById('examStartTime').value||null,location:document.getElementById('examLocation').value.trim(),duration_minutes:Number(document.getElementById('examDuration').value||50),assessment_weight_percent:weightRaw===''?null:Number(weightRaw),booklet_count:Number(document.getElementById('examBookletCount').value||4),paper_size:document.getElementById('examPaperSize').value,paper_orientation:document.getElementById('examPaperOrientation').value,omr_mode:document.getElementById('examOmrMode').value,duplex_print:document.getElementById('examDuplex').checked,instructions:document.getElementById('examInstructions').value,staff_notes:document.getElementById('examStaffNotes').value,sync_students:true};
  try{const exam=await api('POST','/api/exams',body);if(!exam.id)throw new Error('Backend sınav ID döndürmedi.');toast(`Sınav #${exam.id} oluşturuldu. Detayları ve Öğrenim ve Program Çıktıları snapshot’ını kontrol edin.`);await loadExams();await openExam(exam.id);setExamWizardStep(1);}catch(e){toast(e.message,'error');}
});
function renderExamDetailStrip(exam){const snap=exam.paper_snapshot||{},box=document.getElementById('examDetailStrip');if(!box)return;const rows=[['Ders',`${snap.course_code||''} · ${snap.course_name||''}`],['Tarih / Saat',`${exam.exam_date||'—'}${exam.start_time?` · ${exam.start_time}`:''}`],['Salon',exam.location||'—'],['Süre',`${exam.duration_minutes} dk`],['Ders etkisi',exam.assessment_weight_percent==null?'—':`%${exam.assessment_weight_percent}`],['Kitapçık',String(exam.booklet_count||4)]];box.innerHTML=rows.map(x=>`<div><small>${esc(x[0])}</small><b>${esc(x[1])}</b></div>`).join('');}
function renderExamWorkspaceSummary(summary){
  state.examWorkspaceSummary=summary;const p=summary.progress,r=summary.readiness,box=document.getElementById('examWorkspaceSummary');if(!box)return;
  const metrics=[['Sorular',p.questions,`${r.total_points}/100 puan`,r.ready?'ok':'warn'],['Öğrenci',p.students,'sınava atanmış',''],['Puanlama',`%${p.graded_student_percent}`,`${p.graded_students}/${p.students} öğrenci`,p.graded_student_percent===100&&p.students?'ok':''],['Tarama',p.scanned_pages,`${p.pending_reviews} inceleme`,p.pending_reviews?'warn':''],['Kanıt',p.evidence_count,`${p.open_improvements} açık aksiyon`,p.open_improvements?'warn':'']];
  const activity=(summary.recent_activity||[]).slice(0,4);const next=summary.next_action||{};
  box.innerHTML=`<div class="workspace-metrics">${metrics.map(x=>`<div class="workspace-metric ${x[3]}"><b>${esc(x[1])}</b><span>${esc(x[0])}</span><small>${esc(x[2])}</small></div>`).join('')}</div><div class="workspace-ops"><div class="workspace-next"><span class="eyebrow">SONRAKİ ÖNERİLEN ADIM</span><b>${esc(next.label||'Sınavı kontrol edin')}</b><small>Sistem sınav durumuna ve tamamlanma oranına göre önerir.</small><button class="primary small" type="button" data-action-call="goExamNextAction()">Devam et →</button></div><div class="workspace-activity"><span class="eyebrow">SON İŞLEMLER</span>${activity.length?activity.map(a=>`<div><b>${esc(a.action)}</b><span>${esc(a.actor_email||'system')}</span><small>${esc((a.created_at||'').replace('T',' ').slice(0,16))}</small></div>`).join(''):'<p class="muted">Henüz sınav aktivitesi yok.</p>'}</div></div>`;
}
window.goExamNextAction=function(){const next=state.examWorkspaceSummary?.next_action;if(!next)return;if(next.page==='exams'){setExamWizardStep(next.step||1);document.getElementById('examEditor')?.scrollIntoView({behavior:'smooth',block:'start'});if(next.code==='mark_ready'&&state.currentExam?.status==='draft')toast('Kontrol & Çıktı adımında Hazır durumuna alabilirsiniz.');return;}showPage(next.page||'exams');if(next.page==='scan'&&state.currentExam){setTimeout(()=>{const el=document.getElementById('scanExam');if(el){el.value=String(state.currentExam.id);el.dispatchEvent(new Event('change'));}},80);}if(next.page==='grade'&&state.currentExam){setTimeout(()=>{const el=document.getElementById('gradeExam');if(el){el.value=String(state.currentExam.id);el.dispatchEvent(new Event('change'));}},80);}if(next.page==='analytics'&&state.currentExam){setTimeout(()=>{const el=document.getElementById('analyticsExam');if(el){el.value=String(state.currentExam.id);el.dispatchEvent(new Event('change'));}},80);}};
function syncBookletControls(exam){const allowed=['A','B','C','D'].slice(0,exam.booklet_count||4),sel=document.getElementById('paperBooklet');[...sel.options].forEach(o=>o.hidden=!allowed.includes(o.value));if(!allowed.includes(sel.value))sel.value='A';document.querySelectorAll('[data-paper-booklet]').forEach(b=>b.classList.toggle('hidden',!allowed.includes(b.dataset.paperBooklet)));}
function renderExamApprovalPanel(exam){const box=document.getElementById('examApprovalPanel');if(!box)return;const pending=Boolean(exam.approval_requested_at);const approved=Boolean(exam.approved_at);if(exam.status==='draft'||exam.status==='ready'){box.innerHTML='<span class="eyebrow">KURUMSAL ONAY</span><b>Onay zinciri puanlama tamamlanınca açılır.</b><small>Hazırlayan ve onaylayan işlem izi audit kaydında tutulur.</small>';return;}if(exam.status==='grading'){box.innerHTML=`<span class="eyebrow">KURUMSAL ONAY</span><b>${pending?'Onay bekliyor':'Onaya gönderilmeyi bekliyor'}</b><small>${pending?`${esc(exam.approval_requested_by||'')} · ${esc((exam.approval_requested_at||'').replace('T',' ').slice(0,16))}`:'Tüm öğrenci değerlendirmeleri tamamlandığında onay talebi oluşturun.'}</small>${exam.approval_note?`<p>${esc(exam.approval_note)}</p>`:''}<div class="actions">${!pending?'<button type="button" class="primary small" data-approval-action="request">Onaya gönder</button>':'<button type="button" class="primary small" data-approval-action="approve">Onayla</button><button type="button" class="ghost small" data-approval-action="reject">Revizyon iste</button>'}</div>`;return;}box.innerHTML=`<span class="eyebrow">KURUMSAL ONAY</span><b>${approved?'Onaylandı':'Onay kaydı'}</b><small>${esc(exam.approved_by||'')} ${exam.approved_at?`· ${esc(exam.approved_at.replace('T',' ').slice(0,16))}`:''} · Revizyon ${exam.revision_no||1}</small>${exam.approval_note?`<p>${esc(exam.approval_note)}</p>`:''}`;}
async function requestExamApproval(){if(!state.currentExam)return;const data=await workflowForm({eyebrow:'SINAV ONAYI',title:'Sınavı onaya gönder',description:'Onaylayanın göreceği kısa notu ekleyebilirsiniz.',submitLabel:'Onaya gönder',fields:[{name:'note',label:'Onay notu',type:'textarea',rows:4,placeholder:'İsteğe bağlı açıklama'}]});if(!data)return;try{const x=await api('POST',`/api/exams/${state.currentExam.id}/approval-request`,{note:data.note||''});toast('Sınav onaya gönderildi.');await openExam(x.id);}catch(e){toast(e.message,'error');}}
async function rejectExamApproval(){if(!state.currentExam)return;const data=await workflowForm({eyebrow:'REVİZYON',title:'Revizyon iste',description:'Sınavı hazırlayan öğretim elemanına net bir gerekçe iletin.',submitLabel:'Revizyon iste',fields:[{name:'note',label:'Revizyon gerekçesi',type:'textarea',rows:5,value:'Revizyon gerekli',required:true}]});if(!data)return;try{const x=await api('POST',`/api/exams/${state.currentExam.id}/approval-reject`,{note:data.note});toast('Revizyon istendi.');await openExam(x.id);}catch(e){toast(e.message,'error');}}
document.getElementById('examApprovalPanel')?.addEventListener('click',ev=>{const b=ev.target.closest('[data-approval-action]');if(!b)return;if(b.dataset.approvalAction==='request')requestExamApproval();if(b.dataset.approvalAction==='approve')changeCurrentExamStatus('approved');if(b.dataset.approvalAction==='reject')rejectExamApproval();});
window.openExam=async function(id){
  try{if(!state.currentExam||state.currentExam.id!==id)state.currentWizardStep=1;
    const summary=await api('GET',`/api/exams/${id}/workspace-summary`),exam=summary.exam;state.currentExam=exam;
    const box=document.getElementById('examEditor');box.classList.remove('hidden');box.scrollIntoView({behavior:'smooth',block:'start'});
    document.getElementById('editorTitle').textContent=`${exam.title} · #${exam.id}`;document.getElementById('editorMeta').textContent=`${exam.exam_type} · ${exam.student_count} öğrenci · ${exam.duration_minutes} dk${exam.exam_date?` · ${exam.exam_date}`:''}${exam.start_time?` ${exam.start_time}`:''}`;
    renderExamStateBar(exam);const sb=document.getElementById('examStatusBadge');sb.textContent=(exam.status==='ready'&&exam.printed_at)?'Basıldı':examStatusLabel(exam.status);sb.className=`badge status-${exam.status}`;
    const locked=exam.status!=='draft';document.getElementById('questionForm').classList.toggle('hidden',locked);document.getElementById('deleteExam').classList.toggle('hidden',exam.status!=='draft');
    const transitions={draft:{next:'ready',back:null},ready:{next:'grading',back:'draft'},grading:{next:'approved',back:'ready'},approved:{next:'archived',back:null},archived:{next:null,back:null}},tr=transitions[exam.status]||{};document.getElementById('statusNext').classList.toggle('hidden',!tr.next);document.getElementById('statusNext').dataset.status=tr.next||'';document.getElementById('statusNext').textContent=tr.next?`→ ${examStatusLabel(tr.next)}`:'Sonraki durum';document.getElementById('statusBack').classList.toggle('hidden',!tr.back);document.getElementById('statusBack').dataset.status=tr.back||'';document.getElementById('statusBack').textContent=tr.back?`← ${examStatusLabel(tr.back)}`:'Geri';if(exam.status==='grading'&&!exam.approval_requested_at){document.getElementById('statusNext').dataset.status='request_approval';document.getElementById('statusNext').textContent='→ Onaya gönder';}renderExamApprovalPanel(exam);
    const snap=exam.paper_snapshot||{};document.getElementById('paperSnapshot').innerHTML=`<div><b>Resmî kağıt snapshot'ı</b><span class="badge">${esc(exam.paper_template_version||'dou-official-v1')}</span></div><div class="snapshot-grid"><span><small>Ders</small><b>${esc(snap.course_code||'')} · ${esc(snap.course_name||'')}</b></span><span><small>Dönem</small><b>${esc(snap.academic_year||'')} · ${esc(snap.term||'')}</b></span><span><small>Öğretim elemanı</small><b>${esc(snap.instructor||'Tanımsız')}</b></span><span><small>Program</small><b>${esc(snap.program_name||'')} ${snap.department?`· ${esc(snap.department)}`:''}</b></span></div>`;
    document.getElementById('snapshotBadges').innerHTML=exam.learning_outcomes.map(x=>`<span class="badge">${esc(x.code)} · hedef %${x.target_percent}</span>`).join('')||'<span class="muted">Bu derste Öğrenim Çıktısı tanımlı değil.</span>';document.getElementById('qLo').innerHTML=exam.learning_outcomes.map(x=>`<option value="${esc(x.code)}">${esc(x.code)} · ${esc(x.description)}</option>`).join('');
    document.getElementById('draftTitle').value=exam.title||'';document.getElementById('draftType').value=exam.exam_type||'';document.getElementById('draftDate').value=exam.exam_date||'';document.getElementById('draftStartTime').value=exam.start_time||'';document.getElementById('draftLocation').value=exam.location||'';document.getElementById('draftDuration').value=exam.duration_minutes||50;document.getElementById('draftWeight').value=exam.assessment_weight_percent??'';document.getElementById('draftBookletCount').value=String(exam.booklet_count||4);document.getElementById('draftPaperSize').value=exam.paper_size||'A4';document.getElementById('draftPaperOrientation').value=exam.paper_orientation||'portrait';document.getElementById('draftOmrMode').value=exam.omr_mode||'embedded';document.getElementById('draftDuplex').checked=Boolean(exam.duplex_print);document.getElementById('draftInstructions').value=exam.instructions||'';document.getElementById('draftStaffNotes').value=exam.staff_notes||'';
    document.getElementById('examDraftForm').classList.toggle('form-disabled',locked);document.querySelectorAll('#examDraftForm input,#examDraftForm textarea,#examDraftForm select,#examDraftForm button').forEach(x=>x.disabled=locked);
    renderExamDetailStrip(exam);renderExamWorkspaceSummary(summary);loadExamAppeals(exam.id);syncBookletControls(exam);renderExamOutcomePlan(exam);renderOutcomePicker(exam);renderQuestions(exam.questions);renderQuestionComposerStats(exam);await loadExamReadiness(exam.id);await loadExamBank(exam);resetQuestionEditor();setExamWizardStep(state.currentWizardStep||1);
  }catch(e){toast(e.message,'error');}
};
document.getElementById('lockGrades')?.addEventListener('click',async()=>{const e=state.currentExam;if(!e)return;try{const st=await api('GET',`/api/exams/${e.id}/grade-lock`);if(st.locked)return toast(`Puanlar zaten kilitli (${st.locked_by||'—'}).`);if(!confirm('Puanlar kilitlenecek; sonuçlar öğrencilere açılabilir hâle gelir. Kilidi yalnız Program Başkanı/Yönetici açabilir. Devam?'))return;await api('POST',`/api/exams/${e.id}/grade-lock`,{note:''});toast('Puanlar kilitlendi.');}catch(err){toast(err.message,'error');}});
document.getElementById('studentLinks')?.addEventListener('click',async()=>{const e=state.currentExam;if(!e)return;try{const r=await api('GET',`/api/exams/${e.id}/student-links`);const csv='\uFEFFogrenci_no;ad_soyad;baglanti\n'+r.links.map(x=>`${x.student_no};${x.full_name};${location.origin}${x.path}`).join('\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));a.download=`ogrenci-baglantilari-${e.id}.csv`;a.click();toast(`${r.links.length} bağlantı indirildi. Her bağlantı yalnızca ilgili öğrencinin kâğıdını açar; itiraz süresi ${r.appeal_days} gün.`);}catch(err){toast(err.message,'error');}});
document.getElementById('duplicateExam')?.addEventListener('click',async()=>{if(!state.currentExam)return;try{const x=await api('POST',`/api/exams/${state.currentExam.id}/duplicate`,{title:`${state.currentExam.title} · Kopya`,exam_date:null});toast('Sınav soruları ve Öğrenim ve Program Çıktıları snapshot’ıyla taslak olarak kopyalandı.');await loadExams();await openExam(x.id);}catch(e){toast(e.message,'error');}});

async function loadExamAppeals(examId){
  const box=document.getElementById('examAppeals');if(!box)return;
  let rows=[];try{rows=await api('GET',`/api/exams/${examId}/appeals`)}catch{box.classList.add('hidden');return}
  if(!rows.length){box.classList.add('hidden');return}
  const qs=Object.fromEntries((state.currentExam?.questions||[]).map(q=>[q.id,q]));const open=rows.filter(r=>r.status==='open');
  box.classList.remove('hidden');
  document.getElementById('appealsTitle').textContent=`${open.length} açık · ${rows.length-open.length} sonuçlanmış`;document.getElementById('rejectAllAppeals').classList.toggle('hidden',open.length<2);
  document.getElementById('appealsList').innerHTML=rows.map(a=>`<div class="record"><b>Öğrenci #${a.student_id} · ${qs[a.question_id]?`Soru ${qs[a.question_id].order_no}`:'Genel'} · ${esc(a.status==='open'?'Açık':a.status==='accepted'?'Kabul':'Red')}</b><small>${esc(a.reason)}${a.decision_note?` — Karar: ${esc(a.decision_note)}`:''}${a.new_points!=null?` · ${a.old_points??'—'} → ${a.new_points}`:''}</small>${a.status==='open'?`<div class="row"><button class="ghost small" data-appeal-accept="${a.id}">Kabul et</button><button class="ghost small" data-appeal-reject="${a.id}">Reddet</button></div>`:''}</div>`).join('');
  const byId=Object.fromEntries(rows.map(a=>[a.id,a]));
  const decide=async(a,decision)=>{
    const q=qs[a.question_id];const fields=[{name:'note',label:'Karar gerekçesi',type:'textarea',required:true,rows:3}];
    if(decision==='accepted'&&q){if(q.question_type==='classic')(q.rubric?.criteria||[]).forEach(c=>fields.push({name:'r_'+c.id,label:`${c.label} (0–${c.max_points})`,type:'number',required:true,value:a.old_rubric_scores?.[c.id]??''}));else fields.push({name:'points',label:`Yeni puan (0–${q.points})`,type:'number',required:true,value:q.points});}
    const d=await workflowForm({eyebrow:'NOT İTİRAZI',title:decision==='accepted'?'İtirazı kabul et':'İtirazı reddet',description:'Karar öğrenci portalında gerekçesiyle görünür.',submitLabel:decision==='accepted'?'Kabul et ve puanı güncelle':'Reddet',fields});if(!d)return;
    const body={decision,decision_note:d.note};if(decision==='accepted'&&q){if(q.question_type==='classic'){body.rubric_scores={};(q.rubric?.criteria||[]).forEach(c=>body.rubric_scores[c.id]=Number(d['r_'+c.id]));}else body.awarded_points=Number(d.points);}
    try{await api('PATCH',`/api/appeals/${a.id}`,body);toast('İtiraz sonuçlandırıldı.');await loadExamAppeals(examId)}catch(e){toast(e.message,'error')}};
  box.querySelectorAll('[data-appeal-accept]').forEach(b=>b.addEventListener('click',()=>decide(byId[b.dataset.appealAccept],'accepted')));
  box.querySelectorAll('[data-appeal-reject]').forEach(b=>b.addEventListener('click',()=>decide(byId[b.dataset.appealReject],'rejected')));
  {const old=document.getElementById('rejectAllAppeals'),btn=old.cloneNode(true);old.replaceWith(btn);btn.addEventListener('click',async()=>{const d=await workflowForm({eyebrow:'TOPLU KARAR',title:`${open.length} itirazı reddet`,description:'Aynı gerekçe tüm açık itirazlara uygulanır. Puan değişmez.',submitLabel:'Tümünü reddet',fields:[{name:'note',label:'Ortak gerekçe',type:'textarea',required:true,rows:3}]});if(!d)return;let ok=0;for(const a of open){try{await api('PATCH',`/api/appeals/${a.id}`,{decision:'rejected',decision_note:d.note});ok++}catch(e){toast(e.message,'error')}}toast(`${ok} itiraz reddedildi.`);await loadExamAppeals(examId)});}
}

async function loadExamReadiness(examId){
  const r=await api('GET',`/api/exams/${examId}/readiness`);
  const box=document.getElementById('examReadiness');
  box.className=`readiness-panel ${r.ready?'is-ready':'not-ready'}`;
  const pointFix=Math.abs(Number(r.total_points||0)-100)>.01&&r.question_count?`<button type="button" class="ghost small readiness-fix" data-action-call="normalizeExamPointsFromReadiness()">Puanları 100'e ölçekle</button>`:'';
  box.innerHTML=`<div class="readiness-head"><div><b>${r.ready?'Sınav kağıdı hazır':'Hazırlık kontrolü'}</b><small>${r.ready?'Temel sınav koşulları tamamlandı':'Eksikleri tamamlayın; sistem neyin kaldığını gösteriyor'}</small></div><span>${Number(r.total_points||0).toLocaleString('tr-TR')}/100 puan · ${r.question_count} soru</span></div><div class="readiness-counts"><span>${r.mcq_count} test</span><span>${r.classic_count} klasik</span><span>${r.mapped_questions}/${r.question_count} Öğrenim Çıktısı eşleşmesi</span><span>${r.student_count||0} sınav öğrencisi</span></div>${r.issues.length?`<div class="readiness-issue-list">${r.issues.map(x=>`<div><i>!</i><span>${esc(x)}</span></div>`).join('')}</div>`:'<div class="readiness-success">Temel sınav kontrolü tamamlandı.</div>'}${r.warnings?.length?`<div class="readiness-warning-list">${r.warnings.map(x=>`<div><i>i</i><span>${esc(x)}</span></div>`).join('')}</div>`:''}${pointFix?`<div class="readiness-actions">${pointFix}</div>`:''}`;
  renderExamStudentAssignment(r);
  const batch=document.getElementById('downloadStudentPapers');if(batch){batch.disabled=!(r.student_count>0);batch.title=r.student_count>0?'Öğrenciye özel kağıtları toplu üret':'Önce ders öğrencilerini sınava aktarın';}
  return r;
}
function renderExamStudentAssignment(r){
  const box=document.getElementById('examStudentAssignment');if(!box)return;
  const assigned=Number(r.student_count||0),enrolled=Number(r.course_enrollment_count||0);
  const synced=enrolled>0&&assigned===enrolled;
  const title=synced?'Öğrenci ataması hazır':assigned?'Sınava kimlerin gireceğini kontrol edin':'Sınava öğrenci atayın';
  const detail=enrolled?`${assigned} / ${enrolled} ders kayıtlı öğrenci bu sınava atanmış`:'Bu derste kayıtlı öğrenci bulunmuyor';
  let actions='';
  if(enrolled){
    actions=`<button type="button" class="${assigned?'ghost':'primary'} small" data-action-call="openExamStudentManager()">Öğrencileri seç / yönet</button>${enrolled>assigned?`<button type="button" class="ghost small" data-action-call="syncExamStudentsNow()">Tümünü ata</button>`:''}`;
  }else{
    actions=`<button type="button" class="primary small" data-action-call="openExamCourseEnrollment()">Önce derse öğrenci ekle</button>`;
  }
  box.className=`student-assignment-panel ${synced?'is-synced':enrolled?'needs-sync':'is-empty'}`;
  box.innerHTML=`<div class="student-assignment-icon">${synced?'✓':'Ö'}</div><div class="student-assignment-copy"><span class="eyebrow">ÖĞRENCİ ATAMASI</span><b>${title}</b><small>${detail}</small><div class="student-assignment-meter"><span data-style="width:${enrolled?Math.min(100,assigned/enrolled*100):0}%"></span></div></div><div class="student-assignment-action">${actions}</div>`;
}
window.syncExamStudentsNow=async function(){if(!state.currentExam)return;try{const r=await api('POST',`/api/exams/${state.currentExam.id}/sync-students`,{});toast(r.created?`${r.created} öğrenci sınava eklendi.`:`Öğrenci ataması zaten güncel.`);await loadExams();await openExam(state.currentExam.id);setExamWizardStep(4);}catch(e){toast(e.message,'error');}};
window.openExamCourseEnrollment=function(){if(!state.currentExam)return;const courseId=state.currentExam.course_id;showPage('data');setTimeout(()=>openEnrollmentForCourse(courseId),120);};

function closeExamStudentManager(){document.getElementById('examStudentManager')?.classList.add('hidden');document.getElementById('examStudentManagerBackdrop')?.classList.add('hidden');}
function examAssignmentSelectedIds(){return [...(state.examStudentAssignmentSelection||new Set())];}
function updateExamStudentSelectedCount(){const count=examAssignmentSelectedIds().length,el=document.getElementById('examStudentSelectedCount');if(el)el.textContent=`${count} öğrenci seçili`;const data=state.examStudentAssignmentData;if(data){const stats=document.getElementById('examStudentManagerStats');if(stats)stats.innerHTML=`<div><b>${data.course_enrollment_count}</b><span>Ders kayıtlı</span></div><div><b>${count}</b><span>Sınava seçili</span></div><div><b>${Math.max(0,data.course_enrollment_count-count)}</b><span>Sınav dışı</span></div>`;}}
function renderExamStudentManagerList(){const data=state.examStudentAssignmentData,box=document.getElementById('examStudentManagerList');if(!data||!box)return;const selected=state.examStudentAssignmentSelection||new Set();const q=(document.getElementById('examStudentSearch')?.value||'').trim().toLocaleLowerCase('tr-TR');const rows=(data.students||[]).filter(s=>!q||`${s.student_no} ${s.full_name} ${s.class_name||''}`.toLocaleLowerCase('tr-TR').includes(q));box.innerHTML=rows.length?rows.map(s=>`<label class="exam-student-pick-row ${selected.has(Number(s.id))?'was-assigned':''}"><input type="checkbox" data-exam-student-id="${s.id}" ${selected.has(Number(s.id))?'checked':''} ${data.locked?'disabled':''}><span class="exam-student-pick-avatar">${esc(initials(s.full_name))}</span><span class="exam-student-pick-main"><b>${esc(s.student_no)} · ${esc(s.full_name)}</b><small>${esc(s.class_name||'Sınıf bilgisi yok')}</small></span><span class="exam-student-pick-status">${selected.has(Number(s.id))?'Seçili':'Ders kayıtlı'}</span></label>`).join(''):'<div class="empty-state compact-empty"><b>Öğrenci bulunamadı.</b><span>Arama filtresini temizleyin.</span></div>';box.querySelectorAll('input[data-exam-student-id]').forEach(x=>x.addEventListener('change',()=>{const id=Number(x.dataset.examStudentId);if(x.checked)state.examStudentAssignmentSelection.add(id);else state.examStudentAssignmentSelection.delete(id);x.closest('.exam-student-pick-row')?.classList.toggle('was-assigned',x.checked);const st=x.closest('.exam-student-pick-row')?.querySelector('.exam-student-pick-status');if(st)st.textContent=x.checked?'Seçili':'Ders kayıtlı';updateExamStudentSelectedCount();}));updateExamStudentSelectedCount();}
window.openExamStudentManager=async function(){if(!state.currentExam)return;try{const data=await api('GET',`/api/exams/${state.currentExam.id}/student-assignment`);state.examStudentAssignmentData=data;state.examStudentAssignmentSelection=new Set((data.students||[]).filter(x=>x.assigned).map(x=>Number(x.id)));document.getElementById('examStudentManagerTitle').textContent=`${state.currentExam.title} · Öğrenci seçimi`;document.getElementById('examStudentManagerSub').textContent=`Ders kayıtlı ${data.course_enrollment_count} öğrenciden bu sınava katılacak kişileri işaretleyin.`;const notice=document.getElementById('examStudentManagerNotice');if(data.locked){notice.classList.remove('hidden');notice.innerHTML='<b>Atama kilitli.</b><span>Puanlama başladıktan sonra sınav öğrenci listesi değiştirilemez.</span>';}else notice.classList.add('hidden');document.getElementById('saveExamStudentAssignment').disabled=data.locked;document.getElementById('examStudentSearch').value='';renderExamStudentManagerList();document.getElementById('examStudentManagerBackdrop').classList.remove('hidden');document.getElementById('examStudentManager').classList.remove('hidden');}catch(e){toast(e.message,'error');}};
document.getElementById('closeExamStudentManager')?.addEventListener('click',closeExamStudentManager);
document.getElementById('cancelExamStudentManager')?.addEventListener('click',closeExamStudentManager);
document.getElementById('examStudentManagerBackdrop')?.addEventListener('click',closeExamStudentManager);
document.getElementById('examStudentSearch')?.addEventListener('input',renderExamStudentManagerList);
document.getElementById('examStudentSelectAll')?.addEventListener('click',()=>{if(state.examStudentAssignmentData?.locked)return;for(const s of (state.examStudentAssignmentData?.students||[]))state.examStudentAssignmentSelection.add(Number(s.id));renderExamStudentManagerList();});
document.getElementById('examStudentClearAll')?.addEventListener('click',()=>{if(state.examStudentAssignmentData?.locked)return;state.examStudentAssignmentSelection.clear();renderExamStudentManagerList();});
document.getElementById('saveExamStudentAssignment')?.addEventListener('click',async()=>{if(!state.currentExam||state.examStudentAssignmentData?.locked)return;const ids=examAssignmentSelectedIds();try{const r=await api('PUT',`/api/exams/${state.currentExam.id}/students`,{student_ids:ids});toast(`Sınav öğrenci listesi kaydedildi: ${r.student_count} öğrenci.`);closeExamStudentManager();await loadExams();await openExam(state.currentExam.id);setExamWizardStep(4);}catch(e){toast(e.message,'error');}});
window.normalizeExamPointsFromReadiness=function(){document.getElementById('normalizeExamPoints')?.click();};

function questionOutcomeCodes(question){
  const many=Array.isArray(question?.learning_outcome_codes)?question.learning_outcome_codes.filter(Boolean):[];
  if(many.length)return [...new Set(many.map(String))];
  return question?.learning_outcome_code?[String(question.learning_outcome_code)]:[];
}
function selectedValues(selectEl){return selectEl?[...selectEl.options].filter(o=>o.selected).map(o=>o.value).filter(Boolean):[];}
function setSelectedValues(selectEl,codes){const wanted=new Set((codes||[]).map(String));if(!selectEl)return;[...selectEl.options].forEach(o=>{o.selected=wanted.has(o.value);});}
function outcomeBadges(question,empty='Öğrenim Çıktısı yok'){
  const codes=questionOutcomeCodes(question);return codes.length?`<span class="multi-outcome-badges">${codes.map(c=>`<span class="badge">${esc(c)}</span>`).join('')}</span>`:`<span class="badge muted-badge">${esc(empty)}</span>`;
}
function mappedProgramsForQuestion(question){
  const seen=new Map();questionOutcomeCodes(question).forEach(code=>examMappedPrograms(code).forEach(pc=>{if(!seen.has(pc.code))seen.set(pc.code,pc);}));return [...seen.values()];
}
function examMappedPrograms(loCode){
  const exam=state.currentExam;if(!exam||!loCode)return[];const lo=(exam.learning_outcomes||[]).find(x=>x.code===loCode);if(!lo)return[];
  return (exam.outcome_mappings||[]).filter(x=>x.learning_outcome_code===loCode||x.exam_learning_outcome_id===lo.id).map(mp=>{const po=(exam.program_outcomes||[]).find(p=>p.id===mp.exam_program_outcome_id||p.code===mp.program_outcome_code);return po?{...po,contribution:mp.contribution}:null;}).filter(Boolean);
}
function renderQuestions(qs){
  const canEdit=state.currentExam?.status==='draft';
  const rows=[...(qs||[])].sort((a,b)=>a.order_no-b.order_no);
  const count=document.getElementById('questionListCount');if(count)count.textContent=`${rows.length} soru`;
  const box=document.getElementById('questionList');
  box.innerHTML=rows.length?rows.map((q,index)=>{const pcs=mappedProgramsForQuestion(q);return `<div class="question-card builder-question-card" data-question-id="${q.id}" draggable="${canEdit?'true':'false'}"><div class="question-card-top"><div class="q-order-stack"><span class="drag-handle" title="Sürükleyerek sırala">⋮⋮</span><span class="q-number">${q.order_no}</span>${canEdit?`<div class="q-order-buttons"><button class="ghost" type="button" data-action-call="moveExamQuestion(${q.id},-1)" ${index===0?'disabled':''}>↑</button><button class="ghost" type="button" data-action-call="moveExamQuestion(${q.id},1)" ${index===rows.length-1?'disabled':''}>↓</button></div>`:''}</div><div class="q-main"><div class="q-meta"><b>${q.question_type==='mcq'?'Çoktan seçmeli':'Klasik'}</b><span class="points-chip">${Number(q.points).toLocaleString('tr-TR')} puan</span>${outcomeBadges(q)}${q.bank_question_id?'<span class="badge bank-source">Havuz</span>':'<span class="badge manual-source">Manuel</span>'}</div><div class="question-text">${esc(q.text)}</div>${pcs.length?`<div class="pc-mini">${pcs.map(x=>`<span>${esc(x.code)} <b>${x.contribution}</b></span>`).join('')}</div>`:''}${q.question_type==='mcq'?renderChoices(q.choices):`<div class="muted">Cevap alanı: ${q.answer_lines||8} satır</div>`}${q.correct_answer?`<div class="correct-answer">Doğru: <b>${esc(q.correct_answer)}</b>${q.choices?.[q.correct_answer]?` · ${esc(q.choices[q.correct_answer])}`:''}</div>`:''}</div>${canEdit?`<div class="question-card-actions"><button class="ghost small" type="button" data-action-call="editQuestion(${q.id})">Düzenle</button><button class="danger small" type="button" data-action-call="removeQuestion(${q.id})">Sil</button></div>`:''}</div></div>`}).join(''):'<div class="empty-state builder-empty"><b>Henüz soru eklenmedi.</b><span>Soldaki ders havuzundan birden fazla soru seçin veya aşağıdaki manuel soru alanını kullanın.</span></div>';
  if(canEdit){
    box.querySelectorAll('.builder-question-card').forEach(card=>{
      card.addEventListener('dragstart',ev=>{state.dragQuestionId=Number(card.dataset.questionId);card.classList.add('is-dragging');ev.dataTransfer.effectAllowed='move';ev.dataTransfer.setData('text/plain',String(state.dragQuestionId));});
      card.addEventListener('dragend',()=>{state.dragQuestionId=null;box.querySelectorAll('.builder-question-card').forEach(x=>x.classList.remove('is-dragging','drag-over'));});
      card.addEventListener('dragover',ev=>{ev.preventDefault();card.classList.add('drag-over');ev.dataTransfer.dropEffect='move';});
      card.addEventListener('dragleave',()=>card.classList.remove('drag-over'));
      card.addEventListener('drop',async ev=>{ev.preventDefault();card.classList.remove('drag-over');const dragged=state.dragQuestionId||Number(ev.dataTransfer.getData('text/plain'));const target=Number(card.dataset.questionId);if(!dragged||dragged===target)return;const ids=rows.map(x=>x.id).filter(id=>id!==dragged);const targetIndex=ids.indexOf(target);const rect=card.getBoundingClientRect();const after=ev.clientY>rect.top+rect.height/2;ids.splice(targetIndex+(after?1:0),0,dragged);await reorderExamQuestions(ids);});
    });
  }
  renderExamOutcomeCoverage(state.currentExam);
}
function renderQuestionComposerStats(exam){
  const total=(exam.questions||[]).reduce((a,q)=>a+Number(q.points||0),0);const mapped=(exam.questions||[]).filter(q=>questionOutcomeCodes(q).length).length;const diff=100-total;
  document.getElementById('questionComposerStats').innerHTML=`<div><b>${exam.questions.length}</b><span>Soru</span></div><div class="${Math.abs(total-100)<.01?'ok':total>100?'bad':'neutral'}"><b>${Number(total.toFixed(2)).toLocaleString('tr-TR')}</b><span>Toplam puan</span></div><div class="${diff<0?'bad':'neutral'}"><b>${Math.abs(Number(diff.toFixed(2))).toLocaleString('tr-TR')}</b><span>${diff<0?'Fazla puan':'Kalan puan'}</span></div><div class="${mapped===exam.questions.length&&exam.questions.length?'ok':'neutral'}"><b>${mapped}/${exam.questions.length}</b><span>Öğrenim Çıktısı eşleşmesi</span></div>`;
}
function renderExamOutcomeCoverage(exam){
  if(!exam)return;
  const questions=exam.questions||[];const total=questions.reduce((a,q)=>a+Number(q.points||0),0);
  const items=(exam.learning_outcomes||[]).map(lo=>{const qs=questions.filter(q=>questionOutcomeCodes(q).includes(lo.code));const points=qs.reduce((a,q)=>a+Number(q.points||0),0);const weight=total?points/total*100:0;const pcs=examMappedPrograms(lo.code);return {lo,qs,points,weight,pcs};});
  const unmapped=questions.filter(q=>!questionOutcomeCodes(q).length);const unmappedPoints=unmapped.reduce((a,q)=>a+Number(q.points||0),0);
  const html=items.length?`<div class="coverage-head"><div><b>Öğrenim Çıktısı ölçüm ağırlığı</b><span>Bir soru birden fazla Öğrenim Çıktısı'ye katkı verebilir; yüzdeler bu nedenle örtüşebilir.</span></div>${unmapped.length?`<span class="coverage-warning">${unmapped.length} eşleşmemiş soru</span>`:'<span class="coverage-ok">Tüm sorular eşleşti</span>'}</div><div class="coverage-list">${items.map(x=>`<div class="coverage-row"><div class="coverage-code">${esc(x.lo.code)}</div><div class="coverage-main"><div><b>${esc(x.lo.description)}</b><span>${x.qs.length} soru · ${Number(x.points.toFixed(2)).toLocaleString('tr-TR')} puan · %${x.weight.toFixed(1)} ölçüm ağırlığı</span></div><div class="coverage-bar"><span data-style="width:${Math.min(100,x.weight)}%"></span></div><small>${x.pcs.length?`Program Çıktısı: ${x.pcs.map(p=>esc(p.code)).join(', ')}`:'Program Çıktısı bağlantısı eksik'}</small></div></div>`).join('')}${unmapped.length?`<div class="coverage-row coverage-unmapped"><div class="coverage-code">!</div><div class="coverage-main"><div><b>Öğrenim Çıktısı eşleşmesi olmayan sorular</b><span>${unmapped.length} soru · ${Number(unmappedPoints.toFixed(2)).toLocaleString('tr-TR')} puan</span></div></div></div>`:''}</div>`:`<div class="empty-state compact-empty"><b>Öğrenim Çıktısı planı bulunamadı.</b><span>Önce kazanım snapshot'ını kontrol edin.</span></div>`;
  const main=document.getElementById('examOutcomeCoverage');if(main)main.innerHTML=html;
  const final=document.getElementById('finalOutcomeCoverage');if(final)final.innerHTML=`<span class="eyebrow">KAZANIM DAĞILIMI</span>${html}`;
}
async function reorderExamQuestions(questionIds){
  if(!state.currentExam||state.currentExam.status!=='draft')return;
  try{await api('PUT',`/api/exams/${state.currentExam.id}/questions/reorder`,{question_ids:questionIds});state.currentWizardStep=3;await openExam(state.currentExam.id);toast('Soru sırası güncellendi.');}catch(e){toast(e.message,'error');}
}
window.moveExamQuestion=async function(id,delta){const rows=[...(state.currentExam?.questions||[])].sort((a,b)=>a.order_no-b.order_no);const i=rows.findIndex(x=>x.id===id);const j=i+delta;if(i<0||j<0||j>=rows.length)return;[rows[i],rows[j]]=[rows[j],rows[i]];await reorderExamQuestions(rows.map(x=>x.id));};
function renderOutcomePicker(exam){
  const box=document.getElementById('qOutcomePicker');
  box.innerHTML=(exam.learning_outcomes||[]).map(lo=>`<button type="button" class="outcome-chip" data-code="${esc(lo.code)}"><b>${esc(lo.code)}</b><span>${esc(lo.description)}</span></button>`).join('')||'<span class="muted">Bu sınav snapshot’ında Öğrenim Çıktısı yok.</span>';
  box.querySelectorAll('.outcome-chip').forEach(b=>b.addEventListener('click',()=>{const sel=document.getElementById('qLo');const opt=[...sel.options].find(o=>o.value===b.dataset.code);if(opt)opt.selected=!opt.selected;syncOutcomePicker();}));syncOutcomePicker();
}
function syncOutcomePicker(){
  const codes=selectedValues(document.getElementById('qLo'));const selected=new Set(codes);
  document.querySelectorAll('#qOutcomePicker .outcome-chip').forEach(b=>b.classList.toggle('active',selected.has(b.dataset.code)));
  const los=(state.currentExam?.learning_outcomes||[]).filter(x=>selected.has(x.code));const pcMap=new Map();los.forEach(lo=>examMappedPrograms(lo.code).forEach(pc=>{if(!pcMap.has(pc.code))pcMap.set(pc.code,pc);}));const pcs=[...pcMap.values()];
  document.getElementById('qOutcomeContext').innerHTML=los.length?`<div class="selected-outcome-summary"><b>${los.map(x=>esc(x.code)).join(', ')}</b><span>${los.length} Öğrenim Çıktısı seçili</span></div><div class="pc-link-row">${pcs.length?pcs.map(x=>`<span>${esc(x.code)} · katkı ${x.contribution}/5</span>`).join(''):'<span class="warning-chip">Seçili Öğrenim Çıktısı’ler için Program Çıktısı bağlantısı bulunamadı.</span>'}</div>`:'Bir veya birden fazla Öğrenim Çıktısı seçin; bağlı Program Çıktısı’ler burada görünür.';
}
function renderExamOutcomePlan(exam){const box=document.getElementById('examOutcomePlan');box.innerHTML=(exam.learning_outcomes||[]).map(lo=>{const pcs=examMappedPrograms(lo.code);const used=(exam.questions||[]).filter(q=>questionOutcomeCodes(q).includes(lo.code));return `<div class="outcome-plan-card ${pcs.length?'':'needs-map'}"><div class="outcome-plan-code">${esc(lo.code)}</div><div><b>${esc(lo.description)}</b><span>Hedef %${lo.target_percent} · ${used.length} soru</span><div class="pc-link-row">${pcs.length?pcs.map(x=>`<span>${esc(x.code)} · ${x.contribution}/5</span>`).join(''):'<span class="warning-chip">Program Çıktısı bağlantısı eksik</span>'}</div></div></div>`}).join('')||'<div class="empty-state"><b>Öğrenim Çıktısı bulunamadı.</b><span>Öğrenim Çıktısı ↔ Program Çıktısı Haritası ekranından kazanım ekleyin. Yeni sınav oluşturulduğunda snapshot alınır.</span></div>';}

function resetQuestionEditor(){
  if(!state.currentExam)return;
  document.getElementById('qEditId').value='';
  document.getElementById('questionFormTitle').textContent='Soru ekle';
  document.getElementById('saveQuestion').textContent='Soruyu ekle';
  document.getElementById('cancelQuestionEdit').classList.add('hidden');
  const next=state.currentExam.questions.length?Math.max(...state.currentExam.questions.map(q=>q.order_no))+1:1;
  document.getElementById('qOrder').value=next;
  document.getElementById('qType').value='mcq';document.getElementById('qPoints').value=10;document.getElementById('qAnswerLines').value=8;document.getElementById('qTopic').value='';document.getElementById('qUnit').value='';document.getElementById('qDifficulty').value='medium';document.getElementById('qBloom').value='';document.getElementById('qRubric').value='';document.getElementById('qImage').value='';setQuestionImagePreview('qImagePreview','');setSelectedValues(document.getElementById('qLo'),[]);document.getElementById('qText').value='';document.getElementById('qCorrect').value='A';fillChoices('q',null);syncQuestionTypeUI();syncOutcomePicker();syncCorrectButtons();
}
window.editQuestion=function(id){
  const q=state.currentExam?.questions.find(x=>x.id===id);if(!q)return;
  document.querySelector('.manual-question-panel')?.setAttribute('open','');document.getElementById('qEditId').value=q.id;document.getElementById('questionFormTitle').textContent=`${q.order_no}. soruyu düzenle`;document.getElementById('saveQuestion').textContent='Değişiklikleri kaydet';document.getElementById('cancelQuestionEdit').classList.remove('hidden');document.getElementById('qOrder').value=q.order_no;document.getElementById('qType').value=q.question_type;document.getElementById('qPoints').value=q.points;document.getElementById('qAnswerLines').value=q.answer_lines||8;setSelectedValues(document.getElementById('qLo'),questionOutcomeCodes(q));document.getElementById('qText').value=q.text;document.getElementById('qTopic').value=q.topic||'';document.getElementById('qUnit').value=q.unit||'';document.getElementById('qDifficulty').value=q.difficulty||'medium';document.getElementById('qBloom').value=q.bloom_level||'';document.getElementById('qRubric').value=formatRubric(q.rubric);document.getElementById('qImage').value='';setQuestionImagePreview('qImagePreview',q.image_data||'');document.getElementById('qCorrect').value=q.correct_answer||'A';fillChoices('q',q.choices);syncQuestionTypeUI();syncOutcomePicker();syncCorrectButtons();setExamWizardStep(3);document.getElementById('questionForm').scrollIntoView({behavior:'smooth',block:'center'});
};
document.getElementById('cancelQuestionEdit').addEventListener('click',resetQuestionEditor);
window.removeQuestion=async function(id){if(!confirm('Soruyu silmek istediğinize emin misiniz?'))return;try{await api('DELETE',`/api/exams/${state.currentExam.id}/questions/${id}`);toast('Soru silindi.');await openExam(state.currentExam.id);}catch(e){toast(e.message,'error');}};

function examBankVisibleRows(){
  const q=(document.getElementById('examBankSearch')?.value||'').trim().toLocaleLowerCase('tr-TR');
  const type=document.getElementById('examBankType')?.value||'';
  const outcome=document.getElementById('examBankOutcome')?.value||'';
  return (state.examBankRows||[]).filter(x=>{
    if(type&&x.question_type!==type)return false;
    if(outcome&&!questionOutcomeCodes(x).includes(outcome))return false;
    if(q){const hay=[x.text,...questionOutcomeCodes(x),(x.tags||[]).join(' ')].filter(Boolean).join(' ').toLocaleLowerCase('tr-TR');if(!hay.includes(q))return false;}
    return true;
  });
}
function updateExamBankSelection(){
  const existing=new Set((state.currentExam?.questions||[]).map(x=>x.bank_question_id).filter(Boolean));
  [...state.examBankSelected].forEach(id=>{if(existing.has(id)||!(state.examBankRows||[]).some(x=>x.id===id))state.examBankSelected.delete(id);});
  const badge=document.getElementById('examBankSelectedCount');if(badge)badge.textContent=`${state.examBankSelected.size} seçili`;
  document.querySelectorAll('#examBankGrid input[data-bank-id]').forEach(cb=>{const id=Number(cb.dataset.bankId);cb.checked=state.examBankSelected.has(id);});
}
function renderExamBankGrid(){
  const box=document.getElementById('examBankGrid');if(!box)return;
  const rows=examBankVisibleRows();const existing=new Set((state.currentExam?.questions||[]).map(x=>x.bank_question_id).filter(Boolean));const locked=state.currentExam?.status!=='draft';
  if(!rows.length){box.innerHTML='<div class="empty-state compact-empty"><b>Filtreye uygun havuz sorusu yok.</b><span>Soru Havuzu ekranından bu derse yeni soru ekleyebilirsiniz.</span></div>';updateExamBankSelection();return;}
  box.innerHTML=rows.map(x=>{const used=existing.has(x.id);const selected=state.examBankSelected.has(x.id);const tags=(x.tags||[]).slice(0,4).map(t=>`<span>${esc(t)}</span>`).join('');return `<label class="exam-bank-card ${used?'is-used':''} ${selected?'is-selected':''}"><input type="checkbox" data-bank-id="${x.id}" ${selected?'checked':''} ${used||locked?'disabled':''}><div class="exam-bank-card-main"><div class="exam-bank-card-meta"><span class="badge ${x.question_type==='mcq'?'status-approved':'status-ready'}">${x.question_type==='mcq'?'Test':'Klasik'}</span>${outcomeBadges(x)}<b>${Number(x.default_points).toLocaleString('tr-TR')} p</b>${used?'<em>Sınavda</em>':''}</div><p>${esc(x.text)}</p>${tags?`<div class="exam-bank-tags">${tags}</div>`:''}</div></label>`;}).join('');
  box.querySelectorAll('input[data-bank-id]').forEach(cb=>cb.addEventListener('change',()=>{const id=Number(cb.dataset.bankId);if(cb.checked)state.examBankSelected.add(id);else state.examBankSelected.delete(id);renderExamBankGrid();updateExamBankSelection();}));
  updateExamBankSelection();
}
async function loadExamBank(exam){
  state.examBankSelected=new Set();
  const locked=exam.status!=='draft';['examBankSelectAll','examBankClear','addSelectedBankToExam','normalizeExamPoints'].forEach(id=>{const el=document.getElementById(id);if(el)el.disabled=locked;});
  const outcomeSel=document.getElementById('examBankOutcome');if(outcomeSel)outcomeSel.innerHTML='<option value="">Tüm Öğrenim Çıktısı\'ler</option>'+(exam.learning_outcomes||[]).map(x=>`<option value="${esc(x.code)}">${esc(x.code)} · ${esc(x.description)}</option>`).join('');
  try{state.examBankRows=(await api('GET',`/api/question-bank?course_id=${exam.course_id}`)).filter(x=>['approved','institutional'].includes(x.review_status||'institutional'));}catch(e){state.examBankRows=[];toast(e.message,'error');}
  renderExamBankGrid();
}
document.getElementById('examBankSearch').addEventListener('input',renderExamBankGrid);
document.getElementById('examBankType').addEventListener('change',renderExamBankGrid);
document.getElementById('examBankOutcome').addEventListener('change',renderExamBankGrid);
document.getElementById('examBankSelectAll').addEventListener('click',()=>{const existing=new Set((state.currentExam?.questions||[]).map(x=>x.bank_question_id).filter(Boolean));examBankVisibleRows().forEach(x=>{if(!existing.has(x.id))state.examBankSelected.add(x.id);});renderExamBankGrid();});
document.getElementById('examBankClear').addEventListener('click',()=>{state.examBankSelected.clear();renderExamBankGrid();});
document.getElementById('addSelectedBankToExam').addEventListener('click',async()=>{if(!state.currentExam)return;const ids=[...state.examBankSelected];if(!ids.length){toast('Önce havuzdan en az bir soru seçin.','error');return;}try{const r=await api('POST',`/api/exams/${state.currentExam.id}/questions/from-bank/batch`,{bank_question_ids:ids,skip_existing:true});state.examBankSelected.clear();state.currentWizardStep=3;toast(`${r.added} soru sınava eklendi${r.skipped?.length?` · ${r.skipped.length} zaten sınavdaydı`:''}.`);await openExam(state.currentExam.id);}catch(e){toast(e.message,'error');}});
document.getElementById('normalizeExamPoints').addEventListener('click',async()=>{if(!state.currentExam||!state.currentExam.questions.length){toast('Önce sınava soru ekleyin.','error');return;}if(!confirm('Mevcut soru puanları oranları korunarak toplam 100 puana ölçeklensin mi?'))return;try{const r=await api('POST',`/api/exams/${state.currentExam.id}/questions/normalize-points`,{precision:2});state.currentWizardStep=3;toast(`${r.old_total} puan → 100 puan olarak ölçeklendi.`);await openExam(state.currentExam.id);}catch(e){toast(e.message,'error');}});

function setExamWizardStep(step){state.currentWizardStep=Number(step)||1;document.querySelectorAll('#examWizardNav button').forEach(b=>b.classList.toggle('active',Number(b.dataset.step)===state.currentWizardStep));document.querySelectorAll('[data-wizard-panel]').forEach(p=>p.classList.toggle('hidden',Number(p.dataset.wizardPanel)!==state.currentWizardStep));if(state.currentExam&&state.currentWizardStep===3){renderQuestionComposerStats(state.currentExam);renderExamOutcomeCoverage(state.currentExam);renderExamBankGrid();syncOutcomePicker();}if(state.currentExam&&state.currentWizardStep===4){loadExamReadiness(state.currentExam.id);renderExamOutcomeCoverage(state.currentExam);renderPaperPreview();}}
document.querySelectorAll('#examWizardNav button').forEach(b=>b.addEventListener('click',()=>setExamWizardStep(b.dataset.step)));
document.querySelectorAll('[data-go-step]').forEach(b=>b.addEventListener('click',()=>setExamWizardStep(b.dataset.goStep)));
document.getElementById('goOutcomeMap').addEventListener('click',()=>{if(state.currentExam){showPage('outcomes');document.getElementById('outcomeCourse').value=String(state.currentExam.course_id);loadOutcomeMap();}});
document.getElementById('outcomeBackToExam').addEventListener('click',async()=>{if(!state.currentExam)return;const id=state.currentExam.id;showPage('exams');await loadExams();await openExam(id);setExamWizardStep(2);});
document.getElementById('refreshExamOutcomes').addEventListener('click',async()=>{if(!state.currentExam)return;try{const x=await api('POST',`/api/exams/${state.currentExam.id}/refresh-outcome-snapshot`,{});toast('Sınav kazanım snapshot’ı canlı Öğrenim ve Program Çıktıları haritasından yenilendi.');state.currentWizardStep=2;await openExam(x.id);}catch(e){toast(e.message,'error');}});
document.getElementById('examDraftForm').addEventListener('submit',async ev=>{ev.preventDefault();if(!state.currentExam)return;const weightRaw=document.getElementById('draftWeight').value;try{const x=await api('PATCH',`/api/exams/${state.currentExam.id}`,{title:document.getElementById('draftTitle').value.trim(),exam_type:document.getElementById('draftType').value.trim(),exam_date:document.getElementById('draftDate').value||null,start_time:document.getElementById('draftStartTime').value||null,location:document.getElementById('draftLocation').value.trim(),duration_minutes:Number(document.getElementById('draftDuration').value),assessment_weight_percent:weightRaw===''?null:Number(weightRaw),booklet_count:Number(document.getElementById('draftBookletCount').value||4),paper_size:document.getElementById('draftPaperSize').value,paper_orientation:document.getElementById('draftPaperOrientation').value,omr_mode:document.getElementById('draftOmrMode').value,duplex_print:document.getElementById('draftDuplex').checked,instructions:document.getElementById('draftInstructions').value,staff_notes:document.getElementById('draftStaffNotes').value});toast('Sınav planı ve uygulama detayları kaydedildi.');await loadExams();await openExam(x.id);setExamWizardStep(2);}catch(e){toast(e.message,'error');}});
document.getElementById('readyFromWizard').addEventListener('click',()=>changeCurrentExamStatus('ready'));
function syncCorrectButtons(){const v=document.getElementById('qCorrect').value;document.querySelectorAll('#qCorrectButtons button').forEach(b=>b.classList.toggle('active',b.dataset.answer===v));}
document.querySelectorAll('#qCorrectButtons button').forEach(b=>b.addEventListener('click',()=>{document.getElementById('qCorrect').value=b.dataset.answer;syncCorrectButtons();}));
document.getElementById('qLo').addEventListener('change',syncOutcomePicker);
document.getElementById('qType').addEventListener('change',syncQuestionTypeUI);
document.getElementById('qImage')?.addEventListener('change',async e=>{try{setQuestionImagePreview('qImagePreview',await fileToDataUrl(e.target.files[0]));}catch(err){toast(err.message,'error');e.target.value='';}});
document.getElementById('questionForm').addEventListener('submit',async ev=>{
  ev.preventDefault(); if(!state.currentExam){toast('Önce sınav seçin.','error');return;}
  const type=document.getElementById('qType').value;const editId=Number(document.getElementById('qEditId').value||0);
  try{
    const file=document.getElementById('qImage').files[0];const imageData=file?await fileToDataUrl(file):(document.getElementById('qImagePreview').dataset.imageData||null);
    const rubric=type==='classic'?parseRubricText(document.getElementById('qRubric').value):{};
    const body={order_no:Number(document.getElementById('qOrder').value),question_type:type,text:document.getElementById('qText').value.trim(),points:Number(document.getElementById('qPoints').value),correct_answer:type==='mcq'?document.getElementById('qCorrect').value:null,learning_outcome_codes:selectedValues(document.getElementById('qLo')),choices:type==='mcq'?choiceObject('q'):null,answer_lines:Number(document.getElementById('qAnswerLines').value||8),topic:document.getElementById('qTopic').value.trim(),unit:document.getElementById('qUnit').value.trim(),difficulty:document.getElementById('qDifficulty').value,bloom_level:document.getElementById('qBloom').value||'understand',image_data:imageData,rubric};
    if(editId){await api('PATCH',`/api/exams/${state.currentExam.id}/questions/${editId}`,body);toast('Soru güncellendi.');}else{await api('POST',`/api/exams/${state.currentExam.id}/questions`,body);toast('Soru kaydedildi. Sıradaki soruya geçebilirsiniz.');}state.currentWizardStep=3;await openExam(state.currentExam.id);
  }catch(e){toast(e.message,'error');}
});

async function renderPaperPreview(){
  const box=document.getElementById('paperHtmlPreview');if(!box||!state.currentExam)return;
  const exam=state.currentExam;const booklet=document.getElementById('paperBooklet').value||'A';
  if(!(exam.questions||[]).length){box.innerHTML='<div class="empty-state compact-empty"><b>Önizleme için soru gerekli.</b><span>Önce sınava soru ekleyin.</span></div>';return;}
  try{
    const meta=await api('GET',`/api/exams/${exam.id}/paper-metadata?booklet=${encodeURIComponent(booklet)}`);const byId=new Map((exam.questions||[]).map(q=>[q.id,q]));const ordered=(meta.question_order||[]).map(x=>({...x,...byId.get(x.question_id)}));const snap=exam.paper_snapshot||{};
    box.innerHTML=`<div class="paper-sheet"><div class="paper-sheet-brand"><img src="/dou-logo.png" alt="DOU"><div><b>DOĞUŞ ÜNİVERSİTESİ</b><span>${esc(snap.program_name||snap.department||'Akademik Birim')}</span></div><em>Kitapçık ${esc(booklet)}</em></div><div class="paper-sheet-title"><span>${esc(snap.course_code||'')} · ${esc(snap.course_name||'')}</span><b>${esc(exam.title)}</b><small>${esc(exam.exam_type)} · ${exam.duration_minutes} dk · ${exam.exam_date||'Tarih bekleniyor'}${exam.start_time?` · ${esc(exam.start_time)}`:''}${exam.location?` · ${esc(exam.location)}`:''}</small></div><div class="paper-sheet-student"><span>Ad Soyad</span><span>Öğrenci No</span><span>İmza</span></div><div class="paper-preview-questions">${ordered.map((q,i)=>`<div class="paper-preview-q"><div><b>${i+1}.</b><span>${esc(q.text)}</span></div><em>${Number(q.points).toLocaleString('tr-TR')} p</em>${q.question_type==='mcq'&&q.choices?`<div class="paper-preview-options">${Object.entries(q.choices).map(([k,v])=>`<span><b>${esc(k)})</b> ${esc(v)}</span>`).join('')}</div>`:`<div class="paper-preview-lines">${'— '.repeat(Math.min(5,q.answer_lines||5))}</div>`}</div>`).join('')}</div><div class="paper-sheet-foot">DOU Assess · ${esc(meta.template_version||'dou-official-v1')} · QR/OMR hazır</div></div>`;
  }catch(e){box.innerHTML=`<div class="empty-state compact-empty"><b>Önizleme hazırlanamadı.</b><span>${esc(e.message)}</span></div>`;}
}
async function openSelectedPaper(){if(!state.currentExam)return;try{await loadExamReadiness(state.currentExam.id);const booklet=document.getElementById('paperBooklet').value;await downloadApi(`/api/exams/${state.currentExam.id}/paper.pdf?booklet=${encodeURIComponent(booklet)}`,`sinav-${state.currentExam.id}-kitapcik-${booklet}.pdf`,true);}catch(e){toast(e.message,'error');}}
document.getElementById('openPaper').addEventListener('click',openSelectedPaper);
document.getElementById('showAnswerKey').addEventListener('click',async()=>{if(!state.currentExam)return;try{const booklet=document.getElementById('paperBooklet').value;const meta=await api('GET',`/api/exams/${state.currentExam.id}/paper-metadata?booklet=${encodeURIComponent(booklet)}`);const lines=Object.entries(meta.answer_key||{}).map(([n,a])=>`${n}. ${a}`);const box=document.getElementById('answerKeyBox');box.textContent=`Kitapçık ${meta.booklet}\nToken: ${meta.token}\n\n${lines.join('\n')||'Çoktan seçmeli soru yok.'}`;box.classList.remove('hidden');}catch(e){toast(e.message,'error');}});
document.getElementById('downloadStudentPapers').addEventListener('click',async()=>{if(!state.currentExam)return;try{const allowed=['A','B','C','D'].slice(0,state.currentExam.booklet_count||4).join('');await downloadApi(`/api/exams/${state.currentExam.id}/papers-batch.pdf?booklet_strategy=rotate`,`sinav-${state.currentExam.id}-ogrenci-kagitlari-${allowed}.pdf`);toast(`Öğrenciye özel ${allowed.split('').join('/')} kitapçıkları hazırlandı.`);}catch(e){toast(e.message,'error');}});
document.querySelectorAll('[data-paper-booklet]').forEach(btn=>btn.addEventListener('click',async()=>{document.getElementById('paperBooklet').value=btn.dataset.paperBooklet;document.getElementById('answerKeyBox').classList.add('hidden');await renderPaperPreview();await openSelectedPaper();}));
document.getElementById('paperBooklet').addEventListener('change',async()=>{document.getElementById('answerKeyBox').classList.add('hidden');await renderPaperPreview();});


async function changeCurrentExamStatus(status){if(!state.currentExam||!status)return;if(status==='request_approval')return requestExamApproval();try{const x=await api('POST',`/api/exams/${state.currentExam.id}/status`,{status});toast(`Sınav durumu: ${x.status}`);await loadExams();await openExam(x.id);if(status==='ready')setExamWizardStep(4);}catch(e){toast(e.message,'error');}}
document.getElementById('statusNext').addEventListener('click',e=>changeCurrentExamStatus(e.currentTarget.dataset.status));
document.getElementById('statusBack').addEventListener('click',e=>changeCurrentExamStatus(e.currentTarget.dataset.status));
document.getElementById('deleteExam').addEventListener('click',async()=>{if(!state.currentExam||!confirm('Bu taslak sınavı silmek istediğinize emin misiniz?'))return;try{await api('DELETE',`/api/exams/${state.currentExam.id}`);toast('Taslak sınav silindi.');state.currentExam=null;document.getElementById('examEditor').classList.add('hidden');await loadExams();}catch(e){toast(e.message,'error');}});

async function prepareBank(){
  try{
    await refreshCore();
    await updateBankCourseContext();
    await loadBank();
  }catch(e){toast(e.message,'error');}
}
function bankCourseMeta(courseId){
  const course=state.courses.find(c=>Number(c.id)===Number(courseId));
  const program=course?state.programs.find(p=>Number(p.id)===Number(course.program_id)):null;
  return {course,program};
}
function renderBankStats(rows){
  const courseCount=new Set(rows.map(x=>x.source_course_code||x.course_id)).size;
  const mcq=rows.filter(x=>x.question_type==='mcq').length;
  const classic=rows.filter(x=>x.question_type==='classic').length;
  const mapped=rows.filter(x=>questionOutcomeCodes(x).length).length;
  const historical=rows.filter(x=>x.is_historical).length;
  const stats=document.getElementById('bankStats');
  if(stats)stats.innerHTML=[['Toplam soru',rows.length,'Kurumsal aktif soru'],['Ders',courseCount,'Ders kodu / kurumsal soy'],['Geçmiş',historical,'Önceki dönemden erişilebilir'],['Test',mcq,'Çoktan seçmeli'],['Klasik',classic,'Açık uçlu'],['Öğrenim Çıktısı bağlı',mapped,`${rows.length?Math.round(mapped/rows.length*100):0}% eşleşme`]].map(x=>`<div class="bank-stat"><b>${x[1]}</b><span>${x[0]}</span><small>${x[2]}</small></div>`).join('');
}
function renderBankScope(rows){
  const scope=document.getElementById('bankActiveScope');if(!scope)return;
  const courseId=Number(document.getElementById('bankFilterCourse')?.value||0);
  const programId=Number(document.getElementById('bankFilterProgram')?.value||0);
  const type=document.getElementById('bankFilterType')?.value||'',review=document.getElementById('bankFilterReview')?.value||'';
  const outcome=document.getElementById('bankFilterOutcome')?.value.trim()||'';
  const chips=[];
  if(programId){const p=state.programs.find(x=>x.id===programId);if(p)chips.push(`Program: ${p.code}`);}
  if(courseId){const c=state.courses.find(x=>x.id===courseId);if(c)chips.push(`Ders: ${c.code}`);}
  if(type)chips.push(type==='mcq'?'Çoktan seçmeli':'Klasik');
  if(outcome)chips.push(`Öğrenim Çıktısı: ${outcome}`);
  scope.innerHTML=`<span class="scope-title">${state.bankOffset+1}-${state.bankOffset+rows.length} arası</span>${chips.map(x=>`<span class="scope-chip">${esc(x)}</span>`).join('')}${!chips.length?'<span class="scope-chip scope-all">Tüm yetkili akademik kapsam</span>':''}`;
}
function renderBankRows(rows){
  const box=document.getElementById('bankList');
  const editable=!isQualityOnly();
  document.getElementById('bankResultCount').textContent=`${rows.length} soru · sayfa ${Math.floor(state.bankOffset/state.bankLimit)+1}`;
  renderBankStats(rows);renderBankScope(rows);
  if(!rows.length){box.innerHTML='<div class="empty-state bank-empty"><b>Bu filtrelerde soru bulunamadı.</b><span>Filtreleri temizleyin veya yetkili olduğunuz bir derse yeni soru ekleyin.</span></div>';return;}
  const grouped=new Map();
  rows.forEach(x=>{const key=String(x.course_id);if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(x);});
  box.innerHTML=[...grouped.entries()].map(([courseId,items])=>{
    const {course,program}=bankCourseMeta(Number(courseId));
    const title=course?`${course.code} · ${course.name}`:`Ders #${courseId}`;
    const sub=[program?.name,program?.department,course?.instructor_name||course?.instructor_email].filter(Boolean).join(' · ');
    return `<section class="bank-course-group"><div class="bank-course-head"><div><span class="course-code-pill">${esc(course?.code||'DERS')}</span><div><b>${esc(title)}</b><small>${esc(sub||'Akademik ders')}</small></div></div><span>${items.length} soru</span></div><div class="bank-question-grid">${items.map((x,index)=>{
      const tags=(x.tags||[]).map(t=>`<span class="bank-tag">${esc(t)}</span>`).join('');const meta=[x.topic,x.unit,x.difficulty,x.bloom_level,`v${x.version_no||1}`,`${x.usage_count||0} kullanım`].filter(Boolean).map(v=>`<span class="bank-tag muted-tag">${esc(v)}</span>`).join('');
      const source=[x.source_academic_year,x.source_term,x.author?`Yazar: ${x.author}`:'',`v${x.version_no||1}`,`${x.usage_count||0} kullanım`].filter(Boolean).join(' · ');
      const rs={draft:'Taslak',review:'Kontrol bekliyor',revision:'Revizyon',approved:'Onaylı',institutional:'Kurumsal',retired:'Kaldırıldı'}[x.review_status]||'Taslak';
      const psych=`<div class="bank-quality-grid"><span>Güçlük <b>${x.difficulty_index==null?'—':Number(x.difficulty_index).toFixed(2)}</b></span><span>Ayırt <b>${x.discrimination_index==null?'—':Number(x.discrimination_index).toFixed(2)}</b></span><span>Çeldirici <b>${x.distractor_efficiency==null?'—':Number(x.distractor_efficiency).toFixed(0)+'%'}</b></span><span>Örneklem <b>${x.psychometric_sample_size||0}</b></span></div>`;
      const reviewActions=editable&&!x.is_historical?`<div class="bank-review-actions">${x.review_status==='draft'||x.review_status==='revision'?`<button class="ghost small" data-action-call="reviewBankQuestion(${x.id},'review')">Kontrole gönder</button>`:''}${x.review_status==='review'?`<button class="ghost small" data-action-call="reviewBankQuestion(${x.id},'revision')">Revizyon</button><button class="primary small" data-action-call="reviewBankQuestion(${x.id},'approved')">Onayla</button>`:''}${x.review_status==='approved'?`<button class="ghost small" data-action-call="reviewBankQuestion(${x.id},'institutional')">Kurumsal yap</button>`:''}</div>`:'';
      return `<article class="bank-question-card"><div class="bank-q-top"><span class="bank-q-index">${String(index+1).padStart(2,'0')}</span><div class="bank-q-meta"><span class="badge ${x.question_type==='mcq'?'status-approved':'status-ready'}">${x.question_type==='mcq'?'Çoktan seçmeli':'Klasik'}</span>${outcomeBadges(x)}<span>${esc(x.default_points)} puan</span><span class="bank-history-chip ${x.is_historical?'':'current'}">${x.is_historical?'Geçmiş dönem':'Güncel dönem'}</span><span class="bank-review-pill">${esc(rs)}</span></div></div><div class="bank-q-text">${esc(x.text)}</div><div class="bank-source-line">${esc(source||'Kurumsal soru')}</div>${psych}${x.image_data?`<img src="${x.image_data}" alt="Soru görseli" class="question-image-preview">`:''}${x.question_type==='mcq'?renderChoices(x.choices):`<div class="bank-classic-note">Yanıt alanı · ${x.answer_lines||8} satır${x.rubric?.criteria?.length?` · ${x.rubric.criteria.length} rubrik ölçütü`:''}</div>`}<div class="bank-q-bottom"><div class="bank-tags">${tags}${meta||(!tags?'<span class="bank-tag muted-tag">Etiket yok</span>':'')}</div>${editable&&!x.is_historical?`<div class="bank-actions"><button class="ghost small" data-action-call="editBank(${x.id})">Düzenle</button><button class="danger small" data-action-call="archiveBank(${x.id})">Arşivle</button></div>`:''}${reviewActions}</div></article>`;
    }).join('')}</div></section>`;
  }).join('');
}
async function loadBank(){
  const courseId=Number(document.getElementById('bankFilterCourse')?.value||0);
  const programId=Number(document.getElementById('bankFilterProgram')?.value||0);
  const type=document.getElementById('bankFilterType')?.value||'',review=document.getElementById('bankFilterReview')?.value||'';
  const outcome=document.getElementById('bankFilterOutcome')?.value.trim()||'';
  const query=document.getElementById('bankSearch')?.value.trim()||'';
  const params=new URLSearchParams();
  if(courseId)params.set('course_id',courseId);
  if(programId)params.set('program_id',programId);
  if(type)params.set('question_type',type);if(review)params.set('review_status',review);
  if(outcome)params.set('learning_outcome_code',outcome);
  if(query)params.set('q',query);
  params.set('limit',String(state.bankLimit));params.set('offset',String(state.bankOffset));
  const rows=await api('GET',`/api/question-bank?${params}`);
  state.bankRows=rows;state.bankHasNext=rows.length===state.bankLimit;
  renderBankRows(rows);
  const prev=document.getElementById('bankPagePrev'),next=document.getElementById('bankPageNext'),label=document.getElementById('bankPageLabel');
  if(prev)prev.disabled=state.bankOffset===0;if(next)next.disabled=!state.bankHasNext;if(label)label.textContent=`Sayfa ${Math.floor(state.bankOffset/state.bankLimit)+1}`;
}
function renderBankOutcomePicker(los){
  const box=document.getElementById('bankOutcomePicker');if(!box)return;
  box.innerHTML=(los||[]).map(lo=>`<button type="button" class="outcome-chip" data-code="${esc(lo.code)}"><b>${esc(lo.code)}</b><span>${esc(lo.description)}</span></button>`).join('')||'<span class="muted">Bu derste Öğrenim Çıktısı tanımlı değil.</span>';
  box.querySelectorAll('.outcome-chip').forEach(b=>b.addEventListener('click',()=>{const sel=document.getElementById('bankLoSelect');const opt=[...sel.options].find(o=>o.value===b.dataset.code);if(opt)opt.selected=!opt.selected;syncBankOutcomePicker(los);}));
  syncBankOutcomePicker(los);
}
function syncBankOutcomePicker(los){
  const codes=selectedValues(document.getElementById('bankLoSelect')),selected=new Set(codes);
  document.querySelectorAll('#bankOutcomePicker .outcome-chip').forEach(b=>b.classList.toggle('active',selected.has(b.dataset.code)));
  const chosen=(los||[]).filter(x=>selected.has(x.code));const ctx=document.getElementById('bankOutcomeContext');if(ctx)ctx.innerHTML=chosen.length?`<b>${chosen.map(x=>esc(x.code)).join(', ')}</b> · ${chosen.length} Öğrenim Çıktısı seçili`:'Bir veya birden fazla Öğrenim Çıktısı seçebilirsiniz.';
}
async function updateBankCourseContext(preferredOutcomes=[]){
  const courseId=Number(document.getElementById('bankCourse')?.value||0);
  const box=document.getElementById('bankCourseContext');const loSelect=document.getElementById('bankLoSelect');
  const preferred=Array.isArray(preferredOutcomes)?preferredOutcomes:(preferredOutcomes?[preferredOutcomes]:[]);
  if(!courseId){if(box)box.textContent='Yetkili ders bulunamadı.';if(loSelect)loSelect.innerHTML='';renderBankOutcomePicker([]);return;}
  const {course,program}=bankCourseMeta(courseId);
  if(box)box.innerHTML=`<b>${esc(program?.name||'Program')}</b><span>${esc(program?.department||'')} ${program?.department?'·':''} ${esc(course?.instructor_name||course?.instructor_email||'Öğretim elemanı tanımsız')}</span>`;
  try{
    const data=await api('GET',`/api/courses/${courseId}/outcomes`);const los=data.learning_outcomes||[];
    loSelect.innerHTML=los.map(x=>`<option value="${esc(x.code)}">${esc(x.code)} · ${esc(x.description)}</option>`).join('');setSelectedValues(loSelect,preferred);renderBankOutcomePicker(los);
  }catch(e){loSelect.innerHTML='';const picker=document.getElementById('bankOutcomePicker');if(picker)picker.innerHTML='<span class="muted">Öğrenim Çıktısı yüklenemedi.</span>';}
}
function setBankEditorOpen(open){
  const card=document.getElementById('bankEditorCard'),backdrop=document.getElementById('bankEditorBackdrop');
  document.body.classList.toggle('bank-editor-open',!!open);
  card?.classList.toggle('is-open',!!open);
  card?.setAttribute('aria-hidden',open?'false':'true');
  backdrop?.classList.toggle('is-open',!!open);
  if(open)setTimeout(()=>card?.querySelector('select,input,textarea,button')?.focus(),40);
}
function closeBankEditor(){setBankEditorOpen(false);}
function resetBankEditor(){
  state.bankEditId=null;
  document.getElementById('bankEditorTitle').textContent='Yeni soru';
  document.getElementById('saveBank').textContent='Soru havuzuna kaydet';
  document.getElementById('cancelBankEdit').classList.add('hidden');
  document.getElementById('bankType').value='mcq';document.getElementById('bankPoints').value=10;document.getElementById('bankAnswerLines').value=8;document.getElementById('bankTopic').value='';document.getElementById('bankUnit').value='';document.getElementById('bankDifficulty').value='medium';document.getElementById('bankBloom').value='';document.getElementById('bankReviewer').value='';document.getElementById('bankRubric').value='';document.getElementById('bankImage').value='';setQuestionImagePreview('bankImagePreview','');
  if(document.getElementById('bankLoSelect'))setSelectedValues(document.getElementById('bankLoSelect'),[]);syncBankOutcomePicker([]);
  document.getElementById('bankText').value='';document.getElementById('bankCorrect').value='A';document.getElementById('bankTags').value='';fillChoices('bank',null);syncBankTypeUI();
}
document.getElementById('bankTemplateDownload')?.addEventListener('click',async()=>{try{await downloadApi('/api/import/question-bank/template','DOU-Assess-Soru-Havuzu-Sablonu.xlsx');toast('Soru havuzu Excel şablonu indirildi.');}catch(e){toast(e.message,'error');}});
document.getElementById('bankFocusImport')?.addEventListener('click',()=>{const card=document.getElementById('bankImportCard');card?.classList.remove('hidden');card?.scrollIntoView({behavior:'smooth',block:'start'});});
document.getElementById('bankImportClose')?.addEventListener('click',()=>document.getElementById('bankImportCard')?.classList.add('hidden'));
async function runQuestionBankWorkbook(validateOnly=false){
  const file=document.getElementById('bankWorkbookFile')?.files?.[0];const out=document.getElementById('bankWorkbookResult');
  if(!file){toast('Önce soru havuzu Excel dosyasını seçin.','error');return;}
  const fd=new FormData();fd.append('file',file);if(out)out.textContent=validateOnly?'Soru havuzu Excel doğrulanıyor…':'Sorular havuza aktarılıyor…';
  try{
    const r=await api('POST',validateOnly?'/api/import/question-bank/validate':'/api/import/question-bank',fd);
    if(out)out.textContent=JSON.stringify(r,null,2);
    if(validateOnly)toast(`${r.ready??r.rows??0} soru içe aktarmaya hazır${r.duplicates?` · ${r.duplicates} tekrar`:''}.`);
    else{toast(`${r.summary?.created||0} soru havuza eklendi${r.summary?.skipped_duplicates?` · ${r.summary.skipped_duplicates} tekrar atlandı`:''}.`);await loadBank();}
  }catch(e){if(out)out.textContent=e.message;toast(e.message,'error');}
}
document.getElementById('bankWorkbookValidate')?.addEventListener('click',()=>runQuestionBankWorkbook(true));
document.getElementById('bankWorkbookImport')?.addEventListener('click',()=>runQuestionBankWorkbook(false));
document.getElementById('bankWorkbookFile')?.addEventListener('change',ev=>{const f=ev.target.files?.[0];const out=document.getElementById('bankWorkbookResult');if(out)out.textContent=f?`${f.name}\n${Math.round(f.size/1024)} KB · Doğrulamaya hazır`:'Henüz dosya seçilmedi.';});

const resetBankPagingAndLoad=()=>{state.bankOffset=0;return loadBank();};
document.getElementById('bankFilterCourse').addEventListener('change',resetBankPagingAndLoad);
document.getElementById('bankFilterProgram')?.addEventListener('change',async e=>{const pid=Number(e.target.value||0);const courseSel=document.getElementById('bankFilterCourse');const opts=state.courses.filter(c=>!pid||c.program_id===pid).map(c=>`<option value="${c.id}">${esc(c.code)} · ${esc(c.name)}</option>`).join('');courseSel.innerHTML='<option value="">Tüm yetkili dersler</option>'+opts;state.bankOffset=0;await loadBank();});
document.getElementById('bankFilterType')?.addEventListener('change',resetBankPagingAndLoad);
document.getElementById('bankFilterOutcome')?.addEventListener('change',resetBankPagingAndLoad);
document.getElementById('bankFilterReview')?.addEventListener('change',resetBankPagingAndLoad);
document.getElementById('bankSearchBtn').addEventListener('click',resetBankPagingAndLoad);
document.getElementById('bankSearch')?.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();resetBankPagingAndLoad();}});
document.getElementById('bankClearFilters')?.addEventListener('click',async()=>{document.getElementById('bankFilterProgram').value='';fillSelects();document.getElementById('bankFilterCourse').value='';document.getElementById('bankFilterReview').value='';document.getElementById('bankFilterType').value='';document.getElementById('bankFilterOutcome').value='';document.getElementById('bankSearch').value='';state.bankOffset=0;await loadBank();});
document.getElementById('bankPagePrev')?.addEventListener('click',()=>{state.bankOffset=Math.max(0,state.bankOffset-state.bankLimit);loadBank().catch(e=>toast(e.message,'error'));});
document.getElementById('bankPageNext')?.addEventListener('click',()=>{if(!state.bankHasNext)return;state.bankOffset+=state.bankLimit;loadBank().catch(e=>toast(e.message,'error'));});
async function openNewBankQuestion(){
  // 6.66.1: make the question editor independent from page-load timing.
  // A user may click "Yeni soru oluştur" while prepareBank()/refreshCore() is
  // still resolving. In that case the old handler could open an editor with an
  // empty course selector or depend on the legacy 6.40.1 hotfix.
  try{
    if(!Array.isArray(state.courses)||!state.courses.length) await refreshCore();
  }catch(e){
    console.warn('bank-core-refresh',e);
  }
  try{resetBankEditor();}catch(e){console.warn('bank-editor-reset',e);}
  const course=document.getElementById('bankCourse');
  if(course && (!course.options.length || !Number(course.value||0)) && Array.isArray(state.courses) && state.courses.length){
    fillSelects();
  }
  const preferred=Number(state.selectedCourseId||document.getElementById('bankFilterCourse')?.value||course?.value||0);
  if(course&&preferred&&[...course.options].some(o=>Number(o.value)===preferred))course.value=String(preferred);
  setBankEditorOpen(true);
  try{await updateBankCourseContext();}
  catch(e){console.warn('bank-course-context',e);toast('Soru editörü açıldı; ders çıktıları yüklenirken sorun oluştu.','error');}
}
window.openNewBankQuestion=openNewBankQuestion;
// Delegated binding survives page refresh/re-render and does not rely on the
// legacy question-bank-hotfix-6401.js runtime.
document.addEventListener('click',ev=>{
  const btn=ev.target.closest?.('#bankFocusCreate');
  if(!btn)return;
  ev.preventDefault();
  openNewBankQuestion().catch(e=>{console.error('bank-create-open',e);toast(e.message||'Soru editörü açılamadı.','error');});
});
document.getElementById('bankCourse')?.addEventListener('change',()=>updateBankCourseContext());
document.getElementById('bankLoSelect')?.addEventListener('change',()=>syncBankOutcomePicker([]));
document.getElementById('bankType').addEventListener('change',syncBankTypeUI);document.getElementById('bankImage')?.addEventListener('change',async e=>{try{setQuestionImagePreview('bankImagePreview',await fileToDataUrl(e.target.files[0]));}catch(err){toast(err.message,'error');e.target.value='';}});document.getElementById('cancelBankEdit').addEventListener('click',()=>{resetBankEditor();closeBankEditor();});
document.getElementById('bankEditorClose')?.addEventListener('click',()=>{resetBankEditor();closeBankEditor();});
document.getElementById('bankEditorBackdrop')?.addEventListener('click',()=>{resetBankEditor();closeBankEditor();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.body.classList.contains('bank-editor-open')){resetBankEditor();closeBankEditor();}});
document.getElementById('bankForm').addEventListener('submit',async ev=>{
  ev.preventDefault();const type=document.getElementById('bankType').value;
  try{
    const file=document.getElementById('bankImage').files[0];const imageData=file?await fileToDataUrl(file):(document.getElementById('bankImagePreview').dataset.imageData||null);
    const body={course_id:Number(document.getElementById('bankCourse').value),question_type:type,text:document.getElementById('bankText').value.trim(),default_points:Number(document.getElementById('bankPoints').value),correct_answer:type==='mcq'?document.getElementById('bankCorrect').value:null,learning_outcome_codes:selectedValues(document.getElementById('bankLoSelect')),tags:document.getElementById('bankTags').value.split(',').map(x=>x.trim()).filter(Boolean),choices:type==='mcq'?choiceObject('bank'):null,answer_lines:Number(document.getElementById('bankAnswerLines').value||8),topic:document.getElementById('bankTopic').value.trim(),unit:document.getElementById('bankUnit').value.trim(),difficulty:document.getElementById('bankDifficulty').value,bloom_level:document.getElementById('bankBloom').value||'understand',reviewer:document.getElementById('bankReviewer').value.trim(),image_data:imageData,rubric:type==='classic'?parseRubricText(document.getElementById('bankRubric').value):{}};
    if(!body.course_id)return toast('Soru için ders seçin.','error');
    if(!body.text)return toast('Soru metni zorunludur.','error');
    if(type==='mcq'){const keys=Object.keys(body.choices||{});if(keys.length<2)return toast('Çoktan seçmeli soruda en az iki seçenek doldurun.','error');if(!keys.includes(body.correct_answer))return toast('Doğru cevap, doldurduğunuz seçeneklerden biri olmalıdır.','error');}
    if(type==='classic'&&body.rubric?.criteria?.length){const total=body.rubric.criteria.reduce((a,x)=>a+Number(x.max_points||0),0);if(Math.abs(total-body.default_points)>.01)return toast(`Rubrik toplamı (${total}) soru puanına (${body.default_points}) eşit olmalıdır.`,'error');}
    if(state.bankEditId){await api('PATCH',`/api/question-bank/${state.bankEditId}`,body);toast('Havuz sorusu güncellendi.');}else{await api('POST','/api/question-bank',body);toast('Soru ders havuzuna kaydedildi.');}document.getElementById('bankFilterCourse').value=String(body.course_id);resetBankEditor();closeBankEditor();await loadBank();
  }catch(e){toast(e.message,'error');}
});
window.editBank=async function(id){
  const x=(state.bankRows||[]).find(v=>v.id===id);if(!x)return;state.bankEditId=id;
  document.getElementById('bankEditorTitle').textContent='Soruyu düzenle';document.getElementById('bankCourse').value=String(x.course_id);await updateBankCourseContext(questionOutcomeCodes(x));
  document.getElementById('bankType').value=x.question_type;document.getElementById('bankPoints').value=x.default_points;document.getElementById('bankAnswerLines').value=x.answer_lines||8;document.getElementById('bankTopic').value=x.topic||'';document.getElementById('bankUnit').value=x.unit||'';document.getElementById('bankDifficulty').value=x.difficulty||'medium';document.getElementById('bankBloom').value=x.bloom_level||'';document.getElementById('bankReviewer').value=x.reviewer||'';document.getElementById('bankRubric').value=formatRubric(x.rubric);document.getElementById('bankImage').value='';setQuestionImagePreview('bankImagePreview',x.image_data||'');document.getElementById('bankText').value=x.text;document.getElementById('bankCorrect').value=x.correct_answer||'A';document.getElementById('bankTags').value=(x.tags||[]).join(', ');fillChoices('bank',x.choices);syncBankTypeUI();document.getElementById('saveBank').textContent='Değişiklikleri kaydet';document.getElementById('cancelBankEdit').classList.remove('hidden');setBankEditorOpen(true);
};
window.archiveBank=async function(id){if(!confirm('Soruyu aktif havuzdan arşivlemek istiyor musunuz?'))return;try{await api('DELETE',`/api/question-bank/${id}`);toast('Soru arşivlendi.');await loadBank();}catch(e){toast(e.message,'error');}};

async function preparePrint(){
  try{await refreshCore();}catch(e){toast(e.message,'error');return}
  const sel=document.getElementById('printExam'),prev=sel.value;
  sel.innerHTML=(state.exams||[]).filter(e=>e.status!=='archived').map(e=>`<option value="${e.id}">${esc((e.course_code||e.paper_snapshot?.course_code||'')+' · '+e.title)} (${esc(e.status)})</option>`).join('');
  if(prev)sel.value=prev;await loadPrintSummary();
}
async function loadPrintSummary(){
  const id=Number(document.getElementById('printExam').value),box=document.getElementById('printSummary');
  const set=(dis)=>['printBatch','printAttendance','printOne'].forEach(b=>document.getElementById(b).disabled=dis);
  if(!id){box.innerHTML='<p class="muted">Henüz sınav yok.</p>';set(true);document.getElementById('printConfirm').disabled=true;return}
  try{
    const [s,students]=await Promise.all([api('GET',`/api/exams/${id}/print-summary`),api('GET',`/api/exams/${id}/students`)]);
    const ready=s.student_count>0&&s.pages_per_paper>0;set(!ready);document.getElementById('printConfirm').disabled=!s.can_confirm;
    document.getElementById('printStudent').innerHTML=students.map(x=>`<option value="${x.id}">${esc(x.student_no+' · '+x.full_name)}</option>`).join('');
    box.innerHTML=`<div class="readiness-head"><div><b>${s.printed_at?'Basıldı — sorular kilitli':s.ready?'Basıma hazır':'Basımdan önce eksikleri tamamlayın'}</b><small>${s.printed_at?`${esc(s.printed_by)} · ${esc(s.printed_at.slice(0,16).replace('T',' '))}`:`Durum: ${esc(s.status)}`}</small></div></div><div class="readiness-counts"><span>${s.student_count} öğrenci için kâğıt</span><span>${s.pages_per_paper} sayfa / kâğıt</span><span>${s.total_pages} sayfa toplam</span><span>${s.sheets_total} yaprak${s.duplex?' (çift taraflı)':''}</span><span>Kitapçık: ${esc(Object.entries(s.booklets).map(([k,v])=>`${k}=${v}`).join(' · ')||'—')}</span></div>${s.issues.length?`<div class="readiness-issue-list">${s.issues.map(x=>`<div><i>!</i><span>${esc(x)}</span></div>`).join('')}</div>`:''}${s.status==='draft'?'<div class="readiness-warning-list"><div><i>i</i><span>Sınav hâlâ taslak. Önce "Sınav Hazırla" ekranında hazır durumuna alın.</span></div></div>':''}`;
  }catch(e){box.innerHTML=`<p class="muted">${esc(e.message)}</p>`;set(true)}
}
document.getElementById('printExam')?.addEventListener('change',loadPrintSummary);
document.getElementById('printBatch')?.addEventListener('click',async()=>{const id=document.getElementById('printExam').value;try{await downloadApi(`/api/exams/${id}/papers-batch.pdf`,`sinav-${id}-tum-kagitlar.pdf`,true)}catch(e){toast(e.message,'error')}});
document.getElementById('printAttendance')?.addEventListener('click',async()=>{const id=document.getElementById('printExam').value;try{await downloadApi(`/api/exams/${id}/attendance-sheet.pdf`,`yoklama-${id}.pdf`,true)}catch(e){toast(e.message,'error')}});
document.getElementById('printOne')?.addEventListener('click',async()=>{const id=document.getElementById('printExam').value,st=document.getElementById('printStudent').value;if(!st)return;try{await downloadApi(`/api/exams/${id}/students/${st}/paper.pdf`,`sinav-${id}-ogrenci-${st}.pdf`,true)}catch(e){toast(e.message,'error')}});
document.getElementById('printConfirm')?.addEventListener('click',async()=>{const id=document.getElementById('printExam').value;if(!confirm('Kâğıtlar yazdırıldı olarak işaretlenecek ve sorular kilitlenecek. Değişiklik için sınavın kopyası gerekir. Devam?'))return;try{await api('POST',`/api/exams/${id}/print-confirm`);toast('Basım onaylandı; sorular kilitlendi.');await loadPrintSummary()}catch(e){toast(e.message,'error')}});
document.getElementById('printNext')?.addEventListener('click',()=>showPage('scan'));

async function loadScanAudit(){
  const id=Number(document.getElementById('scanExam')?.value||0),box=document.getElementById('scanAuditBox');if(!box)return;
  if(!id){box.innerHTML='<p class="muted">Sınav seçin.</p>';return}
  try{const a=await api('GET',`/api/exams/${id}/scan-audit`);
    const verdict=a.error_rate_percent==null?'Henüz sonuç yok':(a.meets_target?`Hedefte (%${a.error_rate_percent} ≤ %${a.target_error_percent})`:`Hedef aşıldı (%${a.error_rate_percent} > %${a.target_error_percent}) — okumaları gözden geçirin`);
    box.innerHTML=`<div class="readiness-counts"><span>${a.sampled} örnek</span><span>${a.checked} kontrol edildi</span><span>${a.mismatches} hatalı</span><span><b>${esc(verdict)}</b></span></div>`+a.pending.map(p=>`<div class="record"><b>Sayfa ${p.page_no} · öğrenci ${esc(p.student_no||'?')}</b><small>Okunan: ${esc(Object.entries(p.answers||{}).slice(0,40).map(([k,v])=>k+':'+(v||'-')).join(' '))}</small><div class="row"><button class="ghost small" data-audit-view="${p.scan_item_id}">Görseli aç</button><button class="primary small" data-audit-ok="${p.scan_item_id}">Doğru okunmuş</button><button class="danger small" data-audit-bad="${p.scan_item_id}">Hatalı</button></div></div>`).join('');
    box.querySelectorAll('[data-audit-view]').forEach(b=>b.addEventListener('click',()=>downloadApi(`/api/scan-items/${b.dataset.auditView}/review-preview`,'sayfa.jpg',true).catch(e=>toast(e.message,'error'))));
    const judge=async(iid,ok)=>{try{await api('POST',`/api/scan-items/${iid}/audit-result`,{ok,note:''});await loadScanAudit()}catch(e){toast(e.message,'error')}};
    box.querySelectorAll('[data-audit-ok]').forEach(b=>b.addEventListener('click',()=>judge(b.dataset.auditOk,true)));
    box.querySelectorAll('[data-audit-bad]').forEach(b=>b.addEventListener('click',()=>judge(b.dataset.auditBad,false)));
  }catch(e){box.innerHTML=`<p class="muted">${esc(e.message)}</p>`}
}
document.getElementById('scanAuditCard')?.addEventListener('toggle',e=>{if(e.target.open)loadScanAudit()});
document.getElementById('scanAuditRefresh')?.addEventListener('click',loadScanAudit);
document.getElementById('scanAuditDraw')?.addEventListener('click',async()=>{const id=Number(document.getElementById('scanExam').value);if(!id)return toast('Sınav seçin.','error');try{const r=await api('POST',`/api/exams/${id}/scan-audit/sample`,{percent:Number(document.getElementById('scanAuditPercent').value||10),minimum:5});toast(`${r.drawn} sayfa örneklendi.`);await loadScanAudit()}catch(e){toast(e.message,'error')}});
document.getElementById('closurePackage')?.addEventListener('click',async()=>{const e=state.currentExam;if(!e)return;try{await downloadApi(`/api/exams/${e.id}/closure-package.zip`,`kapanis-paketi-sinav-${e.id}.zip`);toast('Kapanış paketi indirildi; içindeki SHA256SUMS.json bütünlük özetidir.')}catch(err){toast(err.message,'error')}});

async function loadRetention(){
  const box=document.getElementById('retentionBox');if(!box)return;
  try{const r=await api('GET','/api/archive/retention');
    box.innerHTML=`<p class="muted">Saklama süresi: ${r.scan_retention_days} gün · süresi dolan: <b>${r.expired_count}</b></p>`+(r.items.length?`<div class="tw"><table class="rt"><thead><tr><th>Sınav</th><th>Kilit tarihi</th><th>Dosya</th><th>Bitiş</th><th></th></tr></thead><tbody>${r.items.map(x=>`<tr><td>${esc(x.title)}</td><td>${esc(x.grade_locked_at.slice(0,10))}</td><td>${x.scan_files}</td><td>${esc(x.retention_until.slice(0,10))}</td><td>${x.expired?`<button class="danger small" data-purge="${x.exam_id}">Görselleri sil</button>`:'<span class="chip">süresi dolmadı</span>'}</td></tr>`).join('')}</tbody></table></div>`:'<p class="muted">Saklanan tarama görseli yok.</p>');
    box.querySelectorAll('[data-purge]').forEach(b=>b.addEventListener('click',async()=>{const d=await workflowForm({eyebrow:'KAYITLI SİLME',title:'Tarama görsellerini sil',description:'Geri alınamaz. Puanlar ve işlem kaydı korunur; silme denetim kaydına yazılır.',submitLabel:'Sil',fields:[{name:'reason',label:'Gerekçe',type:'textarea',required:true,rows:3,placeholder:'Örn. arşiv yönergesi gereği saklama süresi doldu'}]});if(!d)return;try{const r2=await api('POST',`/api/exams/${b.dataset.purge}/purge-scans`,{reason:d.reason});toast(`${r2.files_removed} dosya silindi.`);await loadRetention()}catch(e){toast(e.message,'error')}}));
  }catch(e){box.innerHTML=`<p class="muted">${esc(e.message)}</p>`}
}
document.getElementById('retentionCard')?.addEventListener('toggle',e=>{if(e.target.open)loadRetention()});

async function prepareScan(){
  try{await refreshCore();await loadScanContext();renderScanFileCount();}catch(e){toast(e.message,'error');}
}
function scanCurrentExam(){const id=Number(document.getElementById('scanExam').value);return (state.exams||[]).find(x=>x.id===id)||null;}
function scanIssueLabel(code){return ({AMBIGUOUS_MARK:'Belirsiz işaret',STUDENT_NOT_IDENTIFIED:'Öğrenci bulunamadı',STUDENT_NOT_ASSIGNED:'Sınava atanmamış öğrenci',TOKEN_MISMATCH:'QR / kitapçık doğrulama',EXAM_NOT_GRADING:'Değerlendirme modu kapalı',NO_OMR_MARKERS:'Optik alan bulunamadı',NO_MATCHING_QR:'Sınav QR eşleşmedi',DUPLICATE_PAGE:'Tekrar tarama'})[code]||code;}
function renderScanModeStatus(){
  const exam=scanCurrentExam(),box=document.getElementById('scanModeStatus'),btn=document.getElementById('scanSetGrading');if(!box||!btn)return;
  ['downloadPersonalized','refreshReviews','scanOpenAnalytics'].forEach(id=>{const x=document.getElementById(id);if(x)x.disabled=!exam;});
  if(!exam){box.className='scan-mode-status needs-action';box.innerHTML='<span class="status-dot"></span><div><b>Önce sınav seçin</b><small>Tarama oturumu ve inceleme kuyruğu seçilen sınava göre açılır.</small></div>';btn.classList.add('hidden');renderScanFileCount();return;}
  const grading=exam.status==='grading';box.className=`scan-mode-status ${grading?'is-ready':'needs-action'}`;box.innerHTML=`<span class="status-dot"></span><div><b>${grading?'Tarama ve otomatik puanlama açık':'Otomatik puanlama bekliyor'}</b><small>${grading?'Sınav değerlendirme durumunda. Güvenli optikler doğrudan sonuçlara yazılır.':`Mevcut durum: ${esc(statusLabel(exam.status))}. Tarama yapılabilir ancak sayfalar incelemeye düşebilir.`}</small></div>`;
  btn.classList.toggle('hidden',grading);btn.disabled=exam.status==='draft';btn.title=exam.status==='draft'?'Önce Sınav Hazırla ekranında sınavı hazır durumuna alın.':'';renderScanFileCount();
}
document.getElementById('scanCamera')?.addEventListener('change',e=>{const main=document.getElementById('scanFile');if(!main)return;const dt=new DataTransfer();[...main.files,...e.target.files].forEach(f=>dt.items.add(f));main.files=dt.files;e.target.value='';renderScanFileCount();toast(`${main.files.length} fotoğraf/dosya yüklemeye hazır. Tüm kâğıtları çekince "Yükle ve oku"ya basın.`);});
function renderScanFileCount(){
  const el=document.getElementById('scanFileCount'),input=document.getElementById('scanFile'),drop=input?.closest('.scan-file-drop'),btn=document.getElementById('uploadScan'),count=input?.files?.length||0,hasExam=Boolean(Number(document.getElementById('scanExam')?.value||0));
  if(el)el.textContent=`${count} dosya`;if(drop)drop.classList.toggle('has-files',count>0);if(btn)btn.disabled=!hasExam||count===0;
}
async function loadScanContext(){
  const id=Number(document.getElementById('scanExam').value);renderScanModeStatus();
  if(!id){
    document.getElementById('scanQuickStats').innerHTML='<div><b>—</b><span>Okunan sayfa</span><small>Sınav seçin</small></div><div><b>—</b><span>Otomatik uygulandı</span><small>Sınav seçin</small></div><div><b>—</b><span>Klasik sayfa</span><small>Sınav seçin</small></div><div><b>—</b><span>Karar bekliyor</span><small>Sınav seçin</small></div><div><b>—</b><span>Tekrar tarama</span><small>Sınav seçin</small></div><div><b>—</b><span>Atlanan / reddedilen</span><small>Sınav seçin</small></div>';
    document.getElementById('scanSessions').innerHTML='<div class="empty-state"><b>Tarama geçmişi için sınav seçin.</b><span>Yukarıdaki sınav alanından çalışmak istediğiniz sınavı seçin.</span></div>';
    document.getElementById('scanReviews').innerHTML='<div class="empty-state"><b>İnceleme kuyruğu henüz açılmadı.</b><span>Bir sınav seçtiğinizde bekleyen optikler burada görüntülenir.</span></div>';
    const badge=document.getElementById('scanReviewBadge');if(badge){badge.textContent='0 bekleyen';badge.className='badge status-approved';}
    return;
  }
  const [sessions,reviews,revisions,students]=await Promise.all([api('GET',`/api/exams/${id}/scans`),api('GET',`/api/exams/${id}/scan-reviews`),api('GET',`/api/exams/${id}/answer-key/revisions`),api('GET',`/api/exams/${id}/students`)]);state.scanStudents=students;state.scanReviews=reviews;
  const totals=sessions.reduce((a,x)=>({pages:a.pages+Number(x.page_count||0),accepted:a.accepted+Number(x.accepted_count||0),support:a.support+Number(x.support_count||0),review:a.review+Number(x.review_count||0),duplicate:a.duplicate+Number(x.duplicate_count||0),skipped:a.skipped+Number(x.skipped_count||0)}),{pages:0,accepted:0,support:0,review:0,duplicate:0,skipped:0});
  const usable=Math.max(0,totals.pages-totals.skipped-totals.duplicate-totals.support),autoPct=usable?Math.round(totals.accepted/usable*100):0;
  document.getElementById('scanQuickStats').innerHTML=`<div><b>${totals.pages}</b><span>Okunan sayfa</span></div><div class="ok"><b>${totals.accepted}</b><span>Otomatik uygulandı</span><small>%${autoPct} güvenli akış</small></div><div><b>${totals.support}</b><span>Klasik sayfa</span><small>Puanlama masasına bağlı</small></div><div class="warn"><b>${reviews.length}</b><span>Karar bekliyor</span><small>${reviews.length?'Öğretmen doğrulaması gerekli':'Kuyruk temiz'}</small></div><div><b>${totals.duplicate}</b><span>Tekrar tarama</span></div><div><b>${totals.skipped}</b><span>Atlanan / reddedilen</span></div>`;
  try{const cov=await api('GET',`/api/exams/${id}/scan-coverage`);const box=document.getElementById('scanQuickStats');box.insertAdjacentHTML('beforeend',`<div class="${cov.missing_count?'warn':'ok'}"><b>${cov.scanned}/${cov.attended}</b><span>Kâğıdı okunan öğrenci</span><small>${cov.missing_count?`Eksik: ${esc(cov.missing.slice(0,5).map(x=>x.student_no).join(', '))}${cov.missing_count>5?' …':''}`:'Tüm katılanların kâğıdı var'}</small></div>`+(cov.incomplete_papers?.length?`<div class="warn"><b>${cov.incomplete_papers.length}</b><span>Eksik sayfalı kâğıt</span><small>${esc(cov.incomplete_papers.slice(0,3).map(x=>`${x.student_no}: s.${x.missing_pages.join(',')}`).join(' · '))}</small></div>`:''))}catch(e){}
  document.getElementById('scanSessions').innerHTML=sessions.length?sessions.map(x=>{const total=Number(x.page_count||0);const accepted=Number(x.accepted_count||0);const pct=Number(x.auto_accept_percent??(total?accepted/total*100:0));return `<button class="scan-session-row" type="button" data-session="${x.id}"><div class="scan-session-icon">${Math.round(pct)}%</div><div><b>#${x.id} · ${esc(x.source_name)}</b><small>${total} sayfa · ${x.review_count?'inceleme sürüyor':'tamamlandı'}</small><div class="mini-progress"><span data-style="width:${Math.min(100,pct)}%"></span></div></div><div class="scan-session-meta"><span class="pill-ok">${accepted} kabul</span>${x.support_count?`<span class="badge">${x.support_count} klasik</span>`:''}${x.review_count?`<span class="pill-warn">${x.review_count} inceleme</span>`:''}${x.duplicate_count?`<span class="badge">${x.duplicate_count} tekrar</span>`:''}</div></button>`}).join(''):'<div class="empty-state"><b>Henüz tarama yok.</b><span>ADF cihazından alınan PDF veya görselleri toplu yükleyebilirsiniz.</span></div>';
  renderScanReviews();
  const badge=document.getElementById('scanReviewBadge');badge.textContent=`${reviews.length} bekleyen`;badge.className=`badge ${reviews.length?'status-ready':'status-approved'}`;
  document.getElementById('regradeHistory').innerHTML=revisions.length?revisions.map(x=>`<div class="revision-row"><b>Revizyon #${x.id}</b><span>${esc(x.reason||'Neden belirtilmedi')}</span><small>${x.affected_responses} cevap yeniden puanlandı</small></div>`).join(''):'<p class="muted">Cevap anahtarı revizyonu yok.</p>';
}
function scanAnswerRows(r){
  const rows=r.diagnostic_summary||[];if(!rows.length)return '<div class="review-no-diagnostics">Bu sayfada soru bazlı optik skoru üretilemedi.</div>';
  return rows.map(x=>{const current=(r.answers||{})[String(x.question_no)]||'';const candidates=(x.top_candidates||[]).map(c=>`${esc(c.letter)} %${Math.round(Number(c.score)*100)}`).join(' · ');return `<div class="scan-answer-review ${x.state==='ambiguous'?'needs-review':''}" data-no="${x.question_no}" data-answer="${esc(current)}"><div class="scan-answer-meta"><b>S${x.question_no}</b><span class="${x.state==='ambiguous'?'confidence-low':'confidence-ok'}">${x.state==='ambiguous'?'Kontrol':'Okundu'} · %${Math.round(Number(x.confidence||0)*100)}</span><small>${candidates}</small></div><div class="scan-answer-options">${['A','B','C','D','E'].map(k=>`<button type="button" data-review-choice="${k}" class="${current===k?'active':''} ${x.suggested_answer===k&&x.state==='ambiguous'?'suggested':''}">${k}</button>`).join('')}<button type="button" data-review-choice="" class="blank-choice ${current?'':'active'}">Boş</button></div></div>`;}).join('');
}
function renderScanReviews(){
  const box=document.getElementById('scanReviews'),filter=document.getElementById('scanReviewFilter')?.value||'all';let rows=state.scanReviews||[];if(filter!=='all')rows=rows.filter(r=>(r.issue_codes||[]).includes(filter));
  box.innerHTML=rows.length?rows.map(r=>`<article class="scan-review modern-review scan-review-workbench" data-item="${r.scan_item_id}"><div class="review-preview-col"><div class="review-image-head"><span>Sayfa ${r.page_no}</span><b>Güven %${r.confidence_percent??0}</b></div>${r.preview_url?`<a href="${r.raw_preview_url||r.preview_url}" target="_blank" rel="noopener"><img class="scan-preview scan-annotated-preview" src="${r.preview_url}" alt="Optik inceleme önizlemesi"></a>`:'<div class="preview-placeholder">Optik önizleme üretilemedi</div>'}<div class="preview-legend"><span><i class="legend-green"></i>Okunan</span><span><i class="legend-amber"></i>Şüpheli</span></div></div><div class="review-resolution"><div class="review-title"><div><span class="badge status-ready">Sayfa ${r.page_no}</span><b>${esc(r.student_no||'Öğrenci belirlenemedi')} · Kitapçık ${esc(r.booklet||'-')}</b></div><small>${esc(r.reason)}</small></div><div class="review-issue-chips">${(r.issue_codes||[]).map(c=>`<span>${esc(scanIssueLabel(c))}</span>`).join('')}</div><div class="review-identity-grid"><label>Öğrenci<select class="resolve-student"><option value="">Öğrenci seçin</option>${(state.scanStudents||[]).map(s=>`<option value="${s.id}" ${r.student_id===s.id?'selected':''}>${esc(s.student_no)} · ${esc(s.full_name)}</option>`).join('')}</select></label><label>Kitapçık<select class="resolve-booklet">${['A','B','C','D'].map(k=>`<option ${r.booklet===k?'selected':''}>${k}</option>`).join('')}</select></label></div><div class="review-answer-head"><div><b>Cevap doğrulama</b><span>Turuncu satırlar özellikle kontrol edilmeli.</span></div><span>${r.attention_questions?.length?`${r.attention_questions.length} şüpheli soru`:'Kimlik/durum kontrolü'}</span></div><div class="review-answers review-answer-grid">${scanAnswerRows(r)}</div><label class="review-note">İnceleme notu <input class="resolve-note" placeholder="Opsiyonel: neden düzeltildi / reddedildi"></label><div class="review-actions"><button class="ghost reject-scan" type="button">Sayfayı reddet</button><button class="primary resolve-scan" type="button">Onayla ve sonuçlara uygula</button></div></div></article>`).join(''):`<div class="empty-state success-empty"><b>${filter==='all'?'İnceleme kuyruğu temiz.':'Bu filtrede kayıt yok.'}</b><span>${filter==='all'?'Tüm okunabilir sayfalar otomatik işlendi veya öğretmen tarafından karara bağlandı.':'Farklı bir sorun filtresi seçebilirsiniz.'}</span></div>`;
  box.querySelectorAll('[data-review-choice]').forEach(btn=>btn.addEventListener('click',()=>{const row=btn.closest('.scan-answer-review');row.dataset.answer=btn.dataset.reviewChoice;row.querySelectorAll('[data-review-choice]').forEach(x=>x.classList.toggle('active',x===btn));}));
  box.querySelectorAll('.resolve-scan').forEach(b=>b.addEventListener('click',()=>resolveScanReview(b.closest('.scan-review'),false)));
  box.querySelectorAll('.reject-scan').forEach(b=>b.addEventListener('click',()=>resolveScanReview(b.closest('.scan-review'),true)));
}
async function resolveScanReview(root,reject=false){
  const item=Number(root.dataset.item),student_id=Number(root.querySelector('.resolve-student').value||0),booklet=root.querySelector('.resolve-booklet').value,note=root.querySelector('.resolve-note').value.trim(),answers={};root.querySelectorAll('.scan-answer-review').forEach(x=>answers[x.dataset.no]=x.dataset.answer||null);
  if(reject&&!confirm('Bu tarama sayfası sonuçlara aktarılmadan reddedilsin mi?'))return;
  if(!reject&&!student_id)return toast('Onay için öğrenci seçin.','error');
  try{await api('POST',`/api/scan-items/${item}/resolve`,{action:reject?'reject':'accept',student_id:student_id||null,booklet,answers,note});toast(reject?'Tarama sayfası reddedildi.':'Optik doğrulandı ve sonuçlara uygulandı.');await loadScanContext();}catch(e){toast(e.message,'error');}
}
document.getElementById('scanExam').addEventListener('change',loadScanContext);
document.getElementById('scanReviewFilter').addEventListener('change',renderScanReviews);
document.getElementById('scanFile').addEventListener('change',renderScanFileCount);
document.getElementById('refreshReviews').addEventListener('click',loadScanContext);
document.getElementById('downloadPersonalized').addEventListener('click',async()=>{const id=Number(document.getElementById('scanExam').value);if(!id)return toast('Sınav seçin.','error');try{await downloadApi(`/api/exams/${id}/papers-batch.pdf?booklet_strategy=rotate`,`sinav-${id}-ogrenci-kagitlari.pdf`);}catch(e){toast(e.message,'error');}});
document.getElementById('scanSetGrading').addEventListener('click',async()=>{const exam=scanCurrentExam();if(!exam)return toast('Sınav seçin.','error');if(exam.status==='draft')return toast('Önce Sınav Hazırla ekranında sınavı hazır durumuna alın.','error');try{await api('POST',`/api/exams/${exam.id}/status`,{status:'grading'});toast('Sınav değerlendirme moduna alındı. Otomatik optik puanlama açık.');await refreshCore();document.getElementById('scanExam').value=String(exam.id);await loadScanContext();}catch(e){toast(e.message,'error');}});
document.getElementById('scanOpenAnalytics').addEventListener('click',()=>{const id=Number(document.getElementById('scanExam').value);if(!id)return toast('Sınav seçin.','error');showPage('analytics');setTimeout(()=>{document.getElementById('analyticsExam').value=String(id);},120);});
document.getElementById('uploadScan').addEventListener('click',async()=>{const id=Number(document.getElementById('scanExam').value),files=[...document.getElementById('scanFile').files];if(!id||!files.length)return toast('Sınav ve en az bir tarama dosyası seçin.','error');if(files.length>20)return toast('Tek seferde en fazla 20 dosya seçebilirsiniz.','error');const fd=new FormData();files.forEach(file=>fd.append('files',file));const summary=document.getElementById('scanSummary');summary.classList.remove('hidden');summary.innerHTML=`<b>${files.length} dosya işleniyor…</b><span>QR, öğrenci, kitapçık, optik işaretler ve tekrar taramalar kontrol ediliyor.</span>`;try{const r=await api('POST',`/api/exams/${id}/scans-batch`,fd),t=r.totals||{};summary.innerHTML=`<div class="scan-summary-head"><div><b>Toplu tarama tamamlandı</b><span>${t.completed_files||0}/${t.files||files.length} dosya işlendi${t.failed_files?` · ${t.failed_files} dosya hata verdi`:''}.</span></div>${t.review?`<strong>${t.review} sayfa karar bekliyor</strong>`:'<strong class="ok-text">İnceleme kuyruğu temiz</strong>'}</div><div class="scan-result-grid"><span><strong>${t.pages??'—'}</strong> sayfa</span><span><strong>${t.accepted??'—'}</strong> otomatik kabul</span><span><strong>${t.support??'—'}</strong> klasik sayfa</span><span><strong>${t.review??'—'}</strong> inceleme</span><span><strong>${t.duplicate??'—'}</strong> tekrar</span><span><strong>${t.skipped??'—'}</strong> atlandı</span></div>${r.failed?.length?`<div class="scan-fail-list">${r.failed.map(x=>`<span>${esc(x.source_name)} · ${esc(x.message)}</span>`).join('')}</div>`:''}`;toast('Toplu tarama işlendi.');document.getElementById('scanFile').value='';renderScanFileCount();await loadScanContext();}catch(e){summary.classList.add('hidden');toast(e.message,'error');}});
['runAnnul','runAcceptAlt'].forEach(bid=>document.getElementById(bid)?.addEventListener('click',async()=>{const id=Number(document.getElementById('scanExam').value),qid=Number(document.getElementById('regradeQuestion').value),reason=document.getElementById('regradeReason').value;const annul=bid==='runAnnul';if(!id||!qid)return toast('Sınav ve soru ID girin.','error');if(!confirm(annul?'Bu soru iptal edilecek ve katılan tüm öğrencilere tam puan verilecek. Devam?':'Seçili şık da doğru kabul edilecek. Devam?'))return;try{const r=await api('POST',`/api/exams/${id}/questions/${qid}/key-exception`,{action:annul?'annul':'accept_alternative',alternative:annul?null:document.getElementById('regradeAnswer').value,reason});toast(`${r.affected_responses} cevap güncellendi.`);await loadScanContext();}catch(e){toast(e.message,'error');}}));
document.getElementById('runRegrade').addEventListener('click',async()=>{const id=Number(document.getElementById('scanExam').value),qid=Number(document.getElementById('regradeQuestion').value),ans=document.getElementById('regradeAnswer').value;if(!id||!qid)return toast('Sınav ve soru ID girin.','error');try{const r=await api('POST',`/api/exams/${id}/answer-key/regrade`,{corrections:{[qid]:ans},reason:document.getElementById('regradeReason').value});toast(`${r.affected_responses} cevap yeniden puanlandı.`);await loadScanContext();}catch(e){toast(e.message,'error');}});

document.getElementById('loDiffBtn')?.addEventListener('click',async()=>{
  const courseId=Number(document.getElementById('outcomeCourse').value),box=document.getElementById('loDiffBox');if(!courseId)return;
  try{const d=await api('GET',`/api/courses/${courseId}/outcome-diff`);box.classList.remove('hidden');
    const label={added_in_assess:"Assess'te eklendi (OBS'de yok)",modified:'OBS metninden değiştirildi',inactive:'Pasife alındı'};
    box.innerHTML=d.items.length?`<p class="muted">${d.difference_count} fark var. Bu listeyi OBS'ye elle yansıtabilirsiniz.</p>`+d.items.map(x=>`<div class="outcome-entity-item"><div class="outcome-code-block"><b>${esc(x.code)}</b><small>${esc(label[x.kind]||x.kind)}</small></div><div class="outcome-entity-copy"><b>${esc(x.current.description)}</b>${x.obs_original?`<small>OBS'teki: ${esc(x.obs_original.description)} (hedef %${esc(x.obs_original.target_percent)})</small>`:''}</div></div>`).join(''):'<p class="muted">OBS ile fark yok.</p>';
  }catch(e){toast(e.message,'error');}
});
async function loadGradeCompleteness(){
  const id=Number(document.getElementById('gradeExam')?.value||0),box=document.getElementById('gradeCompleteness');if(!box)return;
  if(!id){box.classList.add('hidden');return}
  try{const g=await api('GET',`/api/exams/${id}/grading-progress`);box.classList.remove('hidden');
    box.innerHTML=`<div class="readiness-head"><div><b>${g.complete?'Tüm puanlar girildi':`${g.missing} puan girilmedi`}</b><small>"Girilmedi" ile 0 puan ayrıdır; eksik puan varsa puanlar kilitlenemez.</small></div><span>${g.entered}/${g.expected} · %${g.percent}</span></div>`+(g.students_with_missing.length?`<div class="readiness-warning-list">${g.students_with_missing.slice(0,6).map(x=>`<div><i>i</i><span>${esc(x.student_no)}: soru ${esc(x.missing_questions.join(', '))} girilmedi</span></div>`).join('')}${g.students_with_missing.length>6?`<div><i>i</i><span>… ve ${g.students_with_missing.length-6} öğrenci daha</span></div>`:''}</div>`:'');
  }catch{box.classList.add('hidden')}
}
document.getElementById('gradeStudent')?.addEventListener('change',loadGradeCompleteness);

function fillGradeGridQuestions(){const sel=document.getElementById('gradeGridQuestion');if(!sel)return;const prev=sel.value;sel.innerHTML=gradeClassicQuestions().map(q=>`<option value="${q.id}">Soru ${q.order_no} (${q.points} puan)</option>`).join('');if(prev)sel.value=prev;}
document.getElementById('gradeGridCard')?.addEventListener('toggle',e=>{if(e.target.open)fillGradeGridQuestions()});
document.getElementById('gradeGridLoad')?.addEventListener('click',async()=>{
  const id=Number(document.getElementById('gradeExam').value),qid=Number(document.getElementById('gradeGridQuestion').value),box=document.getElementById('gradeGridBox'),save=document.getElementById('gradeGridSave');
  if(!id||!qid){box.innerHTML='<p class="muted">Rubrikli klasik soru seçin.</p>';save.classList.add('hidden');return}
  try{const g=await api('GET',`/api/exams/${id}/questions/${qid}/grid`);const cr=g.question.criteria;const blind=gradeBlindEnabled();
    box.innerHTML=`<table class="rt grade-grid" data-q="${qid}" data-exam="${id}"><thead><tr><th>#</th>${cr.map(c=>`<th>${esc(c.label)} <small>/${c.max_points}</small></th>`).join('')}<th>Toplam / ${g.question.points}</th></tr></thead><tbody>${g.rows.map((r,i)=>`<tr data-student="${r.student_id}"><td>${blind?`Aday ${String(i+1).padStart(3,'0')}`:`${esc(r.student_no)} · ${esc(r.name)}`} ${r.entered?'':'<span class="chip">girilmedi</span>'}</td>${cr.map(c=>`<td><input type="number" step="0.5" min="0" max="${c.max_points}" data-crit="${esc(c.id)}" value="${r.rubric_scores?.[c.id]??''}" ${g.editable?'':'disabled'}></td>`).join('')}<td class="grid-total">${r.awarded??'—'}</td></tr>`).join('')}</tbody></table>${g.annulled?'<p class="muted">Bu soru iptal edildi; herkese tam puan verildi.</p>':g.editable?'':'<p class="muted">Puan girişi şu an kapalı (durum veya kilit).</p>'}`;
    save.classList.toggle('hidden',!g.editable);
    box.querySelectorAll('tr[data-student]').forEach(tr=>tr.addEventListener('input',()=>{const v=[...tr.querySelectorAll('input')].map(i=>i.value);tr.querySelector('.grid-total').textContent=v.some(x=>x==='')?'—':v.reduce((a,x)=>a+Number(x),0)}));
  }catch(e){toast(e.message,'error');}
});
document.getElementById('gradeGridSave')?.addEventListener('click',async()=>{
  const t=document.querySelector('#gradeGridBox table.grade-grid');if(!t)return;const id=t.dataset.exam,qid=t.dataset.q;const rows=[];let empty=0;
  t.querySelectorAll('tr[data-student]').forEach(tr=>{const sc={};let full=true;tr.querySelectorAll('input').forEach(i=>{if(i.value==='')full=false;else sc[i.dataset.crit]=Number(i.value)});if(full)rows.push({student_id:Number(tr.dataset.student),rubric_scores:sc});else if(Object.keys(sc).length)empty++;});
  if(empty)return toast(`${empty} satır yarım doldurulmuş; tüm ölçütleri girin ya da satırı boş bırakın.`,'error');
  if(!rows.length)return toast('Kaydedilecek dolu satır yok.','error');
  try{const r=await api('POST',`/api/exams/${id}/questions/${qid}/grid`,{rows});toast(`${r.saved} öğrencinin puanı kaydedildi.`);document.getElementById('gradeGridLoad').click();loadGradeCompleteness();}catch(e){toast(e.message,'error');}
});

async function prepareGrade(){
  try{await refreshCore();await loadGradeStudents();renderGradeProgress();syncGradeModeUI();}catch(e){toast(e.message,'error');}
}
function gradeMode(){return document.getElementById('gradeMode')?.value||'student';}
function gradeBlindEnabled(){return !!document.getElementById('gradeBlind')?.checked;}
function selectedGradeQuestionId(){return Number(document.getElementById('gradeQuestion')?.value||0);}
function gradeClassicQuestions(){return (state.currentGradeExam?.questions||[]).filter(q=>q.question_type==='classic');}
function populateGradeQuestionSelect(exam){const sel=document.getElementById('gradeQuestion');if(!sel)return;const classic=(exam?.questions||[]).filter(q=>q.question_type==='classic');const prev=Number(sel.value||0);sel.innerHTML=classic.map(q=>`<option value="${q.id}">${q.order_no}. soru · ${esc(q.text.slice(0,70))}${q.text.length>70?'…':''}</option>`).join('');if(classic.some(q=>q.id===prev))sel.value=String(prev);}
function syncGradeModeUI(){const serial=gradeMode()==='question';document.getElementById('gradeQuestionWrap')?.classList.toggle('hidden',!serial);document.querySelector('.grade-hero h3').textContent=serial?'Aynı klasik soruyu tüm öğrencilerde seri ve tutarlı biçimde puanlayın':'Öğrenci öğrenci ilerleyin, puanı kaydedip sıradakine geçin';document.querySelector('.grade-hero p').textContent=serial?'Rubrik sabit kalır; yalnız öğrenci cevabı değişir. Kör değerlendirme ve klavye kısayollarıyla hızlı ilerleyin.':'Test cevapları otomatik puanlanır; klasik sorularda taranmış cevap solda, rubrik ve puanlama sağda birlikte açılır.';renderGradeProgress();}
async function loadGradeStudents(){
  const id=Number(document.getElementById('gradeExam').value); const sel=document.getElementById('gradeStudent');document.getElementById('gradeForm').classList.add('hidden');document.getElementById('gradeStudentSummary').classList.add('hidden');
  if(!id){sel.innerHTML='';renderGradeProgress();return;}
  const [rows,exam]=await Promise.all([api('GET',`/api/exams/${id}/students`),api('GET',`/api/exams/${id}`)]);state.gradeStudents=rows;state.currentGradeExam=exam;loadGradeCompleteness();sel.innerHTML=rows.map((s,i)=>`<option value="${s.id}">${gradeBlindEnabled()?`Aday ${String(i+1).padStart(3,'0')}`:`${esc(s.student_no)} · ${esc(s.full_name)}`}</option>`).join('');populateGradeQuestionSelect(exam);syncGradeModeUI();renderGradeProgress();
}
function refreshGradeStudentLabels(){const sel=document.getElementById('gradeStudent');const rows=state.gradeStudents||[];const selected=sel.value;sel.innerHTML=rows.map((s,i)=>`<option value="${s.id}">${gradeBlindEnabled()?`Aday ${String(i+1).padStart(3,'0')}`:`${esc(s.student_no)} · ${esc(s.full_name)}`}</option>`).join('');if(rows.some(x=>String(x.id)===selected))sel.value=selected;}
function renderGradeProgress(){const rows=state.gradeStudents||[];const idx=Math.max(0,rows.findIndex(x=>String(x.id)===document.getElementById('gradeStudent').value));const serial=gradeMode()==='question';const q=gradeClassicQuestions().find(x=>x.id===selectedGradeQuestionId());document.getElementById('gradeProgress').innerHTML=rows.length?`<div class="progress-meta"><b>${idx+1} / ${rows.length}</b><span>${serial?`Soru ${q?.order_no||'—'} · öğrenci`:'Öğrenci'}</span></div><div class="progress-track"><span data-style="width:${Math.round((idx+1)/rows.length*100)}%"></span></div>`:'<div class="muted">Sınav seçildiğinde öğrenci listesi hazırlanır.</div>';}
function gradeStudentIndex(){const rows=state.gradeStudents||[];return rows.findIndex(x=>String(x.id)===document.getElementById('gradeStudent').value);}
async function moveGradeStudent(delta,load=true){const rows=state.gradeStudents||[];if(!rows.length)return;let i=gradeStudentIndex();i=Math.max(0,Math.min(rows.length-1,i+delta));document.getElementById('gradeStudent').value=String(rows[i].id);renderGradeProgress();if(load)await loadCurrentGrade();}
function gradeClassicLiveTotal(){let total=0;document.querySelectorAll('.grade-q[data-type="classic"] .pts,.grade-q[data-type="classic"] .rubric-pts').forEach(x=>total+=Number(x.value||0));const el=document.getElementById('gradeLiveTotal');if(el)el.innerHTML=`<b>${Number(total.toFixed(2))}</b><span>${gradeMode()==='question'?'Bu sorunun rubrik toplamı':'Girilen klasik puan'}</span>`;}
function updateRubricCardTotal(root){if(!root)return;const inputs=[...root.querySelectorAll('.rubric-pts')];if(!inputs.length)return;const total=inputs.reduce((a,x)=>a+Number(x.value||0),0);const max=Number(root.dataset.maxPoints||0);const el=root.querySelector('.rubric-total b');if(el)el.textContent=`Toplam: ${Number(total.toFixed(2))} / ${max}`;}
function gradeChoiceButtons(q,r){const current=String(r.answer_text||'').toUpperCase();const correct=String(q.correct_answer||'').toUpperCase();const legend=`<div class="grade-answer-legend"><span class="student-mark">Öğrencinin işareti</span><span class="correct-mark">Doğru cevap</span><span class="wrong-mark">Yanlış işaret</span></div>`;return `${legend}<div class="grade-choice-buttons"><select class="ans sr-only"><option value="">Cevap yok</option>${Object.entries(q.choices||{}).map(([k,v])=>`<option value="${esc(k)}" ${current===k?'selected':''}>${esc(k)}) ${esc(v)}</option>`).join('')}</select>${Object.entries(q.choices||{}).map(([k,v])=>{const selected=current===k,isCorrect=correct===k,wrongSelected=selected&&correct&&k!==correct;const cls=[selected?'is-student-selected':'',isCorrect?'is-correct-answer':'',wrongSelected?'is-wrong-selection':''].filter(Boolean).join(' ');const labels=[selected?'<em class="student-answer-tag">Öğrenci</em>':'',isCorrect?'<em class="correct-answer-tag">Doğru</em>':'',wrongSelected?'<em class="wrong-answer-tag">Yanlış</em>':''].join('');return `<button type="button" data-answer="${esc(k)}" class="${cls}"><b>${esc(k)}</b><span>${esc(v)}</span><i>${labels}</i></button>`}).join('')}<button type="button" data-answer="" class="clear-choice ${current?'':'active'}">Boş</button></div>`;}
function classicScanPane(q,scanRow){const scan=scanRow?.scan;if(!scan)return `<div class="classic-scan-pane classic-scan-empty"><div class="classic-scan-empty-icon">▧</div><b>Taranmış klasik cevap bulunamadı</b><span>Optik & Kontrol ekranından bu öğrencinin tam sınav kağıdını yükleyin. Puan girişi yine manuel yapılabilir.</span></div>`;const legacy=scan.legacy_association?'<span class="classic-scan-legacy">Eski kağıt · sıralı eşleme</span>':'';return `<div class="classic-scan-pane"><div class="classic-scan-head"><div><span class="eyebrow">TARANMIŞ CEVAP</span><b>Sayfa ${scan.logical_page_no||'—'} · Kitapçık ${esc(scan.booklet||'A')}</b></div>${legacy}</div><div class="classic-scan-canvas"><img class="classic-scan-image" src="${esc(scan.answer_preview_url)}" alt="${q.order_no}. sorunun taranmış klasik cevabı" loading="lazy"></div><div class="classic-scan-toolbar"><button type="button" class="ghost small active" data-scan-src="${esc(scan.answer_preview_url)}">Cevap alanı</button><button type="button" class="ghost small" data-scan-src="${esc(scan.question_preview_url)}">Soru + cevap</button><a class="ghost small classic-full-page" target="_blank" rel="noopener" href="${esc(scan.full_page_url)}">Tam sayfa ↗</a></div></div>`;}
function rubricPresetValues(max){return [0,.25,.5,.75,1].map(r=>Math.round(max*r*2)/2).filter((v,i,a)=>a.indexOf(v)===i);}
function rubricCriterionHtml(c,scores,index){const max=Number(c.max_points||0),value=Number(scores[c.id]??0),vals=rubricPresetValues(max);return `<div class="rubric-criterion-card" data-rubric-row="${index}"><div class="rubric-criterion-head"><span>${esc(c.label)}</span><small>0–${max} puan</small></div><div class="rubric-fast-row">${vals.map((v,i)=>`<button type="button" class="rubric-fast ${Math.abs(value-v)<.001?'active':''}" data-rubric-score="${v}" data-key="${i+1}" title="Kısayol ${i+1}">${v}</button>`).join('')}</div><div class="rubric-input-wrap"><input class="rubric-pts" data-criterion="${esc(c.id)}" type="number" min="0" max="${max}" step="0.5" value="${value}" aria-label="${esc(c.label)} puanı"><small>/ ${max}</small></div></div>`;}
async function loadCurrentGrade(){
  const examId=Number(document.getElementById('gradeExam').value);const studentId=Number(document.getElementById('gradeStudent').value);if(!examId||!studentId)return;
  try{const [exam,existing,classicScans]=await Promise.all([api('GET',`/api/exams/${examId}`),api('GET',`/api/exams/${examId}/students/${studentId}/responses`),api('GET',`/api/exams/${examId}/students/${studentId}/classic-scans`)]);if(exam.status!=='grading'){toast(`Bu sınav ${statusLabel(exam.status)} durumunda. Puan girişi için değerlendirme durumuna alın.`,`error`);}state.currentGradeExam=exam;populateGradeQuestionSelect(exam);const map=new Map(existing.map(x=>[x.question_id,x]));const scanMap=new Map((classicScans.classic_questions||[]).map(x=>[x.question_id,x]));const stu=(state.gradeStudents||[]).find(x=>x.id===studentId);const idx=Math.max(0,gradeStudentIndex());const totalExisting=existing.reduce((a,r)=>a+Number(r.awarded_points||0),0);const classicTotal=(classicScans.classic_questions||[]).length;const classicReady=(classicScans.classic_questions||[]).filter(x=>x.scan).length;const blind=gradeBlindEnabled();const serial=gradeMode()==='question';const identityName=blind?`Aday ${String(idx+1).padStart(3,'0')}`:(stu?.full_name||'');const identityMeta=blind?'Kimlik puanlama tamamlanana kadar gizli':`${stu?.student_no||''} · ${esc(exam.title||exam.name||'Seçili sınav')}`;document.getElementById('gradeStudentSummary').innerHTML=`<div class="grade-student-identity"><span class="eyebrow">${blind?'KÖR DEĞERLENDİRME':'AKTİF ÖĞRENCİ'}</span><div class="student-avatar">${blind?'#':esc(identityName.trim().slice(0,1).toLocaleUpperCase('tr-TR')||'Ö')}</div><div><h3>${esc(identityName)}</h3><p>${identityMeta}</p></div></div><div class="grade-student-metrics"><span><b>${exam.questions.length}</b><small>Toplam soru</small></span><span><b>${classicTotal}</b><small>Klasik</small></span><span><b>${classicReady}/${classicTotal}</b><small>Tarama</small></span></div><div class="student-score"><small>Mevcut puan</small><b>${blind?'—':totalExisting}</b><span>${serial?'Seri puanlama':'Değerlendirme sürüyor'}</span></div>`;document.getElementById('gradeStudentSummary').classList.remove('hidden');
  let questions=exam.questions;if(serial){const qid=selectedGradeQuestionId();questions=questions.filter(q=>q.question_type==='classic'&&q.id===qid);if(!questions.length)questions=exam.questions.filter(q=>q.question_type==='classic').slice(0,1);}
  const html=questions.map(q=>{const r=map.get(q.id)||{};if(q.question_type==='mcq')return `<div class="grade-q modern-grade-q" data-qid="${q.id}" data-type="mcq"><div class="grade-q-head"><span>${q.order_no}</span><div><b>${esc(q.text)}</b><small>${q.points} puan · ${esc(questionOutcomeCodes(q).join(', ')||'Öğrenim Çıktısı yok')}</small></div></div>${gradeChoiceButtons(q,r)}</div>`;const criteria=q.rubric?.criteria||[];const scanPane=classicScanPane(q,scanMap.get(q.id));if(criteria.length){const scores=r.rubric_scores||{};return `<div class="grade-q modern-grade-q classic-grade-card" data-qid="${q.id}" data-type="classic" data-rubric="true" data-max-points="${q.points}"><div class="classic-grade-split">${scanPane}<div class="classic-grade-controls"><div class="grade-q-head"><span>${q.order_no}</span><div><b>${esc(q.text)}</b><small>${q.points} puan · Rubrikli değerlendirme · ${esc(questionOutcomeCodes(q).join(', ')||'Öğrenim Çıktısı yok')}</small></div></div>${q.expected_answer?`<details class="expected-answer"><summary>Beklenen cevap / değerlendirme anahtarı</summary><p>${esc(q.expected_answer)}</p></details>`:''}<div class="rubric-grade-grid premium-rubric-grid">${criteria.map((c,i)=>rubricCriterionHtml(c,scores,i)).join('')}</div><div class="rubric-total"><b>Toplam: ${Number(r.awarded_points||0)} / ${q.points}</b><small>Toplam rubrikten otomatik hesaplanır.</small></div><label class="grader-note">Değerlendirici notu <small>Opsiyonel; yalnız akademik değerlendirme notu yazın.</small><textarea class="ans" rows="3">${esc(r.answer_text||'')}</textarea></label></div></div></div>`;}const current=Number(r.awarded_points||0);const quick=rubricPresetValues(Number(q.points));return `<div class="grade-q modern-grade-q classic-grade-card" data-qid="${q.id}" data-type="classic" data-max-points="${q.points}"><div class="classic-grade-split">${scanPane}<div class="classic-grade-controls"><div class="grade-q-head"><span>${q.order_no}</span><div><b>${esc(q.text)}</b><small>${q.points} puan · ${esc(questionOutcomeCodes(q).join(', ')||'Öğrenim Çıktısı yok')}</small></div></div><div class="classic-score-row"><label>Verilen puan<input class="pts" type="number" min="0" max="${q.points}" step="0.5" value="${current}"></label><div class="quick-score">${quick.map((v,i)=>`<button type="button" data-score="${v}" data-key="${i+1}">${v}</button>`).join('')}</div></div><label class="grader-note">Değerlendirici notu <small>Opsiyonel.</small><textarea class="ans" rows="3">${esc(r.answer_text||'')}</textarea></label></div></div></div>`;}).join('');document.getElementById('gradeQuestions').innerHTML=html||'<div class="empty-state premium-empty grade-empty"><div class="empty-visual">?</div><b>Bu sınavda değerlendirilecek soru yok</b><span>Seri mod için önce sınava rubrikli bir klasik soru ekleyin veya öğrenci bazlı moda dönün.</span></div>';document.getElementById('gradeForm').classList.remove('hidden');document.querySelectorAll('.grade-q[data-rubric="true"]').forEach(updateRubricCardTotal);renderGradeProgress();gradeClassicLiveTotal();document.querySelector('.rubric-pts')?.focus();}catch(e){toast(e.message,'error');}
}
function applyRubricQuick(button){const row=button.closest('.rubric-criterion-card');const input=row?.querySelector('.rubric-pts');if(!input)return;input.value=button.dataset.rubricScore;row.querySelectorAll('.rubric-fast').forEach(b=>b.classList.toggle('active',b===button));updateRubricCardTotal(button.closest('.grade-q'));gradeClassicLiveTotal();input.focus();}
function activeRubricRow(){const focused=document.activeElement?.closest?.('.rubric-criterion-card');return focused||document.querySelector('.rubric-criterion-card');}
document.getElementById('gradeExam').addEventListener('change',loadGradeStudents);
document.getElementById('gradeStudent').addEventListener('change',()=>{renderGradeProgress();if(document.getElementById('gradeForm')&&!document.getElementById('gradeForm').classList.contains('hidden'))loadCurrentGrade();});
document.getElementById('gradeMode').addEventListener('change',()=>{syncGradeModeUI();if(state.currentGradeExam)loadCurrentGrade();});
document.getElementById('gradeQuestion').addEventListener('change',()=>{renderGradeProgress();if(gradeMode()==='question')loadCurrentGrade();});
document.getElementById('gradeBlind').addEventListener('change',()=>{refreshGradeStudentLabels();if(!document.getElementById('gradeForm').classList.contains('hidden'))loadCurrentGrade();});
document.getElementById('loadGrade').addEventListener('click',loadCurrentGrade);
function refreshGradeChoiceState(root,selected){if(!root)return;const correct=root.querySelector('.is-correct-answer')?.dataset.answer||'';root.querySelectorAll('button[data-answer]').forEach(b=>{const chosen=b.dataset.answer===selected&&selected!=='';const wrong=chosen&&correct&&b.dataset.answer!==correct;b.classList.toggle('is-student-selected',chosen);b.classList.toggle('is-wrong-selection',!!wrong);b.classList.toggle('active',b.dataset.answer===''&&selected==='');const labels=[];if(chosen)labels.push('<em class=\"student-answer-tag\">Öğrenci</em>');if(b.dataset.answer===correct&&correct)labels.push('<em class=\"correct-answer-tag\">Doğru</em>');if(wrong)labels.push('<em class=\"wrong-answer-tag\">Yanlış</em>');const slot=b.querySelector('i');if(slot)slot.innerHTML=labels.join('');});}
document.getElementById('gradeQuestions').addEventListener('click',ev=>{const answer=ev.target.closest('[data-answer]');if(answer){const root=answer.closest('.grade-choice-buttons');root.querySelector('.ans').value=answer.dataset.answer;refreshGradeChoiceState(root,answer.dataset.answer);}const rubricQuick=ev.target.closest('[data-rubric-score]');if(rubricQuick){applyRubricQuick(rubricQuick);return;}const score=ev.target.closest('[data-score]');if(score){const q=score.closest('.grade-q');q.querySelector('.pts').value=score.dataset.score;q.querySelectorAll('[data-score]').forEach(b=>b.classList.toggle('active',b===score));gradeClassicLiveTotal();}const scanBtn=ev.target.closest('[data-scan-src]');if(scanBtn){const pane=scanBtn.closest('.classic-scan-pane'),img=pane?.querySelector('.classic-scan-image');if(img)img.src=scanBtn.dataset.scanSrc;pane?.querySelectorAll('[data-scan-src]').forEach(b=>b.classList.toggle('active',b===scanBtn));}});
document.getElementById('gradeQuestions').addEventListener('input',ev=>{if(ev.target.classList.contains('pts')||ev.target.classList.contains('rubric-pts')){gradeClassicLiveTotal();updateRubricCardTotal(ev.target.closest('.grade-q'));if(ev.target.classList.contains('rubric-pts')){const row=ev.target.closest('.rubric-criterion-card'),val=Number(ev.target.value||0);row?.querySelectorAll('.rubric-fast').forEach(b=>b.classList.toggle('active',Math.abs(Number(b.dataset.rubricScore)-val)<.001));}}});
async function saveCurrentGrade(goNext=false){const examId=Number(document.getElementById('gradeExam').value);const studentId=Number(document.getElementById('gradeStudent').value);const responses=[...document.querySelectorAll('.grade-q')].map(el=>{const classic=el.dataset.type==='classic';const rubricInputs=[...el.querySelectorAll('.rubric-pts')];const rubric_scores=rubricInputs.length?Object.fromEntries(rubricInputs.map(x=>[x.dataset.criterion,Number(x.value||0)])):null;return {question_id:Number(el.dataset.qid),answer_text:el.querySelector('.ans')?.value||null,awarded_points:classic&&!rubricInputs.length?Number(el.querySelector('.pts').value):null,rubric_scores};});try{const r=await api('POST',`/api/exams/${examId}/students/${studentId}/responses`,{responses});toast(`${r.saved} cevap kaydedildi.`);if(goNext&&gradeStudentIndex()<(state.gradeStudents||[]).length-1)await moveGradeStudent(1,true);else await loadCurrentGrade();}catch(e){toast(e.message,'error');}}
document.getElementById('gradeForm').addEventListener('submit',async ev=>{ev.preventDefault();await saveCurrentGrade(false);});
document.getElementById('gradeSaveNext').addEventListener('click',()=>saveCurrentGrade(true));
document.getElementById('gradePrev').addEventListener('click',()=>moveGradeStudent(-1,true));
document.getElementById('gradeNext').addEventListener('click',()=>moveGradeStudent(1,true));
document.addEventListener('keydown',ev=>{const page=document.getElementById('page-grade');if(!page?.classList.contains('active')||document.getElementById('gradeForm').classList.contains('hidden'))return;if((ev.ctrlKey||ev.metaKey)&&ev.key==='Enter'){ev.preventDefault();saveCurrentGrade(true);return;}if(ev.altKey&&ev.key==='ArrowRight'){ev.preventDefault();moveGradeStudent(1,true);return;}if(ev.altKey&&ev.key==='ArrowLeft'){ev.preventDefault();moveGradeStudent(-1,true);return;}if(!ev.ctrlKey&&!ev.metaKey&&!ev.altKey&&['1','2','3','4','5'].includes(ev.key)&&!['TEXTAREA','SELECT'].includes(document.activeElement?.tagName)){const row=activeRubricRow();const btn=row?.querySelector(`[data-key="${ev.key}"]`);if(btn){ev.preventDefault();applyRubricQuick(btn);}}});

async function prepareAnalytics(){try{await refreshCore();}catch(e){toast(e.message,'error');}}
function analyticsStatusLabel(status){return status==='achieved'?'Başarılı':'İyileştirme gerekli';}
function analyticsPctBar(value,target=0,label=''){
  const v=Math.max(0,Math.min(100,Number(value)||0));const t=Math.max(0,Math.min(100,Number(target)||0));
  return `<div class="analytics-progress" title="${esc(label)}"><span data-style="width:${v}%"></span>${t?`<i data-style="left:${t}%" title="Hedef %${t}"></i>`:''}</div>`;
}
function analyticsDistributionChart(rows){
  const max=Math.max(1,...(rows||[]).map(x=>Number(x.count)||0));
  return `<div class="distribution-chart">${(rows||[]).map(x=>`<div class="distribution-column"><b>${x.count||0}</b><div class="distribution-bar-track"><span data-style="height:${Math.max(3,(Number(x.count)||0)/max*100)}%"></span></div><small>${esc(x.label)}</small></div>`).join('')}</div>`;
}
function analyticsOutcomeChart(rows){
  if(!rows?.length)return '<div class="empty-state compact"><span>Bu sınavda kazanım verisi yok.</span></div>';
  return `<div class="outcome-chart">${rows.map(x=>`<div class="outcome-chart-row"><div><b>${esc(x.code)}</b><small>${esc(x.description||'')}</small></div><div class="outcome-chart-value"><strong>%${Number(x.attainment_percent||0).toFixed(1)}</strong><span>hedef %${Number(x.target_percent||0).toFixed(1)}</span></div>${analyticsPctBar(x.attainment_percent,x.target_percent,x.code)}</div>`).join('')}</div>`;
}
function analyticsQuestionStatus(x){return x.difficulty_code==='hard'?'risk':x.difficulty_code==='medium'?'watch':'good';}
function renderAnalytics(a){
  state.analyticsData=a;state.analyticsTab='overview';state.analyticsPage=1;state.analyticsPageSize=25;state.analyticsSearch='';
  const sel=a.evidence_selection||{};
  const achieved=(a.learning_outcomes||[]).filter(x=>x.status==='achieved').length;
  const poAchieved=(a.program_outcomes||[]).filter(x=>x.status==='achieved').length;
  const evidenceRows=sel.min?[{slot:'MIN',...sel.min},{slot:'AVG',...sel.average},{slot:'MAX',...sel.max}]:[];
  const hardest=[...(a.question_analysis||[])].sort((x,y)=>Number(x.attainment_percent)-Number(y.attainment_percent)).slice(0,5);
  document.getElementById('analyticsResult').innerHTML=`
    <div class="analytics-sticky-tabs card">
      <div class="analytics-tabs" role="tablist"><button class="active" data-analytics-tab="overview">Genel Bakış</button><button data-analytics-tab="lo">Öğrenim Çıktısı</button><button data-analytics-tab="po">Program Çıktısı</button><button data-analytics-tab="students">Öğrenciler <span>${a.student_count}</span></button><button data-analytics-tab="questions">Sorular <span>${(a.question_analysis||[]).length}</span></button><button data-analytics-tab="evidence">Kanıt</button></div>
    </div>
    <div class="analytics-panel-view active" data-analytics-panel="overview">
      <div class="analytics-kpi-grid">
        <article><span>Sınıf ortalaması</span><b>${a.class_average} / ${a.total_possible_points}</b><small>%${a.class_average_percent}</small></article>
        <article><span>Medyan</span><b>${a.median_score}</b><small>orta öğrenci</small></article>
        <article><span>Standart sapma</span><b>${a.standard_deviation}</b><small>not yayılımı</small></article>
        <article><span>Başarı ≥ %${a.pass_threshold_percent??50}</span><b>%${a.pass_percent}</b><small>${a.pass_count}/${a.student_count} öğrenci</small></article><article><span>Cronbach Alpha</span><b>${a.reliability?.cronbach_alpha??'—'}</b><small>${esc(a.reliability?.interpretation||'veri yetersiz')}</small></article><article><span>KR-20</span><b>${a.reliability?.kr20??'—'}</b><small>${a.problem_question_count||0} problemli soru</small></article>
        <article><span>Başarılı Öğrenim Çıktısı</span><b>${achieved}/${(a.learning_outcomes||[]).length}</b><small>hedef üstü kazanım</small></article>
        <article><span>Başarılı Program Çıktısı</span><b>${poAchieved}/${(a.program_outcomes||[]).length}</b><small>program çıktısı</small></article>
      </div>
      <div class="analytics-chart-grid">
        <article class="analytics-section-card"><div class="section-head"><div><span class="eyebrow">NOT DAĞILIMI</span><h3>Sınıf başarı dağılımı</h3></div><span class="badge">${a.student_count} öğrenci</span></div>${analyticsDistributionChart(a.score_distribution)}</article>
        <article class="analytics-section-card"><div class="section-head"><div><span class="eyebrow">Öğrenim Çıktısı PERFORMANSI</span><h3>Hedefe karşı kazanım</h3></div></div>${analyticsOutcomeChart(a.learning_outcomes)}</article>
      </div>
      <div class="analytics-chart-grid analytics-bottom-grid">
        <article class="analytics-section-card"><div class="section-head"><div><span class="eyebrow">SORU KÖK NEDENİ</span><h3>En zor 5 soru</h3></div><button class="ghost small" data-analytics-tab="questions">Tüm sorular</button></div>${hardest.length?hardest.map(q=>`<div class="analytics-risk-row ${analyticsQuestionStatus(q)}"><span>S${q.order_no}</span><div><b>%${Number(q.attainment_percent).toFixed(1)} başarı · ${esc(q.difficulty)}</b><small>${esc(q.learning_outcome_codes.join(', ')||'Öğrenim Çıktısı bağlanmamış')} · %${q.blank_percent} boş</small></div></div>`).join(''):'<p class="muted">Soru verisi yok.</p>'}</article>
        <article class="analytics-section-card"><div class="section-head"><div><span class="eyebrow">KANIT SEÇİMİ</span><h3>MIN / AVG / MAX</h3></div><button class="ghost small" data-analytics-tab="evidence">Kanıta geç</button></div>${evidenceRows.length?evidenceRows.map(x=>`<div class="evidence-student-row"><span>${x.slot}</span><div><b>${esc(x.full_name)}</b><small>${esc(x.student_no)}</small></div><strong>${x.total_score}</strong></div>`).join(''):'<p class="muted">Öğrenci sonucu yok.</p>'}</article>
      </div>
    </div>
    <div class="analytics-panel-view" data-analytics-panel="lo"><div class="analytics-section-card"><div class="section-head"><div><span class="eyebrow">DERS KAZANIMLARI</span><h3>Öğrenim Çıktısı başarı matrisi</h3><p class="muted">Başarı çubuğu hedef çizgisine ulaşmıyorsa iyileştirme adayıdır.</p></div></div><div class="analytics-outcome-list">${(a.learning_outcomes||[]).map(x=>`<article class="analytics-outcome-card ${x.status==='achieved'?'good':'risk'}"><div class="analytics-outcome-head"><span>${esc(x.code)}</span><div><b>${esc(x.description)}</b><small>${x.question_count} soru · ${x.possible_points} puan kapsamı</small></div><strong>%${Number(x.attainment_percent).toFixed(1)}</strong></div>${analyticsPctBar(x.attainment_percent,x.target_percent)}<div class="analytics-outcome-foot"><span>Hedef %${x.target_percent}</span><b>${analyticsStatusLabel(x.status)}</b><span>Fark ${Number(x.gap_percent)>=0?'+':''}${x.gap_percent} puan</span></div></article>`).join('')}</div></div></div>
    <div class="analytics-panel-view" data-analytics-panel="po"><div class="analytics-section-card"><div class="section-head"><div><span class="eyebrow">PROGRAM KAZANIMLARI</span><h3>Program Çıktısı başarı matrisi</h3></div></div><div class="analytics-outcome-list">${(a.program_outcomes||[]).map(x=>`<article class="analytics-outcome-card ${x.status==='achieved'?'good':'risk'}"><div class="analytics-outcome-head"><span>${esc(x.code)}</span><div><b>${esc(x.description)}</b><small>${(x.contributors||[]).map(c=>`${c.learning_outcome} (${c.contribution})`).join(' · ')||'Katkı tanımsız'}</small></div><strong>%${Number(x.attainment_percent).toFixed(1)}</strong></div>${analyticsPctBar(x.attainment_percent,x.target_percent)}<div class="analytics-outcome-foot"><span>Hedef %${x.target_percent}</span><b>${analyticsStatusLabel(x.status)}</b><span>Fark ${Number(x.gap_percent)>=0?'+':''}${x.gap_percent} puan</span></div></article>`).join('')}</div></div></div>
    <div class="analytics-panel-view" data-analytics-panel="students"><div class="analytics-section-card"><div class="analytics-list-toolbar"><div><span class="eyebrow">ÖĞRENCİLER</span><h3>Öğrenci sonuçları</h3></div><div class="analytics-list-controls"><input id="analyticsStudentSearch" placeholder="No veya ad ara"><select id="analyticsPageSize"><option value="25">25 kişi</option><option value="50">50 kişi</option><option value="100">100 kişi</option></select></div></div><div id="analyticsStudentsTable"></div><div id="analyticsStudentsPager" class="analytics-pager"></div></div></div>
    <div class="analytics-panel-view" data-analytics-panel="questions"><div class="analytics-section-card"><div class="section-head"><div><span class="eyebrow">SORU ANALİZİ</span><h3>Zorluk, boş bırakma ve hedef farkı</h3><p class="muted">Soruları başarı oranına göre inceleyin; bir sorunun birden fazla Öğrenim Çıktısı'ye katkısı birlikte gösterilir.</p></div></div><div class="question-analysis-grid">${(a.question_analysis||[]).map(q=>`<article class="question-analysis-card ${analyticsQuestionStatus(q)}"><div class="question-analysis-head"><span>S${q.order_no}</span><div><b>${esc(q.text)}</b><small>${q.points} puan · ${esc(q.learning_outcome_codes.join(', ')||'Öğrenim Çıktısı yok')}</small></div><strong>%${Number(q.attainment_percent).toFixed(1)}</strong></div>${analyticsPctBar(q.attainment_percent,q.target_percent)}<div class="question-analysis-metrics"><span><b>${q.difficulty}</b>Zorluk</span><span><b>%${q.blank_percent}</b>Boş</span><span><b>${q.discrimination_index==null?'—':Number(q.discrimination_index).toFixed(2)}</b>Ayırt edicilik</span><span><b>${q.point_biserial==null?'—':Number(q.point_biserial).toFixed(2)}</b>Point-biserial</span><span><b>${q.bloom_level||'—'}</b>Bloom</span></div>${(q.quality_flags||[]).length?`<div class="analysis-flags">${q.quality_flags.map(f=>`<span>${esc(f)}</span>`).join('')}</div>`:''}${(q.distractors||[]).length?`<div class="distractor-row">${q.distractors.map(d=>`<span class="${d.is_correct?'correct':''}"><b>${esc(d.choice)}</b> %${d.percent}</span>`).join('')}</div>`:''}</article>`).join('')}</div></div></div>
    <div class="analytics-panel-view" data-analytics-panel="evidence"><div class="analytics-section-card"><div class="section-head"><div><span class="eyebrow">TEMSİLÎ KANIT</span><h3>MIN / AVG / MAX öğrenci seçimi</h3><p class="muted">Akreditasyon kanıtı için sınıfın düşük, ortalamaya en yakın ve yüksek performans temsilcileri.</p></div></div><div class="evidence-selection-grid">${evidenceRows.length?evidenceRows.map(x=>`<article><span>${x.slot}</span><b>${esc(x.full_name)}</b><small>${esc(x.student_no)}</small><strong>${x.total_score} / ${a.total_possible_points}</strong></article>`).join(''):'<div class="empty-state"><span>Kanıt seçimi için öğrenci sonucu yok.</span></div>'}</div></div></div>`;
  switchAnalyticsTab('overview');renderAnalyticsStudents();
}
function switchAnalyticsTab(tab){state.analyticsTab=tab;document.querySelectorAll('[data-analytics-tab]').forEach(b=>b.classList.toggle('active',b.dataset.analyticsTab===tab));document.querySelectorAll('[data-analytics-panel]').forEach(p=>p.classList.toggle('active',p.dataset.analyticsPanel===tab));}
function renderAnalyticsStudents(){
  const a=state.analyticsData;if(!a)return;const box=document.querySelector('#analyticsStudentsTable');if(!box)return;
  const search=String(state.analyticsSearch||'').toLocaleLowerCase('tr-TR');let rows=[...(a.students||[])].sort((x,y)=>Number(x.rank)-Number(y.rank));
  if(search)rows=rows.filter(x=>`${x.student_no} ${x.full_name}`.toLocaleLowerCase('tr-TR').includes(search));
  const size=Number(state.analyticsPageSize||25),pages=Math.max(1,Math.ceil(rows.length/size));state.analyticsPage=Math.min(Math.max(1,Number(state.analyticsPage||1)),pages);const start=(state.analyticsPage-1)*size;const shown=rows.slice(start,start+size);
  box.innerHTML=shown.length?`<div class="analytics-student-table"><div class="analytics-student-table-head"><span>Sıra</span><span>Öğrenci</span><span>Puan</span><span>Başarı</span><span></span></div>${shown.map(x=>`<button type="button" class="analytics-student-table-row" data-analytics-student="${x.exam_student_id}"><span>${x.rank}</span><span><b>${esc(x.full_name)}</b><small>${esc(x.student_no)}</small></span><span><b>${x.total_score}</b><small>/${a.total_possible_points}</small></span><span>${analyticsPctBar(x.score_percent,a.pass_threshold_percent??50)}<small>%${x.score_percent}</small></span><span>Detay →</span></button>`).join('')}</div>`:'<div class="empty-state compact"><span>Aramaya uygun öğrenci bulunamadı.</span></div>';
  const pager=document.querySelector('#analyticsStudentsPager');if(pager)pager.innerHTML=`<span>${rows.length} kayıt · ${state.analyticsPage}/${pages} sayfa</span><div><button class="ghost small" data-analytics-page="prev" ${state.analyticsPage<=1?'disabled':''}>← Önceki</button><button class="ghost small" data-analytics-page="next" ${state.analyticsPage>=pages?'disabled':''}>Sonraki →</button></div>`;
}
async function openAnalyticsStudent(examStudentId){
  const examId=Number(document.getElementById('analyticsExam').value);if(!examId||!examStudentId)return;
  const drawer=document.getElementById('analyticsStudentDrawer'),back=document.getElementById('analyticsDrawerBackdrop'),body=document.getElementById('analyticsStudentDrawerBody');drawer.classList.remove('hidden');back.classList.remove('hidden');body.innerHTML='<div class="loading-state">Öğrenci analizi hazırlanıyor…</div>';
  try{const d=await api('GET',`/api/exams/${examId}/students/${examStudentId}/analytics`);document.getElementById('analyticsStudentDrawerTitle').textContent=`${d.student_no} · ${d.full_name}`;body.innerHTML=`<div class="student-detail-score"><b>${d.total_score} / ${d.total_possible_points}</b><span>%${d.score_percent} başarı</span></div><h4>Öğrenim Çıktısı performansı</h4>${analyticsOutcomeChart(d.learning_outcomes)}<h4>Program Çıktısı performansı</h4>${analyticsOutcomeChart(d.program_outcomes)}<h4>Soru bazlı sonuç</h4><div class="student-question-results">${(d.questions||[]).map(q=>`<div><span>S${q.order_no}</span><div><b>${esc(q.answer_text||'Boş')}</b><small>${esc(q.learning_outcome_codes.join(', ')||'Öğrenim Çıktısı yok')}</small></div><strong>${q.awarded_points}/${q.points}</strong></div>`).join('')}</div>`;}catch(e){body.innerHTML=`<div class="empty-state"><b>Detay açılamadı.</b><span>${esc(e.message)}</span></div>`;}
}
function closeAnalyticsStudent(){document.getElementById('analyticsStudentDrawer')?.classList.add('hidden');document.getElementById('analyticsDrawerBackdrop')?.classList.add('hidden');}
document.getElementById('analyticsResult').addEventListener('click',ev=>{const tab=ev.target.closest('[data-analytics-tab]');if(tab){switchAnalyticsTab(tab.dataset.analyticsTab);return;}const stu=ev.target.closest('[data-analytics-student]');if(stu){openAnalyticsStudent(Number(stu.dataset.analyticsStudent));return;}const pg=ev.target.closest('[data-analytics-page]');if(pg){state.analyticsPage+=(pg.dataset.analyticsPage==='next'?1:-1);renderAnalyticsStudents();}});
document.getElementById('analyticsResult').addEventListener('input',ev=>{if(ev.target.id==='analyticsStudentSearch'){state.analyticsSearch=ev.target.value;state.analyticsPage=1;renderAnalyticsStudents();}});
document.getElementById('analyticsResult').addEventListener('change',ev=>{if(ev.target.id==='analyticsPageSize'){state.analyticsPageSize=Number(ev.target.value);state.analyticsPage=1;renderAnalyticsStudents();}});
document.getElementById('analyticsStudentDrawerClose').addEventListener('click',closeAnalyticsStudent);document.getElementById('analyticsDrawerBackdrop').addEventListener('click',closeAnalyticsStudent);
document.getElementById('loadAnalytics').addEventListener('click',async()=>{
  const id=Number(document.getElementById('analyticsExam').value);if(!id)return toast('Önce sınav seçin.','error');
  try{const a=await api('GET',`/api/exams/${id}/analytics`);renderAnalytics(a);}catch(e){toast(e.message,'error');}
});
document.getElementById('downloadAnalyticsExcel').addEventListener('click',async()=>{
  const id=Number(document.getElementById('analyticsExam').value);if(!id)return toast('Önce sınav seçin.','error');
  try{await downloadApi(`/api/exams/${id}/results.xlsx`,`DOU-Assess-Sinav-${id}-Sonuclar.xlsx`);toast('Excel raporu hazırlandı.');}catch(e){toast(e.message,'error');}
});

async function prepareEvidence(){
  try{await refreshCore();await loadEvidenceStudents();await loadEvidenceList();}catch(e){toast(e.message,'error');}
}
async function loadEvidenceStudents(){const id=Number(document.getElementById('evidenceExam').value);const sel=document.getElementById('evidenceStudent');sel.innerHTML='<option value="">Genel sınav kanıtı</option>';if(!id)return;const rows=await api('GET',`/api/exams/${id}/students`);sel.innerHTML+=rows.map(s=>`<option value="${s.id}">${esc(s.student_no)} · ${esc(s.full_name)}</option>`).join('');}
async function loadEvidenceList(){const id=Number(document.getElementById('evidenceExam').value);const box=document.getElementById('evidenceList');if(!id){box.innerHTML='';return;}const rows=await api('GET',`/api/exams/${id}/evidence`);box.innerHTML=rows.length?rows.map(x=>`<div class="evidence-item"><div><b>${esc(x.kind)} · v${x.version_no||1}</b><span>${esc(x.category||'general')} · ${esc(x.original_name)}</span><small>${x.description?esc(x.description)+' · ':''}${x.retention_until?`saklama: ${esc(x.retention_until)} · `:''}${Math.round(Number(x.size_bytes||0)/1024)} KB · ${esc(x.sha256.slice(0,16))}…</small></div><div class="evidence-item-actions"><button type="button" class="ghost small" data-evidence-preview="${x.id}" data-name="${esc(x.original_name)}">Önizle</button><button type="button" class="ghost small" data-evidence-download="${x.id}" data-name="${esc(x.original_name)}">İndir</button>${isQualityOnly()||canAccreditation()?`<button type="button" class="danger small" data-evidence-delete="${x.id}">Sil</button>`:''}</div></div>`).join(''):'<p class="muted">Henüz kanıt yok.</p>';}
document.getElementById('evidenceExam').addEventListener('change',async()=>{await loadEvidenceStudents();await loadEvidenceList();});
document.getElementById('evidenceForm').addEventListener('submit',async ev=>{ev.preventDefault();const examId=Number(document.getElementById('evidenceExam').value);const file=document.getElementById('evidenceFile').files[0];if(!examId||!file){toast('Sınav ve dosya seçin.','error');return;}const fd=new FormData();fd.append('kind',document.getElementById('evidenceKind').value);fd.append('category',document.getElementById('evidenceCategory').value||'general');fd.append('description',document.getElementById('evidenceDescription').value||'');const retention=document.getElementById('evidenceRetention').value;if(retention)fd.append('retention_until',retention);const sid=document.getElementById('evidenceStudent').value;if(sid)fd.append('student_id',sid);fd.append('file',file);try{await api('POST',`/api/exams/${examId}/evidence`,fd);toast('Kanıt yüklendi.');document.getElementById('evidenceFile').value='';await loadEvidenceList();}catch(e){toast(e.message,'error');}});
document.getElementById('evidenceList')?.addEventListener('click',async ev=>{const p=ev.target.closest('[data-evidence-preview]');if(p){window.open(`/api/evidence/${p.dataset.evidencePreview}/preview`,'_blank','noopener');return;}const d=ev.target.closest('[data-evidence-download]');if(d){try{await downloadApi(`/api/evidence/${d.dataset.evidenceDownload}/download`,d.dataset.name||'kanit');}catch(e){toast(e.message,'error');}return;}const del=ev.target.closest('[data-evidence-delete]');if(del&&confirm('Bu kanıt sürümünü silmek istediğinize emin misiniz?')){try{await api('DELETE',`/api/evidence/${del.dataset.evidenceDelete}`);toast('Kanıt silindi.');await loadEvidenceList();}catch(e){toast(e.message,'error');}}});
document.getElementById('downloadPackage').addEventListener('click',async()=>{const id=Number(document.getElementById('evidenceExam').value);if(!id){toast('Sınav seçin.','error');return;}try{await downloadApi(`/api/exams/${id}/evidence-package`,`sinav-${id}-kanit-paketi.zip`);}catch(e){toast(e.message,'error');}});

function splitKinds(value){return String(value||'').split(',').map(x=>x.trim()).filter(Boolean);}
function accredStatusClass(status){return status==='ready'?'status-approved':status==='archived'?'status-archived':'status-ready';}


function qualityRiskLabel(level){return ({critical:'Kritik',watch:'İzle',no_data:'Ölçülmedi',good:'İyi'})[level]||level||'—';}
function qualityRiskClass(level){return ({critical:'q-critical',watch:'q-watch',no_data:'q-nodata',good:'q-good'})[level]||'q-nodata';}
function qualityPeriodValue(){return document.getElementById('qualityPeriod')?.value||'';}
function qualityQuery(){
  const q=new URLSearchParams();const pv=qualityPeriodValue();
  if(pv){const [y,t]=pv.split('|||');if(y)q.set('academic_year',y);if(t)q.set('term',t);}
  const pid=document.getElementById('qualityProgram')?.value;if(pid)q.set('program_id',pid);
  return q.toString();
}
function qualityKpi(label,value,sub,kind=''){return `<article class="quality-kpi ${kind}"><span>${esc(label)}</span><b>${esc(value)}</b><small>${esc(sub)}</small></article>`;}
async function prepareQuality(){
  if(!canAccreditation()){showPage('dashboard');return;}
  try{await refreshCore();
    const psel=document.getElementById('qualityProgram');const current=psel?.value||'';
    if(psel){psel.innerHTML='<option value="">Tüm programlar</option>'+state.programs.map(x=>`<option value="${x.id}" ${String(x.id)===current?'selected':''}>${esc(x.code)} · ${esc(x.name)}</option>`).join('');}
    await loadQualityDashboard();
  }catch(e){toast(e.message,'error');}
}
async function loadQualityDashboard(){
  const currentPeriod=qualityPeriodValue();const query=qualityQuery();
  const data=await api('GET',`/api/quality/dashboard${query?'?'+query:''}`);state.qualityDashboard=data;
  const f=data.filters||{};const ps=document.getElementById('qualityPeriod');
  if(ps){ps.innerHTML=(f.available_periods||[]).map(x=>`<option value="${esc(x.academic_year)}|||${esc(x.term)}" ${x.academic_year===f.academic_year&&x.term===f.term?'selected':''}>${esc(x.label)}</option>`).join('')||'<option value="">Dönem verisi yok</option>';if(currentPeriod&&(f.available_periods||[]).some(x=>`${x.academic_year}|||${x.term}`===currentPeriod))ps.value=currentPeriod;}
  renderQualityDashboard();
}
function renderQualityDashboard(){
  const d=state.qualityDashboard;if(!d)return;const s=d.summary||{};
  document.getElementById('qualityKpis').innerHTML=[
    qualityKpi('Ölçüm kapsamı',`%${Number(s.measurement_percent||0).toLocaleString('tr-TR')}`,`${s.measured_course_count||0}/${s.course_count||0} ders`),
    qualityKpi('Öğrenim Çıktısı başarı',`%${Number(s.learning_outcome_achievement_percent||0).toLocaleString('tr-TR')}`,`${s.gap_count||0} hedef altı ölçüm`,s.gap_count?'warn':''),
    qualityKpi('Program Çıktısı ortalaması',`%${Number(s.program_outcome_average||0).toLocaleString('tr-TR')}`,`Hedef ort. %${Number(s.program_outcome_target_average||0).toLocaleString('tr-TR')}`),
    qualityKpi('Resmî sınav',s.official_exam_count||0,`${s.exam_count||0} toplam sınav`),
    qualityKpi('Aksiyonsuz açık',s.uncovered_gap_count||0,`${s.open_action_count||0} açık aksiyon`,s.uncovered_gap_count?'danger':''),
    qualityKpi('Riskli ders',s.critical_course_count||0,`${s.critical_program_count||0} program dikkat`,s.critical_course_count?'danger':'')
  ].join('');
  const scope=document.getElementById('qualityScopeBadge');if(scope)scope.textContent=`${d.filters?.academic_year||'—'} ${d.filters?.term||''} · ${s.program_count||0} program`;
  renderQualityHeatmap();renderQualityRisks();renderQualityTrend();
}
function renderQualityHeatmap(){
  const d=state.qualityDashboard||{};const box=document.getElementById('qualityHeatmap');const codes=d.program_outcome_codes||[];const rows=d.program_heatmap||[];
  if(!rows.length){box.innerHTML='<div class="empty-state"><b>Bu dönemde kalite verisi yok.</b><span>Onaylanmış sınavlar oluştuğunda Program Çıktısı heatmap burada hesaplanır.</span></div>';return;}
  const head=codes.map(c=>`<th>${esc(c)}</th>`).join('');
  box.innerHTML=`<table class="quality-heatmap"><thead><tr><th>Program</th>${head}<th>Durum</th></tr></thead><tbody>${rows.map(r=>{const prog=(d.programs||[]).find(x=>x.program_id===r.program_id)||{};return `<tr><th><b>${esc(r.program_code)}</b><span>${esc(r.program_name)}</span></th>${(r.cells||[]).map(cell=>{if(!cell)return '<td class="q-nodata"><b>—</b><small>Ölçülmedi</small></td>';const cls=cell.status==='achieved'?'q-good':Number(cell.gap_points)>=10?'q-critical':'q-watch';return `<td class="${cls}" title="Hedef %${esc(cell.target_percent)} · Fark ${esc(cell.gap_points)}"><b>%${Number(cell.attainment_percent).toLocaleString('tr-TR')}</b><small>Hedef %${Number(cell.target_percent).toLocaleString('tr-TR')}</small></td>`;}).join('')}<td><span class="quality-status ${esc(prog.status||'incomplete')}">${esc(({good:'İyi',watch:'İzle',critical:'Kritik',incomplete:'Eksik ölçüm'})[prog.status]||prog.status||'—')}</span></td></tr>`}).join('')}</tbody></table>`;
}
function renderQualityRisks(){
  const rows=state.qualityDashboard?.risk_courses||[];const risk=rows.filter(x=>x.risk_level!=='good');const box=document.getElementById('qualityRisks');const badge=document.getElementById('qualityRiskBadge');badge.textContent=`${risk.length} öncelik`;
  const shown=(risk.length?risk:rows).slice(0,20);box.innerHTML=shown.length?shown.map(x=>`<button class="quality-risk-row ${qualityRiskClass(x.risk_level)}" data-action-call="openQualityCourse(${x.course_id})"><span class="risk-dot"></span><div class="risk-main"><b>${esc(x.course_code)} · ${esc(x.course_name)}</b><small>${esc(x.program_code)} · ${esc(x.instructor||'Öğretim elemanı atanmadı')}</small></div><div class="risk-numbers"><b>${x.risk_level==='no_data'?'—':`-${Number(x.max_gap_points||0).toLocaleString('tr-TR')} puan`}</b><small>${x.gap_count||0} açık Öğrenim Çıktısı</small></div><span class="quality-risk-pill">${qualityRiskLabel(x.risk_level)}</span><i>→</i></button>`).join(''):'<div class="empty-state"><b>Riskli ders görünmüyor.</b><span>Seçili kapsamda ders verisi yok.</span></div>';
}
function renderQualityTrend(){
  const rows=state.qualityDashboard?.trend||[];const box=document.getElementById('qualityTrend');if(!rows.length){box.innerHTML='<div class="empty-state"><b>Karşılaştırılacak dönem yok.</b><span>Birden fazla dönem verisi geldiğinde trend oluşur.</span></div>';return;}
  box.innerHTML=`<div class="quality-trend-list">${rows.map(x=>`<div class="quality-trend-row"><div><b>${esc(x.label)}</b><small>${x.official_exam_count} resmî sınav · ölçüm %${Number(x.measurement_percent).toLocaleString('tr-TR')}</small></div><div class="trend-bars"><span><i data-style="width:${Math.max(0,Math.min(100,x.learning_outcome_achievement_percent))}%"></i></span><b>Öğrenim Çıktısı %${Number(x.learning_outcome_achievement_percent).toLocaleString('tr-TR')}</b><span><i data-style="width:${Math.max(0,Math.min(100,x.program_outcome_average))}%"></i></span><b>Program Çıktısı %${Number(x.program_outcome_average).toLocaleString('tr-TR')}</b></div></div>`).join('')}</div>`;
}
async function openQualityCourse(courseId){
  try{state.qualityLoFilter=null;state.qualityDrilldown=await api('GET',`/api/quality/courses/${courseId}/drilldown`);renderQualityDrilldown();document.getElementById('qualityDrilldown')?.scrollIntoView({behavior:'smooth',block:'start'});}catch(e){toast(e.message,'error');}
}
function setQualityLoFilter(code){state.qualityLoFilter=state.qualityLoFilter===code?null:code;renderQualityDrilldown();}
function renderQualityDrilldown(){
  const d=state.qualityDrilldown;const box=document.getElementById('qualityDrilldown');if(!d||!box)return;box.classList.remove('hidden');const c=d.course,s=d.summary;const filter=state.qualityLoFilter;
  const questions=(d.questions||[]).filter(q=>!filter||questionOutcomeCodes(q).includes(filter));
  box.innerHTML=`<div class="quality-drill-head"><div><span class="eyebrow">DERS → Öğrenim Çıktısı → SORU</span><h3>${esc(c.code)} · ${esc(c.name)}</h3><p>${esc(c.program_code)} · ${esc(c.program_name)} · ${esc(c.instructor_name||c.instructor_email||'Öğretim elemanı atanmadı')}</p></div><button class="ghost small" data-action-call="hideQualityDrilldown()">Kapat ×</button></div><div class="quality-drill-kpis">${qualityKpi('Resmî sınav',s.official_exam_count,`${s.exam_count} toplam`)}${qualityKpi('Sınıf ort.',`%${Number(s.class_average||0).toLocaleString('tr-TR')}`,'onaylı sınavlar')}${qualityKpi('Açık Öğrenim Çıktısı',s.learning_outcome_gap_count,`${s.learning_outcome_count} ölçülen`)}${qualityKpi('Riskli soru',s.question_risk_count,`${s.unmapped_question_count} Öğrenim Çıktısı’siz`)}</div><div class="quality-drill-grid"><div><div class="section-head"><div><h4>Öğrenim Çıktısı performansı</h4><p class="muted">Bir Öğrenim Çıktısı’ye tıklayarak soru listesini süzün.</p></div>${filter?`<button class="ghost small" data-action-call="setQualityLoFilter('${esc(filter)}')">Filtreyi temizle</button>`:''}</div><div class="quality-lo-list">${(d.learning_outcomes||[]).map(lo=>`<button class="quality-lo-row ${lo.status==='achieved'?'q-good':Number(lo.gap_points)>=10?'q-critical':'q-watch'} ${filter===lo.code?'selected':''}" data-action-call="setQualityLoFilter('${esc(lo.code)}')"><div><b>${esc(lo.code)}</b><span>${esc(lo.description)}</span></div><div class="lo-progress"><span><i data-style="width:${Math.max(0,Math.min(100,lo.attainment_percent))}%"></i></span><small>%${Number(lo.attainment_percent).toLocaleString('tr-TR')} / hedef %${Number(lo.target_percent).toLocaleString('tr-TR')}</small></div></button>`).join('')||'<p class="muted">Öğrenim Çıktısı ölçümü yok.</p>'}</div></div><div><div class="section-head"><div><h4>${filter?esc(filter)+' soruları':'Soru kök neden analizi'}</h4><p class="muted">En büyük başarı farkı üstte gösterilir.</p></div></div><div class="quality-question-list">${questions.map(q=>`<article class="quality-question ${q.status==='needs_improvement'?'q-critical':q.status==='unmapped'?'q-nodata':'q-good'}"><div class="question-quality-top"><span>S${q.order_no} · ${esc(q.exam_title)}</span><b>%${Number(q.attainment_percent).toLocaleString('tr-TR')}</b></div><p>${esc(q.text)}</p><div class="question-quality-meta"><span>${esc(questionOutcomeCodes(q).join(', ')||'Öğrenim Çıktısı yok')}</span><span>${q.points} puan</span>${q.target_percent!==null?`<span>Hedef %${Number(q.target_percent).toLocaleString('tr-TR')}</span>`:''}${q.gap_points>0?`<strong>-${Number(q.gap_points).toLocaleString('tr-TR')} puan</strong>`:''}<button class="ghost tiny" data-action-call="openAccredExam(${q.exam_id})">Sınav analizi →</button></div></article>`).join('')||'<div class="empty-state"><b>Bu filtrede soru yok.</b><span>Başka bir Öğrenim Çıktısı seçin.</span></div>'}</div></div></div><div class="quality-exam-strip">${(d.exams||[]).map(e=>`<button data-action-call="openAccredExam(${e.exam_id})"><b>${esc(e.title)}</b><span>${esc(e.exam_type)} · ${esc(e.exam_date||'')}</span><small>Ort. %${Number(e.class_average).toLocaleString('tr-TR')} · Program Çıktısı %${Number(e.program_outcome_average).toLocaleString('tr-TR')}</small></button>`).join('')}</div>`;
}
document.getElementById('qualityRefresh')?.addEventListener('click',()=>loadQualityDashboard().catch(e=>toast(e.message,'error')));
document.getElementById('qualityProgram')?.addEventListener('change',()=>loadQualityDashboard().catch(e=>toast(e.message,'error')));
document.getElementById('qualityPeriod')?.addEventListener('change',()=>loadQualityDashboard().catch(e=>toast(e.message,'error')));
document.getElementById('qualityExcel')?.addEventListener('click',()=>{const q=qualityQuery();downloadApi(`/api/quality/dashboard.xlsx${q?'?'+q:''}`,'DOU-Assess-Yonetim-Kalite.xlsx').catch(e=>toast(e.message,'error'));});

async function prepareAccreditation(){
  try{
    await refreshCore();
    const [profiles,periods]=await Promise.all([api('GET','/api/accreditation/profiles'),api('GET','/api/accreditation/periods')]);
    state.accredProfiles=profiles;state.accredPeriods=periods;
    document.getElementById('accredProgram').innerHTML=state.programs.map(p=>`<option value="${p.id}">${esc(p.code)} · ${esc(p.name)}</option>`).join('')||'<option value="">Program yok</option>';
    document.getElementById('accredProfile').innerHTML=profiles.map(p=>`<option value="${p.id}">${esc(p.code)} · ${esc(p.name)} · ${esc(p.version)}</option>`).join('')||'<option value="">Önce profil oluşturun</option>';
    document.getElementById('accredPeriodSelect').innerHTML=periods.map(x=>`<option value="${x.id}">${esc(x.title)} · ${esc(x.status)}</option>`).join('')||'<option value="">Dönem yok</option>';
    if(periods.length) await loadAccredDashboard(); else {document.getElementById('accredSummary').innerHTML='<p class="muted">Henüz akreditasyon dönemi oluşturulmadı.</p>';document.getElementById('accredExams').innerHTML='';}
  }catch(e){toast(e.message,'error');}
}

document.getElementById('accredProfileForm').addEventListener('submit',async ev=>{
  ev.preventDefault();
  const payload={
    code:document.getElementById('accredProfileCode').value.trim(),name:document.getElementById('accredProfileName').value.trim(),version:document.getElementById('accredProfileVersion').value.trim(),
    required_general_evidence_kinds:splitKinds(document.getElementById('accredGeneralKinds').value),required_representative_evidence_kinds:splitKinds(document.getElementById('accredRepKinds').value),
    requires_representatives:document.getElementById('accredRequireReps').checked,requires_improvement_for_gaps:document.getElementById('accredRequireActions').checked
  };
  try{await api('POST','/api/accreditation/profiles',payload);toast('Akreditasyon profili oluşturuldu.');document.getElementById('accredProfileForm').reset();document.getElementById('accredRepKinds').value='answer_sheet';document.getElementById('accredRequireReps').checked=true;document.getElementById('accredRequireActions').checked=true;await prepareAccreditation();}catch(e){toast(e.message,'error');}
});

document.getElementById('accredPeriodForm').addEventListener('submit',async ev=>{
  ev.preventDefault();
  const program_id=Number(document.getElementById('accredProgram').value),profile_id=Number(document.getElementById('accredProfile').value),academic_year=document.getElementById('accredYear').value.trim(),term=document.getElementById('accredTerm').value,title=document.getElementById('accredTitle').value.trim();
  if(!program_id||!profile_id||!academic_year||!title)return toast('Program, profil, akademik yıl ve dönem adı zorunludur.','error');
  try{await api('POST','/api/accreditation/periods',{program_id,profile_id,academic_year,term,title});toast('Akreditasyon dönemi oluşturuldu.');await prepareAccreditation();}catch(e){toast(e.message,'error');}
});

async function loadAccredDashboard(){
  const id=Number(document.getElementById('accredPeriodSelect').value);if(!id)return;
  try{
    const d=await api('GET',`/api/accreditation/periods/${id}/dashboard`);state.accredDashboard=d;
    const badge=document.getElementById('accredPeriodBadge');badge.textContent=`${d.period.status} · ${d.profile.code} ${d.profile.version}`;badge.className=`badge ${accredStatusClass(d.period.status)}`;
    const s=d.summary;const pct=s.exam_count?Math.round((s.complete_exam_count/s.exam_count)*100):(s.ready?100:0);document.getElementById('accredProgressFill').style.width=`${Math.min(100,pct)}%`;document.getElementById('accredProgressText').innerHTML=`<b>%${pct}</b> paket hazırlığı · ${s.complete_exam_count}/${s.exam_count} sınav tamam`;
    document.getElementById('accredContext').innerHTML=`<span>${esc(d.program?.code||'')} · ${esc(d.program?.name||'')}</span><span>${esc(d.period.academic_year)} · ${esc(d.period.term)}</span><span>${esc(d.profile.name)} · ${esc(d.profile.version)}</span>`;
    document.getElementById('accredSummary').innerHTML=`<div class="accred-summary modern-accred-summary"><div class="metric"><span>Ders</span><div>${s.course_count}</div></div><div class="metric"><span>Sınav</span><div>${s.exam_count}</div></div><div class="metric ok-metric"><span>Tamamlanan</span><div>${s.complete_exam_count}</div></div><div class="metric ${s.warning_count?'warn-metric':'ok-metric'}"><span>Açık uyarı</span><div>${s.warning_count}</div></div><div class="metric"><span>Genel durum</span><div class="${s.ready?'pill-ok':'pill-warn'}">${s.ready?'PAKETE HAZIR':'ÇALIŞILIYOR'}</div></div></div>`;
    renderAccredKpis(d);renderAccredMatrix(d);renderAccredGaps(d);renderAccredRepresentatives(d);renderAccredActions(d);
    document.getElementById('accredCourses').innerHTML=d.courses.length?d.courses.map(c=>{const cp=c.exam_count?Math.round(c.complete_exam_count/c.exam_count*100):0;const loPct=c.lo_measurement_count?Math.round(c.lo_achieved_count/c.lo_measurement_count*100):0;return `<div class="accred-course modern-course-row ${c.measurement_status==='no_exam'?'course-unmeasured':''}"><div class="course-circle">${c.exam_count?`${cp}%`:'—'}</div><div class="course-row-main"><b>${esc(c.course_code)} · ${esc(c.course_name)}</b><span>${esc(c.instructor||'Öğretim elemanı atanmadı')} · ${c.exam_count} sınav · Öğrenim Çıktısı başarı %${loPct}</span><div class="mini-progress"><span data-style="width:${cp}%"></span></div></div><span class="${c.measurement_status==='no_exam'||c.warning_count?'pill-warn':'pill-ok'}">${c.measurement_status==='no_exam'?'ölçüm yok':c.warning_count?`${c.warning_count} eksik`:'tamam'}</span></div>`}).join(''):'<div class="empty-state"><b>Ders bulunamadı.</b><span>Programın bu akademik yıl/dönem derslerini kontrol edin.</span></div>';
    renderAccredExams(d.exams);
  }catch(e){toast(e.message,'error');}
}

function accredPct(value){return Number.isFinite(Number(value))?Number(value).toFixed(1):'0.0';}
function renderAccredKpis(d){
  const s=d.summary;const rows=[
    ['Öğrenim Çıktısı başarı oranı',`%${accredPct(s.lo_achievement_percent)}`,`${s.lo_achieved_count}/${s.lo_measurement_count} ölçüm`,'target'],
    ['Program Çıktısı dönem ortalaması',`%${accredPct(s.program_outcome_average)}`,`${s.program_outcomes?.length||d.program_outcomes.length} Program Çıktısı`,'matrix'],
    ['Başarısız Öğrenim Çıktısı',s.gap_count,`${s.uncovered_gap_count} aksiyonsuz`,'gap'],
    ['Aksiyon kapsamı',`%${accredPct(s.gap_action_coverage_percent)}`,`${s.improvement_action_count} aktif aksiyon`,'action'],
    ['MIN/AVG/MAX kanıt',`%${accredPct(s.representative_evidence_percent)}`,`${s.representative_frozen_exam_count}/${s.representative_required_exam_count} sınav donduruldu`,'evidence'],
    ['Ölçülmemiş ders',s.unmeasured_course_count,s.unmeasured_course_count?'Dönem kapsamını kontrol edin':'Tüm derslerde ölçüm var','course'],
  ];
  document.getElementById('accredKpis').innerHTML=rows.map(([label,value,note,kind])=>`<div class="card accred-kpi ${kind}"><span>${esc(label)}</span><b>${esc(value)}</b><small>${esc(note)}</small></div>`).join('');
}

function renderAccredMatrix(d){
  const po=d.program_outcomes||[],courses=d.courses||[];const wrap=document.getElementById('accredMatrix');
  document.getElementById('accredPoLegend').innerHTML=po.length?po.map(x=>`<span class="${x.status==='achieved'?'matrix-ok':'matrix-warn'}"><b>${esc(x.code)}</b> %${accredPct(x.attainment_percent)} <small>/ hedef %${accredPct(x.target_percent)}</small></span>`).join(''):'<span class="muted">Program Çıktısı ölçümü yok</span>';
  if(!courses.length||!po.length){wrap.innerHTML='<div class="empty-state"><b>Matris için ölçüm verisi yok.</b><span>Derslerde Öğrenim Çıktısı↔Program Çıktısı eşleştirmesi ve onaylanmış sınav sonucu bulunmalıdır.</span></div>';return;}
  const head=`<tr><th>Ders</th><th>Sınav</th>${po.map(x=>`<th title="${esc(x.description)}">${esc(x.code)}</th>`).join('')}</tr>`;
  const body=courses.map(c=>`<tr><td><b>${esc(c.course_code)}</b><span>${esc(c.course_name)}</span></td><td>${c.exam_count||'—'}</td>${po.map(p=>{const cell=(c.po||{})[p.code];if(!cell)return '<td><span class="matrix-empty">—</span></td>';return `<td><span class="matrix-cell ${cell.status==='achieved'?'achieved':'needs'}"><b>%${accredPct(cell.attainment_percent)}</b><small>H ${accredPct(cell.target_percent)}</small></span></td>`;}).join('')}</tr>`).join('');
  wrap.innerHTML=`<table class="accred-matrix"><thead>${head}</thead><tbody>${body}</tbody></table>`;
}

function renderAccredGaps(d){
  const rows=d.gap_register||[];const badge=document.getElementById('accredGapBadge');badge.textContent=`${rows.length} açık`;badge.className=`badge ${rows.length?'status-ready':'status-approved'}`;
  document.getElementById('accredGaps').innerHTML=rows.length?rows.slice(0,12).map(x=>`<div class="accred-gap-row"><div class="gap-score"><b>-${accredPct(x.gap_points)}</b><small>puan</small></div><div class="gap-copy"><b>${esc(x.course_code)} · ${esc(x.outcome_code)}</b><span>${esc(x.description)}</span><small>${esc(x.exam_title)} · hedef %${accredPct(x.target_percent)} / gerçekleşen %${accredPct(x.attainment_percent)}</small></div><span class="${x.has_action?'pill-ok':'pill-warn'}">${x.has_action?'aksiyon bağlı':'aksiyon gerekli'}</span><button class="ghost small" data-action-call="openAccredExam(${x.exam_id})">Sınavı aç</button></div>`).join(''):'<div class="success-panel">Bu dönemde hedef altında kalan Öğrenim Çıktısı bulunmuyor.</div>';
}

function renderAccredRepresentatives(d){
  const rows=d.representative_register||[],s=d.summary;const badge=document.getElementById('accredRepBadge');badge.textContent=`%${accredPct(s.representative_evidence_percent)}`;badge.className=`badge ${s.representative_evidence_percent>=100?'status-approved':'status-ready'}`;
  document.getElementById('accredRepresentatives').innerHTML=rows.length?rows.slice(0,15).map(x=>`<div class="accred-rep-row"><span class="rep-slot ${x.slot.toLowerCase()}">${esc(x.slot)}</span><div><b>${esc(x.student_no)} · ${esc(x.full_name)}</b><span>${esc(x.course_code)} · ${esc(x.exam_title)}</span><small>Not ${accredPct(x.total_score)} · sınıf ort. ${accredPct(x.class_average)}</small></div><span class="${x.evidence_complete?'pill-ok':'pill-warn'}">${x.evidence_complete?'kanıt tamam':`${x.missing_evidence.length} eksik`}</span><button class="ghost small" data-action-call="openEvidenceExam(${x.exam_id})">Kanıt</button></div>`).join(''):`<div class="action-needed">Henüz dondurulmuş MIN/AVG/MAX seçimi yok. “MIN/AVG/MAX dondur” ile onaylı sınavları toplu hazırlayabilirsiniz.</div>`;
}

function renderAccredActions(d){
  const rows=d.improvement_register||[];document.getElementById('accredActionBadge').textContent=`${rows.length} aksiyon`;
  document.getElementById('accredActions').innerHTML=rows.length?`<div class="accred-action-table"><div class="accred-action-head"><span>Ders / Öğrenim Çıktısı</span><span>Aksiyon</span><span>Sorumlu</span><span>Termin</span><span>Durum</span><span></span></div>${rows.map(a=>`<div class="accred-action-row"><span><b>${esc(a.course_code)}</b><small>${esc(a.outcome_code)} · ${esc(a.exam_title)}</small></span><span>${esc(a.action_text)}</span><input id="imp-owner-${a.id}" value="${esc(a.owner||'')}" placeholder="Sorumlu"><input id="imp-due-${a.id}" type="date" value="${esc(a.due_date||'')}"><select id="imp-status-${a.id}" class="mini-status"><option value="open" ${a.status==='open'?'selected':''}>Açık</option><option value="in_progress" ${a.status==='in_progress'?'selected':''}>Devam</option><option value="done" ${a.status==='done'?'selected':''}>Tamam</option><option value="cancelled" ${a.status==='cancelled'?'selected':''}>İptal</option></select><button class="ghost small" data-action-call="saveImprovement(${a.id})">Kaydet</button></div>`).join('')}</div>`:'<div class="empty-state"><b>Henüz iyileştirme aksiyonu yok.</b><span>Başarısız Öğrenim Çıktısı bulunan sınavı açarak aksiyon tanımlayın.</span></div>';
}

function renderAccredExams(rows){
  const box=document.getElementById('accredExams');
  box.innerHTML=rows.length?rows.map(x=>{const reps=x.representatives||[];const repHtml=reps.length?`<div class="rep-grid">${reps.map(r=>`<div class="rep-card"><b>${esc(r.slot)}</b><span>${esc(r.student_no)} · ${esc(r.full_name)}</span><small>Not ${r.total_score} · Ort ${r.class_average}</small></div>`).join('')}</div>`:'<div class="action-needed">MIN/AVG/MAX temsilcileri henüz dondurulmadı.</div>';const improvements=(x.improvements||[]).map(a=>`<div class="improvement-row"><b>${esc(a.outcome_code)}</b><span>${esc(a.action_text)}</span><span>${esc(a.owner||'Sorumlu yok')}</span><span>${esc(a.due_date||'Termin yok')}</span><span class="${a.status==='done'?'pill-ok':'pill-warn'}">${esc(a.status)}</span></div>`).join('');const gapOpts=(x.improvement_gap_codes||[]).map(code=>`<option>${esc(code)}</option>`).join('');const add=gapOpts?`<div class="improvement-add"><label>Öğrenim Çıktısı<select id="new-imp-code-${x.exam_id}">${gapOpts}</select></label><label>Aksiyon<input id="new-imp-text-${x.exam_id}" placeholder="Bir sonraki uygulamada yapılacak iyileştirme"></label><label>Sorumlu<input id="new-imp-owner-${x.exam_id}"></label><label>Termin<input id="new-imp-due-${x.exam_id}" type="date"></label><button class="primary small" data-action-call="addImprovement(${x.exam_id})">Aksiyon ekle</button></div>`:'';return `<details class="accred-exam modern-accred-exam ${x.complete?'complete':'warn'}" ${x.complete?'':'open'}><summary><div><span class="badge ${x.complete?'status-approved':'status-ready'}">${x.complete?'TAMAM':`${x.warning_count} EKSİK`}</span><b>${esc(x.course_code)} · ${esc(x.title)}</b><small>${esc(x.exam_type)} · ${x.student_count} öğrenci · Ort ${x.class_average} · Öğrenim Çıktısı ${x.lo_achieved}/${x.lo_total} · Program Çıktısı ${x.po_achieved}/${x.po_total}</small></div><span class="summary-arrow">⌄</span></summary><div class="accred-exam-body">${x.warnings.length?`<div class="warning-panel"><b>Tamamlanması gerekenler</b><ul>${x.warnings.map(w=>`<li>${esc(w)}</li>`).join('')}</ul></div>`:'<div class="success-panel">Bu sınav akreditasyon açısından tamamlandı.</div>'}<div class="actions"><button class="ghost small" data-action-call="freezeRepresentatives(${x.exam_id})">MIN/AVG/MAX dondur</button><button class="ghost small" data-action-call="openEvidenceExam(${x.exam_id})">Kanıtları aç</button><button class="ghost small" data-action-call="openAccredExam(${x.exam_id})">Analizi aç</button></div><h4>Temsilci öğrenciler</h4>${repHtml}${improvements?`<h4>İyileştirme aksiyonları</h4>${improvements}`:''}${add}</div></details>`;}).join(''):'<div class="empty-state"><b>Bu döneme bağlı sınav yok.</b><span>“Sınavları eşitle” ile dönem derslerindeki sınavları bağlayın.</span></div>';
}

function openAccredExam(examId){showPage('analytics');document.getElementById('analyticsExam').value=String(examId);document.getElementById('loadAnalytics').click();}

async function freezeRepresentatives(examId){try{await api('POST',`/api/exams/${examId}/representatives/freeze`,{});toast('MIN/AVG/MAX seçimi donduruldu.');await loadAccredDashboard();}catch(e){toast(e.message,'error');}}
async function addImprovement(examId){const outcome_code=document.getElementById(`new-imp-code-${examId}`).value,action_text=document.getElementById(`new-imp-text-${examId}`).value.trim(),owner=document.getElementById(`new-imp-owner-${examId}`).value.trim(),due_date=document.getElementById(`new-imp-due-${examId}`).value||null;if(!action_text)return toast('Aksiyon metni zorunludur.','error');try{await api('POST',`/api/exams/${examId}/improvements`,{outcome_code,action_text,owner,due_date});toast('İyileştirme aksiyonu eklendi.');await loadAccredDashboard();}catch(e){toast(e.message,'error');}}
async function saveImprovement(id){try{await api('PATCH',`/api/improvements/${id}`,{owner:document.getElementById(`imp-owner-${id}`).value,due_date:document.getElementById(`imp-due-${id}`).value||null,status:document.getElementById(`imp-status-${id}`).value});toast('İyileştirme güncellendi.');await loadAccredDashboard();}catch(e){toast(e.message,'error');}}
function openEvidenceExam(examId){showPage('evidence');document.getElementById('evidenceExam').value=String(examId);loadEvidenceStudents();loadEvidenceList();}

document.getElementById('accredLoad').addEventListener('click',loadAccredDashboard);
document.getElementById('accredPeriodSelect').addEventListener('change',loadAccredDashboard);
document.getElementById('accredSync').addEventListener('click',async()=>{const id=Number(document.getElementById('accredPeriodSelect').value);if(!id)return;try{const r=await api('POST',`/api/accreditation/periods/${id}/sync-exams`,{});toast(`${r.added} yeni sınav bağlandı.`);await loadAccredDashboard();}catch(e){toast(e.message,'error');}});
document.getElementById('accredFreezeAll').addEventListener('click',async()=>{const id=Number(document.getElementById('accredPeriodSelect').value);if(!id)return toast('Dönem seçin.','error');try{const r=await api('POST',`/api/accreditation/periods/${id}/representatives/freeze-all`,{});toast(`${r.frozen_count} sınav için MIN/AVG/MAX donduruldu${r.skipped?.length?` · ${r.skipped.length} sınav atlandı`:''}.`);await loadAccredDashboard();}catch(e){toast(e.message,'error');}});
document.getElementById('accredExcel').addEventListener('click',async()=>{const id=Number(document.getElementById('accredPeriodSelect').value);if(!id)return toast('Dönem seçin.','error');try{await downloadApi(`/api/accreditation/periods/${id}/report.xlsx`,`DOU-Assess-Akreditasyon-${id}.xlsx`);toast('Dönem değerlendirme Excel raporu hazırlandı.');}catch(e){toast(e.message,'error');}});
document.getElementById('accredReady').addEventListener('click',async()=>{const id=Number(document.getElementById('accredPeriodSelect').value);if(!id)return;try{await api('POST',`/api/accreditation/periods/${id}/status`,{status:'ready'});toast('Akreditasyon dönemi hazır olarak işaretlendi.');await prepareAccreditation();}catch(e){toast(e.message,'error');}});
document.getElementById('accredArchive').addEventListener('click',async()=>{const id=Number(document.getElementById('accredPeriodSelect').value);if(!id)return;try{await api('POST',`/api/accreditation/periods/${id}/status`,{status:'archived'});toast('Akreditasyon dönemi arşivlendi.');await prepareAccreditation();}catch(e){toast(e.message,'error');}});
document.getElementById('accredDownload').addEventListener('click',async()=>{const id=Number(document.getElementById('accredPeriodSelect').value);if(!id)return toast('Dönem seçin.','error');try{await downloadApi(`/api/accreditation/periods/${id}/evidence-package`,`akreditasyon-donem-${id}.zip`);}catch(e){toast(e.message,'error');}});


function base64Url(bytes){return btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');}
function randomVerifier(size=64){const bytes=new Uint8Array(size);crypto.getRandomValues(bytes);return base64Url(bytes);}
async function pkceChallenge(verifier){return base64Url(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier)));}
function entraRedirectUri(){const configured=state.authConfig?.entra?.redirect_uri;return configured||`${location.origin}${location.pathname}`;}
async function startEntraLogin(){
  const e=state.authConfig?.entra||{};if(!e.configured||!e.tenant_id||!e.client_id)return toast('Microsoft Entra tenant/client ayarları henüz tamamlanmadı.','error');
  if(!e.login_scopes?.length)return toast('ENTRA_LOGIN_SCOPES yapılandırması eksik.','error');
  const verifier=randomVerifier();const challenge=await pkceChallenge(verifier);const oauthState=randomVerifier(24);const nonce=randomVerifier(24);
  sessionStorage.setItem('douPkceVerifier',verifier);sessionStorage.setItem('douOauthState',oauthState);sessionStorage.setItem('douOauthNonce',nonce);
  const scope=['openid','profile','email',...e.login_scopes].filter((v,i,a)=>a.indexOf(v)===i).join(' ');
  const q=new URLSearchParams({client_id:e.client_id,response_type:'code',redirect_uri:entraRedirectUri(),response_mode:'query',scope,state:oauthState,nonce,code_challenge:challenge,code_challenge_method:'S256',prompt:'select_account'});
  location.assign(`${e.authority}/oauth2/v2.0/authorize?${q.toString()}`);
}
async function handleEntraCallback(){
  const q=new URLSearchParams(location.search);if(q.get('error')){const msg=q.get('error_description')||q.get('error');history.replaceState({},document.title,location.pathname);throw new Error(`Microsoft Entra: ${msg}`);}const code=q.get('code');if(!code)return false;
  state.authConfig=await api('GET','/api/auth/config');applyObsIntegrationPolicy();const e=state.authConfig?.entra||{};const expected=sessionStorage.getItem('douOauthState');if(!expected||q.get('state')!==expected)throw new Error('Microsoft Entra state doğrulaması başarısız.');const verifier=sessionStorage.getItem('douPkceVerifier');if(!verifier)throw new Error('PKCE doğrulayıcı bulunamadı. Girişi yeniden başlatın.');
  const scope=['openid','profile','email',...(e.login_scopes||[])].filter((v,i,a)=>a.indexOf(v)===i).join(' ');const form=new URLSearchParams({client_id:e.client_id,grant_type:'authorization_code',code,redirect_uri:entraRedirectUri(),code_verifier:verifier,scope});
  const r=await fetch(`${e.authority}/oauth2/v2.0/token`,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:form});const data=await r.json();if(!r.ok||!data.access_token)throw new Error(data.error_description||'Microsoft Entra access token alınamadı.');sessionStorage.setItem('douEntraAccessToken',data.access_token);sessionStorage.removeItem('douPkceVerifier');sessionStorage.removeItem('douOauthState');sessionStorage.removeItem('douOauthNonce');history.replaceState({},document.title,location.pathname);return true;
}

function currentPageName(){return document.querySelector('.page.active')?.id?.replace('page-','')||'dashboard';}
function feedbackStatusLabel(s){return ({open:'Açık',reviewed:'İnceleniyor',resolved:'Çözüldü'})[s]||s;}
async function prepareFeedback(){
  const page=document.getElementById('feedbackPage');if(page)page.value=pageMeta[state.feedbackSource]?.[0]||state.feedbackSource||'Genel Bakış';
  const filter=document.getElementById('feedbackStatusFilter')?.value||'';
  try{const rows=await api('GET',`/api/feedback?limit=100${filter?'&status='+encodeURIComponent(filter):''}`);state.feedbackRows=rows;renderFeedback();}catch(e){toast(e.message,'error');}
}
function renderFeedback(){
  const manager=hasAnyRole('admin','quality');document.getElementById('feedbackListHint').textContent=manager?'Kapsamınızdaki tüm pilot geri bildirimleri gösterilir.':'Yalnız kendi gönderdiğiniz kayıtlar gösterilir.';
  document.getElementById('feedbackScopeBadge').textContent=manager?'Yönetim görünümü':'Kendi kayıtlarım';
  const box=document.getElementById('feedbackList');const rows=state.feedbackRows||[];
  box.innerHTML=rows.length?rows.map(x=>`<article class="feedback-row status-${esc(x.status)}"><div class="feedback-row-head"><span>${esc(feedbackStatusLabel(x.status))}</span><b>${esc(x.category)}</b><small>${x.rating?`${x.rating}/5`:'—'}</small></div><p>${esc(x.message)}</p><div class="feedback-meta">${esc(x.created_by)} · ${esc(x.page||'Ekran belirtilmedi')} · ${x.created_at?new Date(x.created_at).toLocaleString('tr-TR'):'—'}</div>${x.resolution_note?`<div class="feedback-resolution"><b>Not:</b> ${esc(x.resolution_note)}</div>`:''}${manager&&x.status!=='resolved'?`<div class="feedback-actions"><button class="ghost small" data-action-call="reviewFeedback(${x.id})">İnceleniyor</button><button class="primary small" data-action-call="resolveFeedback(${x.id})">Çözüldü</button></div>`:''}</article>`).join(''):'<div class="empty-state"><b>Henüz geri bildirim yok.</b><span>Pilot sırasında gördüğünüz ilk noktayı buraya kaydedin.</span></div>';
}
window.reviewFeedback=async function(id){try{await api('PATCH',`/api/feedback/${id}`,{status:'reviewed'});toast('Geri bildirim incelemeye alındı.');await prepareFeedback();}catch(e){toast(e.message,'error');}};
window.resolveFeedback=async function(id){const data=await workflowForm({eyebrow:'GERİ BİLDİRİM',title:'Kaydı çözüldü olarak kapat',description:'Çözüm veya alınan karar için kısa bir iz bırakın.',submitLabel:'Çözüldü olarak kapat',fields:[{name:'note',label:'Çözüm / karar notu',type:'textarea',rows:4}]});if(!data)return;try{await api('PATCH',`/api/feedback/${id}`,{status:'resolved',resolution_note:data.note||''});toast('Geri bildirim çözüldü olarak işaretlendi.');await prepareFeedback();}catch(e){toast(e.message,'error');}};
document.getElementById('feedbackForm')?.addEventListener('submit',async ev=>{ev.preventDefault();try{await api('POST','/api/feedback',{category:document.getElementById('feedbackCategory').value,rating:document.getElementById('feedbackRating').value?Number(document.getElementById('feedbackRating').value):null,page:document.getElementById('feedbackPage').value,message:document.getElementById('feedbackMessage').value.trim()});document.getElementById('feedbackMessage').value='';document.getElementById('feedbackRating').value='';toast('Geri bildiriminiz kaydedildi. Teşekkürler.');await prepareFeedback();}catch(e){toast(e.message,'error');}});
document.getElementById('feedbackStatusFilter')?.addEventListener('change',prepareFeedback);


/* 6.20 Quality & Accreditation 360 */
let q360Catalogs=null,q360Frameworks=[],q360Dashboard=null,q360University=null,q360Routing=null;
function q360Fill(id,items,valueKey=null,labelKey=null,selected=null){const el=document.getElementById(id);if(!el)return;el.innerHTML=(items||[]).map(x=>{const v=valueKey?x[valueKey]:x;const l=labelKey?x[labelKey]:x;return `<option value="${esc(v)}" ${selected!=null&&String(selected)===String(v)?'selected':''}>${esc(l)}</option>`}).join('');}
function q360ProgramId(){return Number(document.getElementById('q360Program')?.value||0)}
function q360Year(){return document.getElementById('q360Year')?.value||'2026-2027'}
function q360FrameworkId(){return Number(document.getElementById('q360Framework')?.value||0)||null}
async function loadQualityExecutive(){
  const year=q360Year(); if(!year)return;
  try{
    q360University=await api('GET',`/api/quality360/university/dashboard?academic_year=${encodeURIComponent(year)}`);
    const s=q360University.summary||{}, box=document.getElementById('qualityExecutiveKpis');
    if(box)box.innerHTML=[[s.university_quality_health||0,'Kalite skoru'],[s.faculty_count||0,'Akademik birim'],[s.program_count||0,'Program'],[s.open_cycle_count||0,'Açık PUKÖ'],[s.evidence_count||0,'Kanıt']].map((x,i)=>`<div class="${i===0?'quality-score-kpi':''}"><b>${i===0?'%':''}${esc(x[0])}</b><span>${esc(x[1])}</span></div>`).join('');
    const health=Number(s.university_quality_health||0), level=health<45?'critical':health<70?'watch':'healthy';
    const hb=document.getElementById('qualityExecutiveHealthBadge');if(hb){hb.textContent=`%${health} · ${level==='healthy'?'Güçlü':level==='watch'?'İzlenmeli':'Kritik'}`;hb.className=`badge executive-${level}`;}
    const h=document.getElementById('qualityExecutiveHealth');if(h)h.innerHTML=`<div class="executive-score-ring" data-style="--score:${Math.max(0,Math.min(100,health))}"><div><b>%${health}</b><span>Kurum skoru</span></div></div><div class="executive-health-copy"><b>${health>=70?'Kalite döngüsü güçlü ilerliyor':health>=45?'Bazı birimler yönetim dikkati istiyor':'Öncelikli kalite müdahalesi gerekiyor'}</b><span>${Number(s.critical_program_count||0)} kritik · ${Number(s.watch_program_count||0)} izlenen program</span><div class="executive-health-bar"><i data-style="width:${health}%"></i></div></div>`;
    const ins=document.getElementById('qualityExecutiveInsights');if(ins)ins.innerHTML=(q360University.executive_insights||[]).map(x=>`<article class="executive-insight ${esc(x.severity||'watch')}"><i></i><div><b>${esc(x.title)}</b><span>${esc(x.action)}</span></div></article>`).join('');
    const fac=document.getElementById('qualityFacultyOverview');if(fac)fac.innerHTML=(q360University.faculties||[]).slice(0,8).map(x=>`<article class="executive-faculty-row"><div><b>${esc(x.name)}</b><span>${x.programs} program · ${x.courses} ders · ${x.open_cycles} açık PUKÖ</span></div><div class="executive-row-score"><span class="risk-dot ${esc(x.risk_level)}"></span><b>%${x.quality_health}</b></div></article>`).join('')||'<div class="empty-state"><b>Akademik birim verisi yok.</b></div>';
    const pr=document.getElementById('qualityProgramPriority');if(pr)pr.innerHTML=(q360University.programs||[]).slice(0,7).map(x=>`<button type="button" class="executive-program-row" data-quality-program="${x.id}"><span class="risk-dot ${esc(x.risk_level)}"></span><div><b>${esc(x.name)}</b><span>${esc(x.faculty||'')} · ${esc(x.primary_framework?.family||'Profil bekliyor')}</span></div><strong>%${x.quality_health}</strong><em>→</em></button>`).join('')||'<div class="empty-state"><b>Program verisi yok.</b></div>';
    const fd=document.getElementById('qualityFrameworkDistribution'), dist=q360University.framework_distribution||{}, total=Math.max(1,Object.values(dist).reduce((a,b)=>a+Number(b||0),0));if(fd)fd.innerHTML=Object.entries(dist).sort((a,b)=>b[1]-a[1]).map(([name,count])=>`<div class="framework-distribution-row"><div><b>${esc(name)}</b><span>${count} program</span></div><div class="framework-distribution-bar"><i data-style="width:${Math.round(Number(count)/total*100)}%"></i></div></div>`).join('')||'<div class="empty-state"><b>Framework eşleştirmesi bekleniyor.</b></div>';
  }catch(e){const box=document.getElementById('qualityExecutiveKpis');if(box)box.innerHTML='<span class="muted">Kurumsal özet bu rol için kullanılamıyor.</span>';}
}


async function loadQualityEscalations(){
  const year=q360Year(),box=document.getElementById('qualityEscalationQueue'),sumBox=document.getElementById('qualityEscalationSummary');if(!year||!box)return;
  try{
    const data=await api('GET',`/api/quality360/escalations?academic_year=${encodeURIComponent(year)}`),s=data.summary||{},items=data.items||[];
    const badge=document.getElementById('qualityEscalationCount');if(badge)badge.textContent=`${Number(s.overdue_count||0)} gecikme`;
    if(sumBox)sumBox.innerHTML=[[s.overdue_count||0,'Geciken'],[s.due_soon_count||0,'7 gün içinde'],[s.unscheduled_count||0,'Terminsiz'],[s.institutional_escalation_count||0,'Kurumsal eskalasyon']].map(x=>`<div><b>${esc(x[0])}</b><span>${esc(x[1])}</span></div>`).join('');
    if(!items.length){box.innerHTML='<div class="empty-state success-state"><b>Takip bekleyen kalite aksiyonu yok.</b><span>Açık PUKÖ terminleri kontrol altında.</span></div>';setSectionCollapsed('qualityEscalation',true);return;}
    setSectionCollapsed('qualityEscalation',false);
    box.innerHTML=items.slice(0,12).map(x=>{const state=x.escalation_state||'due_soon',lvl=Number(x.escalation_level||0);return `<article class="quality-escalation-row ${esc(state)} level-${lvl}"><div class="quality-escalation-level"><span>${state==='overdue'?`L${lvl}`:state==='due_soon'?'Yakın':'Termin'}</span></div><div class="quality-escalation-copy"><div class="quality-escalation-title"><b>${esc(x.program_name)}</b><small>${esc(x.faculty||'')} ${x.department?'· '+esc(x.department):''}</small></div><h4>${esc(x.title)}</h4><p>${esc(x.recommended_action)}</p><div class="quality-escalation-meta"><span><small>Ölçüt</small><b>${esc(x.criterion_code)}</b></span><span><small>Sorumlu</small><b>${esc(x.owner||'Atanmamış')}</b></span><span><small>Sonraki seviye</small><b>${esc(x.next_role)}</b></span><span><small>Termin</small><b>${esc(x.due_date||'Belirlenmedi')}</b></span></div></div><div class="quality-escalation-age"><b>${state==='overdue'?`${x.days_overdue} gün`:(state==='due_soon'?`${x.days_remaining} gün`:'—')}</b><span>${esc(x.label)}</span><button type="button" class="ghost compact" data-quality-program="${x.program_id}">Programı aç</button></div></article>`}).join('');
    box.querySelectorAll('[data-quality-program]').forEach(btn=>btn.addEventListener('click',()=>{const pid=Number(btn.dataset.qualityProgram);const sel=document.getElementById('q360Program');if(sel&&pid){sel.value=String(pid);Promise.all([loadQuality360(),loadQualityFrameworkRoute(),loadQualityActions()]);sel.scrollIntoView({behavior:'smooth',block:'center'});}}));
  }catch(e){box.innerHTML=`<div class="empty-state"><b>Eskalasyon kuyruğu hazırlanamadı.</b><span>${esc(e.message)}</span></div>`;}
}

async function loadQualityActions(){
  const pid=q360ProgramId(),year=q360Year(),fw=q360FrameworkId(),box=document.getElementById('qualityActionRecommendations');if(!pid||!year||!box)return;
  try{
    const data=await api('GET',`/api/quality360/programs/${pid}/action-recommendations?academic_year=${encodeURIComponent(year)}${fw?`&framework_id=${fw}`:''}`);
    const proposals=data.proposals||[], badge=document.getElementById('qualityActionCount');if(badge)badge.textContent=`${proposals.length} öneri`;
    if(!proposals.length){box.innerHTML='<div class="empty-state success-state"><b>Kritik kalite aksiyonu görünmüyor.</b><span>Ölçütler hedef aralıkta. Dönemsel izlemeye devam edin.</span></div>';setSectionCollapsed('qualityAction',true);return;}
    setSectionCollapsed('qualityAction',false);
    box.innerHTML=proposals.slice(0,8).map((x,i)=>`<article class="quality-action-card ${esc(x.severity)}"><div class="quality-action-top"><span class="quality-action-severity">${x.severity==='critical'?'Kritik':x.severity==='high'?'Yüksek':'İzle'}</span><span>${esc(x.framework_family)} · ${esc(x.criterion_code)} · %${Math.round(Number(x.score||0))}</span></div><div class="quality-action-copy"><h4>${esc(x.title)}</h4><p>${esc(x.why)}</p></div><div class="quality-action-meta"><span><small>Sorumlu</small><b>${esc(x.owner_role)}</b></span><span><small>Önerilen termin</small><b>${esc(x.suggested_due_date)}</b></span><span><small>Beklenen kanıt</small><b>${esc((x.expected_evidence||[])[0]||'Kalite kanıtı')}</b></span></div><details><summary>Neden önerildi?</summary><ul>${(x.gap_signals||[]).map(g=>`<li>${esc(g)}</li>`).join('')}</ul></details><button type="button" class="primary compact" data-quality-action-index="${i}">PUKÖ olarak başlat</button></article>`).join('');
    box.querySelectorAll('[data-quality-action-index]').forEach(btn=>btn.addEventListener('click',async()=>{const x=proposals[Number(btn.dataset.qualityActionIndex)];if(!x)return;btn.disabled=true;try{await api('POST','/api/quality360/action-recommendations/accept',{program_id:x.program_id,academic_year:x.academic_year,framework_id:x.framework_id,criterion_code:x.criterion_code,title:x.title,owner:x.owner_role,due_date:x.suggested_due_date,plan_text:x.plan_text,do_text:x.do_text,check_text:x.check_text,act_text:x.act_text,expected_evidence:x.expected_evidence||[]});toast('Kalite aksiyonu PUKÖ döngüsü olarak başlatıldı.');await Promise.all([loadQualityActions(),loadQuality360(),loadQualityExecutive()]);}catch(e){toast(e.message,'error');btn.disabled=false;}}));
  }catch(e){box.innerHTML=`<div class="empty-state"><b>Aksiyon önerileri hazırlanamadı.</b><span>${esc(e.message)}</span></div>`;}
}

async function loadQualityFrameworkRoute(){
  const pid=q360ProgramId(),box=document.getElementById('qualityFrameworkRoute');if(!pid||!box)return;
  try{
    q360Routing=await api('GET',`/api/quality360/programs/${pid}/framework-routing`);
    const p=q360Routing.program||{}, manual=q360Routing.assignments||[], recs=q360Routing.recommendations||[];
    const primaryManual=manual.find(x=>x.is_primary&&x.active), primaryAuto=recs.find(x=>x.is_primary), primary=primaryManual?{family:primaryManual.framework?.framework_family,name:primaryManual.framework?.name,rationale:primaryManual.rationale,confidence:1}:primaryAuto;
    const overlays=recs.filter(x=>!x.is_primary);
    box.innerHTML=`<div class="framework-route-head"><div><span class="eyebrow">AKILLI KALİTE EŞLEŞTİRME</span><h3>${esc(p.name||'Program')}</h3><p>${esc(p.faculty||'')} ${p.department?'· '+esc(p.department):''}</p></div><span class="framework-primary">${esc(primary?.family||'Profil seçilmedi')}</span></div><div class="framework-route-body"><div class="framework-main"><small>Birincil alan akreditasyonu</small><b>${esc(primary?.name||'Manuel doğrulama gerekli')}</b><span>${esc(primary?.rationale||'Programın akademik alanına göre kalite yöneticisi profil seçebilir.')}</span></div><div class="framework-overlays">${overlays.map(x=>`<span><b>${esc(x.family)}</b>${esc(x.name)}</span>`).join('')}</div></div>`;
  }catch(e){box.innerHTML=`<div class="empty-state"><b>Kalite profili eşleştirilemedi.</b><span>${esc(e.message)}</span></div>`;}
}

async function prepareQuality360(){
  if(!canAccreditation()){showPage('dashboard');return;}
  if(!state.programs.length)await refreshCore();
  try{
    [q360Catalogs,q360Frameworks]=await Promise.all([api('GET','/api/catalogs'),api('GET','/api/quality360/frameworks')]);
    q360Fill('q360Program',state.programs,'id','name');
    q360Fill('q360Year',q360Catalogs.academic_years,null,null,q360Catalogs.academic_years.find(x=>x.startsWith('2026-'))||q360Catalogs.academic_years[3]);
    const fw=document.getElementById('q360Framework');if(fw)fw.innerHTML=q360Frameworks.map(x=>`<option value="${x.id}">${esc(x.framework_family)} · ${esc(x.version)}${x.status==='transition'?' · 2028+':''}</option>`).join('');
    const initialPid=q360ProgramId();if(initialPid){try{q360Routing=await api('GET',`/api/quality360/programs/${initialPid}/framework-routing`);const manual=(q360Routing.assignments||[]).find(x=>x.is_primary&&x.active),auto=(q360Routing.recommendations||[]).find(x=>x.is_primary),target=manual?.framework_profile_id||auto?.framework_id;if(target&&fw)fw.value=String(target);}catch(_){}}
    q360Fill('q360CurrTerm',q360Catalogs.terms);q360Fill('q360CurrClass',q360Catalogs.class_levels);q360Fill('q360CurrCategory',q360Catalogs.course_categories);
    q360Fill('q360StakeType',q360Catalogs.stakeholder_types);q360Fill('q360StakeEngagement',q360Catalogs.stakeholder_engagement_types);
    q360Fill('q360GradStatus',q360Catalogs.graduate_employment_statuses);q360Fill('q360FacultyTitle',q360Catalogs.instructor_titles);q360Fill('q360FacultyEmployment',q360Catalogs.employment_types);
    q360Fill('q360InfraType',q360Catalogs.infrastructure_types);q360Fill('q360InfraStatus',q360Catalogs.quality_statuses,'value','label');q360Fill('q360CycleStatus',q360Catalogs.quality_cycle_statuses);q360Fill('q360GovBody',q360Catalogs.governance_bodies);
    await Promise.all([loadQuality360(),loadQualityExecutive(),loadQualityFrameworkRoute(),loadQualityActions(),loadQualityEscalations(),loadQualityCalendar(),loadQ360GovernanceActions(),loadQualityClosureReadiness(),loadAccreditationReadiness()]);
  }catch(e){toast(e.message,'error');}
}
async function loadQuality360(){
  const pid=q360ProgramId();if(!pid)return;
  const year=q360Year(),fid=q360FrameworkId();
  try{
    q360Dashboard=await api('GET',`/api/quality360/programs/${pid}/dashboard?academic_year=${encodeURIComponent(year)}${fid?`&framework_id=${fid}`:''}`);
    const d=q360Dashboard,c=d.counts||{};document.getElementById('q360Score').textContent=`%${Number(d.readiness_percent||0).toLocaleString('tr-TR')} · ${d.readiness_label}`;
    document.getElementById('q360Kpis').innerHTML=[['Hazırlık',`%${d.readiness_percent}`,'Ölçütlerin birleşik skoru'],['Müfredat',c.curriculum||0,'Ders kaydı'],['PUKÖ',c.quality_cycles||0,'İyileştirme döngüsü'],['Kanıt',c.quality_evidence||0,'Kalite kanıtı']].map(x=>`<div class="quality-kpi"><span>${esc(x[0])}</span><b>${esc(x[1])}</b><small>${esc(x[2])}</small></div>`).join('');
    document.getElementById('q360Criteria').innerHTML=(d.criteria||[]).map(x=>`<div class="q360-criterion-row"><div class="q360-criterion-copy"><b>${esc(x.code)} · ${esc(x.name)}</b><small>Otomatik %${x.auto_score} ${x.manual_maturity?`· manuel olgunluk ${x.manual_maturity}/5`:''}${(x.subcriteria||[]).length?` · ${(x.subcriteria||[]).length} alt ölçüt`:''}</small>${(x.signals||[]).length?`<span class="q360-signals">${x.signals.map(s=>`${s.ok?'✓':'○'} ${esc(s.label)}`).join(' · ')}</span>`:''}</div><div class="q360-criterion-actions"><span class="badge ${x.readiness==='gap'?'danger':x.readiness==='strong'?'status-approved':'status-ready'}">%${x.score}</span><select aria-label="${esc(x.code)} manuel olgunluk" data-q360-maturity="${esc(x.code)}"><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option></select><button class="ghost small" type="button" data-q360-save="${esc(x.code)}">Kaydet</button></div></div>`).join('');
    (d.criteria||[]).forEach(x=>{const s=document.querySelector(`[data-q360-maturity="${CSS.escape(String(x.code))}"]`);if(s&&x.manual_maturity)s.value=String(x.manual_maturity)});
    const cc=d.curriculum||{};document.getElementById('q360Curriculum').innerHTML=(cc.checks||[]).map(x=>`<div class="q360-curriculum-row"><div><b>${esc(x.label||x.key)}</b><small>Hedef ${x.required} ${esc(x.unit||'AKTS')}</small></div><span class="badge ${x.passed?'status-approved':'danger'}">${x.actual} ${esc(x.unit||'AKTS')} · ${x.passed?'Uygun':'Açık'}</span></div>`).join('')||'<p class="muted">Müfredat kaydı ekleyerek denetimi başlatın.</p>';
    const modules=[['curriculum','Müfredat',c.curriculum],['stakeholders','Paydaş',c.stakeholders],['graduates','Mezun',c.graduates],['faculty','Öğretim kadrosu',c.faculty],['infrastructure','Altyapı',c.infrastructure],['quality_cycles','PUKÖ',c.quality_cycles],['governance','Kurul / karar',c.governance_decisions]];
    const panelMap={curriculum:'curriculum',stakeholders:'stakeholder',graduates:'graduate',faculty:'faculty',infrastructure:'infra',quality_cycles:'cycle',governance:'governance'};
    document.getElementById('q360ModuleCards').innerHTML=modules.map(x=>`<article class="quality-module-card"><div class="quality-module-count">${Number(x[2]||0)}</div><div class="quality-module-copy"><b>${esc(x[1])}</b><small>${Number(x[2]||0)?'Kayıtlar güncel · düzenlemeye hazır':'Henüz kayıt yok · ilk veriyi ekleyin'}</small></div><div class="quality-module-actions"><button class="ghost small" type="button" data-q360-open="${panelMap[x[0]]||'overview'}">Aç</button><button class="ghost small" type="button" data-q360-template="${x[0]}">Excel</button></div></article>`).join('');
    const crit=(d.framework?.criteria||[]),critOptions=crit.flatMap(x=>[{code:x.code,name:x.name,parent:false},...(x.subcriteria||[]).map(sc=>({code:sc.code,name:sc.title||sc.name||sc.code,parent:true}))]);const cyc=document.getElementById('q360CycleCriterion');if(cyc)cyc.innerHTML=critOptions.map(x=>`<option value="${esc(x.code)}">${x.parent?'↳ ':''}${esc(x.code)} · ${esc(x.name)}</option>`).join('');const ev=document.getElementById('q360EvidenceCriterion');if(ev)ev.innerHTML='<option value="">Genel program kanıtı</option>'+critOptions.map(x=>`<option value="${esc(x.code)}">${x.parent?'↳ ':''}${esc(x.code)} · ${esc(x.name)}</option>`).join('');
    await Promise.all([loadQ360Evidence(),loadAccreditationReadiness(),loadMedekOdrReadiness()]);
  }catch(e){toast(e.message,'error');}
}
async function q360Json(path,body,form){try{await api('POST',path,body);form?.reset();toast('Kalite 360 kaydı kaydedildi.');await loadQuality360();}catch(e){toast(e.message,'error')}}

async function loadAccreditationReadiness(){
  const pid=q360ProgramId(),year=q360Year(),fid=q360FrameworkId(),tbody=document.getElementById('q360VisitMatrix');if(!pid||!tbody)return;
  try{
    const data=await api('GET',`/api/quality360/programs/${pid}/accreditation-readiness?academic_year=${encodeURIComponent(year)}${fid?`&framework_id=${fid}`:''}`),sum=data.summary||{};
    const score=document.getElementById('q360VisitScore');if(score)score.textContent=`%${Number(data.visit_readiness_percent||0).toLocaleString('tr-TR')} · ${esc(data.visit_readiness_label||'')}`;
    const k=document.getElementById('q360VisitKpis');if(k)k.innerHTML=[['Hazır',sum.subcriteria_total?sum.subcriteria_ready:sum.ready||0,sum.subcriteria_total?'alt ölçüt':'ölçüt'],['Kontrol',sum.subcriteria_total?sum.subcriteria_attention:sum.attention||0,sum.subcriteria_total?'alt ölçüt':'ölçüt'],['Kritik açık',sum.subcriteria_total?sum.subcriteria_gaps:sum.gaps||0,sum.subcriteria_total?'alt ölçüt':'ölçüt'],['Manuel inceleme',sum.subcriteria_manual_review||0,'alt ölçüt']].map(x=>`<div class="quality-kpi"><span>${esc(x[0])}</span><b>${esc(x[1])}</b><small>${esc(x[2])}</small></div>`).join('');
    const pr=document.getElementById('q360VisitPriority');if(pr)pr.innerHTML=(data.priority_gaps||[]).slice(0,8).map(x=>{const code=x.subcriterion_code||x.criterion_code,title=x.subcriterion_title||x.criterion_name||'',detail=x.subcriterion_code?(x.needs_evidence?'Alt ölçüt kanıtı eksik':x.manual_review_required?'Manuel doğrulama gerekli':'Otomatik sinyal kontrol edilmeli'):(x.needs_evidence?'Doğrudan kanıt eksik':'Kanıt var · içerik kontrolü');const missing=x.missing_evidence||x.missing_signals||[];return `<article class="visit-priority-card"><div><b>${esc(code)} · ${esc(title)}</b><small>${esc(detail)}</small></div><span>${missing.slice(0,2).map(esc).join(' · ')||'Kanıt/içerik kontrolü gerekli'}</span></article>`}).join('');
    tbody.innerHTML=(data.matrix||[]).map(x=>{const subs=x.subcriteria||[];const subDetails=subs.length?`<details class="q360-subcriteria"><summary>${x.subcriteria_ready||0}/${subs.length} alt ölçüt hazır · ${x.subcriteria_gaps||0} açık</summary><div class="q360-subcriteria-list">${subs.map(sc=>`<div class="q360-subcriterion-row"><span><b>${esc(sc.subcriterion_code)}</b> ${esc(sc.title)}</span><span>${sc.auto_ok===true?'Otomatik ✓':sc.auto_ok===false?'Otomatik açık':`<span class="q360-manual-review"><select aria-label="${esc(sc.subcriterion_code)} manuel olgunluk" data-q360-submaturity="${esc(sc.subcriterion_code)}"><option value="1" ${Number(sc.manual_maturity||0)===1?'selected':''}>1</option><option value="2" ${Number(sc.manual_maturity||0)===2?'selected':''}>2</option><option value="3" ${Number(sc.manual_maturity||0)===3?'selected':''}>3</option><option value="4" ${Number(sc.manual_maturity||0)===4?'selected':''}>4</option><option value="5" ${Number(sc.manual_maturity||0)===5?'selected':''}>5</option></select><button type="button" class="ghost compact" data-q360-subreview="${esc(sc.subcriterion_code)}">${sc.manual_review_completed?'Güncelle':'Doğrula'}</button></span>`} · ${sc.evidence_count||0} kanıt · <i class="badge ${sc.status==='ready'?'status-approved':sc.status==='attention'?'status-ready':'danger'}">${sc.status==='ready'?'Hazır':sc.status==='attention'?'Kontrol':'Açık'}</i></span></div>`).join('')}</div></details>`:'';return `<tr><td><b>${esc(x.criterion_code)}</b><small>${esc(x.criterion_name)}</small>${subDetails}</td><td><strong>%${Math.round(Number(x.visit_score||0))}</strong><small>ölçüt %${Math.round(Number(x.criterion_score||0))}</small></td><td><b>${x.evidence_count}</b><small>${x.evidence_count?'ölçüt/alt ölçüt kanıtı':'kanıt bekleniyor'}</small></td><td><b>${x.closed_cycle_count} kapalı</b><small>${x.open_cycle_count} açık</small></td><td><small>${(x.missing_signals||[]).map(esc).join(' · ')||'Temel sinyal açığı yok'}</small></td><td><span class="badge ${x.status==='ready'?'status-approved':x.status==='attention'?'status-ready':'danger'}">${x.status==='ready'?'Hazır':x.status==='attention'?'Kontrol':'Açık'}</span></td></tr>`}).join('')||'<tr><td colspan="6">Hazırlık verisi yok.</td></tr>';
    tbody.querySelectorAll('[data-q360-subreview]').forEach(btn=>btn.addEventListener('click',async()=>{const code=btn.dataset.q360Subreview,sel=tbody.querySelector(`[data-q360-submaturity="${CSS.escape(code)}"]`),maturity=Number(sel?.value||3),frameworkId=Number(fid||data.framework?.id||0);if(!frameworkId)return;btn.disabled=true;try{await api('PUT','/api/quality360/criterion-assessments',{program_id:pid,framework_profile_id:frameworkId,academic_year:year,criterion_code:code,maturity_level:maturity,quality_status:'measured',note:'Alt ölçüt manuel doğrulaması',evidence_refs:[]});toast(`${code} alt ölçüt manuel doğrulaması kaydedildi.`);await Promise.all([loadAccreditationReadiness(),loadQualityActions()]);}catch(e){toast(e.message,'error');btn.disabled=false;}}));
  }catch(e){tbody.innerHTML=`<tr><td colspan="6">${esc(e.message)}</td></tr>`;}
}


async function loadMedekOdrReadiness(){
  const pid=q360ProgramId(),year=q360Year(),fid=q360FrameworkId(),box=document.getElementById('q645MedekOdrMatrix');
  if(!pid||!box)return;
  const fw=q360Dashboard?.framework||{},family=String(fw.framework_family||'').toUpperCase(),version=String(fw.version||'');
  if(family!=='MEDEK'||version!=='v1.1'){
    box.innerHTML='<div class="empty-state"><b>MEDEK v1.1 seçin.</b><span>2026 ÖDR Hazırlık Merkezi yalnız MEDEK v1.1 frameworkü ile çalışır.</span></div>';
    const score=document.getElementById('q645MedekOdrScore');if(score)score.textContent='MEDEK v1.1 gerekli';
    const k=document.getElementById('q645MedekOdrKpis');if(k)k.innerHTML='';
    return;
  }
  const type=document.getElementById('q645MedekOdrType')?.value||'general';
  try{
    const data=await api('GET',`/api/quality360/programs/${pid}/medek-odr-readiness?academic_year=${encodeURIComponent(year)}${fid?`&framework_id=${fid}`:''}&application_type=${encodeURIComponent(type)}`),sum=data.summary||{};
    const score=document.getElementById('q645MedekOdrScore');if(score)score.textContent=`%${Number(sum.internal_completion_percent||0).toLocaleString('tr-TR')} iç tamamlama`;
    const scope=document.getElementById('q645MedekOdrScope');if(scope)scope.textContent=data.scope_note||'';
    const k=document.getElementById('q645MedekOdrKpis');if(k)k.innerHTML=[['ÖDR satırı',sum.official_prompt_count||0,'resmî hazırlık satırı'],['Hazır',sum.prompt_ready||0,'doğrudan kanıtlı'],['Kontrol',sum.prompt_attention||0,'inceleme/bağlama'],['Eksik',sum.prompt_gaps||0,'aksiyon gerekli'],['Ekler',`${sum.appendix_ready||0}/${sum.appendix_total||0}`,'Ek I + Ek II']].map(x=>`<div class="quality-kpi"><span>${esc(x[0])}</span><b>${esc(x[1])}</b><small>${esc(x[2])}</small></div>`).join('');
    const pr=document.getElementById('q645MedekOdrPriority');if(pr)pr.innerHTML=(data.priority_gaps||[]).slice(0,10).map(x=>`<article class="visit-priority-card"><div><b>${esc(x.code)} · ${esc(x.title)}</b><small>${esc(x.owner_role||'')}</small></div><span>${esc(x.next_action||'Kontrol gerekli')}</span><button class="ghost compact" type="button" data-medek-evidence-code="${esc(x.code)}">Kanıta git</button></article>`).join('')||'<div class="empty-state success-state"><b>Öncelikli açık yok.</b><span>İnsan onayı ve resmî dosya kontrolü yine zorunludur.</span></div>';
    const ap=document.getElementById('q645MedekOdrAppendices');if(ap)ap.innerHTML=(data.appendices||[]).map(x=>`<article class="medek-appendix-row"><div><b>${esc(x.code)} · ${esc(x.title)}</b><small>${esc(x.owner_role||'')} · ${x.exact_evidence_count||0} kanıt</small></div><span class="badge ${x.status==='ready'?'status-approved':x.status==='attention'?'status-ready':'danger'}">${x.status==='ready'?'Hazır':x.status==='attention'?'Kontrol':'Eksik'}</span></article>`).join('');
    box.innerHTML=(data.groups||[]).map(g=>`<details class="medek-odr-group" ${Number(g.gaps||0)?'open':''}><summary><span><b>Ölçüt ${esc(g.criterion_code)}</b> · ${esc(g.criterion_name)}</span><span>${g.ready||0}/${g.total||0} hazır · ${g.gaps||0} eksik</span></summary><div class="medek-odr-items">${(g.items||[]).map(x=>`<article class="medek-odr-item ${esc(x.status)}"><div class="medek-odr-item-main"><div><b>${esc(x.code)} · ${esc(x.title)}</b><small>Framework bağlantısı: ${esc(x.mapped_subcriterion||'—')} · Sorumlu: ${esc(x.owner_role||'')}</small><small>Kaynak: ${(x.source_modules||[]).map(esc).join(' · ')}</small></div><span class="badge ${x.status==='ready'?'status-approved':x.status==='attention'?'status-ready':'danger'}">${x.status==='ready'?'Hazır':x.status==='attention'?'Kontrol':'Eksik'}</span></div><div class="medek-odr-item-meta"><span>Doğrudan kanıt <b>${x.exact_evidence_count||0}</b></span><span>Destek kanıtı <b>${x.supporting_evidence_count||0}</b></span><span>${x.auto_ok===true?'Sistem sinyali ✓':x.auto_ok===false?'Sistem sinyali açık':'Manuel inceleme'}</span><span>${esc(x.next_action||'')}</span></div><div class="medek-odr-item-actions"><button class="ghost compact" type="button" data-medek-evidence-code="${esc(x.code)}">Kanıt ilişkilendir</button>${x.auto_ok===null?`<select data-medek-maturity="${esc(x.code)}" aria-label="${esc(x.code)} olgunluk"><option value="1">1</option><option value="2">2</option><option value="3" selected>3</option><option value="4">4</option><option value="5">5</option></select><button class="ghost compact" type="button" data-medek-review="${esc(x.code)}">İncelemeyi kaydet</button>`:''}</div></article>`).join('')}</div></details>`).join('');
    const ev=document.getElementById('q360EvidenceCriterion');if(ev){[...(data.items||[]),...(data.appendices||[])].forEach(x=>{if(![...ev.options].some(o=>o.value===x.code)){const o=document.createElement('option');o.value=x.code;o.textContent=`ÖDR ${x.code} · ${x.title}`;ev.appendChild(o);}});}
    document.querySelectorAll('[data-medek-evidence-code]').forEach(btn=>btn.addEventListener('click',()=>{const code=btn.dataset.medekEvidenceCode,sel=document.getElementById('q360EvidenceCriterion');if(sel)sel.value=code;setQ360Workspace('evidence');document.getElementById('q360EvidenceForm')?.scrollIntoView({behavior:'smooth',block:'center'});}));
    box.querySelectorAll('[data-medek-review]').forEach(btn=>btn.addEventListener('click',async()=>{const code=btn.dataset.medekReview,sel=box.querySelector(`[data-medek-maturity="${CSS.escape(code)}"]`),maturity=Number(sel?.value||3);btn.disabled=true;try{await api('PUT','/api/quality360/criterion-assessments',{program_id:pid,framework_profile_id:Number(fid||fw.id),academic_year:year,criterion_code:code,maturity_level:maturity,quality_status:maturity>=4?'measured':'implemented',note:'MEDEK ÖDR satırı manuel doğrulaması',evidence_refs:[]});toast(`${code} ÖDR incelemesi kaydedildi.`);await loadMedekOdrReadiness();}catch(e){toast(e.message,'error');btn.disabled=false;}}));
  }catch(e){box.innerHTML=`<div class="empty-state"><b>MEDEK ÖDR hazırlığı yüklenemedi.</b><span>${esc(e.message)}</span></div>`;}
}

async function loadQ360Evidence(){const pid=q360ProgramId(),box=document.getElementById('q360EvidenceList');if(!pid||!box)return;try{const rows=await api('GET',`/api/quality360/programs/${pid}/evidence`);box.innerHTML=rows.slice(0,8).map(x=>`<div class="evidence-item"><div><b>${esc(x.criterion_code||'Genel')} · ${esc(x.original_name)}</b><small>${Math.round(x.size_bytes/1024)} KB · ${esc(x.sha256.slice(0,12))}…</small></div><button class="ghost small" data-q360-evidence-download="${x.id}" data-name="${esc(x.original_name)}" type="button">İndir</button></div>`).join('')||'<p class="muted">Henüz Kalite 360 kanıtı yok.</p>';}catch(e){box.innerHTML=`<p class="muted">${esc(e.message)}</p>`}}



async function loadQ360GovernanceActions(){
  const pid=q360ProgramId(),box=document.getElementById('q360GovernanceList');if(!pid||!box)return;
  try{
    const rows=await api('GET',`/api/quality360/programs/${pid}/governance`);
    const d=new Date();d.setDate(d.getDate()+30);const defaultDue=d.toISOString().slice(0,10);
    box.innerHTML=rows.length?rows.slice(0,12).map(x=>`<article class="quality-decision-row"><div class="quality-decision-copy"><b>${esc(x.body_type)} · ${esc(x.subject)}</b><span>${esc(x.meeting_date||'Tarih yok')} · Toplantı ${esc(x.meeting_no)} · Karar ${esc(x.decision_no)}${x.related_criterion?` · Ölçüt ${esc(x.related_criterion)}`:''}</span><p>${esc(x.decision_text)}</p></div><div class="quality-decision-actions"><input class="compact-input" data-gov-owner="${x.id}" value="Program Başkanı" aria-label="Sorumlu"><input class="compact-input" data-gov-due="${x.id}" type="date" value="${defaultDue}" aria-label="Termin"><button class="primary small" type="button" data-gov-action="${x.id}" data-gov-criterion="${esc(x.related_criterion||'')}">PUKÖ'ye dönüştür</button></div></article>`).join(''):'<div class="empty-state"><b>Henüz kurul kararı yok.</b><span>Bir kurul kararı kaydedildiğinde burada aksiyona dönüştürülebilir.</span></div>';
  }catch(e){box.innerHTML=`<div class="empty-state"><b>Kurul kararları yüklenemedi.</b><span>${esc(e.message)}</span></div>`;}
}

async function loadQualityClosureReadiness(){
  const pid=q360ProgramId(),year=q360Year(),box=document.getElementById('q360ClosureList');if(!pid||!box)return;
  try{
    const data=await api('GET',`/api/quality360/programs/${pid}/closure-readiness?academic_year=${encodeURIComponent(year)}`),s=data.summary||{};
    const badge=document.getElementById('q360ClosureBadge');if(badge){badge.textContent=`${Number(s.ready_for_closure||0)} kapanışa hazır`;badge.className=`badge ${Number(s.ready_for_closure||0)?'status-approved':'status-ready'}`;}
    const rows=data.items||[];
    box.innerHTML=rows.length?rows.map(x=>`<article class="quality-closure-row ${x.ready_for_closure_review?'ready':'wait'}"><div class="quality-closure-copy"><b>${esc(x.title)}</b><span>Ölçüt ${esc(x.criterion_code||'GENEL')} · ${esc(x.owner||'Sorumlu atanmamış')} · ${esc(x.due_date||'Termin yok')} · ${Number(x.evidence_count||0)} kanıt</span><div class="quality-closure-checks">${(x.checks||[]).map(c=>`<span class="${c.ok?'ok':''}">${c.ok?'✓':'○'} ${esc(c.label)}</span>`).join('')}</div>${(x.expected_evidence||[]).length?`<p>Beklenen: ${x.expected_evidence.map(esc).join(' · ')}</p>`:''}</div><div class="quality-closure-actions">${x.ready_for_closure_review?`<input class="compact-input closure-note" data-cycle-note="${x.cycle_id}" placeholder="Kapanış / etkililik notu"><button class="primary small" type="button" data-cycle-close="${x.cycle_id}">İncele & kapat</button>`:`<span class="badge status-ready">${esc(x.recommendation)}</span>`}</div></article>`).join(''):'<div class="empty-state success-state"><b>Açık PUKÖ döngüsü yok.</b><span>Yeni aksiyon oluştuğunda kapanış hazırlığı burada izlenir.</span></div>';
  }catch(e){box.innerHTML=`<div class="empty-state"><b>Kapanış hazırlığı yüklenemedi.</b><span>${esc(e.message)}</span></div>`;}
}

function q360CalendarDateParts(value){if(!value)return ['—',''];const d=new Date(`${String(value).slice(0,10)}T12:00:00`);return [String(d.getDate()).padStart(2,'0'),d.toLocaleDateString('tr-TR',{month:'short'})];}
async function loadQualityCalendar(){
  const p=q360ProgramId(),year=q360Year(),box=document.getElementById('q360CalendarStream');if(!p||!box)return;
  try{
    const data=await api('GET',`/api/quality360/programs/${p}/calendar?academic_year=${encodeURIComponent(year)}`),s=data.summary||{};
    const k=document.getElementById('q360CalendarKpis');if(k)k.innerHTML=[[s.total||0,'Toplam kayıt'],[s.overdue||0,'Geciken'],[s.attention||0,'7 gün içinde'],[s.evidence_deadlines||0,'Kanıt teslimi']].map(x=>`<div><b>${esc(x[0])}</b><span>${esc(x[1])}</span></div>`).join('');
    const badge=document.getElementById('q360CalendarBadge');if(badge){badge.textContent=s.overdue?`${s.overdue} geciken`:`${s.total||0} plan`;badge.className=`badge ${s.overdue?'status-risk':'status-ready'}`;}
    const labels={meeting:'Toplantı',evidence_deadline:'Kanıt',pdca_deadline:'PUKÖ',review:'Değerlendirme',audit:'Denetim',other:'Diğer'};
    box.innerHTML=(data.items||[]).length?(data.items||[]).map(x=>{const [day,month]=q360CalendarDateParts(x.start_date);const timing=x.overdue?`${Math.abs(x.days_remaining||0)} gün gecikti`:x.days_remaining===0?'Bugün':x.days_remaining!=null&&x.days_remaining>0?`${x.days_remaining} gün kaldı`:'';return `<article class="quality-calendar-item ${x.overdue?'overdue':x.attention?'attention':''}"><div class="quality-calendar-date"><b>${esc(day)}</b><span>${esc(month)}</span></div><div class="quality-calendar-copy"><b>${esc(x.title)}</b><span>${esc(labels[x.event_type]||x.event_type)} · ${esc(x.owner||x.owner_role||'Sorumlu atanmamış')}${x.criterion_code?` · Ölçüt ${esc(x.criterion_code)}`:''}</span>${x.evidence_required?`<span>Kanıt: ${esc(x.evidence_required)}</span>`:''}</div><div class="quality-calendar-meta"><strong>${esc(timing||x.status||'')}</strong><small>${esc(x.source==='calendar'?'Planlı kayıt':'Sistemden otomatik')}</small></div></article>`}).join(''):'<div class="empty-state"><b>Kalite takvimi boş.</b><span>Toplantı, kanıt teslimi veya değerlendirme tarihi ekleyin. PUKÖ terminleri ve kurul toplantıları otomatik olarak da görünür.</span></div>';
  }catch(e){box.innerHTML=`<div class="empty-state"><b>Takvim yüklenemedi.</b><span>${esc(e.message)}</span></div>`;}
}
document.getElementById('q360Load')?.addEventListener('click',()=>Promise.all([loadQuality360(),loadQualityExecutive(),loadQualityFrameworkRoute(),loadQualityActions(),loadQualityEscalations(),loadQualityCalendar(),loadQ360GovernanceActions(),loadQualityClosureReadiness(),loadQ360SelfEvaluation()]));
document.getElementById('q360Framework')?.addEventListener('change',loadQuality360);
document.getElementById('q645MedekOdrType')?.addEventListener('change',loadMedekOdrReadiness);
document.getElementById('q645MedekOdrDownload')?.addEventListener('click',()=>{const pid=q360ProgramId(),year=q360Year(),fid=q360FrameworkId(),type=document.getElementById('q645MedekOdrType')?.value||'general';if(!pid)return;downloadApi(`/api/quality360/programs/${pid}/medek-odr.docx?academic_year=${encodeURIComponent(year)}${fid?`&framework_id=${fid}`:''}&application_type=${encodeURIComponent(type)}`,`DOU-Assess-MEDEK-ODR-v1.1-${year}.docx`).catch(e=>toast(e.message,'error'));});

document.getElementById('q360Program')?.addEventListener('change',()=>Promise.all([loadQuality360(),loadQualityFrameworkRoute(),loadQualityCalendar(),loadQ360GovernanceActions(),loadQualityClosureReadiness(),loadQ360SelfEvaluation()]));
document.getElementById('q360Year')?.addEventListener('change',()=>Promise.all([loadQuality360(),loadQualityExecutive(),loadQualityActions(),loadQualityEscalations(),loadQualityCalendar(),loadQ360GovernanceActions(),loadQualityClosureReadiness(),loadQ360SelfEvaluation()]));
document.getElementById('qualityProgramPriority')?.addEventListener('click',async e=>{const b=e.target.closest('[data-quality-program]');if(!b)return;const sel=document.getElementById('q360Program');if(sel)sel.value=String(b.dataset.qualityProgram);await Promise.all([loadQuality360(),loadQualityFrameworkRoute(),loadQualityCalendar(),loadQ360GovernanceActions(),loadQualityClosureReadiness(),loadAccreditationReadiness()]);document.getElementById('qualityFrameworkRoute')?.scrollIntoView({behavior:'smooth',block:'start'});});
document.getElementById('q360Odr')?.addEventListener('click',()=>{const p=q360ProgramId();if(!p)return;downloadApi(`/api/quality360/programs/${p}/odr.docx?academic_year=${encodeURIComponent(q360Year())}${q360FrameworkId()?`&framework_id=${q360FrameworkId()}`:''}`,`DOU-Assess-ODR-${p}-${q360Year()}.docx`).catch(e=>toast(e.message,'error'));});

async function loadQ360SelfEvaluation(){
  const p=q360ProgramId(),summary=document.getElementById('q360SelfEvalSummary'),box=document.getElementById('q360SelfEvalCriteria');
  if(!p||!summary||!box)return;
  summary.innerHTML='<div class="empty-state"><b>Rapor hazırlanıyor…</b><span>Kanıt, PUKÖ ve ölçüt sinyalleri birleştiriliyor.</span></div>';
  try{
    const d=await api('GET',`/api/quality360/programs/${p}/self-evaluation?academic_year=${encodeURIComponent(q360Year())}${q360FrameworkId()?`&framework_id=${q360FrameworkId()}`:''}`);
    const strengths=d.executive_summary?.strengths||[],priorities=d.executive_summary?.priorities||[];
    summary.innerHTML=`<div class="self-eval-hero"><div><span class="eyebrow">${esc(d.framework?.code||'QUALITY')} · ${esc(d.academic_year)}</span><h4>${esc(d.program?.code)} · ${esc(d.program?.name)}</h4><p>Hazırlık %${Number(d.readiness_percent||0).toFixed(0)} · ziyaret hazırlığı %${Number(d.visit_readiness_percent||0).toFixed(0)}</p></div><div class="self-eval-score">%${Number(d.visit_readiness_percent||0).toFixed(0)}</div></div><div class="self-eval-columns"><div><b>Güçlü alanlar</b>${strengths.map(x=>`<span>${esc(x.code)} · ${esc(x.name)} <strong>%${Number(x.score||0).toFixed(0)}</strong></span>`).join('')||'<span>Henüz yeterli veri yok.</span>'}</div><div><b>Öncelikli geliştirme</b>${priorities.map(x=>`<span>${esc(x.code)} · ${esc(x.name)} <strong>%${Number(x.score||0).toFixed(0)}</strong></span>`).join('')||'<span>Kritik açık yok.</span>'}</div></div>`;
    box.innerHTML=(d.criteria||[]).map(c=>`<article class="self-eval-card ${esc(c.status||'gap')}"><div class="self-eval-card-head"><div><span>${esc(c.code)}</span><b>${esc(c.name)}</b></div><strong>%${Number(c.visit_score||0).toFixed(0)}</strong></div><p>${esc(c.narrative||'')}</p><div class="self-eval-trace"><span>${c.evidence_refs?.length||0} kanıt</span><span>${c.open_cycle_count||0} açık PUKÖ</span><span>${c.closed_cycle_count||0} kapalı PUKÖ</span><span>${c.decision_count||0} karar</span></div>${(c.evidence_refs||[]).length?`<details><summary>Kanıt izini göster</summary>${c.evidence_refs.map(e=>`<small>E#${e.id} · ${esc(e.name)}</small>`).join('')}</details>`:''}</article>`).join('');
  }catch(e){summary.innerHTML=`<div class="empty-state"><b>Öz değerlendirme oluşturulamadı.</b><span>${esc(e.message)}</span></div>`;box.innerHTML='';}
}

document.getElementById('q360SelfEval')?.addEventListener('click',()=>{document.querySelector('[data-q360-workspace="selfeval"]')?.click();loadQ360SelfEvaluation();});
document.getElementById('q360SelfEvalDownload')?.addEventListener('click',()=>{const p=q360ProgramId();if(!p)return;downloadApi(`/api/quality360/programs/${p}/self-evaluation.docx?academic_year=${encodeURIComponent(q360Year())}${q360FrameworkId()?`&framework_id=${q360FrameworkId()}`:''}`,`DOU-Assess-Oz-Degerlendirme-${p}-${q360Year()}.docx`).catch(e=>toast(e.message,'error'));});

function setQ360Workspace(name='overview'){document.querySelectorAll('[data-q360-workspace]').forEach(b=>b.classList.toggle('active',b.dataset.q360Workspace===name));document.querySelectorAll('.q360-workspace-panel').forEach(p=>p.classList.toggle('active',p.dataset.q360Panel===name));document.querySelector('.quality-workspace-tabs')?.scrollIntoView({behavior:'smooth',block:'nearest'});}
document.getElementById('page-quality360')?.addEventListener('click',e=>{const tab=e.target.closest('[data-q360-workspace]');if(tab){setQ360Workspace(tab.dataset.q360Workspace);if(tab.dataset.q360Workspace==='compliance')loadComplianceCenter();if(tab.dataset.q360Workspace==='medekodr')loadMedekOdrReadiness();return;}const open=e.target.closest('[data-q360-open]');if(open){setQ360Workspace(open.dataset.q360Open);return;}const b=e.target.closest('[data-q360-template]');if(!b)return;downloadApi(`/api/excel-center/${b.dataset.q360Template}/template`,`DOU-Assess-${b.dataset.q360Template}.xlsx`).catch(err=>toast(err.message,'error'));});
document.getElementById('q360GovernanceList')?.addEventListener('click',async e=>{const b=e.target.closest('[data-gov-action]');if(!b)return;const id=Number(b.dataset.govAction),owner=document.querySelector(`[data-gov-owner="${id}"]`)?.value.trim()||'Program Başkanı',due=document.querySelector(`[data-gov-due="${id}"]`)?.value||null;b.disabled=true;try{await api('POST',`/api/quality360/governance/${id}/start-action`,{academic_year:q360Year(),owner,due_date:due,criterion_code:b.dataset.govCriterion||'',expected_evidence:['Kurul kararının uygulama kanıtı','Etkililik değerlendirmesi']});toast('Kurul kararı PUKÖ döngüsüne dönüştürüldü.');await Promise.all([loadQuality360(),loadQualityCalendar(),loadQualityEscalations(),loadQualityClosureReadiness(),loadQ360GovernanceActions()]);}catch(err){toast(err.message,'error');b.disabled=false;}});
document.getElementById('q360ClosureList')?.addEventListener('click',async e=>{const b=e.target.closest('[data-cycle-close]');if(!b)return;const id=Number(b.dataset.cycleClose),note=document.querySelector(`[data-cycle-note="${id}"]`)?.value.trim();if(!note){toast('Kapanış için etkililik / karar notu yazın.','error');return;}if(!confirm('Kanıtları incelediniz ve bu PUKÖ döngüsünü kapatmak istiyor musunuz?'))return;b.disabled=true;try{await api('POST',`/api/quality360/quality-cycles/${id}/close`,{closure_note:note});toast('PUKÖ döngüsü kanıtlı kapanışla tamamlandı.');await Promise.all([loadQuality360(),loadQualityCalendar(),loadQualityEscalations(),loadQualityClosureReadiness(),loadQualityExecutive()]);}catch(err){toast(err.message,'error');b.disabled=false;}});
document.getElementById('q360Criteria')?.addEventListener('click',async e=>{const b=e.target.closest('[data-q360-save]');if(!b||!q360Dashboard)return;const code=b.dataset.q360Save,sel=document.querySelector(`[data-q360-maturity="${CSS.escape(code)}"]`);try{await api('PUT','/api/quality360/criterion-assessments',{program_id:q360ProgramId(),framework_profile_id:q360Dashboard.framework.id,academic_year:q360Year(),criterion_code:code,maturity_level:Number(sel?.value||1),quality_status:Number(sel?.value||1)>=4?'measured':'implemented',note:'',evidence_refs:[]});toast('Ölçüt olgunluğu kaydedildi.');await loadQuality360();}catch(err){toast(err.message,'error')}});
document.getElementById('q360CurriculumForm')?.addEventListener('submit',e=>{e.preventDefault();q360Json('/api/quality360/curriculum',{program_id:q360ProgramId(),academic_year:q360Year(),term:document.getElementById('q360CurrTerm').value,class_level:document.getElementById('q360CurrClass').value,course_code:document.getElementById('q360CurrCode').value.trim(),course_name:document.getElementById('q360CurrName').value.trim(),ects:Number(document.getElementById('q360CurrEcts').value||0),course_category:document.getElementById('q360CurrCategory').value,is_professional:document.getElementById('q360CurrProfessional').checked,is_program_specific:document.getElementById('q360CurrSpecific').checked,is_external_stakeholder_supported:document.getElementById('q360CurrStakeholder').checked,is_applied_or_current_tech:document.getElementById('q360CurrApplied').checked,quality_status:'implemented',notes:''},e.currentTarget)});
document.getElementById('q360StakeholderForm')?.addEventListener('submit',e=>{e.preventDefault();q360Json('/api/quality360/stakeholders',{program_id:q360ProgramId(),stakeholder_type:document.getElementById('q360StakeType').value,name:document.getElementById('q360StakeName').value.trim(),organization:'',engagement_type:document.getElementById('q360StakeEngagement').value,feedback:document.getElementById('q360StakeFeedback').value,resulting_action:document.getElementById('q360StakeAction').value,quality_status:'implemented',evidence_ref:''},e.currentTarget)});
document.getElementById('q360GraduateForm')?.addEventListener('submit',e=>{e.preventDefault();q360Json('/api/quality360/graduates',{program_id:q360ProgramId(),graduate_key:document.getElementById('q360GradKey').value.trim(),full_name:document.getElementById('q360GradName').value.trim(),graduation_year:Number(document.getElementById('q360GradYear').value)||null,employment_status:document.getElementById('q360GradStatus').value,employer:document.getElementById('q360GradEmployer').value.trim(),sector:'',job_title:document.getElementById('q360GradJob').value.trim(),related_field:null,notes:''},e.currentTarget)});
document.getElementById('q360FacultyForm')?.addEventListener('submit',e=>{e.preventDefault();q360Json('/api/quality360/faculty',{program_id:q360ProgramId(),title:document.getElementById('q360FacultyTitle').value,full_name:document.getElementById('q360FacultyName').value.trim(),email:document.getElementById('q360FacultyEmail').value.trim(),employment_type:document.getElementById('q360FacultyEmployment').value,expertise:document.getElementById('q360FacultyExpertise').value.trim(),highest_degree:'',industry_experience_years:0,weekly_course_hours:0,quality_status:'implemented'},e.currentTarget)});
document.getElementById('q360InfraForm')?.addEventListener('submit',e=>{e.preventDefault();const st=document.getElementById('q360InfraStatus').value;q360Json('/api/quality360/infrastructure',{program_id:q360ProgramId(),infrastructure_type:document.getElementById('q360InfraType').value,name:document.getElementById('q360InfraName').value.trim(),location:document.getElementById('q360InfraLocation').value.trim(),capacity:Number(document.getElementById('q360InfraCapacity').value)||null,quality_status:st,accessibility_status:st,isg_status:st,notes:''},e.currentTarget)});
document.getElementById('q360CycleForm')?.addEventListener('submit',e=>{e.preventDefault();q360Json('/api/quality360/quality-cycles',{program_id:q360ProgramId(),academic_year:q360Year(),criterion_code:document.getElementById('q360CycleCriterion').value,title:document.getElementById('q360CycleTitle').value.trim(),plan_text:document.getElementById('q360CyclePlan').value,do_text:document.getElementById('q360CycleDo').value,check_text:document.getElementById('q360CycleCheck').value,act_text:document.getElementById('q360CycleAct').value,owner:document.getElementById('q360CycleOwner')?.value.trim()||'Program Başkanı',due_date:document.getElementById('q360CycleDue')?.value||null,status:document.getElementById('q360CycleStatus').value,evidence_refs:[]},e.currentTarget)});
document.getElementById('q360GovForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST','/api/quality360/governance',{program_id:q360ProgramId(),body_type:document.getElementById('q360GovBody').value,meeting_date:document.getElementById('q360GovMeetingDate')?.value||null,meeting_no:document.getElementById('q360GovMeeting').value.trim(),decision_no:document.getElementById('q360GovDecision').value.trim(),subject:document.getElementById('q360GovSubject').value.trim(),decision_text:document.getElementById('q360GovText').value.trim(),related_criterion:'',status:'implemented',evidence_ref:''});e.currentTarget.reset();toast('Kurul kararı kaydedildi.');await Promise.all([loadQuality360(),loadQualityCalendar(),loadQ360GovernanceActions()]);}catch(err){toast(err.message,'error')}});
document.getElementById('q360CalendarForm')?.addEventListener('submit',async e=>{e.preventDefault();const start=document.getElementById('q360CalendarStart').value;if(!start)return;try{await api('POST','/api/quality360/calendar',{program_id:q360ProgramId(),academic_year:q360Year(),event_type:document.getElementById('q360CalendarType').value,title:document.getElementById('q360CalendarTitle').value.trim(),start_date:start,due_date:document.getElementById('q360CalendarDue').value||null,owner:document.getElementById('q360CalendarOwner').value.trim(),owner_role:document.getElementById('q360CalendarOwnerRole').value.trim(),criterion_code:document.getElementById('q360CalendarCriterion').value.trim(),status:document.getElementById('q360CalendarStatus').value,evidence_required:document.getElementById('q360CalendarEvidence').value.trim(),related_entity_type:'',related_entity_id:null,notes:document.getElementById('q360CalendarNotes').value.trim()});e.currentTarget.reset();toast('Kalite takvimine eklendi.');await loadQualityCalendar();}catch(err){toast(err.message,'error')}});
document.getElementById('q360EvidenceForm')?.addEventListener('submit',async e=>{e.preventDefault();const f=document.getElementById('q360EvidenceFile').files[0];if(!f)return;const fd=new FormData();fd.append('file',f);fd.append('criterion_code',document.getElementById('q360EvidenceCriterion').value);fd.append('category',document.getElementById('q360EvidenceCategory').value);fd.append('description',document.getElementById('q360EvidenceDescription').value);try{await api('POST',`/api/quality360/programs/${q360ProgramId()}/evidence`,fd);e.currentTarget.reset();toast('Kalite kanıtı yüklendi.');await loadQuality360();}catch(err){toast(err.message,'error')}});
document.getElementById('q360EvidenceList')?.addEventListener('click',e=>{const b=e.target.closest('[data-q360-evidence-download]');if(!b)return;downloadApi(`/api/quality360/evidence/${b.dataset.q360EvidenceDownload}/download`,b.dataset.name).catch(err=>toast(err.message,'error'));});

document.getElementById('createDemoScenario')?.addEventListener('click',async()=>{if(!confirm('Demo programı, 30 öğrenci ve örnek sınavlar oluşturulsun mu?'))return;const btn=document.getElementById('createDemoScenario');btn.disabled=true;btn.textContent='Hazırlanıyor…';try{const r=await api('POST','/api/pilot/demo-scenario',{});toast(r.message||'Demo hazır.');await refreshCore();await preparePilotOps();if(r.completed_exam_id){showPage('analytics');setTimeout(()=>{const sel=document.getElementById('analyticsExam');if(sel){sel.value=String(r.completed_exam_id);sel.dispatchEvent(new Event('change'));}},250);}}catch(e){toast(e.message,'error');}finally{btn.disabled=false;btn.textContent='Demo senaryosunu hazırla';}});

function onboardingKey(){return `douOnboarding615:${state.currentUser?.email||'user'}`;}
function onboardingSlides(){
  if(isQualityOnly())return [
    ['Kalite görünümünüz hazır','Ana ekranda hedef altı çıktılar, açık aksiyonlar ve tarama istisnaları önceliklendirilir.','Yönetim & Kalite'],
    ['Program Çıktısı’den soruya inin','Heatmap hücresinden riskli ders → Öğrenim Çıktısı → soru seviyesine kadar kök nedeni görün.','quality'],
    ['Kanıt zincirini kapatın','MIN/AVG/MAX, iyileştirme aksiyonları ve dönem kanıt ZIP’i Akreditasyon Merkezi’nde.','accreditation'],
    ['Pilot notunu bırakın','Bir ekran zor gelirse Pilot Geri Bildirim alanına doğrudan kaydedin.','feedback']
  ];
  if(hasAnyRole('program_head','department_head','faculty_admin','admin'))return [
    ['Rol bazlı ana ekran','Yalnız yönetim için anlamlı KPI ve iş kuyruğu öne çıkarılır.','dashboard'],
    ['Kaliteyi aşağı doğru inceleyin','Program → Program Çıktısı → ders → Öğrenim Çıktısı → soru zincirinde sorunun kaynağına inin.','quality'],
    ['Pilot hazırlığını doğrulayın','Kurumsal Pilot alanında UAT, backup, OBS ve sağlık kontrollerini takip edin.','import'],
    ['Geri bildirimi kapatın','Pilot kullanıcı notlarını inceleyin, karar notuyla çözüldü durumuna alın.','feedback']
  ];
  return [
    ['Dersinizden başlayın','Ana ekran yalnız sizin ders, sınav ve bekleyen işlerinizi gösterir.','dashboard'],
    ['Soru havuzunu yeniden kullanın','Soruları ders bazında biriktirin; birden fazla soruyu tek seferde sınava alın.','bank'],
    ['Kağıdı okutun, yalnız istisnayı kontrol edin','Toplu taramada sistem güvenli cevapları işler; belirsizleri size gösterir.','scan'],
    ['Analizi otomatik alın','Sınav onaylandığında Öğrenim ve Program Çıktıları sonuçları ve Excel raporu hazır olur.','analytics']
  ];
}
function renderOnboarding(){const slides=onboardingSlides(),i=Math.max(0,Math.min(state.onboardingStep,slides.length-1)),x=slides[i];document.getElementById('onboardingBody').innerHTML=`<div class="onboarding-number">0${i+1}</div><h2 id="onboardingTitle">${esc(x[0])}</h2><p>${esc(x[1])}</p><button class="onboarding-link ghost" data-action-call="closeOnboarding();showPage('${x[2]}')">Bu ekranı aç →</button>`;document.getElementById('onboardingProgress').textContent=`${i+1} / ${slides.length}`;document.getElementById('onboardingPrev').disabled=i===0;document.getElementById('onboardingNext').textContent=i===slides.length-1?'Başla':'Devam';}
function openOnboarding(force=false){if(!force&&localStorage.getItem(onboardingKey())==='done')return;state.onboardingStep=0;document.getElementById('onboardingModal').classList.remove('hidden');renderOnboarding();}
window.closeOnboarding=function(){localStorage.setItem(onboardingKey(),'done');document.getElementById('onboardingModal').classList.add('hidden');};
document.getElementById('onboardingClose')?.addEventListener('click',closeOnboarding);document.getElementById('onboardingPrev')?.addEventListener('click',()=>{state.onboardingStep=Math.max(0,state.onboardingStep-1);renderOnboarding();});document.getElementById('onboardingNext')?.addEventListener('click',()=>{const n=onboardingSlides().length;if(state.onboardingStep>=n-1){closeOnboarding();return;}state.onboardingStep++;renderOnboarding();});

document.addEventListener('keydown',e=>{if(e.altKey&&e.key.toLowerCase()==='n'){e.preventDefault();showPage('exams');}if(e.altKey&&e.key.toLowerCase()==='s'){e.preventDefault();showPage('scan');}if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)){const active=currentPageName();if(active==='bank'){e.preventDefault();document.getElementById('bankSearch')?.focus();}}});

async function loadIdentity(){
  state.authConfig=await api('GET','/api/auth/config');
  applyObsIntegrationPolicy();
  const pilotBox=document.getElementById('pilotLoginBox');const entraBox=document.getElementById('entraLoginBox');const obsBox=document.getElementById('obsLoginBox');
  if(!state.authConfig.auth_required){
    pilotBox?.classList.remove('hidden');entraBox?.classList.add('hidden');obsBox?.classList.add('hidden');
    try{state.pilotUsers=await api('GET','/api/auth/pilot-users');}
    catch(e){localStorage.removeItem('douPilotUser');state.pilotUsers=await api('GET','/api/auth/pilot-users');}
    const saved=localStorage.getItem('douPilotUser');
    const chosen=state.pilotUsers.some(x=>x.email===saved)?saved:(state.pilotUsers.find(x=>x.email==='pilot-admin@local')?.email||state.pilotUsers[0]?.email||'pilot-admin@local');
    const loginSelect=document.getElementById('loginPilotUser');
    if(loginSelect)loginSelect.innerHTML=state.pilotUsers.map(x=>`<option value="${esc(x.email)}" ${x.email===chosen?'selected':''}>${esc(x.display_name)} · ${esc(x.email)}</option>`).join('');
    const sideSelect=document.getElementById('pilotUserSelect');
    if(sideSelect)sideSelect.innerHTML=state.pilotUsers.map(x=>`<option value="${esc(x.email)}" ${x.email===chosen?'selected':''}>${esc(x.display_name)} · ${esc(x.email)}</option>`).join('');
    if(localStorage.getItem('douPilotSession')!=='1'){
      showLoginGate();
      return false;
    }
    localStorage.setItem('douPilotUser',chosen);
  }else if(state.authConfig.auth_provider==='obs'){
    pilotBox?.classList.add('hidden');entraBox?.classList.add('hidden');obsBox?.classList.remove('hidden');
    if(!sessionStorage.getItem('douEntraAccessToken')){showLoginGate();return false;}
  }else{
    pilotBox?.classList.add('hidden');entraBox?.classList.remove('hidden');obsBox?.classList.add('hidden');
    if(!sessionStorage.getItem('douEntraAccessToken')){showLoginGate();return false;}
  }
  state.currentUser=await api('GET','/api/auth/me');
  document.getElementById('currentUserName').textContent=state.currentUser.display_name||state.currentUser.email;
  document.getElementById('currentUserRoles').textContent=(state.currentUser.roles||[]).map(x=>x.role_label||x.role).join(' · ')||'Rol atanmamış';
  renderCurrentUserScope();applyRoleUI();enterApplication();setTimeout(()=>openOnboarding(false),350);return true;
}

/* Backward UI contract markers retained for regression compatibility:
   nav('managementNavGroup',management||hasAnyRole('quality'))
   Legacy instructor copy: Bugün sizi bekleyen akademik işleri tamamlayın.
*/
function applyRoleUI(){
  const nav=(id,show)=>{const el=document.getElementById(id);if(el)el.classList.toggle('hidden',!show);};
  const roles=roleNames();
  const qualityOnly=isQualityOnly();
  const admin=isAdmin();
  const instructor=roles.has('instructor')&&!admin&&!qualityOnly&&!roles.has('program_head')&&!roles.has('department_head')&&!roles.has('faculty_admin');
  const management=hasAnyRole('admin','program_head','department_head','faculty_admin');
  const qualityAccess=canAccreditation();

  document.body.classList.toggle('role-instructor-simple',instructor);
  document.body.classList.toggle('role-quality-simple',qualityOnly);
  document.body.classList.toggle('role-management-simple',management||admin);

  nav('usersNav',admin);
  nav('securityNav',admin);
  nav('acceptanceNav',admin);
  nav('pilotOpsNav',hasAnyRole('admin','quality'));
  nav('quality360Nav',qualityAccess);
  nav('programReviewNav',qualityAccess);
  nav('evidenceHubNav',qualityAccess);
  nav('institutionalReadinessNav',qualityAccess);
  nav('assessmentAssuranceNav',qualityAccess);
  nav('qualityNavGroup',qualityAccess);

  const workspaceGroup=document.getElementById('workspaceNavGroup');
  if(workspaceGroup)workspaceGroup.classList.toggle('hidden',qualityOnly);

  const analysisGroup=document.getElementById('analysisNavGroup');
  if(analysisGroup)analysisGroup.classList.toggle('hidden',false);

  /* Pure instructors see only the six screens they use every day. */
  ['programanalytics','studentcards'].forEach(page=>document.querySelectorAll(`.sidebar nav button[data-page="${page}"]`).forEach(el=>el.classList.toggle('hidden',instructor)));
  ['analytics','courseanalytics'].forEach(page=>document.querySelectorAll(`.sidebar nav button[data-page="${page}"]`).forEach(el=>el.classList.toggle('hidden',qualityOnly)));
  ['bank','exams','grade'].forEach(page=>document.querySelectorAll(`.sidebar nav button[data-page="${page}"]`).forEach(el=>el.classList.toggle('hidden',qualityOnly)));

  const showManagement=management||qualityOnly||admin;
  nav('managementNavGroup',showManagement);
  ['programs','courses','students'].forEach(page=>document.querySelectorAll(`.sidebar nav button[data-page="${page}"]`).forEach(el=>el.classList.toggle('hidden',!management)));
  nav('outcomesNav',management||qualityOnly);
  nav('curriculumMapNav',management||qualityOnly);
  nav('assessmentMeasuresNav',management||qualityOnly);
  nav('surveyNav',management||qualityOnly);
  nav('programAnalyticsNav',hasAnyRole('admin','quality','program_head','department_head','faculty_admin'));
  nav('studentCardsNav',hasAnyRole('admin','quality','program_head','department_head','faculty_admin'));

  /* Keep advanced groups collapsed unless the user's whole job is quality. */
  document.querySelectorAll('.nav-group').forEach(g=>{
    const shouldOpen=(instructor&&g.id==='workspaceNavGroup')||(qualityOnly&&g.id==='qualityNavGroup');
    g.classList.toggle('open',shouldOpen);
    const toggle=g.querySelector('.nav-group-toggle');if(toggle)toggle.setAttribute('aria-expanded',shouldOpen?'true':'false');
  });

  const examForm=document.getElementById('examForm');if(examForm)examForm.closest('.card')?.classList.toggle('hidden',qualityOnly);
  const bankForm=document.getElementById('bankForm');if(bankForm)bankForm.closest('.card')?.classList.toggle('hidden',qualityOnly);
  const uploadScan=document.getElementById('uploadScan');if(uploadScan)uploadScan.classList.toggle('hidden',qualityOnly);
  const scanFile=document.getElementById('scanFile');if(scanFile)scanFile.parentElement?.classList.toggle('hidden',qualityOnly);
  const regrade=document.getElementById('runRegrade');if(regrade)regrade.classList.toggle('hidden',qualityOnly);
  const gradeSave=document.querySelector('#gradeForm button[type="submit"]');if(gradeSave)gradeSave.classList.toggle('hidden',qualityOnly);
  const profileCard=document.getElementById('accredProfileForm')?.closest('.card');if(profileCard)profileCard.classList.toggle('hidden',!hasAnyRole('admin','quality'));
  const demoCard=document.getElementById('demoScenarioCard');if(demoCard)demoCard.classList.toggle('hidden',!admin||state.authConfig?.app_env==='production');
  refreshNavGroups();
}


async function prepareCurriculumMap(){
  if(!hasAnyRole('admin','quality','program_head','department_head','faculty_admin')){toast('Müfredat Haritası yönetim veya kalite rolü gerektirir.','error');showPage('dashboard');return;}
  if(!state.programs.length)await refreshCore();
  const programSel=document.getElementById('curriculumMapProgram');
  const versionSel=document.getElementById('curriculumMapVersion');
  if(!programSel||!versionSel)return;
  const previous=Number(programSel.value||0);
  programSel.innerHTML=(state.programs||[]).map(p=>`<option value="${p.id}">${esc(p.code)} · ${esc(p.name)}</option>`).join('');
  if(previous&&state.programs.some(p=>Number(p.id)===previous))programSel.value=String(previous);
  if(!programSel.value){versionSel.innerHTML='';renderCurriculumMapEmpty('Yetkili program bulunamadı.');return;}
  await loadCurriculumMapVersions();
}

async function loadCurriculumMapVersions(){
  const programId=Number(document.getElementById('curriculumMapProgram')?.value||0);
  const versionSel=document.getElementById('curriculumMapVersion');
  if(!programId||!versionSel)return;
  const current=Number(versionSel.value||0);
  try{
    const rows=await api('GET',`/api/programs/${programId}/curriculum-versions`);
    versionSel.innerHTML=(rows||[]).map(x=>`<option value="${x.id}">${esc(x.code)} · ${esc(x.name)}${x.status==='active'?' · Aktif':''}</option>`).join('');
    if(current&&rows.some(x=>Number(x.id)===current))versionSel.value=String(current);
    const preferred=(rows||[]).find(x=>x.status==='active')||rows?.[0];if(preferred&&!current)versionSel.value=String(preferred.id);
    if(!versionSel.value){renderCurriculumMapEmpty('Bu program için henüz müfredat versiyonu yok.');return;}
    await loadCurriculumMapWorkspace();
  }catch(e){toast(e.message,'error');renderCurriculumMapEmpty(e.message);}
}

function renderCurriculumMapEmpty(message){
  const summary=document.getElementById('curriculumMapSummary');const matrix=document.getElementById('curriculumMapMatrix');const gaps=document.getElementById('curriculumMapGaps');
  if(summary)summary.innerHTML='';if(matrix)matrix.innerHTML=`<p class="muted">${esc(message)}</p>`;if(gaps)gaps.innerHTML='<p class="muted">Analiz için müfredat verisi bekleniyor.</p>';
}

function curriculumGapList(title,items,tone='warn'){
  const rows=(items||[]);return `<section class="curriculum-gap-block ${tone}"><div><b>${esc(title)}</b><span>${rows.length}</span></div>${rows.length?`<ul>${rows.map(x=>`<li>${esc(typeof x==='string'?x:(x.code||x.program_outcome||x.course||'Kayıt'))}</li>`).join('')}</ul>`:'<p>Risk bulunmadı.</p>'}</section>`;
}

async function loadCurriculumMapWorkspace(){
  const versionId=Number(document.getElementById('curriculumMapVersion')?.value||0);if(!versionId)return;
  const status=document.getElementById('curriculumMapStatus');if(status){status.textContent='Yükleniyor';status.className='badge';}
  try{
    const [matrix,gaps]=await Promise.all([api('GET',`/api/curriculum-versions/${versionId}/outcome-map`),api('GET',`/api/curriculum-versions/${versionId}/outcome-map/gaps`)]);
    const sm=gaps.summary||{};
    document.getElementById('curriculumMapSummary').innerHTML=[
      ['Müfredat hazırlığı',`%${sm.readiness_score??0}`,'Coverage %60 + Mastery %40','primary'],
      ['PÇ kapsamı',`%${sm.coverage_percent??0}`,`${sm.program_outcome_count||0} Program Çıktısı`,''],
      ['Mastery kapsamı',`%${sm.mastery_percent??0}`,'M seviyesine ulaşan PÇ',''],
      ['Ders kapsamı',String(sm.course_count||0),'Müfredattaki ders','']
    ].map(x=>`<article class="${x[3]?'primary':''}"><span>${esc(x[0])}</span><b>${esc(x[1])}</b><small>${esc(x[2])}</small></article>`).join('');
    const editable=hasAnyRole('admin','program_head','department_head','faculty_admin');
    const pos=matrix.program_outcomes||[];const courses=matrix.courses||[];
    if(!pos.length||!courses.length){document.getElementById('curriculumMapMatrix').innerHTML='<p class="muted">Matris için müfredatta ders ve Program Çıktısı bulunmalıdır.</p>';}
    else{
      document.getElementById('curriculumMapMatrix').innerHTML=`<div class="curriculum-map-table-wrap"><table class="curriculum-map-table"><thead><tr><th class="course-col">Ders</th>${pos.map(po=>`<th title="${esc(po.description)}">${esc(po.code)}</th>`).join('')}</tr></thead><tbody>${courses.map(c=>`<tr><th class="course-col"><b>${esc(c.code)}</b><span>${esc(c.name)}</span><small>${c.semester_no?`${c.semester_no}. yarıyıl`:''}</small></th>${pos.map(po=>{const cell=c.cells?.[String(po.id)]||null;const level=cell?.level||'';return `<td><select class="irm-select level-${level||'none'}" data-version="${versionId}" data-catalog="${c.catalog_item_id}" data-po="${po.id}" data-existing="${level}" ${editable?'':'disabled'} aria-label="${esc(c.code)} ${esc(po.code)} katkı düzeyi"><option value="" ${!level?'selected':''}>—</option><option value="I" ${level==='I'?'selected':''}>I</option><option value="R" ${level==='R'?'selected':''}>R</option><option value="M" ${level==='M'?'selected':''}>M</option></select></td>`}).join('')}</tr>`).join('')}</tbody></table></div>${editable?'':'<p class="muted curriculum-map-readonly">Kalite rolü bu haritayı salt-okunur görüntüler. Düzenleme program/bölüm/fakülte yöneticisine aittir.</p>'}`;
    }
    const g=gaps.gaps||{};
    document.getElementById('curriculumMapGaps').innerHTML=curriculumGapList('Kapsanmayan PÇ',g.outcomes_without_coverage,'danger')+curriculumGapList('Mastery seviyesi olmayan PÇ',g.outcomes_without_mastery,'warn')+curriculumGapList('Tek derse bağımlı PÇ',g.single_course_dependencies,'warn')+curriculumGapList('Hiçbir PÇ’ye bağlanmamış ders',g.courses_without_outcome_mapping,'neutral')+curriculumGapList('I/R/M ilerleme gerilemesi',g.progression_warnings,'danger');
    if(status){status.textContent='Güncel';status.className='badge status-approved';}
  }catch(e){if(status){status.textContent='Hata';status.className='badge status-risk';}renderCurriculumMapEmpty(e.message);toast(e.message,'error');}
}



const measureTypeLabels={exam:'Sınav',assignment:'Ödev',project:'Proje',presentation:'Sunum',laboratory:'Laboratuvar',internship:'Staj',portfolio:'Portfolyo',capstone:'Bitirme / Capstone',practical:'Uygulama',peer_assessment:'Akran Değerlendirme'};
function rubricQuickCriteria(text){
  return String(text||'').split(/\n+/).map(x=>x.trim()).filter(Boolean).map((line,i)=>{const parts=line.split('|').map(x=>x.trim());const max=Number(parts[2]||0);if(!parts[0]||!parts[1]||!Number.isFinite(max)||max<=0)throw new Error(`${i+1}. rubrik satırı KOD | Ölçüt | Puan biçiminde olmalıdır.`);return {code:parts[0],title:parts[1],description:'',order_no:i+1,max_points:max,weight_percent:0,levels:[{code:'4',title:'Üstün',description:'Beklentinin belirgin biçimde üzerinde',score_percent:100,order_no:1},{code:'3',title:'Yeterli',description:'Beklentiyi karşılıyor',score_percent:75,order_no:2},{code:'2',title:'Gelişiyor',description:'Kısmen karşılıyor; iyileştirme gerekli',score_percent:50,order_no:3},{code:'1',title:'Başlangıç',description:'Temel gereklilikler eksik',score_percent:25,order_no:4}]};});
}
async function prepareAssessmentMeasures(){
  if(!state.courses.length)await refreshCore();const sel=document.getElementById('measureCourse');if(!sel)return;const keep=Number(sel.value||0);sel.innerHTML=(state.courses||[]).map(c=>`<option value="${c.id}">${esc(c.code)} · ${esc(c.name)}</option>`).join('');if(keep&&state.courses.some(c=>Number(c.id)===keep))sel.value=String(keep);if(!sel.value){document.getElementById('measureList').innerHTML='<p class="muted">Yetkili ders bulunamadı.</p>';return;}await loadAssessmentMeasures();
}
window.downloadObsGrades=async function(id){try{await downloadApi(`/api/courses/${Number(id)}/obs-grades.xlsx`,`OBS-notlar-ders-${Number(id)}.xlsx`);toast('OBS aktarım dosyası hazırlandı. Şablon düzenini OBS toplu not ekranıyla karşılaştırın.');}catch(e){toast(e.message,'error');}};
document.getElementById('poFormulaBtn')?.addEventListener('click',()=>{const c=(state.courses||[]).find(x=>x.id===Number(document.getElementById('outcomeCourse')?.value));if(!c)return toast('Önce ders seçin.','error');downloadApi(`/api/programs/${c.program_id}/po-formula.md`,'po-hesaplama-belgesi.md',true).catch(e=>toast(e.message,'error'));});
document.getElementById('measureImportCard')?.addEventListener('toggle',async e=>{if(!e.target.open)return;const cid=Number(document.getElementById('measureCourse')?.value||0),sel=document.getElementById('measureImportSelect');if(!cid)return;try{const ms=await api('GET',`/api/courses/${cid}/assessment-measures`);sel.innerHTML=ms.map(x=>`<option value="${x.id}">${esc(x.code)} · ${esc(x.title)}</option>`).join('')}catch(err){toast(err.message,'error')}});
document.getElementById('measureTemplateBtn')?.addEventListener('click',()=>{const id=document.getElementById('measureImportSelect').value;if(id)downloadApi(`/api/assessment-measures/${id}/results-template.xlsx`,`puan-sablonu-${id}.xlsx`).catch(e=>toast(e.message,'error'))});
async function measureImport(validate){const id=document.getElementById('measureImportSelect').value,f=document.getElementById('measureImportFile').files[0],box=document.getElementById('measureImportResult');if(!id||!f)return toast('Ölçme aracı ve dosya seçin.','error');const fd=new FormData();fd.append('file',f);
  try{const r=await api('POST',`/api/assessment-measures/${id}/results-import${validate?'?validate_only=true':''}`,fd);box.innerHTML=`<p class="ok-text">${validate?`${r.rows} satır geçerli.`:`${r.imported} öğrencinin puanı yüklendi.`}</p>`}
  catch(e){const lines=String(e.message||'').split('\n').filter(Boolean).map(l=>{try{const o=JSON.parse(l);return o&&o.row?`Satır ${o.row} (${o.student_no}): ${o.message}`:l}catch{return l}});box.innerHTML=`<div class="readiness-issue-list">${lines.slice(0,40).map(l=>`<div><i>!</i><span>${esc(l)}</span></div>`).join('')}</div>`}}
document.getElementById('measureValidateBtn')?.addEventListener('click',()=>measureImport(true));
document.getElementById('measureImportBtn')?.addEventListener('click',()=>measureImport(false));

async function loadAssessmentMeasures(){
  const courseId=Number(document.getElementById('measureCourse')?.value||0);if(!courseId)return;const status=document.getElementById('measureStatus');if(status)status.textContent='Yükleniyor';try{const [measures,rubrics]=await Promise.all([api('GET',`/api/courses/${courseId}/assessment-measures`),api('GET',`/api/courses/${courseId}/rubrics`)]);const active=rubrics.filter(x=>x.status==='active');const totalWeight=measures.filter(x=>x.status!=='archived').reduce((a,x)=>a+Number(x.weight_percent||0),0);const linked=measures.filter(x=>(x.outcomes||[]).length).length;document.getElementById('measureSummary').innerHTML=[['Ölçme aracı',String(measures.length),'Sınav + alternatif ölçmeler','primary'],['Plan ağırlığı',`%${totalWeight.toFixed(1)}`,'Ders içi toplam ağırlık',''],['ÖÇ bağlantısı',`${linked}/${measures.length||0}`,'Çıktı analitiğine hazır',''],['Aktif rubrik',String(active.length),'Yeniden kullanılabilir rubrik','']].map(x=>`<article class="${x[3]?'primary':''}"><span>${esc(x[0])}</span><b>${esc(x[1])}</b><small>${esc(x[2])}</small></article>`).join('');document.getElementById('measureList').innerHTML=measures.length?`<div class="measure-card-list">${measures.map(x=>`<article class="measure-card"><div><span class="badge">${esc(measureTypeLabels[x.measure_type]||x.measure_type)}</span><b>${esc(x.code)} · ${esc(x.title)}</b><small>${x.rubric_title?`Rubrik: ${esc(x.rubric_title)} · `:''}${(x.outcomes||[]).length} ÖÇ bağlantısı</small></div><div class="measure-card-stats"><span><b>%${Number(x.weight_percent||0).toFixed(0)}</b> ağırlık</span><span><b>${Number(x.max_points||0).toFixed(0)}</b> puan</span><span><b>%${Number(x.target_percent||0).toFixed(0)}</b> hedef</span></div></article>`).join('')}</div>`:'<div class="empty-state"><b>Henüz ölçme aracı yok</b><span>Sınav dışı ölçmeleri de aynı çıktı zincirine ekleyin.</span></div>';document.getElementById('rubricList').innerHTML=rubrics.length?`<div class="rubric-card-list">${rubrics.map(r=>`<article class="rubric-card"><div><b>${esc(r.title)}</b><small>v${r.version_no} · ${r.criteria.length} kriter · ${Number(r.max_points).toFixed(0)} puan</small></div><span class="badge ${r.status==='active'?'status-approved':''}">${r.status==='active'?'Aktif':'Taslak'}</span>${r.status!=='active'?`<button class="ghost small" type="button" data-rubric-activate="${r.id}">Aktifleştir</button>`:''}</article>`).join('')}</div>`:'<div class="empty-state"><b>Rubrik yok</b><span>İlk rubriğinizi sağdaki hızlı oluşturucudan hazırlayın.</span></div>';const rs=document.getElementById('measureRubric');rs.innerHTML='<option value="">Rubriksiz</option>'+active.map(r=>`<option value="${r.id}" data-max="${r.max_points}">${esc(r.title)} · ${Number(r.max_points).toFixed(0)} puan</option>`).join('');if(status){status.textContent='Güncel';status.className='badge status-approved';}}catch(e){if(status){status.textContent='Hata';status.className='badge status-risk';}toast(e.message,'error');}
}
document.getElementById('measureCourse')?.addEventListener('change',loadAssessmentMeasures);
document.getElementById('measureRubric')?.addEventListener('change',e=>{const o=e.target.selectedOptions?.[0];if(o?.dataset.max)document.getElementById('measureMax').value=o.dataset.max;});
document.getElementById('measureCreateForm')?.addEventListener('submit',async e=>{e.preventDefault();const courseId=Number(document.getElementById('measureCourse').value);try{await api('POST',`/api/courses/${courseId}/assessment-measures`,{code:document.getElementById('measureCode').value.trim(),title:document.getElementById('measureTitle').value.trim(),measure_type:document.getElementById('measureType').value,directness:'direct',rubric_template_id:Number(document.getElementById('measureRubric').value)||null,weight_percent:Number(document.getElementById('measureWeight').value||0),max_points:Number(document.getElementById('measureMax').value||100),target_percent:Number(document.getElementById('measureTarget').value||60),instructions:document.getElementById('measureInstructions').value||''});e.target.reset();document.getElementById('measureWeight').value='20';document.getElementById('measureMax').value='100';document.getElementById('measureTarget').value='60';toast('Ölçme aracı oluşturuldu.');await loadAssessmentMeasures();}catch(err){toast(err.message,'error');}});
document.getElementById('rubricCreateForm')?.addEventListener('submit',async e=>{e.preventDefault();const courseId=Number(document.getElementById('measureCourse').value);try{const criteria=rubricQuickCriteria(document.getElementById('rubricCriteria').value);const max_points=criteria.reduce((a,x)=>a+x.max_points,0);await api('POST',`/api/courses/${courseId}/rubrics`,{title:document.getElementById('rubricTitle').value.trim(),description:'',version_no:1,max_points,criteria});e.target.reset();toast('Rubrik taslağı oluşturuldu. Aktifleştirerek ölçme araçlarında kullanabilirsiniz.');await loadAssessmentMeasures();}catch(err){toast(err.message,'error');}});
document.getElementById('rubricList')?.addEventListener('click',async e=>{const b=e.target.closest('[data-rubric-activate]');if(!b)return;try{await api('POST',`/api/rubrics/${Number(b.dataset.rubricActivate)}/activate`,{});toast('Rubrik aktifleştirildi.');await loadAssessmentMeasures();}catch(err){toast(err.message,'error');}});
document.getElementById('curriculumMapProgram')?.addEventListener('change',loadCurriculumMapVersions);
document.getElementById('curriculumMapVersion')?.addEventListener('change',loadCurriculumMapWorkspace);
document.getElementById('curriculumMapMatrix')?.addEventListener('change',async e=>{
  const sel=e.target.closest('.irm-select');if(!sel)return;
  const versionId=Number(sel.dataset.version),catalogId=Number(sel.dataset.catalog),poId=Number(sel.dataset.po),level=sel.value,old=sel.dataset.existing||'';
  sel.disabled=true;document.getElementById('curriculumMapStatus').textContent='Kaydediliyor…';
  try{
    if(!level&&old)await api('DELETE',`/api/curriculum-versions/${versionId}/outcome-map/${catalogId}/${poId}`);
    else if(level)await api('PUT',`/api/curriculum-versions/${versionId}/outcome-map`,{catalog_item_id:catalogId,program_outcome_id:poId,coverage_level:level,note:''});
    await loadCurriculumMapWorkspace();toast('Müfredat haritası güncellendi.');
  }catch(err){toast(err.message,'error');await loadCurriculumMapWorkspace();}
});

document.getElementById('pilotUserSelect').addEventListener('change',e=>{localStorage.setItem('douPilotUser',e.target.value);localStorage.setItem('douPilotSession','1');location.reload();});
document.getElementById('loginPilotBtn')?.addEventListener('click',()=>{const email=document.getElementById('loginPilotUser')?.value;if(!email)return;localStorage.setItem('douPilotUser',email);localStorage.setItem('douPilotSession','1');location.reload();});
document.getElementById('loginPilotUser')?.addEventListener('keydown',e=>{if(e.key==='Enter')document.getElementById('loginPilotBtn')?.click();});
document.getElementById('logoutBtn')?.addEventListener('click',()=>{localStorage.removeItem('douPilotSession');sessionStorage.removeItem('douEntraAccessToken');location.reload();});
function setSectionCollapsed(key,collapsed){
  const section=document.querySelector(`[data-collapsible="${key}"]`);const btn=document.querySelector(`[data-collapse-toggle="${key}"]`);
  if(!section)return;
  section.classList.toggle('is-collapsed',collapsed);
  if(btn){btn.textContent=collapsed?'Göster':'Gizle';btn.setAttribute('aria-expanded',String(!collapsed));}
}
document.querySelectorAll('.section-collapse-toggle').forEach(btn=>btn.addEventListener('click',()=>{
  const key=btn.dataset.collapseToggle;const section=document.querySelector(`[data-collapsible="${key}"]`);
  setSectionCollapsed(key,!section?.classList.contains('is-collapsed'));
}));
document.getElementById('entraLoginBtn')?.addEventListener('click',()=>startEntraLogin().catch(e=>toast(e.message,'error')));
document.getElementById('obsLoginBox')?.addEventListener('submit',async ev=>{
  ev.preventDefault();
  const errBox=document.getElementById('obsLoginError');const btn=document.getElementById('obsLoginBtn');
  const username=document.getElementById('obsLoginUsername')?.value.trim();
  const password=document.getElementById('obsLoginPassword')?.value;
  if(!username||!password)return;
  errBox?.classList.add('hidden');btn.disabled=true;
  try{
    const r=await fetch('/api/auth/obs-login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password})});
    const data=await r.json();
    if(!r.ok)throw new Error(msgText(data));
    sessionStorage.setItem('douEntraAccessToken',data.access_token);
    location.reload();
  }catch(e){
    if(errBox){errBox.textContent=e.message||'Giriş başarısız.';errBox.classList.remove('hidden');}
    btn.disabled=false;
  }
});

function studentCardStatusLabel(status){return status==='achieved'?'Hedef sağlandı':status==='not_measured'?'Ölçülmedi':'Gelişim gerekli';}
function studentInitials(name=''){const p=String(name||'').trim().split(/\s+/).filter(Boolean);return (p.length>1?`${p[0][0]}${p[p.length-1][0]}`:(p[0]?.slice(0,2)||'Ö')).toLocaleUpperCase('tr-TR');}
function studentOutcomeTone(status){return status==='achieved'?'good':status==='not_measured'?'muted':'risk';}
function studentCardOutcomeRow(x){
  const att=Number(x.attainment_percent||0),target=Number(x.target_percent||0),delta=att-target,tone=studentOutcomeTone(x.status);
  const deltaText=x.status==='not_measured'?'Henüz ölçüm yok':`${delta>=0?'+':''}${delta.toFixed(1)} puan`;
  return `<article class="student-card-outcome ${esc(x.status||'')} ${tone}"><div class="student-outcome-main"><span class="outcome-code">${esc(x.code)}</span><div class="student-outcome-copy"><b>${esc(x.description||'')}</b><small>${studentCardStatusLabel(x.status)} · hedef %${target.toFixed(1)}</small></div><div class="student-outcome-score"><strong>%${att.toFixed(1)}</strong><span class="${tone}">${esc(deltaText)}</span></div></div><div class="student-card-meter"><i data-style="width:${Math.max(0,Math.min(100,att))}%"></i><em data-style="left:${Math.max(0,Math.min(100,target))}%" title="Hedef %${target.toFixed(1)}"></em></div></article>`;
}
async function loadStudentCardCandidates(){
  const select=document.getElementById('studentCardStudent');if(!select)return;
  const keep=select.value,q=(document.getElementById('studentCardSearch')?.value||'').trim();const params=new URLSearchParams({limit:'100',offset:'0'});if(q)params.set('q',q);
  state.students=await api('GET',`/api/students?${params.toString()}`);
  select.innerHTML=state.students.map(x=>`<option value="${x.id}">${esc(x.student_no)} · ${esc(x.full_name)}</option>`).join('')||'<option value="">Yetkili öğrenci yok</option>';
  if([...select.options].some(o=>o.value===keep))select.value=keep;
}
async function prepareStudentCards(){
  await refreshCore(false);await loadStudentCardCandidates();
  const select=document.getElementById('studentCardStudent');if(!select)return;
  const year=document.getElementById('studentCardYear');if(year&&!year.value)year.value=actionCenterYear();
  const freeze=document.getElementById('studentCardFreeze');if(freeze)freeze.classList.toggle('hidden',!hasAnyRole('admin','quality','program_head'));
  if(select.value)await loadStudentCard();
}
async function loadStudentCard(){
  const id=Number(document.getElementById('studentCardStudent')?.value||0),year=(document.getElementById('studentCardYear')?.value||'').trim();if(!id)return;
  try{
    const card=await api('GET',`/api/compliance/students/${id}/outcome-card${year?`?academic_year=${encodeURIComponent(year)}`:''}`);state.studentCard=card;
    const s=card.summary||{},overall=Number(card.overall_attainment_percent||0),riskLo=Number(s.risk_learning_outcomes||0),riskPo=Number(s.risk_program_outcomes||0),measuredLo=Number(s.measured_learning_outcomes||0),measuredPo=Number(s.measured_program_outcomes||0);
    const avatar=document.getElementById('studentCardAvatar');if(avatar)avatar.textContent=studentInitials(card.full_name);
    const name=document.getElementById('studentCardName');if(name)name.textContent=card.full_name||'Öğrenci';
    const meta=document.getElementById('studentCardMeta');if(meta)meta.textContent=`${card.student_no||'—'} · ${card.program_name||'Program bilgisi yok'}${card.class_name?` · ${card.class_name}`:''}`;
    const badges=document.getElementById('studentCardIdentityBadges');if(badges)badges.innerHTML=`<span>${esc(year||card.academic_year_cutoff||'Tüm dönemler')}</span><span>${card.course_count||0} ders</span><span>${measuredLo} ölçülen ÖÇ</span>`;
    const ring=document.getElementById('studentCardScoreRing');if(ring)ring.style.setProperty('--score',String(Math.max(0,Math.min(100,overall))));
    const score=document.getElementById('studentCardScore');if(score)score.textContent=`%${overall.toFixed(1)}`;
    const ready=document.getElementById('studentCardReadiness');if(ready){ready.textContent=card.graduate_ready?'Hazır':'İzleniyor';ready.className=card.graduate_ready?'ready':'watch';}
    const readyNote=document.getElementById('studentCardReadinessNote');if(readyNote)readyNote.textContent=card.graduate_ready?'Program çıktılarının tamamı hedef düzeyinde.':(riskPo?`${riskPo} program çıktısında gelişim gerekli.`:'Mezuniyet için yeterli ölçüm henüz oluşmadı.');
    const summary=document.getElementById('studentCardSummary');if(summary)summary.innerHTML=`
      <article class="metric-primary"><span>GENEL ÇIKTI BAŞARISI</span><b>%${overall.toFixed(1)}</b><small>${card.graduate_ready?'Program hedefleri sağlandı':'Akademik gelişim izleniyor'}</small></article>
      <article><span>ÖLÇÜLEN ÖÇ</span><b>${measuredLo}</b><small>${riskLo?`${riskLo} gelişim odağı`:'Riskli ÖÇ yok'}</small></article>
      <article><span>ÖLÇÜLEN PÇ</span><b>${measuredPo}</b><small>${riskPo?`${riskPo} gelişim odağı`:'Riskli PÇ yok'}</small></article>
      <article><span>DERS KAPSAMI</span><b>${card.course_count||0}</b><small>sonuçlandırılmış ölçüm</small></article>`;
    const po=document.getElementById('studentCardPO');if(po)po.innerHTML=(card.program_outcomes||[]).map(studentCardOutcomeRow).join('')||'<div class="empty-state"><b>PÇ ölçümü yok.</b><span>ÖÇ→PÇ eşleştirmesi ve onaylı sınav verisi bekleniyor.</span></div>';
    const strong=s.strongest,weak=s.weakest;
    const focus=document.getElementById('studentCardFocus');if(focus)focus.innerHTML=`<div class="student-focus-grid">
      <article class="good"><div class="focus-icon">↗</div><div><span>EN GÜÇLÜ ALAN</span><b>${strong?esc(strong.code||strong.course_code||'—'):'—'}</b><small>${strong?`${esc(strong.description||'')} · %${Number(strong.attainment_percent||0).toFixed(1)}`:'Henüz yeterli ölçüm yok'}</small></div></article>
      <article class="risk"><div class="focus-icon">◎</div><div><span>GELİŞİM ODAĞI</span><b>${weak?esc(weak.code||weak.course_code||'—'):'—'}</b><small>${weak?`${esc(weak.description||'')} · %${Number(weak.attainment_percent||0).toFixed(1)}`:'Henüz yeterli ölçüm yok'}</small></div></article>
      <article class="neutral"><div class="focus-icon">✓</div><div><span>ÖLÇÜM KAPSAMI</span><b>${measuredLo+measuredPo}</b><small>${measuredLo} ÖÇ ve ${measuredPo} PÇ doğrudan ölçülmüş durumda.</small></div></article>
    </div>`;
    const calc=document.getElementById('studentCardCalculation');if(calc)calc.textContent=card.calculation_note||'Sınav → soru → ÖÇ → PÇ zincirindeki doğrudan ölçümler kullanılır.';
    const verify=document.getElementById('studentCardVerification');if(verify)verify.textContent=card.verification_code||'—';
    const count=document.getElementById('studentCardCourseCount');if(count)count.textContent=`${card.course_count||0} ders`;
    const courses=document.getElementById('studentCardCourses');if(courses)courses.innerHTML=(card.courses||[]).map(course=>{
      const score=Number(course.course_attainment_percent||0),risk=Number(course.risk_count||0),tone=risk?'risk':'good';
      return `<section class="student-course-card ${tone}"><div class="student-course-head"><div class="student-course-title"><span>${esc(course.academic_year)} · ${esc(course.term)}</span><h4>${esc(course.course_code)} · ${esc(course.course_name)}</h4><small>${course.exam_count||0} ölçüm/sınav · ${(course.learning_outcomes||[]).length} ÖÇ</small></div><div class="student-course-score"><b>%${score.toFixed(1)}</b><span class="${tone}">${risk?`${risk} gelişim odağı`:'Hedeflerde'}</span></div></div><div class="student-course-progress"><i data-style="width:${Math.max(0,Math.min(100,score))}%"></i></div><div class="student-course-outcomes">${(course.learning_outcomes||[]).map(studentCardOutcomeRow).join('')||'<p class="muted">Bu derste bireysel ÖÇ ölçümü henüz oluşmadı.</p>'}</div></section>`;
    }).join('')||'<div class="empty-state"><b>Ders ölçümü yok.</b><span>Öğrencinin sonuçlandırılmış sınavı bulunmuyor.</span></div>';
    const badge=document.getElementById('studentCardStatus');if(badge){badge.textContent=(riskLo||riskPo)?'Gelişim izleniyor':(card.graduate_ready?'Mezuniyete hazır':'İyi durumda');badge.className=`badge ${(riskLo||riskPo)?'status-grading':'status-approved'}`;}
  }catch(e){toast(e.message,'error');}
}
document.getElementById('studentCardLoad')?.addEventListener('click',loadStudentCard);
let studentCardSearchTimer=null;document.getElementById('studentCardSearch')?.addEventListener('input',()=>{clearTimeout(studentCardSearchTimer);studentCardSearchTimer=setTimeout(async()=>{await loadStudentCardCandidates();if(document.getElementById('studentCardStudent')?.value)await loadStudentCard();},250);});
document.getElementById('studentCardStudent')?.addEventListener('change',loadStudentCard);
document.getElementById('studentCardPdf')?.addEventListener('click',async()=>{const id=Number(document.getElementById('studentCardStudent')?.value||0),year=(document.getElementById('studentCardYear')?.value||'').trim();if(!id)return;try{await downloadApi(`/api/compliance/students/${id}/outcome-card.pdf${year?`?academic_year=${encodeURIComponent(year)}`:''}`,`DOU-Student-Outcome-Card-${id}.pdf`);}catch(e){toast(e.message,'error')}});
document.getElementById('studentCardFreeze')?.addEventListener('click',async()=>{const id=Number(document.getElementById('studentCardStudent')?.value||0),year=(document.getElementById('studentCardYear')?.value||'').trim();if(!id||!year)return toast('Öğrenci ve akademik yıl seçin.','error');try{const x=await api('POST',`/api/compliance/students/${id}/outcome-snapshots`,{academic_year:year,snapshot_type:'graduation',freeze:true});toast(`Mezuniyet karnesi donduruldu · v${x.version_no}`);}catch(e){toast(e.message,'error')}});

async function prepareUsers(){
  if(!isAdmin()){toast('Kullanıcı yönetimi yalnız sistem yöneticisine açıktır.','error');showPage('dashboard');return;}
  try{
    await refreshCore();
    const [users,cfg]=await Promise.all([api('GET','/api/users'),api('GET','/api/auth/config')]);
    state.users=users;state.authConfig=cfg;
    const userOpts=users.map(u=>`<option value="${u.id}">${esc(u.display_name)} · ${esc(u.email)}</option>`).join('');
    document.getElementById('roleUser').innerHTML=userOpts||'<option value="">Kullanıcı yok</option>';
    document.getElementById('roleProgram').innerHTML='<option value="">—</option>'+state.programs.map(x=>`<option value="${x.id}">${esc(x.code)} · ${esc(x.name)}</option>`).join('');
    document.getElementById('roleCourse').innerHTML='<option value="">—</option>'+state.courses.map(x=>`<option value="${x.id}">${esc(x.code)} · ${esc(x.name)}</option>`).join('');
    syncRoleScopeUI();
    const e=cfg.entra||{};const badge=document.getElementById('entraReadiness');badge.textContent=e.configured?'Entra API yapılandırması hazır':'Entra tenant/client bekleniyor';badge.className=`badge ${e.configured?'status-approved':'status-ready'}`;
    renderUsers();
  }catch(e){toast(e.message,'error');}
}

function syncRoleScopeUI(){
  const role=document.getElementById('roleName')?.value||'instructor';
  const visible={
    instructor:{course:true,hint:'Öğretim Görevlisi yalnız seçilen ders kapsamında soru, sınav, optik, puanlama ve analiz işlemlerini yürütür.'},
    program_head:{program:true,hint:'Program Başkanı seçilen programın akademik, sınav, moderasyon, kalite ve akreditasyon süreçlerini yönetir.'},
    quality:{hint:'Kalite Müdürü kalite, Öğrenim ve Program Çıktıları, akreditasyon, iyileştirme ve kanıt süreçlerini kurum genelinde izler/yönetir.'}
  }[role]||{};
  const map=[['roleProgramWrap','roleProgram','program'],['roleCourseWrap','roleCourse','course'],['roleFacultyWrap','roleFaculty','faculty'],['roleDepartmentWrap','roleDepartment','department'],['roleProgramTextWrap','roleProgramText','programText']];
  map.forEach(([wrap,id,key])=>{const w=document.getElementById(wrap);if(w)w.classList.toggle('hidden',!visible[key]);if(!visible[key]){const el=document.getElementById(id);if(el)el.value='';}});
  const hint=document.getElementById('roleScopeHint');if(hint)hint.textContent=visible.hint||'';
}
document.getElementById('roleName')?.addEventListener('change',syncRoleScopeUI);

function renderUsers(){
  const box=document.getElementById('userList');
  box.innerHTML=state.users.length?state.users.map(u=>{
    const roles=(u.roles||[]).map(r=>`<span class="role-chip"><b>${esc(r.role_label||r.role)}</b>${r.program_id?` · P#${r.program_id}`:''}${r.course_id?` · D#${r.course_id}`:''}${r.scope_faculty?` · ${esc(r.scope_faculty)}`:''}${r.scope_department?` · ${esc(r.scope_department)}`:''}${r.scope_program?` · ${esc(r.scope_program)}`:''}<button data-action-call="removeUserRole(${u.id},${r.id})" title="Rolü kaldır">×</button></span>`).join('')||'<span class="muted">Rol yok</span>';
    return `<div class="user-row"><div><b>${esc(u.display_name)}</b><div class="muted">${esc(u.email)} · ${esc(u.auth_source)}${u.external_object_id?' · Entra bağlı':''}</div></div><div class="user-roles">${roles}</div><div><span class="${u.is_active?'pill-ok':'pill-warn'}">${u.is_active?'Aktif':'Pasif'}</span><button class="ghost small" data-action-call="toggleUserActive(${u.id},${u.is_active?'false':'true'})">${u.is_active?'Pasifleştir':'Aktifleştir'}</button></div></div>`;
  }).join(''):'<p class="muted">Kullanıcı yok.</p>';
}

document.getElementById('userForm').addEventListener('submit',async ev=>{
  ev.preventDefault();
  const payload={email:document.getElementById('userEmail').value.trim(),display_name:document.getElementById('userName').value.trim(),auth_source:document.getElementById('userAuthSource').value,external_object_id:document.getElementById('userObjectId').value.trim()||null,tenant_id:document.getElementById('userTenantId').value.trim()||null,is_active:true};
  try{await api('POST','/api/users',payload);ev.target.reset();toast('Kullanıcı oluşturuldu.');await prepareUsers();}catch(e){toast(e.message,'error');}
});

document.getElementById('roleForm').addEventListener('submit',async ev=>{
  ev.preventDefault();const userId=Number(document.getElementById('roleUser').value);if(!userId)return toast('Kullanıcı seçin.','error');
  const payload={role:document.getElementById('roleName').value,program_id:Number(document.getElementById('roleProgram').value)||null,course_id:Number(document.getElementById('roleCourse').value)||null,scope_faculty:document.getElementById('roleFaculty').value.trim(),scope_department:document.getElementById('roleDepartment').value.trim(),scope_program:document.getElementById('roleProgramText').value.trim()};
  if(payload.role==='instructor'&&!payload.course_id)return toast('Öğretim elemanı için ders seçin.','error');
  try{await api('POST',`/api/users/${userId}/roles`,payload);toast('Rol atandı.');await prepareUsers();}catch(e){toast(e.message,'error');}
});

document.getElementById('syncInstructorUsers').addEventListener('click',async()=>{try{const r=await api('POST','/api/users/sync-course-instructors',{});toast(`${r.created_users} kullanıcı, ${r.created_roles} ders rolü eklendi.`);await prepareUsers();}catch(e){toast(e.message,'error');}});
window.toggleUserActive=async function(id,value){try{await api('PATCH',`/api/users/${id}`,{is_active:value});toast('Kullanıcı durumu güncellendi.');await prepareUsers();}catch(e){toast(e.message,'error');}};
window.removeUserRole=async function(uid,rid){if(!confirm('Bu rol atamasını kaldırmak istiyor musunuz?'))return;try{await api('DELETE',`/api/users/${uid}/roles/${rid}`);toast('Rol kaldırıldı.');await prepareUsers();}catch(e){toast(e.message,'error');}};


async function prepareSecurity(){
  if(!isAdmin()){toast('Sistem güvenliği yalnız sistem yöneticisine açıktır.','error');showPage('dashboard');return;}
  try{
    const [diag,events]=await Promise.all([api('GET','/api/system/diagnostics'),api('GET','/api/security/events?limit=100')]);
    const sec=diag.security||{};const auth=diag.auth||{};const entra=auth.entra||{};
    const issues=sec.production_issues||[];const warnings=sec.production_warnings||[];
    const badge=document.getElementById('securityStatusBadge');
    badge.textContent=diag.app_env==='production'?(issues.length?'Production eksik':'Production hazır'):'Pilot güvenli mod';
    badge.className=`badge ${issues.length?'status-ready':'status-approved'}`;
    document.getElementById('securityDiagnostics').innerHTML=`<div class="kv"><span>Ortam</span><b>${esc(diag.app_env)}</b></div><div class="kv"><span>Sürüm</span><b>${esc(diag.version)}</b></div><div class="kv"><span>DB</span><b>${esc(diag.database_dialect)}</b></div><div class="kv"><span>HTTPS zorunlu</span><b>${sec.require_https?'Evet':'Hayır'}</b></div><div class="kv"><span>Security headers</span><b>${sec.security_headers?'Aktif':'Kapalı'}</b></div><div class="kv"><span>Upload sınırı</span><b>${esc(sec.max_upload_mb)} MB</b></div>${issues.length?`<div class="alert bad"><b>Production eksikleri</b><ul>${issues.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:''}${warnings.length?`<div class="alert warn"><b>Uyarılar</b><ul>${warnings.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:''}`;
    document.getElementById('securityEntra').innerHTML=`<div class="kv"><span>Entra yapılandırılmış</span><b>${entra.configured?'Evet':'Hayır'}</b></div><div class="kv"><span>Tenant</span><b>${entra.tenant_id_configured?'Tanımlı':'Bekleniyor'}</b></div><div class="kv"><span>Audience</span><b>${entra.audience_configured?'Tanımlı':'Bekleniyor'}</b></div><div class="kv"><span>Allowed client</span><b>${entra.allowed_client_ids_configured?'Tanımlı':'Bekleniyor'}</b></div><div class="kv"><span>API scope</span><b>${entra.required_scopes_configured?'Tanımlı':'Bekleniyor'}</b></div><div class="kv"><span>Tarayıcı PKCE scope</span><b>${entra.login_scopes_configured?'Tanımlı':'Bekleniyor'}</b></div><div class="kv"><span>Redirect URI</span><b>${entra.redirect_uri?'Tanımlı':'Bekleniyor'}</b></div><div class="kv"><span>Delegated user</span><b>${entra.require_delegated_user?'Zorunlu':'Opsiyonel'}</b></div>`;
    renderSecurityEvents(events);
    await prepareOperations().catch(()=>{});
  }catch(e){toast(e.message,'error');}
}
function renderSecurityEvents(rows){
  const box=document.getElementById('securityEvents');
  box.innerHTML=rows.length?`<table class="table"><thead><tr><th>Zaman</th><th>Olay</th><th>Seviye</th><th>IP</th><th>İstek</th><th>Request ID</th></tr></thead><tbody>${rows.map(x=>`<tr><td>${esc(x.created_at||'')}</td><td>${esc(x.event_type)}</td><td>${esc(x.severity)}</td><td>${esc(x.remote_addr||'')}</td><td>${esc((x.method||'')+' '+(x.path||''))}</td><td><code>${esc(x.request_id||'')}</code></td></tr>`).join('')}</tbody></table>`:'<p class="muted">Güvenlik olayı yok.</p>';
}
document.getElementById('refreshSecurityEvents')?.addEventListener('click',prepareSecurity);
async function pollOperationalJob(jobId,box,onDone){
  for(let i=0;i<120;i++){
    const j=await api('GET',`/api/operations/jobs/${jobId}`);
    if(box)box.innerHTML=`<div class="kv"><span>İş</span><b>#${esc(j.id)} · ${esc(j.job_type)}</b></div><div class="kv"><span>Durum</span><b>${esc(j.status)}</b></div><div class="kv"><span>İlerleme</span><b>%${esc(j.progress||0)}</b></div>${j.error_text?`<div class="alert bad">${esc(j.error_text)}</div>`:''}`;
    if(j.status==='succeeded'){if(onDone)onDone(j);return j;}
    if(['failed','cancelled'].includes(j.status))throw new Error(j.error_text||`İş ${j.status}`);
    await new Promise(r=>setTimeout(r,1500));
  }
  throw new Error('İş zaman aşımına uğradı; Operasyon kuyruğundan durumunu kontrol edin.');
}
async function prepareOperations(){
  const box=document.getElementById('operationsSummary');if(!box)return;
  try{const r=await api('GET','/api/operations/summary');const j=r.jobs||{},n=r.notifications||{},b=r.backup||{},v=r.backup_verification||{},a=r.automation||{};box.innerHTML=`<div class="grid3"><div class="readybox"><b>${esc(j.queued||0)}</b><span>Kuyrukta iş</span></div><div class="readybox"><b>${esc(j.running||0)}</b><span>Çalışan iş</span></div><div class="readybox"><b>${esc(j.failed||0)}</b><span>Başarısız iş</span></div></div><div class="kv"><span>Okunmamış operasyon bildirimi</span><b>${esc(n.unread||0)}</b></div><div class="kv"><span>Backup otomasyonu</span><b>${a.backup_enabled?'Aktif':'Kapalı'}</b></div><div class="kv"><span>Son backup</span><b>${esc(b.created_at||'Henüz yok')}</b></div><div class="kv"><span>Son backup doğrulaması</span><b>${esc(v.status||'Henüz yok')}</b></div><div class="kv"><span>Scheduler</span><b>${esc(a.scheduler_interval_seconds||60)} sn · bildirim penceresi ${esc(a.notification_lookahead_days||7)} gün</b></div>`;}catch(e){box.textContent=e.message;}
}
document.getElementById('refreshOperations')?.addEventListener('click',prepareOperations);
document.getElementById('runSchedulerNow')?.addEventListener('click',async()=>{try{const r=await api('POST','/api/operations/scheduler/run',{});toast(`Scheduler tamamlandı · ${r.notifications?.created||0} bildirim`);await prepareOperations();}catch(e){toast(e.message,'error');}});
document.getElementById('queueBackupNow')?.addEventListener('click',async()=>{const box=document.getElementById('operationsSummary');try{const j=await api('POST','/api/operations/jobs/backup',{});toast(`Backup işi #${j.id} kuyruğa alındı.`);await pollOperationalJob(j.id,box,()=>toast('Backup ve doğrulaması tamamlandı.'));await prepareOperations();}catch(e){toast(e.message,'error');await prepareOperations();}});

// 6.68 — User-facing notification center
function notificationSeverityClass(value){const v=String(value||'').toLowerCase();if(['critical','danger','error'].includes(v))return 'critical';if(['success','ready','ok'].includes(v))return 'success';if(['info','notice'].includes(v))return 'info';return 'warning';}
function notificationTime(value){if(!value)return '';try{return new Intl.DateTimeFormat('tr-TR',{dateStyle:'short',timeStyle:'short'}).format(new Date(value));}catch{return String(value);}}
async function refreshNotificationBadge(){
  const badge=document.getElementById('notificationBadge');if(!badge)return;
  try{const r=await api('GET','/api/operations/notifications?status=unread&limit=1&offset=0');const n=Number(r.total||0);badge.textContent=n>99?'99+':String(n);badge.classList.toggle('hidden',n<1);}catch{badge.classList.add('hidden');}
}
async function loadNotifications(){
  const list=document.getElementById('notificationList'),count=document.getElementById('notificationCount');if(!list)return;
  list.innerHTML='<p class="muted">Bildirimler yükleniyor…</p>';
  try{
    const r=await api('GET','/api/operations/notifications?limit=80&offset=0');const items=r.items||[];
    if(count)count.textContent=`${r.total||0} aktif bildirim`;
    list.innerHTML=items.length?items.map(n=>`<button type="button" class="notification-row ${notificationSeverityClass(n.severity)} ${n.status==='unread'?'unread':''}" data-notification-id="${Number(n.id)}" data-notification-url="${esc(n.action_url||'')}"><i class="notification-dot"></i><span class="notification-copy"><b>${esc(n.title||'Bildirim')}</b><span>${esc(n.body||'')}</span><small>${esc(notificationTime(n.created_at))}${n.status==='unread'?' · Okunmadı':' · Okundu'}</small></span><span class="notification-open">Aç →</span></button>`).join(''):'<div class="empty-state"><b>Aktif bildirim yok</b><span>Yaklaşan termin veya gecikmiş aksiyon oluştuğunda burada görünecek.</span></div>';
    await refreshNotificationBadge();
  }catch(e){list.innerHTML=`<p class="muted">${esc(e.message)}</p>`;if(count)count.textContent='Bildirimler alınamadı';}
}
async function openNotificationCenter(){document.getElementById('notificationModal')?.classList.remove('hidden');await loadNotifications();}
function closeNotificationCenter(){document.getElementById('notificationModal')?.classList.add('hidden');}
function openNotificationAction(url){const raw=String(url||'');const hash=raw.includes('#')?raw.split('#').pop():'';if(hash&&pageMeta[hash])showPage(hash);}
document.getElementById('notificationBtn')?.addEventListener('click',openNotificationCenter);
document.getElementById('notificationClose')?.addEventListener('click',closeNotificationCenter);
document.getElementById('notificationModal')?.addEventListener('click',e=>{if(e.target.id==='notificationModal')closeNotificationCenter();});
document.getElementById('notificationReadAll')?.addEventListener('click',async()=>{try{const r=await api('POST','/api/operations/notifications/read-all',{});toast(`${r.updated||0} bildirim okundu olarak işaretlendi.`);await loadNotifications();}catch(e){toast(e.message,'error');}});
document.getElementById('notificationList')?.addEventListener('click',async e=>{const row=e.target.closest('[data-notification-id]');if(!row)return;const id=Number(row.dataset.notificationId||0),url=row.dataset.notificationUrl||'';try{if(row.classList.contains('unread'))await api('PATCH',`/api/operations/notifications/${id}/read`,{});}catch{}closeNotificationCenter();openNotificationAction(url);await refreshNotificationBadge();});

document.getElementById('runEvidenceIntegrityScan')?.addEventListener('click',async()=>{
  const box=document.getElementById('evidenceIntegrityStatus');const btn=document.getElementById('runEvidenceIntegrityScan');
  try{btn.disabled=true;box.textContent='Bütünlük taraması worker kuyruğuna alınıyor…';const j=await api('POST','/api/operations/jobs/integrity-scan',{});await pollOperationalJob(j.id,box,(done)=>{const r=done.result||{},c=r.counts||{};box.innerHTML=`<div class="kv"><span>Kontrol edilen</span><b>${esc(r.checked||0)}</b></div><div class="kv"><span>Doğrulandı</span><b>${esc(c.verified||0)}</b></div><div class="kv"><span>Hash uyuşmazlığı</span><b>${esc(c.mismatch||0)}</b></div><div class="kv"><span>Eksik fiziksel dosya</span><b>${esc(c.missing||0)}</b></div>${(r.failures||[]).length?`<div class="alert bad"><b>Bütünlük uyarıları</b><ul>${r.failures.slice(0,20).map(x=>`<li>${esc(x.entity_type)} #${esc(x.id)} · ${esc(x.status)}</li>`).join('')}</ul></div>`:'<div class="alert good"><b>Bütünlük kontrolü temiz.</b></div>'}`;});toast('Kanıt bütünlüğü taraması tamamlandı.');}
  catch(e){box.textContent=e.message;toast(e.message,'error');}
  finally{btn.disabled=false;}
});


// 6.69 — Program Review & Evidence Hub 2.0
function programReviewStatusLabel(value){return ({draft:'Taslak',in_progress:'Hazırlanıyor',review:'İncelemede',final:'Final',archived:'Arşiv',not_started:'Başlanmadı',submitted:'İncelemede',approved:'Onaylı',changes_requested:'Revizyon istendi'})[value]||value||'—';}
function programReviewStatusClass(value){return value==='approved'||value==='final'?'success':value==='changes_requested'?'danger':value==='submitted'||value==='review'?'warning':'';}
function evidenceSourceLabel(value){return ({exam:'Sınav',quality:'Quality360',controlled:'Kontrollü doküman'})[value]||value||'Kanıt';}
function fillProgramSelect(el,includeAll=false){if(!el)return;const keep=el.value;el.innerHTML=(includeAll?'<option value="">Yetkili tüm programlar</option>':'')+(state.programs||[]).map(p=>`<option value="${Number(p.id)}">${esc(p.code)} · ${esc(p.name)}</option>`).join('');if([...el.options].some(o=>o.value===keep))el.value=keep;}
async function loadProgramReviewTemplates(){state.programReviewTemplates=await api('GET','/api/program-review/templates');const sel=document.getElementById('programReviewTemplate');if(sel){const keep=sel.value;sel.innerHTML=state.programReviewTemplates.map(x=>`<option value="${Number(x.id)}">${esc(x.code)} · ${esc(x.title)} · v${esc(x.version)}</option>`).join('')||'<option value="">Aktif şablon yok</option>';if([...sel.options].some(o=>o.value===keep))sel.value=keep;}}
async function prepareProgramReview(){
  if(!canAccreditation()){toast('Program Review kalite veya program yönetimi rolü gerektirir.','error');showPage('dashboard');return;}
  try{if(!state.programs.length)await refreshCore();fillProgramSelect(document.getElementById('programReviewProgram'));await loadProgramReviewTemplates();await loadProgramReviewList();}catch(e){toast(e.message,'error');}
}
async function loadProgramReviewList(){
  const pid=Number(document.getElementById('programReviewProgram')?.value||0),year=(document.getElementById('programReviewYear')?.value||'').trim(),box=document.getElementById('programReviewList');
  if(!pid){if(box)box.innerHTML='<p class="muted">Yetkili program bulunamadı.</p>';return;}
  const rows=await api('GET',`/api/programs/${pid}/program-reviews${year?`?academic_year=${encodeURIComponent(year)}`:''}`);state.programReviewRows=rows;
  if(box)box.innerHTML=rows.length?rows.map(x=>`<button type="button" class="compact-record program-review-record" data-program-review-id="${Number(x.id)}"><b>${esc(x.title)}</b><span>${esc(x.academic_year)} · Sürüm ${esc(x.review_no)} · ${esc(programReviewStatusLabel(x.status))}</span>${x.final_sha256?`<small>SHA ${esc(x.final_sha256.slice(0,16))}…</small>`:''}</button>`).join(''):'<div class="empty-state"><b>Bu dönem için Program Review yok</b><span>Aktif şablon seçip yeni değerlendirme oluşturun.</span></div>';
  const preferred=state.currentProgramReview?.review?.id;const target=rows.find(x=>Number(x.id)===Number(preferred))||rows[0];if(target)await loadProgramReview(target.id);else{state.currentProgramReview=null;document.getElementById('programReviewWorkspace')?.classList.add('hidden');const p=document.getElementById('programReviewProgress');if(p)p.innerHTML='Bir review seçin.';}
}
async function loadProgramReview(reviewId){
  const d=await api('GET',`/api/program-reviews/${Number(reviewId)}`);state.currentProgramReview=d;renderProgramReviewWorkspace(d);
}
function renderProgramReviewWorkspace(d){
  const review=d.review||{},sections=d.sections||[],progress=d.progress||{};document.getElementById('programReviewWorkspace')?.classList.remove('hidden');
  const title=document.getElementById('programReviewWorkspaceTitle');if(title)title.textContent=review.title||'Program Review';const meta=document.getElementById('programReviewWorkspaceMeta');if(meta)meta.textContent=`${review.academic_year||''} · Sürüm ${review.review_no||1} · ${programReviewStatusLabel(review.status)}${review.owner?` · ${review.owner}`:''}`;
  const badge=document.getElementById('programReviewStatusBadge');if(badge){badge.textContent=programReviewStatusLabel(review.status);badge.className=`badge ${programReviewStatusClass(review.status)}`;}
  const p=document.getElementById('programReviewProgress');if(p)p.innerHTML=`<div class="quality-kpi-grid"><article><span>Bölüm</span><b>${Number(progress.total||0)}</b></article><article><span>Onaylı</span><b>${Number(progress.approved||0)}</b></article><article><span>İlerleme</span><b>%${Number(progress.percent||0).toFixed(0)}</b></article></div><div class="progress"><i data-style="width:${Math.min(100,Number(progress.percent||0))}%"></i></div>${review.final_sha256?`<div class="kv"><span>Final SHA-256</span><b><code>${esc(review.final_sha256)}</code></b></div><button type="button" class="ghost small" data-pr-verify-final="${Number(review.id)}">Final snapshot bütünlüğünü doğrula</button>`:''}`;
  const final=review.status==='final'||review.status==='archived';const finalize=document.getElementById('programReviewFinalize');if(finalize){finalize.disabled=final;finalize.textContent=final?'Final mühürlendi':'Final snapshot oluştur';}
  const box=document.getElementById('programReviewSections');if(!box)return;box.innerHTML=sections.map(s=>{const evidence=s.evidence||[];const locked=final;return `<article class="program-review-section" data-pr-section="${Number(s.id)}"><div class="program-review-section-head"><div><h4>${Number(s.order_no)}. ${esc(s.title)}</h4><small>${esc(s.guidance||'')}</small></div><span class="badge ${programReviewStatusClass(s.status)}">${esc(programReviewStatusLabel(s.status))}</span></div><label>Anlatım<textarea data-pr-narrative ${locked?'disabled':''}>${esc(s.narrative||'')}</textarea></label><div class="program-review-meta-grid"><label>Katkı veren<input data-pr-contributor value="${esc(s.contributor_email||'')}" ${locked?'disabled':''}></label><label>Reviewer<input data-pr-reviewer value="${esc(s.reviewer_email||'')}" ${locked?'disabled':''}></label><label>Termin<input data-pr-due type="date" value="${esc(s.due_date||'')}" ${locked?'disabled':''}></label></div>${s.reviewer_note?`<div class="alert ${s.status==='changes_requested'?'warn':'good'}"><b>Reviewer notu</b><span>${esc(s.reviewer_note)}</span></div>`:''}<div class="program-review-evidence">${evidence.length?evidence.map(e=>`<span>${esc(evidenceSourceLabel(e.source_type))} #${Number(e.source_id)}${e.note?` · ${esc(e.note)}`:''}${!locked?` <button type="button" class="icon-x" data-pr-unlink="${Number(e.id)}" aria-label="Kanıt bağlantısını kaldır">×</button>`:''}</span>`).join(''):'<small class="muted">Henüz kanıt bağlı değil.</small>'}</div><label>Reviewer notu<input data-pr-review-note value="${esc(s.reviewer_note||'')}" placeholder="Onay veya revizyon gerekçesi" ${locked?'disabled':''}></label><div class="actions">${!locked?`<button type="button" class="ghost small" data-pr-save="${Number(s.id)}">Kaydet</button><button type="button" class="ghost small" data-pr-add-evidence="${Number(s.id)}">Kanıt ekle</button>${!['submitted','approved'].includes(s.status)?`<button type="button" class="primary small" data-pr-submit="${Number(s.id)}">İncelemeye gönder</button>`:''}${s.status==='submitted'?`<button type="button" class="primary small" data-pr-review="${Number(s.id)}" data-decision="approve">Onayla</button><button type="button" class="ghost small" data-pr-review="${Number(s.id)}" data-decision="changes_requested">Revizyon iste</button>`:''}`:''}</div></article>`;}).join('');
}
async function createDefaultProgramReviewTemplate(){
  const sections=[['profile','Program Profili','Programın amacı, kapsamı, öğrenci profili ve son değerlendirme döneminden bu yana değişiklikleri açıklayın.'],['students','Öğrenci Verileri','Başvuru, kayıt, devam, başarı, mezuniyet ve risk göstergelerini kanıtlarla yorumlayın.'],['curriculum','Müfredat','Müfredat yapısını, I/R/M kapsamını, ders katkılarını ve değişiklik gerekçelerini değerlendirin.'],['outcomes','Öğrenme Sonuçları','Doğrudan/dolaylı ölçüm, PÇ hedefleri, trendler ve hedef altı sonuçları yorumlayın.'],['stakeholders','Paydaş ve Mezun','İç/dış paydaş, mezun ve işveren geri bildirimlerini kararlarla ilişkilendirin.'],['faculty','Akademik Kadro','Kadro yeterliliği, uzmanlık dağılımı, iş yükü ve gelişim ihtiyaçlarını değerlendirin.'],['resources','Kaynaklar ve Altyapı','Laboratuvar, yazılım, bütçe, erişilebilirlik ve bakım durumunu değerlendirin.'],['swot','SWOT ve Riskler','Güçlü/zayıf yönler, fırsatlar, tehditler ve öncelikli riskleri kanıtlayın.'],['action','Eylem Planı','Öncelikli iyileştirmeleri sorumlu, termin, hedef ve doğrulama yöntemiyle tanımlayın.']].map((x,i)=>({key:x[0],title:x[1],guidance:x[2],order_no:i+1}));
  try{await api('POST','/api/program-review/templates',{code:'DOU-PR',version:'1.0',title:'DOU Periyodik Program Değerlendirmesi',description:'Kurumsal program review standart şablonu',sections});toast('Standart Program Review şablonu oluşturuldu.');}catch(e){if(!String(e.message).includes('zaten var'))throw e;toast('Standart şablon zaten mevcut.');}await loadProgramReviewTemplates();
}
async function prepareEvidenceHub(reset=false){
  if(!canAccreditation()){toast('Kanıt Merkezi kalite veya program yönetimi rolü gerektirir.','error');showPage('dashboard');return;}
  try{if(!state.programs.length)await refreshCore();fillProgramSelect(document.getElementById('evidenceHubProgram'),true);if(reset)state.evidenceHubOffset=0;renderEvidenceHubTarget();await loadEvidenceHub();}catch(e){toast(e.message,'error');}
}
function renderEvidenceHubTarget(){const box=document.getElementById('evidenceHubTarget');if(!box)return;const t=state.evidenceHubTargetSection;if(!t){box.classList.add('hidden');box.textContent='';return;}box.classList.remove('hidden');box.innerHTML=`<b>Kanıt bağlama hedefi:</b> ${esc(t.title)} <button type="button" class="ghost tiny" data-evidence-clear-target>Hedefi kaldır</button>`;}
function evidenceHubQueryString(){const params=new URLSearchParams();const program=document.getElementById('evidenceHubProgram')?.value,source=document.getElementById('evidenceHubSource')?.value,integrity=document.getElementById('evidenceHubIntegrity')?.value,tag=(document.getElementById('evidenceHubTag')?.value||'').trim(),q=(document.getElementById('evidenceHubQuery')?.value||'').trim();if(program)params.set('program_id',program);if(source)params.set('source_type',source);if(integrity)params.set('integrity_status',integrity);if(tag)params.set('tag',tag);if(q)params.set('q',q);params.set('limit',String(state.evidenceHubLimit));params.set('offset',String(state.evidenceHubOffset));return params.toString();}
async function loadEvidenceHub(){
  const r=await api('GET',`/api/evidence-hub?${evidenceHubQueryString()}`);state.evidenceHubTotal=Number(r.total||0);const items=r.items||[],box=document.getElementById('evidenceHubList'),count=document.getElementById('evidenceHubCount');if(count)count.textContent=`${state.evidenceHubTotal} kanıt · ${state.evidenceHubOffset+1}-${Math.min(state.evidenceHubOffset+items.length,state.evidenceHubTotal)}`;
  if(box)box.innerHTML=items.length?items.map(x=>`<article class="evidence-hub-row"><div><h4>${esc(x.title)}</h4><p>${esc(x.description||x.context||'')}</p><div class="evidence-hub-meta"><span class="evidence-hub-chip">${esc(evidenceSourceLabel(x.source_type))}</span>${x.category?`<span class="evidence-hub-chip">${esc(x.category)}</span>`:''}<span class="evidence-hub-chip ${x.integrity_status==='verified'?'good':x.integrity_status==='mismatch'||x.integrity_status==='missing'?'bad':''}">${esc(x.integrity_status||'unchecked')}</span><span class="evidence-hub-chip">${Number(x.review_usage_count||0)} review kullanımı</span>${(x.tags||[]).map(t=>`<span class="evidence-hub-chip">#${esc(t.label)}</span>`).join('')}</div></div><div class="evidence-hub-actions"><button type="button" class="ghost tiny" data-evidence-detail="${esc(x.source_type)}:${Number(x.source_id)}">Detay</button>${x.download_url?`<button type="button" class="ghost tiny" data-evidence-download="${esc(x.download_url)}">Aç</button>`:''}${state.evidenceHubTargetSection?`<button type="button" class="primary tiny" data-evidence-link="${esc(x.source_type)}:${Number(x.source_id)}">Bölüme bağla</button>`:''}</div></article>`).join(''):'<div class="empty-state"><b>Kanıt bulunamadı</b><span>Filtreleri değiştirip tekrar arayın.</span></div>';
  const page=Math.floor(state.evidenceHubOffset/state.evidenceHubLimit)+1,totalPages=Math.max(1,Math.ceil(state.evidenceHubTotal/state.evidenceHubLimit));const info=document.getElementById('evidenceHubPageInfo');if(info)info.textContent=`${page} / ${totalPages}`;const prev=document.getElementById('evidenceHubPrev'),next=document.getElementById('evidenceHubNext');if(prev)prev.disabled=state.evidenceHubOffset<=0;if(next)next.disabled=state.evidenceHubOffset+state.evidenceHubLimit>=state.evidenceHubTotal;
}
async function showEvidenceHubDetail(sourceType,sourceId){const d=await api('GET',`/api/evidence-hub/item/${encodeURIComponent(sourceType)}/${Number(sourceId)}`);state.evidenceHubCurrent={sourceType,sourceId,detail:d};const e=d.evidence||{},box=document.getElementById('evidenceHubDetail');if(!box)return;box.innerHTML=`<h4>${esc(e.title||'Kanıt')}</h4><div class="kv"><span>Kaynak</span><b>${esc(evidenceSourceLabel(sourceType))} #${Number(sourceId)}</b></div><div class="kv"><span>Bağlam</span><b>${esc(e.context||'—')}</b></div><div class="kv"><span>SHA-256</span><b><code>${esc(e.sha256||'—')}</code></b></div><div class="kv"><span>Bütünlük</span><b>${esc(e.integrity_status||'unchecked')}</b></div><div class="evidence-detail-tags">${(d.tags||[]).map(t=>`<span class="evidence-hub-chip">#${esc(t.label)} <button type="button" class="icon-x" data-evidence-delete-tag="${Number(t.id)}">×</button></span>`).join('')||'<span class="muted">Etiket yok.</span>'}</div><div class="row"><input data-evidence-new-tag placeholder="Yeni etiket"><button type="button" class="ghost small" data-evidence-add-tag>Etiket ekle</button></div><h4>Kullanım zinciri</h4><div class="evidence-detail-usage">${(d.program_review_usage||[]).length?(d.program_review_usage||[]).map(u=>`<div><b>${esc(u.review_title)}</b><span>${esc(u.section_title)} · ${esc(programReviewStatusLabel(u.status))}</span></div>`).join(''):'<div class="muted">Henüz Program Review bölümünde kullanılmıyor.</div>'}</div>`;}
async function linkEvidenceToReview(sourceType,sourceId){const t=state.evidenceHubTargetSection;if(!t)return toast('Önce Program Review bölümünden Kanıt ekle seçin.','error');const data=await workflowForm({eyebrow:'KANIT BAĞLANTISI',title:'Kanıtı Program Review bölümüne bağla',description:t.title||'Seçili bölüm',submitLabel:'Kanıtı bağla',fields:[{name:'note',label:'Bağlantı notu',type:'textarea',rows:3,placeholder:'Bu kanıtın bölümü nasıl desteklediğini kısaca yazın.'}]});if(!data)return;await api('POST',`/api/program-review-sections/${Number(t.id)}/evidence`,{source_type:sourceType,source_id:Number(sourceId),note:data.note||''});toast('Kanıt Program Review bölümüne bağlandı.');const rid=t.reviewId;state.evidenceHubTargetSection=null;showPage('programreview');setTimeout(()=>loadProgramReview(rid).catch(e=>toast(e.message,'error')),80);}

document.getElementById('programReviewReload')?.addEventListener('click',()=>loadProgramReviewList().catch(e=>toast(e.message,'error')));
document.getElementById('programReviewProgram')?.addEventListener('change',()=>{state.currentProgramReview=null;loadProgramReviewList().catch(e=>toast(e.message,'error'));});
document.getElementById('programReviewYear')?.addEventListener('change',()=>{state.currentProgramReview=null;loadProgramReviewList().catch(e=>toast(e.message,'error'));});
document.getElementById('programReviewCreateDefaultTemplate')?.addEventListener('click',()=>createDefaultProgramReviewTemplate().catch(e=>toast(e.message,'error')));
document.getElementById('programReviewCreate')?.addEventListener('click',async()=>{const pid=Number(document.getElementById('programReviewProgram')?.value||0),tid=Number(document.getElementById('programReviewTemplate')?.value||0),year=(document.getElementById('programReviewYear')?.value||'').trim();if(!pid||!tid||!year)return toast('Program, akademik yıl ve şablon seçin.','error');try{const r=await api('POST',`/api/programs/${pid}/program-reviews`,{template_id:tid,academic_year:year,owner:state.currentUser?.email||''});state.currentProgramReview={review:r};toast('Program Review oluşturuldu.');await loadProgramReviewList();}catch(e){toast(e.message,'error');}});
document.getElementById('programReviewList')?.addEventListener('click',e=>{const b=e.target.closest('[data-program-review-id]');if(b)loadProgramReview(Number(b.dataset.programReviewId)).catch(err=>toast(err.message,'error'));});
document.getElementById('programReviewSections')?.addEventListener('click',async e=>{const card=e.target.closest('[data-pr-section]');if(!card)return;const sid=Number(card.dataset.prSection),rid=Number(state.currentProgramReview?.review?.id||0);try{if(e.target.closest('[data-pr-save]')){await api('PATCH',`/api/program-review-sections/${sid}`,{narrative:card.querySelector('[data-pr-narrative]')?.value||'',contributor_email:card.querySelector('[data-pr-contributor]')?.value||'',reviewer_email:card.querySelector('[data-pr-reviewer]')?.value||'',due_date:card.querySelector('[data-pr-due]')?.value||null});toast('Bölüm kaydedildi.');await loadProgramReview(rid);}else if(e.target.closest('[data-pr-submit]')){await api('POST',`/api/program-review-sections/${sid}/submit`,{});toast('Bölüm reviewer incelemesine gönderildi.');await loadProgramReview(rid);}else{const review=e.target.closest('[data-pr-review]');if(review){await api('POST',`/api/program-review-sections/${sid}/review`,{decision:review.dataset.decision,note:card.querySelector('[data-pr-review-note]')?.value||''});toast(review.dataset.decision==='approve'?'Bölüm onaylandı.':'Revizyon istendi.');await loadProgramReview(rid);return;}const add=e.target.closest('[data-pr-add-evidence]');if(add){const sec=(state.currentProgramReview?.sections||[]).find(x=>Number(x.id)===sid);state.evidenceHubTargetSection={id:sid,reviewId:rid,title:sec?.title||`Bölüm #${sid}`};showPage('evidencehub');return;}const unlink=e.target.closest('[data-pr-unlink]');if(unlink){if(!confirm('Kanıt bağlantısı kaldırılsın mı?'))return;await api('DELETE',`/api/program-review-evidence-links/${Number(unlink.dataset.prUnlink)}`);toast('Kanıt bağlantısı kaldırıldı.');await loadProgramReview(rid);}}}catch(err){toast(err.message,'error');}});
document.getElementById('programReviewFinalize')?.addEventListener('click',async()=>{const id=Number(state.currentProgramReview?.review?.id||0);if(!id)return;if(!confirm('Tüm onaylı bölümler immutable final snapshot olarak mühürlensin mi?'))return;try{await api('POST',`/api/program-reviews/${id}/finalize`,{});toast('Program Review final snapshot ile mühürlendi.');await loadProgramReview(id);}catch(e){toast(e.message,'error');}});
document.getElementById('programReviewProgress')?.addEventListener('click',async e=>{const b=e.target.closest('[data-pr-verify-final]');if(!b)return;try{const r=await api('GET',`/api/program-reviews/${Number(b.dataset.prVerifyFinal)}/final-snapshot`);toast(r.integrity_status==='verified'?'Final snapshot SHA doğrulandı.':'Final snapshot SHA uyuşmuyor!',r.integrity_status==='verified'?'ok':'error');}catch(err){toast(err.message,'error');}});
document.getElementById('evidenceHubSearch')?.addEventListener('click',()=>{state.evidenceHubOffset=0;loadEvidenceHub().catch(e=>toast(e.message,'error'));});
document.getElementById('evidenceHubProgram')?.addEventListener('change',()=>{state.evidenceHubOffset=0;loadEvidenceHub().catch(e=>toast(e.message,'error'));});
document.getElementById('evidenceHubPrev')?.addEventListener('click',()=>{state.evidenceHubOffset=Math.max(0,state.evidenceHubOffset-state.evidenceHubLimit);loadEvidenceHub().catch(e=>toast(e.message,'error'));});
document.getElementById('evidenceHubNext')?.addEventListener('click',()=>{if(state.evidenceHubOffset+state.evidenceHubLimit<state.evidenceHubTotal){state.evidenceHubOffset+=state.evidenceHubLimit;loadEvidenceHub().catch(e=>toast(e.message,'error'));}});
document.getElementById('evidenceHubList')?.addEventListener('click',async e=>{const detail=e.target.closest('[data-evidence-detail]'),link=e.target.closest('[data-evidence-link]'),download=e.target.closest('[data-evidence-download]');try{if(detail){const [t,id]=detail.dataset.evidenceDetail.split(':');await showEvidenceHubDetail(t,Number(id));}else if(link){const [t,id]=link.dataset.evidenceLink.split(':');await linkEvidenceToReview(t,Number(id));}else if(download){await downloadApi(download.dataset.evidenceDownload,'evidence',true);}}catch(err){toast(err.message,'error');}});
document.getElementById('evidenceHubTarget')?.addEventListener('click',e=>{if(e.target.closest('[data-evidence-clear-target]')){state.evidenceHubTargetSection=null;renderEvidenceHubTarget();loadEvidenceHub().catch(err=>toast(err.message,'error'));}});
document.getElementById('evidenceHubDetail')?.addEventListener('click',async e=>{const cur=state.evidenceHubCurrent;if(!cur)return;try{if(e.target.closest('[data-evidence-add-tag]')){const label=(document.getElementById('evidenceHubDetail')?.querySelector('[data-evidence-new-tag]')?.value||'').trim();if(!label)return toast('Etiket yazın.','error');await api('POST',`/api/evidence-hub/item/${cur.sourceType}/${cur.sourceId}/tags`,{label});toast('Etiket eklendi.');await showEvidenceHubDetail(cur.sourceType,cur.sourceId);await loadEvidenceHub();}const del=e.target.closest('[data-evidence-delete-tag]');if(del){await api('DELETE',`/api/evidence-hub/tags/${Number(del.dataset.evidenceDeleteTag)}`);toast('Etiket kaldırıldı.');await showEvidenceHubDetail(cur.sourceType,cur.sourceId);await loadEvidenceHub();}}catch(err){toast(err.message,'error');}});
document.getElementById('evidenceHubDuplicates')?.addEventListener('click',async()=>{try{const pid=document.getElementById('evidenceHubProgram')?.value;const r=await api('GET',`/api/evidence-hub/duplicates/sha256${pid?`?program_id=${encodeURIComponent(pid)}`:''}`);const box=document.getElementById('evidenceHubDetail');box.innerHTML=`<h4>Duplicate SHA-256 grupları</h4><p class="muted">Aynı içerik hash'ine sahip ${Number(r.duplicate_groups||0)} grup.</p>${(r.items||[]).length?(r.items||[]).map(g=>`<div class="duplicate-group"><b>${Number(g.count)} kayıt</b><code>${esc(g.sha256)}</code>${(g.items||[]).map(i=>`<div>${esc(evidenceSourceLabel(i.source_type))} #${Number(i.source_id)} · ${esc(i.title)}</div>`).join('')}</div>`).join(''):'<div class="empty-state"><b>Duplicate kanıt yok</b><span>Aynı SHA-256 ile tekrar kayıt tespit edilmedi.</span></div>'}`;}catch(e){toast(e.message,'error');}});

syncQuestionTypeUI();syncBankTypeUI();
(async()=>{try{await handleEntraCallback();const entered=await loadIdentity();if(!entered)return;await checkReady();await refreshCore().catch(()=>{});await refreshNotificationBadge().catch(()=>{});showPage(isQualityOnly()?'quality360':'dashboard');}catch(e){showLoginGate();toast(e.message,'error');document.getElementById('readyText').textContent='Kimlik doğrulama gerekli';}})();

// 6.20 contextual guide + Excel Data Center
const GUIDE_PAGES={
  coursestudents:{title:'Ders Öğrencileri',steps:['Dersi seçin.','Derse kayıtlı öğrencileri kontrol edin.','Eksik kayıt varsa OBS/akademik yönetim sürecine yönlendirin.'],tip:'Öğretim elemanı ana öğrenci verisini düzenlemek zorunda değildir.'},
  mycourses:{title:'Derslerim',steps:['Dersinizi seçin.','Ders çalışma alanından ilgili sekmeyi açın.','Sınavdan analize kadar aynı ders bağlamında ilerleyin.'],tip:'Ders bağlamını koruyun; sistem yalnız ilgili işlemleri öne çıkarır.'},
  courseanalytics:{title:'Ders Analizi',steps:['Dersi seçin.','Öğrenim Çıktısı hedef açıklarını inceleyin.','Dönem trendini kontrol edin.','Sorunlu sınava drill-down yapın.'],tip:'Tek sınavdan çok tekrar eden dönemsel sorunlara odaklanın.'},
  programanalytics:{title:'Program Analizi',steps:['Programı seçin.','Program Çıktısı hedef karşılama durumunu inceleyin.','Riskli veya ölçülmeyen dersleri açın.','Açık PUKÖ aksiyonlarını kalite merkezinde kapatın.'],tip:'Program analizi sınav verisini yönetim kararına dönüştürür.'},
  dashboard:{title:'Genel Bakış',steps:['İş kuyruğundaki uyarıları kontrol edin.','Devam eden sınavınız varsa kaldığınız yerden açın.','Rolünüze göre hızlı işlem düğmesini kullanın.'],tip:'Kırmızı/turuncu uyarılar önce ele alınması gereken işleri gösterir.'},
  data:{title:'Akademik Veri',steps:['Program, ders ve öğrenci kayıtlarını kontrol edin.','Toplu veri için üstteki Excel Yükle düğmesini kullanın.','Öğrencileri ilgili derse kaydedin.'],tip:'Aynı akademik yıl ve dönem için ders kodlarını tutarlı kullanın.'},
  outcomes:{title:'Öğrenim ve Program Çıktıları',steps:['Ders öğrenme çıktılarını tanımlayın.','Program çıktılarını tanımlayın.','Öğrenim Çıktısı → Program Çıktısı katkısını 1–5 ölçeğinde eşleyin.'],tip:'Sınav soruları en az bir Öğrenim Çıktısı ile eşleşmeden sınav hazır duruma alınamaz.'},
  bank:{title:'Soru Havuzu',steps:['Dersi seçin.','Test veya klasik soru oluşturun.','Klasik soruda beklenen cevap, Bloom, Öğrenim Çıktısı ve rubriği tamamlayın.','Excel ile toplu soru aktarımında önce Doğrula adımını çalıştırın.'],tip:'Klasik rubrik kriterlerinin Öğrenim Çıktısı eşleşmesi zorunludur.'},
  exams:{title:'Sınav Merkezi',steps:['Sınav bilgilerini oluşturun.','Öğrencileri sınava atayın.','Soruları ekleyin ve puan toplamını 100 yapın.','Hazırlık kontrolünü geçip sınavı Hazır durumuna alın.','Kişiselleştirilmiş A/B/C/D kağıtları üretin.'],tip:'Hazırlık kontrolündeki kırmızı maddeler çözülmeden sınav yayınlanmaz.'},
  scan:{title:'Optik & Kontrol',steps:['Sınavı Değerlendirme moduna alın.','ADF/PDF taramasını yükleyin.','Otomatik kabul edilenleri ve inceleme kuyruğunu kontrol edin.','Belirsiz işaretleri görsel kanıtla karara bağlayın.'],tip:'Klasik sayfalar öğrenci ve soru ile QR üzerinden otomatik ilişkilendirilir.'},
  grade:{title:'Klasik Puanlama',steps:['Sınav ve öğrenciyi seçin.','Taranmış klasik cevabı görüntüleyin.','Her rubrik kriterini ayrı puanlayın.','Kaydet ve Sonraki ile ilerleyin.'],tip:'Toplam klasik puanı elle yazılmaz; rubrik puanlarından otomatik hesaplanır.'},
  analytics:{title:'Sınav Analizi',steps:['Sınavı seçin.','Not, soru ve Öğrenim ve Program Çıktıları sonuçlarını inceleyin.','Küçük örneklem uyarılarını dikkate alın.','Riskli çıktılar için kalite aksiyonu başlatın.'],tip:'Devamsız, mazeretli ve geçersiz öğrenciler ölçüm paydasına dahil edilmez.'},
  quality:{title:'Kalite Dashboard',steps:['Dönem ve programı seçin.','Hedef altı Öğrenim ve Program Çıktıları ve riskli soruları açın.','Kök nedene kadar drill-down yapın.','PDCA aksiyonunu hedef ve doğrulama yöntemiyle takip edin.'],tip:'Aksiyon, gerçekleşen sonuç ve etkililik doğrulanmadan kapatılmaz.'},
  accreditation:{title:'Akreditasyon',steps:['Akreditasyon profilini/dönemini seçin.','Sınavları ve doğrudan ölçüm kanıtlarını bağlayın.','Eksik kanıt/iyileştirme uyarılarını kapatın.','Dönem paketini dondurup kanıt ZIP’ini üretin.'],tip:'Ölçüm → iyileştirme → tekrar ölçüm zinciri kanıtla birlikte korunur.'},
  programreview:{title:'Program Review',steps:['Program ve akademik yılı seçin.','Review şablonuyla dönem kaydı oluşturun.','Bölümlerde contributor ve reviewer atayın.','Kanıt Merkezi’nden gerçek kanıtları bağlayın.','Tüm bölümler onaylandığında final snapshot oluşturun.'],tip:'Final snapshot sonrası anlatım ve kanıt bağlantıları değiştirilemez; yeni değerlendirme sürümü açılmalıdır.'},
  evidencehub:{title:'Kanıt Merkezi',steps:['Program, kaynak veya bütünlük durumuyla arayın.','Etiketlerle kanıtı sınıflandırın.','Kullanım zincirinden hangi Program Review bölümlerinde kullanıldığını görün.','Program Review’dan geldiyseniz kanıtı hedef bölüme bağlayın.'],tip:'Kanıt fiziksel olarak kopyalanmaz; kaynak kayda referans ve SHA-256 zinciri korunur.'},
  evidence:{title:'Kanıt Yönetimi',steps:['Sınavı seçin.','Kanıt türü ve açıklamasını girin.','Dosyayı yükleyin ve SHA-256 bütünlüğünü koruyun.','Akreditasyon paketini indirin.'],tip:'Öğrenci kağıdı, rubrik ve analiz sonuçları doğrudan ölçüm kanıtıdır.'},
  users:{title:'Kullanıcı & Yetki',steps:['Kullanıcıyı oluşturun veya Entra hesabıyla eşleyin.','Yalnız üç akademik hesap tipinden birini atayın.','Öğretim Görevlisine ders, Program Başkanına program kapsamı verin.'],tip:'Kalite Müdürü kurum genelinde kalite/akreditasyon odaklıdır. Teknik admin akademik hesap tipi değildir.'},
  import:{title:'Kurumsal Pilot',steps:['Sistem readiness durumunu kontrol edin.','Akademik dönem/OBS işlemlerini doğrulayın.','UAT ve backup/restore kontrollerini takip edin.'],tip:'Production kurulumundan sonra gerçek Entra, TLS/DNS ve fiziksel ADF kabulü ayrıca yapılır.'},
  security:{title:'Sistem & Güvenlik',steps:['Production güvenlik uyarılarını kontrol edin.','Entra yapılandırmasını doğrulayın.','Güvenlik olay kayıtlarını inceleyin.'],tip:'Bu ekran yalnız teknik sistem yöneticisine açıktır.'},
  feedback:{title:'Geri Bildirim',steps:['Bulunduğunuz ekran için konu seçin.','Sorunu veya öneriyi kısa ve somut yazın.','Çözüm durumunu takip edin.'],tip:'Pilot sırasında gördüğünüz her sürtünmeyi burada kayıt altına alın.'}
};
function guidePersona(){
  if(hasAnyRole('quality')&&!hasAnyRole('admin'))return {name:'Kalite Müdürü',steps:['Kalite','Öğrenim ve Program Çıktıları','Akreditasyon','İyileştirme','Kanıt']};
  if(hasAnyRole('program_head'))return {name:'Program Başkanı',steps:['Program','Öğrenim ve Program Çıktıları','Sınav & Moderasyon','Kalite','Kanıt']};
  if(hasAnyRole('instructor'))return {name:'Öğretim Görevlisi',steps:['Soru Havuzu','Sınav','Optik','Puanlama','Analiz']};
  return {name:'Teknik Yönetici',steps:['Readiness','Kullanıcı','Güvenlik','Yedek','Entegrasyon']};
}
function currentPageName(){return document.querySelector('.page.active')?.id?.replace('page-','')||'dashboard';}
function openGuide(){
  const page=currentPageName(),g=GUIDE_PAGES[page]||GUIDE_PAGES.dashboard,p=guidePersona();
  document.getElementById('guideTitle').textContent=g.title;
  document.getElementById('guideRoleFlow').innerHTML=`<b>${esc(p.name)} · önerilen akış</b><div class="guide-flow-steps">${p.steps.map((x,i)=>`<span>${i+1}. ${esc(x)}</span>`).join('')}</div>`;
  document.getElementById('guideContent').innerHTML=`<h4>Bu ekranda izlenecek yol</h4><ol>${g.steps.map(x=>`<li>${esc(x)}</li>`).join('')}</ol><div class="guide-tip"><b>İpucu</b><br>${esc(g.tip)}</div>`;
  document.getElementById('guideDrawer')?.classList.remove('hidden');document.getElementById('guideBackdrop')?.classList.remove('hidden');
}
function closeGuide(){document.getElementById('guideDrawer')?.classList.add('hidden');document.getElementById('guideBackdrop')?.classList.add('hidden');}
document.getElementById('guideBtn')?.addEventListener('click',openGuide);document.getElementById('guideClose')?.addEventListener('click',closeGuide);document.getElementById('guideBackdrop')?.addEventListener('click',closeGuide);

let excelCatalog=[],excelSelected=null;
const excelPageMap={data:'academic',outcomes:'academic',bank:'question_bank',exams:'exam_students',scan:'exam_students',grade:'classic_grades',quality:'improvements',accreditation:'improvements',users:'users_roles'};
async function openExcelCenter(){
  try{const payload=await api('GET','/api/excel-center');excelCatalog=payload.items||[];document.getElementById('excelCenterKinds').innerHTML=excelCatalog.map(x=>`<button type="button" class="excel-kind-card" data-excel-kind="${esc(x.kind)}"><b>${esc(x.title)}</b><small>${esc(x.description)}</small></button>`).join('');document.getElementById('excelCenterModal')?.classList.remove('hidden');const wanted=excelPageMap[currentPageName()];const item=excelCatalog.find(x=>x.kind===wanted)||excelCatalog[0];if(item)selectExcelKind(item.kind);}catch(e){toast(e.message,'error');}
}
function closeExcelCenter(){document.getElementById('excelCenterModal')?.classList.add('hidden');excelSelected=null;}
function selectExcelKind(kind){excelSelected=excelCatalog.find(x=>x.kind===kind);if(!excelSelected)return;document.querySelectorAll('[data-excel-kind]').forEach(x=>x.classList.toggle('active',x.dataset.excelKind===kind));document.getElementById('excelSelectedInfo').innerHTML=`<div class="excel-selected-title">${esc(excelSelected.title)}</div><div class="excel-selected-sub">${esc(excelSelected.description)}</div>`;document.getElementById('excelCenterWork')?.classList.remove('hidden');document.getElementById('excelCenterResult').textContent='';const f=document.getElementById('excelCenterFile');if(f)f.value='';document.getElementById('excelCenterFileName').textContent='Dosya seçilmedi';}
async function excelSubmit(validateOnly){if(!excelSelected)return;const file=document.getElementById('excelCenterFile')?.files?.[0];if(!file)return toast('Önce Excel dosyasını seçin.','error');const fd=new FormData();fd.append('file',file);const out=document.getElementById('excelCenterResult');out.textContent='İşleniyor...';try{const r=await api('POST',validateOnly?excelSelected.validate_url:excelSelected.import_url,fd);out.textContent=JSON.stringify(r,null,2);toast(validateOnly?'Excel doğrulandı; içe aktarmaya hazır.':'Excel verileri içe aktarıldı.');if(!validateOnly)await refreshCore();}catch(e){out.textContent=e.message;toast(e.message,'error');}}
document.getElementById('excelCenterBtn')?.addEventListener('click',openExcelCenter);document.getElementById('excelCenterClose')?.addEventListener('click',closeExcelCenter);document.getElementById('excelCenterModal')?.addEventListener('click',e=>{if(e.target.id==='excelCenterModal')closeExcelCenter();});document.getElementById('excelCenterKinds')?.addEventListener('click',e=>{const b=e.target.closest('[data-excel-kind]');if(b)selectExcelKind(b.dataset.excelKind);});document.getElementById('excelCenterFile')?.addEventListener('change',e=>{document.getElementById('excelCenterFileName').textContent=e.target.files?.[0]?.name||'Dosya seçilmedi';});document.getElementById('excelTemplateBtn')?.addEventListener('click',async()=>{if(!excelSelected)return;try{await downloadApi(excelSelected.template_url,`DOU-Assess-${excelSelected.kind}-Sablon.xlsx`);}catch(e){toast(e.message,'error');}});document.getElementById('excelValidateBtn')?.addEventListener('click',()=>excelSubmit(true));document.getElementById('excelImportBtn')?.addEventListener('click',()=>excelSubmit(false));


// 6.23 — Belirtke + kurumsal soru yaşam döngüsü
const blueprintState={rows:[],current:null};
function blueprintRowTemplate(r={}){return `<div class="blueprint-row"><label class="wide">Konu<input data-bp="topic" value="${esc(r.topic||'')}" placeholder="Örn. Fonksiyonlar"></label><label>Öğrenim Çıktısı<input data-bp="learning_outcome_code" value="${esc(r.learning_outcome_code||'')}" placeholder="Öğrenim Çıktısı3"></label><label>Bloom<select data-bp="bloom_level"><option value="remember">Hatırlama</option><option value="understand">Anlama</option><option value="apply">Uygulama</option><option value="analyze">Analiz</option><option value="evaluate">Değerlendirme</option><option value="create">Yaratma</option></select></label><label>Zorluk<select data-bp="difficulty"><option value="easy">Kolay</option><option value="medium">Orta</option><option value="hard">Zor</option></select></label><label>Soru<input data-bp="question_count" type="number" min="1" value="${r.question_count||1}"></label><label>Puan<input data-bp="points" type="number" min="1" value="${r.points||5}"></label><button class="ghost small bp-remove" type="button">Sil</button></div>`}
function addBlueprintRow(r={}){const box=document.getElementById('blueprintRows');if(!box)return;box.insertAdjacentHTML('beforeend',blueprintRowTemplate(r));const el=box.lastElementChild;el.querySelector('[data-bp="bloom_level"]').value=r.bloom_level||'understand';el.querySelector('[data-bp="difficulty"]').value=r.difficulty||'medium';el.querySelector('.bp-remove').addEventListener('click',()=>{el.remove();refreshBlueprintSummary()});el.querySelectorAll('input,select').forEach(x=>x.addEventListener('input',refreshBlueprintSummary));refreshBlueprintSummary()}
function collectBlueprintRows(){return [...document.querySelectorAll('#blueprintRows .blueprint-row')].map(el=>({topic:el.querySelector('[data-bp="topic"]').value.trim(),learning_outcome_code:el.querySelector('[data-bp="learning_outcome_code"]').value.trim(),bloom_level:el.querySelector('[data-bp="bloom_level"]').value,difficulty:el.querySelector('[data-bp="difficulty"]').value,question_count:Number(el.querySelector('[data-bp="question_count"]').value||1),points:Number(el.querySelector('[data-bp="points"]').value||5),weight_percent:0}))}
function refreshBlueprintSummary(){const rows=collectBlueprintRows(),q=rows.reduce((a,x)=>a+x.question_count,0),pts=rows.reduce((a,x)=>a+x.question_count*x.points,0),target=Number(document.getElementById('blueprintTotalQuestions')?.value||0);const b=document.getElementById('blueprintSummary');if(b)b.innerHTML=`${rows.length} mikro hedef · <b>${q}/${target}</b> soru · <b>${pts}</b> planlanan puan ${q===target?'· <span class="good">Soru sayısı dengeli</span>':'· <span class="warn">Toplamı tamamlayın</span>'}`;}
document.getElementById('blueprintAddRow')?.addEventListener('click',()=>addBlueprintRow());document.getElementById('blueprintTotalQuestions')?.addEventListener('input',refreshBlueprintSummary);
document.getElementById('blueprintNew')?.addEventListener('click',()=>{document.getElementById('blueprintRows').innerHTML='';addBlueprintRow();document.getElementById('blueprintState').textContent='Yeni plan'});
document.getElementById('blueprintSave')?.addEventListener('click',async()=>{try{const course_id=Number(document.getElementById('blueprintCourse').value||0);if(!course_id)throw new Error('Önce ders seçin');const items=collectBlueprintRows(),total_questions=Number(document.getElementById('blueprintTotalQuestions').value||20);const course=(state.courses||[]).find(x=>x.id===course_id);const exam_type=document.getElementById('blueprintExamType').value;const body={course_id,exam_type,title:`${course?.code||''} ${exam_type} Belirtkesi`,total_questions,total_points:100,items};const r=await api('POST','/api/blueprints',body);blueprintState.current=r;document.getElementById('blueprintState').textContent=r.ready?'Havuz hazır':'Soru açığı var';document.getElementById('blueprintSummary').innerHTML=`Belirtke kaydedildi · ${r.coverage.filter(x=>x.ready).length}/${r.coverage.length} hedefte havuz yeterli. ${r.ready?'<b>Sınav sorusu seçimine hazırsınız.</b>':'Eksik hedefler için soru bankasını geliştirin.'}`;toast('Belirtke kaydedildi.');}catch(e){toast(e.message,'error')}});
async function reviewBankQuestion(id,status){try{await api('POST',`/api/question-bank/${id}/review`,{status,note:'',reviewer:''});toast('Soru durumu güncellendi.');await loadBank();}catch(e){toast(e.message,'error')}}window.reviewBankQuestion=reviewBankQuestion;


document.getElementById('q360VisitModeToggle')?.addEventListener('click',()=>{document.body.classList.toggle('accreditation-visit-mode');const b=document.getElementById('q360VisitModeToggle');if(b)b.textContent=document.body.classList.contains('accreditation-visit-mode')?'Normal görünüme dön':'Ziyaret görünümü';});

let q360InstitutionalReport=null;
function institutionalFaculty(){return document.getElementById('q360InstitutionalFaculty')?.value||'';}
async function loadInstitutionalQualityReport(){
  const year=q360Year(); if(!year)return;
  try{
    const faculty=institutionalFaculty();
    q360InstitutionalReport=await api('GET',`/api/quality360/institutional/self-evaluation?academic_year=${encodeURIComponent(year)}${faculty?`&faculty=${encodeURIComponent(faculty)}`:''}`);
    const r=q360InstitutionalReport,s=r.summary||{};
    const fac=document.getElementById('q360InstitutionalFaculty');
    if(fac&&q360University?.faculties?.length){const cur=fac.value;fac.innerHTML='<option value="">Tüm üniversite</option>'+q360University.faculties.map(x=>`<option value="${esc(x.name)}">${esc(x.name)}</option>`).join('');fac.value=cur;}
    const k=document.getElementById('q360InstitutionalSummary');if(k)k.innerHTML=[[s.visit_readiness_percent||0,'Ortalama hazırlık'],[s.program_count||0,'Program'],[s.evidence_count||0,'Kanıt'],[s.open_cycle_count||0,'Açık PUKÖ'],[s.closed_cycle_count||0,'Kapalı PUKÖ']].map((x,i)=>`<div class="${i===0?'quality-score-kpi':''}"><b>${i===0?'%':''}${esc(x[0])}</b><span>${esc(x[1])}</span></div>`).join('');
    const pri=document.getElementById('q360InstitutionalPriorities');if(pri)pri.innerHTML=(r.priorities||[]).slice(0,6).map(x=>`<article class="executive-insight critical"><i></i><div><b>${esc(x.program_code)} · ${esc(x.code)} · ${esc(x.name)}</b><span>%${esc(x.score)} · ${esc((x.missing_signals||[]).slice(0,2).join(' · ')||'Kanıt/ölçüm derinliği artırılmalı')}</span></div></article>`).join('')||'<div class="empty-state"><b>Öncelikli açık bulunamadı</b><span>Programlar kalite hedeflerini karşılıyor.</span></div>';
    const str=document.getElementById('q360InstitutionalStrengths');if(str)str.innerHTML=(r.strengths||[]).slice(0,6).map(x=>`<article class="executive-insight healthy"><i></i><div><b>${esc(x.program_code)} · ${esc(x.code)} · ${esc(x.name)}</b><span>%${esc(x.score)} hazırlık</span></div></article>`).join('')||'<div class="empty-state"><b>Henüz güçlü alan oluşmadı</b><span>Daha fazla doğrulanmış kalite verisi bekleniyor.</span></div>';
    const tb=document.getElementById('q360InstitutionalPrograms');if(tb)tb.innerHTML=(r.programs||[]).map(x=>`<tr><td><b>${esc(x.code)}</b><br><span class="muted">${esc(x.name)}</span></td><td>${esc(x.faculty||'-')}</td><td>${esc(x.framework?.code||'-')}</td><td>%${esc(x.visit_readiness_percent||0)}</td><td>${esc(x.evidence_count||0)}</td><td>${esc(x.open_cycle_count||0)}</td></tr>`).join('')||'<tr><td colspan="6">Raporlanacak program bulunamadı.</td></tr>';
  }catch(e){toast(e.message,'error')}
}
document.getElementById('q360InstitutionalLoad')?.addEventListener('click',loadInstitutionalQualityReport);
document.getElementById('q360InstitutionalFaculty')?.addEventListener('change',loadInstitutionalQualityReport);
document.getElementById('q360InstitutionalDownload')?.addEventListener('click',()=>{const year=q360Year(),faculty=institutionalFaculty();downloadApi(`/api/quality360/institutional/self-evaluation.docx?academic_year=${encodeURIComponent(year)}${faculty?`&faculty=${encodeURIComponent(faculty)}`:''}`,faculty?`DOU-Assess-Birim-ODR-${year}.docx`:`DOU-Assess-KIDR-${year}.docx`).catch(e=>toast(e.message,'error'));});
document.querySelector('[data-q360-workspace="institutional"]')?.addEventListener('click',loadInstitutionalQualityReport);


let q360StrategyReport=null;
async function loadStrategicQuality(){
  const year=q360Year(); if(!year)return;
  try{
    q360StrategyReport=await api('GET',`/api/quality360/strategy/dashboard?academic_year=${encodeURIComponent(year)}`);
    const r=q360StrategyReport,s=r.summary||{};
    const sum=document.getElementById('q360StrategySummary'); if(sum)sum.innerHTML=[[s.strategy_score_percent||0,'Strateji skoru'],[s.objective_count||0,'Stratejik hedef'],[s.kpi_count||0,'KPI'],[s.risk_kpi_count||0,'Riskli KPI']].map((x,i)=>`<div class="${i===0?'quality-score-kpi':''}"><b>${i===0?'%':''}${esc(x[0])}</b><span>${esc(x[1])}</span></div>`).join('');
    const box=document.getElementById('q360StrategyObjectives'); if(box)box.innerHTML=(r.objectives||[]).map(o=>`<article class="strategy-objective-card"><div class="strategy-objective-head"><div><span class="eyebrow">${esc(o.code)} · ${esc(o.scope_name||'')}</span><h4>${esc(o.title)}</h4><p>${esc(o.owner||'Sorumlu tanımlanmadı')}${o.due_date?` · ${esc(o.due_date)}`:''}</p></div><div class="strategy-score">%${esc(o.score_percent||0)}</div></div><div class="strategy-kpi-list">${(o.kpis||[]).map(k=>`<div class="strategy-kpi ${esc(k.health)}"><div><b>${esc(k.code)} · ${esc(k.name)}</b><span>${esc(k.actual_value)} ${esc(k.unit)} / hedef ${esc(k.target_value)} ${esc(k.unit)}</span></div><div class="strategy-kpi-progress"><span data-style="width:${Math.max(0,Math.min(100,Number(k.progress_percent||0)))}%"></span></div><strong>%${esc(k.progress_percent||0)}</strong></div>`).join('')||'<div class="empty-state compact"><b>Henüz KPI yok</b><span>Bu hedefe ölçülebilir gösterge bağlayın.</span></div>'}</div></article>`).join('')||'<div class="empty-state"><b>Stratejik hedef tanımlanmadı</b><span>Üniversitenin kalite hedeflerini KPI ile bağlamak için ilk hedefi ekleyin.</span></div>';
    const sel=document.getElementById('q360StrategyObjectiveSelect'); if(sel){const cur=sel.value;sel.innerHTML='<option value="">Hedef seçin</option>'+(r.objectives||[]).map(o=>`<option value="${o.id}">${esc(o.code)} · ${esc(o.title)}</option>`).join('');if([...sel.options].some(x=>x.value===cur))sel.value=cur;}
  }catch(e){toast(e.message,'error')}
}
document.getElementById('q360StrategyLoad')?.addEventListener('click',loadStrategicQuality);
document.querySelector('[data-q360-workspace="strategy"]')?.addEventListener('click',loadStrategicQuality);
document.getElementById('q360StrategyObjectiveForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST','/api/quality360/strategy/objectives',{academic_year:q360Year(),scope_type:document.getElementById('q360StrategyScope').value,scope_name:document.getElementById('q360StrategyScopeName').value.trim()||'Doğuş Üniversitesi',program_id:null,code:document.getElementById('q360StrategyCode').value.trim(),title:document.getElementById('q360StrategyTitle').value.trim(),description:'',owner:document.getElementById('q360StrategyOwner').value.trim(),status:'active',start_date:null,due_date:document.getElementById('q360StrategyDue').value||null});e.currentTarget.reset();document.getElementById('q360StrategyScopeName').value='Doğuş Üniversitesi';toast('Stratejik hedef kaydedildi.');await loadStrategicQuality();}catch(err){toast(err.message,'error')}});
document.getElementById('q360StrategyKpiForm')?.addEventListener('submit',async e=>{e.preventDefault();try{const objective_id=Number(document.getElementById('q360StrategyObjectiveSelect').value||0);if(!objective_id)throw new Error('Önce stratejik hedef seçin');await api('POST','/api/quality360/strategy/kpis',{objective_id,code:document.getElementById('q360StrategyKpiCode').value.trim(),name:document.getElementById('q360StrategyKpiName').value.trim(),unit:document.getElementById('q360StrategyUnit').value.trim()||'%',baseline_value:Number(document.getElementById('q360StrategyBaseline').value||0),target_value:Number(document.getElementById('q360StrategyTarget').value||0),actual_value:Number(document.getElementById('q360StrategyActual').value||0),weight:1,direction:document.getElementById('q360StrategyDirection').value,source_type:'manual',source_ref:'',status:'active'});e.currentTarget.reset();document.getElementById('q360StrategyUnit').value='%';document.getElementById('q360StrategyTarget').value='100';toast('KPI stratejik hedefe bağlandı.');await loadStrategicQuality();}catch(err){toast(err.message,'error')}});

// ---------------------------------------------------------------------------
// 6.41 Accreditation Compliance Core
// ---------------------------------------------------------------------------
let q641Cache={templates:[],frameworks:[],pos:[],faculty:[],graduates:[],infra:[],students:[],applications:[]};
function q641Opt(sel,rows,label,value='id'){
  if(!sel)return; sel.innerHTML=(rows||[]).map(x=>`<option value="${esc(x[value])}">${esc(typeof label==='function'?label(x):x[label])}</option>`).join('');
}
function q641Record(title,meta=''){return `<div class="compact-record"><b>${esc(title)}</b><span>${esc(meta)}</span></div>`}
function q644PrimaryFrameworkFamily(){const select=document.getElementById('q360Framework');const fw=q641Cache.frameworks.find(x=>x.id===Number(select?.value||0));return fw?.framework_family||'';}
async function q644RefreshMudekRoute(){
  const box=document.getElementById('q644MudekRoute'),sel=document.getElementById('q641ApplicationFramework'); if(!box||!sel)return;
  const family=q644PrimaryFrameworkFamily();
  if(!['MÜDEK','MEDEK'].includes(family)){box.hidden=true;q641Opt(sel,q641Cache.frameworks.filter(x=>x.status!=='archived'),x=>`${x.framework_family} · ${x.version} · ${x.name}`);return;}
  try{
    const kind=document.getElementById('q641ApplicationType')?.value||'general';
    const routeName=family==='MEDEK'?'medek-route':'mudek-route';
    const routePath=family==='MEDEK'?'/api/quality360/frameworks/medek-route':'/api/quality360/frameworks/mudek-route';
    const route=await api('GET',`${routePath}?academic_year=${encodeURIComponent(q360Year())}&application_type=${encodeURIComponent(kind)}&program_id=${encodeURIComponent(q360ProgramId()||'')}`);
    q641Opt(sel,route.allowed_frameworks||[],x=>`${family} · ${x.version} · ${x.name}`);
    if(route.selected_framework)sel.value=String(route.selected_framework.id);
    box.hidden=false;box.innerHTML=`<b>${esc(family)} sürüm kuralı</b><span>${esc(route.rationale||'')}</span>${route.warning?`<small>⚠ ${esc(route.warning)}</small>`:''}${route.selection_required?'<small>Bu değerlendirme için önceki genel sürümün doğrulanması / resmî sürüm seçimi zorunludur.</small>':''}`;
  }catch(err){box.hidden=false;box.innerHTML=`<b>${esc(family)} sürüm kuralı</b><small>${esc(err.message)}</small>`;}
}

async function q646LoadMedekProgramSpecific(pid,year,fwId){
  const box=document.getElementById('q646MedekProgramSpecific'),badge=document.getElementById('q646MedekProgramSpecificBadge');if(!box)return;
  const fw=q641Cache.frameworks.find(x=>x.id===Number(fwId));
  if(!fw||fw.framework_family!=='MEDEK'){box.innerHTML=q641Record('MEDEK profili seçilmedi','Programa özgü çıktı kataloğu yalnız MEDEK framework ile etkinleşir.');if(badge){badge.textContent='—';badge.className='badge'}return;}
  try{
    const profile=await api('GET',`/api/quality360/programs/${pid}/medek-program-specific?framework_id=${fwId}&academic_year=${encodeURIComponent(year)}`);
    if(profile.match_status!=='exact'){
      box.innerHTML=q641Record('Manuel doğrulama gerekli',profile.warning||'Program için yerleşik MEDEK katalog eşleşmesi yok.');if(badge){badge.textContent='KONTROL';badge.className='badge warning'}return;
    }
    if(badge){badge.textContent=`${profile.mapped_count}/${profile.required_count} EŞLİ`;badge.className=`badge ${profile.ready?'success':'warning'}`;}
    box.innerHTML=`<div class="compact-record"><b>${esc(profile.canonical_name)} · MEDEK ${esc(profile.framework_version)}</b><span>Resmî bölüm ${esc(profile.source_section||'')} · kapsama %${esc(profile.coverage_percent)}</span></div>`+(profile.outputs||[]).map(o=>`<div class="compact-record medek-program-output ${o.mapped?'is-ready':'is-gap'}"><b>${o.mapped?'✓':'○'} ${esc(o.code)} · ${esc(o.title)}</b><span>${o.mapped?`Eşlendi: ${esc((o.mappings||[]).map(m=>m.program_outcome_code).join(', ')||'PÇ')}`:'Mevcut PÇ seçip eşleyin.'}</span>${o.mapped?'':`<div class="compliance-actions"><button class="ghost tiny" type="button" data-q646-map-medek-output="${esc(o.code)}" data-output-title="${esc(o.title)}" data-framework-version="${esc(profile.framework_version)}">Seçili PÇ ile eşle</button></div>`}</div>`).join('');
  }catch(err){box.innerHTML=q641Record('Programa özgü çıktı profili yüklenemedi',err.message);if(badge){badge.textContent='HATA';badge.className='badge danger'}}
}

async function q647LoadMudekReadiness(pid,year,fwId){
  const ek=document.getElementById('q647MudekEk1'),rooms=document.getElementById('q647MudekRooms'),badge=document.getElementById('q647MudekBadge');if(!ek)return;
  const fw=q641Cache.frameworks.find(x=>x.id===Number(fwId));
  if(!fw||fw.framework_family!=='MÜDEK'){ek.innerHTML=q641Record('MÜDEK framework seçilmedi','EK-1 ve belge odası hazırlığı MÜDEK için etkinleşir.');if(rooms)rooms.innerHTML='';if(badge){badge.textContent='—';badge.className='badge'}return;}
  const evidenceButton=code=>`<button class="ghost tiny" type="button" data-q647-evidence-code="${esc(code)}">Kanıt ilişkilendir</button>`;
  try{
    const [profile,bbo,fbo]=await Promise.all([
      api('GET',`/api/quality360/programs/${pid}/mudek-ek1?academic_year=${encodeURIComponent(year)}&framework_id=${fwId}`),
      api('GET',`/api/quality360/programs/${pid}/mudek-evidence-room-readiness?academic_year=${encodeURIComponent(year)}&room_type=BBO&framework_id=${fwId}`),
      api('GET',`/api/quality360/programs/${pid}/mudek-evidence-room-readiness?academic_year=${encodeURIComponent(year)}&room_type=FBO&framework_id=${fwId}`)
    ]);
    if(!profile.matched){ek.innerHTML=q641Record('Manuel EK-1 doğrulaması gerekli',profile.reason||'Program adı yerleşik profile eşleşmedi.');if(badge){badge.textContent='KONTROL';badge.className='badge warning'}}
    else{
      const es=profile.summary||{};if(badge){badge.textContent=`EK-1 ${es.ready||0}/${es.total||0}`;badge.className=`badge ${(es.gap||0)===0&&(es.review||0)===0?'success':'warning'}`;}
      ek.innerHTML=`<div class="compact-record"><b>${esc(profile.profile_title||'MÜDEK EK-1')}</b><span>Ölçüt 5.1 · disipline özgü eğitim planı konuları · program çıktısı değildir</span></div>`+(profile.topics||[]).map(x=>`<div class="compact-record medek-program-output ${x.status==='ready'?'is-ready':x.status==='gap'?'is-gap':''}"><b>${x.status==='ready'?'✓':x.status==='review'?'◐':'○'} ${esc(x.code)} · ${esc(x.title)}</b><span>${x.matched_course_count||0} ders · ${x.evidence_count||0} doğrudan kanıt · ${x.manual_review_completed?'kalite doğrulandı':'kalite doğrulaması bekliyor'}</span>${(x.matched_courses||[]).length?`<small>${(x.matched_courses||[]).slice(0,4).map(c=>`${esc(c.course_code)} · ${esc(c.course_name)}`).join(' · ')}</small>`:''}<div class="compliance-actions">${evidenceButton(x.code)}<select data-q647-ek1-maturity="${esc(x.code)}" aria-label="${esc(x.code)} olgunluk"><option value="1" ${Number(x.manual_maturity||0)===1?'selected':''}>1</option><option value="2" ${Number(x.manual_maturity||0)===2?'selected':''}>2</option><option value="3" ${!x.manual_maturity||Number(x.manual_maturity)===3?'selected':''}>3</option><option value="4" ${Number(x.manual_maturity||0)===4?'selected':''}>4</option><option value="5" ${Number(x.manual_maturity||0)===5?'selected':''}>5</option></select><button class="ghost tiny" type="button" data-q647-ek1-review="${esc(x.code)}">${x.manual_review_completed?'Doğrulamayı güncelle':'Doğrula'}</button></div></div>`).join('');
    }
    if(rooms){
      const br=bbo.summary||{},fr=fbo.summary||{};
      const renderRoom=(label,data)=>`<details class="medek-odr-group" ${(data.summary?.gap||0)?'open':''}><summary><span><b>${label}</b> · %${esc(data.readiness_percent||0)} hazırlık</span><span>${data.summary?.ready||0}/${data.summary?.mandatory_total||0} hazır · ${data.summary?.gap||0} eksik</span></summary><div class="medek-odr-items">${(data.items||[]).map(x=>`<article class="medek-odr-item ${x.status==='gap'?'gap':x.status==='review'?'attention':'ready'}"><div class="medek-odr-item-main"><div><b>${x.status==='ready'?'✓':x.status==='review'?'◐':x.status==='optional'?'—':'○'} ${esc(x.code)} · ${esc(x.title)}</b><small>Sorumlu: ${esc(x.owner||'')} · Kaynak ölçüt: ${esc(x.criterion||'—')}</small></div><span class="badge ${x.status==='ready'?'status-approved':x.status==='review'?'status-ready':x.status==='optional'?'':'danger'}">${x.status==='ready'?'Hazır':x.status==='review'?'Kontrol':x.status==='optional'?'Opsiyonel':'Eksik'}</span></div><div class="medek-odr-item-meta"><span>Doğrudan kanıt <b>${x.exact_evidence_count||0}</b></span><span>Destek kanıtı <b>${x.support_evidence_count||0}</b></span><span>${x.auto_signal?'Sistem sinyali ✓':'Sistem sinyali yok'}</span></div><small>Beklenen: ${(x.required_evidence||[]).map(esc).join(' · ')}</small><div class="medek-odr-item-actions">${evidenceButton(x.code)}</div></article>`).join('')}</div></details>`;
      rooms.innerHTML=`<div class="compact-record"><b>BBO ${br.ready||0}/${br.mandatory_total||0} · FBO ${fr.ready||0}/${fr.mandatory_total||0}</b><span>MÜDEK Sanal Belge Odaları · ${esc(bbo.source?.version||'2.1')} · doğrudan kanıt zorunluluğu</span></div>${renderRoom('Bölüm Belge Odası (BBO)',bbo)}${renderRoom('Fakülte Belge Odası (FBO)',fbo)}`;
    }
    document.querySelectorAll('[data-q647-evidence-code]').forEach(btn=>btn.addEventListener('click',()=>{const code=btn.dataset.q647EvidenceCode,sel=document.getElementById('q360EvidenceCriterion');if(sel)sel.value=code;setQ360Workspace('evidence');document.getElementById('q360EvidenceForm')?.scrollIntoView({behavior:'smooth',block:'center'});}));
    ek.querySelectorAll('[data-q647-ek1-review]').forEach(btn=>btn.addEventListener('click',async()=>{const code=btn.dataset.q647Ek1Review,sel=ek.querySelector(`[data-q647-ek1-maturity="${CSS.escape(code)}"]`),maturity=Number(sel?.value||3);btn.disabled=true;try{await api('PUT','/api/quality360/criterion-assessments',{program_id:pid,framework_profile_id:Number(fwId),academic_year:year,criterion_code:code,maturity_level:maturity,quality_status:maturity>=4?'measured':'implemented',note:'MÜDEK EK-1 disipline özgü konu doğrulaması',evidence_refs:[]});toast(`${code} EK-1 doğrulaması kaydedildi.`);await q647LoadMudekReadiness(pid,year,fwId);}catch(err){toast(err.message,'error');btn.disabled=false;}}));
  }catch(err){ek.innerHTML=q641Record('MÜDEK hazırlık matrisi yüklenemedi',err.message);if(badge){badge.textContent='HATA';badge.className='badge danger'}}
}

async function loadComplianceCenter(){
  const pid=q360ProgramId(),year=q360Year(); if(!pid)return;
  const fwId=Number(document.getElementById('q360Framework')?.value||0);
  try{
    const [matrix,templates,frameworks,pea,pos,docs,budget,apps,faculty,graduates,infra,students,gradDash,maint,research,social,international]=await Promise.all([
      api('GET',`/api/compliance/programs/${pid}/matrix?academic_year=${encodeURIComponent(year)}`),
      api('GET','/api/compliance/templates'),api('GET','/api/quality360/frameworks'),
      api('GET',`/api/compliance/programs/${pid}/pea?academic_year=${encodeURIComponent(year)}`),
      api('GET',`/api/compliance/programs/${pid}/program-outcomes?academic_year=${encodeURIComponent(year)}`),
      api('GET',`/api/compliance/documents?program_id=${pid}`),
      api('GET',`/api/compliance/programs/${pid}/budget?academic_year=${encodeURIComponent(year)}`),
      api('GET',`/api/compliance/programs/${pid}/applications?academic_year=${encodeURIComponent(year)}`),
      api('GET',`/api/quality360/programs/${pid}/faculty`),api('GET',`/api/quality360/programs/${pid}/graduates`),
      api('GET',`/api/quality360/programs/${pid}/infrastructure`),api('GET',`/api/students?program_id=${pid}`),
      api('GET',`/api/compliance/programs/${pid}/graduate-followup-dashboard`),api('GET',`/api/compliance/programs/${pid}/infrastructure-maintenance`),
      api('GET',`/api/compliance/mission/research?academic_year=${encodeURIComponent(year)}&program_id=${pid}`),
      api('GET',`/api/compliance/mission/social_contribution?academic_year=${encodeURIComponent(year)}&program_id=${pid}`),
      api('GET',`/api/compliance/mission/internationalization?academic_year=${encodeURIComponent(year)}&program_id=${pid}`)
    ]);
    q641Cache={templates,frameworks,pos,faculty,graduates,infra,students,applications:apps};
    const sum=matrix.summary||{},badge=document.getElementById('q641ComplianceBadge'); if(badge){badge.textContent=`${sum.green||0}/${sum.total||0} YEŞİL`;badge.className='badge success'}
    const counts=sum.runtime_data_counts||{};
    const kpis=[['Uyum kabiliyeti',`${sum.green||0}/${sum.total||0}`],['PEA',counts.pea||0],['PÇ bileşeni',counts.po_components||0],['Framework snapshot',counts.framework_snapshots||0],['Kontrollü doküman',counts.documents||0],['Başvuru',counts.applications||0]];
    document.getElementById('q641ComplianceKpis').innerHTML=kpis.map(([a,b])=>`<div class="quality-kpi"><span>${esc(a)}</span><strong>${esc(b)}</strong></div>`).join('');
    document.getElementById('q641ComplianceMatrix').innerHTML=(matrix.items||[]).map(x=>`<div class="compliance-matrix-item"><strong><span class="compliance-green">●</span> ${esc(x.requirement)}</strong><small>${esc(x.implementation)}</small></div>`).join('');
    document.getElementById('q641PeaList').innerHTML=(pea||[]).map(x=>q641Record(`${x.code} · ${x.description}`,`${(x.outcome_maps||[]).length} PÇ bağlantısı · ${x.review_cycle_years} yıllık gözden geçirme`)).join('')||q641Record('Henüz PEA yok','İlk program eğitim amacını ekleyin.');
    q641Opt(document.getElementById('q641PoSelect'),pos,x=>`${x.code} · ${x.description}`);
    document.getElementById('q641PoComponentList').innerHTML=(pos||[]).flatMap(x=>(x.components||[]).map(c=>q641Record(`${c.code} · ${c.description}`,`${x.code} · ${c.component_type}`))).join('')||q641Record('Henüz PÇ bileşeni yok','MÜDEK 3.1 bileşenlerini PÇ altında tanımlayın.');
    await q646LoadMedekProgramSpecific(pid,year,fwId);
    await q647LoadMudekReadiness(pid,year,fwId);
    q641Opt(document.getElementById('q641DocumentSelect'),docs,x=>`${x.document_code} · ${x.title}`);
    const canApproveDocs=roleNames().has('admin')||roleNames().has('quality');
    document.getElementById('q641DocumentList').innerHTML=(docs||[]).slice(0,8).map(x=>{const r=x.latest_revision;let action='';if(r?.status==='draft')action=`<button class="ghost tiny" data-q667-doc-action="submit" data-revision-id="${r.id}">İncelemeye gönder</button>`;else if(r?.status==='submitted'&&canApproveDocs)action=`<button class="ghost tiny" data-q667-doc-action="review" data-revision-id="${r.id}">Kontrol et</button>`;else if(r?.status==='reviewed'&&canApproveDocs)action=`<button class="primary tiny" data-q667-doc-action="approve" data-revision-id="${r.id}">Onayla</button>`;return `<div class="compact-record"><b>${esc(x.document_code)} · ${esc(x.title)}</b><span>${r?`R${r.revision_no} · ${esc(r.status)} · ${esc(String(r.sha256||'').slice(0,12))}… · bütünlük ${esc(r.integrity_status||'unchecked')}`:'Revizyon bekliyor'}</span>${action}</div>`}).join('')||q641Record('Doküman kasası boş','Politika/yönerge/prosedür ekleyin.');
    document.querySelectorAll('[data-q667-doc-action]').forEach(btn=>btn.addEventListener('click',async()=>{const action=btn.dataset.q667DocAction,id=Number(btn.dataset.revisionId||0);btn.disabled=true;try{await api('POST',`/api/compliance/document-revisions/${id}/${action}`,{});toast(action==='approve'?'Revizyon onaylandı.':action==='review'?'Revizyon kontrol edildi.':'Revizyon incelemeye gönderildi.');await loadComplianceCenter();}catch(err){toast(err.message,'error');btn.disabled=false;}}));
    document.getElementById('q641BudgetSummary').innerHTML=budget.plan?q641Record(`${Number(budget.plan.allocated_amount||0).toLocaleString('tr-TR')} ${budget.plan.currency}`,`Harcanan ${Number(budget.plan.spent_amount||0).toLocaleString('tr-TR')} · Kalan ${Number(budget.variance||0).toLocaleString('tr-TR')}`):q641Record('Bütçe planı yok','Bu akademik yıl için kaynak planını oluşturun.');
    const domainCards=[['Ar-Ge',research],['Toplumsal katkı',social],['Uluslararasılaşma',international]];
    document.getElementById('q641MissionSummary').innerHTML=domainCards.map(([n,x])=>q641Record(n,`${x.summary?.activity_count||0} faaliyet · hedef gerçekleşme %${x.summary?.target_attainment_percent||0}`)).join('');
    q641Opt(document.getElementById('q641ApplicationFramework'),frameworks.filter(x=>x.status!=='archived'),x=>`${x.framework_family} · ${x.version} · ${x.name}`);
    await q644RefreshMudekRoute();
    const stages=['preparation','submitted','pre_review','correction','visit_ready','site_visit','response_30_day','decision','closed'];
    const medekStages=['preparation','submitted','pre_review','correction','visit_ready','site_visit','response_7_day','decision','closed'];
    document.getElementById('q641ApplicationList').innerHTML=(apps||[]).map(x=>{const fw=q641Cache.frameworks.find(f=>f.id===x.framework_profile_id),family=fw?.framework_family||'',flow=family==='MEDEK'?medekStages:stages,i=flow.indexOf(x.stage),rawNext=i>=0&&i<flow.length-1?flow[i+1]:'',next=(family==='MEDEK'&&x.stage==='site_visit')?'':rawNext;return `<div class="compact-record"><b>${esc(family)} · ${esc(x.academic_year)} · ${esc(x.application_type)} · ${esc(x.stage)}</b><span>${esc(x.owner||'Sorumlu atanmamış')}</span><div class="compliance-actions">${next?`<button class="ghost tiny" data-q641-next-app="${x.id}" data-next-stage="${next}">Sonraki: ${esc(next)}</button>`:''}<button class="ghost tiny" data-q641-evaluator="${x.id}">Değerlendirici alanı</button><button class="ghost tiny" data-q641-docreq="${x.id}">Ek belge talebi</button>${family==='MEDEK'?`<button class="ghost tiny" data-q651-pdr="${x.id}">MEDEK PDR</button>`:`<button class="ghost tiny" data-q648-center="${x.id}">Ziyaret merkezi</button>`}</div></div>`}).join('')||q641Record('Aktif başvuru yok','Framework seçip akreditasyon yaşam döngüsünü başlatın.');
    q641Opt(document.getElementById('q641FacultySelect'),faculty,x=>`${x.title} ${x.full_name}`);q641Opt(document.getElementById('q641GraduateSelect'),graduates,x=>`${x.graduate_key} · ${x.full_name||'Mezun'}`);q641Opt(document.getElementById('q641InfraSelect'),infra,x=>`${x.infrastructure_type} · ${x.name}`);q641Opt(document.getElementById('q641StudentSelect'),students,x=>`${x.student_no} · ${x.full_name}`);
    document.getElementById('q641PeopleSummary').innerHTML=q641Record('Mezun izleme',`1. yıl %${gradDash.coverage?.['1_year']||0} · 3. yıl %${gradDash.coverage?.['3_year']||0} · 5. yıl %${gradDash.coverage?.['5_year']||0}`)+q641Record('Öğretim kadrosu',`${faculty.length} aktif kayıt · CV ve ders yükü sürümlenebilir`);
    document.getElementById('q641MaintenanceSummary').innerHTML=q641Record('Bakım kayıtları',`${(maint||[]).length} kayıt · ${infra.length} altyapı varlığı`);
    q641Opt(document.getElementById('q641TemplateSelect'),templates,x=>`${x.framework_family} · ${x.report_type} · ${x.version}`);
    document.getElementById('q641TemplateList').innerHTML=(templates||[]).map(x=>`<div class="compact-record"><b>${esc(x.framework_family)} · ${esc(x.report_type)} · ${esc(x.version)}</b><span>${x.stored_name?'Fiziksel resmî kaynak kilitli · SHA '+esc(String(x.source_sha256).slice(0,12))+'…':'Registry tanımı hazır · resmî kaynak dosyası yüklenebilir'}</span>${x.report_type==='ODR'||x.report_type==='KIDR'?`<div class="compliance-actions"><button class="ghost tiny" data-q641-render-template="${x.id}">Word üret</button></div>`:''}</div>`).join('');
    if(fwId){
      try{const tree=await api('GET',`/api/compliance/programs/${pid}/criteria-tree?framework_profile_id=${fwId}&academic_year=${encodeURIComponent(year)}`);const evSel=document.getElementById('q360EvidenceCriterion');if(evSel){const opts=['<option value="">Genel program kanıtı</option>'];(tree.criteria||[]).forEach(c=>{opts.push(`<option value="${esc(c.code)}">${esc(c.code)} · ${esc(c.name)}</option>`);(c.subcriteria||[]).forEach(sc=>opts.push(`<option value="${esc(sc.code)}">↳ ${esc(sc.code)} · ${esc(sc.name)}</option>`));});evSel.innerHTML=opts.join('');}}
      catch(_e){}
    }
  }catch(e){toast(`Uyum Merkezi: ${e.message}`,'error')}
}
async function q641Refresh(){await Promise.all([loadComplianceCenter(),loadQuality360()]);}

document.getElementById('q641FreezeFramework')?.addEventListener('click',async()=>{const fid=Number(document.getElementById('q360Framework')?.value||0);if(!fid)return toast('Önce değerlendirme profili seçin.','error');try{await api('POST',`/api/compliance/programs/${q360ProgramId()}/framework-freeze`,{framework_profile_id:fid,academic_year:q360Year()});toast('Resmî framework sürümü SHA-256 ile donduruldu.');await loadComplianceCenter();}catch(e){toast(e.message,'error')}});
document.getElementById('q641MatrixDocx')?.addEventListener('click',()=>downloadApi(`/api/compliance/programs/${q360ProgramId()}/matrix.docx?academic_year=${encodeURIComponent(q360Year())}`,`DOU-Assess-Uyum-Matrisi-${q360Year()}.docx`).catch(e=>toast(e.message,'error')));
document.getElementById('q641BboZip')?.addEventListener('click',()=>downloadApi(`/api/compliance/programs/${q360ProgramId()}/evidence-room.zip?academic_year=${encodeURIComponent(q360Year())}&room_type=BBO&framework_id=${encodeURIComponent(document.getElementById('q360Framework')?.value||'')}`,`DOU-Assess-MUDEK-BBO-${q360Year()}.zip`).catch(e=>toast(e.message,'error')));
document.getElementById('q641FboZip')?.addEventListener('click',()=>downloadApi(`/api/compliance/programs/${q360ProgramId()}/evidence-room.zip?academic_year=${encodeURIComponent(q360Year())}&room_type=FBO&framework_id=${encodeURIComponent(document.getElementById('q360Framework')?.value||'')}`,`DOU-Assess-MUDEK-FBO-${q360Year()}.zip`).catch(e=>toast(e.message,'error')));

document.getElementById('q641PeaForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST','/api/compliance/pea',{program_id:q360ProgramId(),academic_year:q360Year(),code:document.getElementById('q641PeaCode').value.trim(),description:document.getElementById('q641PeaDescription').value.trim(),stakeholder_basis:document.getElementById('q641PeaStakeholder').value.trim(),mission_alignment:document.getElementById('q641PeaMission').value.trim(),review_cycle_years:Number(document.getElementById('q641PeaCycle').value||3),target_indicator:'',quality_status:'implemented',evidence_refs:[]});e.currentTarget.reset();toast('Program Eğitim Amacı kaydedildi.');await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641PoComponentForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST','/api/compliance/program-outcome-components',{program_outcome_id:Number(document.getElementById('q641PoSelect').value),code:document.getElementById('q641PoComponentCode').value.trim(),description:document.getElementById('q641PoComponentDescription').value.trim(),component_type:document.getElementById('q641PoComponentType').value,framework_family:q641Cache.frameworks.find(x=>x.id===Number(document.getElementById('q360Framework')?.value))?.framework_family||'',framework_version:q641Cache.frameworks.find(x=>x.id===Number(document.getElementById('q360Framework')?.value))?.version||'',framework_component_code:'',required:true,evidence_refs:[]});e.currentTarget.reset();toast('PÇ bileşeni kaydedildi.');await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641DocumentForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST','/api/compliance/documents',{program_id:q360ProgramId(),document_code:document.getElementById('q641DocumentCode').value.trim(),document_type:document.getElementById('q641DocumentType').value,title:document.getElementById('q641DocumentTitle').value.trim(),owner:document.getElementById('q641DocumentOwner').value.trim(),status:'active',retention_years:5});e.currentTarget.reset();toast('Kontrollü doküman oluşturuldu.');await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641DocumentRevisionForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST',`/api/compliance/documents/${Number(document.getElementById('q641DocumentSelect').value)}/revisions`,{revision_no:Number(document.getElementById('q641RevisionNo').value||1),status:'draft',change_summary:document.getElementById('q641RevisionSummary').value.trim(),content_text:document.getElementById('q641RevisionContent').value,effective_date:null,review_date:null,original_name:'',mime_type:'text/plain',approved_by:''});toast('Taslak revizyon SHA-256 ile kaydedildi. İncelemeye göndermek için doküman listesindeki aksiyonu kullanın.');await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641BudgetForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST','/api/compliance/budget-plans',{program_id:q360ProgramId(),academic_year:q360Year(),currency:document.getElementById('q641BudgetCurrency').value,allocated_amount:Number(document.getElementById('q641BudgetAllocated').value||0),spent_amount:0,owner:document.getElementById('q641BudgetOwner').value.trim(),quality_status:'implemented',evidence_refs:[]});toast('Bütçe ve kaynak planı oluşturuldu.');await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641MissionForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST','/api/compliance/mission-activities',{program_id:q360ProgramId(),academic_year:q360Year(),domain:document.getElementById('q641MissionDomain').value,scope_type:'program',scope_name:document.getElementById('q360Program')?.selectedOptions?.[0]?.textContent||'',code:document.getElementById('q641MissionCode').value.trim(),title:document.getElementById('q641MissionTitle').value.trim(),activity_type:'activity',owner:'',partner:'',country:'',participants:0,budget_amount:0,target_value:document.getElementById('q641MissionTarget').value===''?null:Number(document.getElementById('q641MissionTarget').value),actual_value:document.getElementById('q641MissionActual').value===''?null:Number(document.getElementById('q641MissionActual').value),unit:'',status:'planned',outcome_text:'',evidence_refs:[]});e.currentTarget.reset();toast('YÖKAK misyon faaliyeti kaydedildi.');await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q646MedekProgramSpecific')?.addEventListener('click',async e=>{const b=e.target.closest('[data-q646-map-medek-output]');if(!b)return;const poId=Number(document.getElementById('q641PoSelect')?.value||0);if(!poId)return toast('Önce eşlenecek program çıktısını seçin.','error');try{await api('POST','/api/compliance/program-outcome-components',{program_outcome_id:poId,code:`MEDEK-${b.dataset.frameworkVersion}-${b.dataset.q646MapMedekOutput}`,description:b.dataset.outputTitle||'',component_type:'competency',framework_family:'MEDEK',framework_version:b.dataset.frameworkVersion||'',framework_component_code:b.dataset.q646MapMedekOutput,required:true,evidence_refs:[]});toast(`${b.dataset.q646MapMedekOutput} seçili PÇ ile eşlendi.`);await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641ApplicationType')?.addEventListener('change',()=>q644RefreshMudekRoute());
document.getElementById('q641ApplicationForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST','/api/compliance/applications',{program_id:q360ProgramId(),framework_profile_id:Number(document.getElementById('q641ApplicationFramework').value),academic_year:q360Year(),application_type:document.getElementById('q641ApplicationType').value,stage:'preparation',status:'active',owner:document.getElementById('q641ApplicationOwner').value.trim(),notes:'',evaluation_mode:document.getElementById('q649EvaluationMode')?.value||'site_visit'});toast('Akreditasyon yaşam döngüsü başlatıldı ve framework snapshot donduruldu.');await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641FacultyWorkloadForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST','/api/compliance/faculty-workload',{faculty_record_id:Number(document.getElementById('q641FacultySelect').value),academic_year:q360Year(),term:document.getElementById('q641WorkloadTerm').value,course_code:document.getElementById('q641WorkloadCourse').value.trim(),workload_type:'course',weekly_hours:Number(document.getElementById('q641WorkloadHours').value||0),source:'ui',notes:''});toast('Öğretim yükü kaydedildi.');await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641FacultyCvForm')?.addEventListener('submit',async e=>{e.preventDefault();const f=q641Cache.faculty.find(x=>x.id===Number(document.getElementById('q641FacultySelect').value));try{await api('POST','/api/compliance/faculty-cv',{faculty_record_id:Number(document.getElementById('q641FacultySelect').value),format_type:document.getElementById('q641CvFormat').value,version_no:Number(document.getElementById('q641CvVersion').value||1),cv_data:{full_name:f?.full_name||'',title:f?.title||'',email:f?.email||'',highest_degree:document.getElementById('q641CvDegree').value.trim(),expertise:document.getElementById('q641CvExpertise').value.trim()},approved:false});toast('YÖKSİS/ÜAK CV snapshot kaydedildi.');await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641GraduateFollowupForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST','/api/compliance/graduate-followups',{graduate_record_id:Number(document.getElementById('q641GraduateSelect').value),followup_year:Number(document.getElementById('q641FollowupYear').value),survey_date:new Date().toISOString().slice(0,10),employment_status:document.getElementById('q641FollowupStatus').value.trim(),employer:'',job_title:'',related_field:null,satisfaction_percent:null,employer_feedback:'',resulting_action:'',evidence_refs:[]});toast('Mezun takip kaydı oluşturuldu.');await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641MaintenanceForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('POST','/api/compliance/infrastructure-maintenance',{infrastructure_id:Number(document.getElementById('q641InfraSelect').value),maintenance_type:document.getElementById('q641MaintenanceType').value,planned_date:document.getElementById('q641MaintenanceDate').value||null,completed_date:null,status:'planned',owner:'',notes:'',evidence_refs:[]});toast('Bakım/İSG/erişilebilirlik kaydı oluşturuldu.');await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641TemplateUploadForm')?.addEventListener('submit',async e=>{e.preventDefault();const f=document.getElementById('q641TemplateFile').files[0];if(!f)return;const fd=new FormData();fd.append('file',f);try{await api('POST',`/api/compliance/templates/${Number(document.getElementById('q641TemplateSelect').value)}/upload`,fd);toast('Resmî şablon fiziksel dosyası SHA-256 ile kilitlendi.');e.currentTarget.reset();await loadComplianceCenter();}catch(err){toast(err.message,'error')}});
document.getElementById('q641StudentCardLoad')?.addEventListener('click',async()=>{const id=Number(document.getElementById('q641StudentSelect').value);if(!id)return;try{const x=await api('GET',`/api/compliance/students/${id}/outcome-card?academic_year=${encodeURIComponent(q360Year())}`);document.getElementById('q641StudentCard').innerHTML=`${q641Record(`${x.student_no} · ${x.full_name}`,`Genel çıktı başarısı %${x.overall_attainment_percent} · ${x.graduate_ready?'Mezuniyet çıktıları sağlandı':'İzleme sürüyor'}`)}${(x.program_outcomes||[]).map(po=>`<div class="student-outcome-po"><b>${esc(po.code)} · %${esc(po.attainment_percent)}</b><span>${esc(po.description)}</span><div class="meter"><i data-style="width:${Math.max(0,Math.min(100,Number(po.attainment_percent||0)))}%"></i></div></div>`).join('')}`;}catch(e){toast(e.message,'error')}});
document.getElementById('q641StudentCardFreeze')?.addEventListener('click',async()=>{const id=Number(document.getElementById('q641StudentSelect').value);if(!id)return;try{const x=await api('POST',`/api/compliance/students/${id}/outcome-snapshots`,{academic_year:q360Year(),snapshot_type:'graduation',freeze:true});toast(`Mezuniyet karnesi donduruldu · v${x.version_no} · ${String(x.content_sha256).slice(0,12)}…`);}catch(e){toast(e.message,'error')}});
async function q648LoadVisitCenter(applicationId){
  const box=document.getElementById('q648VisitCenter'), badge=document.getElementById('q648VisitBadge'), hidden=document.getElementById('q648ApplicationId');
  if(!box||!applicationId)return; hidden.value=String(applicationId);
  const [d,closure,history]=await Promise.all([api('GET',`/api/compliance/applications/${applicationId}/visit-control-center`),api('GET',`/api/compliance/applications/${applicationId}/closure-matrix`),api('GET',`/api/compliance/applications/${applicationId}/decision-history`)]);
  const s=d.summary||{}, scope=d.interim_primary_scope_codes||[], mode=d.application?.evaluation_mode||'site_visit';
  badge.textContent=`${mode==='report_only'?'Raporla':'Ziyaretle'} · ${s.open_findings||0} açık bulgu · ${s.overdue_requests||0} gecikmiş talep`;
  const visitBtn=document.getElementById('q648AddVisitNote'); if(visitBtn) visitBtn.hidden=mode==='report_only';
  const findings=(d.findings||[]).map(x=>`<div class="compact-record"><b>${esc(x.criterion_code||'GENEL')} · ${esc(x.finding_type)} · ${esc(x.title)}</b><span>${esc(x.status)}${x.carried_forward?' · Önceki değerlendirmeden taşındı':''}</span></div>`).join('');
  const req=(d.document_requests||[]).map(x=>`<div class="compact-record"><b>${esc(x.criterion_code||'GENEL')} · ${esc(x.title)}</b><span>${esc(x.status)} · ${x.due_date?`Termin ${esc(x.due_date)}`:'Termin yok'} · SLA ${esc(x.sla_state||'open')}</span></div>`).join('');
  const notes=(d.visit_notes||[]).map(x=>`<div class="compact-record"><b>${esc(x.note_type)} · ${esc(x.title)}</b><span>${esc(x.criterion_code||'GENEL')} · ${esc(x.recorded_by||'')}${x.note?` · ${esc(x.note)}`:''}</span>${x.note_type==='evaluator_comment'?`<button class="ghost small" type="button" data-visit-reply="${x.id}">Yanıtla</button>`:''}</div>`).join('');
  const c=closure.summary||{}; const hist=(history||[]).slice(-5).reverse().map(x=>`<div class="compact-record"><b>${esc(x.action)} · ${esc(x.decision_code||x.to_stage||'')}</b><span>${esc(x.note||x.created_at||'')}</span></div>`).join('');
  box.innerHTML=`${q641Record('Değerlendirme yöntemi',mode==='report_only'?'Raporla Ara Değerlendirme':'Ziyaretle Değerlendirme')}${q641Record('Ara değerlendirme birincil kapsamı',scope.length?scope.join(', '):'Önceki açık zayıflık yok / genel değerlendirme')}${q641Record('Bulgu kapanış matrisi',`${c.closure_ready||0}/${c.total||0} kapanışa hazır · ${c.open||0} açık`)}${findings||q641Record('Bulgu','Henüz bulgu kaydı yok.')}${req||q641Record('Belge talebi','Açık ek belge talebi yok.')}${mode==='site_visit'?(notes||q641Record('Ziyaret notu','Henüz ziyaret notu yok.')):''}${hist||q641Record('Karar geçmişi','Henüz karar kaydı yok.')}`;
}


async function q651LoadPdrCenter(applicationId){
  const box=document.getElementById('q651PdrCenter'),badge=document.getElementById('q651PdrBadge'),hidden=document.getElementById('q651ApplicationId'); if(!box||!applicationId)return; hidden.value=String(applicationId);
  try{const d=await api('GET',`/api/compliance/applications/${applicationId}/medek-pdr-center`),sum=d.summary||{},ph=d.phases||{}; badge.textContent=`${sum.final_confirmed||0} nihai kayıt · ${sum.improvement_areas||0} gelişime açık alan · ${sum.site_questions||0} saha sorusu`;
    const phase=(label,rows)=>`<details class="medek-odr-group" ${(rows||[]).length?'open':''}><summary><span><b>${label}</b></span><span>${(rows||[]).length} kayıt</span></summary><div class="medek-odr-items">${(rows||[]).map(x=>`<div class="compact-record"><b>${esc(x.criterion_code||'GENEL')} · ${esc(x.item_type)} · ${esc(x.assessment_value||'')}</b><span>${esc(x.narrative)}${x.carried_forward?' · Önceki değerlendirmeden taşındı':''}</span></div>`).join('')||q641Record('Kayıt yok','Bu aşamada henüz PDR maddesi yok.')}</div></details>`;
    const scope=(d.interim_scope||[]).map(x=>`${esc(x.criterion_code||'GENEL')} · ${esc(x.narrative)}`).join('<br>');
    box.innerHTML=`${q641Record('MEDEK PDR süreci',d.official_process_note||'')}${d.application?.application_type==='interim'?q641Record('Ara değerlendirme kapsamı',scope||'Önceki iyileştirmeye açık alan kaydı yok.'):''}${phase('Bireysel ön rapor',ph.individual)}${phase('Takım ön uzlaşımı',ph.pre_consensus)}${phase('Saha ziyareti taslağı',ph.site_draft)}${phase('Nihai PDR',ph.final)}`;
  }catch(e){box.innerHTML=q641Record('MEDEK PDR yüklenemedi',e.message); badge.textContent='Hata';}
}

document.getElementById('q651AddPdrItem')?.addEventListener('click',async()=>{const appId=Number(document.getElementById('q651ApplicationId')?.value||0);if(!appId)return toast('Önce MEDEK başvurusu seçin.','error');const d=await workflowForm({eyebrow:'MEDEK PDR',title:'PDR maddesi ekle',description:'Değerlendirici görüşünü ölçüt ve aşama ile kayıt altına alın.',submitLabel:'PDR maddesini kaydet',fields:[{name:'phase',label:'Aşama',type:'select',value:'individual',options:[{value:'individual',label:'Bireysel değerlendirme'},{value:'pre_consensus',label:'Ön uzlaşı'},{value:'site_draft',label:'Ziyaret taslağı'},{value:'final',label:'Final'}]},{name:'type',label:'Madde türü',type:'select',value:'improvement_area',options:[{value:'strength',label:'Güçlü yön'},{value:'improvement_area',label:'İyileştirme alanı'},{value:'site_question',label:'Ziyaret sorusu'},{value:'assessment',label:'Değerlendirme'}]},{name:'criterion',label:'Ölçüt / alt ölçüt kodu',placeholder:'Örn. 3.1'},{name:'narrative',label:'PDR açıklaması',type:'textarea',rows:5,required:true}]});if(!d)return;try{await api('POST','/api/compliance/medek-pdr-items',{application_id:appId,workspace_id:null,report_phase:d.phase,criterion_code:d.criterion||'',evaluator_name:'Değerlendirme Takımı',item_type:d.type,narrative:d.narrative,assessment_value:'',evidence_refs:[],status:'confirmed'});toast('MEDEK PDR maddesi kaydedildi.');await q651LoadPdrCenter(appId);}catch(e){toast(e.message,'error')}});
document.getElementById('q651Open7Day')?.addEventListener('click',async()=>{const appId=Number(document.getElementById('q651ApplicationId')?.value||0);if(!appId)return toast('Önce MEDEK başvurusu seçin.','error');try{const x=await api('POST',`/api/compliance/applications/${appId}/open-medek-7-day-response`,{});toast(`MEDEK +7 gün yanıt penceresi açıldı · Son tarih ${x.correction_due}`);await q651LoadPdrCenter(appId);await loadComplianceCenter();}catch(e){toast(e.message,'error')}});
async function q652LoadForms(){const appId=Number(document.getElementById('q651ApplicationId')?.value||0),box=document.getElementById('q652FormCenter');if(!box||!appId)return;try{const [forms,report]=await Promise.all([api('GET',`/api/compliance/applications/${appId}/medek-pdr-forms`),api('GET',`/api/compliance/applications/${appId}/medek-institution-report`)]);const rows=['FORM1','FORM2','FORM3'].map(code=>{const a=forms.forms?.[code]||[],ok=a.some(x=>x.status==='confirmed');return `<div class="compact-record"><b>${ok?'✓':'○'} ${code}</b><span>${a.length} kayıt · ${ok?'onaylı':'eksik/taslak'}</span></div>`}).join('');box.innerHTML=rows+`<div class="compact-record"><b>Kurum raporu</b><span>${report.team_consolidation_ready?'Konsolidasyona hazır':'Eksik: '+(report.missing_required_forms||[]).join(', ')}</span></div>`;}catch(e){box.innerHTML=`<div class="compact-record"><b>FORM yüklenemedi</b><span>${esc(e.message)}</span></div>`;}}
document.getElementById('q652LoadForms')?.addEventListener('click',q652LoadForms);


document.getElementById('q648AddFinding')?.addEventListener('click',async()=>{const appId=Number(document.getElementById('q648ApplicationId')?.value||0);if(!appId)return toast('Önce başvuru seçin.','error');const d=await workflowForm({eyebrow:'ZİYARET BULGUSU',title:'Akreditasyon bulgusu ekle',description:'Bulgunun türünü, ölçütünü ve başlığını yapılandırılmış biçimde kaydedin.',submitLabel:'Bulguyu kaydet',fields:[{name:'criterion',label:'Ölçüt / alt ölçüt kodu',placeholder:'Örn. 3.1'},{name:'type',label:'Bulgu türü',type:'select',value:'weakness',options:[{value:'deficiency',label:'Eksiklik'},{value:'weakness',label:'Zayıflık'},{value:'concern',label:'Kaygı'},{value:'observation',label:'Gözlem'},{value:'strength',label:'Güçlü yön'}]},{name:'title',label:'Bulgu başlığı',required:true},{name:'description',label:'Açıklama',type:'textarea',rows:4}]});if(!d)return;try{await api('POST','/api/compliance/findings',{application_id:appId,criterion_code:d.criterion||'',finding_type:d.type,title:d.title,description:d.description||'',status:'open',owner:'Program Başkanı',due_date:null,evidence_refs:[],response_note:''});toast('Akreditasyon bulgusu kaydedildi.');await q648LoadVisitCenter(appId);}catch(e){toast(e.message,'error')}});
document.getElementById('q648VisitCenter')?.addEventListener('click',async e=>{const b=e.target.closest('[data-visit-reply]');if(!b)return;try{const d=await workflowForm({eyebrow:'DEĞERLENDİRİCİ YORUMU',title:'Kurum yanıtı',description:'Yanıt değerlendiricinin Kanıt Odası > Yorumlarım ekranında görünür.',submitLabel:'Yanıtı gönder',fields:[{name:'note',label:'Yanıt',type:'textarea',required:true,rows:4}]});if(!d)return;await api('POST',`/api/compliance/visit-notes/${b.dataset.visitReply}/reply`,{note:d.note});toast('Yanıt değerlendiriciye iletildi.');await q648LoadVisitCenter(Number(document.getElementById('q648ApplicationId').value))}catch(err){toast(err.message,'error')}});
document.getElementById('q648AddVisitNote')?.addEventListener('click',async()=>{const appId=Number(document.getElementById('q648ApplicationId')?.value||0);if(!appId)return toast('Önce başvuru seçin.','error');const d=await workflowForm({eyebrow:'SAHA ZİYARETİ',title:'Ziyaret notu ekle',description:'Notu ilgili ölçüt ve açıklamasıyla kaydedin.',submitLabel:'Notu kaydet',fields:[{name:'title',label:'Not başlığı',required:true},{name:'criterion',label:'İlgili ölçüt kodu',placeholder:'Örn. 4.2'},{name:'note',label:'Ziyaret notu',type:'textarea',rows:5}]});if(!d)return;try{await api('POST','/api/compliance/visit-notes',{application_id:appId,criterion_code:d.criterion||'',note_type:'observation',title:d.title,note:d.note||'',recorded_by:'Kalite Koordinatörlüğü',visibility:'internal',evidence_refs:[],occurred_at:null});toast('Ziyaret notu kaydedildi.');await q648LoadVisitCenter(appId);}catch(e){toast(e.message,'error')}});
document.getElementById('q648Open30Day')?.addEventListener('click',async()=>{const appId=Number(document.getElementById('q648ApplicationId')?.value||0);if(!appId)return toast('Önce başvuru seçin.','error');try{const x=await api('POST',`/api/compliance/applications/${appId}/open-30-day-response`,{});toast(`30-gün yanıt penceresi açıldı · Son tarih ${x.correction_due}`);await q648LoadVisitCenter(appId);await loadComplianceCenter();}catch(e){toast(e.message,'error')}});

document.getElementById('q641ApplicationList')?.addEventListener('click',async e=>{const next=e.target.closest('[data-q641-next-app]'),ev=e.target.closest('[data-q641-evaluator]'),dr=e.target.closest('[data-q641-docreq]'),center=e.target.closest('[data-q648-center]'),pdr=e.target.closest('[data-q651-pdr]');try{if(pdr){await q651LoadPdrCenter(Number(pdr.dataset.q651Pdr));}else if(center){await q648LoadVisitCenter(Number(center.dataset.q648Center));}else if(next){await api('PATCH',`/api/compliance/applications/${next.dataset.q641NextApp}`,{stage:next.dataset.nextStage});toast('Akreditasyon süreci bir sonraki aşamaya ilerletildi.');await loadComplianceCenter();}else if(ev){const data=await workflowForm({eyebrow:'DIŞ DEĞERLENDİRİCİ',title:'Salt-okuma çalışma alanı oluştur',description:'Davet bağlantısı tek sefer gösterilir ve süreli erişim sağlar.',submitLabel:'Davet oluştur',fields:[{name:'email',label:'Değerlendirici e-posta adresi',type:'email',required:true},{name:'name',label:'Ad Soyad',value:'Dış Değerlendirici'}]});if(!data)return;const created=await api('POST','/api/compliance/evaluator-workspaces',{application_id:Number(ev.dataset.q641Evaluator),evaluator_email:data.email,evaluator_name:data.name||'Dış Değerlendirici',access_mode:'read_only',expires_at:null});const invite=created.invitation_path?`${location.origin}${created.invitation_path}`:'';if(invite)await workflowForm({eyebrow:'DAVET HAZIR',title:'Değerlendirici davet bağlantısı',description:'Bu bağlantıyı güvenli bir kanaldan paylaşın. Token daha sonra tekrar gösterilmez. Değerlendirici; programın dersleri, öğrenme/program çıktıları, onaylı sınavları, sınav kâğıtları ve öğrenci cevaplarını (öğrenci adları maskeli) salt-okunur görür; tüm erişimler denetim kaydına yazılır.',submitLabel:'Tamam',fields:[{name:'invite',label:'Tek kullanımlık davet bağlantısı',value:invite,readonly:true}]});toast('Salt-okuma değerlendirici workspace ve süreli davet bağlantısı oluşturuldu.');}else if(dr){const data=await workflowForm({eyebrow:'BELGE TALEBİ',title:'Ek bilgi / belge iste',description:'Değerlendirici talebini başlık, ölçüt ve termin ile kayıt altına alın.',submitLabel:'Talebi oluştur',fields:[{name:'title',label:'Talep başlığı',required:true},{name:'criterion',label:'İlgili ölçüt',placeholder:'Örn. 3.2'},{name:'description',label:'Açıklama',type:'textarea',rows:4},{name:'due_date',label:'Son tarih',type:'date'}]});if(!data)return;await api('POST','/api/compliance/document-requests',{application_id:Number(dr.dataset.q641Docreq),criterion_code:data.criterion||'',title:data.title,description:data.description||'',requested_by:'Evaluator',due_date:data.due_date||null,evidence_refs:[]});toast('Ek belge talebi kaydedildi.');}}catch(err){toast(err.message,'error')}});
document.getElementById('q641TemplateList')?.addEventListener('click',e=>{const b=e.target.closest('[data-q641-render-template]');if(!b)return;downloadApi(`/api/compliance/templates/${b.dataset.q641RenderTemplate}/render.docx?program_id=${q360ProgramId()}&academic_year=${encodeURIComponent(q360Year())}`,`DOU-Assess-Resmi-Rapor-${q360Year()}.docx`).catch(err=>toast(err.message,'error'));});

document.getElementById('q653DecisionReadiness')?.addEventListener('click',async()=>{const appId=Number(document.getElementById('q651ApplicationId')?.value||0);if(!appId)return toast('Önce MEDEK başvurusu seçin.','error');try{const d=await api('GET',`/api/compliance/applications/${appId}/medek-final-readiness`),box=document.getElementById('q652FormCenter');box.innerHTML=(box.innerHTML||'')+`<div class="compact-record"><b>${d.ready?'✓ Karara hazır':'○ Karar hazırlığı eksik'}</b><span>${d.ready?'Uygun seçenekler: '+(d.eligible_decision_options||[]).join(', '):(d.gaps||[]).join(' · ')}</span></div>`;}catch(e){toast(e.message,'error')}});
document.getElementById('q653RecordDecision')?.addEventListener('click',async()=>{const appId=Number(document.getElementById('q651ApplicationId')?.value||0);if(!appId)return toast('Önce MEDEK başvurusu seçin.','error');const data=await workflowForm({eyebrow:'MEDEK KARARI',title:'Final akreditasyon kararını kaydet',description:'Karar türünü, başlangıç tarihini ve takım görüşünü yapılandırılmış biçimde kaydedin.',submitLabel:'Kararı kaydet',fields:[{name:'code',label:'Karar',type:'select',value:'full',options:[{value:'full',label:'Tam akreditasyon'},{value:'conditional',label:'Koşullu akreditasyon'},{value:'short_term',label:'Kısa dönem'},{value:'reapply',label:'Yeniden başvuru'}]},{name:'start',label:'Akreditasyon başlangıcı',type:'date'},{name:'opinion',label:'Takım görüşü',type:'textarea',rows:5}]});if(!data)return;try{const qs=new URLSearchParams({decision_code:data.code,team_opinion:data.opinion||''});if(data.start)qs.set('accreditation_start',data.start);const d=await api('POST',`/api/compliance/applications/${appId}/medek-final-decision?${qs.toString()}`,{});toast(`MEDEK kararı kaydedildi · ${d.decision_profile?.label||data.code}`);await q652LoadForms();}catch(e){toast(e.message,'error')}});
function q653Download(appId,kind){window.open(`/api/compliance/applications/${appId}/medek-institution-report.${kind}`,'_blank','noopener');}
document.getElementById('q653Docx')?.addEventListener('click',()=>{const id=Number(document.getElementById('q651ApplicationId')?.value||0);if(id)q653Download(id,'docx')});
document.getElementById('q653Pdf')?.addEventListener('click',()=>{const id=Number(document.getElementById('q651ApplicationId')?.value||0);if(id)q653Download(id,'pdf')});
document.getElementById('q653Freeze')?.addEventListener('click',async()=>{const appId=Number(document.getElementById('q651ApplicationId')?.value||0);if(!appId)return toast('Önce MEDEK başvurusu seçin.','error');if(!confirm('MEDEK karar dönemi değişmez snapshot ile dondurulsun mu?'))return;try{const d=await api('POST',`/api/compliance/applications/${appId}/medek-finalize`,{});toast(`MEDEK dönemi donduruldu · ${d.report?.snapshot_sha256?.slice(0,12)||''}`);await loadComplianceCenter();}catch(e){toast(e.message,'error')}});


const surveyTypeLabels={student:'Öğrenci',graduate:'Mezun',employer:'İşveren',external_stakeholder:'Dış paydaş',faculty:'Öğretim elemanı',course_evaluation:'Ders değerlendirme',program_evaluation:'Program değerlendirme'};
function surveyQuestionLines(raw=''){return String(raw||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map((line,i)=>{const p=line.split('|').map(x=>x.trim());if(p.length<2)throw new Error(`${i+1}. satır için KOD | Soru biçimi gerekir.`);return {code:p[0],prompt:p[1],po_code:p[2]||'',question_type:'likert',required:true,order_no:i+1,scale_min:1,scale_max:5,options:[],weight_percent:100};});}
async function prepareSurveys(){
  if(!state.programs.length)await refreshCore();const sel=document.getElementById('surveyProgram');if(!sel)return;const keep=Number(sel.value||0);sel.innerHTML=(state.programs||[]).map(p=>`<option value="${p.id}">${esc(p.code)} · ${esc(p.name)}</option>`).join('');if(keep&&state.programs.some(p=>Number(p.id)===keep))sel.value=String(keep);if(!sel.value){document.getElementById('surveyList').innerHTML='<p class="muted">Yetkili program bulunamadı.</p>';return;}const programId=Number(sel.value);const course=(state.courses||[]).find(c=>Number(c.program_id)===programId);if(course?.academic_year&&!document.getElementById('surveyYear').dataset.touched)document.getElementById('surveyYear').value=course.academic_year;await loadSurveys();
}
async function loadSurveys(){
  const programId=Number(document.getElementById('surveyProgram')?.value||0),year=document.getElementById('surveyYear')?.value.trim();if(!programId)return;const status=document.getElementById('surveyStatus');if(status)status.textContent='Yükleniyor';try{const [surveys,ctx,mix]=await Promise.all([api('GET',`/api/programs/${programId}/surveys`),api('GET',`/api/programs/${programId}/survey-context?academic_year=${encodeURIComponent(year)}`),api('GET',`/api/programs/${programId}/outcome-evidence-mix?academic_year=${encodeURIComponent(year)}&direct_weight=70&indirect_weight=30`)]);window.__surveyContext=ctx;const campaigns=surveys.reduce((a,x)=>a+Number(x.campaign_count||0),0),mapped=surveys.reduce((a,x)=>a+(x.questions||[]).filter(q=>(q.targets||[]).length).length,0),questions=surveys.reduce((a,x)=>a+(x.questions||[]).length,0);document.getElementById('surveySummary').innerHTML=[['Anket şablonu',String(surveys.length),'Program düzeyi dolaylı ölçmeler','primary'],['Soru',String(questions),`${mapped} soru kanıta bağlı`,''],['Kampanya',String(campaigns),'Dönemsel uygulama',''],['Tam PÇ kanıtı',String((mix.program_outcomes||[]).filter(x=>x.evidence_status==='complete').length),`${(mix.program_outcomes||[]).length} Program Çıktısı içinde`,'']].map(x=>`<article class="${x[3]?'primary':''}"><span>${esc(x[0])}</span><b>${esc(x[1])}</b><small>${esc(x[2])}</small></article>`).join('');document.getElementById('surveyList').innerHTML=surveys.length?`<div class="survey-card-list">${surveys.map(s=>`<article class="survey-card"><div class="survey-card-main"><div><span class="badge">${esc(surveyTypeLabels[s.survey_type]||s.survey_type)}</span><b>${esc(s.code)} · ${esc(s.title)}</b><small>v${s.version_no} · ${(s.questions||[]).length} soru · ${s.anonymous?'Anonim':'Kimlik doğrulamalı'} · ${s.campaign_count} kampanya</small></div><button class="ghost small" type="button" data-survey-campaign="${s.id}" ${s.status!=='active'?'disabled':''}>Kampanya aç</button></div><div class="survey-question-mini">${(s.questions||[]).map(q=>`<span><b>${esc(q.code)}</b>${esc(q.prompt)} <em>${(q.targets||[]).map(t=>esc(t.program_outcome_code||t.objective_code||`${t.framework_family} ${t.criterion_code}`)).join(', ')||'eşleşmemiş'}</em></span>`).join('')}</div></article>`).join('')}</div>`:'<div class="empty-state"><b>Henüz dolaylı ölçüm yok</b><span>İlk öğrenci, mezun veya işveren anketinizi oluşturun.</span></div>';document.getElementById('surveyEvidenceMix').innerHTML=(mix.program_outcomes||[]).length?`<div class="evidence-mix-list">${mix.program_outcomes.map(x=>`<article class="evidence-mix-row"><div><b>${esc(x.code)}</b><small>${esc(x.description||'')}</small></div><div class="evidence-mix-values"><span>Direct <b>${x.direct_percent==null?'—':`%${Number(x.direct_percent).toFixed(1)}`}</b></span><span>Indirect <b>${x.indirect_percent==null?'—':`%${Number(x.indirect_percent).toFixed(1)}`}</b></span><span class="${x.evidence_status==='complete'?'good':'muted'}">Birleşik <b>${x.combined_percent==null?'—':`%${Number(x.combined_percent).toFixed(1)}`}</b></span></div></article>`).join('')}</div>`:'<p class="muted">Bu akademik yıl için Program Çıktısı bulunamadı.</p>';if(status){status.textContent='Güncel';status.className='badge status-approved';}}catch(e){if(status){status.textContent='Hata';status.className='badge status-risk';}toast(e.message,'error');}
}
document.getElementById('surveyProgram')?.addEventListener('change',loadSurveys);document.getElementById('surveyYear')?.addEventListener('change',e=>{e.target.dataset.touched='1';loadSurveys();});
document.getElementById('surveyCreateForm')?.addEventListener('submit',async e=>{e.preventDefault();const programId=Number(document.getElementById('surveyProgram').value),year=document.getElementById('surveyYear').value.trim();try{const parsed=surveyQuestionLines(document.getElementById('surveyQuestions').value),questions=parsed.map(({po_code,...q})=>q);const created=await api('POST',`/api/programs/${programId}/surveys`,{code:document.getElementById('surveyCode').value.trim(),title:document.getElementById('surveyTitle').value.trim(),description:'',survey_type:document.getElementById('surveyType').value,version_no:1,target_percent:Number(document.getElementById('surveyTarget').value||60),anonymous:document.getElementById('surveyAnonymous').checked,questions});const poByCode=new Map((window.__surveyContext?.program_outcomes||[]).map(x=>[String(x.code).toLocaleUpperCase('tr-TR'),x]));for(let i=0;i<parsed.length;i++){const poCode=String(parsed[i].po_code||'').toLocaleUpperCase('tr-TR');if(!poCode)continue;const po=poByCode.get(poCode);if(!po)throw new Error(`${parsed[i].po_code} bu akademik yılda bulunamadı.`);await api('PUT',`/api/survey-questions/${created.questions[i].id}/targets`,{items:[{target_type:'program_outcome',program_outcome_id:po.id,objective_id:null,framework_family:'',criterion_code:'',weight_percent:100}]});}await api('POST',`/api/surveys/${created.id}/activate`,{});e.target.reset();document.getElementById('surveyTarget').value='60';document.getElementById('surveyAnonymous').checked=true;toast('Anket şablonu oluşturuldu ve aktifleştirildi.');await loadSurveys();}catch(err){toast(err.message,'error');}});
document.getElementById('surveyList')?.addEventListener('click',async e=>{const b=e.target.closest('[data-survey-campaign]');if(!b)return;const surveyId=Number(b.dataset.surveyCampaign),year=document.getElementById('surveyYear').value.trim();try{const code=`CMP-${year.replace(/\D/g,'')}-${Date.now().toString().slice(-6)}`;const c=await api('POST',`/api/surveys/${surveyId}/campaigns`,{code,academic_year:year,term:'',audience_type:'',start_date:null,end_date:null});const opened=await api('POST',`/api/survey-campaigns/${c.id}/open`,{});toast(`Kampanya açıldı: ${opened.public_path}`);await loadSurveys();}catch(err){toast(err.message,'error');}});


const assessmentAssuranceStatusLabels={not_planned:'Planlanmamış',plan_gap:'Plan açığı',awaiting_evidence:'Kanıt bekliyor',achieved:'Hedefe ulaştı',below_target:'Hedef altı'};
async function prepareAssessmentAssurance(){
  if(!state.programs.length)await refreshCore();
  const sel=document.getElementById('assessmentAssuranceProgram');if(!sel)return;
  const keep=Number(sel.value||0);sel.innerHTML=(state.programs||[]).map(p=>`<option value="${p.id}">${esc(p.code)} · ${esc(p.name)}</option>`).join('');
  if(keep&&state.programs.some(p=>Number(p.id)===keep))sel.value=String(keep);
  if(!sel.value){document.getElementById('assessmentAssuranceMatrix').innerHTML='<p class="muted">Yetkili program bulunamadı.</p>';return;}
  const programId=Number(sel.value),course=(state.courses||[]).find(c=>Number(c.program_id)===programId),year=document.getElementById('assessmentAssuranceYear');
  if(course?.academic_year&&!year.dataset.touched)year.value=course.academic_year;
  await loadAssessmentAssurance();
}
async function loadAssessmentAssurance(){
  const programId=Number(document.getElementById('assessmentAssuranceProgram')?.value||0),year=document.getElementById('assessmentAssuranceYear')?.value.trim(),status=document.getElementById('assessmentAssuranceStatus');if(!programId||!year)return;
  status.textContent='Yükleniyor';status.className='badge';
  try{
    const plans=await api('GET',`/api/programs/${programId}/assessment-plans?academic_year=${encodeURIComponent(year)}`),plan=plans[0]||null;
    window.__assessmentAssurancePlan=plan;
    const reviewBtn=document.getElementById('assessmentAssuranceReview');reviewBtn.disabled=!plan;
    document.getElementById('assessmentAssurancePlanTitle').textContent=plan?`${plan.title} · v${plan.version_no}`:'Aktif plan yok';
    document.getElementById('assessmentAssurancePlanMeta').textContent=plan?`${plan.status} · Direct %${Number(plan.direct_weight).toFixed(0)} / Indirect %${Number(plan.indirect_weight).toFixed(0)} · ${plan.items?.length||0} plan kalemi`:'Mevcut sınav, proje/rubrik ve anket eşleşmelerinden planı otomatik oluşturabilirsiniz.';
    if(!plan){
      document.getElementById('assessmentAssuranceSummary').innerHTML=[['Plan','—','Henüz oluşturulmadı','primary'],['Plan kapsamı','%0','Direct + indirect',''],['Kanıt tamlığı','%0','İki kanal birlikte',''],['Hedef altı','—','Review sonrası','']].map(x=>`<article class="${x[3]?'primary':''}"><span>${x[0]}</span><b>${x[1]}</b><small>${x[2]}</small></article>`).join('');
      document.getElementById('assessmentAssuranceMatrix').innerHTML='<div class="empty-state"><b>Yıllık ölçme güvence planı yok</b><span>Mevcut sınav, ölçme aracı ve anket PÇ eşleşmelerini kullanarak otomatik taslak oluşturun.</span></div>';
      document.getElementById('assessmentAssuranceReviews').innerHTML='<p class="muted">Henüz review snapshot yok.</p>';status.textContent='Plan gerekli';status.className='badge status-risk';return;
    }
    const [dash,reviews]=await Promise.all([api('GET',`/api/assessment-plans/${plan.id}/dashboard`),api('GET',`/api/assessment-plans/${plan.id}/reviews`)]),sum=dash.summary||{};
    document.getElementById('assessmentAssuranceSummary').innerHTML=[['Plan kapsamı',`%${Number(sum.plan_coverage_percent||0).toFixed(1)}`,'Her PÇ direct + indirect','primary'],['Kanıt tamlığı',`%${Number(sum.evidence_completeness_percent||0).toFixed(1)}`,'Gerçek ölçüm oluşan PÇ',''],['Hedef başarısı',`%${Number(sum.target_attainment_percent||0).toFixed(1)}`,'Ölçülen PÇ içinde',''],['Hedef altı',String(sum.below_target_count||0),`${sum.plan_gap_count||0} plan açığı`,'']].map(x=>`<article class="${x[3]?'primary':''}"><span>${esc(x[0])}</span><b>${esc(x[1])}</b><small>${esc(x[2])}</small></article>`).join('');
    const rows=dash.program_outcomes||[];
    document.getElementById('assessmentAssuranceMatrix').innerHTML=rows.length?`<div class="assessment-assurance-table">${rows.map(r=>`<article class="assessment-assurance-row ${r.status}"><div class="assessment-assurance-outcome"><span class="badge">${esc(r.code)}</span><div><b>${esc(r.description||'')}</b><small>Hedef %${Number(r.target_percent||0).toFixed(1)} · ${esc(assessmentAssuranceStatusLabels[r.status]||r.status)}</small></div></div><div class="assessment-assurance-channel"><span>Doğrudan <b>${r.direct_percent==null?'—':`%${Number(r.direct_percent).toFixed(1)}`}</b><small>${r.planned_direct_count} yöntem</small></span><span>Dolaylı <b>${r.indirect_percent==null?'—':`%${Number(r.indirect_percent).toFixed(1)}`}</b><small>${r.planned_indirect_count} yöntem</small></span><span>Birleşik <b>${r.combined_percent==null?'—':`%${Number(r.combined_percent).toFixed(1)}`}</b><small>${r.needs_pdca?'PUKÖ adayı':'—'}</small></span></div><details><summary>Yöntemleri göster</summary><div class="assessment-method-list">${(r.methods||[]).map(m=>`<span><b>${esc(m.channel==='direct'?'Direct':'Indirect')} · ${esc(m.method_label)}</b><small>${esc(m.owner||'Sorumlu tanımsız')} · hedef %${Number(m.target_percent||0).toFixed(0)}</small></span>`).join('')||'<span class="muted">Plan kalemi yok.</span>'}</div></details></article>`).join('')}</div>`:'<p class="muted">Bu akademik yıl için Program Çıktısı bulunamadı.</p>';
    document.getElementById('assessmentAssuranceReviews').innerHTML=reviews.length?reviews.map(r=>`<div class="compact-record"><b>Review #${r.review_no} · ${esc(r.status)}</b><span>${new Date(r.reviewed_at).toLocaleString('tr-TR')} · ${esc(r.reviewed_by||'system')}<br>${esc(r.decision||'Karar notu yok')}</span></div>`).join(''):'<p class="muted">Henüz review snapshot yok.</p>';
    status.textContent='Güncel';status.className='badge status-approved';
  }catch(e){status.textContent='Hata';status.className='badge status-risk';toast(e.message,'error');}
}
document.getElementById('assessmentAssuranceProgram')?.addEventListener('change',loadAssessmentAssurance);
document.getElementById('assessmentAssuranceYear')?.addEventListener('change',e=>{e.target.dataset.touched='1';loadAssessmentAssurance();});
document.getElementById('assessmentAssuranceAutoBuild')?.addEventListener('click',async()=>{const programId=Number(document.getElementById('assessmentAssuranceProgram')?.value||0),year=document.getElementById('assessmentAssuranceYear')?.value.trim();if(!programId||!year)return;try{const p=await api('POST',`/api/programs/${programId}/assessment-plans/autobuild`,{academic_year:year,title:`${year} Program Ölçme Güvence Planı`,version_no:1,direct_weight:70,indirect_weight:30,owner:'Program Başkanı / Kalite',review_date:null,notes:'Direct + indirect PÇ güvence planı'});toast(`Ölçme güvence planı hazır · ${p.autobuilt_item_count||0} yöntem eklendi.`);await loadAssessmentAssurance();}catch(e){toast(e.message,'error')}});
document.getElementById('assessmentAssuranceReview')?.addEventListener('click',async()=>{const plan=window.__assessmentAssurancePlan;if(!plan)return;const d=await workflowForm({eyebrow:'YIL SONU REVIEW',title:'Ölçme güvence planını dondur',description:'Kurul değerlendirmesini kalıcı review snapshot ile mühürleyin.',submitLabel:'Review snapshot oluştur',fields:[{name:'decision',label:'Kurul karar / değerlendirme notu',type:'textarea',rows:6,required:true,value:'Ölçme sonuçları gözden geçirildi; hedef altı çıktılar için iyileştirme aksiyonları Quality360 üzerinden izlenecektir.'}]});if(!d)return;try{await api('POST',`/api/assessment-plans/${plan.id}/reviews`,{decision:d.decision,final:true});toast('Yıllık ölçme review snapshot donduruldu.');await loadAssessmentAssurance();}catch(e){toast(e.message,'error')}});

// ---------------------------------------------------------------------------
// 6.63 Institutional Accreditation Readiness
// ---------------------------------------------------------------------------
let irLoaded=false;
function irStatusBadge(status){
  const labels={ready:'Hazır',attention:'Dikkat',risk:'Riskli',gap:'Eksik'};
  return `<span class="badge ir-status ${esc(status||'attention')}">${esc(labels[status]||status||'Dikkat')}</span>`;
}
async function prepareInstitutionalReadiness(){
  const year=document.getElementById('irYear');
  if(!irLoaded){
    const cat=await api('GET','/api/catalogs');
    year.innerHTML=(cat.academic_years||['2026-2027']).map(x=>`<option>${esc(x)}</option>`).join('');
    if(!year.value)year.value='2026-2027';
    document.getElementById('irReload')?.addEventListener('click',loadInstitutionalReadiness);
    document.getElementById('irFreeze')?.addEventListener('click',freezeInstitutionalReadiness);
    document.getElementById('irCrosswalkForm')?.addEventListener('submit',createInstitutionalCrosswalk);
    irLoaded=true;
  }
  await loadInstitutionalReadiness();
}
async function loadInstitutionalReadiness(){
  const year=document.getElementById('irYear')?.value||'2026-2027';
  try{
    const cycleYear=Number(String(year).slice(0,4))||2026;
    const [data,crosswalks,snapshots,lifecycle]=await Promise.all([
      api('GET',`/api/quality360/institutional/readiness?academic_year=${encodeURIComponent(year)}`),
      api('GET','/api/quality360/institutional/crosswalks'),
      api('GET',`/api/quality360/institutional/readiness-snapshots?academic_year=${encodeURIComponent(year)}&scope_type=institution&scope_key=DOGUS`),
      api('GET',`/api/compliance/framework-lifecycle-profiles?cycle_year=${cycleYear}`)
    ]);
    const s=data.summary||{};
    document.getElementById('irKpis').innerHTML=[
      ['Kurumsal hazırlık',`${Number(s.institutional_readiness_percent||0).toFixed(0)}%`],
      ['Program',s.program_count||0],['Kritik açık',s.critical_gap_count||0],
      ['Açık PUKÖ',s.open_quality_cycle_count||0],['Kanıt',s.evidence_total||0],
      ['Ortak kanıt',s.reusable_evidence_count||0]
    ].map(([k,v])=>`<div class="card ir-kpi"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');
    document.getElementById('irFrameworks').innerHTML=(data.frameworks||[]).map(x=>`<article class="ir-framework"><div><b>${esc(x.family)}</b><span>${x.program_count} program · ${x.critical_gap_count} açık</span></div><div class="ir-progress"><i data-style="width:${Math.max(0,Math.min(100,Number(x.readiness_percent||0)))}%"></i></div><strong>${Number(x.readiness_percent||0).toFixed(0)}%</strong></article>`).join('')||'<div class="empty">Framework hazırlık verisi bulunamadı.</div>';
    const gaps=data.priority_gaps||[];document.getElementById('irGapCount').textContent=`${gaps.length} açık`;
    document.getElementById('irGaps').innerHTML=gaps.slice(0,12).map(g=>`<article class="ir-gap"><div><b>${esc(g.program_name)}</b><span>${esc(g.framework_family)} · ${esc(g.criterion_code||'Ölçüt')}</span><p>${esc(g.title||'Hazırlık açığı')}</p></div><div class="ir-gap-meta"><span>${esc(g.owner||'Program / Kalite Sorumlusu')}</span><small>${esc(g.due_date||'Termin atanmadı')}</small></div></article>`).join('')||'<div class="empty">Öncelikli açık bulunmuyor.</div>';
    const tl=document.getElementById('irTimeline');const asof=document.getElementById('irTimelineAsOf');if(asof)asof.textContent=`${esc(lifecycle.as_of||'')} itibarıyla`;
    if(tl)tl.innerHTML=(lifecycle.upcoming||[]).slice(0,10).map(e=>{const when=e.date||([e.start,e.end].filter(Boolean).join(' → '));return `<article class="ir-timeline-item ${e.status==='active'?'active':''}"><div class="ir-timeline-date"><b>${esc(when)}</b><span>${e.status==='active'?'Aktif':'Yaklaşıyor'}</span></div><div><strong>${esc(e.framework_family)} · ${esc(e.label)}</strong><small>${esc(e.actor||'')} · ${esc(e.stage||'')}</small></div></article>`}).join('')||'<div class="empty">Bu döngü yılı için kaynak kontrollü resmî takvim tanımlı değil.</div>';
    document.getElementById('irPrograms').innerHTML=(data.programs||[]).map(p=>`<tr data-ir-program="${p.program_id}"><td><b>${esc(p.program_name)}</b><small>${esc(p.program_code||'')}</small></td><td>${esc(p.faculty||p.department||'—')}</td><td><span class="badge">${esc(p.framework_family)} ${esc(p.framework_version||'')}</span></td><td><div class="ir-cell-progress"><span>${Number(p.readiness_percent||0).toFixed(0)}%</span><i><b data-style="width:${Math.max(0,Math.min(100,Number(p.readiness_percent||0)))}%"></b></i></div></td><td>${p.evidence_total||0}</td><td>${p.gap_count||0}</td><td>${p.open_quality_cycles||0}</td><td>${irStatusBadge(p.status)}</td></tr>`).join('');
    document.getElementById('irReusableEvidence').innerHTML=(data.reusable_evidence||[]).map(e=>`<div class="compact-record"><b>${esc(e.name)}</b><span>${esc(e.program_name)} · ${esc(e.source.family)} ${esc(e.source.criterion_code)}</span><small>${(e.targets||[]).map(t=>`${esc(t.family)} ${esc(t.criterion_code)}`).join(' · ')}</small></div>`).join('')||'<div class="empty">Henüz onaylanmış çapraz-framework kanıt ilişkisi yok.</div>';
    document.getElementById('irCrosswalkCount').textContent=`${(crosswalks||[]).filter(x=>x.review_status==='approved').length} onaylı`;
    document.getElementById('irCrosswalks').innerHTML=(crosswalks||[]).map(x=>`<div class="compact-record ir-crosswalk"><b>${esc(x.source_framework_family)} ${esc(x.source_criterion_code)} → ${esc(x.target_framework_family)} ${esc(x.target_criterion_code)}</b><span>${esc(x.rationale||'Gerekçe girilmedi')} · ${esc(x.review_status)}</span>${x.review_status==='draft'?`<div><button class="ghost small" data-ir-approve="${x.id}" type="button">Onayla</button><button class="ghost small" data-ir-reject="${x.id}" type="button">Reddet</button></div>`:''}</div>`).join('')||'<div class="empty">Crosswalk kaydı yok.</div>';
    document.querySelectorAll('[data-ir-approve]').forEach(b=>b.addEventListener('click',()=>reviewInstitutionalCrosswalk(b.dataset.irApprove,'approved')));
    document.querySelectorAll('[data-ir-reject]').forEach(b=>b.addEventListener('click',()=>reviewInstitutionalCrosswalk(b.dataset.irReject,'rejected')));
    document.getElementById('irSnapshots').innerHTML=(snapshots||[]).map(x=>`<div class="compact-record"><b>Snapshot #${x.snapshot_no} · ${esc(x.academic_year)}</b><span>${esc(x.frozen_by||'Sistem')} · ${esc(String(x.frozen_at||'').replace('T',' ').slice(0,16))}</span><small>SHA-256 ${esc((x.content_sha256||'').slice(0,18))}…</small></div>`).join('')||'<div class="empty">Henüz yönetim snapshot\'ı dondurulmadı.</div>';
  }catch(err){toast(err.message,'error')}
}
async function createInstitutionalCrosswalk(ev){
  ev.preventDefault();
  try{
    await api('POST','/api/quality360/institutional/crosswalks',{
      source_framework_family:document.getElementById('irCrossSrcFamily').value,
      source_framework_version:document.getElementById('irCrossSrcVersion').value,
      source_criterion_code:document.getElementById('irCrossSrcCode').value,
      target_framework_family:document.getElementById('irCrossDstFamily').value,
      target_framework_version:document.getElementById('irCrossDstVersion').value,
      target_criterion_code:document.getElementById('irCrossDstCode').value,
      relationship:'supports',rationale:document.getElementById('irCrossRationale').value
    });toast('Taslak cross-framework eşleme oluşturuldu.');ev.target.reset();await loadInstitutionalReadiness();
  }catch(err){toast(err.message,'error')}
}
async function reviewInstitutionalCrosswalk(id,status){try{await api('PATCH',`/api/quality360/institutional/crosswalks/${id}`,{review_status:status});toast(status==='approved'?'Eşleme onaylandı.':'Eşleme reddedildi.');await loadInstitutionalReadiness();}catch(err){toast(err.message,'error')}}
async function freezeInstitutionalReadiness(){
  const year=document.getElementById('irYear')?.value||'2026-2027';
  try{const x=await api('POST','/api/quality360/institutional/readiness-snapshots',{academic_year:year,scope_type:'institution',scope_key:'DOGUS'});toast(`Snapshot #${x.snapshot_no} donduruldu.`);await loadInstitutionalReadiness();}catch(err){toast(err.message,'error')}
}


let acceptanceLoaded=false;
async function prepareProductionAcceptance(){
  if(!acceptanceLoaded){document.getElementById('acceptanceReload')?.addEventListener('click',loadProductionAcceptance);acceptanceLoaded=true;}
  await loadProductionAcceptance();
}
async function loadProductionAcceptance(){
  const d=await api('GET','/api/production-acceptance');
  document.getElementById('acceptanceScore').textContent=`${d.score}%`;
  document.getElementById('acceptanceSummary').innerHTML=[['Zorunlu kapı',d.required_total],['Kapanan',d.required_passed],['Release',d.release_ready?'HAZIR':'BEKLİYOR']].map(([k,v])=>`<div class="card ir-kpi"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');
  document.getElementById('acceptanceGates').innerHTML=(d.gates||[]).map(g=>`<article class="compact-record acceptance-gate"><b>${esc(g.title)}</b><span>Sistem: ${esc(g.system_status)} · Kurum: ${esc(g.manual_status)}${g.required?' · Zorunlu':''}</span><small>${esc(g.system_detail||'')}</small><div class="row"><input data-acceptance-evidence="${g.key}" placeholder="Kanıt / ticket / rapor referansı" value="${esc(g.evidence_ref||'')}"><input data-acceptance-note="${g.key}" placeholder="Kabul notu" value="${esc(g.note||'')}"><button class="ghost small" data-acceptance-pass="${g.key}" type="button">PASS</button><button class="ghost small" data-acceptance-pending="${g.key}" type="button">Bekliyor</button></div></article>`).join('');
  document.querySelectorAll('[data-acceptance-pass]').forEach(b=>b.addEventListener('click',()=>updateAcceptanceGate(b.dataset.acceptancePass,'passed')));
  document.querySelectorAll('[data-acceptance-pending]').forEach(b=>b.addEventListener('click',()=>updateAcceptanceGate(b.dataset.acceptancePending,'pending')));
}
async function updateAcceptanceGate(key,status){
  const evidence=document.querySelector(`[data-acceptance-evidence="${key}"]`)?.value||'';const note=document.querySelector(`[data-acceptance-note="${key}"]`)?.value||'';
  if(status==='passed'&&!evidence.trim())return toast('PASS için kanıt / ticket / rapor referansı girin.','error');
  await api('PATCH',`/api/production-acceptance/${encodeURIComponent(key)}`,{status,evidence_ref:evidence,note});toast('Kabul kapısı güncellendi.');await loadProductionAcceptance();
}
