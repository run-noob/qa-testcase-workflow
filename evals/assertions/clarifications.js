const { golden, artifacts, weightedMatch } = require('./helpers');

module.exports = (output) => {
  const text = artifacts(output).clarifications?.content || '';
  const matched = weightedMatch(text, golden.requiredClarifications);
  return {
    pass: matched.score >= 0.75,
    score: matched.score,
    reason: `必需澄清项命中 ${matched.earned}/${matched.total}`,
    componentResults: matched.componentResults,
  };
};
