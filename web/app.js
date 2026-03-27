const STEPS = ["project", "insights", "draft", "publish"];

const state = {
  currentStep: "project",
  selectedProject: "",
  currentProjectInfo: null,
  insights: [],
  insightsStats: null,
  draftFiles: [],
  draftDir: "",
  activeDraftFile: null,
  draftMode: "read",
  draftStale: false,
  publishRoot: "",
  publishedInfo: null,
  publishStale: false,
};

const els = {
  flowSteps: document.getElementById("flowSteps"),
  statusBanner: document.getElementById("statusBanner"),
  cwdPrefixInput: document.getElementById("cwdPrefixInput"),
  chooseProjectBtn: document.getElementById("chooseProjectBtn"),
  projectSummary: document.getElementById("projectSummary"),
  projectMeta: document.getElementById("projectMeta"),
  projectNextBtn: document.getElementById("projectNextBtn"),
  insightsStage: document.getElementById("insightsStage"),
  insightsSummary: document.getElementById("insightsSummary"),
  insightsList: document.getElementById("insightsList"),
  insightsBackBtn: document.getElementById("insightsBackBtn"),
  insightsRefreshBtn: document.getElementById("insightsRefreshBtn"),
  insightsNextBtn: document.getElementById("insightsNextBtn"),
  draftSummary: document.getElementById("draftSummary"),
  draftFileList: document.getElementById("draftFileList"),
  draftContent: document.getElementById("draftContent"),
  draftEditor: document.getElementById("draftEditor"),
  draftActiveFileName: document.getElementById("draftActiveFileName"),
  draftActiveFilePath: document.getElementById("draftActiveFilePath"),
  draftReadModeBtn: document.getElementById("draftReadModeBtn"),
  draftEditModeBtn: document.getElementById("draftEditModeBtn"),
  saveDraftFileBtn: document.getElementById("saveDraftFileBtn"),
  draftBackBtn: document.getElementById("draftBackBtn"),
  draftRefreshBtn: document.getElementById("draftRefreshBtn"),
  draftNextBtn: document.getElementById("draftNextBtn"),
  publishSummary: document.getElementById("publishSummary"),
  publishRootValue: document.getElementById("publishRootValue"),
  publishNameValue: document.getElementById("publishNameValue"),
  publishBackBtn: document.getElementById("publishBackBtn"),
  changePublishRootBtn: document.getElementById("changePublishRootBtn"),
  publishNowBtn: document.getElementById("publishNowBtn"),
  sessionsRootInput: document.getElementById("sessionsRootInput"),
  minFrequencyInput: document.getElementById("minFrequencyInput"),
  skillNameInput: document.getElementById("skillNameInput"),
  draftOutDirInput: document.getElementById("draftOutDirInput"),
  publishRootInput: document.getElementById("publishRootInput"),
  projectStage: document.getElementById("projectStage"),
  draftStage: document.getElementById("draftStage"),
  publishStage: document.getElementById("publishStage"),
};

function setStatus(message, tone = "") {
  if (!message) {
    els.statusBanner.textContent = "";
    els.statusBanner.className = "status-line is-hidden";
    return;
  }
  els.statusBanner.textContent = message;
  els.statusBanner.className = `status-line${tone ? ` is-${tone}` : ""}`;
}

function getSessionsRoot() {
  return els.sessionsRootInput.value.trim();
}

function getCwdPrefix() {
  return els.cwdPrefixInput.value.trim() || state.selectedProject || "";
}

function getMinFrequency() {
  const value = Number.parseInt(els.minFrequencyInput.value, 10);
  return Number.isFinite(value) && value > 0 ? value : 2;
}

function getSkillName() {
  return els.skillNameInput.value.trim() || "design-skill-draft";
}

function getDraftOutDir() {
  return els.draftOutDirInput.value.trim();
}

function getPublishRoot() {
  return els.publishRootInput.value.trim() || state.publishRoot || "";
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
}

async function pickDirectory(title, startPath = "") {
  return requestJson("/api/fs/pick-directory", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title,
      start_path: startPath || undefined,
    }),
  });
}

