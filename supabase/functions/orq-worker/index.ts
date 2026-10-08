// Orquestra Dev v1.0 — authenticated device queue, no paid provider keys.
// Deploy with verify_jwt=false; independently validate user JWT or paired node secret.
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.57.0';
const admin = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!, {
  auth: { persistSession: false },
});
const allowedOrigin = Deno.env.get('ORQ_ALLOWED_ORIGIN') || 'https://orquestra-dev.vercel.app';
const apiHeaders = (origin: string | null) => ({
  'content-type': 'application/json', 'cache-control': 'no-store',
  'x-content-type-options':'nosniff',
  'access-control-allow-origin': origin === allowedOrigin ? allowedOrigin : 'null',
  'vary': 'Origin',
  'access-control-allow-headers':'authorization,apikey,content-type,x-orq-device-id,x-orq-device-secret',
  'access-control-allow-methods':'POST,OPTIONS',
});
const json = (data:unknown, status:number, origin:string|null) =>
  new Response(JSON.stringify(data), { status, headers:apiHeaders(origin) });
const hex=(bytes: Uint8Array) => Array.from(bytes).map(c => c.toString(16).padStart(2,'0')).join('');
const sha256=async(value:string)=>hex(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))));
const same=(a:string,b:string) => { if(a.length !== b.length)return false;
  let result=0; for(let i=0;i<a.length;i++)result |= a.charCodeAt(i)^b.charCodeAt(i);
  return result === 0; };
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
Deno.serve(async request => {
  const origin=request.headers.get('origin');
  const reply=(data:unknown,status=200) => json(data,status,origin);
  if(request.method==='OPTIONS') return new Response(null,{status:204,headers:apiHeaders(origin)});
  if(request.method!=='POST')return reply({error:'method_not_allowed'},405);
  const length=Number(request.headers.get('content-length')||'0');
  if(length>24000)return reply({error:'request_too_large'},413);
  let body:Record<string,unknown>;
  try { const raw=await request.text(); if(raw.length>24000)throw Error();
    const decoded=JSON.parse(raw); if(!decoded||typeof decoded!=='object'||Array.isArray(decoded))throw Error();
    body=decoded; } catch { return reply({error:'invalid_json'},400); }
  const action=body.action;
  try {
    if(action==='register') {
      if(origin && origin!==allowedOrigin)return reply({error:'invalid_origin'},403);
      const jwt=(request.headers.get('authorization')||'').replace(/^Bearer\s+/i,'');
      if(!jwt)return reply({error:'login_required'},401);
      const {data:user,error:authError}=await admin.auth.getUser(jwt);
      if(authError||!user.user)return reply({error:'session_invalid'},401);
      const name=String(body.name||'').trim().slice(0,90);
      if(!name)return reply({error:'name_required'},400);
      const secret=hex(crypto.getRandomValues(new Uint8Array(32)));
      const {data:node,error:dbError}=await admin.from('orq_nodes').insert({
        owner_id:user.user.id,name,secret_hash:await sha256(secret)
      }).select('id,name').single();
      if(dbError)throw dbError;
      return reply({node,secret}); // disclose once to authenticated owner only
    }
    const id=request.headers.get('x-orq-device-id')||'';
    const secret=request.headers.get('x-orq-device-secret')||'';
    if(!UUID.test(id)||!/^[0-9a-f]{64}$/i.test(secret))return reply({error:'device_credentials_required'},401);
    const {data:node,error:nodeError}=await admin.from('orq_nodes')
      .select('id,owner_id,secret_hash,revoked_at').eq('id',id).maybeSingle();
    if(nodeError||!node||node.revoked_at||!same(await sha256(secret),node.secret_hash))
      return reply({error:'device_not_authorized'},401);
    await admin.from('orq_nodes').update({last_seen_at:new Date().toISOString()}).eq('id',id);
    if(action==='capabilities') {
      const allowed=['diagnose','integrations','codex','claude','joint'];
      const requested=body.capabilities;
      if(!Array.isArray(requested)||requested.length>5 ||
         !requested.every(item=>typeof item==='string'&&allowed.includes(item)))
        return reply({error:'invalid_capabilities'},400);
      const capabilities=[...new Set(requested)];
      if(!capabilities.includes('diagnose'))capabilities.push('diagnose');
      const {error:updateError}=await admin.from('orq_nodes')
        .update({capabilities}).eq('id',id).eq('owner_id',node.owner_id);
      if(updateError)throw updateError;
      return reply({ok:true,capabilities});
    }
    if(action==='poll') {
      const {data,error}=await admin.rpc('orq_claim_task',{p_node_id:id});
      if(error)throw error;
      const task=data?.[0];
      return reply({task:task?{id:task.id,project_id:task.project_id,kind:task.kind,
        title:task.title,instructions:task.instructions,attempt:task.attempts,
        max_attempts:task.max_attempts,lease_expires_at:task.lease_expires_at}:null});
    }
    if(action==='heartbeat') {
      const taskId=String(body.task_id||'');
      if(!UUID.test(taskId))return reply({error:'invalid_id'},400);
      const {data,error}=await admin.rpc('orq_heartbeat_task',{p_node_id:id,p_task_id:taskId});
      if(error)throw error;
      return data===true?reply({ok:true}):reply({error:'task_not_running_or_lease_expired'},409);
    }
    if(action==='complete') {
      const taskId=String(body.task_id||'');
      if(!UUID.test(taskId))return reply({error:'invalid_id'},400);
      const output=String(body.output||'').slice(0,18000);
      const {data,error}=await admin.rpc('orq_finish_task',{
        p_node_id:id,p_task_id:taskId,p_ok:body.ok===true,p_output:output,
      });
      if(error)throw error;
      return data===true?reply({ok:true}):reply({error:'task_not_running_or_lease_expired'},409);
    }
    return reply({error:'unknown_action'},400);
  } catch(error) {
    console.error('orq-worker internal failure',error instanceof Error?error.name:'unknown');
    return reply({error:'internal_error'},500);
  }
});
