// static/js/main.js

// Global variables
let timelineData = [];
let zoomLevel = 1;
const eventColors = {
    'read': '#28a745',
    'write': '#007bff',
    'ioctl': '#6f42c1',
    'binder': '#fd7e14',
    'network': '#17a2b8',
    'other': '#6c757d'
};

// DOM ready
$(document).ready(function() {
    // Load initial data
    loadAllData();

    // Setup event listeners
    $('#apply-filters').click(loadAllData);
    $('#reset-filters').click(resetFilters);
    $('#zoom-in').click(zoomIn);
    $('#zoom-out').click(zoomOut);
    $('#reset-zoom').click(resetZoom);
});

// Load all data based on current filters
function loadAllData() {
    const pid = $('#pid-filter').val();
    const device = $('#device-filter').val();

    // Load timeline data
    loadTimelineData(pid, device);

    // Load statistics
    loadDeviceStats(pid);
    loadEventStats(pid, device);
    // Replace loadTcpStats with loadStatsSummary
    loadStatsSummary(pid, device);

    // Load charts
    loadDevicePieChart(pid);
    loadEventPieChart(pid, device);
}

function loadStatsSummary(pid, device) {
    // In a real implementation, you would fetch this data from an API
    // For now, we'll use the sample data you provided
    const summaryData = {
        totalWindows: 16,
        totalCategoriesUsed: 2,
        totalUniqueDevices: 35,
        mostUsedCategory: {
            name: 'camera',
            count: 97
        },
        topDevices: [
            { device: 10485885, count: 13 },
            { device: 512753665, count: 13 },
            { device: 260046858, count: 11 },
            { device: 10485855, count: 9 },
            { device: 508559371, count: 9 }
        ]
    };

    renderStatsSummary(summaryData);
    renderTopDevicesChart(summaryData.topDevices);
}

