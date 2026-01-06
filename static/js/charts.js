document.addEventListener("DOMContentLoaded", function() {
    // Heart Rate Line Chart
    if(document.getElementById('hrChart')) {
        new Chart(document.getElementById('hrChart'), {
            type: 'line',
            data: {
                labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '23:59'],
                datasets: [{
                    label: 'Heart Rate',
                    data: [60, 55, 75, 85, 78, 68, 62],
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
                    x: { grid: { display: false } },
                    y: { display: false, min: 40 }
                }
            }
        });

        // Steps Bar Chart
        new Chart(document.getElementById('stepsChart'), {
            type: 'bar',
            data: {
                labels: ['M', 'T', 'W', 'T', 'F', 'S', 'S'],
                datasets: [{
                    data: [4000, 6000, 3000, 8000, 5000, 9000, 3500],
                    backgroundColor: '#2dd4bf',
                    borderRadius: 4,
                    barThickness: 10
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#6b7280' }, grid: { display: false } },
                    y: { display: false }
                }
            }
        });
        
        // Sleep Doughnut
        new Chart(document.getElementById('sleepChart'), {
            type: 'doughnut',
            data: {
                labels: ['Deep', 'Light', 'REM'],
                datasets: [{
                    data: [35, 45, 20],
                    backgroundColor: ['#3b82f6', '#dbeafe', '#6366f1'],
                    borderWidth: 0
                }]
            },
            options: {
                cutout: '75%',
                responsive: true,
                plugins: { legend: { display: false } }
            }
        });
    }
});