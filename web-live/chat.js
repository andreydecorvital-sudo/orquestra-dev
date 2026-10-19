// Orquestra Chat: real task inbox over owner-scoped Supabase RLS.
// Honest MVP: one request = one diagnose mission. No simulated model response,
// artificial thread continuity, automatic deploy or third-party model access.
const $ = id => document.getElementById(id);
const state = {client:null,user:null,projects:[],tasks:[],nodes:[],projectId:'',selected:null,loading:false,busy:false};
const cfg = window.ORQ_CONFIG || {};
const TARGET = 'https://ydyzjpcmavqffdazteib.supabase.co';
const taskLabels = {queued:'Na fila',running:'Em execução',completed:'Concluída',failed:'Falhou',cancelled:'Cancelada'};
function notice(message,id='notice'){ $(id).textContent=message||'' }
function node(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e}
function showModal(id,visible){ $(id).hidden=!visible }
function timeLabel(raw){const d=new Date(raw||0);return Number.isFinite(+d)?d.toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'}):'—'}
function onlineNodes(){const now=Date.now();return state.nodes.filter(n=>!n.revoked_at&&n.last_seen_at&&now-Date.parse(n.last_seen_at)<120000)}
function renderConnectivity(){
 const available=onlineNodes(),status=$('executorLabel'),dot=$('executorDot');
 dot.classList.toggle('online',available.length>0);
 status.textContent=available.length?available.length+' executor(es) online':state.nodes.length?'Executor offline':'Executor não pareado';
 const kinds=new Set(available.flatMap(n=>n.capabilities||[]));
 let providers=[];
 if(kinds.has('codex')||kinds.has('joint'))providers.push('Codex');
 if(kinds.has('claude')||kinds.has('joint'))providers.push('Claude');
 if(kinds.has('hermes'))providers.push('Hermes');
 $('modelsLabel').textContent=providers.length?'Capacidades anunciadas: '+providers.join(', '):'Modelos de IA ainda não disponíveis neste workspace.';
 $('connectionStatus').textContent=!state.user?'Login necessário':!available.length?'Fila pronta · sem executor':'Executor online · fila pronta';
 $('composerHint').textContent=!state.user?'Entre para criar missões':!state.projectId?'Crie um projeto para continuar':!available.length?'Diagnóstico: entrará na fila, sem execução até parear executor':'Diagnóstico seguro: nenhuma alteração externa';
 $('send').disabled=!state.user||!state.projectId||state.busy;
}
function renderProjects(){
 const select=$('projectSelect'),saved=state.projectId;
 select.replaceChildren();
 if(!state.projects.length)select.add(new Option('Nenhum projeto cadastrado',''));
 for(const p of state.projects)select.add(new Option(p.name,p.id));
 if(state.projects.some(p=>p.id===saved))select.value=saved;
 else state.projectId=state.projects[0]?.id||'';
 if(state.projectId)select.value=state.projectId;
}
function renderHistory(){
 const list=$('missionList');list.replaceChildren();
 if(!state.user){list.append(node('span','muted','Faça login para ver suas missões.'));return}
 const entries=state.tasks.filter(t=>t.project_id===state.projectId);
 if(!entries.length){list.append(node('span','muted','Nenhuma missão ainda.'));return}
 for(const task of entries){
  const button=node('button',state.selected===task.id?'selected':'',task.title);
  button.type='button';button.title=task.title;
  button.addEventListener('click',()=>{state.selected=task.id;renderConversation();renderHistory();closeSidebar()});
  list.append(button);
 }
}
function renderConversation(){
 const welcome=$('welcome'),holder=$('messages');holder.replaceChildren();
 const task=state.tasks.find(t=>t.id===state.selected&&t.project_id===state.projectId);
 welcome.hidden=!!task;
 if(!task)return;
 const user=node('div','message user',task.instructions);
 const reply=node('section','message system');
 const top=node('div','speaker');
 top.append(node('span','mini-logo','◈'),node('span','', 'Orquestra'));
 const status=node('span','state-pill'+(task.status==='completed'?' done':task.status==='failed'?' failed':''),taskLabels[task.status]||task.status);
 top.append(status);reply.append(top);
 let summary;
 if(task.status==='queued')summary='Missão registrada no Supabase. Aguardando um executor autorizado para iniciar.';
 else if(task.status==='running')summary='Executor trabalhando. Vou mostrar o relatório assim que estiver disponível.';
 else if(task.status==='completed')summary='O executor concluiu a missão. Confira o relatório e suas evidências.';
 else if(task.status==='failed')summary='A missão falhou. Veja o relatório antes de tentar novamente.';
 else if(task.status==='cancelled')summary='Esta missão foi cancelada.';
 else summary='Status registrado: '+String(task.status||'desconhecido');
 reply.append(node('p','answer',summary));
 if(task.output) reply.append(node('pre','report',task.output));
 const meta=node('small','', 'Tipo: '+task.kind+' · '+timeLabel(task.created_at)+' · Tentativas: '+(task.attempts||0));
 reply.append(meta);holder.append(user,reply);
}
function render(){
 renderProjects();renderHistory();renderConversation();renderConnectivity();
 $('signOut').hidden=!state.user;
 $('authOverlay').hidden=!!state.user;
}
async function refresh(){
 if(!state.client||!state.user||state.loading||document.hidden)return;
 state.loading=true;
 try{
  const [projects,nodes,tasks]=await Promise.all([
   state.client.from('orq_projects').select('id,name,repo_url,created_at').order('created_at',{ascending:false}).limit(100),
   state.client.from('orq_nodes').select('id,name,capabilities,last_seen_at,revoked_at'),
   state.client.from('orq_tasks').select('id,project_id,title,instructions,kind,status,output,attempts,created_at').order('created_at',{ascending:false}).limit(100)
  ]);
  const failure=projects.error||nodes.error||tasks.error;
  if(failure)throw failure;
  state.projects=projects.data||[];state.nodes=nodes.data||[];state.tasks=tasks.data||[];
  if(!state.projectId||!state.projects.some(p=>p.id===state.projectId)){state.projectId=state.projects[0]?.id||'';state.selected=null}
  render();
  if(!state.projects.length)notice('Crie um projeto para começar. O CRM não será alterado.');
  else notice('');
 }catch(error){
  $('connectionStatus').textContent='Sincronização indisponível';
  notice('Não foi possível consultar a fila. Confira a sessão e as permissões da Orquestra.');
  console.warn('orquestra_chat_sync_error',error?.code||'unknown');
 }finally{state.loading=false}
}
async function connect(){
 if(!/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(cfg.supabaseUrl||'')||
    cfg.supabaseUrl!==TARGET ||
    !/^sb_publishable_[A-Za-z0-9_-]{8,}$/.test(cfg.supabasePublishableKey||'')){
  $('connectionStatus').textContent='Configuração indisponível';
  notice('A configuração pública do Chatbot não está disponível nesta versão.');
  $('loginNotice').textContent='Abra uma versão atualizada do painel Orquestra.';
  showModal('authOverlay',true);return;
 }
 try{
  const {createClient}=await import('https://esm.sh/@supabase/supabase-js@2.57.0');
  state.client=createClient(cfg.supabaseUrl,cfg.supabasePublishableKey,{
   auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true,storage:sessionStorage}
  });
  const {data}=await state.client.auth.getUser();
  state.user=data?.user||null;
  render();
  if(state.user)await refresh();
  state.client.auth.onAuthStateChange((event,session)=>{
   if(event==='SIGNED_OUT'){state.user=null;state.projects=[];state.nodes=[];state.tasks=[];state.projectId='';state.selected=null;render()}
   else if(event==='SIGNED_IN'&&session?.user){state.user=session.user;render();setTimeout(refresh,0)}
  });
 }catch(error){$('connectionStatus').textContent='Offline';notice('Não foi possível iniciar o cliente Supabase. Tente atualizar a página.')}
}
$('loginForm').addEventListener('submit',async e=>{
 e.preventDefault();if(!state.client)return;
 const b=e.submitter;b.disabled=true;
 try{
  const data=new FormData(e.currentTarget);
  const {error}=await state.client.auth.signInWithPassword({email:String(data.get('email')||''),password:String(data.get('password')||'')});
  if(error)throw error;
  e.currentTarget.reset();notice('','loginNotice');
 }catch(error){notice('Não foi possível entrar. Confira sua conta e senha.','loginNotice')}
 finally{b.disabled=false}
});
$('signOut').addEventListener('click',async()=>{if(state.client)await state.client.auth.signOut()});
$('projectForm').addEventListener('submit',async e=>{
 e.preventDefault();if(!state.user||!state.client)return;
 const btn=e.submitter;btn.disabled=true;
 try{
  const data=new FormData(e.currentTarget);
  const name=String(data.get('name')||'').trim(), repo_url=String(data.get('repo_url')||'').trim();
  if(name.length<2||name.length>90)throw Error('Nome inválido');
  if(repo_url&&!/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/.test(repo_url))throw Error('Informe um link GitHub válido');
  const {data:project,error}=await state.client.from('orq_projects').insert({name,repo_url}).select('id').single();
  if(error)throw error;
  state.projectId=project.id;state.selected=null;showModal('projectOverlay',false);
  e.currentTarget.reset();await refresh();
 }catch(error){notice('Não foi possível criar: '+String(error.message||'falha'),'projectNotice')}
 finally{btn.disabled=false}
});
$('addProject').addEventListener('click',()=>{notice('','projectNotice');showModal('projectOverlay',true);closeSidebar()});
$('cancelProject').addEventListener('click',()=>showModal('projectOverlay',false));
$('projectSelect').addEventListener('change',e=>{state.projectId=e.target.value;state.selected=null;render();closeSidebar()});
$('newChat').addEventListener('click',()=>{state.selected=null;renderConversation();renderHistory();$('prompt').focus();closeSidebar()});
$('composer').addEventListener('submit',async e=>{
 e.preventDefault();if(!state.client||!state.user||!state.projectId||state.busy)return;
 const instructions=$('prompt').value.trim();
 if(instructions.length<5){notice('Descreva o objetivo com pelo menos cinco caracteres.');return}
 state.busy=true;renderConnectivity();notice('Registrando missão...');
 try{
  const title=instructions.split('\n')[0].slice(0,137)||'Nova missão';
  const {data,error}=await state.client.from('orq_tasks').insert({
   project_id:state.projectId,title:title.length<3?'Nova missão':title,instructions,kind:'diagnose'
  }).select('id').single();
  if(error)throw error;
  $('prompt').value='';state.selected=data.id;
  await refresh();
  if(state.selected!==data.id)state.selected=data.id;
  renderHistory();renderConversation();notice('Missão registrada. Aguardando execução verificada.');
 }catch(error){notice('A missão não foi salva: '+String(error.message||'falha de conexão'))}
 finally{state.busy=false;renderConnectivity()}
});
$('prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('composer').requestSubmit()}});
function closeSidebar(){$('sidebar').classList.remove('open')}
$('openMenu').addEventListener('click',()=>$('sidebar').classList.add('open'));
$('closeMenu').addEventListener('click',closeSidebar);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});
setInterval(()=>{if(!document.hidden)refresh()},30000);
connect();
