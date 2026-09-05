// ============================================================
// StockSage AI - Frontend
// ============================================================

let metricsData = {};
let isAsking = false;


// ============================================================
// HELPERS
// ============================================================

function byId(id) {
    return document.getElementById(id);
}


function escapeHTML(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function formatNumber(value, decimals = 0) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "0";
    }

    return number.toLocaleString("en-IN", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}


function formatAIResponse(text) {
    if (!text) {
        return "<p>No answer returned.</p>";
    }

    const safeText = escapeHTML(text);

    const lines = safeText.split("\n");
    let html = "";
    let inList = false;

    const headings = new Set([
        "Finding",
        "Evidence",
        "Recommendation",
        "Recommended Action",
        "Assumption",
        "Limitation"
    ]);

    function closeList() {
        if (inList) {
            html += "</ul>";
            inList = false;
        }
    }

    lines.forEach(line => {
        const trimmed = line.trim();

        if (!trimmed) {
            closeList();
            return;
        }

        // Section headings
        if (headings.has(trimmed)) {
            closeList();
            html += `<h4>${trimmed}</h4>`;
            return;
        }

        // Bullet points
        if (trimmed.startsWith("• ")) {
            if (!inList) {
                html += '<ul class="ai-list">';
                inList = true;
            }

            html += `<li>${trimmed.substring(2)}</li>`;
            return;
        }

        // Markdown bullets
        if (trimmed.startsWith("- ")) {
            if (!inList) {
                html += '<ul class="ai-list">';
                inList = true;
            }

            html += `<li>${trimmed.substring(2)}</li>`;
            return;
        }

        // Numbered list
        const numbered = trimmed.match(/^(\d+)\.\s+(.*)$/);

        if (numbered) {
            closeList();

            html += `
                <div class="ai-numbered-item">
                    <span class="ai-number">${numbered[1]}</span>
                    <span>${numbered[2]}</span>
                </div>
            `;

            return;
        }

        closeList();

        // Bold markdown
        const formatted = trimmed.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );

        html += `<p>${formatted}</p>`;
    });

    closeList();

    return `
        <div class="ai-formatted-response">
            ${html}
        </div>
    `;
}


// ============================================================
// AI STATUS
// ============================================================

function createAIStatus() {
    let status = byId("ai-status");

    if (status) {
        return status;
    }

    status = document.createElement("div");
    status.id = "ai-status";
    status.className = "ai-status fallback";

    status.innerHTML = `
        <span class="status-indicator"></span>
        <span class="status-text">Data Copilot Mode</span>
    `;

    const copilotCard = document.querySelector(".copilot-card");

    if (copilotCard) {
        copilotCard.appendChild(status);
    }

    return status;
}


function setAIStatus(source) {
    const status = createAIStatus();

    if (!status) {
        return;
    }

    const text = status.querySelector(".status-text");

    status.classList.remove(
        "active",
        "fallback",
        "loading",
        "error"
    );

    if (source === "gemini") {
        status.classList.add("active");

        if (text) {
            text.textContent = "Gemini AI Active";
        }

        status.title = "Response generated using Gemini AI";
        return;
    }

    if (
        source === "deterministic" ||
        source === "deterministic_fallback"
    ) {
        status.classList.add("fallback");

        if (text) {
            text.textContent = "Data Copilot Mode";
        }

        status.title =
            "Using deterministic retail analytics with grounded business data";
        return;
    }

    if (source === "loading") {
        status.classList.add("loading");

        if (text) {
            text.textContent = "Analyzing...";
        }

        return;
    }

    status.classList.add("error");

    if (text) {
        text.textContent = "Connection Issue";
    }

    status.title = "The application could not reach the backend";
}


// ============================================================
// DASHBOARD
// ============================================================

async function loadDashboard() {
    try {
        const response = await fetch("/api/metrics");

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        metricsData = await response.json();

        const totalSales = byId("total-sales");
        const inventoryUnits = byId("inventory-units");
        const productsRisk = byId("products-risk");
        const overstocked = byId("overstocked");

        if (totalSales) {
            totalSales.textContent =
                "₹" + formatNumber(metricsData.total_sales, 1);
        }

        if (inventoryUnits) {
            inventoryUnits.textContent =
                formatNumber(metricsData.inventory_units);
        }

        if (productsRisk) {
            productsRisk.textContent =
                formatNumber(metricsData.products_at_risk);
        }

        if (overstocked) {
            overstocked.textContent =
                formatNumber(metricsData.overstocked_products);
        }

    } catch (error) {
        console.error("Dashboard error:", error);
    }

    await Promise.all([
        loadRisk(),
        loadSales()
    ]);
}


// ============================================================
// STOCK RISK
// ============================================================

