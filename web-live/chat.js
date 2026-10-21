// Orquestra 2: owner-scoped conversation UI. No artificial AI replies.
const $ = id => document.getElementById(id);
const cfg = window.ORQ_CONFIG || {};
const TARGET = 'https://ydyzjpcmavqffdazteib.supabase.co';
const state = {
  client: null, user: null, threads: [], messages: [], turns: [], threadId: '',
  api: 'checking', busy: false, loading: false, pending: null, requestSerial: 0,
};
const BLOCKERS = {
  provider_not_connected: 'IA ainda não conectada. A mensagem está salva, mas não houve resposta.',
  executor_unavailable: 'O executor está indisponível. Não houve resposta de IA.',
  quota_exhausted: 'Limite do provedor atingido. Nenhuma nova execução foi iniciada.',
  approval_required: 'A operação depende de autorização específica.',
};
const ERROR_MESSAGES = {
  login_required: 'Entre novamente para continuar.',
  session_invalid: 'A sessão expirou. Entre novamente.',
  rate_limited: 'Limite de envios atingido. Tente mais tarde.',
  request_conflict: 'Este identificador já foi usado para outra mensagem.',
  thread_not_found: 'Esta conversa não está disponível na sua conta.',
  invalid_message: 'Confira o conteúdo antes de enviar.',
  invalid_thread_id: 'Identificador da conversa inválido.',
};
function elt(tag, cls, content) {
  const element = document.createElement(tag);
  if (cls) element.className = cls;
  if (content !== undefined) element.textContent = content; // text-only rendering prevents HTML injection
  return element;
}
function showMessage(message, id = 'notice') { $(id).textContent = message || ''; }
function dateLabel(timestamp) {
  const date = new Date(timestamp || 0);
  return Number.isFinite(date.valueOf()) ?
    date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '';
}
function showMenu(open) {
  $('sidebar').classList.toggle('open', open);
  $('menuShade').hidden = !open;
}
function renderAvailability() {
  const authenticated = Boolean(state.user);
  const live = authenticated && state.api === 'ready';
  const headline = {
    checking: 'Verificando serviço',
    ready: 'Histórico conectado',
    unavailable: 'Serviço pendente',
  }[state.api] || 'Entrar para continuar';
  $('chatStatus').textContent = headline;
  $('runtimeSummary').textContent = live ? 'Conversas privadas disponíveis' :
    state.api === 'checking' ? 'Verificando infraestrutura' :
      'Chat aguardando ativação';
  $('runtimeDot').classList.toggle('online', live);
  $('availabilityNotice').hidden = live;
  $('availabilityNotice').textContent =
    'A infraestrutura de conversas ainda não está ativa. Nenhuma IA será simulada. ' +
    'As missões existentes continuam disponíveis na aba Atividade.';
  $('send').disabled = !live || state.busy;
  $('retrySend').hidden = !state.pending || !live || state.pending.message !== $('prompt').value.trim();
  $('retrySend').disabled = state.busy;
  $('composerHint').textContent = !authenticated ? 'Entre para salvar conversas' :
    !live ? 'Envio temporariamente indisponível' :
      'Histórico privado · resposta de IA ainda não conectada';
  $('accountName').textContent = state.user?.email || 'Sessão privada';
  $('authOverlay').hidden = authenticated;
  $('signOut').hidden = !authenticated;
}
function renderThreads() {
  const list = $('threadList');
  list.replaceChildren();
  if (!state.user) {
    list.append(elt('p', 'muted', 'Entre para consultar seu histórico.'));
    return;
  }
  if (!state.threads.length) {
    list.append(elt('p', 'muted', 'Suas conversas aparecerão aqui.'));
    return;
  }
  for (const thread of state.threads) {
    const button = elt('button',
      state.threadId === thread.id ? 'selected' : '', thread.title || 'Conversa');
    button.type = 'button';
    button.title = thread.title || 'Conversa';
    if (state.threadId === thread.id) button.setAttribute('aria-current', 'true');
    button.addEventListener('click', () => { void openThread(thread.id); });
    list.append(button);
  }
}
function renderMessages() {
  const list = $('messageList');
  list.replaceChildren();
  $('welcome').hidden = state.messages.length > 0;
  const current = state.threads.find(x => x.id === state.threadId);
  $('threadTitle').textContent = current?.title || 'Nova conversa';
  const turnByMessage = new Map(state.turns.map(turn => [turn.message_id, turn]));
  for (const message of state.messages) {
    if (message.role !== 'user' && message.role !== 'assistant') continue;
    const div = elt('article', 'message ' + message.role);
    div.append(elt('div', 'speaker', message.role === 'user' ? 'Você' : 'Orquestra'));
    div.append(elt('div', 'body', message.content));
    const time = elt('time', '', dateLabel(message.created_at));
    if (message.created_at) time.dateTime = message.created_at;
    div.append(time);
    list.append(div);
    const turn = turnByMessage.get(message.id);
    if (turn && message.role === 'user') {
      const marker = elt('div', 'turn-status');
      marker.textContent = turn.status === 'blocked' ?
        (BLOCKERS[turn.blocker_code] || 'Mensagem registrada; execução bloqueada.') :
        turn.status === 'failed' ? 'Falha registrada. Confira o estado do provedor.' :
        turn.status === 'queued' || turn.status === 'running' ?
          'Processamento registrado; ainda não há resposta confirmada.' : '';
      if (marker.textContent) list.append(marker);
    }
  }
  const scroller = document.querySelector('.conversation');
  if (scroller && state.messages.length) scroller.scrollTop = scroller.scrollHeight;
}
function render() { renderAvailability(); renderThreads(); renderMessages(); }

