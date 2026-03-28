# Architecture

## What This Project Does

`design-skill-miner` turns repeated design discussions from local session exports into editable skill drafts.

It is not a chat summarizer. It is a local agent workflow that:

1. reads local session exports
2. attributes sessions to a project
3. filters design-relevant messages
4. clusters repeated topics
5. distills them into candidate rules
6. reviews signal quality
7. optionally uses an LLM to polish rule wording
8. writes draft skill files
9. optionally publishes the draft into a staging directory

## End-to-End Flow

```text
sessions -> ingest -> attribution -> filter -> cluster -> distill
         -> review -> optional llm polish -> draft files -> publish
```

## Main Layers

### 1. Core mining pipeline

These modules produce deterministic insights from local sessions:

- `ingest.py`
- `attribution.py`
- `filter.py`
- `cluster.py`
- `distill.py`
- `pipeline.py`

### 2. Agent workflow

These modules add execution planning, review, and optional LLM enhancement:

- `agent.py`
- `review.py`
- `llm.py`

### 3. Draft and publish

These modules transform insights into skill-shaped outputs:

- `report.py`
- `draft_skill.py`
- `apply_skill.py`
- `publish_skill.py`

### 4. Interfaces

These modules expose the workflow to users:

- `cli.py`
- `web.py`
- `web_support.py`
- `run_jobs.py`
- `web/`

## Repository Structure

```text
design-skill-miner/
├── src/design_skill_miner/
│   ├── agent.py
│   ├── apply_skill.py
│   ├── attribution.py
│   ├── cli.py
│   ├── cluster.py
│   ├── config.py
│   ├── distill.py
│   ├── draft_skill.py
│   ├── filter.py
│   ├── indexer.py
│   ├── ingest.py
│   ├── llm.py
│   ├── models.py
│   ├── pipeline.py
│   ├── publish_skill.py
│   ├── report.py
│   ├── review.py
│   ├── run_jobs.py
│   ├── web.py
│   └── web_support.py
├── web/
├── tests/
├── docs/
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
└── CHANGELOG.md
```

## Outputs

Typical agent output:

```text
agent-out/
├── agent-run.json
├── draft/
│   ├── SKILL.md
│   ├── manifest.json
│   └── references/
└── reports/
    ├── insights.json
    ├── insights.md
    └── review.json
```

## Configuration Model

The project separates public and local configuration:

- commit `.design-skill-miner.toml.example`
- keep `.design-skill-miner.toml` local only
- keep real secrets in environment variables

This is important for open-source safety and reproducible local setup.
