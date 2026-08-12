const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');

const { golden, artifacts } = require('./helpers');

const STATUS_SCORES = { covered: 1, partial: 0.5, missing: 0 };
const DEFAULT_MODEL = 'gpt-5.6-luna';
const DEFAULT_TIMEOUT_SECONDS = 180;

function extractCaseIds(files) {
  return new Set(
    files.flatMap((file) =>
      [...(file.content || '').matchAll(/用例编号\*{0,2}\s*[:：]\s*([^\s]+)/g)].map(
        (match) => match[1],
      ),
    ),
  );
}

function buildPrompt(coverageUnits, files) {
  const units = coverageUnits.map(({ id, description }) => ({ id, description }));
  const testCases = files.map(({ path: filePath, content }) => ({ path: filePath, content }));
  return `你是严格、保守的 QA 测试覆盖评审员。请仅根据下面提供的模块测试用例，逐项判断黄金覆盖点的语义覆盖情况。

判定规则：
1. 不得根据分析报告、汇总表或覆盖声明判定覆盖；只认可实际模块用例。
2. 可以组合同一条用例的标题、前置条件、步骤和预期结果，不要求固定词序或固定措辞。
3. covered：场景条件、执行动作和可验证预期完整表达。
4. partial：提到该场景，但缺少关键条件、执行动作或可验证预期。
5. missing：没有相关用例，或只有声明而没有实际测试步骤。
6. 待确认或条件性用例只有在明确保留未知项，并给出确认后可执行的动作与预期口径时，才可判为 covered。
7. covered 或 partial 必须引用真实存在的用例编号，并给出简短原文证据；missing 的 caseIds 必须为空，evidence 可以为空。
8. 每个覆盖点必须且只能返回一次。不要增加输入中不存在的覆盖点。

黄金覆盖点：
${JSON.stringify(units, null, 2)}

模块测试用例：
${JSON.stringify(testCases, null, 2)}
`;
}

function runCodexGrader(prompt, options = {}) {
  const model =
    options.model ||
    process.env.CODEX_EVAL_GRADER_MODEL ||
    process.env.CODEX_EVAL_MODEL ||
    DEFAULT_MODEL;
  const timeoutSeconds = Number(
    options.timeoutSeconds ||
      process.env.CODEX_EVAL_GRADER_TIMEOUT_SECONDS ||
      DEFAULT_TIMEOUT_SECONDS,
  );
  const schemaPath = path.join(__dirname, 'llm-coverage-schema.json');
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'qa-coverage-grader-'));
  const outputPath = path.join(tempDir, 'result.json');
  const args = [
    'exec',
    '--ephemeral',
    '--skip-git-repo-check',
    '--ignore-rules',
    '--sandbox',
    process.env.CODEX_EVAL_GRADER_SANDBOX || 'read-only',
    '--output-schema',
    schemaPath,
    '--output-last-message',
    outputPath,
    '--model',
    model,
    '--',
    '-',
  ];
  console.log(args.join(' '))
  return new Promise((resolve, reject) => {
    const child = spawn(process.env.CODEX_BIN || 'codex', args, {
      cwd: path.resolve(__dirname, '../..'),
      detached: true,
      stdio: ['pipe', 'ignore', 'pipe'],
    });
    let stderr = '';
    let settled = false;
    let timedOut = false;
    let killTimer;

    const cleanup = () => fs.rmSync(tempDir, { recursive: true, force: true });
    const finish = (callback) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      clearTimeout(killTimer);
      callback();
    };
    const timer = setTimeout(() => {
      timedOut = true;
      try {
        process.kill(-child.pid, 'SIGTERM');
      } catch {}
      killTimer = setTimeout(() => {
        try {
          process.kill(-child.pid, 'SIGKILL');
        } catch {}
      }, 5000);
    }, timeoutSeconds * 1000);

    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
      if (stderr.length > 8000) stderr = stderr.slice(-8000);
    });
    child.on('error', (error) =>
      finish(() => {
        cleanup();
        reject(error);
      }),
    );
    child.on('close', (code) =>
      finish(() => {
        try {
          if (timedOut) throw new Error(`Codex grader timed out after ${timeoutSeconds}s`);
          if (code !== 0) {
            throw new Error(`Codex grader exited with code ${code}: ${stderr.trim() || 'no stderr'}`);
          }
          if (!fs.existsSync(outputPath)) throw new Error('Codex grader produced no result file');
          resolve(JSON.parse(fs.readFileSync(outputPath, 'utf8')));
        } catch (error) {
          reject(error);
        } finally {
          cleanup();
        }
      }),
    );
    child.stdin.on('error', () => {});
    child.stdin.end(prompt);
  });
}

