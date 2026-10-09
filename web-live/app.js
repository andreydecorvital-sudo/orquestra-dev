// Orquestra Dev v1.0 — connected UI (never stores a service role key).
// Only PUBLIC Supabase publishable credentials are accepted in setup.
const $=id=>document.getElementById(id);
const configKey='orquestra-public-supabase-config-v1';
const pageNames={home:'Visão geral',tasks:'Missões',projects:'Projetos',nodes:'Executores',settings:'Configurar'};
let client=null,mode='setup',page='settings',data={projects:[],nodes:[],tasks:[]};
function assertPublicConfig(raw){
  if(!raw || typeof raw!=='object')throw Error('Configuração inválida');
  const url=String(raw.supabaseUrl||'').trim().replace(/\/$/,'');
  const key=String(raw.supabasePublishableKey||'').trim();
  if(!/^https:\/\/[a-z0-9-]+\.supabase\.co$/i.test(url))throw Error('Informe a URL HTTPS de um projeto Supabase');
  if(!/^sb_publishable_[\w-]{8,}$/.test(key) && !/^eyJ[A-Za-z0-9._-]{30,}$/.test(key))
    throw Error('Use apenas a chave pública/publishable (nunca service_role)');
  if(/service_role|sb_secret|sk-proj|sk-ant/i.test(key))throw Error('Chave secreta não permitida');
  return {supabaseUrl:url,supabasePublishableKey:key};
}
function savedConfig(){try{const raw=window.ORQ_CONFIG?.supabaseUrl?window.ORQ_CONFIG:JSON.parse(localStorage.getItem(configKey)||'null');return assertPublicConfig(raw)}catch{return null}}
function setBanner(message,online=false){$('banner').textContent=message;$('banner').classList.toggle('online',online)}
function message(id,text){$(id).textContent=text}
function when(date){if(!date)return '—';const dt=new Date(date);return Number.isNaN(+dt)?'—':dt.toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'})}
function shortId(id){return String(id||'').slice(0,8)}
function el(tag,className,text){const e=document.createElement(tag);if(className)e.className=className;if(text!==undefined)e.textContent=text;return e}
function listItem(title,metadata,status,output){
  const row=el('div','listitem');const body=el('div','listbody');
  const h=el('strong','',title),info=el('small','',metadata);body.append(h,info);
  if(output){const details=el('details');details.append(el('summary','','Ver relatório'));const pre=el('pre','',output);details.append(pre);body.append(details)}
  const badge=el('span','status '+(status==='completed'?'completed':status==='running'?'running':''),status);
  row.append(body,badge);return row;
}
function replaceList(id,items,empty){const target=$(id);target.replaceChildren();if(!items.length){target.append(el('div','empty',empty));return}for(const row of items)target.append(row)}
function setPage(name){if(!(name in pageNames))return;page=name;document.querySelectorAll('section.page').forEach(section=>section.hidden=section.id!==name);document.querySelectorAll('[data-page]').forEach(button=>button.classList.toggle('active',button.dataset.page===name));$('crumb').textContent=pageNames[name];$('nodeSecret').hidden=true;$('nodeSecret').textContent='';window.scrollTo(0,0)}
function updateMode(){
 const active=mode==='live',authNeeded=mode==='auth';
 $('auth').hidden=!authNeeded;
 document.querySelectorAll('section.page').forEach(section=>section.hidden=authNeeded||section.id!==page);
 $('logout').hidden=!active;
 $('sideStatus').replaceChildren();const dot=el('i','dot'+(active?' on':''));$('sideStatus').append(dot,document.createTextNode(active?'Autenticado':authNeeded?'Login necessário':'Banco não conectado'));
 $('chip').textContent=active?'AUTENTICADO':authNeeded?'LOGIN NECESSÁRIO':'SEM BACKEND';
 if(active){setBanner('Backend conectado. Tarefas podem ser enviadas à fila; a execução depende de um worker pareado e autorizado.',true)}
 else if(authNeeded)setBanner('Banco conectado, mas você precisa entrar. O site não utiliza nem armazena logins de GPT ou Claude.');
 else setBanner('Configure um Supabase exclusivo em “Configurar”. Nenhuma tarefa real é executada sem essa conexão.');
 $('queueButton').disabled=!active;
}
function render(){
 const {projects,nodes,tasks}=data;
 $('queuedCount').textContent=mode==='live'?tasks.filter(t=>t.status==='queued').length:'—';
 $('runningCount').textContent=mode==='live'?tasks.filter(t=>t.status==='running').length:'—';
 $('doneCount').textContent=mode==='live'?tasks.filter(t=>t.status==='completed').length:'—';
 const online=nodes.filter(n=>!n.revoked_at&&n.last_seen_at&&(Date.now()-Date.parse(n.last_seen_at))<120000).length;
 $('nodeCount').textContent=mode==='live'?online:'—';
 for(const sel of document.querySelectorAll('.projectSelect')){
   const val=sel.value;sel.replaceChildren();
   if(!projects.length)sel.append(new Option('Cadastre um projeto primeiro',''));
   for(const project of projects)sel.append(new Option(project.name,project.id));
   if(projects.some(x=>x.id===val))sel.value=val;
 }
 const taskRows=tasks.map(t=>{
   const project=projects.find(p=>p.id===t.project_id)?.name||shortId(t.project_id);
   return listItem(t.title,project+' · '+t.kind+' · '+when(t.created_at)+' · Tentativas: '+t.attempts,t.status,t.output);
 });
 replaceList('recentList',taskRows.slice(0,4),'Sem missões ainda. Cadastre um projeto e crie a primeira tarefa.');
 replaceList('tasksList',taskRows,'Sem missões nesta conta.');
 replaceList('projectsList',projects.map(p=>listItem(p.name,p.repo_url||'Sem URL cadastrada','REGISTRADO')),'Nenhum projeto cadastrado.');
 replaceList('nodesList',nodes.map(n=>listItem(n.name,'ID: '+n.id+' · Último contato: '+when(n.last_seen_at),n.revoked_at?'REVOGADO':n.last_seen_at&&(Date.now()-Date.parse(n.last_seen_at))<120000?'ONLINE · '+(n.capabilities||[]).join(', '):'OFFLINE')),'Nenhum executor pareado.');
}
async function refresh(){if(mode!=='live'||!client)return;
 try{
  const [projects,nodes,tasks]=await Promise.all([
    client.from('orq_projects').select('id,name,repo_url,created_at').order('created_at',{ascending:false}),
    client.from('orq_nodes').select('id,name,last_seen_at,revoked_at,capabilities').order('created_at',{ascending:false}),
    client.from('orq_tasks').select('id,project_id,title,kind,status,output,created_at,started_at,finished_at,attempts').order('created_at',{ascending:false}).limit(100)
  ]);
  if(projects.error||nodes.error||tasks.error)throw projects.error||nodes.error||tasks.error;
  data={projects:projects.data||[],nodes:nodes.data||[],tasks:tasks.data||[]};render();
 }catch(error){setBanner('Não foi possível sincronizar. Verifique as migrações, permissões RLS e o projeto escolhido.');console.warn('Sync unavailable:',error?.code||'unknown')}
}
async function connect(cfg){
 try{
   const {createClient}=await import('https://esm.sh/@supabase/supabase-js@2.57.0');
   client=createClient(cfg.supabaseUrl,cfg.supabasePublishableKey,{
     auth:{autoRefreshToken:true,persistSession:true,detectSessionInUrl:true,storage:sessionStorage}
   });
   const {data:auth,error}=await client.auth.getUser();
   if(error && error.name!=='AuthSessionMissingError')console.warn('Initial auth status:',error.name);
   mode=auth?.user?'live':'auth';
   updateMode();
   if(mode==='live'){setPage('home');await refresh()}
   client.auth.onAuthStateChange((event,session)=>{
     if(event==='SIGNED_IN'&&session){mode='live';updateMode();setPage('home');setTimeout(refresh,0)}
     if(event==='SIGNED_OUT'){mode='auth';data={projects:[],nodes:[],tasks:[]};updateMode();render()}
   });
 }catch(error){client=null;mode='setup';setPage('settings');updateMode();message('setupMsg','Falha ao iniciar conexão pública. Verifique se a URL e a chave estão corretas.')}
}
document.querySelectorAll('[data-page]').forEach(b=>b.addEventListener('click',()=>setPage(b.dataset.page)));
$('setupForm').addEventListener('submit',async event=>{
 event.preventDefault();message('setupMsg','');const fd=new FormData(event.currentTarget);
 try{
   const cfg=assertPublicConfig({supabaseUrl:fd.get('supabaseUrl'),supabasePublishableKey:fd.get('publishableKey')});
   localStorage.setItem(configKey,JSON.stringify(cfg));
   await connect(cfg);
   if(mode==='auth')message('setupMsg','Conexão salva. Entre com a conta cadastrada no projeto Supabase.');
 }catch(e){message('setupMsg',e.message||'Configuração inválida')}
});
$('loginForm').addEventListener('submit',async event=>{
 event.preventDefault();if(!client)return;
 message('loginMsg','Entrando…');const fd=new FormData(event.currentTarget);
 const {error}=await client.auth.signInWithPassword({email:String(fd.get('email')),password:String(fd.get('password'))});
 message('loginMsg',error?'Não foi possível entrar. Verifique a conta e a senha.':'Conectado.');
});
$('logout').addEventListener('click',async()=>{if(client)await client.auth.signOut()});
$('disconnect').addEventListener('click',async()=>{
 if(client)await client.auth.signOut();
 localStorage.removeItem(configKey);sessionStorage.clear();
 client=null;mode='setup';data={projects:[],nodes:[],tasks:[]};render();updateMode();setPage('settings');
 message('setupMsg','Conexão local apagada.');
});
$('projectForm').addEventListener('submit',async event=>{
 event.preventDefault();if(mode!=='live'||!client){message('projectMsg','Entre no Supabase antes de cadastrar.');return}
 const fd=new FormData(event.currentTarget);
 const name=String(fd.get('name')||'').trim(),repo_url=String(fd.get('repo_url')||'').trim();
 if(name.length<2||name.length>90)return;
 if(repo_url && !/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/.test(repo_url)){message('projectMsg','Use uma URL de repositório GitHub sem credenciais.');return}
 const {error}=await client.from('orq_projects').insert({name,repo_url});
 if(error){message('projectMsg','Falha ao cadastrar: '+error.message);return}
 event.currentTarget.reset();message('projectMsg','Projeto registrado. Configure o mesmo projeto no allowlist do executor.');await refresh();
});
$('quickForm').addEventListener('submit',async event=>{
 event.preventDefault();if(mode!=='live'||!client){message('quickMsg','Backend não conectado.');return}
 const fd=new FormData(event.currentTarget);
 const title=String(fd.get('title')||'').trim(),instructions=String(fd.get('instructions')||'').trim();
 const project_id=String(fd.get('project')||''),kind=String(fd.get('kind')||'codex');
 if(!data.projects.some(p=>p.id===project_id)){message('quickMsg','Cadastre e selecione um projeto.');return}
 if(!['codex','claude','joint','diagnose','integrations'].includes(kind))return;
 if(title.length<3||instructions.length<5)return;
 message('quickMsg','Salvando na fila…');
 const {error}=await client.from('orq_tasks').insert({project_id,title,instructions,kind});
 if(error){message('quickMsg','Falha ao salvar: '+error.message);return}
 event.currentTarget.reset();message('quickMsg','Missão registrada. Aguardando um executor autorizado.');await refresh();setPage('tasks');
});
$('nodeForm').addEventListener('submit',async event=>{
 event.preventDefault();if(mode!=='live'||!client){message('nodeMsg','Faça login antes de parear.');return}
 const fd=new FormData(event.currentTarget);const name=String(fd.get('name')||'').trim();
 const projectId=String(fd.get('project_id')||'');const localPath=String(fd.get('local_path')||'').trim();
 if(!name||name.length>90)return;
 if(!data.projects.some(p=>p.id===projectId)){message('nodeMsg','Cadastre e selecione primeiro um projeto autorizado.');return}
 if(!/^[a-z]:\\[^\r\n]{3,255}$/i.test(localPath)){message('nodeMsg','Informe um caminho absoluto válido no Windows, como C:\\Orquestra\\Repos\\orquestra-dev');return}
 message('nodeMsg','Criando credencial…');
 const {data:auth}=await client.auth.getSession();
 if(!auth.session){message('nodeMsg','Sua sessão expirou.');return}
 const cfg=savedConfig();
 try{
 const result=await fetch(cfg.supabaseUrl+'/functions/v1/orq-worker',{
   method:'POST',headers:{'Authorization':'Bearer '+auth.session.access_token,
   'apikey':cfg.supabasePublishableKey,'Content-Type':'application/json'},
   body:JSON.stringify({action:'register',name})});
 const value=await result.json();
 if(!result.ok)throw Error(value.error||'pairing_failed');
 const payload={
   supabase_url:cfg.supabaseUrl,node_id:value.node.id,node_secret:value.secret,
   allow_execution:false,poll_seconds:25,projects:{
     [projectId]:{slug:'orquestra',path:localPath}
   }
 };
 const pairingFile=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'});
 const temporaryUrl=URL.createObjectURL(pairingFile);
 const download=document.createElement('a');
 download.href=temporaryUrl;download.download='orquestra-agent-worker.json';
 download.textContent='Baixar arquivo de pareamento (uma vez)';
 download.className='subtle';
 const secretDiv=$('nodeSecret');
 secretDiv.replaceChildren(document.createTextNode('Credencial criada para '+value.node.name+'. Baixe o JSON e guarde-o com segurança. NÃO compartilhe o arquivo nem o publique no GitHub. '),download);
 secretDiv.hidden=false;
 download.addEventListener('click',()=>setTimeout(()=>URL.revokeObjectURL(temporaryUrl),2000),{once:true});
 message('nodeMsg','Executor registrado. O arquivo de pareamento permanece disponível apenas nesta tela.');
 event.currentTarget.reset();await refresh();
 }catch(e){message('nodeMsg','Não foi possível parear: '+String(e.message||'falha'))}
});
$('refresh').addEventListener('click',refresh);
const cfg=savedConfig();
if(cfg){$('supabaseUrl').value=cfg.supabaseUrl;$('publishableKey').value=cfg.supabasePublishableKey;await connect(cfg)}
else{mode='setup';setPage('settings');updateMode()}
render();
setInterval(()=>{if(mode==='live'&&!document.hidden)refresh()},20000);
