// Unit-like test of extension background with a fake Chrome tabs API.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
let listener;
const current=[
  {url:'https://chatgpt.com/c/abc'},
  {url:'https://claude.ai/new'},
  {url:'https://chatgpt.com.evil.example/'},
  {url:'chrome://extensions/'}
];
const chrome={
  runtime:{
    lastError:null,
    onMessage:{addListener:(cb)=>{listener=cb}}
  },
  tabs:{query:(filter,cb)=>cb(current)}
};
vm.runInNewContext(fs.readFileSync('browser-bridge/background.js','utf8'),{chrome,URL});
let response=null;
const accepted=listener({channel:'orq-browser-bridge',action:'status'},
  {tab:{url:'https://orquestra-dev-app.vercel.app/'}},r=>{response=r});
assert.equal(accepted,true);
assert.equal(response.ok,true);
assert.equal(response.chatgptTabOpen,true);
assert.equal(response.claudeTabOpen,true);
assert.deepEqual(Object.keys(response).sort(),['chatgptTabOpen','claudeTabOpen','ok','protocol']);
response=null;
const rejected=listener({channel:'orq-browser-bridge',action:'status'},
  {tab:{url:'https://evil.example/'}},r=>{response=r});
assert.equal(rejected,false);
assert.equal(response,null);
console.log('Chrome bridge mock passed: official host matching, reduced payload and origin rejection.');