function slugifyProject(pathValue) {
  const basename = pathValue
    .trim()
    .split("/")
    .filter(Boolean)
    .pop() || "design-skill";
  return basename
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/_/g, "-")
    .replace(/[^a-z0-9\-一-龥]/g, "");
}

function applyDerivedDefaults(projectPath) {
  const slug = slugifyProject(projectPath) || "design-skill";
  els.skillNameInput.value = `${slug}-design-skill`;
  els.draftOutDirInput.value = `/tmp/design-skill-miner-drafts/${slug}`;
}

function setCurrentStep(step) {
  state.currentStep = step;
  renderApp();
}

function resetForProjectChange() {
  state.currentProjectInfo = null;
  state.insights = [];
  state.insightsStats = null;
  state.draftFiles = [];
  state.draftDir = "";
  state.activeDraftFile = null;
  state.draftMode = "read";
  state.draftStale = false;
  state.publishedInfo = null;
  state.publishStale = false;
}

function markDraftStale() {
  if (state.draftFiles.length) {
    state.draftStale = true;
  }
  if (state.publishedInfo) {
    state.publishStale = true;
  }
}

function clearPublishState() {
  state.publishedInfo = null;
  state.publishStale = false;
}

function getStepState(step) {
  if (step === "project") {
    return state.currentStep === "project" ? "current" : state.selectedProject ? "complete" : "pending";
  }
  if (step === "insights") {
    if (!state.selectedProject) return "pending";
    if (state.currentStep === "insights") return "current";
    return state.insights.length ? "complete" : "pending";
  }
  if (step === "draft") {
    if (!state.insights.length) return "pending";
    if (state.currentStep === "draft") return "current";
    if (!state.draftFiles.length) return "pending";
    return state.draftStale ? "stale" : "complete";
  }
  if (!state.draftFiles.length) return "pending";
  if (state.currentStep === "publish") return "current";
  if (!state.publishedInfo) return "pending";
  return state.publishStale ? "stale" : "complete";
}

function getStepIcon(stepState) {
  return {
    complete: "✓",
    current: "●",
    stale: "!",
    pending: "○",
  }[stepState] || "○";
}

function getStepSummary(step) {
  if (step === "project") {
    return state.currentProjectInfo?.project_id || state.selectedProject || "选择项目目录";
  }
  if (step === "insights") {
    return state.insights.length ? `${state.insights.length} 条规则` : "先生成规则";
  }
  if (step === "draft") {
    if (!state.draftFiles.length) return "先生成草稿";
    return state.draftStale ? `${state.draftFiles.length} 个文件 · 需更新` : `${state.draftFiles.length} 个文件`;
  }
  if (state.publishStale) return "需重新发布";
  if (state.publishedInfo) return "已发布到暂存区";
  return getPublishRoot() ? "暂存目录已设置" : "先设置暂存目录";
}

function renderFlowSteps() {
  const labels = {
    project: "选择项目",
    insights: "规则洞察",
    draft: "Skill 草稿",
    publish: "发布到暂存区",
  };

  els.flowSteps.innerHTML = STEPS.map((step) => {
    const stepState = getStepState(step);
    const disabled = stepState === "pending" && step !== "project";
    return `
      <button
        class="step-card is-${stepState} ${disabled ? "is-disabled" : ""}"
        type="button"
        data-action="goto-step"
        data-step="${step}"
        ${disabled ? "disabled" : ""}
      >
        <div class="step-card-row">
          <span class="step-icon">${getStepIcon(stepState)}</span>
          <div class="step-text">
            <span class="step-title">${labels[step]}</span>
            <span class="step-summary">${escapeHtml(getStepSummary(step))}</span>
          </div>
        </div>
      </button>
    `;
  }).join("");
}

function renderStages() {
  document.querySelectorAll(".stage-panel").forEach((panel) => panel.classList.remove("is-active"));
  if (state.currentStep === "project") els.projectStage.classList.add("is-active");
  if (state.currentStep === "insights") els.insightsStage.classList.add("is-active");
  if (state.currentStep === "draft") els.draftStage.classList.add("is-active");
  if (state.currentStep === "publish") els.publishStage.classList.add("is-active");
}

