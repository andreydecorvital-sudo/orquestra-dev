"""Private Origin integration must fail closed on identity, path, token or state."""
import base64
import json
import urllib.error
import unittest

from orchestration.origin_knowledge import (
    ALLOWED_DOCUMENTS, ORIGIN_REPOSITORY, OriginReadGrant,
    OriginUnavailable, read_origin_document, load_origin_context,
    recommended_origin_paths,
    propose_origin_learning,
)


def grant():
    return OriginReadGrant(
        owner_id="owner-one", repository=ORIGIN_REPOSITORY,
        allowed_paths=frozenset(ALLOWED_DOCUMENTS),
    )


def gh_response(path="START_HERE.md", content="# Origin read only"):
    return json.dumps({
        "type": "file", "path": path, "encoding": "base64",
        "sha": "a" * 40,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
    }).encode("utf-8")


class OriginKnowledgeTests(unittest.TestCase):
    def read(self, **kwargs):
        args = {
            "path": "START_HERE.md",
            "owner_id": "owner-one",
            "grant": grant(),
            "github_token": "github_pat_test_token_only",
            "fetch": lambda *_: gh_response(),
        }
        args.update(kwargs)
        return read_origin_document(**args)

    def test_read_curated_document_with_sha_and_provenance(self):
        captured = []
        def fetch(req, timeout):
            captured.append((req, timeout))
            return gh_response()
        doc = self.read(fetch=fetch)
        self.assertEqual(doc.blob_sha, "a" * 40)
        self.assertEqual(doc.repository, ORIGIN_REPOSITORY)
        self.assertIn("# Origin", doc.content)
        self.assertIn("blob/main/START_HERE.md", doc.source_url)
        self.assertEqual(len(captured), 1)
        self.assertTrue(captured[0][0].full_url.startswith("https://api.github.com/repos/"))
        self.assertEqual(captured[0][0].get_method(), "GET")

    def test_wrong_owner_never_calls_network(self):
        with self.assertRaises(OriginUnavailable):
            self.read(owner_id="some-other-user",
                      fetch=lambda *_: self.fail("network should not run"))

    def test_no_implicit_private_repository_access(self):
        with self.assertRaises(OriginUnavailable):
            self.read(github_token="",
                      fetch=lambda *_: self.fail("network should not run"))

    def test_public_or_other_repo_cannot_substitute_origin(self):
        denied = OriginReadGrant(owner_id="owner-one",
                                 repository="other/other",
                                 allowed_paths=frozenset(ALLOWED_DOCUMENTS))
        with self.assertRaises(OriginUnavailable):
            self.read(grant=denied,
                      fetch=lambda *_: self.fail("network should not run"))

    def test_grant_can_restrict_individual_files(self):
        denied = OriginReadGrant(owner_id="owner-one",
                                 repository=ORIGIN_REPOSITORY,
                                 allowed_paths=frozenset({"AGENTS.md"}))
        with self.assertRaises(OriginUnavailable):
            self.read(grant=denied,
                      fetch=lambda *_: self.fail("network should not run"))

    def test_block_private_source_or_arbitrary_path(self):
        for path in (".env", "src/discovery.mjs", "../README.md",
                     "https://attacker.example", "docs/../../secrets"):
            with self.subTest(path=path), self.assertRaises(OriginUnavailable):
                self.read(path=path, fetch=lambda *_: self.fail("network should not run"))

    def test_failed_github_access_is_not_treated_as_empty_knowledge(self):
        def denied(*_):
            raise urllib.error.HTTPError("https://api.github.com", 403,
                                         "Forbidden", None, None)
        with self.assertRaisesRegex(OriginUnavailable, "inacessível"):
            self.read(fetch=denied)

    def test_refuse_malformed_or_oversized_payload(self):
        for payload in (
            b"{}",
            gh_response(path="OTHER.md"),
            gh_response(content="x" * 65537),
            b"x" * 100001,
            json.dumps({"type":"file","path":"START_HERE.md",
                        "sha":"not-a-sha","encoding":"base64",
                        "content":"ZW5n"}).encode(),
        ):
            with self.subTest(size=len(payload)), self.assertRaises(OriginUnavailable):
                self.read(fetch=lambda *_, p=payload: p)

    def test_role_references_are_not_assumed_loaded(self):
        roles = ("assistant", "engineering", "research", "marketing",
                 "commerce", "design", "review")
        for role in roles:
            with self.subTest(role=role):
                self.assertTrue(recommended_origin_paths(role))
                self.assertTrue(set(recommended_origin_paths(role)) <= ALLOWED_DOCUMENTS)
        self.assertEqual(recommended_origin_paths("unknown"), ())

    def test_bounded_context_reads_rules_first_and_uses_same_owner_grant(self):
        called = []
        def fetch(req, timeout):
            path = req.full_url.split("/contents/")[1].split("?")[0]
            called.append(path)
            return gh_response(path=path, content="# verified source")
        docs = load_origin_context(
            role="engineering", owner_id="owner-one", grant=grant(),
            github_token="github_pat_test_token_only", fetch=fetch)
        self.assertEqual(called[0:2], ["START_HERE.md", "AGENTS.md"])
        self.assertIn("skills/evidence-driven-loop/SKILL.md", called)
        self.assertEqual(len(docs), len(called))
        self.assertTrue(all(d.blob_sha == "a" * 40 for d in docs))

    def test_context_load_rejects_unknown_role_limit_and_other_owner(self):
        def no_network(*_):
            self.fail("network must not run")
        base = dict(owner_id="owner-one", grant=grant(),
                    github_token="github_pat_test_token_only", fetch=no_network)
        with self.assertRaises(OriginUnavailable):
            load_origin_context(role="unknown", **base)
        with self.assertRaises(OriginUnavailable):
            load_origin_context(role="engineering", max_documents=0, **base)
        with self.assertRaises(OriginUnavailable):
            load_origin_context(role="engineering", max_documents=100, **base)
        with self.assertRaises(OriginUnavailable):
            load_origin_context(role="engineering", owner_id="other-user",
                                grant=grant(), github_token="github_pat_test_token_only",
                                fetch=no_network)

    def test_learning_is_proposal_not_automatic_repo_write(self):
        with self.assertRaises(ValueError):
            propose_origin_learning(title="Broken retry", learning="Patch should be checked",
                                    evidence=("test.py",), verified=False)
        item = propose_origin_learning(
            title="Avoid replay after uncertain results",
            learning="Reconcile an unknown external result before retrying any operation.",
            evidence=("tests/test_retry.py:12", "PR #16"),
            verified=True,
        )
        self.assertEqual(item.status, "proposed")
        self.assertFalse(item.write_authorized)
        self.assertEqual(item.target, "docs/LEARNING_LOG.md")


if __name__ == "__main__":
    unittest.main()
