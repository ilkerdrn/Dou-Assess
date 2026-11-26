(()=>{
  const q=new URLSearchParams(location.search);const workspace=q.get('workspace');
  const token=(location.hash.match(/(?:^#|&)token=([^&]+)/)||[])[1];
  const state=document.getElementById('accessState');const error=document.getElementById('errorPanel');const panel=document.getElementById('workspacePanel');
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const record=(title,meta)=>`<div class="record"><b>${esc(title||'Kayıt')}</b><small>${esc(meta||'')}</small></div>`;
  function fail(message){state.textContent='Erişim yok';state.classList.add('bad');document.getElementById('errorText').textContent=message;error.classList.remove('hidden');panel.classList.add('hidden')}
  async function run(){
    if(!workspace||!token)return fail('Davet bağlantısı eksik veya geçersiz. Kalite biriminden yeni bir bağlantı isteyin.');
    // Remove the secret from browser history/address bar after reading the URL fragment.
    history.replaceState(null,'',`${location.pathname}?workspace=${encodeURIComponent(workspace)}`);
    const r=await fetch(`/api/public/evaluator-workspaces/${encodeURIComponent(workspace)}/snapshot`,{headers:{'X-DOU-Evaluator-Token':decodeURIComponent(token)}});
    if(!r.ok){let m='Değerlendirici erişimi doğrulanamadı.';try{const j=await r.json();m=j?.error?.message||m}catch{}return fail(m)}
    const d=await r.json(),a=d.application||{},f=d.framework_snapshot||{},w=d.workspace||{};
    state.textContent='Salt okunur erişim';document.getElementById('frameworkName').textContent=`${f.framework_code||a.framework_code||'—'} ${f.framework_version||''}`.trim();document.getElementById('academicYear').textContent=a.academic_year||'—';document.getElementById('applicationStage').textContent=a.stage||'—';document.getElementById('snapshotSha').textContent=d.snapshot_sha256||'—';
    document.getElementById('applicationInfo').innerHTML=[['Değerlendirici',w.evaluator_name||w.evaluator_email],['E-posta',w.evaluator_email],['Erişim türü',w.access_mode],['Son kullanım',w.last_access_at||'İlk erişim'],['Başvuru türü',a.application_type],['Değerlendirme modu',a.evaluation_mode],['Sorumlu',a.owner],['Son geçerlilik',w.expires_at]].map(([k,v])=>`<div class="kv"><span>${esc(k)}</span><b>${esc(v||'—')}</b></div>`).join('');
    const req=d.document_requests||[],find=d.findings||[],notes=d.visit_notes||[];document.getElementById('requestCount').textContent=req.length;document.getElementById('findingCount').textContent=find.length;document.getElementById('noteCount').textContent=notes.length;
    document.getElementById('documentRequests').innerHTML=req.map(x=>record(x.title,`${x.criterion_code||''} · ${x.status||''} · termin ${x.due_date||'—'}`)).join('')||'<div class="empty">Açık belge talebi yok.</div>';
    document.getElementById('findings').innerHTML=find.map(x=>record(x.title||x.finding_type||'Bulgu',`${x.criterion_code||''} · ${x.severity||''} · ${x.status||''}`)).join('')||'<div class="empty">Kayıtlı bulgu yok.</div>';
    document.getElementById('visitNotes').innerHTML=notes.map(x=>record(x.title||x.note_type||'Ziyaret notu',x.note||x.content||x.description||'')).join('')||'<div class="empty">Paylaşılmış ziyaret notu yok.</div>';
    panel.classList.remove('hidden');error.classList.add('hidden');
  }
  run().catch(e=>fail(e?.message||'Beklenmeyen erişim hatası.'));
})();