function renderProjectStage() {
  els.cwdPrefixInput.value = state.selectedProject || "";
  els.projectMeta.textContent = "";

  if (!state.selectedProject) {
    els.projectSummary.className = "summary-card is-hidden";
    els.projectSummary.innerHTML = "";
    els.projectNextBtn.disabled = true;
    return;
  }

  const info = state.currentProjectInfo;
  els.projectSummary.className = "summary-card";
  els.projectSummary.innerHTML = `
    <strong>${escapeHtml(info?.project_id || slugifyProject(state.selectedProject))}</strong>
    <span class="muted">${escapeHtml(String(info?.session_count || 0))} 个 session</span>
  `;
  els.projectNextBtn.disabled = false;
}

function renderInsightsStage() {
  if (!state.selectedProject) {
    els.insightsSummary.className = "summary-card is-hidden";
    els.insightsSummary.innerHTML = "";
    els.insightsList.innerHTML = "";
    els.insightsNextBtn.disabled = true;
    els.insightsRefreshBtn.disabled = true;
    return;
  }

  if (!state.insights.length) {
    els.insightsSummary.className = "summary-card is-hidden";
    els.insightsSummary.innerHTML = "";
    els.insightsList.innerHTML = "";
    els.insightsNextBtn.disabled = true;
    els.insightsRefreshBtn.disabled = false;
    return;
  }

  const stats = state.insightsStats || {};
  const groupedInsights = groupInsightsByCategory(state.insights);
  const categoryCount = groupedInsights.length;
  els.insightsSummary.className = "summary-card";
  els.insightsSummary.innerHTML = `
    <strong>${escapeHtml(String(stats.insights_written || state.insights.length))} 条规则</strong>
    <span class="muted">${categoryCount} 个分类 · ${escapeHtml(String(stats.sessions_scanned || 0))} 个 session</span>
  `;
  els.insightsList.innerHTML = groupedInsights.map((group) => renderInsightGroup(group)).join("");
  els.insightsNextBtn.disabled = false;
  els.insightsRefreshBtn.disabled = false;
}

function groupInsightsByCategory(insights) {
  const groups = new Map();
  insights.forEach((insight) => {
    const category = insight.category || "unknown";
    if (!groups.has(category)) {
      groups.set(category, []);
    }
    groups.get(category).push(insight);
  });

  return Array.from(groups.entries()).map(([category, items]) => ({
    category,
    label: categoryLabel(category),
    items,
  }));
}

function renderInsightGroup(group) {
  return `
    <section class="insight-group">
      <header class="insight-group-head">
        <h3>${escapeHtml(group.label)}</h3>
        <span class="tag">${escapeHtml(String(group.items.length))} 条</span>
      </header>
      <div class="insight-group-list">
        ${group.items.map((insight) => renderInsightCard(insight)).join("")}
      </div>
    </section>
  `;
}

function renderInsightCard(insight) {
  const rules = (insight.normalized_rules || insight.proposed_rules || [])
    .map((rule) => `<div class="insight-rule">${escapeHtml(rule)}</div>`)
    .join("");
  const evidence = (insight.evidence || [])
    .map((item) => `<li><strong>${escapeHtml(item.date || "unknown-date")}</strong> · ${escapeHtml(item.quote_summary || "")}</li>`)
    .join("");

  return `
    <article class="insight-card">
      <div class="insight-topline">
        <h3>${escapeHtml(insight.title || "未命名规则")}</h3>
        <div class="insight-tags">
          <span class="tag">${escapeHtml(String(insight.frequency || 0))} 次</span>
        </div>
      </div>
      <p class="insight-summary">${escapeHtml(insight.summary || "无摘要")}</p>
      <div class="insight-rules">${rules || '<div class="insight-rule">暂时没有整理后的规则。</div>'}</div>
      <div class="insight-footer">
        <span class="subtle-meta">${escapeHtml(stabilityLabel(insight.stability || "unknown"))} · ${escapeHtml(scopeLabel(insight.scope || "unknown"))}</span>
        <details>
          <summary>证据（${escapeHtml(String((insight.evidence || []).length))}）</summary>
          <ul class="evidence-list">${evidence || "<li>暂无证据。</li>"}</ul>
        </details>
      </div>
    </article>
  `;
}

