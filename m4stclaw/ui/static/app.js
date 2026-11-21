document.addEventListener("DOMContentLoaded", () => {
    const get = id => document.getElementById(id);
    const views = ["dashboard", "playground", "keys", "telemetry"];
    const navigate = view => {
        for (const name of views) {
            const selected = name === view;
            const button = get("nav-btn-" + name);
            button.classList.toggle("active", selected);
            get("view-" + name).classList.toggle("active-view", selected);
            if (selected) button.setAttribute("aria-current", "page");
            else button.removeAttribute("aria-current");
        }

        get("view-" + view).querySelector("h1").focus();
    };

    for (const name of views) get("nav-btn-" + name).addEventListener("click", () => navigate(name));
    get("open-console").addEventListener("click", () => navigate("playground"));

    const activity = get("log-terminal-output");
    const activityEmpty = get("activity-empty");
    const clearLogs = get("btn-clear-logs");
    const timeFormat = new Intl.DateTimeFormat(undefined, {
        hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"
    });

    function addActivity(type, message) {
        const item = document.createElement("div");
        item.className = "log-line";
        if (["success", "error", "warning"].includes(type)) item.classList.add(type);

        const now = new Date();
        const time = document.createElement("time");
        time.dateTime = now.toISOString();
        time.textContent = timeFormat.format(now);
        const text = document.createElement("span");
        text.textContent = message;

        item.append(time, text);
        activity.append(item);
        while (activity.childElementCount > 200) activity.firstElementChild.remove();
        activity.scrollTop = activity.scrollHeight;
        activityEmpty.hidden = true;
        clearLogs.disabled = false;
    }

    clearLogs.addEventListener("click", () => {
        activity.replaceChildren();
        activityEmpty.hidden = false;
        clearLogs.disabled = true;
    });

    const unlockForm = get("dashboard-unlock");
    const tokenInput = get("dashboard-token");
    const unlockStatus = get("dashboard-unlock-status");
    const accessStatus = get("telemetry-status");
    const editToken = get("edit-token");
    const chatStatus = get("chat-status");
    let token = "";
    let pollingToken = "";

    function setAccess(state, message) {
        accessStatus.parentElement.dataset.state = state;
        if (accessStatus.textContent !== message) accessStatus.textContent = message;
    }

    async function apiFetch(resource, options = {}, credential = token) {
        const headers = new Headers(options.headers);
        headers.set("Authorization", "Bearer " + credential);
        const response = await fetch(resource, { ...options, headers, credentials: "omit", redirect: "error" });

        if (response.status === 401 && credential === token) {
            token = "";
            showTokenForm();
            setAccess("locked", "Dashboard locked");
            chatStatus.textContent = "Locked";
            clearTelemetry();
        }
        return response;
    }

    function showTokenForm() {
        unlockForm.hidden = false;
        editToken.hidden = true;
    }

    editToken.addEventListener("click", () => {
        showTokenForm();
        tokenInput.focus();
    });

    function requireAccess() {
        if (token) return true;
        showTokenForm();
        unlockStatus.textContent = "Enter your token to continue.";
        tokenInput.focus();
        return false;
    }

    unlockForm.addEventListener("submit", async event => {
        event.preventDefault();
        const candidate = tokenInput.value.trim();
        tokenInput.value = "";
        const submit = unlockForm.querySelector("button");
        submit.disabled = true;

        try {
            const response = await apiFetch("/api/auth/check", {}, candidate);
            if (!response.ok) {
                unlockStatus.textContent = response.status === 503 ? "Configure the server token first." : "Token rejected.";
                tokenInput.focus();
                return;
            }

            token = candidate;
            unlockStatus.textContent = "";
            setAccess("connecting", "Loading telemetry");
            if (chatStatus.dataset.state !== "working") chatStatus.textContent = "Ready";
            const moveFocus = unlockForm.contains(document.activeElement);
            unlockForm.hidden = true;
            editToken.hidden = false;
            if (moveFocus) editToken.focus({ preventScroll: true });
            void refreshTelemetry();
        } catch {
            unlockStatus.textContent = "Could not reach the local dashboard.";
        } finally {
            submit.disabled = false;
        }
    });

    const routingStatus = get("routing-status");
    const routingFlow = get("routing-flow");
    const routingContext = get("routing-context");
    const chatForm = get("chat-input-form");
    const chatInput = get("chat-user-prompt");
    const chatSelect = get("chat-task-select");
    const chatSend = get("chat-btn-submit");
    const chatMessages = get("chat-messages-container");
    const chatEmpty = get("chat-empty");
    const codePreview = get("playground-preview-area");
    const diffPlaceholder = codePreview.firstElementChild;

    document.querySelectorAll("[data-prompt]").forEach(button => {
        button.addEventListener("click", () => {
            chatInput.value = button.dataset.prompt;
            chatInput.focus();
            chatInput.setSelectionRange(chatInput.value.length, chatInput.value.length);
        });
    });

    function appendMessage(role, text) {
        chatEmpty.hidden = true;
        const message = document.createElement("div");
        message.classList.add("chat-bubble", role);
        const body = document.createElement("p");
        body.textContent = text;
        message.append(body);
        chatMessages.append(message);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return body;
    }

    async function renderStream(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const bubble = appendMessage("assistant", "");
        let result = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            result += decoder.decode(value, { stream: true });
            bubble.textContent = result;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        result += decoder.decode();
        bubble.textContent = result || "The model returned an empty response.";
        return result.trim();
    }

    function renderDiff(result) {
        if (!result.includes("diff --git") && !result.includes("+++")) return;
        const diff = document.createElement("div");
        diff.className = "diff-container";
        const lines = result.split("\n").filter(line => /^(diff |@@|[+-])/.test(line)).slice(0, 20);
        for (const line of lines) {
            const item = document.createElement("div");
            item.className = "diff-line";
            if (line.startsWith("+")) item.classList.add("add");
            else if (line.startsWith("-")) item.classList.add("del");
            item.textContent = line;
            diff.append(item);
        }
        codePreview.replaceChildren(diff);
    }

    function setRunInProgress(active) {
        chatSend.disabled = active;
        chatStatus.textContent = active ? "Running" : token ? "Ready" : "Locked";
        chatStatus.dataset.state = active ? "working" : "";
        routingStatus.textContent = active ? "Routing" : "Idle";
        routingStatus.dataset.state = active ? "working" : "";
        routingFlow.dataset.state = active ? "working" : "";
    }

    chatForm.addEventListener("submit", async event => {
        event.preventDefault();
        const prompt = chatInput.value.trim();
        if (!prompt || chatSend.disabled || !requireAccess()) return;

        const selected = chatSelect.selectedOptions[0];
        const task = selected.value;
        const route = selected.textContent;
        chatInput.value = "";
        appendMessage("user", prompt);
        codePreview.replaceChildren(diffPlaceholder);
        routingContext.textContent = "Selected route · " + route;
        setRunInProgress(true);
        addActivity("route", "Prompt sent to " + route + ".");

        try {
            const isMesh = task === "agent";
            const response = await apiFetch(isMesh ? "/api/mesh/execute" : "/api/execute/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt, task })
            });

            if (!response.ok) {
                appendMessage("assistant", response.status === 401 ? "Unlock the dashboard and try again." : "The server could not start this task.");
                addActivity("error", "Request failed (HTTP " + response.status + ").");
            } else if (isMesh) {
                const data = await response.json();
                appendMessage("assistant", data.response || data.detail || "No response returned.");
                for (const entry of data.logs || []) addActivity(entry.type, entry.text);
                if (data.status === "success") addActivity("success", "Agent run completed.");
                else addActivity("error", "Agent run failed.");
            } else {
                const result = await renderStream(response);
                if (result && !result.startsWith("ERROR:")) {
                    renderDiff(result);
                    addActivity("success", "Response completed.");
                } else {
                    addActivity("error", "The model did not complete the response.");
                }
            }
        } catch {
            appendMessage("assistant", "The connection ended before the task completed.");
            addActivity("error", "The task connection ended early.");
        } finally {
            setRunInProgress(false);
            void refreshTelemetry();
        }
    });

    const keysForm = get("keys-manager-form");
    const saveKeys = get("btn-save-keys");
    const saveStatus = get("keys-save-status");
    const keyFields = ["groq", "gemini", "openrouter", "deepseek", "cerebras", "composio"];
    const keyInputs = keyFields.map(key => get("key-input-" + key));

    keysForm.addEventListener("submit", async event => {
        event.preventDefault();
        if (saveKeys.disabled || !requireAccess()) return;

        const values = Object.fromEntries(keyFields.map((key, index) => [key, keyInputs[index].value.trim()]));
        saveKeys.disabled = true;
        keyInputs.forEach(input => { input.readOnly = true; });
        saveStatus.textContent = "Saving…";
        saveStatus.className = "feedback";

        try {
            const response = await apiFetch("/api/keys", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(values)
            });
            const data = await response.json();
            if (response.ok && data.status === "success") {
                saveStatus.textContent = data.updated ? "Provider keys saved." : "No keys changed.";
                saveStatus.classList.add("success");
                keysForm.reset();
                if (data.updated) {
                    addActivity("success", "Provider keys saved.");
                    void refreshTelemetry();
                }
            } else {
                saveStatus.textContent = response.status === 401 ? "Unlock the dashboard and try again." :
                    typeof data.detail === "string" ? data.detail : "Could not save keys.";
                saveStatus.classList.add("error");
            }
        } catch {
            saveStatus.textContent = "Could not reach the local dashboard.";
            saveStatus.classList.add("error");
        } finally {
            saveKeys.disabled = false;
            keyInputs.forEach(input => { input.readOnly = false; });
        }
    });

    const providerRows = get("provider-status-rows");
    const cooldowns = get("cooldowns-list-container");
    const statIds = ["completed", "duration", "cache-rate", "keys-count", "errors-count", "cache-size", "cooldowns-count"];
    const providerNames = {
        groq: "Groq", gemini: "Gemini", openrouter: "OpenRouter", deepseek: "DeepSeek",
        cerebras: "Cerebras", nvidia: "NVIDIA", ollama: "Ollama", perplexity: "Perplexity"
    };

    function textElement(tag, text, className) {
        const element = document.createElement(tag);
        if (className) element.className = className;
        element.textContent = text;
        return element;
    }

    function providerEmpty(message) {
        const row = document.createElement("tr");
        const cell = textElement("td", message);
        cell.colSpan = 3;
        row.append(cell);
        providerRows.replaceChildren(row);
    }

    function renderProviders(providers) {
        if (!providers.length) {
            providerEmpty("The router has no provider entries.");
            return;
        }

        const rows = document.createDocumentFragment();
        for (const provider of providers) {
            const row = document.createElement("tr");
            const name = textElement("th", providerNames[provider.name] || provider.name);
            name.scope = "row";
            const models = textElement("td", provider.models.join(", "));
            const configuration = document.createElement("td");
            const status = textElement("span", "Key missing", "pill");

            if (provider.local) {
                status.textContent = "Local endpoint (unverified)";
            } else if (provider.cooling_keys > 0) {
                status.textContent = provider.cooling_keys + " of " + provider.configured_keys + " keys cooling down";
                status.dataset.state = "warning";
            } else if (provider.configured_keys > 0) {
                status.textContent = "Configured";
                status.dataset.state = "configured";
            }

            configuration.append(status);
            row.append(name, models, configuration);
            rows.append(row);
        }
        providerRows.replaceChildren(rows);
    }

    function renderCooldowns(entries) {
        if (!entries.length) {
            cooldowns.replaceChildren(textElement("p", "No cooldowns reported.", "section-note"));
            return;
        }

        const rows = entries.map(([key, seconds]) => {
            const item = document.createElement("div");
            item.className = "cooldown-badge";
            item.append(textElement("span", key, "cooldown-name"),
                textElement("span", Math.ceil(seconds) + "s remaining", "cooldown-time"));
            return item;
        });
        cooldowns.replaceChildren(...rows);
    }

    function clearTelemetry() {
        for (const id of statIds) get("telemetry-" + id).textContent = "—";
        providerEmpty("Unlock the dashboard to see provider configuration.");
        cooldowns.replaceChildren(textElement("p", "Unlock the dashboard to see active cooldowns.", "section-note"));
    }

    async function refreshTelemetry() {
        const credential = token;
        if (!credential || pollingToken === credential) return false;
        pollingToken = credential;

        try {
            const response = await apiFetch("/api/telemetry", {}, credential);
            if (token !== credential) return false;
            if (!response.ok) throw new Error("Telemetry request failed.");
            const data = await response.json();
            if (token !== credential) return false;

            const entries = Object.entries(data.active_cooldowns);
            const values = [data.completed_runs,
                data.last_run_duration_ms === null ? "—" : data.last_run_duration_ms + " ms",
                data.cache_hit_rate_pct === null ? "—" : data.cache_hit_rate_pct + "%",
                data.keys_configured, data.failed_runs, data.cache_entries, entries.length];
            statIds.forEach((id, index) => { get("telemetry-" + id).textContent = values[index]; });
            renderProviders(data.providers);
            renderCooldowns(entries);
            setAccess("connected", "Connected");
            return true;
        } catch {
            if (token === credential) setAccess("unavailable", "Telemetry unavailable");
            return false;
        } finally {
            if (pollingToken === credential) pollingToken = "";
        }
    }

    for (const button of document.querySelectorAll("[data-refresh]")) {
        button.addEventListener("click", async () => {
            if (requireAccess() && await refreshTelemetry()) addActivity("info", "Telemetry refreshed.");
        });
    }

    setInterval(refreshTelemetry, 5000);
});
