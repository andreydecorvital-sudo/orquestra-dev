"""Contract for the safe chat-first Orquestra UI.

A chat message is a persisted diagnostic task, not fabricated model output.
"""
import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
HTML=(ROOT/'web-live/missions.html').read_text(encoding='utf-8')
JS=(ROOT/'web-live/missions.js').read_text(encoding='utf-8')
CSS=(ROOT/'web-live/missions.css').read_text(encoding='utf-8')
ADVANCED=(ROOT/'web-live/index.html').read_text(encoding='utf-8')


class ChatFirstTests(unittest.TestCase):
    def test_page_and_navigation(self):
        self.assertIn('lang="pt-BR"',HTML)
        self.assertIn('<script src="/config.js"></script>',HTML)
        self.assertIn('src="/missions.js"',HTML)
        self.assertIn('href="/missions.css"',HTML)
        self.assertIn('href="/" class="advanced-link"',HTML)
        self.assertIn('href="/chat.html"',ADVANCED)
        self.assertIn('id="composer"',HTML)
        self.assertIn('id="messages"',HTML)
        self.assertIn('id="missionList"',HTML)
        self.assertIn('@media(max-width:800px)',CSS)

    def test_pop_culture_squad_is_presentation_not_provider_claim(self):
        for asset in ('/assets/lelouch.webp', '/assets/nagi.webp'):
            self.assertIn(asset, HTML)
            self.assertTrue((ROOT / 'web-live' / asset.lstrip('/')).exists(), asset)
        for label in ('LELOUCH', 'Nagi', 'CONHEÇA O ESQUADRÃO',
                      'Os personagens representam papéis', 'MISSION CONTROL'):
            self.assertIn(label.lower(), HTML.lower())
        self.assertIn('squad-grid', CSS)
        self.assertIn('prefers-reduced-motion:reduce', CSS)
        self.assertIn('data-seed-prompt', HTML)
        self.assertIn('document.querySelectorAll(\'[data-seed-prompt]\')', JS)
        self.assertIn('button.dataset.seedPrompt', JS)
        self.assertIn('OPERATION //', JS)
        self.assertNotIn("data-seed-prompt')?.click()", JS)

    def test_hermes_oauth_panel_does_not_fake_chatgpt_signin(self):
        self.assertIn('id="hermesOverlay"', HTML)
        self.assertIn('id="openHermesConnect"', HTML)
        self.assertIn('id="openHermesFromAuth"', HTML)
        self.assertIn('id="hermesRuntimeStatus"', HTML)
        self.assertIn('id="hermesCommand"', HTML)
        self.assertIn('https://railway.com/project/6f38abc3-4a78-4725-a55d-b2063019be11', HTML)
        self.assertIn('Hermes oficial já foi implantado', HTML)
        self.assertIn('id="refreshHermesStatus"', HTML)
        self.assertIn('id="copyHermesCommand"', HTML)
        self.assertIn('id="closeHermesConnect"', HTML)
        self.assertIn('hermes auth add openai-codex --type oauth', HTML)
        self.assertIn('O Hermes exibe um link oficial e um código temporário.', HTML)
        self.assertIn("showModal('hermesOverlay',true)", JS)
        self.assertIn("const hermesNodes=online.filter(", JS)
        self.assertIn("button", HTML)
        self.assertIn("navigator.clipboard.writeText(command.value)", JS)
        self.assertIn('Nenhum código foi gerado.', JS)
        self.assertNotIn('href="https://chatgpt.com/"', HTML)
        self.assertNotIn("window.open(", JS)
        self.assertNotIn('document.cookie', JS)
        self.assertNotIn('chrome.cookies', JS)
        self.assertNotIn('chatgpt_connected:true', JS)

    def test_every_dom_id_exists(self):
        ids=set(re.findall(r'id="([a-zA-Z][a-zA-Z0-9_-]*)"',HTML))
        lookups=set(re.findall(r"\$\('([a-zA-Z][a-zA-Z0-9_-]*)'\)",JS))
        self.assertFalse(lookups-ids,lookups-ids)

    def test_real_authenticated_queue(self):
        for token in (
            'state.client.auth.getUser()', 'state.client.auth.signInWithPassword',
            "state.client.from('orq_projects')", "state.client.from('orq_tasks')",
            "state.client.from('orq_nodes')", "kind:'diagnose'",
            ".insert({", "state.client.auth.signOut()", "task.output",
            "state.selected=data.id", "taskLabels[task.status]",
        ):
            self.assertIn(token,JS)
        self.assertIn("document.createElement(tag)",JS)
        self.assertIn("e.textContent=text",JS)

    def test_does_not_impersonate_multi_agent_service(self):
        self.assertIn("No simulated model response",JS)
        self.assertIn("Modelos de IA ainda não disponíveis",JS)
        self.assertIn("Não modifica sistemas",HTML)
        self.assertIn("O chat não simula resultados",HTML)
        self.assertIn("Executor não pareado",JS)
        self.assertNotIn("Deno.env",JS)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY",JS)
        self.assertNotIn("sb_secret_",JS)
        self.assertNotIn("localStorage",JS)
        self.assertIn("storage:sessionStorage",JS)

    def test_project_scoped_history_and_no_executors_by_default(self):
        self.assertIn("const ids=activeProjectIds()",JS)
        self.assertIn("state.tasks.filter(t=>ids.has(t.project_id))",JS)
        self.assertIn("t.id===state.selected&&ids.has(t.project_id)",JS)
        self.assertIn("state.projects.some(p=>p.id===state.projectId)",JS)
        self.assertIn("onlineNodes()",JS)

    def test_repeated_project_creation_reuses_canonical_record(self):
        self.assertIn("state.creatingProject||!state.user", JS)
        self.assertIn("state.creatingProject=true", JS)
        self.assertIn("btn.disabled=true", JS)
        self.assertIn("function visibleProjects()", JS)
        self.assertIn("function activeProjectIds()", JS)
        self.assertIn("const key=projectKey(p)", JS)
        self.assertIn("taskCount(p.id)>taskCount(prior.id)", JS)
        self.assertIn("Projeto já cadastrado. Abri o existente.", JS)
        self.assertIn("showModal('projectOverlay',false)", JS)
        self.assertIn("state.creatingProject=false", JS)
        self.assertIn("setInterval(()=>{if(!document.hidden)refresh()},30000)",JS)


if __name__=='__main__':
    unittest.main()
