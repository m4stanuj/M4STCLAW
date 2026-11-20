/**
 * M4STCLAW Dashboard — app.js
 * ============================
 * Professional admin panel controller.
 * Handles navigation, chat interactions, API key management, DAG rendering,
 * telemetry polling, and log console. All DOM manipulation uses safe textContent/createElement.
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

                addLogLine("system", "Switched view to " + key.toUpperCase());
            });
        }
    });

    // ── TERMINAL LOG CONSOLE ──────────────────────────────────────────
    const terminalOutput = document.getElementById("log-terminal-output");
    const btnClearLogs = document.getElementById("btn-clear-logs");

    function addLogLine(type, text) {
        if (!terminalOutput) return;
        const line = document.createElement("div");
        line.classList.add("log-line", type);

        const timestamp = new Date().toLocaleTimeString();
        line.textContent = "[" + timestamp + "] [" + type.toUpperCase() + "] " + text;

        terminalOutput.appendChild(line);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;

        // Keep log size manageable (max 200 lines)
        while (terminalOutput.children.length > 200) {
            terminalOutput.removeChild(terminalOutput.firstChild);
        }
    }

    const unlockForm = document.getElementById("dashboard-unlock");
    const tokenInput = document.getElementById("dashboard-token");
    const unlockStatus = document.getElementById("dashboard-unlock-status");
    let dashboardToken = "";

    async function apiFetch(resource, options = {}) {
        const headers = new Headers(options.headers);
        if (dashboardToken) headers.set("Authorization", `Bearer ${dashboardToken}`);
        return fetch(resource, { ...options, headers, credentials: "omit", redirect: "error" });
    }

    unlockForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const candidate = tokenInput.value.trim();
        tokenInput.value = "";
        const submit = unlockForm.querySelector("button");
        submit.disabled = true;
        try {
            const response = await fetch("/api/auth/check", {
                headers: { "Authorization": `Bearer ${candidate}` },
                credentials: "omit",
                redirect: "error",
            });
            if (response.ok) {
                dashboardToken = candidate;
                unlockStatus.textContent = "Dashboard unlocked.";
                void pollTelemetry();
            } else {
                unlockStatus.textContent = response.status === 503 ? "Configure the server token first." : "Token rejected.";
            }
        } catch {
            unlockStatus.textContent = "Could not reach the local dashboard.";
        } finally {
            submit.disabled = false;
        }
    });

    if (btnClearLogs) {
        btnClearLogs.addEventListener("click", () => {
            if (terminalOutput) {
                terminalOutput.replaceChildren();
                addLogLine("system", "Log console cleared.");
            }
        });
    }

    // ── DYNAMIC SVG DAG VISUALIZER ────────────────────────────────────
    const svgCanvas = document.getElementById("dag-canvas");
    const svgNamespace = "http://www.w3.org/2000/svg";

    const nodes = [
        { id: "query", label: "User Prompt", x: 60, y: 200, role: "entry" },
        { id: "router", label: "Task Router", x: 220, y: 200, role: "routing" },

        // Task chains
        { id: "speed", label: "Speed", x: 400, y: 60, role: "chain" },
        { id: "reasoning", label: "Reasoning", x: 400, y: 130, role: "chain" },
        { id: "code", label: "Code", x: 400, y: 200, role: "chain" },
        { id: "write", label: "Write", x: 400, y: 270, role: "chain" },
        { id: "pentest", label: "Pentest", x: 400, y: 340, role: "chain" },

        // Output
        { id: "cache", label: "Semantic Cache", x: 580, y: 170, role: "caching" },
        { id: "output", label: "Response", x: 730, y: 200, role: "exit" }
    ];

    const connections = [
        { from: "query", to: "router" },
        { from: "router", to: "speed" },
        { from: "router", to: "reasoning" },
        { from: "router", to: "code" },
        { from: "router", to: "write" },
        { from: "router", to: "pentest" },

        { from: "speed", to: "cache" },
        { from: "reasoning", to: "cache" },
        { from: "code", to: "cache" },
        { from: "write", to: "cache" },
        { from: "pentest", to: "cache" },
        { from: "cache", to: "output" }
    ];

    function drawDAG(activeChainId, activeNodeId) {
        if (!svgCanvas) return;
        svgCanvas.replaceChildren(); // Safe clear

        // 1. Draw edges
        connections.forEach(conn => {
            const fromNode = nodes.find(n => n.id === conn.from);
            const toNode = nodes.find(n => n.id === conn.to);

            if (fromNode && toNode) {
                const line = document.createElementNS(svgNamespace, "path");
                const cpx = (fromNode.x + toNode.x) / 2;
                const d = "M " + fromNode.x + " " + fromNode.y
                    + " C " + cpx + " " + fromNode.y
                    + ", " + cpx + " " + toNode.y
                    + ", " + toNode.x + " " + toNode.y;

                line.setAttribute("d", d);
                line.setAttribute("class", "dag-link");

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

        // 2. Draw nodes
        nodes.forEach(node => {
            const g = document.createElementNS(svgNamespace, "g");
            g.setAttribute("class", "dag-node");

            if (node.id === activeNodeId || (node.role === "chain" && node.id === activeChainId)) {
                g.classList.add("active");
            }

            const circle = document.createElementNS(svgNamespace, "circle");
            circle.setAttribute("cx", String(node.x));
            circle.setAttribute("cy", String(node.y));
            circle.setAttribute("r", node.role === "routing" ? "22" : "16");

            const label = document.createElementNS(svgNamespace, "text");
            label.setAttribute("x", String(node.x));
            label.setAttribute("y", String(node.y + 32));
            label.setAttribute("text-anchor", "middle");
            label.textContent = node.label;

            g.appendChild(circle);
            g.appendChild(label);
            svgCanvas.appendChild(g);
        });
    }

    // Initial draw
    drawDAG(null, null);

    // ── INTERACTIVE PLAYGROUND CHAT ───────────────────────────────────
    const chatForm = document.getElementById("chat-input-form");
    const chatInput = document.getElementById("chat-user-prompt");
    const chatSelect = document.getElementById("chat-task-select");
    const chatMessages = document.getElementById("chat-messages-container");
    const previewArea = document.getElementById("playground-preview-area");

    if (chatForm && chatInput && chatMessages) {
        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const prompt = chatInput.value.trim();
            const task = chatSelect ? chatSelect.value : "speed";

            if (!prompt) return;

            // Add user bubble
            addChatBubble("user", prompt);
            chatInput.value = "";

            // Update DAG state
            drawDAG(task, "router");
            addLogLine("route", "Routing to chain: " + task.toUpperCase());

            // Query backend
            if (task === "agent") {
                try {
                    const response = await apiFetch("/api/mesh/execute", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ prompt: prompt, task: task })
                    });
                    const data = await response.json();
                    
                    if (data.status === "success") {
                        addChatBubble("assistant", data.response);
                        addLogLine("success", "Mesh execution completed in " + data.duration_ms + "ms.");
                        if (data.logs && Array.isArray(data.logs)) {
                            data.logs.forEach(logLine => {
                                addLogLine(logLine.type, logLine.text);
                            });
                        }
                    } else {
                        addChatBubble("assistant", "ERROR: " + (data.detail || data.response || "Mesh execution failed."));
                        addLogLine("error", "Mesh task execution failed.");
                    }
                } catch (err) {
                    addChatBubble("assistant", "Connection error: " + err);
                    addLogLine("error", "Failed to contact API backend.");
                }
            } else {
                try {
                    const response = await apiFetch("/api/execute/stream", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ prompt: prompt, task: task })
                    });
                    
                    if (!response.ok) {
                        addChatBubble("assistant", "ERROR: Failed to establish text stream.");
                        addLogLine("error", "Failed to fetch model stream.");
                        // Reset DAG and return
                        drawDAG(null, null);
                        return;
                    }
                    
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder("utf-8");
                    let assistantBubble = addChatBubble("assistant", "");
                    let fullText = "";
                    
                    addLogLine("info", "Receiving real-time stream tokens...");
                    
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        const chunk = decoder.decode(value, { stream: true });
                        fullText += chunk;
                        assistantBubble.querySelector("p").textContent = fullText;
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                    
                    fullText += decoder.decode();
                    assistantBubble.querySelector("p").textContent = fullText || "No response returned.";
                    if (fullText.trim() && !fullText.trimStart().startsWith("ERROR:")) {
                        addLogLine("success", "Response complete.");
                    } else {
                        addLogLine("error", "The provider did not return a response.");
                    }
                    
                    // Render preview dynamically if a diff block is detected in the response
                    if (fullText.includes("diff --git") || fullText.includes("+++")) {
                        const diffLines = fullText.split("\n").filter(line => line.startsWith("+") || line.startsWith("-") || line.startsWith("@@") || line.startsWith("diff")).slice(0, 20);
                        renderDiffPreview(diffLines);
                    }
                } catch (err) {
                    addChatBubble("assistant", "Connection error: " + err);
                    addLogLine("error", "Failed to contact API backend.");
                }
            }

            // Reset DAG
            drawDAG(null, null);
            void pollTelemetry();
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
        return bubble;
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

    // ── ABORT BUTTON ──────────────────────────────────────────────────
    const btnAbort = document.getElementById("btn-abort-task");
    if (btnAbort) {
        btnAbort.addEventListener("click", async () => {
            try {
                const response = await apiFetch("/api/abort", { method: "POST" });
                if (!response.ok) {
                    const detail = await response.json();
                    addLogLine("warning", detail.detail || "The task could not be cancelled.");
                }
            } catch (e) {
                addLogLine("warning", "The dashboard could not contact the local server.");
            }
        });
    }

    // ── REFRESH BUTTON ────────────────────────────────────────────────
    const btnRefresh = document.getElementById("btn-refresh-telemetry");
    if (btnRefresh) {
        btnRefresh.addEventListener("click", () => {
            pollTelemetry();
            addLogLine("info", "Telemetry data refreshed.");
        });
    }

    // ── SECRET COMMIT ENGINE ──────────────────────────────────────────
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
                saveStatus.textContent = "Saving...";
                saveStatus.className = "save-status-text";
            }

            try {
                const response = await apiFetch("/api/keys", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(secrets)
                });

                const data = await response.json();

                if (data.status === "success") {
                    if (saveStatus) {
                        saveStatus.textContent = "Configuration saved successfully.";
                        saveStatus.className = "save-status-text success";
                    }
                    addLogLine("success", "API keys updated in .env configuration.");

                    // Clear inputs for security
                    document.querySelectorAll("#keys-manager-form input").forEach(input => {
                        input.value = "";
                    });
                } else {
                    if (saveStatus) {
                        saveStatus.textContent = "Error: " + (data.message || "Save failed");
                        saveStatus.className = "save-status-text error";
                    }
                }
            } catch (err) {
                if (saveStatus) {
                    saveStatus.textContent = "Failed to save configuration.";
                    saveStatus.className = "save-status-text error";
                }
            }
        });
    }

    // ── TELEMETRY POLLING ─────────────────────────────────────────────
    const completedElem = document.getElementById("telemetry-completed");
    const durationElem = document.getElementById("telemetry-duration");
    const errorsElem = document.getElementById("telemetry-errors-count");
    const cacheRateElem = document.getElementById("telemetry-cache-rate");
    const keysCountElem = document.getElementById("telemetry-keys-count");
    const cacheSizeElem = document.getElementById("telemetry-cache-size");
    const cooldownContainer = document.getElementById("cooldowns-list-container");
    const providerRows = document.getElementById("provider-status-rows");
    const telemetryStatus = document.getElementById("telemetry-status");
    let pollingTelemetry = false;

    function renderProviders(providers) {
        const rows = document.createDocumentFragment();
        for (const provider of providers) {
            const row = document.createElement("tr");
            const name = document.createElement("th");
            name.scope = "row";
            name.textContent = provider.name;
            const models = document.createElement("td");
            models.textContent = provider.models.join(", ");
            const status = document.createElement("td");
            if (provider.local) {
                status.textContent = "Local endpoint (unverified)";
            } else if (provider.configured_keys === 0) {
                status.textContent = "Key missing";
            } else if (provider.cooling_keys > 0) {
                status.textContent = `${provider.cooling_keys} of ${provider.configured_keys} keys cooling down`;
            } else {
                status.textContent = "Configured";
            }
            row.append(name, models, status);
            rows.append(row);
        }
        providerRows.replaceChildren(rows);
    }

    async function pollTelemetry() {
        if (!dashboardToken || pollingTelemetry) return;
        pollingTelemetry = true;
        try {
            const response = await apiFetch("/api/telemetry");
            if (response.status === 401) {
                dashboardToken = "";
                telemetryStatus.textContent = "Dashboard locked";
                return;
            }
            if (!response.ok) {
                telemetryStatus.textContent = "Telemetry unavailable";
                return;
            }

            const data = await response.json();

            // Update stat cards
            if (completedElem) completedElem.textContent = data.completed_runs;
            if (durationElem) durationElem.textContent = data.last_run_duration_ms === null ? "—" : data.last_run_duration_ms + " ms";
            if (errorsElem) errorsElem.textContent = data.failed_runs;
            if (cacheRateElem) cacheRateElem.textContent = data.cache_hit_rate_pct === null ? "—" : data.cache_hit_rate_pct + "%";
            if (keysCountElem) keysCountElem.textContent = data.keys_configured + " Keys";
            if (cacheSizeElem) cacheSizeElem.textContent = data.cache_entries + " entries";
            renderProviders(data.providers);
            telemetryStatus.textContent = "Telemetry connected";

            // Update cooldowns
            if (cooldownContainer) {
                cooldownContainer.replaceChildren(); // Safe clear
                const cds = data.active_cooldowns;

                if (Object.keys(cds).length === 0) {
                    const p = document.createElement("p");
                    p.classList.add("cooldown-empty-msg");
                    p.textContent = "No cooldowns reported.";
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
                        timeSpan.textContent = Math.round(sec) + "s remaining";

                        badge.appendChild(nameSpan);
                        badge.appendChild(timeSpan);
                        cooldownContainer.appendChild(badge);
                    });
                }
            }

        } catch {
            telemetryStatus.textContent = "Telemetry unavailable";
        } finally {
            pollingTelemetry = false;
        }
    }

    // Poll telemetry every 5 seconds
    setInterval(pollTelemetry, 5000);
    pollTelemetry();
});
