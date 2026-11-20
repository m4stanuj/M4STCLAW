#!/usr/bin/env node

/**
 * ⚡ M4STCLAW v5.0 — Bahubali Autonomous Agent OS
 * Author: Mast Anuj (@m4stanuj)
 * Integrated with: Scrapling, LiteLLM Router, Mem0, FastMCP, NVIDIA NIM H100
 */

const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const readline = require('readline');

function getSecret(keyName) {
  if (process.env[keyName]) return process.env[keyName];
  const candidates = [
    path.join(process.cwd(), '.env'),
    path.join(__dirname, '.env'),
    path.join(process.env.USERPROFILE || '', '.m4stclaw', '.env')
  ];
  for (const envPath of candidates) {
    try {
      if (fs.existsSync(envPath)) {
        const lines = fs.readFileSync(envPath, 'utf8').split('\n');
        for (const line of lines) {
          const match = line.match(new RegExp(`^${keyName}=(.*)$`));
          if (match) return match[1].trim().replace(/^['"]|['"]$/g, '');
        }
      }
    } catch (_) {}
  }
  return '';
}

const NVIDIA_KEY = getSecret('NVIDIA_API_KEY');
const N8N_TUNNEL = process.env.N8N_TUNNEL || '(not configured)';
const LIBRECHAT_TUNNEL = process.env.LIBRECHAT_TUNNEL || '(not configured)';
const SCRAPLING_TUNNEL = process.env.SCRAPLING_TUNNEL || '(not configured)';
const LOCAL_BRIDGE = process.env.LOCAL_BRIDGE || 'http://127.0.0.1:3090';

let currentModel = 'deepseek-ai/deepseek-v4.1-flash';

function printBanner() {
  console.log('\x1b[36m%s\x1b[0m', '========================================================================');
  console.log('\x1b[33m%s\x1b[0m', '   ⚡ M4STCLAW v5.0 — BAHUBALI AUTONOMOUS AGENT OS                      ');
  console.log('\x1b[35m%s\x1b[0m', '   Architect: Mast Anuj (@m4stanuj) | NVIDIA NIM H100 Enterprise        ');
  console.log('\x1b[36m%s\x1b[0m', '========================================================================');
  console.log('\x1b[32m%s\x1b[0m', '🟢 AI Cockpit:   ' + LIBRECHAT_TUNNEL);
  console.log('\x1b[32m%s\x1b[0m', '🟢 24/7 Engine:  ' + N8N_TUNNEL);
  console.log('\x1b[32m%s\x1b[0m', '🟢 Stealth Mesh: ' + SCRAPLING_TUNNEL);
  console.log('\x1b[36m%s\x1b[0m', '------------------------------------------------------------------------');
}

function queryHttp(url, options = {}) {
  return new Promise((resolve, reject) => {
    const isHttps = url.startsWith('https://');
    const lib = isHttps ? https : http;
    const req = lib.request(url, options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, data }));
    });
    req.on('error', reject);
    if (options.body) req.write(options.body);
    req.end();
  });
}

async function queryNvidiaBrain(prompt, model = currentModel) {
  const postData = JSON.stringify({
    model: model,
    messages: [
      {
        role: 'system',
        content: 'You are M4STCLAW Bahubali OS, created by Mast Anuj (@m4stanuj). You are an elite autonomous agent engineer. Give direct, sharp, high-intelligence responses.'
      },
      { role: 'user', content: prompt }
    ],
    max_tokens: 1024,
    temperature: 0.6
  });

  const res = await queryHttp('https://integrate.api.nvidia.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${NVIDIA_KEY}`,
      'Content-Length': Buffer.byteLength(postData)
    },
    body: postData
  });

  try {
    const parsed = JSON.parse(res.data);
    const answer = parsed.choices?.[0]?.message?.content || parsed.choices?.[0]?.message?.reasoning_content || res.data;
    return answer;
  } catch (e) {
    return res.data;
  }
}

async function runStealthSearch(query) {
  try {
    const res = await queryHttp(`${LOCAL_BRIDGE}/api/search?q=${encodeURIComponent(query)}`);
    const parsed = JSON.parse(res.data);
    if (parsed.results && parsed.results.length > 0) {
      console.log('\x1b[33m%s\x1b[0m', `\nFound ${parsed.results.length} live results for "${query}":`);
      parsed.results.forEach((r, idx) => {
        console.log(`\x1b[36m[${idx + 1}] ${r.title}\x1b[0m`);
        console.log(`    Link: ${r.link}`);
        console.log(`    ${r.snippet}\n`);
      });
    } else {
      console.log('\x1b[31m%s\x1b[0m', 'No results found or search bridge unreachable.');
    }
  } catch (e) {
    console.log('\x1b[31m%s\x1b[0m', `Search error: ${e.message}`);
  }
}

