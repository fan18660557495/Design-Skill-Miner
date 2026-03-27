from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from design_skill_miner.apply_skill import apply_draft_to_skill
from design_skill_miner.draft_skill import write_skill_draft
from design_skill_miner.pipeline import generate_insights
from design_skill_miner.publish_skill import publish_draft


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


if __name__ == "__main__":
    unittest.main()
