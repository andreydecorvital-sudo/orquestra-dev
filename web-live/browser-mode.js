// Browser-first assistance: no access to ChatGPT/Claude cookies or APIs.
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const urls = Object.freeze({ gpt:'https://chatgpt.com/', claude:'https://claude.ai/new' });
  const state = { title:'', instructions:'', role:'gpt', prompt:'' };
  const description = {
    gpt: 'Você é um engenheiro experiente. Produza uma solução concreta, segura, com testes propostos e pontos que precisam ser verificados.',
    claude: 'Você é um arquiteto e revisor independente. Priorize clareza, riscos, acessibilidade, qualidade e critérios de aceitação.'
  };
  function build(title, instructions, role){
    if (!['gpt','claude'].includes(role)) throw Error('Especialista não permitido');
    if (title.length < 3 || title.length > 140 || instructions.length < 5 || instructions.length > 7000)
      throw Error('Preencha um título e objetivo válidos');
    return [
      '[ORQUESTRA DEV — MISSÃO NO NAVEGADOR]',
      'Especialista: '+(role==='gpt'?'ChatGPT':'Claude'),
      description[role],
      'Título: '+title, 'Objetivo:', instructions, '',
      'Regras: não invente resultados de testes, não alegue acesso a ferramentas ou arquivos que não recebeu.',
      'Se houver código, explique como validar, proteja dados e indique o que precisa de aprovação.',
      'A resposta será avaliada manualmente; não execute deploy, compras ou ações externas.'
    ].join('\n');
  }
  function makeReview(answer){
    if (!state.prompt) throw Error('Prepare primeiro uma missão');
    if (!answer.trim()) throw Error('Cole primeiro a resposta recebida no chat');
    if (answer.length > 22000) throw Error('Resposta acima do limite permitido');
    const other = state.role==='gpt'?'Claude':'ChatGPT';
    return [
      '[ORQUESTRA DEV — REVISÃO INDEPENDENTE]',
      'Você está no '+other+'. A resposta a seguir foi escrita em outro chat.',
      'Encontre erros factuais, problemas técnicos, lacunas de segurança e critérios de aceite faltantes.',
      'Não afirme que executou testes; se faltar contexto, especifique o que deve ser verificado.',
      'MISSÃO ORIGINAL:\n'+state.prompt,
      'RESPOSTA PARA REVISAR:\n'+answer,
      'Entregue: achados priorizados, correções sugeridas e uma versão final se for possível.'
    ].join('\n');
  }
  async function copy(text, target, statusId){
    if (!text.trim()){ $(statusId).textContent='Prepare o texto antes de copiar.';return; }
    try {
      if(!navigator.clipboard?.writeText) throw Error('clipboard_unavailable');
      await navigator.clipboard.writeText(text);
      $(statusId).textContent='Texto copiado. Cole na aba oficial do '+(target==='claude'?'Claude.':'ChatGPT.');
    } catch {
      const area=$(target==='review'?'browserReviewPrompt':'browserPrompt');
      area.focus();area.select();
      $(statusId).textContent='Selecione e copie com Ctrl+C, depois cole no chat oficial.';
    }
  }
  $('browserForm').addEventListener('submit', event => {
    event.preventDefault();
    const form=new FormData(event.currentTarget);
    const title=String(form.get('title')||'').trim();
    const instructions=String(form.get('instructions')||'').trim();
    const role=String(form.get('role')||'');
    try {
      const prompt=build(title,instructions,role);
      Object.assign(state,{title,instructions,role,prompt});
      $('browserPrompt').value=prompt;
      $('browserReviewPrompt').value='';
      $('browserBuildMsg').textContent='Missão pronta. Copie o texto e abra '+(role==='gpt'?'o ChatGPT':'o Claude')+'.';
      $('browserReviewMsg').textContent='';
    } catch(e){ $('browserBuildMsg').textContent=e.message || 'Não foi possível preparar a missão'; }
  });
  $('browserCopy').addEventListener('click',() => copy($('browserPrompt').value,state.role,'browserBuildMsg'));
  $('browserReview').addEventListener('click',() => {
    try {
      $('browserReviewPrompt').value=makeReview($('browserAnswer').value);
      $('browserReviewMsg').textContent='Revisão pronta. Copie e cole no outro chat oficial.';
    }catch(e){$('browserReviewMsg').textContent=e.message||'Erro na revisão'}
  });
  $('browserCopyReview').addEventListener('click',() => copy($('browserReviewPrompt').value,'review','browserReviewMsg'));
  $('browserClear').addEventListener('click',() => {
    Object.assign(state,{title:'',instructions:'',role:'gpt',prompt:''});
    $('browserForm').reset();
    for (const id of ['browserPrompt','browserAnswer','browserReviewPrompt']) $(id).value='';
    $('browserBuildMsg').textContent='Textos apagados desta aba.';
    $('browserReviewMsg').textContent='';
  });
  // These links open the official websites; no attempt to embed or hijack login.
  if ($('browserChatGPT')?.href !== urls.gpt || $('browserClaude')?.href !== urls.claude) {
    $('browserBuildMsg').textContent='Confira os endereços dos chats oficiais.';
  }
})();