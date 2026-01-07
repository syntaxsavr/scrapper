// Dashboard Charts JavaScript - make stats look nice
document.addEventListener('DOMContentLoaded', function() {
    // load chart data and initialize charts
    loadChartsData();
});

function loadChartsData() {
    // fetch stats data from api
    fetch('/api/scraping-stats/')  // api endpoint for chart data
        .then(response => response.json())
        .then(data => {
            initMonthlyChart(data.monthly_stats);  // monthly activity chart
            initStatusChart(data.status_distribution);  // status pie chart
            initProjectChart(data.project_stats);  // project activity if needed
        })
        .catch(error => {
            console.error('Error loading chart data:', error);  // debug info
        });
}

function initMonthlyChart(monthlyStats) {
    const ctx = document.getElementById('monthlyChart');
    if (!ctx) return;  // chart element not found

    new Chart(ctx, {
        type: 'line',  // line chart for time series
        data: {
            labels: monthlyStats.map(stat => stat.month),  // month labels
            datasets: [{
                label: 'Scrapes',
                data: monthlyStats.map(stat => stat.scrapes),  // scrape counts
                borderColor: '#007bff',  // blue line
                backgroundColor: 'rgba(0, 123, 255, 0.1)',  // light blue fill
                tension: 0.4,  // smooth curves
                fill: true  // fill area under line
            }]
        },
        options: {
            responsive: true,  // resize with container
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false  // hide legend for single dataset
                }
            },
            scales: {
                y: {
                    beginAtZero: true,  // start from 0
                    ticks: {
                        precision: 0  // whole numbers only
                    }
                }
            }
        }
    });
}

function initStatusChart(statusStats) {
    const ctx = document.getElementById('statusChart');
    if (!ctx) return;  // chart element not found

    // colors for different statuses
    const statusColors = {
        'completed': '#28a745',  // green
        'failed': '#dc3545',     // red  
        'running': '#007bff',    // blue
        'pending': '#6c757d',    // gray
        'cancelled': '#ffc107'   // yellow
    };

    const labels = statusStats.map(stat => stat.status.charAt(0).toUpperCase() + stat.status.slice(1));  // capitalize
    const data = statusStats.map(stat => stat.count);
    const colors = statusStats.map(stat => statusColors[stat.status] || '#6c757d');

    new Chart(ctx, {
        type: 'doughnut',  // donut chart looks modern
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#ffffff'  // white borders between segments
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',  // legend below chart
                    labels: {
                        padding: 20,  // space around labels
                        usePointStyle: true  // circular legend markers
                    }
                }
            }
        }
    });
}

function initProjectChart(projectStats) {
    // could add project activity chart later if needed
    console.log('Project stats:', projectStats);  // debug for now
}

// utility function to format numbers nicely
function formatNumber(num) {
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'k';  // 1.5k format
    }
    return num.toString();
}

// add some interactive features
function addChartInteractions() {
    // could add click handlers or tooltips
    const statCards = document.querySelectorAll('.stat-card');
    
    statCards.forEach(card => {
        card.addEventListener('click', function() {
            // maybe navigate to detailed view
            console.log('Stat card clicked');  // placeholder
        });
    });
}
