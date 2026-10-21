// Orquestra chat persistence API. NOT deployed; no inference or provider token.
// Requires the separately approved SQL 008 migration. Never touches CRM tables.
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.57.0';

const admin = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  { auth: { persistSession: false } },
);
// Explicit, verified origins only. No wildcard project domains.
// Extra trusted origins may be supplied as a server-side secret.
const allowedOrigins = new Set([
  'https://orquestra-dev-app.vercel.app',
  'https://orquestra-dev-749aiiuwe-vitaldecor.vercel.app',
  ...(Deno.env.get('ORQ_ALLOWED_ORIGINS') || '').split(',').map(x => x.trim()).filter(Boolean),
  ...(Deno.env.get('ORQ_ALLOWED_ORIGIN') ? [Deno.env.get('ORQ_ALLOWED_ORIGIN')!] : []),
].filter(x => /^https:\/\/[a-z0-9.-]+(?::443)?$/.test(x)));
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function headers(origin: string | null): Record<string, string> {
  return {
    'content-type': 'application/json',
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff',
    'access-control-allow-origin': origin && allowedOrigins.has(origin) ? origin : 'null',
    'access-control-allow-headers': 'authorization,apikey,content-type',
    'access-control-allow-methods': 'GET,POST,OPTIONS',
    'vary': 'Origin',
  };
}

