/* DOU Assess 6.70.11.5 — standalone pilot login fallback
   Deliberately independent from app.js/runtime-core.js so login still works
   when a later application initialization error prevents normal handlers. */
(function(){
  'use strict';
  const USER_KEY='douPilotUser';
  const SESSION_KEY='douPilotSession';
  const $=id=>document.getElementById(id);

  function status(message,type){
    const el=$('pilotLoginError');
    if(!el) return;
    el.textContent=message||'';
    el.classList.toggle('show',!!message);
    el.dataset.loginStatus=type||'';
  }
  function busy(on){
    const btn=$('loginPilotBtn');
    $('pilotLoginBox')?.classList.toggle('is-busy',!!on);
    if(!btn) return;
    btn.disabled=!!on;
    const text=on?'Giriş yapılıyor… ':'Sisteme giriş yap ';
    if(btn.firstChild) btn.firstChild.textContent=text;
  }
  async function jsonFetch(url,options={},timeoutMs=10000){
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),timeoutMs);
    try{
      const r=await fetch(url,{...options,cache:'no-store',signal:controller.signal});
      const ct=r.headers.get('content-type')||'';
      const data=ct.includes('application/json')?await r.json():await r.text();
      if(!r.ok){
        const msg=(data&&typeof data==='object'&&(data.error?.message||data.detail||data.message))||String(data||`HTTP ${r.status}`);
        throw new Error(msg);
      }
      return data;
    }catch(e){
      if(e?.name==='AbortError') throw new Error('Sunucu yanıt vermedi. 10 saniyelik giriş zaman aşımı oluştu.');
      throw e;
    }finally{clearTimeout(timer);}
  }
  async function populate(){
    const sel=$('loginPilotUser');
    if(!sel) return;
    try{
      const cfg=await jsonFetch('/api/auth/config',{},8000);
      window.state=window.state||{};
      window.state.authConfig=cfg;
      if(cfg?.auth_required) return;
      const users=await jsonFetch('/api/auth/pilot-users',{},8000);
      if(!Array.isArray(users)||!users.length) throw new Error('Aktif pilot kullanıcı bulunamadı.');
      const saved=localStorage.getItem(USER_KEY)||'pilot-admin@local';
      const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
      sel.innerHTML=users.map(u=>`<option value="${esc(u.email)}">${esc(u.display_name||u.email)} · ${esc(u.email)}</option>`).join('');
      if([...sel.options].some(o=>o.value===saved)) sel.value=saved;
    }catch(e){status(e?.message||'Kullanıcı listesi yüklenemedi.','error');}
  }
  function reveal(email,user){
    window.state=window.state||{};
    window.state.currentUser=user;
    localStorage.setItem(USER_KEY,email);
    localStorage.setItem(SESSION_KEY,'1');

    const name=$('currentUserName'); if(name) name.textContent=user.display_name||user.email||email;
    const roles=$('currentUserRoles'); if(roles) roles.textContent=(user.roles||[]).map(x=>x.role_label||x.role).join(' · ')||'Rol atanmamış';
    const side=$('pilotUserSelect');
    if(side&&[...side.options].some(o=>o.value===email)) side.value=email;

    document.body.classList.remove('login-active');
    $('loginGate')?.classList.add('hidden');
    document.querySelector('.shell')?.classList.remove('app-shell-hidden');
    $('onboardingModal')?.classList.add('hidden');

    // Main app enhancement is best-effort only; none of these can re-block login.
    try{ if(typeof window.renderCurrentUserScope==='function') window.renderCurrentUserScope(); }catch(e){console.warn(e);}
    try{ if(typeof window.applyRoleUI==='function') window.applyRoleUI(); }catch(e){console.warn(e);}
    try{ if(typeof window.enterApplication==='function') window.enterApplication(); }catch(e){console.warn(e);}
    try{ if(typeof window.showPage==='function') window.showPage((user.role_names||[]).includes('quality')&&!(user.role_names||[]).includes('admin')?'quality360':'dashboard'); }catch(e){console.warn(e);}
    status('','');
  }
  async function login(){
    const email=String($('loginPilotUser')?.value||'').trim().toLowerCase();
    if(!email){status('Lütfen bir akademik kullanıcı seçin.','error');return false;}
    busy(true);status('Kullanıcı doğrulanıyor…','working');
    try{
      const user=await jsonFetch('/api/auth/me',{headers:{'X-DOU-Pilot-User':email,'Cache-Control':'no-cache'}},10000);
      if(!user?.email) throw new Error('Kullanıcı oturumu doğrulanamadı.');
      reveal(email,user);
      return true;
    }catch(e){
      localStorage.removeItem(SESSION_KEY);
      status(e?.message||'Giriş başarısız.','error');
      document.body.classList.add('login-active');
      $('loginGate')?.classList.remove('hidden');
      document.querySelector('.shell')?.classList.add('app-shell-hidden');
      return false;
    }finally{busy(false);}
  }
  window.douPilotFallbackLogin=login;

  // Capture phase wins over every legacy handler and prevents duplicate login chains.
  document.addEventListener('click',function(e){
    const btn=e.target?.closest?.('#loginPilotBtn');
    if(!btn) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    login();
  },true);
  document.addEventListener('keydown',function(e){
    if(e.key!=='Enter'||e.target?.id!=='loginPilotUser') return;
    e.preventDefault();
    e.stopImmediatePropagation();
    login();
  },true);

  populate();
})();
