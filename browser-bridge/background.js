// Queries tab URL metadata only. No cookie/content access, storage, network, or AI calls.
'use strict';
const HOME='https://orquestra-dev-app.vercel.app/';
const CHANNEL='orq-browser-bridge';
function officialSite(raw){
  try {
    const u=new URL(raw);
    if(u.protocol!=='https:')return '';
    if(u.hostname==='chatgpt.com')return 'chatgpt';
    if(u.hostname==='claude.ai')return 'claude';
  } catch { /* Chrome internal tabs may not be URLs. */ }
  return '';
}
chrome.runtime.onMessage.addListener((msg,sender,sendResponse)=>{
  if(msg?.channel!==CHANNEL || msg?.action!=='status')return false;
  if(!sender.tab || typeof sender.tab.url!=='string' || !sender.tab.url.startsWith(HOME))return false;
  chrome.tabs.query({url:['https://chatgpt.com/*','https://claude.ai/*']}, tabs=>{
    if(chrome.runtime.lastError){sendResponse({ok:false,protocol:1});return;}
    const sites=new Set(tabs.map(tab=>officialSite(tab.url)));
    sendResponse({ok:true,protocol:1,chatgptTabOpen:sites.has('chatgpt'),
      claudeTabOpen:sites.has('claude')});
  });
  return true;
});