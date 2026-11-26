(function(root){
  'use strict';
  function parseRubricText(value){
    const lines=String(value||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
    if(!lines.length)return {};
    return {criteria:lines.map((line,i)=>{
      const parts=line.split('|');
      const label=(parts[0]||'').trim();
      const max=Number((parts[1]||'').trim().replace(',','.'));
      if(!label||!Number.isFinite(max)||max<=0)throw new Error(`Rubrik ${i+1}. satırı "Ölçüt | Puan" biçiminde olmalıdır.`);
      return {id:`c${i+1}`,label,max_points:max};
    })};
  }
  function formatRubric(rubric){
    return (rubric?.criteria||[]).map(x=>`${x.label} | ${x.max_points}`).join('\n');
  }
  function paperFormatLabel(exam){
    const size=exam?.paper_size||'A4';
    const orientation=exam?.paper_orientation==='landscape'?'Yatay':'Dikey';
    return `${size} · ${orientation}`;
  }
  function assessmentWeightState(total){
    const value=Number(total||0);
    return {total:value,valid:Math.abs(value-100)<0.001,remaining:Math.max(0,100-value)};
  }
  root.DOUAssessmentEngine=Object.freeze({parseRubricText,formatRubric,paperFormatLabel,assessmentWeightState});
})(window);
