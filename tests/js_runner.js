// Runs the demo's core (docs/app.js) under Node on fixture files and prints
// JSON: [{file, issues, offers, compare}] so tests/test_parity.py can compare
// it with Python. Usage: node tests/js_runner.js path/to/app.js fixture.json...
'use strict';
const fs = require('fs');
const core = require(require('path').resolve(process.argv[2]));
const out = { tables: core.TABLES, presets: core.PRESETS, runs: [] };
for (const file of process.argv.slice(3)) {
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  const v = core.validate(data);
  const hasErr = v.issues.some((i) => i.level === 'error');
  out.runs.push({
    file,
    issues: v.issues,
    offers: v.offers,
    compare: (!hasErr && v.offers.length) ? core.compare(v.offers) : null,
  });
}
process.stdout.write(JSON.stringify(out));