async function loadRisk() {
    try {
        const response = await fetch("/api/stock-risk");

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const items = Array.isArray(data.items) ? data.items : [];

        const container = byId("risk-list");

        if (container) {
            if (!items.length) {
                container.innerHTML =
                    '<p class="empty-state">No immediate stock risks.</p>';
            } else {
                container.innerHTML = items
                    .slice(0, 6)
                    .map(item => `
                        <div class="list-row">
                            <div>
                                <div class="product-name">
                                    ${escapeHTML(item.product_name)}
                                </div>

                                <div class="product-info">
                                    ${escapeHTML(item.store_name)}
                                    · Stock:
                                    ${formatNumber(item.quantity)} units
                                    · ${formatNumber(item.days_remaining, 1)}
                                    days remaining
                                </div>
                            </div>

                            <div class="risk ${String(item.risk).toLowerCase()}">
                                ${escapeHTML(item.risk)}
                            </div>
                        </div>
                    `)
                    .join("");
            }
        }


        // Inventory table
        const table = byId("inventory-table");

        if (table) {
            if (!items.length) {
                table.innerHTML =
                    '<p class="empty-state">No inventory risks found.</p>';
                return;
            }

            table.innerHTML = `
                <div class="table-wrap">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Store</th>
                                <th>Product</th>
                                <th>Stock</th>
                                <th>Daily Sales</th>
                                <th>Days Remaining</th>
                                <th>Risk</th>
                                <th>Reorder</th>
                            </tr>
                        </thead>

                        <tbody>
                            ${items.map(item => `
                                <tr>
                                    <td>
                                        ${escapeHTML(item.store_name)}
                                    </td>

                                    <td>
                                        ${escapeHTML(item.product_name)}
                                    </td>

                                    <td>
                                        ${formatNumber(item.quantity)}
                                    </td>

                                    <td>
                                        ${formatNumber(
                                            item.avg_daily_sales,
                                            1
                                        )}
                                    </td>

                                    <td>
                                        ${formatNumber(
                                            item.days_remaining,
                                            1
                                        )}
                                    </td>

                                    <td>
                                        <span class="risk-pill ${String(
                                            item.risk
                                        ).toLowerCase()}">
                                            ${escapeHTML(item.risk)}
                                        </span>
                                    </td>

                                    <td>
                                        <strong>
                                            ${formatNumber(
                                                item.reorder_quantity
                                            )} units
                                        </strong>
                                    </td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>
            `;
        }

    } catch (error) {
        console.error("Risk error:", error);

        const container = byId("risk-list");

        if (container) {
            container.innerHTML =
                '<p class="empty-state error-text">Unable to load stock risk.</p>';
        }
    }
}


// ============================================================
// SALES CHANGES
// ============================================================

async function loadSales() {
    try {
        const response = await fetch("/api/sales-change");

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const items = Array.isArray(data.items) ? data.items : [];

        const container = byId("sales-list");

        if (container) {
            if (!items.length) {
                container.innerHTML =
                    '<p class="empty-state">No sales changes found.</p>';
            } else {
                container.innerHTML = items
                    .slice(0, 6)
                    .map(item => {
                        const change = Number(item.change_percent) || 0;

                        const className =
                            change < 0
                                ? "change-negative"
                                : "change-positive";

                        const symbol =
                            change > 0 ? "+" : "";

                        return `
                            <div class="list-row">
                                <div>
                                    <div class="product-name">
                                        ${escapeHTML(item.product_name)}
                                    </div>

                                    <div class="product-info">
                                        Current:
                                        ${formatNumber(item.current_units)}
                                        units
                                        · Previous:
                                        ${formatNumber(item.previous_units)}
                                    </div>
                                </div>

                                <div class="${className}">
                                    ${symbol}${formatNumber(change, 1)}%
                                </div>
                            </div>
                        `;
                    })
                    .join("");
            }
        }


        // Sales table
        const table = byId("sales-table");

        if (table) {
            if (!items.length) {
                table.innerHTML =
                    '<p class="empty-state">No sales changes found.</p>';
                return;
            }

            table.innerHTML = `
                <div class="table-wrap">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Product</th>
                                <th>Current Units</th>
                                <th>Previous Units</th>
                                <th>Change</th>
                            </tr>
                        </thead>

                        <tbody>
                            ${items.map(item => {
                                const change =
                                    Number(item.change_percent) || 0;

                                return `
                                    <tr>
                                        <td>
                                            ${escapeHTML(
                                                item.product_name
                                            )}
                                        </td>

                                        <td>
                                            ${formatNumber(
                                                item.current_units
                                            )}
                                        </td>

                                        <td>
                                            ${formatNumber(
                                                item.previous_units
                                            )}
                                        </td>

                                        <td class="${
                                            change < 0
                                                ? "change-negative"
                                                : "change-positive"
                                        }">
                                            ${
                                                change > 0 ? "+" : ""
                                            }${formatNumber(change, 1)}%
                                        </td>
                                    </tr>
                                `;
                            }).join("")}
                        </tbody>
                    </table>
                </div>
            `;
        }

    } catch (error) {
        console.error("Sales error:", error);

        const container = byId("sales-list");

        if (container) {
            container.innerHTML =
                '<p class="empty-state error-text">Unable to load sales data.</p>';
        }
    }
}


// ============================================================
// MAIN COPILOT
// ============================================================

async function askCopilot() {
    const input = byId("question-input");

    if (!input) {
        return;
    }

    const question = input.value.trim();

    if (!question || isAsking) {
        return;
    }

    await sendQuestion(
        question,
        "response-card",
        "ai-response",
        "evidence-data"
    );
}


// ============================================================
// SUGGESTED QUESTIONS
// ============================================================

function askSuggested(question) {
    const input = byId("question-input");

    if (!input) {
        return;
    }

    input.value = question;

    askCopilot();
}


// ============================================================
// SEND QUESTION TO BACKEND
// ============================================================

async function sendQuestion(
    question,
    responseCardId,
    responseId,
    evidenceId
) {
    const card = byId(responseCardId);
    const responseElement = byId(responseId);
    const evidenceElement = byId(evidenceId);

    if (!card || !responseElement) {
        return;
    }

    isAsking = true;

    card.classList.remove("hidden");

    setAIStatus("loading");

    responseElement.innerHTML = `
        <div class="ai-loading">
            <span class="loading-dot"></span>
            <span>Analyzing your retail data...</span>
        </div>
    `;

    if (evidenceElement) {
        evidenceElement.textContent = "Loading supporting data...";
    }

    try {
        const response = await fetch("/api/copilot", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                question: question
            })
        });


        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }


        const data = await response.json();


        // Render AI/data answer
        responseElement.innerHTML =
            formatAIResponse(
                data.answer || "No answer returned."
            );


        // Update status based on backend source
        setAIStatus(
            data.source || "deterministic"
        );


        // Supporting evidence
        if (evidenceElement) {
            evidenceElement.textContent =
                JSON.stringify(
                    data.facts || {},
                    null,
                    2
                );
        }


        // If Gemini failed but deterministic fallback worked,
        // do NOT show an error to the user.
        if (data.source === "deterministic_fallback") {
            console.info(
                "Gemini unavailable. Using deterministic fallback."
            );
        }

    } catch (error) {
        console.error(
            "Copilot request error:",
            error
        );

        setAIStatus("error");

        responseElement.innerHTML = `
            <div class="ai-error">
                <strong>StockSage could not process the request.</strong>
                <p>
                    Please check that the application is running
                    and try again.
                </p>
            </div>
        `;

        if (evidenceElement) {
            evidenceElement.textContent =
                "No supporting data available.";
        }

    } finally {
        isAsking = false;
    }
}


// ============================================================
// KEYBOARD HANDLING
// ============================================================

function handleEnter(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        askCopilot();
    }
}


function handleLargeEnter(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        askLargeCopilot();
    }
}


// ============================================================
// LARGE COPILOT PAGE
// ============================================================

async function askLargeCopilot() {
    const input = byId("question-input-large");

    if (!input) {
        return;
    }

    const question = input.value.trim();

    if (!question || isAsking) {
        return;
    }

    const response = byId("large-response");

    if (!response) {
        return;
    }

    isAsking = true;

    response.classList.remove("hidden");

    response.innerHTML = `
        <div class="ai-loading">
            <span class="loading-dot"></span>
            <span>Analyzing your retail data...</span>
        </div>
    `;

    try {
        const result = await fetch("/api/copilot", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                question: question
            })
        });


        if (!result.ok) {
            throw new Error(`HTTP ${result.status}`);
        }


        const data = await result.json();


        response.innerHTML =
            formatAIResponse(
                data.answer || "No answer returned."
            );


        setAIStatus(
            data.source || "deterministic"
        );

    } catch (error) {
        console.error(
            "Large copilot error:",
            error
        );

        response.innerHTML = `
            <div class="ai-error">
                <strong>StockSage could not process the request.</strong>
                <p>Please try again.</p>
            </div>
        `;

        setAIStatus("error");

    } finally {
        isAsking = false;
    }
}


// ============================================================
// NAVIGATION
// ============================================================

function showSection(sectionId) {
    document.querySelectorAll(".section")
        .forEach(section => {
            section.classList.remove(
                "active-section"
            );
        });


    const target = byId(sectionId);

    if (target) {
        target.classList.add(
            "active-section"
        );
    }


    document.querySelectorAll(".nav-item")
        .forEach(item => {
            item.classList.remove("active");
        });


    const clickedButton =
        [...document.querySelectorAll(".nav-item")]
            .find(button =>
                button
                    .getAttribute("onclick")
                    ?.includes(sectionId)
            );


    if (clickedButton) {
        clickedButton.classList.add("active");
    }


    const titles = {
        dashboard: "Good morning, Manager",
        inventory: "Inventory Intelligence",
        sales: "Sales Analytics",
        copilot: "AI Retail Copilot"
    };


    const pageTitle = byId("page-title");

    if (pageTitle && titles[sectionId]) {
        pageTitle.textContent =
            titles[sectionId];
    }
}


// ============================================================
// INITIALIZE
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        createAIStatus();

        loadDashboard();

        // Enter key support
        const questionInput =
            byId("question-input");

        if (questionInput) {
            questionInput.addEventListener(
                "keydown",
                handleEnter
            );
        }


        const largeInput =
            byId("question-input-large");

        if (largeInput) {
            largeInput.addEventListener(
                "keydown",
                handleLargeEnter
            );
        }
    }
);