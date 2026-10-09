// Orquestra local browser bridge status. No ChatGPT/Claude scraping or OAuth.
(() => {
  'use strict';
  const SOURCE = 'orquestra-web';
  const RESPONSE_SOURCE = 'orquestra-extension';
  const REQUEST_TYPE = 'ORQ_BRIDGE_PING';
  const RESPONSE_TYPE = 'ORQ_BRIDGE_STATUS';
  const $ = id => document.getElementById(id);
  const pending = new Map();

  function setStatus(id, detailId, label, detail, ok=false) {
    const node = $(id);
    if (!node) return;
    node.textContent = label;
    node.classList.toggle('completed',ok);
    $(detailId).textContent = detail;
  }
  function update(result){
    const g = result.chatgptTabOpen === true;
    const c = result.claudeTabOpen === true;
    setStatus('bridgeState','bridgeDetail','Extensão detectada',
      'A extensão respondeu neste navegador. Somente presença de abas foi verificada.',true);
    setStatus('gptTabState','gptTabDetail',g?'Aba aberta':'Aba não encontrada',
      g?'Aba oficial detectada. Login não verificado.':'Abra chatgpt.com no mesmo perfil do Chrome.',g);
    setStatus('claudeTabState','claudeTabDetail',c?'Aba aberta':'Aba não encontrada',
      c?'Aba oficial detectada. Login não verificado.':'Abra claude.ai no mesmo perfil do Chrome.',c);
  }
  function unavailable(){
    setStatus('bridgeState','bridgeDetail','Não detectada',
      'Extensão ausente, desativada ou sem acesso ao domínio Orquestra.');
    setStatus('gptTabState','gptTabDetail','Não verificado','Sem extensão, não é possível verificar abas.');
    setStatus('claudeTabState','claudeTabDetail','Não verificado','Sem extensão, não é possível verificar abas.');
  }
  function probe(){
    if(document.hidden)return;
    for(const [nonce,timeout] of pending){clearTimeout(timeout);pending.delete(nonce);}
    if(!window.crypto?.randomUUID){unavailable();return;}
    const nonce=window.crypto.randomUUID();
    const timeout=setTimeout(() => {
      if(!pending.has(nonce))return;
      pending.delete(nonce);
      unavailable();
    },1800);
    pending.set(nonce,timeout);
    window.postMessage({source:SOURCE,type:REQUEST_TYPE,nonce},window.location.origin);
  }
  window.addEventListener('message',event => {
    if(event.source!==window || event.origin!==window.location.origin)return;
    const v=event.data;
    if(!v || v.source!==RESPONSE_SOURCE || v.type!==RESPONSE_TYPE || v.protocol!==1
       || typeof v.nonce!=='string' || !pending.has(v.nonce))return;
    const timeout=pending.get(v.nonce);
    clearTimeout(timeout);
    pending.delete(v.nonce);
    if(typeof v.chatgptTabOpen!=='boolean' || typeof v.claudeTabOpen!=='boolean')return unavailable();
    update(v);
  });
  $('bridgeRefresh')?.addEventListener('click',probe);
  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden && !$('connections')?.hidden)probe();
  });
  document.querySelectorAll('[data-page="connections"]').forEach(button =>
    button.addEventListener('click',()=>setTimeout(probe,0)));
  // No tokens, tabs, prompts or messages persist anywhere.
  setTimeout(probe,0);
})();