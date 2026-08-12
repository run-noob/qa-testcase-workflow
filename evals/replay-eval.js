const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const ROOT = path.resolve(__dirname, '..');
const EVALS_DIR = path.join(ROOT, 'evals');

const METRICS = {
  artifact_contract: { file: 'artifact-contract.js', metric: 'artifact_contract' },
  core_fact_recall: { file: 'analysis-facts.js', metric: 'core_fact_recall' },
  forbidden_claim_control: { file: 'forbidden-claims.js', metric: 'forbidden_claim_control' },
  clarification_recall: { file: 'clarifications.js', metric: 'clarification_recall' },
  testcase_coverage: { file: 'testcase-coverage.js', metric: 'testcase_coverage' },
  llm_testcase_coverage: { file: 'llm-testcase-coverage.js', metric: 'testcase_coverage' },
  testcase_quality: { file: 'testcase-quality.js', metric: 'testcase_quality' },
  cross_artifact_consistency: { file: 'consistency.js', metric: 'cross_artifact_consistency' },
};

const PROFILES = {
  standard: [
    'artifact_contract',
    'core_fact_recall',
    'forbidden_claim_control',
    'clarification_recall',
    'testcase_coverage',
    'testcase_quality',
    'cross_artifact_consistency',
  ],
  llm: [
    'artifact_contract',
    'core_fact_recall',
    'forbidden_claim_control',
    'clarification_recall',
    'llm_testcase_coverage',
    'testcase_quality',
    'cross_artifact_consistency',
  ],
};

function usage() {
  return `用法:
  npm run eval:replay -- [选项]

选项:
  --report <path>       源 Promptfoo JSON 报告
  --result-index <n>    报告中的结果索引，默认 0
  --metrics <list>      逗号分隔的评测点，覆盖 --profile
  --profile <name>      standard 或 llm，默认 llm
  --output-name <name>  输出文件名前缀，默认 replay-<timestamp>
  --list-metrics        列出可选评测点
  --help                显示帮助

示例:
  npm run eval:replay -- --metrics core_fact_recall,clarification_recall
  npm run eval:replay -- --report evals/reports/coupon-results.json --profile standard
  npm run eval:replay -- --metrics llm_testcase_coverage --result-index 0`;
}

function parseArgs(argv) {
  const options = {
    report: path.join(EVALS_DIR, 'reports/coupon-llm-results.json'),
    resultIndex: 0,
    profile: 'llm',
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--help' || arg === '--list-metrics') {
      options[arg.slice(2).replace('-', '')] = true;
      continue;
    }
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) throw new Error(`${arg} 缺少参数值`);
    index += 1;
    if (arg === '--report') options.report = path.resolve(ROOT, value);
    else if (arg === '--result-index') options.resultIndex = Number(value);
    else if (arg === '--metrics') options.metrics = value.split(',').map((item) => item.trim()).filter(Boolean);
    else if (arg === '--profile') options.profile = value;
    else if (arg === '--output-name') options.outputName = value;
    else throw new Error(`未知参数: ${arg}`);
  }
  if (!Number.isInteger(options.resultIndex) || options.resultIndex < 0) {
    throw new Error('--result-index 必须是非负整数');
  }
  if (!PROFILES[options.profile]) throw new Error(`未知 profile: ${options.profile}`);
  options.metrics ||= PROFILES[options.profile];
  const unknown = options.metrics.filter((metric) => !METRICS[metric]);
  if (unknown.length) throw new Error(`未知评测点: ${unknown.join(', ')}`);
  options.metrics = [...new Set(options.metrics)];
  return options;
}

function inspectSource(reportPath, resultIndex) {
  if (!fs.existsSync(reportPath)) throw new Error(`源报告不存在: ${reportPath}`);
  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
  const result = report.results?.results?.[resultIndex];
  if (!result?.response?.output) {
    throw new Error(`源报告缺少 results.results[${resultIndex}].response.output`);
  }
  return {
    evalId: report.evalId || 'unknown',
    caseId: result.vars?.case_id || result.response.output.run?.caseId || `result-${resultIndex}`,
  };
}