// Function to render the top devices chart
function renderTopDevicesChart(topDevices) {
    // Clear existing content
    d3.select('#top-devices-chart-container').html("");

    const width = document.getElementById('top-devices-chart-container').clientWidth;
    const height = 400;
    const margin = { top: 30, right: 30, bottom: 70, left: 60 };
    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    // Create SVG
    const svg = d3.select('#top-devices-chart-container')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${margin.left}, ${margin.top})`);

    // Add title
    svg.append('text')
        .attr('x', chartWidth / 2)
        .attr('y', -10)
        .attr('text-anchor', 'middle')
        .style('font-size', '16px')
        .style('font-weight', 'bold')
        .text('Top 5 Devices by Usage');

    // X scale
    const x = d3.scaleBand()
        .domain(topDevices.map(d => d.device.toString()))
        .range([0, chartWidth])
        .padding(0.2);

    // Y scale
    const y = d3.scaleLinear()
        .domain([0, d3.max(topDevices, d => d.count) * 1.1])
        .range([chartHeight, 0]);

    // Add X axis
    svg.append('g')
        .attr('transform', `translate(0, ${chartHeight})`)
        .call(d3.axisBottom(x))
        .selectAll('text')
        .style('text-anchor', 'end')
        .attr('dx', '-.8em')
        .attr('dy', '.15em')
        .attr('transform', 'rotate(-45)');

    // Add Y axis
    svg.append('g')
        .call(d3.axisLeft(y));

    // Add X axis label
    svg.append('text')
        .attr('x', chartWidth / 2)
        .attr('y', chartHeight + margin.bottom - 5)
        .attr('text-anchor', 'middle')
        .text('Device ID');

    // Add Y axis label
    svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', -margin.left + 15)
        .attr('x', -chartHeight / 2)
        .attr('text-anchor', 'middle')
        .text('Count');

    // Add bars
    svg.selectAll('rect')
        .data(topDevices)
        .enter()
        .append('rect')
        .attr('x', d => x(d.device.toString()))
        .attr('y', d => y(d.count))
        .attr('width', x.bandwidth())
        .attr('height', d => chartHeight - y(d.count))
        .attr('fill', '#4682B4')
        .attr('stroke', 'black')
        .attr('stroke-width', 1);

    // Add labels on top of bars
    svg.selectAll('.label')
        .data(topDevices)
        .enter()
        .append('text')
        .attr('class', 'label')
        .attr('x', d => x(d.device.toString()) + x.bandwidth() / 2)
        .attr('y', d => y(d.count) - 5)
        .attr('text-anchor', 'middle')
        .text(d => d.count);
}


// Function to render the statistics summary table
function renderStatsSummary(data) {
    const tableBody = $('#stats-summary-table tbody');
    tableBody.empty();

    // Add rows to the table
    tableBody.append(`
        <tr>
            <td><strong>Total windows</strong></td>
            <td>${data.totalWindows}</td>
        </tr>
        <tr>
            <td><strong>Total categories used</strong></td>
            <td>${data.totalCategoriesUsed}</td>
        </tr>
        <tr>
            <td><strong>Total unique devices</strong></td>
            <td>${data.totalUniqueDevices}</td>
        </tr>
        <tr>
            <td><strong>Most used category</strong></td>
            <td>${data.mostUsedCategory.name} (count: ${data.mostUsedCategory.count})</td>
        </tr>
    `);

    // Add top devices as a list in a single row
    let topDevicesHtml = '<ul class="list-unstyled mb-0">';
    data.topDevices.forEach(device => {
        topDevicesHtml += `<li>Device ${device.device}, count ${device.count}</li>`;
    });
    topDevicesHtml += '</ul>';

    tableBody.append(`
        <tr>
            <td><strong>Top 5 devices by usage</strong></td>
            <td>${topDevicesHtml}</td>
        </tr>
    `);
}


// Reset all filters
function resetFilters() {
    $('#pid-filter').val('');
    $('#device-filter').val('');
    loadAllData();
}

// Timeline functions
function loadTimelineData(pid, device) {
    let url = '/api/timeline';
    let params = [];
    if (pid) params.push(`pid=${pid}`);
    if (device) params.push(`device=${device}`);
    if (params.length > 0) url += '?' + params.join('&');

    $.getJSON(url, function(data) {
        timelineData = data;
        renderTimeline();
    });
}

function renderTimeline() {
    // Clear existing timeline
    d3.select('#timeline-container').html('');

    if (timelineData.length === 0) {
        d3.select('#timeline-container')
            .append('div')
            .attr('class', 'alert alert-info')
            .text('Δεν βρέθηκαν δεδομένα για τα επιλεγμένα φίλτρα.');
        return;
    }

    // Set up dimensions
    const margin = {top: 20, right: 20, bottom: 50, left: 100};
    const width = document.getElementById('timeline-container').clientWidth - margin.left - margin.right;
    const height = document.getElementById('timeline-container').clientHeight - margin.top - margin.bottom;

    // Create SVG
    const svg = d3.select('#timeline-container')
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Apply zoom scaling
    const visibleDataCount = Math.ceil(timelineData.length / zoomLevel);
    const visibleData = timelineData.slice(0, visibleDataCount);

    // Set up scales
    const x = d3.scaleLinear()
        .domain([0, visibleDataCount])
        .range([0, width]);

    // Group data by category for easier display
    const categoryGroups = {};
    const categories = ['read', 'write', 'ioctl', 'binder', 'network', 'other'];

    visibleData.forEach(event => {
        if (!categoryGroups[event.category]) {
            categoryGroups[event.category] = [];
        }
        categoryGroups[event.category].push(event);
    });

    // Calculate y positions for each category
    const y = d3.scaleBand()
        .domain(categories)
        .range([0, height])
        .padding(0.1);

    // Add background stripes for categories
    categories.forEach(category => {
        svg.append('rect')
            .attr('x', 0)
            .attr('y', y(category))
            .attr('width', width)
            .attr('height', y.bandwidth())
            .attr('fill', '#f8f9fa')
            .attr('stroke', '#eee');
    });

    // Add category labels
    svg.selectAll('.category-label')
        .data(categories)
        .enter()
        .append('text')
        .attr('class', 'category-label')
        .attr('x', -10)
        .attr('y', d => y(d) + y.bandwidth() / 2)
        .attr('text-anchor', 'end')
        .attr('dominant-baseline', 'middle')
        .text(d => d.charAt(0).toUpperCase() + d.slice(1));

    // Draw events
    Object.keys(categoryGroups).forEach(category => {
        svg.selectAll(`.dot-${category}`)
            .data(categoryGroups[category])
            .enter()
            .append('circle')
            .attr('class', `dot-${category}`)
            .attr('cx', d => x(d.time))
            .attr('cy', d => y(d.category) + y.bandwidth() / 2)
            .attr('r', 4)
            .attr('fill', eventColors[category])
            .on('mouseover', function(event, d) {
                showTooltip(event, d);
            })
            .on('mouseout', hideTooltip);
    });

    // Add x-axis
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).ticks(10).tickFormat(d3.format('d')));

    // Add x-axis label
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', height + 40)
        .attr('text-anchor', 'middle')
        .text('Timeline of events');

    // Create tooltip div if it doesn't exist
    if (!d3.select('#timeline-tooltip').node()) {
        d3.select('body').append('div')
            .attr('id', 'timeline-tooltip')
            .style('position', 'absolute')
            .style('background', 'white')
            .style('border', '1px solid #ddd')
            .style('border-radius', '4px')
            .style('padding', '10px')
            .style('box-shadow', '0 0 10px rgba(0,0,0,0.1)')
            .style('pointer-events', 'none')
            .style('opacity', 0)
            .style('z-index', 1000);
    }
}

function showTooltip(event, d) {
    const tooltip = d3.select('#timeline-tooltip');
    tooltip.transition().duration(200).style('opacity', 0.9);

    // Format device and pathname information
    let deviceInfo = '';
    if (d.device !== null && d.device !== 0) {
        deviceInfo = `<strong>Συσκευή:</strong> ${d.device}<br>`;
    }

    let pathnameInfo = '';
    if (d.pathname) {
        pathnameInfo = `<strong>Διαδρομή:</strong> ${d.pathname}<br>`;
    }

    tooltip.html(`
        <strong>Συμβάν:</strong> ${d.event}<br>
        <strong>Κατηγορία:</strong> ${d.category}<br>
        <strong>PID:</strong> ${d.pid || 'N/A'}<br>
        <strong>TID:</strong> ${d.tid || 'N/A'}<br>
        ${deviceInfo}
        ${pathnameInfo}
    `)
    .style('left', (event.pageX + 10) + 'px')
    .style('top', (event.pageY - 28) + 'px');
}

function hideTooltip() {
    d3.select('#timeline-tooltip').transition().duration(500).style('opacity', 0);
}

// Zoom functions
function zoomIn() {
    zoomLevel = Math.min(zoomLevel * 1.5, timelineData.length / 10);
    renderTimeline();
}

function zoomOut() {
    zoomLevel = Math.max(zoomLevel / 1.5, 1);
    renderTimeline();
}

function resetZoom() {
    zoomLevel = 1;
    renderTimeline();
}

// Statistics functions
function loadDeviceStats(pid) {
    let url = '/api/device_stats';
    if (pid) url += `?pid=${pid}`;

    $.getJSON(url, function(data) {
        renderDeviceStats(data);
    });
}

function renderDeviceStats(data) {
    const tableBody = $('#device-stats-table tbody');
    tableBody.empty();

    if (data.length === 0) {
        tableBody.append('<tr><td colspan="4" class="text-center">Δεν βρέθηκαν δεδομένα</td></tr>');
        return;
    }

    data.forEach(item => {
        const paths = item.paths.join(', ');
        tableBody.append(`
            <tr>
                <td>${item.device}</td>
                <td>${item.count}</td>
                <td>${item.path_count}</td>
                <td title="${paths}">${paths.length > 50 ? paths.substring(0, 50) + '...' : paths}</td>
            </tr>
        `);
    });
}

function loadEventStats(pid, device) {
    let url = '/api/event_stats';
    let params = [];
    if (pid) params.push(`pid=${pid}`);
    if (device) params.push(`device=${device}`);
    if (params.length > 0) url += '?' + params.join('&');

    $.getJSON(url, function(data) {
        renderEventStats(data);
    });
}

function renderEventStats(data) {
    const tableBody = $('#event-stats-table tbody');
    tableBody.empty();

    if (data.length === 0) {
        tableBody.append('<tr><td colspan="3" class="text-center">Δεν βρέθηκαν δεδομένα</td></tr>');
        return;
    }

    const totalEvents = data.reduce((sum, item) => sum + item.count, 0);

    data.forEach(item => {
        const percentage = ((item.count / totalEvents) * 100).toFixed(2);
        tableBody.append(`
            <tr>
                <td>${item.event}</td>
                <td>${item.count}</td>
                <td>${percentage}%</td>
            </tr>
        `);
    });
}

function loadTcpStats(pid) {
    let url = '/api/tcp_stats';
    if (pid) url += `?pid=${pid}`;

    $.getJSON(url, function(data) {
        renderTcpStats(data);
    });
}

function renderTcpStats(data) {
    const tableBody = $('#tcp-stats-table tbody');
    tableBody.empty();

    if (data.length === 0) {
        tableBody.append('<tr><td colspan="5" class="text-center">Δεν βρέθηκαν δεδομένα</td></tr>');
        return;
    }

    data.forEach(item => {
        tableBody.append(`
            <tr>
                <td>${item.ip_address}</td>
                <td>${item.port}</td>
                <td>${item.protocol}</td>
                <td>${item.bytes_sent}</td>
                <td>${item.bytes_received}</td>
            </tr>
        `);
    });
}

// Chart functions
function loadDevicePieChart(pid) {
    let url = '/api/device_stats';
    if (pid) url += `?pid=${pid}`;

    $.getJSON(url, function(data) {
        renderDevicePieChart(data);
    });
}

function renderDevicePieChart(data) {
    if (data.length === 0) {
        $('#device-pie-chart').html('<div class="alert alert-info">Δεν βρέθηκαν δεδομένα</div>');
        return;
    }

    // Prepare data for pie chart
    const chartData = data.map(item => ({
        name: item.device,
        y: item.count
    }));

    // Create the chart
    Highcharts.chart('device-pie-chart', {
        chart: {
            type: 'pie'
        },
        title: {
            text: 'Συχνότητα πρόσβασης συσκευών'
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    enabled: true,
                    format: '<b>{point.name}</b>: {point.percentage:.1f} %'
                }
            }
        },
        series: [{
            name: 'Πρόσβαση',
            colorByPoint: true,
            data: chartData
        }]
    });
}

function loadEventPieChart(pid, device) {
    let url = '/api/event_stats';
    let params = [];
    if (pid) params.push(`pid=${pid}`);
    if (device) params.push(`device=${device}`);
    if (params.length > 0) url += '?' + params.join('&');

    $.getJSON(url, function(data) {
        renderEventPieChart(data);
    });
}

function renderEventPieChart(data) {
    if (data.length === 0) {
        $('#event-pie-chart').html('<div class="alert alert-info">Δεν βρέθηκαν δεδομένα</div>');
        return;
    }

    // Prepare data for pie chart
    const chartData = data.map(item => ({
        name: item.event,
        y: item.count,
        color: eventColors[item.category] || eventColors.other
    }));

    // Create the chart
    Highcharts.chart('event-pie-chart', {
        chart: {
            type: 'pie'
        },
        title: {
            text: 'Συχνότητα συμβάντων'
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    enabled: true,
                    format: '<b>{point.name}</b>: {point.percentage:.1f} %'
                }
            }
        },
        series: [{
            name: 'Συμβάντα',
            colorByPoint: true,
            data: chartData
        }]
    });
}