async function apiCall(payload) {
  if (!state.client || !state.user) throw Error('login_required');
  const { data: sessionData, error: sessionError } = await state.client.auth.getSession();
  const token = sessionData?.session?.access_token;
  if (sessionError || !token) throw Error('session_invalid');
  const response = await fetch(cfg.supabaseUrl + '/functions/v1/orq-chat', {
    method: 'POST',
    headers: {
      'authorization': 'Bearer ' + token,
      'apikey': cfg.supabasePublishableKey,
      'content-type': 'application/json',
    },
    body: JSON.stringify(payload),
    cache: 'no-store',
  });
  let result;
  try { result = await response.json(); } catch { throw Error('invalid_server_reply'); }
  if (!response.ok) throw Error(result?.error || 'request_failed');
  return result;
}
async function loadThreads() {
  const result = await apiCall({ action: 'list_threads' });
  state.threads = Array.isArray(result.threads) ? result.threads : [];
  renderThreads();
  return state.threads;
}
async function loadThread(threadId) {
  const serial = ++state.requestSerial;
  const result = await apiCall({ action: 'read_thread', thread_id: threadId });
  if (serial !== state.requestSerial || threadId !== state.threadId) return;
  state.messages = Array.isArray(result.messages) ? result.messages : [];
  state.turns = Array.isArray(result.turns) ? result.turns : [];
  renderMessages();
}
async function openThread(threadId) {
  if (state.pending) {
    showMessage('Há um envio sem confirmação. Use “Tentar novamente” antes de trocar de conversa.');
    return;
  }
  if (state.api !== 'ready' || !state.threads.some(x => x.id === threadId)) return;
  state.threadId = threadId;
  state.messages = []; state.turns = [];
  $('welcome').hidden = false;
  render();
  showMenu(false);
  try { await loadThread(threadId); showMessage(''); }
  catch { showMessage('Não foi possível carregar esta conversa. Seu histórico não foi alterado.'); }
}
function resetConversation() {
  if (state.pending) {
    showMessage('Um envio ainda não foi confirmado. Use “Tentar novamente” antes de iniciar outra conversa.');
    return;
  }
  state.threadId = ''; state.messages = []; state.turns = [];
  ++state.requestSerial; render();
  $('prompt').focus(); showMenu(false);
  showMessage('');
}
async function probeService() {
  if (!state.client || !state.user || state.loading) return;
  state.loading = true; state.api = 'checking'; renderAvailability();
  try {
    await loadThreads(); // verifies Edge Function AND database, not just /health
    state.api = 'ready'; showMessage('');
    if (state.threadId && state.threads.some(x => x.id === state.threadId))
      await loadThread(state.threadId);
  } catch {
    state.api = 'unavailable';
    state.threads = []; state.messages = []; state.turns = [];
    showMessage('A API de conversas ou as tabelas privadas ainda não estão disponíveis. As missões antigas continuam preservadas.');
  } finally {
    state.loading = false;
    render();
  }
}
async function submit() {
  if (!state.user || state.api !== 'ready' || state.busy) return;
  const message = $('prompt').value.trim();
  if (!message || message.length > 12000) {
    showMessage('Escreva uma mensagem de até 12.000 caracteres.'); return;
  }
  if (state.pending && state.pending.message !== message) {
    showMessage('A mensagem anterior ainda não foi confirmada. Restaure o texto e tente novamente.');
    return;
  }
  if (!state.pending) {
    state.pending = {
      requestId: crypto.randomUUID(),
      threadId: state.threadId || crypto.randomUUID(),
      message,
    };
  }
  state.busy = true; renderAvailability();
  showMessage('Salvando sua mensagem…');
  try {
    const pending = state.pending;
    if (!state.threadId) {
      const result = await apiCall({
        action: 'create_thread',
        thread_id: pending.threadId,
        title: pending.message.split('\n')[0].trim().slice(0, 80) || 'Nova conversa',
      });
      state.threadId = result.thread.id;
    }
    await apiCall({
      action: 'send', thread_id: state.threadId,
      message: pending.message, client_request_id: pending.requestId,
    });
    state.pending = null;
    $('prompt').value = '';
    try {
      await loadThreads();
      await loadThread(state.threadId);
      showMessage('Mensagem armazenada. O modelo de IA ainda não está conectado.');
    } catch {
      showMessage('A mensagem foi salva, mas o histórico não pôde ser atualizado. Nenhum novo envio é necessário.');
    }
  } catch (error) {
    // Keep requestId + threadId for safe retry after an ambiguous network error.
    const reason = error instanceof Error ? error.message : 'request_failed';
    showMessage((ERROR_MESSAGES[reason] || 'Não foi possível confirmar o envio.') +
      ' O texto foi mantido para tentar novamente com o mesmo identificador.');
  } finally {
    state.busy = false;
    renderAvailability();
  }
}
async function connect() {
  if (!/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(cfg.supabaseUrl || '') ||
      cfg.supabaseUrl !== TARGET ||
      !/^sb_publishable_[A-Za-z0-9_-]{8,}$/.test(cfg.supabasePublishableKey || '')) {
    state.api = 'unavailable'; render();
    showMessage('Configuração pública de autenticação indisponível.');
    return;
  }
  try {
    const { createClient } = await import('https://esm.sh/@supabase/supabase-js@2.57.0');
    state.client = createClient(cfg.supabaseUrl, cfg.supabasePublishableKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true,
        storage: sessionStorage },
    });
    const { data } = await state.client.auth.getUser();
    state.user = data?.user || null;
    render();
    if (state.user) await probeService();
    state.client.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT') {
        state.user = null; state.threadId = ''; state.threads = [];
        state.messages = []; state.turns = []; state.pending = null;
        state.api = 'checking'; ++state.requestSerial; render();
      } else if (event === 'SIGNED_IN' && session?.user) {
        if (state.user?.id && state.user.id !== session.user.id) {
          state.threadId = ''; state.threads = [];
          state.messages = []; state.turns = []; state.pending = null;
          ++state.requestSerial;
        }
        state.user = session.user; render(); void probeService();
      }
    });
  } catch {
    state.api = 'unavailable'; render();
    showMessage('Não foi possível inicializar a autenticação. Atualize a página.');
  }
}
$('loginForm').addEventListener('submit', async event => {
  event.preventDefault();
  if (!state.client) return;
  const button = event.submitter;
  button.disabled = true;
  try {
    const values = new FormData(event.currentTarget);
    const { error } = await state.client.auth.signInWithPassword({
      email: String(values.get('email') || ''),
      password: String(values.get('password') || ''),
    });
    if (error) throw error;
    event.currentTarget.reset();
    showMessage('', 'loginNotice');
  } catch { showMessage('Não foi possível entrar. Confira o usuário e a senha.', 'loginNotice'); }
  finally { button.disabled = false; }
});
$('signOut').addEventListener('click', async () => {
  if (state.client) await state.client.auth.signOut();
});
$('newChat').addEventListener('click', resetConversation);
$('composer').addEventListener('submit', event => { event.preventDefault(); void submit(); });
$('retrySend').addEventListener('click', () => { void submit(); });
$('prompt').addEventListener('input', () => {
  $('retrySend').hidden = !state.pending || state.pending.message !== $('prompt').value.trim();
});
$('prompt').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault(); $('composer').requestSubmit();
  }
});
document.querySelectorAll('[data-prompt]').forEach(button => {
  button.addEventListener('click', () => {
    if (state.pending) return showMessage('Confirme o envio pendente antes de mudar a mensagem.');
    $('prompt').value = button.dataset.prompt || ''; $('prompt').focus();
  });
});
$('openMenu').addEventListener('click', () => showMenu(true));
$('closeMenu').addEventListener('click', () => showMenu(false));
$('menuShade').addEventListener('click', () => showMenu(false));
document.addEventListener('keydown', event => { if (event.key === 'Escape') showMenu(false); });
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && state.user && state.api !== 'ready') void probeService();
});
setInterval(() => {
  if (!document.hidden && state.user && state.api === 'ready' && !state.busy) {
    void (async () => {
      try {
        await loadThreads();
        if (state.threadId) await loadThread(state.threadId);
      } catch { showMessage('A atualização do histórico falhou; a conversa não foi alterada.'); }
    })();
  }
}, 30000);
render();
void connect();
