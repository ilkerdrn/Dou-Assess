(() => {
  function showEditorNow(){
    const card=document.getElementById('bankEditorCard');
    const backdrop=document.getElementById('bankEditorBackdrop');
    document.body.classList.add('bank-editor-open');
    card?.classList.add('is-open');
    card?.setAttribute('aria-hidden','false');
    backdrop?.classList.add('is-open');
    setTimeout(()=>card?.querySelector('select,input,textarea,button')?.focus(),30);
  }
  async function openQuestionEditor(){
    try{ if(typeof window.resetBankEditor==='function') window.resetBankEditor(); }catch(e){ console.warn('bank-reset-hotfix',e); }
    try{
      const course=document.getElementById('bankCourse');
      const filter=document.getElementById('bankFilterCourse');
      const preferred=Number(window.state?.selectedCourseId||filter?.value||course?.value||0);
      if(course && preferred && [...course.options].some(o=>Number(o.value)===preferred)) course.value=String(preferred);
    }catch(e){ console.warn('bank-course-hotfix',e); }
    showEditorNow();
    try{ if(typeof window.updateBankCourseContext==='function') await window.updateBankCourseContext(); }catch(e){ console.warn('bank-outcomes-hotfix',e); }
  }
  function bind(){
    const btn=document.getElementById('bankFocusCreate');
    if(!btn || btn.dataset.qb6401Bound==='1') return;
    btn.dataset.qb6401Bound='1';
    btn.addEventListener('click',ev=>{
      ev.preventDefault();
      ev.stopImmediatePropagation();
      openQuestionEditor();
    },true);
  }
  window.openQuestionBankEditor6401=openQuestionEditor;
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',bind,{once:true}); else bind();
})();