function renderDraftStage() {
  if (!state.insights.length) {
    els.draftSummary.className = "summary-card is-hidden";
    els.draftSummary.innerHTML = "";
    els.draftFileList.className = "draft-file-list is-hidden";
    els.draftFileList.innerHTML = "";
    els.draftContent.textContent = "";
    els.draftEditor.value = "";
    els.draftActiveFileName.textContent = "";
    els.draftActiveFilePath.textContent = "";
    els.draftNextBtn.disabled = true;
    els.draftRefreshBtn.disabled = true;
    applyDraftMode();
    return;
  }

  if (!state.draftFiles.length) {
    els.draftSummary.className = "summary-card is-hidden";
    els.draftSummary.innerHTML = "";
    els.draftFileList.className = "draft-file-list is-hidden";
    els.draftFileList.innerHTML = "";
    els.draftContent.textContent = "";
    els.draftEditor.value = "";
    els.draftActiveFileName.textContent = "";
    els.draftActiveFilePath.textContent = "";
    els.draftNextBtn.disabled = true;
    els.draftRefreshBtn.disabled = false;
    applyDraftMode();
    return;
  }

  if (!state.activeDraftFile || !state.draftFiles.some((file) => file.path === state.activeDraftFile.path)) {
    state.activeDraftFile = state.draftFiles[0];
  }

  els.draftSummary.className = `summary-card${state.draftStale ? " is-warning" : ""}`;
  els.draftSummary.innerHTML = state.draftStale
    ? "草稿需更新"
    : `${escapeHtml(String(state.draftFiles.length))} 个文件`;

  els.draftFileList.className = "draft-file-list";
  els.draftFileList.innerHTML = state.draftFiles.map((file) => {
    const active = state.activeDraftFile && file.path === state.activeDraftFile.path;
    return `
      <button class="draft-file-button ${active ? "is-active" : ""}" data-action="open-draft-file" data-path="${escapeHtml(file.path)}" type="button">
        <strong>${escapeHtml(readableFileName(file))}</strong>
        <span class="muted">${escapeHtml(file.relative_path)}</span>
      </button>
    `;
  }).join("");

  els.draftActiveFileName.textContent = readableFileName(state.activeDraftFile);
  els.draftActiveFilePath.textContent = state.activeDraftFile.relative_path;
  els.draftContent.innerHTML = renderDocument(state.activeDraftFile);
  els.draftEditor.value = state.activeDraftFile.content || "";
  els.draftNextBtn.disabled = false;
  els.draftRefreshBtn.disabled = false;
  applyDraftMode();
}

function renderPublishStage() {
  els.publishRootValue.textContent = getPublishRoot() || "首次发布时选择";
  els.publishNameValue.textContent = getSkillName();

  if (!state.draftFiles.length) {
    els.publishSummary.className = "summary-card is-hidden";
    els.publishSummary.innerHTML = "";
    els.publishNowBtn.disabled = true;
    return;
  }

  if (!state.publishedInfo) {
    els.publishSummary.className = "summary-card is-hidden";
    els.publishSummary.innerHTML = "";
  } else if (state.publishStale) {
    els.publishSummary.className = "summary-card is-warning";
    els.publishSummary.innerHTML = `需重新发布`;
  } else {
    els.publishSummary.className = "summary-card";
    els.publishSummary.innerHTML = `
      <strong>已发布</strong>
      <span class="muted">${escapeHtml(state.publishedInfo.publish_dir)}</span>
    `;
  }

  els.publishNowBtn.disabled = false;
}

function renderDocument(file) {
  if (!file) {
    return "请先生成 Skill 草稿。";
  }
  if (!file.name.endsWith(".md")) {
    return `<pre>${escapeHtml(file.content || "")}</pre>`;
  }
  return renderMarkdownDocument(file.content || "");
}

