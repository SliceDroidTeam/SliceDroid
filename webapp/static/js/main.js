// Global variables
let timelineData = [];
let zoomLevel = 1;
let eventColors = {};
let appConfig = {};

// DOM ready
$(document).ready(function() {
    // Load configuration first, then data
    loadConfiguration().then(function() {
        loadAllData();
        setupEventListeners();
    }).catch(function(error) {
        console.error('Failed to load configuration:', error);
        // Use fallback configuration
        setFallbackConfiguration();
        loadAllData();
        setupEventListeners();
    });
});

// Load app configuration from server
function loadConfiguration() {
    return $.getJSON('/api/config')
        .done(function(config) {
            appConfig = config;
            eventColors = config.event_categories || {};
            zoomLevel = config.default_zoom || 1;
        });
}

// Fallback configuration if server config fails
function setFallbackConfiguration() {
    eventColors = {
        'read': '#28a745',
        'write': '#007bff',
        'ioctl': '#6f42c1',
        'binder': '#fd7e14',
        'network': '#17a2b8',
        'other': '#6c757d'
    };
    appConfig = {
        timeline_max_events: 1000,
        default_zoom: 1.0,
        top_devices: 10,
        top_events: 10
    };
}

// Setup event listeners
function setupEventListeners() {
    $('#apply-filters').click(loadAllData);
    $('#reset-filters').click(resetFilters);
    $('#zoom-in').click(zoomIn);
    $('#zoom-out').click(zoomOut);
    $('#reset-zoom').click(resetZoom);
    
    // Upload functionality
    $('#trace-file-input').change(handleFileSelection);
    $('#upload-btn').click(handleUpload);
    
    // Advanced analytics
    $('#load-analytics-btn').click(loadAdvancedAnalytics);
}

// Load all data based on current filters
function loadAllData() {
    const pid = $('#pid-filter').val();
    const device = $('#device-filter').val();

    // Load timeline data
    loadTimelineData(pid, device);

    // Load statistics
    loadDeviceStats(pid);
    loadEventStats(pid, device);
    loadStatsSummary(pid, device);

    // Load charts
    loadDevicePieChart(pid);
    loadEventPieChart(pid, device);
    
    // Auto-load advanced analytics
    loadAdvancedAnalytics();
}

function loadStatsSummary(pid, device) {
    // Build API URL with parameters
    let url = '/api/device_stats';
    let params = [];
    if (pid) params.push(`pid=${pid}`);
    if (device) params.push(`device=${device}`);
    if (params.length > 0) url += '?' + params.join('&');

    $.getJSON(url, function(deviceData) {
        // Also get event stats for more comprehensive summary
        let eventUrl = '/api/event_stats';
        if (params.length > 0) eventUrl += '?' + params.join('&');
        
        $.getJSON(eventUrl, function(eventData) {
            const summaryData = calculateSummaryFromData(deviceData, eventData);
            renderStatsSummary(summaryData);
            renderTopDevicesChart(summaryData.topDevices);
        }).fail(function() {
            showError('Failed to load event statistics');
        });
    }).fail(function() {
        showError('Failed to load device statistics');
    });
}

// Show error message
function showError(message) {
    console.error(message);
    const errorHtml = `<div class="alert alert-danger">${message}</div>`;
    $('#stats-summary-table tbody').html(`<tr><td colspan="2">${errorHtml}</td></tr>`);
}

// Calculate summary statistics from actual data
function calculateSummaryFromData(deviceData, eventData) {
    const totalDevices = deviceData.length;
    const totalEvents = eventData.reduce((sum, item) => sum + item.count, 0);
    
    // Find most used event type
    const mostUsedEvent = eventData.length > 0 ? eventData[0] : { event: 'none', count: 0 };
    
    // Get top devices (limit based on config)
    const topN = appConfig.top_devices || 5;
    const topDevices = deviceData.slice(0, topN).map(d => ({
        device: d.device,
        count: d.count
    }));
    
    return {
        totalEvents: totalEvents,
        totalEventTypes: eventData.length,
        totalUniqueDevices: totalDevices,
        mostUsedEvent: {
            name: mostUsedEvent.event,
            count: mostUsedEvent.count
        },
        topDevices: topDevices
    };
}

// Function to render the top devices chart
function renderTopDevicesChart(topDevices) {
    if (!topDevices || topDevices.length === 0) {
        $('#top-devices-chart-container').html('<div class="alert alert-info">No data found</div>');
        return;
    }

    const chartData = topDevices.map(device => ({
        label: `Device ${device.device}`,
        value: device.count
    }));

    createBarChart('top-devices-chart-container', chartData, 
                  `Top ${appConfig.top_devices || 5} Devices by Usage`, 
                  'Device ID', 'Count');
}

