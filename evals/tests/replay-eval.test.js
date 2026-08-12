const test = require('node:test');
const assert = require('node:assert/strict');

const { parseArgs, buildConfig } = require('../replay-eval');

test('重评参数支持 profile、单项和多项指标', () => {
  assert.deepEqual(parseArgs([]).metrics, [
    'artifact_contract',
    'core_fact_recall',
    'forbidden_claim_control',
    'clarification_recall',
    'llm_testcase_coverage',
    'testcase_quality',
    'cross_artifact_consistency',
  ]);
  assert.deepEqual(
    parseArgs(['--metrics', 'core_fact_recall,clarification_recall']).metrics,
    ['core_fact_recall', 'clarification_recall'],
  );
  assert.throws(() => parseArgs(['--metrics', 'unknown']), /未知评测点/);
});

test('动态配置只包含指定 assertions 和源报告', () => {
  const options = parseArgs([
    '--report',
    'evals/reports/coupon-results.json',
    '--metrics',
    'core_fact_recall,testcase_quality',
  ]);
  const config = buildConfig(options, { evalId: 'eval-source', caseId: 'coupon-001' });
  assert.match(config, /analysis-facts\.js/);
  assert.match(config, /testcase-quality\.js/);
  assert.doesNotMatch(config, /llm-testcase-coverage\.js/);
  assert.doesNotMatch(config, /assertScoringFunction/);
  assert.match(config, /coupon-results\.json/);
});

test('完整 profile 复用综合评分函数，子集不使用完整硬门禁', () => {
  const full = buildConfig(parseArgs(['--profile', 'llm']), {
    evalId: 'eval-source',
    caseId: 'coupon-001',
  });
  assert.match(full, /assertScoringFunction/);
  assert.match(full, /scoring\.js/);
});