function renderMarkdownDocument(content) {
  const lines = stripFrontmatter(content).split("\n");
  const root = splitSections(lines);
  const blocks = [];

  if (root.title) {
    blocks.push(`<h1>${renderInline(root.title)}</h1>`);
  }
  if (root.paragraphs.length) {
    blocks.push(root.paragraphs.map((paragraph) => `<p class="doc-intro">${renderInline(paragraph)}</p>`).join(""));
  }

  root.sections.forEach((section) => {
    if (matchesSection(section.title, ["规则总览", "Consolidated Rules"])) {
      blocks.push(renderRulesOverview(section));
      return;
    }
    if (matchesSection(section.title, ["候选条目"])) {
      blocks.push(renderTopicEntries(section));
      return;
    }
    if (matchesSection(section.title, ["证据附录", "Evidence Appendix"])) {
      blocks.push(renderEvidenceSection(section));
      return;
    }
    blocks.push(renderGenericSection(section));
  });

  return blocks.join("");
}

function stripFrontmatter(content) {
  if (!content.startsWith("---")) return content;
  const end = content.indexOf("\n---", 3);
  if (end === -1) return content;
  return content.slice(end + 4).trim();
}

function splitSections(lines) {
  let i = 0;
  let title = "";
  const paragraphs = [];
  const sections = [];

  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) {
      i += 1;
      continue;
    }
    if (line.startsWith("# ")) {
      title = line.slice(2);
      i += 1;
      continue;
    }
    if (line.startsWith("## ")) break;
    const result = collectParagraphs(lines, i);
    paragraphs.push(...result.paragraphs);
    i = result.nextIndex;
  }

  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) {
      i += 1;
      continue;
    }
    if (!line.startsWith("## ")) {
      i += 1;
      continue;
    }
    const sectionTitle = line.slice(3);
    i += 1;
    const sectionLines = [];
    while (i < lines.length) {
      const current = lines[i];
      if (current.trim().startsWith("## ")) break;
      sectionLines.push(current);
      i += 1;
    }
    sections.push({ title: sectionTitle, lines: sectionLines });
  }

  return { title, paragraphs, sections };
}

function renderRulesOverview(section) {
  const items = collectBulletItemsFromLines(section.lines);
  return `<section class="doc-section"><h2>${renderInline(section.title)}</h2><div class="rule-highlight-list">${items.map((item) => `<div class="rule-highlight">${renderInline(item)}</div>`).join("")}</div></section>`;
}

function renderTopicEntries(section) {
  const entries = splitSubsections(section.lines, "### ");
  const cards = entries.map((entry) => {
    const summary = collectLeadingParagraphs(entry.lines).join(" ");
    const subSections = splitSubsections(entry.lines, "#### ");
    const signals = [];
    const rules = [];

    subSections.forEach((subSection) => {
      const items = collectBulletItemsFromLines(subSection.lines);
      if (subSection.title === "沉淀信号") signals.push(...items);
      if (subSection.title === "建议规则") rules.push(...items);
    });

    return `
      <article class="topic-card">
        <h3>${renderInline(entry.title)}</h3>
        ${summary ? `<p class="topic-summary">${renderInline(summary)}</p>` : ""}
        ${signals.length ? `<div class="topic-signals">${signals.map((item) => `<span>${renderInline(item)}</span>`).join("")}</div>` : ""}
        ${rules.length ? `<div class="rule-highlight-list">${rules.map((item) => `<div class="rule-highlight">${renderInline(item)}</div>`).join("")}</div>` : ""}
      </article>
    `;
  });

  return `<section class="doc-section"><h2>${renderInline(section.title)}</h2>${cards.join("")}</section>`;
}

function renderEvidenceSection(section) {
  const entries = splitSubsections(section.lines, "### ");
  const blocks = entries.map((entry) => {
    const items = collectBulletItemsFromLines(entry.lines);
    return `
      <details class="evidence-block">
        <summary>${renderInline(entry.title)} · ${items.length} 条</summary>
        <ul>${items.map((item) => `<li>${renderInline(item)}</li>`).join("")}</ul>
      </details>
    `;
  });
  return `<section class="doc-section"><h2>${renderInline(section.title)}</h2>${blocks.join("")}</section>`;
}

