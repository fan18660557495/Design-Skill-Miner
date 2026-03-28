from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from design_skill_miner.apply_skill import apply_draft_to_skill
from design_skill_miner.agent import AgentSettings, run_agent_mine
from design_skill_miner.draft_skill import write_skill_draft
from design_skill_miner.llm import LLMConfig, merge_batch_payload
from design_skill_miner.models import Evidence, Insight
from design_skill_miner.pipeline import generate_insights
from design_skill_miner.publish_skill import publish_draft
from design_skill_miner.web_support import api_agent_mine, api_get_agent_run, api_start_agent_run, api_test_llm_connection


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "sessions"


class PipelineTests(unittest.TestCase):
    def test_generate_insights_from_fixture(self) -> None:
        insights, stats = generate_insights(
            FIXTURE_ROOT,
            cwd_prefix="/Users/fan/code/minibuild/minibuild01",
            min_frequency=1,
        )
        self.assertEqual(stats["sessions_scanned"], 1)
        self.assertGreaterEqual(stats["candidate_messages"], 4)
        categories = {item.category for item in insights}
        self.assertIn("component-patterns", categories)
        self.assertIn("style-system", categories)
        self.assertIn("content-rules", categories)

    def test_write_and_apply_skill_draft(self) -> None:
        insights, _stats = generate_insights(
            FIXTURE_ROOT,
            cwd_prefix="/Users/fan/code/minibuild/minibuild01",
            min_frequency=1,
        )

        with tempfile.TemporaryDirectory() as draft_tmp, tempfile.TemporaryDirectory() as target_tmp:
            draft_dir = Path(draft_tmp)
            target_dir = Path(target_tmp)
            outputs = write_skill_draft(
                insights,
                draft_dir,
                skill_name="fixture-design-skill",
            )
            self.assertTrue(outputs["skill"].exists())
            self.assertTrue((draft_dir / "manifest.json").exists())

            target_skill = target_dir / "SKILL.md"
            target_skill.write_text(
                "---\nname: target-skill\ndescription: test\n---\n\n# Target Skill\n",
                encoding="utf-8",
            )
            result = apply_draft_to_skill(draft_dir, target_dir)
            self.assertTrue(Path(result["target_skill"]).exists())
            self.assertTrue(Path(result["target_manifest"]).exists())
            self.assertTrue((target_dir / "references" / "mined").exists())

            updated = target_skill.read_text(encoding="utf-8")
            self.assertIn("自动沉淀候选", updated)

            manifest = json.loads((draft_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["skill_name"], "fixture-design-skill")

    def test_publish_draft_to_staging(self) -> None:
        insights, _stats = generate_insights(
            FIXTURE_ROOT,
            cwd_prefix="/Users/fan/code/minibuild/minibuild01",
            min_frequency=1,
        )

        with tempfile.TemporaryDirectory() as draft_tmp, tempfile.TemporaryDirectory() as staging_tmp:
            draft_dir = Path(draft_tmp)
            staging_dir = Path(staging_tmp)
            write_skill_draft(
                insights,
                draft_dir,
                skill_name="fixture-design-skill",
            )

            result = publish_draft(draft_dir, staging_dir, publish_name="fixture-design-skill")
            self.assertTrue(Path(result["publish_dir"]).exists())
            self.assertTrue((Path(result["publish_dir"]) / "SKILL.md").exists())
            self.assertTrue((Path(result["publish_dir"]) / "published.json").exists())

    def test_agent_workflow_writes_review_and_draft(self) -> None:
        with tempfile.TemporaryDirectory() as out_tmp:
            result = run_agent_mine(
                FIXTURE_ROOT,
                cwd_prefix="/Users/fan/code/minibuild/minibuild01",
                min_frequency=1,
                out_dir=Path(out_tmp),
                skill_name="fixture-agent-skill",
                agent_settings=AgentSettings(review_min_score=0.5),
                llm_config=LLMConfig(enabled=False),
            )

            self.assertTrue((Path(out_tmp) / "reports" / "insights.json").exists())
            self.assertTrue((Path(out_tmp) / "reports" / "review.json").exists())
            self.assertTrue((Path(out_tmp) / "draft" / "SKILL.md").exists())
            self.assertTrue((Path(out_tmp) / "agent-run.json").exists())
            self.assertGreaterEqual(result.review.score, 0.0)
            self.assertEqual(result.llm_status, "disabled")

    def test_web_agent_api_returns_review_payload(self) -> None:
        with tempfile.TemporaryDirectory() as out_tmp:
            payload = api_agent_mine(
                FIXTURE_ROOT,
                cwd_prefix="/Users/fan/code/minibuild/minibuild01",
                min_frequency=1,
                out_dir=Path(out_tmp),
                skill_name="fixture-web-agent-skill",
            )

            self.assertIn("review", payload)
            self.assertIn("files", payload)
            self.assertTrue((Path(out_tmp) / "agent-run.json").exists())
            self.assertIsInstance(payload["review"]["score"], float)
            self.assertGreaterEqual(len(payload["files"]), 1)

    def test_background_agent_run_completes(self) -> None:
        with tempfile.TemporaryDirectory() as out_tmp:
            job = api_start_agent_run(
                FIXTURE_ROOT,
                cwd_prefix="/Users/fan/code/minibuild/minibuild01",
                min_frequency=1,
                out_dir=Path(out_tmp),
                skill_name="fixture-background-agent-skill",
                llm_timeout_seconds=5,
                run_target="draft",
            )

            final = None
            for _ in range(40):
                current = api_get_agent_run(job["run_id"])
                if current["status"] in {"completed", "failed"}:
                    final = current
                    break
                time.sleep(0.05)

            self.assertIsNotNone(final)
            self.assertEqual(final["status"], "completed")
            self.assertIn("result", final)
            self.assertTrue((Path(out_tmp) / "agent-run.json").exists())

    def test_merge_batch_payload_preserves_missing_items(self) -> None:
        original = [
            Insight(
                title="样式系统：颜色",
                summary="old",
                category="style-system",
                granularity="token",
                frequency=2,
                decision="candidate_for_skill",
                scope="project_specific_skill",
                stability="stable",
                confidence=0.8,
                why_it_repeats=["old why"],
                normalized_rules=["old rule"],
                evidence=[Evidence(source="a")],
            ),
            Insight(
                title="组件模式：按钮",
                summary="old2",
                category="component-patterns",
                granularity="component",
                frequency=2,
                decision="candidate_for_skill",
                scope="project_specific_skill",
                stability="stable",
                confidence=0.8,
                why_it_repeats=["old why2"],
                normalized_rules=["old rule2"],
                evidence=[Evidence(source="b")],
            ),
        ]

        merged, failures = merge_batch_payload(
            original,
            {
                "insights": [
                    {
                        "title": "样式系统：颜色",
                        "summary": "new",
                        "why_it_repeats": ["new why"],
                        "normalized_rules": ["new rule"],
                    }
                ]
            },
        )

        self.assertEqual(failures, 1)
        self.assertEqual(merged[0].summary, "new")
        self.assertEqual(merged[1].summary, "old2")

    def test_llm_test_api_reports_invalid_config(self) -> None:
        payload = api_test_llm_connection(
            llm_model=None,
            llm_base_url="https://api.moonshot.ai/v1",
        )
        self.assertFalse(payload["ok"])
        self.assertIn("not ready", payload["error"])


if __name__ == "__main__":
    unittest.main()