// Function to render the statistics summary table
function renderStatsSummary(data) {
    const tableBody = $('#stats-summary-table tbody');
    tableBody.empty();

    // Add rows to the table
    tableBody.append(`
        <tr>
            <td><strong>Total Events</strong></td>
            <td>${data.totalEvents}</td>
        </tr>
        <tr>
            <td><strong>Event Types</strong></td>
            <td>${data.totalEventTypes}</td>
        </tr>
        <tr>
            <td><strong>Unique Devices</strong></td>
            <td>${data.totalUniqueDevices}</td>
        </tr>
        <tr>
            <td><strong>Most Used Event</strong></td>
            <td>${data.mostUsedEvent.name} (${data.mostUsedEvent.count} times)</td>
        </tr>
    `);

    // Add top devices as a list in a single row
    const topN = appConfig.top_devices || 5;
    let topDevicesHtml = '<ul class="list-unstyled mb-0">';
    data.topDevices.forEach(device => {
        topDevicesHtml += `<li>Device ${device.device}: ${device.count} events</li>`;
    });
    topDevicesHtml += '</ul>';

    tableBody.append(`
        <tr>
            <td><strong>Top ${topN} Devices</strong></td>
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
        if (data.error) {
            showError(`Timeline error: ${data.error}`);
            return;
        }
        timelineData = data;
        renderTimeline();
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load timeline data';
        showError(errorMsg);
    });
}

function renderTimeline() {
    // Clear existing timeline
    d3.select('#timeline-container').html('');

    if (timelineData.length === 0) {
        d3.select('#timeline-container')
            .append('div')
            .attr('class', 'alert alert-info')
            .text('No data found for the selected filters.');
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
        deviceInfo = `<strong>Device:</strong> ${d.device}<br>`;
    }

    let pathnameInfo = '';
    if (d.pathname) {
        pathnameInfo = `<strong>Path:</strong> ${d.pathname}<br>`;
    }

    tooltip.html(`
        <strong>Event:</strong> ${d.event}<br>
        <strong>Category:</strong> ${d.category}<br>
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
        if (data.error) {
            showError(`Device stats error: ${data.error}`);
            return;
        }
        renderDeviceStats(data);
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load device statistics';
        showError(errorMsg);
    });
}

function renderDeviceStats(data) {
    const tableBody = $('#device-stats-table tbody');
    tableBody.empty();

    if (data.length === 0) {
        tableBody.append('<tr><td colspan="4" class="text-center">No data found</td></tr>');
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
        if (data.error) {
            showError(`Event stats error: ${data.error}`);
            return;
        }
        renderEventStats(data);
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load event statistics';
        showError(errorMsg);
    });
}

