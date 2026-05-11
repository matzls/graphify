/**
 * Plan Brief - deterministic human-readable companions for PLAN.md artifacts.
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const {
  atomicWriteFileSync,
  error,
  findPhaseInternal,
  normalizeMd,
  output,
  toPosixPath,
} = require('./core.cjs');
const { extractFrontmatter, parseMustHavesBlock } = require('./frontmatter.cjs');

const GENERATOR_ID = 'gsd-plan-brief-v1.2';

function normalizeForHash(content) {
  return String(content || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
}

function sourcePlanHash(content) {
  return 'sha256:' + crypto.createHash('sha256').update(normalizeForHash(content), 'utf8').digest('hex');
}

function planBriefPathFor(planPath) {
  if (!/-PLAN\.md$/i.test(planPath)) {
    error(`Plan brief requires a *-PLAN.md file, got: ${planPath}`);
  }
  return planPath.replace(/-PLAN\.md$/i, '-BRIEF.md');
}

function yamlQuote(value) {
  return `"${String(value || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

function compactText(value, fallback = 'Not specified in source plan.') {
  const text = String(value || '')
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  return text || fallback;
}

function extractXmlBlock(content, tag) {
  const re = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, 'i');
  const match = content.match(re);
  return match ? match[1].trim() : '';
}

function extractXmlTag(content, tag) {
  return compactText(extractXmlBlock(content, tag), '');
}

function extractTasks(content) {
  const tasks = [];
  const re = /<task\b([^>]*)>([\s\S]*?)<\/task>/gi;
  let match;
  while ((match = re.exec(content)) !== null) {
    const attrs = match[1] || '';
    const body = match[2] || '';
    const id = (attrs.match(/\bid=["']([^"']+)["']/i) || [])[1] || `task-${tasks.length + 1}`;
    const title = extractXmlTag(body, 'name') || compactText(body.split(/\r?\n/)[0], `Task ${tasks.length + 1}`);
    const action = extractXmlTag(body, 'action') || extractXmlTag(body, 'description') || 'Not specified in source plan.';
    const done = extractXmlTag(body, 'done') || extractXmlTag(body, 'success') || 'Not specified in source plan.';
    tasks.push({ id, title, action, done });
  }
  return tasks;
}

function cleanTaskTitle(title, fallback) {
  return compactText(title, fallback)
    .replace(/^Task\s+\d+\s*:\s*/i, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function sentenceCase(value) {
  const text = compactText(value, '');
  if (!text) return '';
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function trimSentence(value, maxLength = 180) {
  const text = compactText(value, '');
  if (text.length <= maxLength) return text.endsWith('.') ? text : `${text}.`;
  const clipped = text.slice(0, maxLength + 1);
  const boundary = Math.max(clipped.lastIndexOf(' '), clipped.lastIndexOf(','));
  const trimmed = clipped.slice(0, boundary > 80 ? boundary : maxLength).replace(/[,\s]+$/g, '');
  return `${trimmed}.`;
}

function truncateText(value, maxLength = 260) {
  const text = compactText(value, '');
  if (text.length <= maxLength) return text;
  const clipped = text.slice(0, maxLength + 1);
  const boundary = clipped.lastIndexOf(' ');
  const trimmed = clipped.slice(0, boundary > 80 ? boundary : maxLength).replace(/[,\s]+$/g, '');
  return `${trimmed}...`;
}

function takeSentences(value, maxSentences = 2, maxLength = 360) {
  const text = compactText(value, '');
  if (!text) return '';
  const parts = splitSentences(text);
  let picked = parts.slice(0, maxSentences).join(' ').trim();
  if (!picked) picked = text;
  if (picked.length <= maxLength) return picked;
  return trimSentence(picked, maxLength);
}

function splitSentences(value) {
  return compactText(value, '')
    .split(/(?<=[.!?])\s+(?=[`"']?[A-Z])/)
    .map(sentence => sentence.trim())
    .filter(Boolean);
}

function titleAsAction(title) {
  const cleanTitle = cleanTaskTitle(title, 'Complete the planned task.');
  return trimSentence(sentenceCase(cleanTitle));
}

function taskWorkSummary(task) {
  const fallback = titleAsAction(task.title);
  const action = compactText(task.action, '');
  if (!action) return fallback;

  let text = action
    .replace(/`[^`]+`/g, '')
    .replace(/\s+/g, ' ')
    .trim();

  const sentenceMatch = text.match(/^(.+?[.!?])(?:\s|$)/);
  text = sentenceMatch ? sentenceMatch[1] : text;
  text = text
    .split(';')[0]
    .replace(/:\s+.*$/i, '')
    .replace(/^(Create|Add|Implement|Extend|Run|Capture|Define|Wire)\b([\s\S]*?)\s+and\s+.*$/i, '$1$2')
    .replace(/\s+by\s+(adapting|copying|calling|using|patching|importing)\b.*$/i, '')
    .replace(/\s+from\s+\S+.*$/i, '')
    .replace(/\s+with\s+[`./\w-]+.*$/i, '')
    .replace(/\s+and\s+(assert|capture|patch|import|inspect|confirm)\b.*$/i, '')
    .replace(/\s+/g, ' ')
    .trim();

  if (
    text.length < 24 ||
    /^(create|add|implement|extend|run|capture|cover|define|wire)$/i.test(text) ||
    /^create\s+as\b/i.test(text)
  ) {
    return fallback;
  }
  return trimSentence(sentenceCase(text));
}

function listValue(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  if (typeof value === 'string') {
    if (value.trim() === '[]') return [];
    return value.split(',').map(v => v.replace(/^\[|\]$/g, '').trim()).filter(Boolean);
  }
  return [];
}

function bulletList(items, fallback = 'Not specified in source plan.') {
  const clean = items.map(item => compactText(item, '')).filter(Boolean);
  if (clean.length === 0) return `- ${fallback}`;
  return clean.map(item => `- ${item}`).join('\n');
}

function markdownTable(headers, rows) {
  const head = `| ${headers.join(' | ')} |`;
  const sep = `| ${headers.map(() => '---').join(' | ')} |`;
  const body = rows.map(row => `| ${row.map(cell => String(cell || '').replace(/\|/g, '\\|')).join(' | ')} |`);
  return [head, sep, ...body].join('\n');
}

function mermaidLabel(value) {
  return String(value || 'unspecified')
    .replace(/\\/g, '/')
    .replace(/"/g, "'")
    .replace(/`/g, '')
    .replace(/\[\[/g, '')
    .replace(/\]\]/g, '')
    .replace(/[\[\]{}<>]/g, '')
    .replace(/\|/g, '/')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 80);
}

function dependencyMermaid(keyLinks, tasks) {
  const lines = ['```mermaid', 'flowchart LR'];
  if (keyLinks.length > 0) {
    const ids = new Map();
    const idFor = (label) => {
      const key = mermaidLabel(label);
      if (!ids.has(key)) ids.set(key, `N${ids.size + 1}`);
      return ids.get(key);
    };
    for (const link of keyLinks) {
      if (!link || typeof link !== 'object') continue;
      const from = link.from || link.source || 'source plan';
      const to = link.to || link.target || 'planned artifact';
      const via = link.via || link.provides || 'feeds';
      const fromId = idFor(from);
      const toId = idFor(to);
      lines.push(`  ${fromId}["${mermaidLabel(from)}"] -->|${mermaidLabel(via)}| ${toId}["${mermaidLabel(to)}"]`);
    }
  } else if (tasks.length > 0) {
    tasks.forEach((task, index) => {
      const id = `T${index + 1}`;
      lines.push(`  ${id}["${mermaidLabel(task.title)}"]`);
      if (index > 0) lines.push(`  T${index} --> ${id}`);
    });
  } else {
    lines.push('  P["Source PLAN.md"] --> B["Human-readable brief"]');
  }
  lines.push('```');
  return lines.join('\n');
}

function isRuntimeLink(link) {
  const via = compactText(link && (link.via || link.provides || link.pattern), '').toLowerCase();
  const to = compactText(link && (link.to || link.target), '').toLowerCase();
  return !(
    /\b(test|tests|spec|coverage|covered by|assert|verif|proof)\b/.test(via) ||
    /\b(test|tests|spec)\b/.test(to)
  );
}

function flowMermaid(keyLinks, tasks) {
  const runtimeLinks = keyLinks.filter(isRuntimeLink);
  const lines = ['```mermaid', 'flowchart TD'];
  if (runtimeLinks.length > 0) {
    const ids = new Map();
    const idFor = (label) => {
      const key = mermaidLabel(label);
      if (!ids.has(key)) ids.set(key, `S${ids.size + 1}`);
      return ids.get(key);
    };
    const incoming = new Set();
    const outgoing = new Set();
    for (const link of runtimeLinks) {
      if (!link || typeof link !== 'object') continue;
      const from = link.from || link.source || 'source plan';
      const to = link.to || link.target || 'planned artifact';
      const via = link.via || link.provides || 'hands off';
      const fromId = idFor(from);
      const toId = idFor(to);
      outgoing.add(fromId);
      incoming.add(toId);
      lines.push(`  ${fromId}["${mermaidLabel(from)}"] -->|${mermaidLabel(via)}| ${toId}["${mermaidLabel(to)}"]`);
    }
    const startIds = [...outgoing].filter(id => !incoming.has(id));
    if (startIds.length > 0) {
      lines.splice(2, 0, `  Start(["Start"]) --> ${startIds[0]}`);
    }
  } else if (tasks.length > 0) {
    lines.push('  Start(["Start"])');
    tasks.forEach((task, index) => {
      const id = `T${index + 1}`;
      lines.push(`  ${id}["${mermaidLabel(cleanTaskTitle(task.title, task.id))}"]`);
      lines.push(index === 0 ? `  Start --> ${id}` : `  T${index} --> ${id}`);
    });
  } else {
    lines.push('  Start(["Source PLAN.md"]) --> Brief["Human-readable brief"]');
  }
  lines.push('```');
  return lines.join('\n');
}

function flowLinkSentence(link) {
  const from = compactText(link.from || link.source || 'the starting component', '');
  const to = compactText(link.to || link.target || 'the next component', '');
  const via = compactText(link.via || link.provides || 'hands off control', '');
  if (!from || !to) return '';
  return `- \`${from}\` hands off to \`${to}\`${via ? ` via ${via}` : ''}.`;
}

function taskDetailSentence(task, index) {
  const title = cleanTaskTitle(task.title, `Task ${index + 1}`);
  const action = takeSentences(
    sentenceCase(task.action)
      .replace(/with tests named exactly:[\s\S]*?Tests must/i, 'with named safety tests. Tests must')
      .replace(/Implement pure helpers for testability:[\s\S]*?Source validation/i, 'Implement pure testable helpers. Source validation'),
    2,
    380
  );
  const done = trimSentence(sentenceCase(task.done), 220);
  const parts = [`- **${title}:** ${action}`];
  if (done && done !== 'Not specified in source plan.') {
    parts.push(`Done when ${done.charAt(0).toLowerCase()}${done.slice(1)}`);
  }
  return parts.join(' ');
}

function flowExplanation(tasks, keyLinks) {
  const runtimeLinks = keyLinks.filter(isRuntimeLink);
  const lines = [];
  lines.push('Read this as the implementation/runtime story behind the plan: what gets built first, what calls what, and where responsibility moves.');
  lines.push('');
  lines.push('**Build order:**');
  if (tasks.length > 0) {
    tasks.forEach((task, index) => lines.push(taskDetailSentence(task, index)));
  } else {
    lines.push('- Not specified in source plan.');
  }
  lines.push('');
  lines.push('**Runtime hand-off:**');
  const linkLines = runtimeLinks.map(flowLinkSentence).filter(Boolean);
  if (linkLines.length > 0) {
    lines.push(...linkLines);
  } else if (tasks.length > 0) {
    tasks.forEach((task, index) => {
      const title = cleanTaskTitle(task.title, `Task ${index + 1}`);
      const next = tasks[index + 1] ? cleanTaskTitle(tasks[index + 1].title, `Task ${index + 2}`) : '';
      lines.push(next ? `- \`${title}\` feeds \`${next}\`.` : `- \`${title}\` completes the planned flow.`);
    });
  } else {
    lines.push('- Not specified in source plan.');
  }
  return lines.join('\n');
}

function extractNonGoals(content) {
  const nonGoals = [];
  const seen = new Set();
  const body = String(content || '').replace(/^---[\s\S]*?\n---\s*/m, '');
  for (const rawLine of body.split(/\r?\n/)) {
    const line = compactText(rawLine.replace(/^\s*[-*]\s*/, ''), '');
    if (!line || /^(phase|plan|type|wave|depends_on|files_modified|requirements):/i.test(line)) continue;
    if (/\b(rg -n|pytest|assert\.|expect\(|grep)\b/i.test(line)) continue;
    for (const sentence of splitSentences(line)) {
      if (!/\b(does not|do not|must not|not as|not import|not call|not write|not include|not planned|not touch)\b/i.test(sentence)) {
        continue;
      }
      const clean = truncateText(sentence, 260);
      const key = clean.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      nonGoals.push(clean);
      break;
    }
    if (nonGoals.length >= 6) break;
  }
  return nonGoals;
}

function makeTitle(planPath, frontmatter) {
  const planId = path.basename(planPath).replace(/-PLAN\.md$/i, '');
  const phase = frontmatter.phase ? `Phase ${frontmatter.phase}` : 'Plan';
  return `${phase} Brief: ${planId}`;
}

function generateBrief(planPath, content, opts = {}) {
  const now = opts.date || new Date().toISOString().slice(0, 10);
  const fm = extractFrontmatter(content);
  const tasks = extractTasks(content);
  const keyLinks = parseMustHavesBlock(content, 'key_links').filter(link => link && typeof link === 'object');
  const artifacts = parseMustHavesBlock(content, 'artifacts');
  const requirements = listValue(fm.requirements || fm.requirements_addressed);
  const filesModified = listValue(fm.files_modified);
  const dependencies = listValue(fm.depends_on);
  const objective = compactText(extractXmlBlock(content, 'objective'));
  const nonGoals = extractNonGoals(content);
  const title = makeTitle(planPath, fm);
  const relSource = './' + path.basename(planPath);
  const hash = sourcePlanHash(content);

  const changes = [];
  for (const file of filesModified) changes.push(`File or area: ${file}`);
  for (const artifact of artifacts) {
    if (artifact && typeof artifact === 'object' && artifact.path) {
      changes.push(`${artifact.path}${artifact.provides ? ` - ${artifact.provides}` : ''}`);
    } else if (artifact) {
      changes.push(String(artifact));
    }
  }

  const taskRows = tasks.length > 0
    ? tasks.map(task => [task.id, cleanTaskTitle(task.title, task.id), taskWorkSummary(task)])
    : [['Not specified', 'Not specified in source plan.', 'Not specified in source plan.']];

  const sourceRows = [
    ['Source plan', path.basename(planPath)],
    ['Source hash', hash],
    ['Generator', GENERATOR_ID],
  ];
  if (requirements.length > 0) sourceRows.push(['Requirements', requirements.join(', ')]);
  if (dependencies.length > 0) sourceRows.push(['Plan dependencies', dependencies.join(', ')]);

  const lines = [
    '---',
    `title: ${yamlQuote(title)}`,
    'kind: brief',
    'status: active',
    'audience: "humans-agents"',
    'canonicality: derived',
    `created: ${now}`,
    `updated: ${now}`,
    `source_of_truth: ${yamlQuote(relSource)}`,
    `source_plan: ${yamlQuote(path.basename(planPath))}`,
    `source_plan_hash: ${yamlQuote(hash)}`,
    `brief_generator: ${yamlQuote(GENERATOR_ID)}`,
    '---',
    '',
    `# ${title}`,
    '',
    '> This is a derived, human-readable companion to the executable PLAN.md. If this brief disagrees with the source plan, the PLAN.md is authoritative.',
    '',
    '## Plain-English Goal',
    '',
    objective,
    '',
    '## What Will Change',
    '',
    bulletList(changes),
    '',
    '## Dependency Map',
    '',
    dependencyMermaid(keyLinks, tasks),
    '',
    '## How The Flow Works',
    '',
    flowExplanation(tasks, keyLinks),
    '',
    '## Flow Diagram',
    '',
    flowMermaid(keyLinks, tasks),
    '',
    '## Task Summary',
    '',
    markdownTable(['Task', 'Outcome', 'Plain-English Work'], taskRows),
    '',
    '## What This Does Not Do',
    '',
    bulletList(nonGoals),
    '',
    '## Success Looks Like',
    '',
    bulletList(tasks.map(task => task.done)),
    '',
    '## Risks / Watchpoints',
    '',
    bulletList([
      dependencies.length > 0 ? `Depends on prior plan(s): ${dependencies.join(', ')}` : '',
      content.includes('<threat_model>') ? 'Source plan includes a threat model section that should be checked during execution.' : '',
      content.includes('<validation') || content.includes('<verification') ? 'Source plan includes validation expectations that should be preserved.' : '',
    ]),
    '',
    '## Source Trace',
    '',
    markdownTable(['Field', 'Value'], sourceRows),
    '',
  ];

  return normalizeMd(lines.join('\n'));
}

function readBriefFrontmatter(content) {
  const fm = extractFrontmatter(content);
  return {
    sourcePlanHash: fm.source_plan_hash || '',
    generator: fm.brief_generator || '',
  };
}

function resolvePlanFiles(cwd, target) {
  if (!target) error('plan-brief requires a *-PLAN.md path, phase directory, or phase number');

  const fullTarget = path.isAbsolute(target) ? target : path.join(cwd, target);
  if (fs.existsSync(fullTarget)) {
    const stat = fs.statSync(fullTarget);
    if (stat.isFile()) return [fullTarget];
    if (stat.isDirectory()) return listPlanFiles(fullTarget);
  }

  const phase = findPhaseInternal(cwd, target);
  if (!phase || !phase.directory) error(`Phase not found for plan-brief target: ${target}`);
  return listPlanFiles(path.join(cwd, phase.directory));
}

function listPlanFiles(dir) {
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    error(`Plan brief target is not a directory: ${dir}`);
  }
  return fs.readdirSync(dir)
    .filter(name => /-PLAN\.md$/i.test(name) && !/\.pre-bounce\.md$/i.test(name))
    .sort()
    .map(name => path.join(dir, name));
}

function generatePlanBriefs(cwd, target, raw) {
  const plans = resolvePlanFiles(cwd, target);
  const briefs = plans.map(planPath => {
    const content = fs.readFileSync(planPath, 'utf-8');
    const briefPath = planBriefPathFor(planPath);
    const brief = generateBrief(planPath, content);
    atomicWriteFileSync(briefPath, brief);
    return {
      plan: toPosixPath(path.relative(cwd, planPath)),
      brief: toPosixPath(path.relative(cwd, briefPath)),
      source_plan_hash: sourcePlanHash(content),
    };
  });
  output({ generated: true, checked: false, count: briefs.length, briefs }, raw);
}

function checkPlanBriefs(cwd, target, raw) {
  const plans = resolvePlanFiles(cwd, target);
  const briefs = plans.map(planPath => {
    const content = fs.readFileSync(planPath, 'utf-8');
    const briefPath = planBriefPathFor(planPath);
    const expectedHash = sourcePlanHash(content);
    const exists = fs.existsSync(briefPath);
    const actual = exists ? readBriefFrontmatter(fs.readFileSync(briefPath, 'utf-8')) : { sourcePlanHash: '', generator: '' };
    const hashMismatch = actual.sourcePlanHash !== expectedHash;
    const generatorMismatch = actual.generator !== GENERATOR_ID;
    const stale = !exists || hashMismatch || generatorMismatch;
    return {
      plan: toPosixPath(path.relative(cwd, planPath)),
      brief: toPosixPath(path.relative(cwd, briefPath)),
      exists,
      stale,
      generator_mismatch: generatorMismatch,
      expected_hash: expectedHash,
      actual_hash: actual.sourcePlanHash,
      expected_generator: GENERATOR_ID,
      actual_generator: actual.generator,
    };
  });
  const missingCount = briefs.filter(item => !item.exists).length;
  const staleCount = briefs.filter(item => item.stale).length;
  output({
    generated: false,
    checked: true,
    passed: missingCount === 0 && staleCount === 0,
    count: briefs.length,
    missing_count: missingCount,
    stale_count: staleCount,
    briefs,
  }, raw);
}

function cmdPlanBrief(cwd, args, raw) {
  const check = args.includes('--check');
  const target = args.slice(1).filter(arg => arg !== '--check')[0];
  if (check) {
    checkPlanBriefs(cwd, target, raw);
  } else {
    generatePlanBriefs(cwd, target, raw);
  }
}

module.exports = {
  GENERATOR_ID,
  cmdPlanBrief,
  generateBrief,
  normalizeForHash,
  planBriefPathFor,
  sourcePlanHash,
  taskWorkSummary,
};
