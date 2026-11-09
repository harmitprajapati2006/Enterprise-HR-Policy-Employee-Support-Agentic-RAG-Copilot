document.addEventListener("DOMContentLoaded", () => {
    // Initialize Lucide Icons
    if (window.lucide) {
        lucide.createIcons();
    }

    // DOM Elements
    const chatHistory = document.getElementById("chatHistory");
    const chatForm = document.getElementById("chatForm");
    const queryInput = document.getElementById("queryInput");
    const sendBtn = document.getElementById("sendBtn");
    const docList = document.getElementById("docList");
    const traceFeed = document.getElementById("traceFeed");
    const presetQueries = document.getElementById("presetQueries");

    // Modals
    const uploadModal = document.getElementById("uploadModal");
    const btnOpenUpload = document.getElementById("btnOpenUpload");
    const btnCloseUpload = document.getElementById("btnCloseUpload");
    const btnCancelUpload = document.getElementById("btnCancelUpload");
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const fileInfo = document.getElementById("fileInfo");
    const selectedFileName = document.getElementById("selectedFileName");
    const clearFileBtn = document.getElementById("clearFileBtn");
    const btnSubmitUpload = document.getElementById("btnSubmitUpload");
    const uploadProgress = document.getElementById("uploadProgress");
    const uploadStatusText = document.getElementById("uploadStatusText");

    const auditModal = document.getElementById("auditModal");
    const btnOpenAudit = document.getElementById("btnOpenAudit");
    const btnCloseAudit = document.getElementById("btnCloseAudit");
    const auditTableBody = document.getElementById("auditTableBody");

    let isProcessing = false;
    let selectedUploadFile = null;

    // Auto-resize textarea
    queryInput.addEventListener("input", function () {
        this.style.height = "auto";
        this.style.height = Math.min(this.scrollHeight, 120) + "px";
    });

    queryInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (queryInput.value.trim() && !isProcessing) {
                chatForm.dispatchEvent(new Event("submit"));
            }
        }
    });

    // Preset Queries Click
    presetQueries.addEventListener("click", (e) => {
        const btn = e.target.closest(".preset-btn");
        if (!btn || isProcessing) return;
        const query = btn.getAttribute("data-query");
        if (query) {
            queryInput.value = query;
            queryInput.dispatchEvent(new Event("input"));
            chatForm.dispatchEvent(new Event("submit"));
        }
    });

    // Form Submit (Chat Inquiry)
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query || isProcessing) return;

        // Add user message to UI
        appendUserMessage(query);
        queryInput.value = "";
        queryInput.style.height = "auto";
        isProcessing = true;
        sendBtn.disabled = true;

        // Reset and animate visualizer
        resetGraphNodes();
        activateGraphNode("node-router", "Evaluating Query...");

        // Add temporary typing placeholder
        const typingId = appendTypingIndicator();

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: query, session_id: "web-session" }),
            });

            if (!response.ok) {
                throw new Error(`Server returned error: ${response.statusText}`);
            }

            const data = await response.json();
            removeMessage(typingId);

            // Animate trace and visualizer
            processExecutionTrace(data.trace, data.source_used);

            // Append assistant response
            appendAssistantMessage(data);

        } catch (err) {
            removeMessage(typingId);
            appendErrorMessage(err.message || "Failed to contact HR Copilot API.");
            resetGraphNodes();
        } finally {
            isProcessing = false;
            sendBtn.disabled = false;
            queryInput.focus();
        }
    });

    // Graph Visualizer Controls
    function resetGraphNodes() {
        const nodes = ["node-router", "node-retrieve", "node-grade-kb", "node-web-search", "node-generate"];
        nodes.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.className = "graph-node" + (id === "node-web-search" ? " fallback" : "");
                el.querySelector(".node-state").textContent = id === "node-web-search" ? "Standby" : "Idle";
            }
        });
    }

    function activateGraphNode(id, stateText) {
        const el = document.getElementById(id);
        if (el) {
            el.classList.add("active");
            el.querySelector(".node-state").textContent = stateText || "Processing";
        }
    }

    function markGraphNodeSuccess(id, stateText) {
        const el = document.getElementById(id);
        if (el) {
            el.classList.remove("active");
            el.classList.add("success");
            el.querySelector(".node-state").textContent = stateText || "Completed";
        }
    }

    function processExecutionTrace(trace, sourceUsed) {
        if (!trace || !Array.isArray(trace)) return;

        traceFeed.innerHTML = "";
        trace.forEach(step => {
            const item = document.createElement("div");
            item.className = "trace-item";
            item.innerHTML = `
                <div class="trace-header">
                    <span class="node-badge">[${escapeHtml(step.node)}]</span>
                    <span class="trace-time">${escapeHtml(step.timestamp || "")}</span>
                </div>
                <div class="trace-desc">${escapeHtml(step.details || "")}</div>
            `;
            traceFeed.appendChild(item);
        });
        traceFeed.scrollTop = traceFeed.scrollHeight;

        // Update graph visualizer node states
        markGraphNodeSuccess("node-router", "Routed");

        if (sourceUsed === "private_kb") {
            markGraphNodeSuccess("node-retrieve", "Retrieved Chunks");
            markGraphNodeSuccess("node-grade-kb", "Good Evidence");
            markGraphNodeSuccess("node-generate", "Grounded KB Output");
        } else if (sourceUsed === "web_search") {
            markGraphNodeSuccess("node-retrieve", "Insufficient KB");
            markGraphNodeSuccess("node-grade-kb", "Weak Evidence");
            const webNode = document.getElementById("node-web-search");
            if (webNode) {
                webNode.className = "graph-node fallback fallback-active success";
                webNode.querySelector(".node-state").textContent = "Tavily Evidence";
            }
            markGraphNodeSuccess("node-generate", "Web-Sourced Answer");
        } else if (sourceUsed === "direct") {
            markGraphNodeSuccess("node-router", "Direct Conversational");
            markGraphNodeSuccess("node-generate", "Direct Greeting");
        } else {
            markGraphNodeSuccess("node-generate", "Fallback Escalation");
        }
    }

    // Message Render Helpers
    function appendUserMessage(text) {
        const card = document.createElement("div");
        card.className = "message-card user";
        card.innerHTML = `
            <div class="content-col">
                <div class="message-body">
                    <p>${escapeHtml(text)}</p>
                </div>
            </div>
        `;
        chatHistory.appendChild(card);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function appendAssistantMessage(data) {
        const card = document.createElement("div");
        card.className = "message-card assistant";

        let routeBadgeClass = "private";
        let routeBadgeText = "Private KB Grounded";

        if (data.source_used === "web_search") {
            routeBadgeClass = "web";
            routeBadgeText = "External Web Fallback";
        } else if (data.source_used === "direct") {
            routeBadgeClass = "direct";
            routeBadgeText = "Direct Conversation";
        } else if (data.source_used === "insufficient_evidence") {
            routeBadgeClass = "insufficient";
            routeBadgeText = "Evidence Insufficient";
        }

        // Citations HTML
        let citationsHtml = "";
        if (data.citations && data.citations.length > 0) {
            citationsHtml = `
                <div class="citations-box">
                    <div class="citations-header">
                        <i data-lucide="book-marked"></i>
                        <span>Verified Policy Citations (${data.citations.length})</span>
                    </div>
                    <div class="citation-chips">
                        ${data.citations.map(c => `
                            <div class="citation-chip" title="${escapeHtml(c.snippet)}">
                                <span class="citation-source">${escapeHtml(c.title || c.source)}</span>
                                <span class="citation-snippet">${escapeHtml(c.snippet)}</span>
                            </div>
                        `).join("")}
                    </div>
                </div>
            `;
        }

        card.innerHTML = `
            <div class="avatar-col">
                <div class="agent-avatar"><i data-lucide="bot"></i></div>
            </div>
            <div class="content-col">
                <div class="author-row">
                    <span class="author-name">Enterprise HR Copilot</span>
                    <span class="badge route-badge ${routeBadgeClass}">${routeBadgeText}</span>
                    <span class="timestamp">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <div class="message-body">
                    ${formatMarkdown(data.answer)}
                </div>
                ${citationsHtml}
            </div>
        `;

        chatHistory.appendChild(card);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        if (window.lucide) lucide.createIcons();
    }

    function appendTypingIndicator() {
        const id = "typing-" + Date.now();
        const card = document.createElement("div");
        card.id = id;
        card.className = "message-card assistant typing-card";
        card.innerHTML = `
            <div class="avatar-col">
                <div class="agent-avatar"><i data-lucide="bot"></i></div>
            </div>
            <div class="content-col">
                <div class="author-row">
                    <span class="author-name">Enterprise HR Copilot</span>
                    <span class="badge route-badge direct">Thinking & Routing...</span>
                </div>
                <div class="message-body">
                    <p><i data-lucide="loader" class="spin" style="width:16px;height:16px;vertical-align:middle;margin-right:6px;"></i> Analyzing query against Enterprise HR vector store...</p>
                </div>
            </div>
        `;
        chatHistory.appendChild(card);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        if (window.lucide) lucide.createIcons();
        return id;
    }

    function removeMessage(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function appendErrorMessage(msg) {
        const card = document.createElement("div");
        card.className = "message-card assistant";
        card.innerHTML = `
            <div class="avatar-col">
                <div class="agent-avatar" style="background:#ef4444;"><i data-lucide="alert-triangle"></i></div>
            </div>
            <div class="content-col" style="border-color:#ef4444;">
                <div class="author-row">
                    <span class="author-name">System Error</span>
                </div>
                <div class="message-body" style="color:#fca5a5;">
                    <p>${escapeHtml(msg)}</p>
                </div>
            </div>
        `;
        chatHistory.appendChild(card);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        if (window.lucide) lucide.createIcons();
    }

    // Load Knowledge Base Documents
    async function loadDocuments() {
        try {
            const res = await fetch("/api/documents");
            const data = await res.json();
            docList.innerHTML = "";

            if (!data.documents || data.documents.length === 0) {
                docList.innerHTML = `<div class="doc-item">No documents indexed yet.</div>`;
                return;
            }

            data.documents.forEach(doc => {
                const item = document.createElement("div");
                item.className = "doc-item";
                const icon = doc.type === "uploaded" ? "file-plus" : "file-check-2";
                item.innerHTML = `
                    <i data-lucide="${icon}"></i>
                    <span class="doc-name" title="${escapeHtml(doc.name)}">${escapeHtml(doc.name)}</span>
                `;
                docList.appendChild(item);
            });
            if (window.lucide) lucide.createIcons();
        } catch (err) {
            docList.innerHTML = `<div class="doc-item">Unable to load document directory.</div>`;
        }
    }

    // Load Audit Logs and Metrics
    async function loadAuditModal() {
        try {
            const [statsRes, auditRes] = await Promise.all([
                fetch("/api/stats"),
                fetch("/api/audit?limit=20"),
            ]);
            const stats = await statsRes.json();
            const logs = await auditRes.json();

            document.getElementById("statTotalQueries").textContent = stats.total_queries || 0;
            document.getElementById("statKbRate").textContent = stats.kb_resolution_rate || "0%";
            document.getElementById("statWebCount").textContent = stats.web_search_count || 0;
            document.getElementById("statDirectCount").textContent = stats.direct_count || 0;

            auditTableBody.innerHTML = "";
            if (!logs || logs.length === 0) {
                auditTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:16px;">No audit queries logged yet.</td></tr>`;
                return;
            }

            logs.forEach(log => {
                const tr = document.createElement("tr");
                const timeStr = log.created_at ? log.created_at.replace("T", " ").split(".")[0] : "-";
                tr.innerHTML = `
                    <td style="font-family:var(--font-mono);">${escapeHtml(timeStr)}</td>
                    <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(log.question)}">${escapeHtml(log.question)}</td>
                    <td><span class="badge route-badge ${log.source_used === 'private_kb' ? 'private' : (log.source_used === 'web_search' ? 'web' : 'direct')}">${escapeHtml(log.source_used)}</span></td>
                    <td>${escapeHtml(log.kb_grade || '-')}</td>
                    <td>${log.retry_count || 0}</td>
                `;
                auditTableBody.appendChild(tr);
            });
        } catch (err) {
            auditTableBody.innerHTML = `<tr><td colspan="5" style="color:var(--rose-500);text-align:center;">Failed to load audit records: ${err.message}</td></tr>`;
        }
    }

    // Modal Events
    btnOpenUpload.addEventListener("click", () => {
        uploadModal.classList.add("open");
    });

    const closeUploadModal = () => {
        uploadModal.classList.remove("open");
        selectedUploadFile = null;
        fileInfo.style.display = "none";
        btnSubmitUpload.disabled = true;
        uploadProgress.style.display = "none";
    };

    btnCloseUpload.addEventListener("click", closeUploadModal);
    btnCancelUpload.addEventListener("click", closeUploadModal);

    btnOpenAudit.addEventListener("click", () => {
        auditModal.classList.add("open");
        loadAuditModal();
    });

    btnCloseAudit.addEventListener("click", () => {
        auditModal.classList.remove("open");
    });

    // File Drop Zone
    dropZone.addEventListener("click", () => fileInput.click());

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleSelectedFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleSelectedFile(e.target.files[0]);
        }
    });

    clearFileBtn.addEventListener("click", () => {
        selectedUploadFile = null;
        fileInput.value = "";
        fileInfo.style.display = "none";
        btnSubmitUpload.disabled = true;
    });

    function handleSelectedFile(file) {
        selectedUploadFile = file;
        selectedFileName.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        fileInfo.style.display = "flex";
        btnSubmitUpload.disabled = false;
        if (window.lucide) lucide.createIcons();
    }

    btnSubmitUpload.addEventListener("click", async () => {
        if (!selectedUploadFile) return;

        const formData = new FormData();
        formData.append("file", selectedUploadFile);

        uploadProgress.style.display = "flex";
        uploadStatusText.textContent = `Chunking and embedding ${selectedUploadFile.name} into Pinecone...`;
        btnSubmitUpload.disabled = true;

        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Upload failed");
            }

            const data = await res.json();
            alert(`Document successfully indexed!\nFile: ${data.filename}\nChunks: ${data.chunks_indexed}\nNamespace: ${data.namespace}`);
            closeUploadModal();
            loadDocuments();
        } catch (err) {
            alert(`Upload error: ${err.message}`);
            uploadProgress.style.display = "none";
            btnSubmitUpload.disabled = false;
        }
    });

    // Formatting & Utility functions
    function formatMarkdown(text) {
        if (!text) return "";
        let html = escapeHtml(text);

        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        // Bullet points
        html = html.replace(/^\s*-\s+(.*?)$/gm, "<li>$1</li>");
        html = html.replace(/(<li>.*?<\/li>)/gs, "<ul>$1</ul>");
        // Clean double <ul> tags
        html = html.replace(/<\/ul>\s*<ul>/g, "");
        // Numbered list
        html = html.replace(/^\s*\d+\.\s+(.*?)$/gm, "<li>$1</li>");
        // Paragraph breaks
        html = html.split("\n\n").map(p => {
            if (p.startsWith("<ul>") || p.startsWith("<ol>")) return p;
            return `<p>${p}</p>`;
        }).join("");

        return html;
    }

    function escapeHtml(string) {
        const entityMap = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
        };
        return String(string).replace(/[&<>"']/g, (s) => entityMap[s]);
    }

    // Initial Load
    loadDocuments();
});
