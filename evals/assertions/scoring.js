module.exports = (scores) => {
  const required = [
    'artifact_contract',
    'core_fact_recall',
    'forbidden_claim_control',
    'clarification_recall',
    'testcase_coverage',
    'testcase_quality',
    'cross_artifact_consistency',
  ];
  const missing = required.filter((name) => scores[name] === undefined);
  const weightedScore =
    (scores.core_fact_recall || 0) * 0.30 +
    (scores.forbidden_claim_control || 0) * 0.15 +
    (scores.clarification_recall || 0) * 0.15 +
    (scores.testcase_coverage || 0) * 0.25 +
    (scores.testcase_quality || 0) * 0.075 +
    (scores.cross_artifact_consistency || 0) * 0.075;

  const hardFailures = [];
  if ((scores.artifact_contract || 0) < 1) hardFailures.push('产物契约未全部满足');
  if ((scores.forbidden_claim_control || 0) < 1) hardFailures.push('出现严重无依据结论');
  if ((scores.core_fact_recall || 0) < 0.95) hardFailures.push('核心事实召回率低于 95%');
  if ((scores.testcase_coverage || 0) < 0.90) hardFailures.push('用例覆盖率低于 90%');
  if (missing.length) hardFailures.push(`缺少指标: ${missing.join(', ')}`);

  const pass = hardFailures.length === 0 && weightedScore >= 0.85;
  return {
    pass,
    score: weightedScore,
    reason: `${hardFailures.length ? hardFailures.join('；') : '硬门禁通过'}；综合得分 ${(weightedScore * 100).toFixed(1)}`,
  };
};
