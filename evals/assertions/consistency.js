const { artifacts } = require('./helpers');

module.exports = (output) => {
  const data = artifacts(output);
  const progress = data.progress?.content || '';
  const summary = data.summary?.content || '';
  const files = data.testCases || [];
  const allCases = files.map((item) => item.content || '').join('\n');
  const ids = [...allCases.matchAll(/用例编号\*{0,2}\s*[:：]\s*([^\s]+)/g)].map((match) => match[1]);
  const summaryIds = [...summary.matchAll(/[A-Z][A-Z0-9_]+-\d{3}/g)].map((match) => match[0]);
  const missingSummaryIds = [...new Set(summaryIds)].filter((id) => !ids.includes(id));

  const checks = [
    ['进度中的模块均完成', /已完成/.test(progress) && !/待生成|生成中/.test(progress)],
    ['进度文件列出全部模块用例文件', files.every((file) => progress.includes(file.path.split('/').pop()))],
    ['汇总文件列出全部模块用例文件', files.every((file) => summary.includes(file.path.split('/').pop()))],
    ['汇总引用的用例编号真实存在', missingSummaryIds.length === 0],
    ['汇总包含覆盖矩阵', /覆盖矩阵/.test(summary)],
    ['汇总包含覆盖缺口或待确认项', /(覆盖缺口|待确认项)/.test(summary)],
  ];
  const score = checks.filter(([, ok]) => ok).length / checks.length;
  return {
    pass: score >= 0.90,
    score,
    reason: checks.map(([name, ok]) => `${ok ? 'PASS' : 'FAIL'} ${name}`).join('；'),
    componentResults: checks.map(([name, ok]) => ({ pass: ok, score: ok ? 1 : 0, reason: name })),
  };
};