function renderGenericSection(section) {
  const paragraphs = collectLeadingParagraphs(section.lines);
  const items = collectBulletItemsFromLines(section.lines);
  const content = [];
  if (paragraphs.length) {
    content.push(paragraphs.map((paragraph) => `<p>${renderInline(paragraph)}</p>`).join(""));
  }
  if (items.length) {
    content.push(`<div class="rule-highlight-list">${items.map((item) => `<div class="rule-highlight">${renderInline(item)}</div>`).join("")}</div>`);
  }
  return `<section class="doc-section"><h2>${renderInline(section.title)}</h2>${content.join("")}</section>`;
}

function splitSubsections(lines, headingPrefix) {
  const entries = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) {
      i += 1;
      continue;
    }
    if (!line.startsWith(headingPrefix)) {
      i += 1;
      continue;
    }
    const title = line.slice(headingPrefix.length);
    i += 1;
    const buffer = [];
    while (i < lines.length) {
      const current = lines[i];
      if (current.trim().startsWith(headingPrefix)) break;
      buffer.push(current);
      i += 1;
    }
    entries.push({ title, lines: buffer });
  }
  return entries;
}

function collectBulletItemsFromLines(lines) {
  return lines.map((line) => line.trim()).filter((line) => line.startsWith("- ")).map((line) => line.slice(2));
}

function collectLeadingParagraphs(lines) {
  const paragraphs = [];
  let buffer = [];
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i].trim();
    if (!line) {
      if (buffer.length) {
        paragraphs.push(buffer.join(" "));
        buffer = [];
      }
      continue;
    }
    if (line.startsWith("#") || line.startsWith("- ")) break;
    buffer.push(line);
  }
  if (buffer.length) paragraphs.push(buffer.join(" "));
  return paragraphs;
}

function collectParagraphs(lines, startIndex) {
  const paragraphs = [];
  let i = startIndex;
  let current = [];
  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) {
      if (current.length) {
        paragraphs.push(current.join(" "));
        current = [];
      }
      i += 1;
      if (paragraphs.length) break;
      continue;
    }
    if (line.startsWith("#") || line.startsWith("- ")) break;
    current.push(line);
    i += 1;
  }
  if (current.length) paragraphs.push(current.join(" "));
  return { paragraphs, nextIndex: i };
}

function matchesSection(title, candidates) {
  return candidates.some((candidate) => title === candidate);
}

function readableFileName(file) {
  const map = {
    "SKILL.md": "入口说明",
    "principles.md": "设计原则",
    "page-patterns.md": "页面模式",
    "interaction-patterns.md": "交互模式",
    "component-patterns.md": "组件模式",
    "style-system.md": "样式系统",
    "content-rules.md": "表达规范",
    "manifest.json": "草稿清单",
  };
  return map[file.name] || file.name;
}

function categoryLabel(value) {
  return {
    principles: "设计原则",
    "page-patterns": "页面模式",
    "interaction-patterns": "交互模式",
    "component-patterns": "组件模式",
    "style-system": "样式系统",
    "content-rules": "表达规范",
  }[value] || value;
}

function stabilityLabel(value) {
  return {
    stable: "稳定",
    emerging: "待收敛",
    disputed: "有争议",
  }[value] || value;
}

function scopeLabel(value) {
  return {
    general_design_skill: "通用",
    project_specific_skill: "项目专属",
    product_doc: "产品文档",
    temporary_issue: "临时问题",
  }[value] || value;
}

