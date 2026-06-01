/**
 * M4STCLAW Client Application — app.js
 * =====================================
 * Handles navigation, interactive chats, API key commitments, SVG DAG rendering,
 * web audio chimes/whips, and canvas hover particle dynamics.
 * Respects strict vanilla XSS DOM injection constraints.
 */

document.addEventListener("DOMContentLoaded", () => {
    
    // ── NAVIGATION CONTROLLER ─────────────────────────────────────────
    const navButtons = {
        dashboard: document.getElementById("nav-btn-dashboard"),
        playground: document.getElementById("nav-btn-playground"),
        keys: document.getElementById("nav-btn-keys"),
        telemetry: document.getElementById("nav-btn-telemetry")
    };
    
    const views = {
        dashboard: document.getElementById("view-dashboard"),
        playground: document.getElementById("view-playground"),
        keys: document.getElementById("view-keys"),
        telemetry: document.getElementById("view-telemetry")
    };
    
    Object.keys(navButtons).forEach(key => {
        const btn = navButtons[key];
        const view = views[key];
        
        if (btn && view) {
            btn.addEventListener("click", () => {
                // Deactivate all
                Object.values(navButtons).forEach(b => b.classList.remove("active"));
                Object.values(views).forEach(v => v.classList.remove("active-view"));
                
                // Activate clicked
                btn.classList.add("active");
                view.classList.add("active-view");
                
                addLogLine("system", `Switched view to ${key.toUpperCase()}`);
            });
        }
    });

    // ── WEB AUDIO SYNTHESIZER (No asset download requirement) ────────
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    
    function playChime() {
        try {
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
            // Wholesome success sound
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            
            osc.type = "sine";
            osc.frequency.setValueAtTime(523.25, audioCtx.currentTime); // C5
            osc.frequency.exponentialRampToValueAtTime(783.99, audioCtx.currentTime + 0.15); // G5
            osc.frequency.exponentialRampToValueAtTime(1046.50, audioCtx.currentTime + 0.3); // C6
            
            gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5);
            
            osc.start();
            osc.stop(audioCtx.currentTime + 0.5);
        } catch (e) {
            console.debug("Audio play blocked", e);
        }
    }
    
    function playWhipCrack() {
        try {
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
            // Laser whip glitch crack
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            
            osc.type = "sawtooth";
            osc.frequency.setValueAtTime(800, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(80, audioCtx.currentTime + 0.12);
            
            gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.15);
            
            osc.start();
            osc.stop(audioCtx.currentTime + 0.2);
        } catch (e) {
            console.debug("Audio play blocked", e);
        }
    }

    // ── DYNAMIC PARTICLE ENGINE (Canvas Overlay) ──────────────────────
    const canvas = document.getElementById("particle-overlay-canvas");
    const ctx = canvas.getContext("2d");
    let particles = [];
    let isWhipMode = false; // default to Wand sparkles mode
    
    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();
    
    class Particle {
        constructor(x, y, color) {
            this.x = x;
            this.y = y;
            this.vx = (Math.random() - 0.5) * 3;
            this.vy = (Math.random() - 0.5) * 3 - (isWhipMode ? 0 : 1.5);
            this.size = Math.random() * 4 + 1;
            this.alpha = 1.0;
            this.color = color;
            this.decay = Math.random() * 0.02 + 0.015;
        }
        update() {
            this.x += this.vx;
            this.y += this.vy;
            this.alpha -= this.decay;
        }
        draw() {
            ctx.save();
            ctx.globalAlpha = this.alpha;
            ctx.shadowBlur = isWhipMode ? 6 : 4;
            ctx.shadowColor = this.color;
            ctx.fillStyle = this.color;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }
    }
    
    window.addEventListener("mousemove", (e) => {
        const color = isWhipMode ? "#EF4444" : "#00E5FF";
        if (Math.random() < 0.35) {
            particles.push(new Particle(e.clientX, e.clientY, color));
        }
    });
    
    window.addEventListener("click", (e) => {
        if (isWhipMode) {
            playWhipCrack();
            // Spawn aggressive sparks on click
            for (let i = 0; i < 20; i++) {
                const p = new Particle(e.clientX, e.clientY, "#EF4444");
                p.vx = (Math.random() - 0.5) * 8;
                p.vy = (Math.random() - 0.5) * 8;
                particles.push(p);
            }
            addLogLine("warning", "Whip crack triggered: Halting runaway process sequences!");
            haltActiveTask();
        } else {
            // Wand sparkles burst
            playChime();
            for (let i = 0; i < 15; i++) {
                const p = new Particle(e.clientX, e.clientY, "#00E5FF");
                p.vx = (Math.random() - 0.5) * 5;
                p.vy = (Math.random() - 0.5) * 5;
                particles.push(p);
            }
        }
    });
    
    function animateParticles() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles = particles.filter(p => {
            p.update();
            p.draw();
            return p.alpha > 0;
        });
        requestAnimationFrame(animateParticles);
    }
    animateParticles();
    
    // Theme toggle buttons hook
    const btnWand = document.getElementById("mode-btn-wand");
    const btnWhip = document.getElementById("mode-btn-whip");
    
    if (btnWand && btnWhip) {
        btnWand.addEventListener("click", () => {
            btnWand.classList.add("active");
            btnWhip.classList.remove("active");
            isWhipMode = false;
            addLogLine("system", "Magic Wand mode enabled. Sparkles and chimes ready.");
        });
        btnWhip.addEventListener("click", () => {
            btnWhip.classList.add("active");
            btnWand.classList.remove("active");
            isWhipMode = true;
            addLogLine("warning", "Laser Whip mode activated. Clicking anywhere cracks the whip and aborts processes.");
        });
    }

    // ── TERMINAL LOG CONSOLE ──────────────────────────────────────────
    const terminalOutput = document.getElementById("log-terminal-output");
    const btnClearLogs = document.getElementById("btn-clear-logs");
    
    function addLogLine(type, text) {
        if (!terminalOutput) return;
        const line = document.createElement("div");
        line.classList.add("log-line", type);
        
        const timestamp = new Date().toLocaleTimeString();
        line.textContent = `[${timestamp}] [${type.toUpperCase()}] ${text}`;
        
        terminalOutput.appendChild(line);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
    
    if (btnClearLogs) {
        btnClearLogs.addEventListener("click", () => {
            if (terminalOutput) {
                terminalOutput.replaceChildren();
                addLogLine("system", "Log console output cleared.");
            }
        });
    }

    // ── DYNAMIC SVG DAG VISUALIZER ────────────────────────────────────
    const svgCanvas = document.getElementById("dag-canvas");
    const svgNamespace = "http://www.w3.org/2000/svg";
    
    const nodes = [
        { id: "query", label: "User Prompt", x: 60, y: 200, role: "entry" },
        { id: "router", label: "Task Router", x: 220, y: 200, role: "routing" },
        
        // Task Pipelines
        { id: "speed", label: "Speed Chain", x: 420, y: 80, role: "chain" },
        { id: "reasoning", label: "Reason Chain", x: 420, y: 160, role: "chain" },
        { id: "code", label: "Code Chain", x: 420, y: 240, role: "chain" },
        { id: "pentest", label: "Pentest Chain", x: 420, y: 320, role: "chain" },
        
        // Output Endpoint
        { id: "cache", label: "Semantic Cache", x: 620, y: 150, role: "caching" },
        { id: "output", label: "Response", x: 740, y: 200, role: "exit" }
    ];
    
    const connections = [
        { from: "query", to: "router" },
        { from: "router", to: "speed" },
        { from: "router", to: "reasoning" },
        { from: "router", to: "code" },
        { from: "router", to: "pentest" },
        
        { from: "speed", to: "cache" },
        { from: "reasoning", to: "cache" },
        { from: "code", to: "cache" },
        { from: "pentest", to: "cache" },
        { from: "cache", to: "output" }
    ];
    
    function drawDAG(activeChainId = null, activeNodeId = null) {
        if (!svgCanvas) return;
        svgCanvas.replaceChildren(); // Safe clear
        
        // 1. Draw Links/Edges
        connections.forEach(conn => {
            const fromNode = nodes.find(n => n.id === conn.from);
            const toNode = nodes.find(n => n.id === conn.to);
            
            if (fromNode && toNode) {
                const line = document.createElementNS(svgNamespace, "path");
                const d = `M ${fromNode.x} ${fromNode.y} C ${(fromNode.x + toNode.x)/2} ${fromNode.y}, ${(fromNode.x + toNode.x)/2} ${toNode.y}, ${toNode.x} ${toNode.y}`;
                
                line.setAttribute("d", d);
                line.setAttribute("class", "dag-link");
                
                // Determine if this connection line is currently active
                const isActivePath = 
                    (conn.from === "query" && conn.to === "router") ||
                    (conn.from === "router" && conn.to === activeChainId) ||
                    (conn.from === activeChainId && conn.to === "cache") ||
                    (conn.from === "cache" && conn.to === "output");
                    
                if (activeChainId && isActivePath) {
                    line.classList.add("active");
                }
                
                svgCanvas.appendChild(line);
            }
        });
        
        // 2. Draw Nodes
        nodes.forEach(node => {
            const g = document.createElementNS(svgNamespace, "g");
            g.setAttribute("class", "dag-node");
            
            if (node.id === activeNodeId || (node.role === "chain" && node.id === activeChainId)) {
                g.classList.add("active");
            }
            
            const circle = document.createElementNS(svgNamespace, "circle");
            circle.setAttribute("cx", node.x);
            circle.setAttribute("cy", node.y);
            circle.setAttribute("r", node.role === "router" ? "22" : "16");
            
            const label = document.createElementNS(svgNamespace, "text");
            label.setAttribute("x", node.x);
            label.setAttribute("y", node.y + 32);
            label.setAttribute("text-anchor", "middle");
            label.textContent = node.label;
            
            g.appendChild(circle);
            g.appendChild(label);
            svgCanvas.appendChild(g);
        });
    }
    
    // Initial draw
    drawDAG();

    // ── INTERACTIVE PLAYGROUND CHAT & FORM ─────────────────────────────
    const chatForm = document.getElementById("chat-input-form");
    const chatInput = document.getElementById("chat-user-prompt");
    const chatSelect = document.getElementById("chat-task-select");
    const chatMessages = document.getElementById("chat-messages-container");
    const previewArea = document.getElementById("playground-preview-area");
    
    if (chatForm && chatInput && chatMessages) {
        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const prompt = chatInput.value.strip ? chatInput.value.strip() : chatInput.value.trim();
            const task = chatSelect.value;
            
            if (!prompt) return;
            
            // 1. Add User Bubble
            addChatBubble("user", prompt);
            chatInput.value = "";
            
            // Update DAG State
            drawDAG(task, "router");
            addLogLine("route", `Routing prompt to chain: '${task.toUpperCase()}'...`);
            
            // 2. Query FastAPI server
            try {
                const response = await fetch("/api/execute", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ prompt, task })
                });
                
                const data = await response.json();
                
                if (data.status === "success") {
                    addChatBubble("assistant", data.response);
                    addLogLine("success", `Response received from LLM chain in ${data.duration_ms}ms.`);
                    
                    // Trigger dynamic visual preview if response looks like code or lists
                    if (data.preview_type === "diff") {
                        renderDiffPreview(data.preview_content);
                    } else if (data.preview_type === "screenshot") {
                        renderScreenshotPreview(data.preview_content);
                    }
                    
                    // Flash magic sparkles on success
                    if (!isWhipMode) {
                        playChime();
                    }
                } else {
                    addChatBubble("assistant", `ERROR: ${data.message}`);
                    addLogLine("error", `Task execution failed: ${data.message}`);
                }
            } catch (err) {
                addChatBubble("assistant", `Connection error: ${err}`);
                addLogLine("error", `Failed to contact API backend coordinator.`);
            }
            
            // Return DAG state to idle
            drawDAG(null, null);
        });
    }
    
    function addChatBubble(role, text) {
        if (!chatMessages) return;
        const bubble = document.createElement("div");
        bubble.classList.add("chat-bubble", role);
        const p = document.createElement("p");
        p.textContent = text;
        
        bubble.appendChild(p);
        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function renderDiffPreview(diffLines) {
        if (!previewArea) return;
        previewArea.replaceChildren(); // Safe clear
        
        const container = document.createElement("div");
        container.classList.add("diff-container");
        
        diffLines.forEach(line => {
            const div = document.createElement("div");
            div.classList.add("diff-line");
            if (line.startsWith("+")) {
                div.classList.add("add");
            } else if (line.startsWith("-")) {
                div.classList.add("del");
            } else {
                div.classList.add("normal");
            }
            div.textContent = line;
            container.appendChild(div);
        });
        
        previewArea.appendChild(container);
    }
    
    function renderScreenshotPreview(base64Image) {
        if (!previewArea) return;
        previewArea.replaceChildren();
        
        const img = document.createElement("img");
        img.src = `data:image/png;base64,${base64Image}`;
        img.alt = "Screen preview visual";
        img.style.maxWidth = "100%";
        img.style.borderRadius = "8px";
        img.style.border = "1px solid var(--border-glass)";
        
        previewArea.appendChild(img);
    }
    
    async function haltActiveTask() {
        try {
            await fetch("/api/abort", { method: "POST" });
            addLogLine("warning", "Abort signal dispatched to API client worker.");
        } catch (e) {
            console.error("Abort fail", e);
        }
    }

    // ── SECRET COMMIT ENGINES ──────────────────────────────────────────
    const keysForm = document.getElementById("keys-manager-form");
    const saveStatus = document.getElementById("keys-save-status");
    
    if (keysForm) {
        keysForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            const secrets = {
                groq: document.getElementById("key-input-groq").value.trim(),
                gemini: document.getElementById("key-input-gemini").value.trim(),
                openrouter: document.getElementById("key-input-openrouter").value.trim(),
                deepseek: document.getElementById("key-input-deepseek").value.trim(),
                cerebras: document.getElementById("key-input-cerebras").value.trim(),
                composio: document.getElementById("key-input-composio").value.trim()
            };
            
            if (saveStatus) {
                saveStatus.textContent = "Committing secrets...";
                saveStatus.className = "save-status-text";
            }
            
            try {
                const response = await fetch("/api/keys", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(secrets)
                });
                
                const data = await response.json();
                
                if (data.status === "success") {
                    saveStatus.textContent = "Secrets committed successfully to .env!";
                    saveStatus.className = "save-status-text success";
                    addLogLine("success", "API secret rotations updated in local configuration.");
                    
                    // Clear inputs for security
                    document.querySelectorAll("#keys-manager-form input").forEach(input => {
                        input.value = "";
                    });
                } else {
                    saveStatus.textContent = `Error: ${data.message}`;
                    saveStatus.className = "save-status-text error";
                }
            } catch (err) {
                saveStatus.textContent = "Failed to commit secrets.";
                saveStatus.className = "save-status-text error";
            }
        });
    }

    // ── TELEMETRY SYSTEM POLL ─────────────────────────────────────────
    const costElem = document.getElementById("telemetry-cost");
    const speedElem = document.getElementById("telemetry-speed");
    const cacheRateElem = document.getElementById("telemetry-cache-rate");
    const keysCountElem = document.getElementById("telemetry-keys-count");
    const cacheSizeElem = document.getElementById("telemetry-cache-size");
    const cooldownContainer = document.getElementById("cooldowns-list-container");
    
    async function pollTelemetry() {
        try {
            const response = await fetch("/api/telemetry");
            if (!response.ok) return;
            
            const data = await response.json();
            
            // Update cards
            if (costElem) costElem.textContent = `$${data.total_cost.toFixed(4)}`;
            if (speedElem) speedElem.textContent = `${data.speed_tps} t/s`;
            if (cacheRateElem) cacheRateElem.textContent = `${data.cache_hit_rate_pct}%`;
            if (keysCountElem) keysCountElem.textContent = `${data.keys_configured} Keys`;
            if (cacheSizeElem) cacheSizeElem.textContent = `${data.cache_entries} entries`;
            
            // Update cooldowns badges
            if (cooldownContainer) {
                cooldownContainer.replaceChildren(); // Safe clear
                const cds = data.active_cooldowns;
                
                if (Object.keys(cds).length === 0) {
                    const p = document.createElement("p");
                    p.classList.add("cooldown-empty-msg");
                    p.textContent = "No keys are currently in a cooldown state. All providers ready.";
                    cooldownContainer.appendChild(p);
                } else {
                    Object.entries(cds).forEach(([key, sec]) => {
                        const badge = document.createElement("div");
                        badge.classList.add("cooldown-badge");
                        
                        const nameSpan = document.createElement("span");
                        nameSpan.classList.add("cooldown-name");
                        nameSpan.textContent = key;
                        
                        const timeSpan = document.createElement("span");
                        timeSpan.classList.add("cooldown-time");
                        timeSpan.textContent = `⏳ ${Math.round(sec)}s`;
                        
                        badge.appendChild(nameSpan);
                        badge.appendChild(timeSpan);
                        cooldownContainer.appendChild(badge);
                    });
                }
            }
            
        } catch (e) {
            console.debug("Telemetry fetch failed", e);
        }
    }
    
    // Poll telemetry data every 3 seconds
    setInterval(pollTelemetry, 3000);
    pollTelemetry();
});