async function runStealthScrape(url) {
  try {
    console.log('\x1b[34m%s\x1b[0m', `Stealth scraping ${url} (bypassing anti-bot)...`);
    const payload = JSON.stringify({ targetUrl: url });
    const res = await queryHttp(`${LOCAL_BRIDGE}/api/scrape`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) },
      body: payload
    });
    const parsed = JSON.parse(res.data);
    if (parsed.markdown) {
      console.log('\x1b[32m%s\x1b[0m', `\n--- [Title: ${parsed.title || 'Untitled'}] ---`);
      console.log(parsed.markdown.slice(0, 1500));
      if (parsed.markdown.length > 1500) console.log('\n...[Content truncated for display]');
    } else {
      console.log('\x1b[31m%s\x1b[0m', `Scrape returned no content: ${res.data}`);
    }
  } catch (e) {
    console.log('\x1b[31m%s\x1b[0m', `Scrape error: ${e.message}`);
  }
}

function startCli() {
  printBanner();
  console.log('\x1b[33m%s\x1b[0m', 'Active Model: ' + currentModel);
  console.log('\x1b[37m%s\x1b[0m', 'Commands:');
  console.log(' - Type any prompt to reason with NVIDIA NIM H100');
  console.log(' - "search <query>"       -> Zero-cost live stealth web search');
  console.log(' - "scrape <url>"         -> Stealth scrape webpage to Markdown');
  console.log(' - "agent <mission>"      -> Dispatch 24/7 background agent to n8n');
  console.log(' - "model <vision|flash>" -> Switch between Vision and Reasoning brain');
  console.log(' - "exit"                 -> Quit M4STCLAW\n');

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: '\x1b[35mM4STCLAW>\x1b[0m '
  });

  rl.prompt();

  rl.on('line', async (line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      rl.prompt();
      return;
    }

    if (trimmed === 'exit' || trimmed === 'quit') {
      console.log('\x1b[36m%s\x1b[0m', 'M4STCLAW Offline. Stay unstoppable!');
      process.exit(0);
    }

    if (trimmed.startsWith('model ')) {
      const choice = trimmed.substring(6).trim().toLowerCase();
      if (choice === 'vision') {
        currentModel = 'meta/llama-3.2-11b-vision-instruct';
      } else {
        currentModel = 'deepseek-ai/deepseek-v4.1-flash';
      }
      console.log('\x1b[32m%s\x1b[0m', `Switched active brain to: ${currentModel}`);
      rl.prompt();
      return;
    }

    if (trimmed.startsWith('search ')) {
      const q = trimmed.substring(7);
      await runStealthSearch(q);
      rl.prompt();
      return;
    }

    if (trimmed.startsWith('scrape ')) {
      const u = trimmed.substring(7);
      await runStealthScrape(u);
      rl.prompt();
      return;
    }

    if (trimmed.startsWith('agent ')) {
      const task = trimmed.substring(6);
      console.log('\x1b[33m%s\x1b[0m', `Dispatching 24/7 autonomous mission: "${task}"...`);
      try {
        const payload = JSON.stringify({ source: 'M4STCLAW Binary', mission: task });
        await queryHttp(`${LOCAL_BRIDGE}/api/trigger-agent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) },
          body: payload
        });
        console.log('\x1b[32m%s\x1b[0m', `✅ Mission dispatched to n8n worker! Check: ${N8N_TUNNEL}`);
      } catch (e) {
        console.log('\x1b[31m%s\x1b[0m', `Failed to dispatch: ${e.message}`);
      }
      rl.prompt();
      return;
    }

    console.log('\x1b[34m%s\x1b[0m', `⚡ Reasoning with NVIDIA NIM H100 (${currentModel})...`);
    try {
      const reply = await queryNvidiaBrain(trimmed);
      console.log('\n\x1b[32m%s\x1b[0m\n', reply);
    } catch (err) {
      console.log('\x1b[31m%s\x1b[0m', `Error: ${err.message}`);
    }

    rl.prompt();
  });
}

startCli();
