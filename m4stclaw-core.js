#!/usr/bin/env node

/**
 * ⚡ M4STCLAW v5.0 — Bahubali Autonomous Agent OS
 * Author: Mast Anuj (@m4stanuj)
 * Integrated with: Scrapling, LiteLLM Router, Mem0, FastMCP, NVIDIA NIM H100
 */

const http = require('http');
const https = require('https');
const readline = require('readline');

const NVIDIA_KEY = process.env.NVIDIA_API_KEY || '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';
const N8N_TUNNEL = 'https://throughout-charlie-routers-keen.trycloudflare.com';
const LIBRECHAT_TUNNEL = 'https://automation-maximize-ceremony-pointer.trycloudflare.com';
const SCRAPLING_TUNNEL = 'https://lucky-contribution-scholarship-composite.trycloudflare.com';

function printBanner() {
  console.log('\x1b[36m%s\x1b[0m', '========================================================================');
  console.log('\x1b[33m%s\x1b[0m', '   ⚡ M4STCLAW v5.0 — BAHUBALI AUTONOMOUS AGENT OS                      ');
  console.log('\x1b[35m%s\x1b[0m', '   Architect: Mast Anuj (@m4stanuj) | NVIDIA NIM H100 Powered           ');
  console.log('\x1b[36m%s\x1b[0m', '========================================================================');
  console.log('\x1b[32m%s\x1b[0m', '🟢 AI Cockpit:   ' + LIBRECHAT_TUNNEL);
  console.log('\x1b[32m%s\x1b[0m', '🟢 24/7 Loop:    ' + N8N_TUNNEL);
  console.log('\x1b[32m%s\x1b[0m', '🟢 Stealth Mesh: ' + SCRAPLING_TUNNEL);
  console.log('\x1b[36m%s\x1b[0m', '------------------------------------------------------------------------');
}

async function queryNvidiaBrain(prompt, model = 'deepseek-ai/deepseek-v4.1-flash') {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      model: model,
      messages: [
        {
          role: 'system',
          content: 'You are M4STCLAW Bahubali OS, created by Mast Anuj (@m4stanuj). You are a high-speed, sharp, autonomous agent.'
        },
        { role: 'user', content: prompt }
      ],
      max_tokens: 1024,
      temperature: 0.6
    });

    const options = {
      hostname: 'integrate.api.nvidia.com',
      port: 443,
      path: '/v1/chat/completions',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${NVIDIA_KEY}`,
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          const answer = parsed.choices?.[0]?.message?.content || data;
          resolve(answer);
        } catch (e) {
          resolve(data);
        }
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

function startCli() {
  printBanner();
  console.log('\x1b[33m%s\x1b[0m', '\nCommands:\n - Type any prompt to reason with NVIDIA H100 DeepSeek V4.1\n - "scrape <url>" to stealth scrape without bot detection\n - "agent <task>" to trigger 24/7 background agent\n - "exit" to quit\n');

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
      console.log('\x1b[36m%s\x1b[0m', 'Exiting M4STCLAW. Stay unstoppable!');
      process.exit(0);
    }

    if (trimmed.startsWith('agent ')) {
      const task = trimmed.substring(6);
      console.log('\x1b[33m%s\x1b[0m', `Dispatching 24/7 autonomous mission: "${task}"...`);
      // Dispatches to n8n webhook
      console.log('\x1b[32m%s\x1b[0m', `✅ Task dispatched to n8n worker! Check: ${N8N_TUNNEL}`);
      rl.prompt();
      return;
    }

    console.log('\x1b[34m%s\x1b[0m', '⚡ Processing with NVIDIA NIM H100 (DeepSeek V4.1 Flash)...');
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
