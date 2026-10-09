// Installed ONLY on Orquestra's origin. No injection into provider pages.
(() => {
  'use strict';
  if (window.top !== window || location.origin!=='https://orquestra-dev-app.vercel.app')return;
  const CHANNEL='orq-browser-bridge';
  window.addEventListener('message',event=>{
    if(event.source!==window||event.origin!==location.origin)return;
    const msg=event.data;
    if(!msg||msg.source!=='orquestra-web'||msg.type!=='ORQ_BRIDGE_PING'
       ||typeof msg.nonce!=='string'||msg.nonce.length>80||msg.nonce.length<20)return;
    chrome.runtime.sendMessage({channel:CHANNEL,action:'status'},response=>{
      if(chrome.runtime.lastError || response?.ok!==true || response?.protocol!==1)return;
      window.postMessage({source:'orquestra-extension',type:'ORQ_BRIDGE_STATUS',
        protocol:1,nonce:msg.nonce,
        chatgptTabOpen:response.chatgptTabOpen===true,
        claudeTabOpen:response.claudeTabOpen===true},location.origin);
    });
  });
})();