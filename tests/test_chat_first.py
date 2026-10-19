"""Contract for the safe chat-first Orquestra UI.

A chat message is a persisted diagnostic task, not fabricated model output.
"""
import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
HTML=(ROOT/'web-live/chat.html').read_text(encoding='utf-8')
JS=(ROOT/'web-live/chat.js').read_text(encoding='utf-8')
CSS=(ROOT/'web-live/chat.css').read_text(encoding='utf-8')
ADVANCED=(ROOT/'web-live/index.html').read_text(encoding='utf-8')


class ChatFirstTests(unittest.TestCase):
    def test_page_and_navigation(self):
        self.assertIn('lang="pt-BR"',HTML)
        self.assertIn('<script src="/config.js"></script>',HTML)
        self.assertIn('src="/chat.js"',HTML)
        self.assertIn('href="/chat.css"',HTML)
        self.assertIn('href="/" class="advanced-link"',HTML)
        self.assertIn('href="/chat.html"',ADVANCED)
        self.assertIn('id="composer"',HTML)
        self.assertIn('id="messages"',HTML)
        self.assertIn('id="missionList"',HTML)
        self.assertIn('@media(max-width:800px)',CSS)

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
        self.assertIn("t.project_id===state.projectId",JS)
        self.assertIn("task.project_id===state.projectId",JS)
        self.assertIn("state.projects.some(p=>p.id===state.projectId)",JS)
        self.assertIn("onlineNodes()",JS)
        self.assertIn("setInterval(()=>{if(!document.hidden)refresh()},30000)",JS)


if __name__=='__main__':
    unittest.main()