function yamlString(value) {
  return JSON.stringify(String(value));
}

function buildConfig(options, source) {
  const providerPath = path.join(EVALS_DIR, 'providers/replay_report_provider.js');
  const assertions = options.metrics.map((selection) => {
    const assertion = METRICS[selection];
    return `      - type: javascript
        value: ${yamlString(`file://${path.join(EVALS_DIR, 'assertions', assertion.file)}`)}
        metric: ${assertion.metric}`;
  }).join('\n');
  const isFullProfile = Object.values(PROFILES).some(
    (profile) => profile.length === options.metrics.length && profile.every((item) => options.metrics.includes(item)),
  );
  const scoring = isFullProfile
    ? `\ndefaultTest:\n  threshold: 0.85\n  assertScoringFunction: ${yamlString(`file://${path.join(EVALS_DIR, 'assertions/scoring.js')}`)}\n`
    : '';
  return `description: ${yamlString(`历史产物重评 ${source.caseId}: ${options.metrics.join(', ')}`)}

providers:
  - id: ${yamlString(`file://${providerPath}`)}
    label: replay-${source.caseId}
    config:
      report: ${yamlString(options.report)}
      resultIndex: ${options.resultIndex}

prompts:
  - ${yamlString('已有工作流产物重评')}

tests:
  - description: ${yamlString(`${source.caseId} 历史产物重评`)}
    vars:
      case_id: ${yamlString(source.caseId)}
    metadata:
      stage: replay
      sourceEvalId: ${yamlString(source.evalId)}
      metrics: ${yamlString(options.metrics.join(','))}
    assert:
${assertions}
${scoring}
sharing: false
`;
}

function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
    if (options.help) return console.log(usage());
    if (options.listmetrics) return console.log(Object.keys(METRICS).join('\n'));
    const source = inspectSource(options.report, options.resultIndex);
    const timestamp = new Date().toISOString().replace(/[-:]/g, '').replace(/[TZ.]/g, '-').replace(/-$/, '');
    const outputName = options.outputName || `replay-${timestamp}`;
    if (!/^[A-Za-z0-9._-]+$/.test(outputName)) throw new Error('--output-name 只能包含字母、数字、点、下划线和连字符');

    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'qa-eval-replay-'));
    const configPath = path.join(tempDir, 'promptfooconfig.yaml');
    fs.writeFileSync(configPath, buildConfig(options, source));
    const jsonPath = path.join(EVALS_DIR, 'reports', `${outputName}-results.json`);
    const htmlPath = path.join(EVALS_DIR, 'reports', `${outputName}-report.html`);
    const promptfoo = path.join(ROOT, 'node_modules/.bin/promptfoo');

    console.log(`源评测: ${source.evalId}，结果索引: ${options.resultIndex}`);
    console.log(`评测点: ${options.metrics.join(', ')}`);
    const child = spawnSync(promptfoo, [
      'eval', '-c', configPath, '--no-cache', '-o', jsonPath, '-o', htmlPath,
    ], {
      cwd: ROOT,
      env: { ...process.env, PROMPTFOO_CONFIG_DIR: path.join(EVALS_DIR, '.promptfoo') },
      stdio: 'inherit',
    });
    fs.rmSync(tempDir, { recursive: true, force: true });
    if (child.error) throw child.error;
    process.exitCode = child.status ?? 1;
    console.log(`JSON: ${jsonPath}`);
    console.log(`HTML: ${htmlPath}`);
  } catch (error) {
    console.error(`重评失败: ${error.message}`);
    console.error(usage());
    process.exitCode = 1;
  }
}

if (require.main === module) main();

module.exports = { METRICS, PROFILES, parseArgs, inspectSource, buildConfig };
