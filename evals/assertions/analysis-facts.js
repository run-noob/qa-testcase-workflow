const { golden, artifacts, weightedMatch } = require('./helpers');

module.exports = (output) => {
  const text = artifacts(output).analysis?.content || '';
  const matched = weightedMatch(text, golden.coreFacts);
  return {
    pass: matched.score >= 0.95,
    score: matched.score,
    reason: `核心事实加权命中 ${matched.earned}/${matched.total}`,
    componentResults: matched.componentResults,
  };
};
