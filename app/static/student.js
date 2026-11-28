(()=>{
  const q=new URLSearchParams(location.search),ex=q.get('exam'),st=q.get('student');
  const token=decodeURIComponent((location.hash.match(/(?:^#|&)t=([^&]+)/)||[])[1]||'');
  const $=id=>document.getElementById(id);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const base=`/api/public/student-exam/${encodeURIComponent(ex)}/${encodeURIComponent(st)}`;
  const H={'X-DOU-Student-Token':token};
  function fail(m){$('state').textContent='Erişim yok';$('state').classList.add('bad');$('err').textContent=m;$('err').classList.remove('hidden');$('main').classList.add('hidden')}
  async function api(p,o={}){const r=await fetch(base+p,{...o,headers:{...H,...(o.headers||{})}});if(!r.ok){let m='İstek başarısız';try{m=(await r.json())?.error?.message||m}catch{}throw new Error(m)}return r}
  const label={open:'İnceleniyor',accepted:'Kabul edildi',rejected:'Reddedildi'};
  async function load(){
    if(!ex||!st||!token)return fail('Bağlantı eksik veya geçersiz.');
    history.replaceState(null,'',location.pathname+location.search);
    let d;try{d=await (await api('')).json()}catch(e){return fail(e.message)}
    $('who').textContent=`${d.student.student_no} · ${d.student.name}`;$('state').textContent='Yalnızca sizin kâğıdınız';
    $('exTitle').textContent=d.exam.title;$('total').textContent=`${d.total} / ${d.possible}`;
    $('deadline').textContent=d.appeal_open?`İtiraz son tarihi: ${d.appeal_deadline.slice(0,10)}`:'İtiraz süresi sona erdi.';
    const open=new Set(d.appeals.filter(a=>a.status==='open').map(a=>a.question_id));
    $('qs').innerHTML=d.questions.map(x=>`<div class="record"><b>${x.no}. ${esc(x.text)}</b><small>${x.type==='mcq'?`Cevabınız: ${esc(x.answer??'—')} · Doğru: ${esc(x.correct_answer??'—')}`:`Rubrik puanları: ${esc(Object.entries(x.rubric_scores||{}).map(([k,v])=>k+': '+v).join(', ')||'—')}`} · <b>${x.awarded}/${x.points}</b></small>${d.appeal_open&&!open.has(x.id)?`<div class="search"><input data-r="${x.id}" placeholder="İtiraz gerekçeniz (en az 10 karakter)"><button class="link" data-q="${x.id}">İtiraz et</button></div>`:open.has(x.id)?'<small class="ok">İtirazınız inceleniyor</small>':''}</div>`).join('');
    $('outcomes').innerHTML=(d.outcomes||[]).length?d.outcomes.map(o=>`<div class="record"><b>${esc(o.code)} · ${esc(o.description)}</b><small>Gerçekleşme %${Number(o.attainment_percent).toFixed(1)} · Hedef %${Number(o.target_percent).toFixed(0)} · ${o.status==='achieved'?'Hedefe ulaştınız':'Hedefin altında'}</small></div>`).join(''):'<p class="note">Bu sınav için çıktı bilgisi yok.</p>';
    $('appeals').innerHTML=d.appeals.map(a=>`<div class="record"><b>Soru ${esc(d.questions.find(x=>x.id===a.question_id)?.no??'—')} · ${esc(label[a.status]||a.status)}</b><small>${esc(a.reason)}${a.decision_note?' — Karar: '+esc(a.decision_note):''}</small></div>`).join('')||'<div class="empty">İtirazınız yok.</div>';
    $('scans').innerHTML=d.scan_pages.length?'':'<div class="empty">Taranmış sayfa yok.</div>';
    for(const p of d.scan_pages){try{const b=await (await api(`/scan/${p.id}`)).blob();const i=new Image();i.className='scan-img';i.src=URL.createObjectURL(b);i.alt=`Sayfa ${p.page_no}`;$('scans').appendChild(i)}catch{}}
    document.querySelectorAll('[data-q]').forEach(b=>b.onclick=async()=>{const reason=document.querySelector(`[data-r="${b.dataset.q}"]`).value.trim();if(reason.length<10)return alert('Gerekçe en az 10 karakter olmalı.');b.disabled=true;try{await api('/appeals',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question_id:Number(b.dataset.q),reason})});load()}catch(e){alert(e.message);b.disabled=false}});
    $('main').classList.remove('hidden');
  }
  load().catch(e=>fail(e.message));
})();
