// Navigation Logic
function showPage(pageId, element) {
    // Hide all pages
    document.querySelectorAll('.page-section').forEach(page => {
        page.style.display = 'none';
        page.classList.remove('active');
    });
    
    // Show selected page
    document.getElementById(pageId).style.display = 'block';
    setTimeout(() => document.getElementById(pageId).classList.add('active'), 10);

    // Update Sidebar UI
    document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
    element.classList.add('active');

    // Resize Three.js if switching to analytics
    if(pageId === '3d-analytics' && window.resizeThreeJS) {
        window.resizeThreeJS();
    }
}

// Chart.js Implementations for Overview Page
document.addEventListener("DOMContentLoaded", function() {
    
    // Store chart instances to destroy them if they exist
    const chartInstances = {};
    
    // Helper function to get or create chart
    function getOrCreateChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        
        // Destroy existing chart if it exists
        if (chartInstances[canvasId]) {
            chartInstances[canvasId].destroy();
        }
        
        // Create new chart
        const ctx = canvas.getContext('2d');
        chartInstances[canvasId] = new Chart(ctx, config);
        return chartInstances[canvasId];
    }
    
    // 1. Heart Rate Trend (Line Chart)
    getOrCreateChart('heartRateChart', {
        type: 'line',
        data: {
            labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '23:59'],
            datasets: [{
                label: 'Heart Rate',
                data: [62, 58, 75, 82, 78, 70, 65],
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: { min: 40, max: 100, grid: { borderDash: [5, 5] } },
                x: { grid: { display: false } }
            }
        }
    });

    // 2. Activity Chart (Bar Chart)
    getOrCreateChart('activityChart', {
        type: 'bar',
        data: {
            labels: ['M', 'T', 'W', 'T', 'F', 'S', 'S'],
            datasets: [{
                data: [5000, 7000, 4500, 8000, 6000, 9500, 4000],
                backgroundColor: '#2dd4bf',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: { display: false },
                x: { grid: { display: false }, ticks: { color: '#6b7280' } }
            }
        }
    });
});