const CHART_TITLES = {
    version: "Top 5 Versions by %",
    python_version: "Top 5 Python Versions by %",
    country: "Top 5 Countries by %",
};

async function fetchData() {
    const response = await fetch("/api/v1/records/summary/");
    if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
    }
    return await response.json();
}

function renderChart(canvas, summary) {
    new Chart(canvas, {
        type: "pie",
        data: {
            labels: summary.map(({ label }) => label),
            datasets: [{ data: summary.map(({ percentage }) => percentage) }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: "bottom" },
                title: { display: false },
            },
            animation: { animateRotate: false, animateScale: false },
        },
    });
}

async function init() {
    let data;
    try {
        data = await fetchData();
    } catch {
        document.getElementById("error-banner").innerHTML =
            '<div class="alert alert-danger">Failed to load census data. Please try again later.</div>';
        return;
    }

    for (const [kind, summary] of Object.entries(data)) {
        if (!CHART_TITLES[kind]) continue;

        const container = document.getElementById(kind + "-chart");
        const spinner = container.querySelector(".chart-spinner");
        const canvas = container.querySelector("canvas");

        if (spinner) spinner.classList.add("d-none");
        canvas.classList.remove("d-none");
        renderChart(canvas, summary);
    }
}

window.onload = init;
