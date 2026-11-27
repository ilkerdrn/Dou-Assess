(()=>{
  // Read-only evidence room for external evaluators. All data comes from /room endpoints (header token only).
  const q=new URLSearchParams(location.search);const ws=q.get('workspace');
  let token=(location.hash.match(/(?:^#|&)token=([^&]+)/)||[])[1];token=token?decodeURIComponent(token):null;
  if(!ws||!token)return;
  const base=`/api/public/evaluator-workspaces/${encodeURIComponent(ws)}/room`;
  const body=document.getElementById('roomBody'),crumbs=document.getElementById('roomCrumbs'),tabs=document.getElementById('roomTabs');
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>v==null||v===''?'—':(Math.round(Number(v)*100)/100);
  const pct=v=>v==null?'—':num(v)+'%';
  const st=v=>v==null?'':`<span class="${Number(v.attainment_percent)>=Number(v.target_percent)?'ok':'bad'}">${pct(v.attainment_percent)}</span>`;
  async function api(path){const r=await fetch(base+path,{headers:{'X-DOU-Evaluator-Token':token}});if(!r.ok){let m='İstek başarısız';try{m=(await r.json())?.error?.message||m}catch{}throw new Error(m)}return r}
  const json=async p=>(await api(p)).json();
  async function openBlob(path){const w=window.open('','_blank');try{const b=await (await api(path)).blob();w.location=URL.createObjectURL(b)}catch(e){w.close();alert(e.message)}}
  const table=(head,rows)=>`<div class="tw"><table class="rt"><thead><tr>${head.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')||`<tr><td colspan="${head.length}" class="empty">Kayıt yok.</td></tr>`}</tbody></table></div>`;
  const commentBox=(refType,refId)=>`<h3>Kuruma soru / yorum</h3><div class="search"><input id="cTitle" maxlength="200" placeholder="Başlık"><button class="link" id="cSend">Gönder</button></div><textarea id="cNote" rows="2" maxlength="4000" placeholder="Soru veya gözleminiz (kurumun ziyaret notlarına düşer)" style="width:100%;font:inherit;border:1px solid var(--line);border-radius:6px;padding:7px"></textarea><div class="note" id="cMsg">Bu, salt-okunur odada yapabileceğiniz tek yazma işlemidir.</div>`;
  function bindComment(refType,refId){const send=body.querySelector('#cSend');if(!send)return;send.onclick=async()=>{const title=body.querySelector('#cTitle').value.trim();if(title.length<2)return;send.disabled=true;try{const r=await fetch(base+'/comments',{method:'POST',headers:{'X-DOU-Evaluator-Token':token,'Content-Type':'application/json'},body:JSON.stringify({title,note:body.querySelector('#cNote').value,ref_type:refType,ref_id:refId})});if(!r.ok)throw new Error((await r.json())?.error?.message||'Gönderilemedi');body.querySelector('#cMsg').textContent='Gönderildi.';body.querySelector('#cTitle').value='';body.querySelector('#cNote').value=''}catch(e){body.querySelector('#cMsg').textContent=e.message}finally{send.disabled=false}}}
  async function comments(){setCrumbs([{t:'Yorumlarım'}]);const d=await json('/comments');body.innerHTML=table(['Başlık','Not','Kurum yanıtı','Bağlam','Tarih'],d.map(x=>`<tr><td>${esc(x.title)}</td><td>${esc(x.note)}</td><td>${(x.replies||[]).map(r=>esc(r.note)).join('<hr>')||'<span class="note">Bekliyor</span>'}</td><td>${(x.refs||[]).map(r=>`<span class="chip">${esc(r)}</span>`).join('')}</td><td>${esc((x.created_at||'').slice(0,16).replace('T',' '))}</td></tr>`))+commentBox('',null);bindComment('',null)}
  const view={stack:[]};
  function setCrumbs(items){crumbs.innerHTML=items.map((x,i)=>x.go?`<a data-i="${i}">${esc(x.t)}</a>`:esc(x.t)).join(' › ');crumbs.querySelectorAll('a').forEach(a=>a.onclick=()=>items[a.dataset.i].go())}
  async function overview(year){
    const d=await json(''+(year?`?academic_year=${encodeURIComponent(year)}`:''));setCrumbs([{t:d.program.name}]);
    body.innerHTML=`<div class="kv-list"><div class="kv"><span>Program</span><b>${esc(d.program.code)} · ${esc(d.program.name)}</b></div><div class="kv"><span>Fakülte / Bölüm</span><b>${esc(d.program.faculty)} / ${esc(d.program.department)}</b></div><div class="kv"><span>Öğrenci sayısı</span><b>${d.student_count}</b></div><div class="kv"><span>Ders sayısı</span><b>${d.courses.length}</b></div></div>
    <div class="search"><label>Akademik yıl <select id="yr"><option value="">Tümü</option>${d.academic_years.map(y=>`<option ${y===year?'selected':''}>${esc(y)}</option>`).join('')}</select></label></div>
    <h3>Program çıktıları</h3>${table(['Kod','Açıklama'],d.program_outcomes.map(p=>`<tr><td><b>${esc(p.code)}</b></td><td>${esc(p.description)}</td></tr>`))}
    <h3>Dersler</h3>${table(['Kod','Ders','Yıl / Dönem','Öğr. elemanı','Ders çıktısı','Sınav','Öğrenci',''],d.courses.map(c=>`<tr><td>${esc(c.code)}</td><td>${esc(c.name)}</td><td>${esc(c.academic_year)} ${esc(c.term)}</td><td>${esc(c.instructor)}</td><td>${c.outcome_count}</td><td>${c.exam_count}</td><td>${c.student_count}</td><td><button class="link" data-course="${c.id}">Aç</button></td></tr>`))}`;
    body.querySelector('#yr').onchange=e=>overview(e.target.value);body.querySelectorAll('[data-course]').forEach(b=>b.onclick=()=>course(b.dataset.course));
  }
  async function matrix(){
    const d=await json('/outcome-matrix');setCrumbs([{t:'Çıktı matrisi'}]);
    body.innerHTML=`<p class="note">Ders öğrenme çıktısı → program çıktısı katkı düzeyi (1–5).</p>`+table(['Ders','Öğrenme çıktısı',...d.program_outcomes.map(p=>p.code)],d.rows.map(r=>`<tr><td>${esc(r.course_code)}<br><small>${esc(r.academic_year)}</small></td><td><b>${esc(r.lo_code)}</b> ${esc(r.lo_description)}</td>${d.program_outcomes.map(p=>`<td class="cell">${r.contributions[p.id]??''}</td>`).join('')}</tr>`));
  }
  async function course(id){
    const d=await json('/courses/'+id);const c=d.course;
    setCrumbs([{t:'Genel',go:()=>overview()},{t:`${c.code} ${c.name}`}]);
    body.innerHTML=`<div class="kv-list"><div class="kv"><span>Dönem</span><b>${esc(c.academic_year)} ${esc(c.term)}</b></div><div class="kv"><span>Öğretim elemanı</span><b>${esc(c.instructor)}</b></div><div class="kv"><span>Geçme notu</span><b>${num(c.pass_threshold_percent)}%</b></div></div>
    <p><button class="link" id="cfile">Ders dosyasını indir (Word)</button></p><h3>Ders öğrenme çıktıları ve program çıktısı katkıları</h3>${table(['Kod','Açıklama','Hedef','Program çıktıları'],d.learning_outcomes.map(l=>`<tr><td><b>${esc(l.code)}</b></td><td>${esc(l.description)}</td><td>${pct(l.target_percent)}</td><td>${l.program_outcomes.map(p=>`<span class="chip" title="${esc(p.description)}">${esc(p.code)} · ${p.contribution}</span>`).join('')}</td></tr>`))}
    <h3>Sınavlar</h3>${table(['Sınav','Tür','Tarih','Ağırlık','Soru','Durum',''],d.exams.map(e=>`<tr><td>${esc(e.title)}</td><td>${esc(e.exam_type)}</td><td>${esc(e.exam_date||'—')}</td><td>${e.weight_percent==null?'—':pct(e.weight_percent)}</td><td>${e.question_count}</td><td>${esc(e.status)}</td><td><button class="link" data-exam="${e.id}">Aç</button></td></tr>`))}
    <h3>Kayıtlı öğrenciler</h3>${table(['No','Ad (maskeli)','Sınıf',''],d.students.map(s=>`<tr><td>${esc(s.student_no)}</td><td>${esc(s.name)}</td><td>${esc(s.class_name)}</td><td><button class="link" data-card="${s.student_id}">Karne</button></td></tr>`))}${commentBox()}`;
    bindComment('course',Number(id));body.querySelector('#cfile').onclick=async()=>{try{const b=await (await api(`/courses/${id}/course-file.docx`)).blob();const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=`ders-dosyasi-${c.code}.docx`;a.click()}catch(e){alert(e.message)}};body.querySelectorAll('[data-exam]').forEach(b=>b.onclick=()=>exam(b.dataset.exam,id,c));body.querySelectorAll('[data-card]').forEach(b=>b.onclick=()=>card(b.dataset.card,()=>course(id)));
  }
  async function exam(id,courseId,c){
    const d=await json('/exams/'+id);const e=d.exam,s=d.summary||{};
    setCrumbs([{t:'Genel',go:()=>overview()},{t:`${c.code} ${c.name}`,go:()=>course(courseId)},{t:e.title}]);
    body.innerHTML=`<div class="kv-list"><div class="kv"><span>Tür / Durum</span><b>${esc(e.exam_type)} · ${esc(e.status)}</b></div><div class="kv"><span>Tarih / Süre</span><b>${esc(e.exam_date||'—')} · ${e.duration_minutes} dk</b></div><div class="kv"><span>Onaylayan</span><b>${esc(e.approved_by||'—')}</b></div><div class="kv"><span>Sınıf ort. / geçme</span><b>${num(s.class_average)} (${pct(s.class_average_percent)}) · ${pct(s.pass_percent)}</b></div></div>
    <p><button class="link" id="pdf">Sınav kâğıdını aç (PDF, A kitapçığı)</button></p>
    <h3>Öğrenme çıktısı başarısı</h3>${table(['Çıktı','Açıklama','Hedef','Başarı'],d.learning_outcomes.map(l=>`<tr><td><b>${esc(l.code)}</b></td><td>${esc(l.description)}</td><td>${pct(l.target_percent)}</td><td>${st(l)}</td></tr>`))}
    <h3>Program çıktısı başarısı</h3>${table(['Çıktı','Açıklama','Hedef','Başarı'],d.program_outcomes.map(l=>`<tr><td><b>${esc(l.code)}</b></td><td>${esc(l.description)}</td><td>${pct(l.target_percent)}</td><td>${st(l)}</td></tr>`))}
    <h3>Sorular ve cevap anahtarı</h3>${table(['#','Soru','Tür','Puan','Çıktılar','Doğru / beklenen cevap','Başarı'],d.questions.map(x=>`<tr><td>${x.order_no}</td><td>${esc(x.text)}${x.has_image?' <span class="chip">görsel</span>':''}</td><td>${esc(x.type)}</td><td>${num(x.points)}</td><td>${x.learning_outcomes.map(k=>`<span class="chip">${esc(k)}</span>`).join('')}</td><td>${esc(x.correct_answer||x.expected_answer||'—')}</td><td>${pct(x.attainment_percent)}</td></tr>`))}
    <h3>Öğrenciler</h3>${table(['No','Ad (maskeli)','Katılım','Puan','%','Tarama',''],d.students.map(x=>`<tr><td>${esc(x.student_no)}</td><td>${esc(x.name)}</td><td>${esc(x.attendance)}</td><td>${num(x.total_score)}</td><td>${pct(x.score_percent)}</td><td>${x.has_scan?'var':'—'}</td><td><button class="link" data-st="${x.student_id}">Kâğıt</button></td></tr>`))}${commentBox()}`;
    bindComment('exam',Number(id));body.querySelector('#pdf').onclick=()=>openBlob(`/exams/${id}/paper.pdf`);
    body.querySelectorAll('[data-st]').forEach(b=>b.onclick=()=>studentExam(id,b.dataset.st,()=>exam(id,courseId,c)));
  }
  async function studentExam(examId,sid,back){
    const d=await json(`/exams/${examId}/students/${sid}`);setCrumbs([{t:'← Sınava dön',go:back},{t:`${d.student.student_no} ${d.student.name}`}]);
    body.innerHTML=`<div class="kv-list"><div class="kv"><span>Toplam</span><b>${num(d.total_score)} / ${num(d.total_possible_points)} (${pct(d.score_percent)})</b></div><div class="kv"><span>Katılım</span><b>${esc(d.attendance)}</b></div></div>
    <h3>Madde bazlı değerlendirme</h3>${table(['#','Soru','Öğrenci cevabı','Doğru','Puan'],d.answers.map(a=>`<tr><td>${a.order_no}</td><td>${esc(a.text)}</td><td>${esc(a.answer??'—')}</td><td>${esc(a.correct_answer??'')}</td><td>${num(a.awarded_points)} / ${num(a.points)}</td></tr>`))}
    <h3>Öğrenme çıktısı başarısı</h3>${table(['Çıktı','Başarı'],d.learning_outcomes.map(l=>`<tr><td><b>${esc(l.code)}</b> ${esc(l.description)}</td><td>${st(l)}</td></tr>`))}
    <h3>Taranmış sınav kâğıdı</h3><div id="scans">${d.scan_pages.filter(p=>p.has_preview).length?'':'<div class="empty">Taranmış sayfa yok.</div>'}</div>`;
    for(const p of d.scan_pages.filter(p=>p.has_preview)){try{const b=await (await api(`/scan-items/${p.id}/preview`)).blob();const i=new Image();i.className='scan-img';i.alt=`Sayfa ${p.page_no}`;i.src=URL.createObjectURL(b);body.querySelector('#scans').appendChild(i)}catch{}}
  }
  async function card(sid,back){
    const d=await json(`/students/${sid}/outcome-card`);setCrumbs([{t:'← Geri',go:back},{t:'Öğrenci çıktı karnesi'}]);
    const po=d.program_outcomes||[],cs=d.courses||[];
    body.innerHTML=`<h3>Program çıktıları</h3>${table(['Çıktı','Açıklama','Hedef','Başarı'],po.map(l=>`<tr><td><b>${esc(l.code)}</b></td><td>${esc(l.description)}</td><td>${pct(l.target_percent)}</td><td>${st(l)}</td></tr>`))}
    <h3>Dersler</h3>${table(['Ders','Çıktılar'],cs.map(c=>`<tr><td>${esc(c.course_code||c.code)} ${esc(c.course_name||c.name||'')}</td><td>${(c.learning_outcomes||[]).map(l=>`<span class="chip">${esc(l.code)} ${pct(l.attainment_percent)}</span>`).join('')}</td></tr>`))}`;
  }
  let sq='',so=0;
  async function students(){
    setCrumbs([{t:'Öğrenciler'}]);const d=await json(`/students?q=${encodeURIComponent(sq)}&limit=50&offset=${so}`);
    body.innerHTML=`<div class="search"><input id="sq" placeholder="Öğrenci numarası ara" value="${esc(sq)}"><button class="link" id="go">Ara</button></div>${table(['No','Ad (maskeli)','Sınıf',''],d.items.map(s=>`<tr><td>${esc(s.student_no)}</td><td>${esc(s.name)}</td><td>${esc(s.class_name)}</td><td><button class="link" data-card="${s.student_id}">Karne</button></td></tr>`))}<p class="note">${d.total} kayıt · ${so+1}–${Math.min(so+50,d.total)}</p><button class="link" id="pv" ${so?'':'disabled'}>‹ Önceki</button> <button class="link" id="nx" ${so+50<d.total?'':'disabled'}>Sonraki ›</button>`;
    body.querySelector('#go').onclick=()=>{sq=body.querySelector('#sq').value;so=0;students().catch(fail)};body.querySelector('#pv').onclick=()=>{so=Math.max(0,so-50);students().catch(fail)};body.querySelector('#nx').onclick=()=>{so+=50;students().catch(fail)};
    body.querySelectorAll('[data-card]').forEach(b=>b.onclick=()=>card(b.dataset.card,students));
  }
  const fail=e=>{body.innerHTML=`<div class="empty bad">${esc(e.message||'Yüklenemedi')}</div>`};
  const go={overview:()=>overview(),matrix,comments,students};
  tabs.querySelectorAll('button').forEach(b=>b.onclick=()=>{tabs.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));go[b.dataset.tab]().catch(fail)});
  overview().catch(fail);
})();
