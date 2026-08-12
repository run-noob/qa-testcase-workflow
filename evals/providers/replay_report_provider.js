const path = require('node:path');

class ReplayReportProvider {
  constructor(options = {}) {
    this.config = options.config || {};
  }

  id() {
    return 'replay-report';
  }

  async callApi() {
    const reportPath = path.resolve(
      this.config.basePath || process.cwd(),
      process.env.QA_EVAL_REPLAY_REPORT ||
        this.config.report ||
        'reports/coupon-llm-results.json',
    );
    delete require.cache[require.resolve(reportPath)];
    const report = require(reportPath);
    const resultIndex = Number(
      process.env.QA_EVAL_REPLAY_RESULT_INDEX ?? this.config.resultIndex ?? 0,
    );
    const result = report.results?.results?.[resultIndex];
    const output = result?.response?.output;

    if (!output) {
      return {
        error: `无法从报告读取 results.results[${resultIndex}].response.output: ${reportPath}`,
      };
    }

    return {
      output,
      metadata: {
        replayedFrom: reportPath,
        sourceEvalId: report.evalId,
        sourceRunDir: result.metadata?.runDir,
      },
    };
  }
}

module.exports = ReplayReportProvider;