Deno.serve(async (request: Request) => {
  const origin = request.headers.get('origin');
  const reqId = crypto.randomUUID();
  const reply = (data: unknown, status = 200) =>
    new Response(JSON.stringify(data), {
      status,
      headers: { ...headers(origin), 'x-orq-request-id': reqId },
    });

  if (origin && !allowedOrigins.has(origin)) return reply({ error: 'origin_not_allowed' }, 403);
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: headers(origin) });
  }
  if (request.method === 'GET' &&
      new URL(request.url).pathname.endsWith('/health')) {
    return reply({ service: 'orq-chat', persistence: 'prepared', inference: 'not_connected' });
  }
  if (request.method !== 'POST') return reply({ error: 'method_not_allowed' }, 405);
  if (Number(request.headers.get('content-length') || '0') > 15000) {
    return reply({ error: 'request_too_large' }, 413);
  }

  let body: Record<string, unknown>;
  try {
    const raw = await request.text();
    if (raw.length > 15000) return reply({ error: 'request_too_large' }, 413);
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return reply({ error: 'invalid_json' }, 400);
    }
    body = parsed as Record<string, unknown>;
  } catch {
    return reply({ error: 'invalid_json' }, 400);
  }

  const token = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!token) return reply({ error: 'login_required' }, 401);
  const { data: verified, error: authError } = await admin.auth.getUser(token);
  if (authError || !verified.user) return reply({ error: 'session_invalid' }, 401);
  const owner = verified.user.id;
  // Chatbot Auth is also used by the CRM. Authentication alone MUST NOT
  // grant an Orquestra account. Allowlist is configured only as a server secret.
  // Fail closed if omitted; never include the list in responses or browser JS.
  const owners = (Deno.env.get('ORQ_CHAT_ALLOWED_OWNER_IDS') || '')
    .split(',')
    .map(value => value.trim().toLowerCase())
    .filter(value => UUID.test(value));
  if (owners.length === 0) return reply({ error: 'orquestra_not_configured' }, 503);
  if (!owners.includes(owner.toLowerCase())) {
    return reply({ error: 'orquestra_access_denied' }, 403);
  }
  const action = body.action;

  try {
    if (action === 'create_thread') {
      const title = typeof body.title === 'string' ? body.title.trim().slice(0, 80) : 'Nova conversa';
      if (!title) return reply({ error: 'invalid_title' }, 400);
      // Client-chosen UUID makes creation safely repeatable after a lost response.
      // It is never a permission or ownership claim; owner comes only from getUser(JWT).
      const threadId = body.thread_id;
      if (typeof threadId !== 'string' || !UUID.test(threadId)) {
        return reply({ error: 'invalid_thread_id' }, 400);
      }
      const { data, error } = await admin.from('orq_chat_threads')
        .insert({ id: threadId, owner_id: owner, title })
        .select('id,title,created_at,updated_at').single();
      if (error) {
        if (error.code !== '23505') throw error;
        // A duplicate must belong to the authenticated owner and same title.
        const { data: existing, error: lookupError } = await admin.from('orq_chat_threads')
          .select('id,title,created_at,updated_at')
          .eq('id', threadId).eq('owner_id', owner).maybeSingle();
        if (lookupError) throw lookupError;
        if (!existing || existing.title !== title) {
          return reply({ error: 'thread_conflict' }, 409);
        }
        return reply({ thread: existing }, 200);
      }
      return reply({ thread: data }, 201);
    }

    if (action === 'list_threads') {
      const { data, error } = await admin.from('orq_chat_threads')
        .select('id,title,created_at,updated_at')
        .eq('owner_id', owner).order('updated_at', { ascending: false }).limit(50);
      if (error) throw error;
      return reply({ threads: data || [] });
    }

    if (action === 'read_thread' || action === 'send') {
      const threadId = body.thread_id;
      if (typeof threadId !== 'string' || !UUID.test(threadId)) {
        return reply({ error: 'invalid_thread_id' }, 400);
      }
      const { data: thread, error: threadError } = await admin.from('orq_chat_threads')
        .select('id,title,created_at,updated_at')
        .eq('id', threadId).eq('owner_id', owner).maybeSingle();
      if (threadError) throw threadError;
      if (!thread) return reply({ error: 'thread_not_found' }, 404);

      if (action === 'read_thread') {
        const [messages, turns] = await Promise.all([
          admin.from('orq_chat_messages')
            .select('id,role,content,created_at')
            .eq('owner_id', owner).eq('thread_id', threadId)
            .order('created_at', { ascending: false }).limit(100),
          admin.from('orq_chat_turns')
            .select('id,message_id,status,blocker_code,provider,created_at')
            .eq('owner_id', owner).eq('thread_id', threadId)
            .order('created_at', { ascending: false }).limit(100),
        ]);
        if (messages.error || turns.error) throw messages.error || turns.error;
        return reply({
          thread,
          messages: (messages.data || []).reverse(),
          turns: (turns.data || []).reverse(),
          inference: 'not_connected',
        });
      }

      const message = body.message;
      const requestId = body.client_request_id;
      if (typeof message !== 'string' || message.trim().length === 0 ||
          message.length > 12000 || typeof requestId !== 'string' || !UUID.test(requestId)) {
        return reply({ error: 'invalid_message' }, 400);
      }
      const { data: saved, error: saveError } = await admin.rpc('orq_chat_submit', {
        p_owner_id: owner,
        p_thread_id: threadId,
        p_request_id: requestId,
        p_content: message,
      });
      if (saveError) {
        const reason = saveError.message || '';
        if (reason.includes('ORQ_CHAT_RATE_LIMIT')) return reply({ error: 'rate_limited' }, 429);
        if (reason.includes('ORQ_CHAT_IDEMPOTENCY_CONFLICT')) return reply({ error: 'request_conflict' }, 409);
        if (reason.includes('ORQ_CHAT_THREAD_NOT_FOUND')) return reply({ error: 'thread_not_found' }, 404);
        throw saveError;
      }
      return reply({
        turn: saved?.[0] || null,
        inference: 'not_connected',
        message: 'Mensagem salva. Nenhum modelo de IA está conectado; nenhuma resposta foi gerada.',
      }, 202);
    }

    return reply({ error: 'unknown_action' }, 400);
  } catch (error) {
    // Never send database diagnostics, secrets, tokens or user prompts in error responses/logs.
    console.error('orq-chat internal error', reqId, error instanceof Error ? error.name : 'unknown');
    return reply({ error: 'internal_error', request_id: reqId }, 500);
  }
});
