Chart.register(ChartDataLabels);

let statusChart, worstRoutesChart;

// load and render the network summary + main table
async function loadMergedView() {
    const res = await fetch("/api/merged");
    const data = await res.json();

    document.getElementById("totalRoutes").innerText = data.batch_layer.total_routes ?? "—";
    document.getElementById("windowSeconds").innerText = (data.speed_layer.window_seconds ?? "—") + "s";
    document.getElementById("eventsInWindow").innerText = data.speed_layer.total_events_in_window ?? "—";
    document.getElementById("avgRecentScore").innerText = data.speed_layer.average_reliability_score_recent ?? "—";
    document.getElementById("avgRecentScoreLabel").innerText = scoreLabel(data.speed_layer.average_reliability_score_recent);
    document.getElementById("lastUpdated").innerText = "Updated " + formatTime(data.generated_at);

    renderRoutesTable(data.routes);
    renderWorstRoutesChart(data.routes);
}

// plain-English read of a 0-100 score, so the number isn't left to guesswork
function scoreLabel(score) {
    if (score === null || score === undefined) return "";
    if (score >= 85) return "Excellent";
    if (score >= 70) return "Good";
    if (score >= 55) return "Needs attention";
    return "Poor";
}

// load and render the status breakdown chart separately (comes from the speed endpoint)
async function loadStatusBreakdown() {
    const res = await fetch("/api/speed");
    const data = await res.json();
    if (data.status_counts) renderStatusChart(data.status_counts);
}

function formatTime(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleTimeString();
}

// small colored badge for recent-vs-historical trend
function trendBadge(delta) {
    if (delta === null || delta === undefined) return '<span class="trend trend--flat">—</span>';
    if (delta > 0) return `<span class="trend trend--up">▲ ${delta}</span>`;
    if (delta < 0) return `<span class="trend trend--down">▼ ${delta}</span>`;
    return '<span class="trend trend--flat">flat</span>';
}

function renderRoutesTable(routes) {
    const tbody = document.getElementById("routesTableBody");
    tbody.innerHTML = "";

    const sorted = [...routes].sort((a, b) => {
        if (a.recent_vs_history_delta !== null && b.recent_vs_history_delta === null) return -1;
        if (a.recent_vs_history_delta === null && b.recent_vs_history_delta !== null) return 1;
        return (b.historical_total_trips || 0) - (a.historical_total_trips || 0);
    });

    for (const r of sorted.slice(0, 100)) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${r.route_id}</td>
            <td>${fmtScore(r.historical_average_score)}</td>
            <td>${r.historical_total_trips}</td>
            <td>${r.recent_window_average_score ?? "—"}</td>
            <td>${r.recent_window_event_count}</td>
            <td>${trendBadge(r.recent_vs_history_delta)}</td>
        `;
        tbody.appendChild(tr);
    }
}

function fmtScore(v) {
    return v?.toFixed ? v.toFixed(1) : v;
}

// traffic-light palette: green = good, red = bad, distinct at a glance
const STATUS_COLORS = {
    Excellent: "#1E8A5F",
    Good: "#6FB93C",
    Average: "#E8A33D",
    Poor: "#E0702B",
    Critical: "#C1272D",
};

function renderStatusChart(statusCounts) {
    const labels = Object.keys(statusCounts);
    const values = Object.values(statusCounts);
    const colors = labels.map(l => STATUS_COLORS[l]);
    const total = values.reduce((a, b) => a + b, 0) || 1;

    // plain-language headline above the chart
    const healthy = (statusCounts.Excellent || 0) + (statusCounts.Good || 0);
    const pct = Math.round((100 * healthy) / total);
    document.getElementById("statusSummary").innerText =
        `${pct}% of recent trips are running well (Excellent or Good)`;

    // readable legend with real counts, not just a color key
    const legend = document.getElementById("statusLegend");
    legend.innerHTML = labels.map((label, i) => {
        const pctLabel = Math.round((100 * values[i]) / total);
        return `<span class="legend__item">
            <span class="legend__swatch" style="background:${colors[i]}"></span>
            ${label} <span class="legend__count">${values[i]} (${pctLabel}%)</span>
        </span>`;
    }).join("");

    const ctx = document.getElementById("statusChart");
    if (statusChart) statusChart.destroy();
    statusChart = new Chart(ctx, {
        type: "doughnut",
        data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 0 }] },
        options: {
            plugins: {
                legend: { display: false },  // using the custom HTML legend instead
                datalabels: {
                    color: "#fff",
                    font: { weight: 600, size: 11 },
                    formatter: (value) => value > 0 ? `${Math.round(100 * value / total)}%` : "",
                },
            },
        },
    });
}

function renderWorstRoutesChart(routes) {
    const withScores = routes.filter(r => r.recent_window_average_score !== null);
    const worst = [...withScores]
        .sort((a, b) => a.recent_window_average_score - b.recent_window_average_score)
        .slice(0, 8);

    const ctx = document.getElementById("worstRoutesChart");
    if (worstRoutesChart) worstRoutesChart.destroy();
    worstRoutesChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: worst.map(r => r.route_id),
            datasets: [{
                data: worst.map(r => r.recent_window_average_score),
                backgroundColor: "#E0702B",
                borderRadius: 4,
            }],
        },
        options: {
            indexAxis: "y",
            plugins: {
                legend: { display: false },
                datalabels: {
                    color: "#fff",
                    anchor: "end",
                    align: "start",
                    font: { weight: 600 },
                    formatter: (value) => value,
                },
            },
            scales: { x: { min: 0, max: 100 } },
        },
    });
}

// search: explicit button/Enter only, own panel, never touched by auto-refresh
async function runSearch() {
    const query = document.getElementById("searchBox").value.trim();
    const section = document.getElementById("searchResultsSection");
    const heading = document.getElementById("searchResultsHeading");
    const tbody = document.getElementById("searchResultsTableBody");

    if (!query) {
        section.hidden = true;
        return;
    }

    const res = await fetch(`/api/search/${encodeURIComponent(query)}`);
    const data = await res.json();

    section.hidden = false;
    tbody.innerHTML = "";

    if (data.message) {
        heading.innerText = `${data.message} for "${data.query}"`;
        return;
    }

    heading.innerText = `${data.total_matches} route(s) matching "${data.query}"`;

    for (const m of data.matches) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${m.route_id}</td>
            <td>${m.source}</td>
            <td>${m.destination}</td>
            <td>${fmtScore(m.historical_average_score)}</td>
            <td>${m.recent_window_average_score ?? "—"}</td>
            <td>${trendBadge(m.recent_vs_history_delta)}</td>
        `;
        tbody.appendChild(tr);
    }
}

function clearSearch() {
    document.getElementById("searchBox").value = "";
    document.getElementById("searchResultsSection").hidden = true;
}

document.getElementById("searchButton").addEventListener("click", runSearch);
document.getElementById("clearSearchButton").addEventListener("click", clearSearch);
document.getElementById("searchBox").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); runSearch(); }
});

loadMergedView();
loadStatusBreakdown();
setInterval(loadMergedView, 5000);
setInterval(loadStatusBreakdown, 5000);