function validateAndScore(response, coverageUnits, validCaseIds) {
  if (!response || !Array.isArray(response.results)) {
    throw new Error('grader response must contain a results array');
  }
  const expectedIds = new Set(coverageUnits.map((item) => item.id));
  const seen = new Set();

  for (const item of response.results) {
    if (!item || typeof item !== 'object') throw new Error('grader result must be an object');
    if (!expectedIds.has(item.id)) throw new Error(`unknown coverage id: ${item.id}`);
    if (seen.has(item.id)) throw new Error(`duplicate coverage id: ${item.id}`);
    seen.add(item.id);
    if (!Object.hasOwn(STATUS_SCORES, item.status)) {
      throw new Error(`invalid status for ${item.id}: ${item.status}`);
    }
    if (!Array.isArray(item.caseIds)) throw new Error(`caseIds must be an array for ${item.id}`);
    if (new Set(item.caseIds).size !== item.caseIds.length) {
      throw new Error(`duplicate case id for ${item.id}`);
    }
    const unknownIds = item.caseIds.filter((id) => !validCaseIds.has(id));
    if (unknownIds.length) throw new Error(`unknown case id for ${item.id}: ${unknownIds.join(', ')}`);
    if (item.status === 'missing' && item.caseIds.length) {
      throw new Error(`missing result ${item.id} must not reference case ids`);
    }
    if (item.status !== 'missing' && (!item.caseIds.length || !String(item.evidence || '').trim())) {
      throw new Error(`${item.status} result ${item.id} requires case ids and evidence`);
    }
    if (!String(item.reason || '').trim()) throw new Error(`result ${item.id} requires a reason`);
  }

  const missingIds = [...expectedIds].filter((id) => !seen.has(id));
  if (missingIds.length) throw new Error(`missing coverage ids: ${missingIds.join(', ')}`);

  const byId = new Map(response.results.map((item) => [item.id, item]));
  const total = coverageUnits.reduce((sum, item) => sum + (item.weight || 1), 0);
  const earned = coverageUnits.reduce(
    (sum, item) => sum + (item.weight || 1) * STATUS_SCORES[byId.get(item.id).status],
    0,
  );
  const score = total ? earned / total : 0;
  const componentResults = coverageUnits.map((unit) => {
    const item = byId.get(unit.id);
    const caseText = item.caseIds.length ? `；用例 ${item.caseIds.join(', ')}` : '';
    const evidenceText = item.evidence ? `；证据：${item.evidence}` : '';
    return {
      pass: item.status === 'covered',
      score: STATUS_SCORES[item.status],
      reason: `${unit.id} [${item.status}] ${unit.description}${caseText}${evidenceText}；${item.reason}`,
    };
  });
  return { score, earned, total, componentResults };
}

async function evaluate(output, options = {}) {
  const files = artifacts(output).testCases || [];
  if (!files.length) return { pass: false, score: 0, reason: '未解析到模块测试用例' };
  const coverageUnits = golden.coverageUnits;
  try {
    const runner = options.runner || runCodexGrader;
    const response = await runner(buildPrompt(coverageUnits, files), options);
    const result = validateAndScore(response, coverageUnits, extractCaseIds(files));
    return {
      pass: result.score >= 0.9,
      score: result.score,
      reason: `LLM 用例覆盖加权得分 ${result.earned}/${result.total} (${(result.score * 100).toFixed(1)}%)`,
      componentResults: result.componentResults,
    };
  } catch (error) {
    return {
      pass: false,
      score: 0,
      reason: `LLM grader error: ${error.message}`,
    };
  }
}

module.exports = evaluate;
module.exports.buildPrompt = buildPrompt;
module.exports.extractCaseIds = extractCaseIds;
module.exports.runCodexGrader = runCodexGrader;
module.exports.validateAndScore = validateAndScore;
