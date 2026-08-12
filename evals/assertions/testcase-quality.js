const { artifacts } = require('./helpers');

function extractCases(text) {
  return text
    .split(/(?=^###\s+)/m)
    .filter((section) => /^###\s+/m.test(section) && /用例编号/.test(section));
}

module.exports = (output) => {
  const files = artifacts(output).testCases || [];
  const cases = files.flatMap((file) => extractCases(file.content || ''));
  if (!cases.length) {
    return { pass: false, score: 0, reason: '未解析到测试用例' };
  }

  const ids = [];
  const componentResults = [];
  for (const [index, item] of cases.entries()) {
    const id = item.match(/用例编号\*{0,2}\s*[:：]\s*([^\s]+)/)?.[1] || '';
    if (id) ids.push(id);
    const checks = [
      ['编号', Boolean(id)],
      ['类型', /用例类型\*{0,2}\s*[:：]/.test(item)],
      ['优先级', /优先级\*{0,2}\s*[:：]\s*P[0-3]/.test(item)],
      ['前置条件', /前置条件\*{0,2}\s*[:：]/.test(item)],
      ['步骤表', /\|\s*步骤\s*\|\s*操作\s*\|\s*预期结果\s*\|/.test(item)],
      ['测试数据', /测试数据\*{0,2}\s*[:：]/.test(item)],
      ['至少两个步骤', (item.match(/^\s*\|\s*\d+\s*\|/gm) || []).length >= 2],
      ['预期非空泛', !/预期结果[^\n]*(正常|符合预期)[。\s|]*$/m.test(item)],
    ];
    const score = checks.filter(([, ok]) => ok).length / checks.length;
    componentResults.push({
      pass: score === 1,
      score,
      reason: `用例 ${id || index + 1}: ${checks.filter(([, ok]) => !ok).map(([name]) => name).join('、') || '结构完整'}`,
    });
  }

  const duplicateIds = ids.filter((id, index) => ids.indexOf(id) !== index);
  const uniqueScore = duplicateIds.length ? 0 : 1;
  componentResults.push({
    pass: uniqueScore === 1,
    score: uniqueScore,
    reason: duplicateIds.length ? `重复用例编号: ${[...new Set(duplicateIds)].join(', ')}` : '用例编号唯一',
  });

  const score = componentResults.reduce((sum, item) => sum + item.score, 0) / componentResults.length;
  return {
    pass: score >= 0.90,
    score,
    reason: `解析 ${cases.length} 条用例，结构质量 ${(score * 100).toFixed(1)}%`,
    componentResults,
  };
};
