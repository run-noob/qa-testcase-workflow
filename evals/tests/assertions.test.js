const test = require('node:test');
const assert = require('node:assert/strict');

const contract = require('../assertions/artifact-contract');
const facts = require('../assertions/analysis-facts');
const forbidden = require('../assertions/forbidden-claims');
const clarifications = require('../assertions/clarifications');
const coverage = require('../assertions/testcase-coverage');
const quality = require('../assertions/testcase-quality');
const consistency = require('../assertions/consistency');
const scoring = require('../assertions/scoring');

function passingOutput() {
  const analysis = `
当前表现：只要告警配置为“是”，无论批次状态是否有效都会一直告警。
批次无效时不再告警；当前时间已超过截止时间时不再告警。
当前删除优惠券多码批次时，底表兑换码没有同步删除。
删除多码批次时同步删除对应批次所有未兑换兑换码。
`;
  const clarificationText = `
当前时间等于截止时间是否视为过期？
有效、无效与截图中的上线状态如何映射和定义？
未兑换和已兑换以哪个字段、状态值或枚举判定？
底表清理失败时，事务回滚、重试与数据一致性策略是什么？
`;
  const caseA = `
### 验证告警条件组合及状态变化
- **用例编号**: COUPON_ALERT-001
- **用例类型**: 正常
- **优先级**: P0
- **前置条件**:
  1. 告警配置为“是”。
- **测试步骤**:
  | 步骤 | 操作 | 预期结果 |
  |---|---|---|
  | 1 | 设置批次有效且当前时间早于截止时间并执行任务 | 继续触发告警。 |
  | 2 | 将状态由有效改为无效后再次执行下一次任务 | 后续不再告警。 |
  | 3 | 设置有效但当前时间已超过截止时间并执行任务 | 批次被过滤，不产生告警。 |
- **测试数据**: 使用测试环境实际批次。

### 验证无效批次和关闭告警配置
- **用例编号**: COUPON_ALERT-002
- **用例类型**: 回归
- **优先级**: P1
- **前置条件**:
  1. 可执行告警任务。
- **测试步骤**:
  | 步骤 | 操作 | 预期结果 |
  |---|---|---|
  | 1 | 设置批次无效并执行任务 | 不再告警。 |
  | 2 | 设置告警配置为“否”并执行任务 | 不产生告警，既有行为不受影响。 |
- **测试数据**: 使用测试环境实际批次。
`;
  const caseD = `
### 删除多码批次并校验兑换码隔离
- **用例编号**: COUPON_DELETE-001
- **用例类型**: 正常
- **优先级**: P0
- **前置条件**:
  1. 批次存在未兑换兑换码。
- **测试步骤**:
  | 步骤 | 操作 | 预期结果 |
  |---|---|---|
  | 1 | 删除多码批次 | 该批次所有未兑换兑换码删除，数量为0。 |
  | 2 | 查询其他批次 | 其他批次不受影响。 |
- **测试数据**: 使用测试环境实际批次。

### 删除混合兑换状态的多码批次
- **用例编号**: COUPON_DELETE-002
- **用例类型**: 正常
- **优先级**: P0
- **前置条件**:
  1. 同时存在未兑换和已兑换兑换码。
- **测试步骤**:
  | 步骤 | 操作 | 预期结果 |
  |---|---|---|
  | 1 | 删除目标批次 | 未兑换兑换码删除，已兑换兑换码仍存在并保留。 |
  | 2 | 查询其他批次 | 不影响其他批次。 |
- **测试数据**: 使用测试环境实际批次。

### 删除没有未兑换兑换码的批次
- **用例编号**: COUPON_DELETE-003
- **用例类型**: 边界
- **优先级**: P1
- **前置条件**:
  1. 没有未兑换兑换码，仅有已兑换记录。
- **测试步骤**:
  | 步骤 | 操作 | 预期结果 |
  |---|---|---|
  | 1 | 删除目标批次 | 不报错，已兑换记录保留且不误删。 |
  | 2 | 查询其他批次 | 其他批次保持不变。 |
- **测试数据**: 使用测试环境实际批次。
`;
  return {
    run: { exitCode: 0 },
    artifacts: {
      analysis: {
        exists: true,
        path: 'prd/优惠券系统小细节优化/output/优惠券系统小细节优化-analysis.md',
        content: analysis,
      },
      clarifications: {
        exists: true,
        path: 'prd/优惠券系统小细节优化/output/优惠券系统小细节优化-clarifications.md',
        content: clarificationText,
      },
      progress: {
        exists: true,
        content: '| 优惠券告警 | 告警.md | 已完成 |\n| 多码删除 | 删除.md | 已完成 |',
      },
      summary: {
        exists: true,
        content: '覆盖矩阵\n覆盖缺口与待确认项\n告警.md\n删除.md\nCOUPON_ALERT-001 COUPON_ALERT-002 COUPON_DELETE-001 COUPON_DELETE-002 COUPON_DELETE-003',
      },
      testCases: [
        { path: 'prd/x/output/test-cases/告警.md', content: caseA },
        { path: 'prd/x/output/test-cases/删除.md', content: caseD },
      ],
      binaryExports: [],
      globalCaseLibraryChanges: [],
    },
  };
}

test('黄金结构样本通过全部核心 assertions', () => {
  const output = passingOutput();
  const results = {
    artifact_contract: contract(output).score,
    core_fact_recall: facts(output).score,
    forbidden_claim_control: forbidden(output).score,
    clarification_recall: clarifications(output).score,
    testcase_coverage: coverage(output).score,
    testcase_quality: quality(output).score,
    cross_artifact_consistency: consistency(output).score,
  };
  assert.equal(results.artifact_contract, 1);
  assert.equal(results.core_fact_recall, 1);
  assert.equal(results.forbidden_claim_control, 1);
  assert.equal(results.clarification_recall, 1);
  assert.ok(results.testcase_coverage >= 0.9);
  assert.ok(results.testcase_quality >= 0.9);
  assert.equal(results.cross_artifact_consistency, 1);
  assert.equal(scoring(results).pass, true);
});

test('缺失独立澄清清单触发硬门禁失败', () => {
  const output = passingOutput();
  output.artifacts.clarifications = { exists: false, content: '' };
  const gate = contract(output);
  assert.ok(gate.score < 1);
  assert.equal(gate.pass, false);
});

test('严重无依据结论触发失败', () => {
  const output = passingOutput();
  output.artifacts.analysis.content += '\n上线就是有效，状态0就是未兑换。';
  const result = forbidden(output);
  assert.equal(result.score, 0);
  assert.equal(result.pass, false);
});
