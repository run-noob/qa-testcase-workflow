const test = require('node:test');
const assert = require('node:assert/strict');

const coverage = require('../assertions/llm-testcase-coverage');
const { golden } = require('../assertions/helpers');

const caseIds = new Set(['CASE-001', 'CASE-002']);

function response(overrides = {}) {
  return {
    results: golden.coverageUnits.map((unit) => ({
      id: unit.id,
      status: 'covered',
      caseIds: ['CASE-001'],
      evidence: '完整场景、操作和预期',
      reason: '语义覆盖完整',
      ...overrides[unit.id],
    })),
  };
}

function output() {
  return {
    artifacts: {
      testCases: [
        {
          path: 'cases.md',
          content: '### 用例\n- **用例编号**: CASE-001\n| 步骤 | 操作 | 预期结果 |',
        },
      ],
    },
  };
}

test('结构化结果按黄金权重计分，partial 计 0.5', () => {
  const result = coverage.validateAndScore(
    response({ A05: { status: 'partial' } }),
    golden.coverageUnits,
    caseIds,
  );
  assert.equal(result.earned, 22.5);
  assert.equal(result.total, 23);
  assert.equal(result.score, 22.5 / 23);
  assert.equal(result.componentResults.find((item) => item.reason.startsWith('A05')).score, 0.5);
});

test('拒绝覆盖点缺失、重复和非法状态', () => {
  const missing = response();
  missing.results.pop();
  assert.throws(
    () => coverage.validateAndScore(missing, golden.coverageUnits, caseIds),
    /missing coverage ids/,
  );

  const duplicate = response();
  duplicate.results.push({ ...duplicate.results[0] });
  assert.throws(
    () => coverage.validateAndScore(duplicate, golden.coverageUnits, caseIds),
    /duplicate coverage id/,
  );

  const invalid = response({ A01: { status: 'maybe' } });
  assert.throws(
    () => coverage.validateAndScore(invalid, golden.coverageUnits, caseIds),
    /invalid status/,
  );
});

test('拒绝不存在的用例编号和缺少证据的覆盖判断', () => {
  assert.throws(
    () =>
      coverage.validateAndScore(
        response({ A01: { caseIds: ['CASE-001', 'CASE-001'] } }),
        golden.coverageUnits,
        caseIds,
      ),
    /duplicate case id/,
  );
  assert.throws(
    () =>
      coverage.validateAndScore(
        response({ A01: { caseIds: ['NOT-FOUND'] } }),
        golden.coverageUnits,
        caseIds,
      ),
    /unknown case id/,
  );
  assert.throws(
    () =>
      coverage.validateAndScore(
        response({ A01: { evidence: '' } }),
        golden.coverageUnits,
        caseIds,
      ),
    /requires case ids and evidence/,
  );
});

test('runner 超时、非零退出和非法 JSON 结果显示为 grader error', async () => {
  const timeoutResult = await coverage(output(), {
    runner: async () => {
      throw new Error('Codex grader timed out after 1s');
    },
  });
  assert.equal(timeoutResult.pass, false);
  assert.match(timeoutResult.reason, /LLM grader error:.*timed out/);

  const exitResult = await coverage(output(), {
    runner: async () => {
      throw new Error('Codex grader exited with code 1');
    },
  });
  assert.equal(exitResult.pass, false);
  assert.match(exitResult.reason, /LLM grader error:.*exited with code 1/);

  const invalidResult = await coverage(output(), { runner: async () => ({ bad: true }) });
  assert.equal(invalidResult.pass, false);
  assert.match(invalidResult.reason, /LLM grader error:.*results array/);
});

test('语义回归响应可识别 A01、A03、A05，保留 D03 缺失', async () => {
  const graderResponse = response({
    D03: { status: 'missing', caseIds: [], evidence: '', reason: '没有仅含已兑换码的场景' },
  });
  const result = await coverage(output(), { runner: async () => graderResponse });
  assert.equal(result.componentResults.find((item) => item.reason.startsWith('A01')).score, 1);
  assert.equal(result.componentResults.find((item) => item.reason.startsWith('A03')).score, 1);
  assert.equal(result.componentResults.find((item) => item.reason.startsWith('A05')).score, 1);
  assert.equal(result.componentResults.find((item) => item.reason.startsWith('D03')).score, 0);
  assert.equal(result.score, 21 / 23);
  assert.equal(result.pass, true);
});
