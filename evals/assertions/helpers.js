const golden = require('../goldens/coupon.json');

function parseOutput(output) {
  if (typeof output === 'string') {
    try {
      return JSON.parse(output);
    } catch (error) {
      return { run: { exitCode: -1, error: `无法解析 provider 输出: ${error.message}` }, artifacts: {} };
    }
  }
  return output || { run: { exitCode: -1, error: 'provider 输出为空' }, artifacts: {} };
}

function regexMatches(text, patterns) {
  return patterns.some((pattern) => new RegExp(pattern, 'is').test(text));
}

function weightedMatch(text, items) {
  const componentResults = [];
  let earned = 0;
  let total = 0;

  for (const item of items) {
    const matched = regexMatches(text, item.patterns);
    total += item.weight || 1;
    if (matched) earned += item.weight || 1;
    componentResults.push({
      pass: matched,
      score: matched ? 1 : 0,
      reason: `${item.id}: ${item.description}`,
    });
  }

  return {
    score: total ? earned / total : 0,
    componentResults,
    earned,
    total,
  };
}

function artifacts(output) {
  return parseOutput(output).artifacts || {};
}

function allTestCaseText(output) {
  return (artifacts(output).testCases || []).map((item) => item.content || '').join('\n\n');
}

function allArtifactText(output) {
  const data = artifacts(output);
  return [
    data.analysis?.content,
    data.clarifications?.content,
    data.progress?.content,
    data.summary?.content,
    ...(data.testCases || []).map((item) => item.content),
  ]
    .filter(Boolean)
    .join('\n\n');
}

function result(score, reason, componentResults = []) {
  return {
    pass: score >= 0.999999,
    score,
    reason,
    componentResults,
  };
}

module.exports = {
  golden,
  parseOutput,
  regexMatches,
  weightedMatch,
  artifacts,
  allTestCaseText,
  allArtifactText,
  result,
};
