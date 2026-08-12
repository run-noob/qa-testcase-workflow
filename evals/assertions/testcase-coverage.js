const { golden, allTestCaseText, weightedMatch } = require('./helpers');

module.exports = (output) => {
  const matched = weightedMatch(allTestCaseText(output), golden.coverageUnits);
  return {
    pass: matched.score >= 0.90,
    score: matched.score,
    reason: `用例覆盖单元加权命中 ${matched.earned}/${matched.total}`,
    componentResults: matched.componentResults,
  };
};
