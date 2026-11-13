#!/usr/bin/env node
// Renders the cards of a JMeter HTML dashboard report (jmeter -g/-e -o) to PNG files.
// Data is read as JSON from content/js/dashboard.js and graph.js; the report's JS is never executed.
import fs from 'node:fs';
import path from 'node:path';
import { createCanvas } from 'canvas';
import { ChartJSNodeCanvas } from 'chartjs-node-canvas';

const USAGE = `Usage: node render-cards.mjs <report-dir | report/index.html> [--out <dir>] [--only <card,...>] [--list]

  --out   Directory to write PNGs to (default: current directory)
  --only  Comma-separated card names to render (see --list)
  --list  Print the cards found in the report and exit`;

const PALETTE = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'];
const CHART_SIZE = { width: 1400, height: 700 };

const TABLE_CARDS = {
  apdexTable: { name: 'apdex', title: 'APDEX (Application Performance Index)', format: formatApdex },
  statisticsTable: { name: 'statistics', title: 'Statistics', format: formatStatistics, groupHeader: statisticsGroupHeader },
  errorsTable: { name: 'errors', title: 'Errors', format: formatErrors },
  top5ErrorsBySamplerTable: { name: 'top-5-errors-by-sampler', title: 'Top 5 Errors by sampler', format: (_, v) => v },
};

function parseArgs(argv) {
  const args = { out: process.cwd(), only: null, list: false, report: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--out') args.out = argv[++i];
    else if (a === '--only') args.only = new Set(argv[++i].split(',').map((s) => s.trim()).filter(Boolean));
    else if (a === '--list') args.list = true;
    else if (a === '-h' || a === '--help') { console.log(USAGE); process.exit(0); }
    else if (!args.report) args.report = a;
    else fail(`Unexpected argument: ${a}`);
  }
  if (!args.report) fail(USAGE);
  return args;
}

function fail(message) {
  console.error(message);
  process.exit(1);
}

function resolveReport(input) {
  const stat = fs.statSync(input, { throwIfNoEntry: false });
  if (!stat) fail(`Report not found: ${input}`);
  const dir = stat.isDirectory() ? input : path.dirname(input);
  const jsDir = path.join(dir, 'content', 'js');
  const dashboard = path.join(jsDir, 'dashboard.js');
  if (!fs.existsSync(dashboard)) {
    fail(`Not a JMeter dashboard report: ${dashboard} is missing.\nPass the folder produced by "jmeter -g results.jtl -o <dir>" (or its index.html).`);
  }
  const graph = path.join(jsDir, 'graph.js');
  const index = path.join(dir, 'index.html');
  return {
    dashboard: fs.readFileSync(dashboard, 'utf8'),
    graph: fs.existsSync(graph) ? fs.readFileSync(graph, 'utf8') : '',
    index: fs.existsSync(index) ? fs.readFileSync(index, 'utf8') : '',
  };
}

// Reads the JSON object literal that starts at `from` (after optional whitespace).
function readJsonObject(src, from) {
  let i = from;
  while (/\s/.test(src[i])) i++;
  if (src[i] !== '{') return null;
  let depth = 0;
  let inString = false;
  for (let j = i; j < src.length; j++) {
    const ch = src[j];
    if (inString) {
      if (ch === '\\') j++;
      else if (ch === '"') inString = false;
    } else if (ch === '"') inString = true;
    else if (ch === '{' || ch === '[') depth++;
    else if (ch === '}' || ch === ']') {
      depth--;
      if (depth === 0) return JSON.parse(src.slice(i, j + 1));
    }
  }
  return null;
}

