import unittest
from orchestration.router import route, as_dict

class RouterTests(unittest.TestCase):
    def test_gpt_implements_code(self):
        p=route(work_type='code', complexity='low')
        self.assertEqual(p.strategy,'gpt')
        self.assertEqual(p.lead,'gpt')
        self.assertIn('qa',[s.role for s in p.stages])
        self.assertNotIn('claude',[s.role for s in p.stages])

    def test_claude_owns_design_and_gpt_implements(self):
        p=route(work_type='design')
        self.assertEqual(p.lead,'claude')
        self.assertEqual([s.role for s in p.stages[:3]],['claude','gpt','qa'])

    def test_design_spec_only_skips_code(self):
        p=route(work_type='design',needs_implementation=False)
        self.assertNotIn('gpt',[s.role for s in p.stages])

    def test_joint_for_mixed(self):
        p=route(work_type='mixed')
        self.assertEqual(p.strategy,'joint')
        self.assertIn('claude',[s.role for s in p.stages])
        self.assertIn('gpt',[s.role for s in p.stages])
        self.assertIn('support',[s.role for s in p.stages])

    def test_independent_investigation(self):
        p=route(work_type='investigation')
        actions=[s.action for s in p.stages]
        self.assertTrue(any('independente' in a for a in actions))

    def test_high_risk_must_approve_first(self):
        p=route(work_type='code',risk='high')
        self.assertTrue(p.approval_before_execute)
        self.assertEqual(p.stages[0].role,'human')
        self.assertTrue(p.stages[0].approval_required)
        self.assertEqual(p.strategy,'joint')

    def test_manual_override_does_not_bypass_approval(self):
        p=route(work_type='code',risk='high',mode='gpt')
        self.assertEqual(p.strategy,'gpt')
        self.assertTrue(p.approval_before_execute)
        self.assertTrue(p.approval_before_merge)

    def test_missing_claude_blocks(self):
        p=route(work_type='design',claude_available=False)
        self.assertEqual(p.status,'blocked')
        self.assertIn('claude',p.reason)

    def test_missing_gpt_blocks_design_implementation(self):
        p=route(work_type='design',gpt_available=False)
        self.assertEqual(p.status,'blocked')

    def test_limited_budget_single_developer(self):
        p=route(work_type='code',complexity='medium',risk='low')
        self.assertNotIn('claude',[s.role for s in p.stages])

    def test_unknown_complexity_joint(self):
        p=route(work_type='code',complexity='unknown')
        self.assertEqual(p.strategy,'joint')

    def test_research_supports_without_gpt(self):
        p=route(work_type='research',claude_available=False,gpt_available=False)
        self.assertEqual(p.status,'planned')
        self.assertEqual(p.lead,'support')

    def test_no_live_execution(self):
        p=route(work_type='code')
        self.assertFalse(p.provider_runnable)
        self.assertTrue(p.stages[-1].approval_required)

    def test_serialize(self):
        p=as_dict(route(work_type='mixed'))
        self.assertIn('stages',p)
        self.assertEqual(p['strategy'],'joint')

    def test_invalid_config_rejected(self):
        for field,value in [('work_type','danger'),('complexity','super'),('risk','critical'),('mode','unlimited')]:
            with self.subTest(field=field):
                args={'work_type':'code'}
                args[field]=value
                with self.assertRaises(ValueError): route(**args)

if __name__=='__main__': unittest.main()
