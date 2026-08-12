const { parseOutput, artifacts } = require('./helpers');

module.exports = (output) => {
  const parsed = parseOutput(output);
  const data = artifacts(output);
  const checks = [
    ['Codex 正常退出', parsed.run?.exitCode === 0],
    ['生成分析报告', data.analysis?.exists === true],
    ['生成独立澄清清单', data.clarifications?.exists === true],
    ['分析报告路径符合需求目录契约', data.analysis?.path === 'prd/优惠券系统小细节优化/output/优惠券系统小细节优化-analysis.md'],
    ['澄清清单路径符合需求目录契约', data.clarifications?.path === 'prd/优惠券系统小细节优化/output/优惠券系统小细节优化-clarifications.md'],
    ['生成进度文件', data.progress?.exists === true],
    ['生成用例汇总', data.summary?.exists === true],
    ['至少生成一个模块用例文件', (data.testCases || []).length > 0],
    ['未生成 Excel/XMind', (data.binaryExports || []).length === 0],
    ['未修改全量 test-cases 用例库', (data.globalCaseLibraryChanges || []).length === 0],
  ];
  const passed = checks.filter(([, ok]) => ok).length;
  const score = passed / checks.length;
  return {
    pass: score === 1,
    score,
    reason: checks.map(([name, ok]) => `${ok ? 'PASS' : 'FAIL'} ${name}`).join('；'),
    componentResults: checks.map(([name, ok]) => ({ pass: ok, score: ok ? 1 : 0, reason: name })),
  };
};
