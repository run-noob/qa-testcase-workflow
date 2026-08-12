const { golden, allArtifactText, regexMatches } = require('./helpers');

module.exports = (output) => {
  const text = allArtifactText(output);
  const violations = golden.forbiddenClaims.filter((item) => regexMatches(text, item.patterns));
  const score = violations.length === 0 ? 1 : 0;
  return {
    pass: score === 1,
    score,
    reason: violations.length
      ? `发现严重无依据结论：${violations.map((item) => `${item.id} ${item.description}`).join('；')}`
      : '未发现严重无依据结论',
    componentResults: golden.forbiddenClaims.map((item) => {
      const violated = violations.some((entry) => entry.id === item.id);
      return { pass: !violated, score: violated ? 0 : 1, reason: `${item.id}: ${item.description}` };
    }),
  };
};
