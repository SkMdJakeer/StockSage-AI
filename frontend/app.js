let metricsData = {};

async function loadDashboard() {
    try {
        const response = await fetch("/api/metrics");
        metricsData = await response.json();

        document.getElementById("total-sales").textContent =
            "₹" + metricsData.total_sales.toLocaleString("en-IN");

        document.getElementById("inventory-units").textContent =
            metricsData.inventory_units.toLocaleString("en-IN");

        document.getElementById("products-risk").textContent =
            metricsData.products_at_risk;

        document.getElementById("overstocked").textContent =
            metricsData.overstocked_products;

    } catch (error) {
        console.error("Dashboard error:", error);
    }

    loadRisk();
    loadSales();
}


async function loadRisk() {

    try {

        const response = await fetch("/api/stock-risk");
        const data = await response.json();

        const container = document.getElementById("risk-list");

        if (!data.items.length) {
            container.innerHTML = "<p>No immediate stock risks.</p>";
            return;
        }

        container.innerHTML = data.items.slice(0, 6).map(item => `
            <div class="list-row">

                <div>
                    <div class="product-name">
                        ${item.product_name}
                    </div>

                    <div class="product-info">
                        Stock: ${Math.round(item.quantity)} units
                        · ${item.days_remaining} days remaining
                    </div>
                </div>

                <div class="risk">
                    ${item.risk}
                </div>

            </div>
        `).join("");

        const table = document.getElementById("inventory-table");

        table.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Stock</th>
                        <th>Daily Sales</th>
                        <th>Days Remaining</th>
                        <th>Risk</th>
                    </tr>
                </thead>

                <tbody>

                    ${data.items.map(item => `
                        <tr>
                            <td>${item.product_name}</td>
                            <td>${Math.round(item.quantity)}</td>
                            <td>${item.avg_daily_sales.toFixed(1)}</td>
                            <td>${item.days_remaining}</td>
                            <td class="risk">${item.risk}</td>
                        </tr>
                    `).join("")}

                </tbody>
            </table>
        `;

    } catch (error) {
        console.error("Risk error:", error);
    }
}


async function loadSales() {

    try {

        const response = await fetch("/api/sales-change");
        const data = await response.json();

        const container = document.getElementById("sales-list");

        container.innerHTML = data.items.slice(0, 6).map(item => {

            const change = item.change_percent;

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
                            ${item.product_name}
                        </div>

                        <div class="product-info">
                            Current: ${item.current_units} units
                            · Previous: ${item.previous_units}
                        </div>
                    </div>

                    <div class="${className}">
                        ${symbol}${change}%
                    </div>

                </div>
            `;

        }).join("");

        const table = document.getElementById("sales-table");

        table.innerHTML = `
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

                    ${data.items.map(item => {

                        const change = item.change_percent;

                        return `
                            <tr>
                                <td>${item.product_name}</td>
                                <td>${item.current_units}</td>
                                <td>${item.previous_units}</td>
                                <td class="${change < 0 ? "change-negative" : "change-positive"}">
                                    ${change > 0 ? "+" : ""}${change}%
                                </td>
                            </tr>
                        `;

                    }).join("")}

                </tbody>

            </table>
        `;

    } catch (error) {
        console.error("Sales error:", error);
    }
}


async function askCopilot() {

    const input = document.getElementById("question-input");

    const question = input.value.trim();

    if (!question) {
        return;
    }

    await sendQuestion(
        question,
        "response-card",
        "ai-response",
        "evidence-data"
    );
}


function askSuggested(question) {

    document.getElementById("question-input").value = question;

    askCopilot();
}


async function sendQuestion(
    question,
    responseCardId,
    responseId,
    evidenceId
) {

    const card = document.getElementById(responseCardId);
    const responseElement = document.getElementById(responseId);

    card.classList.remove("hidden");

    responseElement.textContent = "StockSage AI is analyzing your data...";

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

        const data = await response.json();

        responseElement.textContent =
            data.answer || "No answer returned.";

        if (evidenceId) {

            document.getElementById(evidenceId).textContent =
                JSON.stringify(data.facts || {}, null, 2);

        }

    } catch (error) {

        responseElement.textContent =
            "Unable to connect to StockSage AI.";

        console.error(error);
    }
}


function handleEnter(event) {

    if (event.key === "Enter") {
        askCopilot();
    }
}


function handleLargeEnter(event) {

    if (event.key === "Enter") {
        askLargeCopilot();
    }
}


async function askLargeCopilot() {

    const input =
        document.getElementById("question-input-large");

    const question = input.value.trim();

    if (!question) {
        return;
    }

    const response =
        document.getElementById("large-response");

    response.classList.remove("hidden");

    response.textContent =
        "StockSage AI is analyzing your data...";

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

        const data = await result.json();

        response.textContent =
            data.answer || "No answer returned.";

    } catch (error) {

        response.textContent =
            "Unable to connect to StockSage AI.";

        console.error(error);
    }
}


function showSection(sectionId) {

    document.querySelectorAll(".section")
        .forEach(section => {
            section.classList.remove("active-section");
        });

    document.getElementById(sectionId)
        .classList.add("active-section");

    document.querySelectorAll(".nav-item")
        .forEach(item => {
            item.classList.remove("active");
        });

    const clickedButton =
        [...document.querySelectorAll(".nav-item")]
            .find(button =>
                button.getAttribute("onclick")
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

    document.getElementById("page-title").textContent =
        titles[sectionId];
}


loadDashboard();