function renderEventStats(data) {
    const tableBody = $('#event-stats-table tbody');
    tableBody.empty();

    if (data.length === 0) {
        tableBody.append('<tr><td colspan="3" class="text-center">No data found</td></tr>');
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

// Chart functions
function loadDevicePieChart(pid) {
    let url = '/api/device_stats';
    if (pid) url += `?pid=${pid}`;

    $.getJSON(url, function(data) {
        if (data.error) {
            showError(`Device chart error: ${data.error}`);
            return;
        }
        renderDevicePieChart(data);
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load device chart data';
        showError(errorMsg);
    });
}

function renderDevicePieChart(data) {
    if (data.length === 0) {
        $('#device-chart-container').html('<div class="alert alert-info">No data found</div>');
        return;
    }

    // Prepare data for pie chart (top N devices)
    const topN = appConfig.top_devices || 10;
    const topDevices = data.slice(0, topN);
    const chartData = topDevices.map(item => ({
        label: `Device ${item.device}`,
        value: item.count
    }));

    createPieChart('device-chart-container', chartData, 'Device Usage Distribution');
}

function loadEventPieChart(pid, device) {
    let url = '/api/event_stats';
    let params = [];
    if (pid) params.push(`pid=${pid}`);
    if (device) params.push(`device=${device}`);
    if (params.length > 0) url += '?' + params.join('&');

    $.getJSON(url, function(data) {
        if (data.error) {
            showError(`Event chart error: ${data.error}`);
            return;
        }
        renderEventPieChart(data);
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load event chart data';
        showError(errorMsg);
    });
}

function renderEventPieChart(data) {
    if (data.length === 0) {
        $('#event-chart-container').html('<div class="alert alert-info">No data found</div>');
        return;
    }

    // Prepare data for pie chart (top N events)
    const topN = appConfig.top_events || 10;
    const topEvents = data.slice(0, topN);
    const chartData = topEvents.map(item => ({
        label: item.event,
        value: item.count
    }));

    createPieChart('event-chart-container', chartData, 'Event Type Distribution');
}

// Upload functionality
function handleFileSelection() {
    const fileInput = $('#trace-file-input')[0];
    const uploadBtn = $('#upload-btn');
    
    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        if (file.name.endsWith('.trace')) {
            uploadBtn.prop('disabled', false);
            hideUploadResult();
        } else {
            uploadBtn.prop('disabled', true);
            showUploadError('Please select a .trace file');
        }
    } else {
        uploadBtn.prop('disabled', true);
    }
}

function handleUpload() {
    const fileInput = $('#trace-file-input')[0];
    
    if (fileInput.files.length === 0) {
        showUploadError('Please select a file');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('trace_file', file);
    
    // Show progress
    showUploadProgress();
    $('#upload-btn').prop('disabled', true);
    
    // Upload file
    $.ajax({
        url: '/api/upload',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.upload_id) {
                checkUploadProgress(response.upload_id);
            } else {
                showUploadError('Upload failed: No upload ID received');
                resetUploadUI();
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON?.error || 'Upload failed';
            showUploadError(error);
            resetUploadUI();
        }
    });
}

function checkUploadProgress(uploadId) {
    const checkProgress = () => {
        $.get(`/api/upload/progress/${uploadId}`)
            .done(function(data) {
                updateProgressBar(data.progress);
                updateProgressStatus(data.status);
                
                if (data.completed) {
                    if (data.error) {
                        showUploadError(data.error);
                    } else if (data.result && data.result.success) {
                        showUploadSuccess(data.result);
                        // Reload data after successful processing
                        setTimeout(() => {
                            loadAllData();
                        }, 1000);
                    } else {
                        showUploadError(data.result?.error || 'Processing failed');
                    }
                    resetUploadUI();
                } else {
                    // Continue checking progress
                    setTimeout(checkProgress, 1000);
                }
            })
            .fail(function() {
                showUploadError('Failed to check upload progress');
                resetUploadUI();
            });
    };
    
    checkProgress();
}

function showUploadProgress() {
    $('#upload-progress').show();
    $('#upload-result').hide();
    updateProgressBar(0);
    updateProgressStatus('Starting upload...');
}

function updateProgressBar(progress) {
    $('#progress-bar').css('width', progress + '%').attr('aria-valuenow', progress);
}

function updateProgressStatus(status) {
    $('#upload-status').text(status);
}

function showUploadSuccess(result) {
    $('#upload-progress').hide();
    $('#upload-result').show();
    $('#upload-alert')
        .removeClass('alert-danger')
        .addClass('alert-success')
        .html(`
            <strong>Success!</strong> ${result.message}<br>
            <small>
                Events processed: ${result.events_count}<br>
                Target PID: ${result.target_pid}<br>
                Output file: ${result.json_file}
            </small>
        `);
}

function showUploadError(error) {
    $('#upload-progress').hide();
    $('#upload-result').show();
    $('#upload-alert')
        .removeClass('alert-success')
        .addClass('alert-danger')
        .html(`<strong>Error:</strong> ${error}`);
}

function hideUploadResult() {
    $('#upload-result').hide();
}

function resetUploadUI() {
    $('#upload-btn').prop('disabled', false);
    $('#trace-file-input').val('');
    $('#upload-btn').prop('disabled', true);
}

// Advanced Analytics functionality
function loadAdvancedAnalytics() {
    const pid = $('#pid-filter').val();
    let url = '/api/advanced-analytics';
    if (pid) url += `?pid=${pid}`;
    
    // Show loading
    $('#analytics-loading').show();
    $('#analytics-content').hide();
    $('#analytics-error').hide();
    $('#load-analytics-btn').prop('disabled', true);
    
    $.getJSON(url, function(data) {
        if (data.error) {
            showAnalyticsError(data.error);
        } else {
            renderAdvancedAnalytics(data);
        }
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load advanced analytics';
        showAnalyticsError(errorMsg);
    }).always(function() {
        $('#analytics-loading').hide();
        $('#load-analytics-btn').prop('disabled', false);
    });
}

function renderAdvancedAnalytics(data) {
    $('#analytics-content').show();
    
    // Render summary cards
    renderAnalyticsSummary(data);
    
    // Render charts
    renderAnalyticsCharts(data.charts);
    
    // Render detailed insights
    renderDetailedInsights(data);
}

function renderAnalyticsSummary(data) {
    const summaryContainer = $('#analytics-summary');
    summaryContainer.empty();
    
    // Create summary cards
    const summaryCards = [
        {
            title: 'Target PID',
            value: data.target_pid || 'N/A',
            icon: 'fas fa-bullseye',
            color: 'primary'
        },
        {
            title: 'Total Events',
            value: data.total_events?.toLocaleString() || '0',
            icon: 'fas fa-list',
            color: 'success'
        },
        {
            title: 'Unique Processes',
            value: data.process_analysis?.unique_processes || '0',
            icon: 'fas fa-cogs',
            color: 'info'
        },
        {
            title: 'Unique Devices',
            value: data.device_analysis?.unique_devices || '0',
            icon: 'fas fa-hdd',
            color: 'warning'
        },
        {
            title: 'Duration',
            value: data.time_range?.duration ? `${data.time_range.duration.toFixed(2)}s` : 'N/A',
            icon: 'fas fa-clock',
            color: 'secondary'
        },
        {
            title: 'Events/Second',
            value: data.temporal_patterns?.events_per_second ? 
                   data.temporal_patterns.events_per_second.toFixed(2) : 'N/A',
            icon: 'fas fa-tachometer-alt',
            color: 'danger'
        }
    ];
    
    summaryCards.forEach(card => {
        summaryContainer.append(`
            <div class="col-md-2 mb-3">
                <div class="card border-${card.color}">
                    <div class="card-body text-center">
                        <i class="${card.icon} fa-2x text-${card.color} mb-2"></i>
                        <h5 class="card-title">${card.value}</h5>
                        <small class="text-muted">${card.title}</small>
                    </div>
                </div>
            </div>
        `);
    });
}

function renderAnalyticsCharts(charts) {
    if (!charts) return;
    
    // Render each chart
    if (charts.behavior_timeline) {
        $('#behavior-timeline-chart').html(`<img src="${charts.behavior_timeline}" class="img-fluid" alt="High-Level Behavior Timeline">`);
    } else {
        $('#behavior-timeline-chart').html('<div class="alert alert-info">No behavior timeline data available</div>');
    }
    
    if (charts.category_distribution) {
        $('#category-chart').html(`<img src="${charts.category_distribution}" class="img-fluid" alt="Category Distribution">`);
    } else {
        $('#category-chart').html('<div class="alert alert-info">No category data available</div>');
    }
    
    if (charts.device_usage) {
        $('#device-usage-chart').html(`<img src="${charts.device_usage}" class="img-fluid" alt="Device Usage">`);
    } else {
        $('#device-usage-chart').html('<div class="alert alert-info">No device usage data available</div>');
    }
    
    if (charts.process_activity) {
        $('#process-activity-chart').html(`<img src="${charts.process_activity}" class="img-fluid" alt="Process Activity">`);
    } else {
        $('#process-activity-chart').html('<div class="alert alert-info">No process activity data available</div>');
    }
    
    if (charts.network_activity) {
        $('#network-chart').html(`<img src="${charts.network_activity}" class="img-fluid" alt="Network Activity">`);
    } else {
        $('#network-chart').html('<div class="alert alert-info">No network activity data available</div>');
    }
}

function renderDetailedInsights(data) {
    const insightsContainer = $('#detailed-insights');
    insightsContainer.empty();
    
    if (!data.detailed_insights || Object.keys(data.detailed_insights).length === 0) {
        insightsContainer.html('<div class="alert alert-info">No detailed insights available</div>');
        return;
    }
    
    let insights = '<div class="accordion" id="insightsAccordion">';
    
    // Render insights from backend
    Object.entries(data.detailed_insights).forEach(([key, insightData]) => {
        insights += createInsightSection(key, insightData.title, 
            generateInsightContent(insightData.insights));
    });
    
    insights += '</div>';
    insightsContainer.html(insights);
}

function generateInsightContent(insights) {
    if (!insights || insights.length === 0) {
        return '<div class="alert alert-info">No insights available</div>';
    }
    
    let content = '<ul class="list-group list-group-flush">';
    insights.forEach(insight => {
        content += `<li class="list-group-item">${insight.icon} ${insight.text}</li>`;
    });
    content += '</ul>';
    return content;
}

function createInsightSection(id, title, content) {
    return `
        <div class="accordion-item">
            <h2 class="accordion-header">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" 
                        data-bs-target="#collapse${id}" aria-expanded="false">
                    ${title}
                </button>
            </h2>
            <div id="collapse${id}" class="accordion-collapse collapse" data-bs-parent="#insightsAccordion">
                <div class="accordion-body">
                    ${content}
                </div>
            </div>
        </div>
    `;
}

function showAnalyticsError(error) {
    $('#analytics-error').html(`<strong>Error:</strong> ${error}`).show();
}