function renderInline(text) {
  return escapeHtml(text).replace(/`([^`]+)`/g, "<code>$1</code>");
}

async function chooseProject() {
  const picked = await pickDirectory("选择项目目录", state.selectedProject || "/Users/fan/code");
  if (picked.canceled || !picked.path) {
    setStatus("已取消目录选择。");
    return;
  }

  if (picked.path !== state.selectedProject) {
    state.selectedProject = picked.path;
    els.cwdPrefixInput.value = picked.path;
    applyDerivedDefaults(picked.path);
    resetForProjectChange();
  }

  await identifyProject();
  state.currentStep = "project";
  renderApp();
  setStatus(`已选择项目：${picked.path}`, "success");
}

async function identifyProject() {
  const sessionsRoot = getSessionsRoot();
  const cwdPrefix = getCwdPrefix();
  if (!sessionsRoot || !cwdPrefix) return;
  const params = new URLSearchParams({
    sessions_root: sessionsRoot,
    cwd_prefix: cwdPrefix,
  });
  const payload = await requestJson(`/api/projects?${params.toString()}`);
  state.currentProjectInfo = payload.projects?.[0] || {
    project_id: slugifyProject(cwdPrefix),
    session_count: 0,
    sample_cwd: cwdPrefix,
  };
}

async function scanInsights() {
  if (!state.selectedProject) {
    setStatus("先选择项目目录。", "warning");
    return;
  }

  setStatus("正在生成规则洞察…");
  const params = new URLSearchParams({
    sessions_root: getSessionsRoot(),
    cwd_prefix: getCwdPrefix(),
    min_frequency: String(getMinFrequency()),
  });
  const payload = await requestJson(`/api/scan?${params.toString()}`);
  state.insights = payload.insights || [];
  state.insightsStats = payload.stats || null;
  markDraftStale();
  state.currentStep = "insights";
  renderApp();
  setStatus("规则洞察已生成。", "success");
}

async function mineSkill() {
  if (!state.selectedProject) {
    setStatus("先选择项目目录。", "warning");
    return;
  }
  if (!state.insights.length) {
    setStatus("请先生成规则洞察。", "warning");
    return;
  }

  setStatus("正在生成 Skill 草稿…");
  const payload = await requestJson("/api/mine-skill", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sessions_root: getSessionsRoot(),
      cwd_prefix: getCwdPrefix(),
      min_frequency: getMinFrequency(),
      out_dir: getDraftOutDir() || undefined,
      skill_name: getSkillName(),
    }),
  });

  state.draftFiles = payload.files || [];
  state.draftDir = payload.draft_dir || "";
  state.activeDraftFile = state.draftFiles[0] || null;
  state.draftMode = "read";
  state.draftStale = false;
  state.publishStale = !!state.publishedInfo;
  state.currentStep = "draft";
  renderApp();
  setStatus("Skill 草稿已生成。", "success");
}

async function saveDraftFile() {
  if (!state.activeDraftFile) {
    setStatus("请先生成草稿。", "warning");
    return;
  }

  setStatus("正在保存草稿…");
  const payload = await requestJson("/api/save-draft-file", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_path: state.activeDraftFile.path,
      content: els.draftEditor.value,
    }),
  });

  const savedFile = payload.file;
  state.draftFiles = state.draftFiles.map((file) => (file.path === savedFile.path ? savedFile : file));
  state.activeDraftFile = savedFile;
  state.draftMode = "read";
  state.publishStale = !!state.publishedInfo;
  renderApp();
  setStatus("草稿已保存。", "success");
}

async function ensurePublishRoot() {
  let publishRoot = getPublishRoot();
  if (publishRoot) return publishRoot;

  const picked = await pickDirectory("选择 Skill 暂存发布目录", "/Users/fan/Documents");
  if (picked.canceled || !picked.path) return "";
  state.publishRoot = picked.path;
  els.publishRootInput.value = picked.path;
  localStorage.setItem("designSkillMiner.publishRoot", picked.path);
  renderApp();
  return picked.path;
}

async function choosePublishRoot() {
  const current = getPublishRoot() || "/Users/fan/Documents";
  const picked = await pickDirectory("选择 Skill 暂存发布目录", current);
  if (picked.canceled || !picked.path) {
    setStatus("已取消选择暂存目录。");
    return;
  }
  state.publishRoot = picked.path;
  els.publishRootInput.value = picked.path;
  localStorage.setItem("designSkillMiner.publishRoot", picked.path);
  renderApp();
  setStatus(`已设置暂存目录：${picked.path}`, "success");
}

async function publishDraftNow() {
  if (!state.draftDir) {
    setStatus("请先生成草稿。", "warning");
    return;
  }

  const publishRoot = await ensurePublishRoot();
  if (!publishRoot) {
    setStatus("已取消发布。");
    return;
  }

  setStatus("正在发布到暂存区…");
  const payload = await requestJson("/api/publish-draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      draft_dir: state.draftDir,
      publish_root: publishRoot,
      publish_name: getSkillName(),
    }),
  });

  state.publishedInfo = payload;
  state.publishStale = false;
  state.currentStep = "publish";
  renderApp();
  setStatus("草稿已发布到暂存区。", "success");
}

function setDraftMode(mode) {
  state.draftMode = mode;
  applyDraftMode();
}

function applyDraftMode() {
  const isEdit = state.draftMode === "edit";
  els.draftContent.classList.toggle("is-hidden", isEdit);
  els.draftEditor.classList.toggle("is-hidden", !isEdit);
  els.draftReadModeBtn.classList.toggle("is-active", !isEdit);
  els.draftEditModeBtn.classList.toggle("is-active", isEdit);
  els.saveDraftFileBtn.disabled = !isEdit || !state.activeDraftFile;
}

function renderApp() {
  renderFlowSteps();
  renderStages();
  renderProjectStage();
  renderInsightsStage();
  renderDraftStage();
  renderPublishStage();
}

function handleClick(event) {
  const target = event.target.closest("[data-action]");
  if (!target) return;

  const action = target.getAttribute("data-action");
  if (action === "goto-step") {
    const step = target.getAttribute("data-step");
    if (step) setCurrentStep(step);
    return;
  }

  if (action === "open-draft-file") {
    const path = target.getAttribute("data-path");
    const file = state.draftFiles.find((item) => item.path === path);
    if (!file) return;
    state.activeDraftFile = file;
    renderDraftStage();
  }
}

function loadPreferences() {
  const savedPublishRoot = localStorage.getItem("designSkillMiner.publishRoot") || "";
  state.publishRoot = savedPublishRoot;
  els.publishRootInput.value = savedPublishRoot;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

els.chooseProjectBtn.addEventListener("click", () => {
  chooseProject().catch((error) => {
    setStatus(`选择项目失败：${error.message}`, "warning");
  });
});

els.projectNextBtn.addEventListener("click", () => {
  scanInsights().catch((error) => {
    setStatus(`生成规则洞察失败：${error.message}`, "warning");
  });
});

els.insightsBackBtn.addEventListener("click", () => setCurrentStep("project"));
els.insightsRefreshBtn.addEventListener("click", () => {
  scanInsights().catch((error) => {
    setStatus(`重新生成规则失败：${error.message}`, "warning");
  });
});
els.insightsNextBtn.addEventListener("click", () => {
  mineSkill().catch((error) => {
    setStatus(`生成 Skill 草稿失败：${error.message}`, "warning");
  });
});

els.draftBackBtn.addEventListener("click", () => setCurrentStep("insights"));
els.draftRefreshBtn.addEventListener("click", () => {
  mineSkill().catch((error) => {
    setStatus(`重新生成草稿失败：${error.message}`, "warning");
  });
});
els.draftNextBtn.addEventListener("click", () => setCurrentStep("publish"));
els.draftReadModeBtn.addEventListener("click", () => setDraftMode("read"));
els.draftEditModeBtn.addEventListener("click", () => setDraftMode("edit"));
els.saveDraftFileBtn.addEventListener("click", () => {
  saveDraftFile().catch((error) => {
    setStatus(`保存草稿失败：${error.message}`, "warning");
  });
});

els.publishBackBtn.addEventListener("click", () => setCurrentStep("draft"));
els.changePublishRootBtn.addEventListener("click", () => {
  choosePublishRoot().catch((error) => {
    setStatus(`设置暂存目录失败：${error.message}`, "warning");
  });
});
els.publishNowBtn.addEventListener("click", () => {
  publishDraftNow().catch((error) => {
    setStatus(`发布失败：${error.message}`, "warning");
  });
});

document.addEventListener("click", handleClick);

loadPreferences();
renderApp();