function extractDashboard(src) {
  const summaryMatch = /var\s+data\s*=\s*(?=\{)/.exec(src);
  const requestsSummary = summaryMatch ? readJsonObject(src, summaryMatch.index + summaryMatch[0].length) : null;

  const tables = {};
  const tableRe = /createTable\(\s*\$\(\s*["']#(\w+)["']\s*\)\s*,/g;
  for (let m; (m = tableRe.exec(src)); ) {
    const info = readJsonObject(src, tableRe.lastIndex);
    if (info?.titles) tables[m[1]] = info;
  }
  return { requestsSummary, tables };
}

function extractGraphs(src) {
  const graphs = {};
  const graphRe = /var\s+(\w+)Infos\s*=\s*\{\s*data\s*:/g;
  const matches = [...src.matchAll(graphRe)];
  matches.forEach((m, i) => {
    const data = readJsonObject(src, m.index + m[0].length);
    if (!data?.result?.series?.length) return;
    // getOptions() declares the x axis then the y axis; computed labels (e.g. elapsed time) stay null.
    const block = src.slice(m.index, matches[i + 1]?.index ?? src.length);
    const labels = [...block.matchAll(/axisLabel\s*:\s*(?:"([^"]*)"|[^,\n]+)/g)].map((l) => l[1] ?? null);
    // JMeter shifts over-time series by the generating machine's UTC offset and the dashboard displays them as UTC.
    const offset = /fixTimeStamps\([^,]+,\s*(-?\d+)\s*\)/.exec(block);
    graphs[m[1]] = {
      ...data.result,
      axisLabels: { x: labels[0] ?? null, y: labels[1] ?? null },
      timeOffset: offset ? Number(offset[1]) : null,
    };
  });
  return graphs;
}

function extractGeneralInfos(html) {
  const table = /<table[^>]*id=["']generalInfos["'][^>]*>([\s\S]*?)<\/table>/i.exec(html);
  if (!table) return null;
  const rows = [];
  for (const tr of table[1].matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/gi)) {
    const cells = [...tr[1].matchAll(/<t[dh][^>]*>([\s\S]*?)<\/t[dh]>/gi)].map((c) => decodeHtml(c[1].replace(/<[^>]+>/g, '')).trim());
    if (cells.length) rows.push(cells);
  }
  return rows.length ? rows : null;
}

function decodeHtml(s) {
  return s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&');
}

// Formats like the dashboard, e.g. 1500 -> "1 sec 500 ms".
function formatDuration(ms) {
  const parts = [];
  let rest = ms;
  for (const [unit, size] of [['day', 86400000], ['hour', 3600000], ['min', 60000], ['sec', 1000]]) {
    const n = Math.floor(rest / size);
    if (n > 0) parts.push(`${n} ${unit}`);
    rest -= n * size;
  }
  if (rest > 0 || parts.length === 0) parts.push(`${rest} ms`);
  return parts.join(' ');
}

const fixed = (v, d) => (typeof v === 'number' ? v.toFixed(d) : v);
const pct = (v) => (typeof v === 'number' ? `${v.toFixed(2)}%` : v);

function formatApdex(i, v) {
  if (i === 0) return fixed(v, 3);
  if (i === 1 || i === 2) return typeof v === 'number' ? formatDuration(v) : v;
  return v;
}

function formatStatistics(i, v) {
  if (i === 3) return pct(v);
  if (i === 4 || (i >= 7 && i <= 13)) return fixed(v, 2);
  return v;
}

function formatErrors(i, v) {
  return i === 2 || i === 3 ? pct(v) : v;
}

function statisticsGroupHeader(titles) {
  if (titles.length !== 14) return null;
  return [['Requests', 1], ['Executions', 3], ['Response Times (ms)', 7], ['Throughput', 1], ['Network (KB/sec)', 2]];
}

function renderTable({ title, header, rows, groupHeader, boldRows = 0 }) {
  const scale = 2;
  const pad = 10;
  const rowH = 30;
  const titleH = 50;
  const maxColW = 480;
  const font = '14px sans-serif';
  const bold = 'bold 14px sans-serif';
  const text = (v) => (v === null || v === undefined ? '' : String(v));

  const measure = createCanvas(1, 1).getContext('2d');
  measure.font = bold;
  const widths = header.map((h, c) => {
    const longest = Math.max(measure.measureText(text(h)).width, ...rows.map((r) => measure.measureText(text(r[c])).width));
    return Math.min(maxColW, Math.ceil(longest) + pad * 2);
  });
  if (groupHeader) {
    let col = 0;
    for (const [label, span] of groupHeader) {
      const spanW = widths.slice(col, col + span).reduce((a, b) => a + b, 0);
      const need = Math.ceil(measure.measureText(label).width) + pad * 2 - spanW;
      if (need > 0) widths[col + span - 1] += need;
      col += span;
    }
  }
  const tableW = widths.reduce((a, b) => a + b, 0);
  const headerRows = groupHeader ? 2 : 1;
  const width = tableW + pad * 2;
  const height = titleH + (headerRows + rows.length) * rowH + pad;

  const canvas = createCanvas(width * scale, height * scale);
  const ctx = canvas.getContext('2d');
  ctx.scale(scale, scale);
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = '#333';
  ctx.font = 'bold 18px sans-serif';
  ctx.textBaseline = 'middle';
  ctx.fillText(title, pad, titleH / 2);

  const fit = (s, maxW) => {
    if (ctx.measureText(s).width <= maxW) return s;
    while (s.length > 1 && ctx.measureText(`${s}…`).width > maxW) s = s.slice(0, -1);
    return `${s}…`;
  };
  const cell = (x, y, w, value, { fill, fontStyle, align }) => {
    ctx.fillStyle = fill;
    ctx.fillRect(x, y, w, rowH);
    ctx.strokeStyle = '#ddd';
    ctx.strokeRect(x + 0.5, y + 0.5, w, rowH);
    ctx.fillStyle = '#333';
    ctx.font = fontStyle;
    const s = fit(text(value), w - pad * 2);
    ctx.textAlign = align;
    const tx = align === 'right' ? x + w - pad : align === 'center' ? x + w / 2 : x + pad;
    ctx.fillText(s, tx, y + rowH / 2);
  };

  let y = titleH;
  if (groupHeader) {
    let x = pad;
    let col = 0;
    for (const [label, span] of groupHeader) {
      const w = widths.slice(col, col + span).reduce((a, b) => a + b, 0);
      cell(x, y, w, label, { fill: '#e8e8e8', fontStyle: bold, align: 'center' });
      x += w;
      col += span;
    }
    y += rowH;
  }
  let x = pad;
  header.forEach((h, c) => {
    cell(x, y, widths[c], h, { fill: '#f0f0f0', fontStyle: bold, align: 'center' });
    x += widths[c];
  });
  y += rowH;
  rows.forEach((row, r) => {
    x = pad;
    const isBold = r < boldRows;
    const fill = isBold ? '#f7f7f7' : r % 2 ? '#fafafa' : '#fff';
    header.forEach((_, c) => {
      const v = row[c];
      const numeric = typeof v === 'number' || /^-?[\d.,]+%?$/.test(text(v));
      cell(x, y, widths[c], v, { fill, fontStyle: isBold ? bold : font, align: numeric ? 'right' : 'left' });
      x += widths[c];
    });
    y += rowH;
  });
  return canvas.toBuffer('image/png');
}

function tableCard(info, spec) {
  const format = (row) => row.map((v, i) => (v === null ? '' : spec.format(i, v)));
  const rows = [];
  if (info.overall?.data?.length) rows.push(format(info.overall.data));
  for (const item of info.items ?? []) if (item.data?.length) rows.push(format(item.data));
  return renderTable({
    title: spec.title,
    header: info.titles,
    rows,
    groupHeader: spec.groupHeader?.(info.titles),
    boldRows: info.overall?.data?.length ? 1 : 0,
  });
}

const kebab = (s) => s.replace(/([a-z0-9])([A-Z])/g, '$1-$2').replace(/[^a-zA-Z0-9]+/g, '-').toLowerCase().replace(/^-|-$/g, '');
const humanize = (s) => s.replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/^./, (c) => c.toUpperCase());
const colorAt = (i, series) => series.color ?? PALETTE[i % PALETTE.length];
const formatTime = (ms, offset) =>
  offset == null ? new Date(ms).toLocaleTimeString('en-GB') : new Date(ms + offset).toLocaleTimeString('en-GB', { timeZone: 'UTC' });
const TIME_STEPS = [1, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 10800, 21600, 43200, 86400].map((s) => s * 1000);

function utcOffsetLabel(offset) {
  const minutes = offset == null ? -new Date().getTimezoneOffset() : Math.round(offset / 60000);
  const abs = Math.abs(minutes);
  return `UTC${minutes < 0 ? '-' : '+'}${String(Math.floor(abs / 60)).padStart(2, '0')}:${String(abs % 60).padStart(2, '0')}`;
}

function timeAxis(series, offset) {
  const xs = series.flatMap((s) => s.data.map(([x]) => x));
  const min = Math.min(...xs);
  const max = Math.max(...xs);
  const stepSize = TIME_STEPS.find((step) => (max - min) / step <= 12) ?? TIME_STEPS.at(-1);
  return { min, max, ticks: { stepSize, callback: (v) => formatTime(v, offset) } };
}

function elapsedTimeLabel(granularity, offset) {
  const parts = [typeof granularity === 'number' ? `granularity: ${formatDuration(granularity)}` : null, utcOffsetLabel(offset)];
  return `Elapsed Time (${parts.filter(Boolean).join(', ')})`;
}

function axisTitle(text) {
  return text ? { display: true, text } : { display: false };
}

function chartConfig(key, result) {
  const title = result.title ?? humanize(key);
  const plugins = { title: { display: true, text: title, font: { size: 20 } }, legend: { position: 'bottom' } };
  const { x: xLabel, y: yLabel } = result.axisLabels ?? {};

  if (key === 'syntheticResponseTimeDistribution' && result.ticks) {
    const ticks = result.ticks.map(([pos, label]) => [pos, String(label).replace(/\s+/g, ' ')]);
    return {
      type: 'bar',
      data: {
        labels: ticks.map(([, label]) => label),
        datasets: result.series.map((s, i) => ({
          label: String(s.label).replace(/\s+/g, ' '),
          data: ticks.map(([pos]) => s.data.find(([x]) => x === pos)?.[1] ?? null),
          backgroundColor: colorAt(i, s),
          skipNull: true,
        })),
      },
      options: { plugins, scales: { x: { stacked: true, title: axisTitle(xLabel) }, y: { stacked: true, title: axisTitle(yLabel ?? 'Number of responses') } } },
    };
  }

  if (key === 'responseTimeDistribution') {
    const xs = [...new Set(result.series.flatMap((s) => s.data.map(([x]) => x)))].sort((a, b) => a - b);
    return {
      type: 'bar',
      data: {
        labels: xs.map((x) => `${x} ms`),
        datasets: result.series.map((s, i) => ({
          label: s.label,
          data: xs.map((x) => s.data.find(([dx]) => dx === x)?.[1] ?? 0),
          backgroundColor: colorAt(i, s),
        })),
      },
      options: { plugins, scales: { x: { title: axisTitle(xLabel) }, y: { title: axisTitle(yLabel ?? 'Number of responses') } } },
    };
  }

  const firstX = result.series[0]?.data?.[0]?.[0];
  const isTime = typeof firstX === 'number' && firstX > 1e11;
  const isScatter = /VsRequest$/.test(key);
  return {
    type: 'scatter',
    data: {
      datasets: result.series.map((s, i) => ({
        label: s.label,
        data: s.data.map(([x, y]) => ({ x, y })).sort((a, b) => (isScatter ? 0 : a.x - b.x)),
        borderColor: colorAt(i, s),
        backgroundColor: colorAt(i, s),
        showLine: !isScatter,
        pointRadius: isScatter ? 4 : 2,
        borderWidth: 2,
      })),
    },
    options: {
      plugins,
      scales: {
        x: {
          type: 'linear',
          ...(isTime ? timeAxis(result.series, result.timeOffset) : {}),
          title: axisTitle(isTime ? elapsedTimeLabel(result.granularity, result.timeOffset) : xLabel ?? (key === 'responseTimePercentiles' ? 'Percentiles' : '')),
        },
        y: { beginAtZero: true, title: axisTitle(yLabel) },
      },
    },
  };
}

function pieConfig(summary) {
  const slices = [['PASS', summary.OkPercent, '#9ACD32'], ['FAIL', summary.KoPercent, '#FF6347']];
  return {
    type: 'pie',
    data: {
      labels: slices.map(([label, v]) => `${label} (${Number(v).toFixed(2)}%)`),
      datasets: [{ data: slices.map(([, v]) => v), backgroundColor: slices.map(([, , c]) => c) }],
    },
    options: { plugins: { title: { display: true, text: 'Requests Summary', font: { size: 20 } }, legend: { position: 'bottom' } } },
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const report = resolveReport(args.report);
  const { requestsSummary, tables } = extractDashboard(report.dashboard);
  const graphs = extractGraphs(report.graph);
  const generalInfos = extractGeneralInfos(report.index);

  const chartCanvas = new ChartJSNodeCanvas({ ...CHART_SIZE, backgroundColour: 'white' });
  const pieCanvas = new ChartJSNodeCanvas({ width: 800, height: 700, backgroundColour: 'white' });

  const cards = [];
  if (generalInfos) {
    cards.push({ name: 'test-and-report-information', render: () => renderTable({ title: 'Test and Report information', header: ['Property', 'Value'], rows: generalInfos }) });
  }
  if (requestsSummary && 'OkPercent' in requestsSummary) {
    cards.push({ name: 'requests-summary', render: () => pieCanvas.renderToBuffer(pieConfig(requestsSummary)) });
  }
  for (const [id, spec] of Object.entries(TABLE_CARDS)) {
    if (tables[id]) cards.push({ name: spec.name, render: () => tableCard(tables[id], spec) });
  }
  for (const [key, result] of Object.entries(graphs)) {
    cards.push({ name: kebab(key), render: () => chartCanvas.renderToBuffer(chartConfig(key, result)) });
  }

  if (args.list) {
    for (const c of cards) console.log(c.name);
    return;
  }
  if (args.only) {
    const unknown = [...args.only].filter((n) => !cards.some((c) => c.name === n));
    if (unknown.length) fail(`Unknown card(s): ${unknown.join(', ')}. Run with --list to see available cards.`);
  }

  fs.mkdirSync(args.out, { recursive: true });
  for (const card of cards) {
    if (args.only && !args.only.has(card.name)) continue;
    const file = path.join(args.out, `jmeter-${card.name}.png`);
    fs.writeFileSync(file, await card.render());
    console.log(file);
  }
}

main().catch((err) => fail(err.stack ?? String(err)));
