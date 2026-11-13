// Generates a realistic JMeter CSV results file (10 min run, ramp to 50 threads).
// Usage: node generate-sample-jtl.mjs [out.jtl]
import fs from 'node:fs';

const outFile = process.argv[2] ?? 'results.jtl';

let seed = 42;
const rand = () => ((seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296);
const gauss = () => Math.sqrt(-2 * Math.log(rand() || 1e-9)) * Math.cos(2 * Math.PI * rand());

const start = Date.UTC(2025, 10, 3, 1, 0, 0);
const durationMs = 10 * 60 * 1000;
const rampMs = 4 * 60 * 1000;
const maxThreads = 50;

const steps = [
  { label: 'Login', url: 'https://shop.example.test/api/login', median: 210, sigma: 0.45, bytes: 1720, sent: 440, errors: [['401', 'Unauthorized', 0.005]] },
  { label: 'Search Products', url: 'https://shop.example.test/api/search?q=phone', median: 350, sigma: 0.5, bytes: 5560, sent: 310, errors: [['500', 'Internal Server Error', 0.005], ['timeout', '', 0.002]] },
  { label: 'View Product', url: 'https://shop.example.test/api/products/1042', median: 165, sigma: 0.4, bytes: 3970, sent: 295, errors: [['500', 'Internal Server Error', 0.001]] },
  { label: 'Add to Cart', url: 'https://shop.example.test/api/cart', median: 260, sigma: 0.45, bytes: 840, sent: 545, errors: [['500', 'Internal Server Error', 0.004], ['timeout', '', 0.003]] },
  { label: 'Checkout', url: 'https://shop.example.test/api/checkout', median: 700, sigma: 0.55, bytes: 1620, sent: 770, errors: [['500', 'Internal Server Error', 0.007], ['503', 'Service Unavailable', 0.007], ['timeout', '', 0.011]] },
];
// Per-iteration flow: login, 2x search, 2x view, add to cart, and checkout on every other iteration.
const flow = [0, 1, 2, 1, 2, 3];

const header = 'timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect';
const rows = [];
const activeAt = (t) => Math.min(maxThreads, Math.max(1, Math.ceil(((t - start) / rampMs) * maxThreads)));

for (let thread = 1; thread <= maxThreads; thread++) {
  let t = start + ((thread - 1) / maxThreads) * rampMs;
  let iteration = 0;
  while (t < start + durationMs) {
    const order = iteration % 2 === 0 ? [...flow, 4] : flow;
    for (const idx of order) {
      if (t >= start + durationMs) break;
      const step = steps[idx];
      const load = activeAt(t) / maxThreads;
      let elapsed = Math.round(step.median * (0.7 + 0.45 * load) * Math.exp(step.sigma * gauss()));
      let code = '200', message = 'OK', success = 'true', failure = '', bytes = Math.round(step.bytes * (0.95 + rand() * 0.1));
      const r = rand();
      let acc = 0;
      for (const [errCode, errMsg, p] of step.errors) {
        acc += p * (0.5 + load);
        if (r < acc) {
          success = 'false';
          if (errCode === 'timeout') {
            code = 'Non HTTP response code: java.net.SocketTimeoutException';
            message = 'Non HTTP response message: Read timed out';
            elapsed = 5000 + Math.round(rand() * 20);
            bytes = 0;
          } else {
            code = errCode;
            message = errMsg;
            failure = `Test failed: code expected to equal /200/`;
          }
          break;
        }
      }
      const connect = rand() < 0.1 ? Math.round(20 + rand() * 40) : 0;
      const latency = Math.max(0, elapsed - Math.round(rand() * 15));
      const all = activeAt(t);
      rows.push([Math.round(t), elapsed, step.label, code, message, `Thread Group 1-${thread}`, 'text', success, failure, bytes, step.sent, all, all, step.url, latency, 0, connect].join(','));
      t += elapsed + 500 + rand() * 1500;
    }
    iteration++;
  }
}

rows.sort((a, b) => Number(a.split(',')[0]) - Number(b.split(',')[0]));
fs.writeFileSync(outFile, [header, ...rows].join('\n') + '\n');
console.log(`${rows.length} samples -> ${outFile}`);
