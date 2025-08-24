// Global variables
let behaviorTimelineData = [];
let behaviorZoomLevel = 1;
let eventColors = {};
let appConfig = {};
let securityData = {};
let networkData = {};
let processData = {};

// DOM ready
$(document).ready(function() {
    // Initialize UI first
    initializeUI();
    
    updateAppStatus('loading', 'Loading...');

    // Load configuration first, then data
    loadConfiguration().then(function() {
        updateAppStatus('success', 'System Ready');
        // Skip loading trace data automatically
        setupEventListeners();
        
        // Initialize upload functionality
        initializeUploadFunctionality();
        
        // Initialize app selection
        initializeAppSelection();
    }).catch(function(error) {
        console.error('Failed to load configuration:', error);
        updateAppStatus('warning', 'Fallback Mode');
        // Use fallback configuration
        setFallbackConfiguration();
        // Skip loading trace data automatically
        setupEventListeners();
        
        // Initialize upload functionality
        initializeUploadFunctionality();
        
        // Initialize app selection
        initializeAppSelection();
    });
});

// Load app configuration from server
function loadConfiguration() {
    console.log('Loading configuration...');
    return $.ajax({
        url: '/api/config',
        method: 'GET',
        timeout: 10000,
        dataType: 'json'
    })
    .done(function(config) {
        console.log('Configuration loaded successfully:', config);
        appConfig = config;
        eventColors = config.event_categories || {};
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load configuration:', textStatus, errorThrown, jqXHR);
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
    // Upload functionality is now handled in inline script

    // Advanced analytics
    $('#load-analytics-btn').click(loadAdvancedAnalytics);
    $('#apply-analytics-config').click(loadAdvancedAnalyticsWithConfig);
    
    // Also bind to the actual configure button
    $(document).on('click', '#apply-analytics-config', loadAdvancedAnalyticsWithConfig);

}

// Load all data
function loadAllData() {
    // Show loading state for main sections
    showSectionLoading();

    try {
        // Load statistics
        loadDeviceStats();
        loadEventStats();

        // Load charts
        loadDevicePieChart();
        loadEventPieChart();

        // Auto-load advanced analytics
        loadAdvancedAnalytics();
        
        // Load new enhanced analysis
        loadNetworkAnalysis();
    } catch (error) {
        console.error('Error loading data:', error);
        showToast('Loading Error', 'Failed to load some data sections', 'error');
    }
}

function showSectionLoading() {
    // Add loading indicators to main sections
    $('#device-stats-table tbody').html('<tr><td colspan="5" class="text-center"><div class="loading-spinner"></div> Loading...</td></tr>');
    $('#event-stats-table tbody').html('<tr><td colspan="3" class="text-center"><div class="loading-spinner"></div> Loading...</td></tr>');
}

// Show error message
function showError(message) {
    console.error(message);
    showToast('Error', message, 'error');
}

// Behavior Timeline zoom functions
function behaviorZoomIn() {
    behaviorZoomLevel = Math.min(behaviorZoomLevel * 1.5, 10);
    renderBehaviorTimelineChart();
}

function behaviorZoomOut() {
    behaviorZoomLevel = Math.max(behaviorZoomLevel / 1.5, 1);
    renderBehaviorTimelineChart();
}

function behaviorResetZoom() {
    behaviorZoomLevel = 1;
    renderBehaviorTimelineChart();
}

// Behavior Timeline function (creates timeline from SliceDroid reconstruction)
function renderBehaviorTimeline(analysisData) {
    const container = document.getElementById('behavior-timeline-chart');
    if (!container) return;

    // Clear existing content
    container.innerHTML = '';

    // First check if we have valid analysis data
    if (!analysisData || typeof analysisData !== 'object') {
        container.innerHTML = '<div class="alert alert-info">No analysis data available. Please analyze an app first.</div>';
        return;
    }

    // Extract comprehensive analytics data (from SliceDroid reconstruction)
    const comprehensiveAnalytics = analysisData.comprehensive_analytics;
    
    if (!comprehensiveAnalytics) {
        container.innerHTML = '<div class="alert alert-info">No behavior timeline data available - comprehensive analysis not performed</div>';
        return;
    }

    // Get window data from SliceDroid reconstruction
    const kdevsTrace = comprehensiveAnalytics.kdevs_trace || [];
    const tcpTrace = comprehensiveAnalytics.TCP_trace || [];
    const sensitiveTrace = comprehensiveAnalytics.sensitive_data_trace || {};
    
    if (kdevsTrace.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No behavior windows found</div>';
        return;
    }

    // Load device category mapping from file
    let dev2cat = {};
    
    // Load the category mapping asynchronously
    console.log('Loading device category mapping...');
    fetch('/data/mappings/cat2devs.txt')
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(categoryMapping => {
            console.log('Category mapping loaded successfully:', Object.keys(categoryMapping).length, 'categories');
            // Convert category-to-devices mapping to device-to-category mapping
            Object.keys(categoryMapping).forEach(category => {
                categoryMapping[category].forEach(deviceId => {
                    // Handle both string and numeric device IDs
                    // For strings like "124845621 - 5421", use the whole string as key
                    let deviceKey;
                    if (typeof deviceId === 'string' && deviceId.includes(' - ')) {
                        deviceKey = deviceId; // Keep compound IDs as strings
                    } else {
                        deviceKey = parseInt(deviceId) || deviceId;
                    }
                    dev2cat[deviceKey] = category;
                });
            });
            
            // Now process the timeline data with the loaded mapping
            processBehaviorTimelineData(kdevsTrace, tcpTrace, sensitiveTrace, dev2cat);
        })
        .catch(error => {
            console.error('Error loading device mapping:', error);
            container.innerHTML = '<div class="alert alert-warning">Could not load device category mapping. Behavior timeline unavailable.</div>';
        });
}

// Separate function to process behavior timeline data
function processBehaviorTimelineData(kdevsTrace, tcpTrace, sensitiveTrace, dev2cat) {
    console.log('processBehaviorTimelineData called');
    const container = document.getElementById('behavior-timeline-chart');
    console.log('Container found:', container);
    if (!container) {
        console.log('Container not found, returning');
        return;
    }

    // Create behavior timeline from window data (similar to legacy code)
    behaviorTimelineData = [];
    
    // Process each window
    kdevsTrace.forEach((kdevWindow, windowIndex) => {
        const windowCategories = [];
        
        // Process device events in this window
        Object.keys(kdevWindow).forEach(kdev => {
            const count = kdevWindow[kdev];
            
            // Try to map device to category - check both numeric and string forms
            let category = null;
            const deviceIdNum = parseInt(kdev);
            const deviceIdStr = kdev.toString();
            
            if (deviceIdNum in dev2cat) {
                category = dev2cat[deviceIdNum];
            } else if (deviceIdStr in dev2cat) {
                category = dev2cat[deviceIdStr];
            }
            
            // Skip unknown devices
            if (!category) {
                return;
            }
            
            // Add category to this window if not already present
            if (!windowCategories.includes(category)) {
                windowCategories.push(category);
                
                behaviorTimelineData.push({
                    timestamp: windowIndex,
                    windowIndex: windowIndex,
                    type: 'device',
                    category: category,
                    process: 'system',
                    details: `${category} Activity (Device ${kdev}, ${count} events)`,
                    deviceId: kdev,
                    count: count
                });
            }
        });
        
        // Add TCP events for this window
        if (tcpTrace[windowIndex] && tcpTrace[windowIndex].length > 0) {
            tcpTrace[windowIndex].forEach(tcpEvent => {
                const tcpDetails = tcpEvent.details || {};
                const state = tcpDetails.newstate || 'UNKNOWN';
                const daddr = tcpDetails.daddr || 'unknown';
                
                behaviorTimelineData.push({
                    timestamp: windowIndex + 0.1, // Slight offset to show after device events
                    windowIndex: windowIndex,
                    type: 'network',
                    category: 'TCP',
                    process: tcpEvent.process || 'network',
                    details: `${state}: ${daddr}`,
                    tcpState: state,
                    targetAddr: daddr
                });
            });
        }
        
        // Add sensitive data events for this window
        Object.keys(sensitiveTrace).forEach(sensitiveType => {
            if (sensitiveTrace[sensitiveType] && 
                sensitiveTrace[sensitiveType][windowIndex] && 
                sensitiveTrace[sensitiveType][windowIndex].length > 0) {
                
                // Get the actual sensitive events for this specific window
                const windowEvents = sensitiveTrace[sensitiveType][windowIndex];
                
                if (windowEvents.length > 0) {
                    behaviorTimelineData.push({
                        timestamp: windowIndex + 0.2, // Offset for sensitive events
                        windowIndex: windowIndex,
                        type: 'sensitive',
                        category: sensitiveType,
                        process: 'system',
                        details: `${sensitiveType.charAt(0).toUpperCase() + sensitiveType.slice(1)} Access (${windowEvents.length} events)`,
                        count: windowEvents.length
                    });
                }
            }
        });
    });

    // Sort events by timestamp (window order)
    behaviorTimelineData.sort((a, b) => a.timestamp - b.timestamp);

    if (behaviorTimelineData.length === 0) {
        if (container) {
            container.innerHTML = '<div class="alert alert-info">No behavior events found in reconstruction windows</div>';
        }
        return;
    }

    renderBehaviorTimelineChart();
}

function renderBehaviorTimelineChart() {
    const container = document.getElementById('behavior-timeline-chart');
    if (!container || behaviorTimelineData.length === 0) return;

    // Clear existing content
    container.innerHTML = '';

    // Apply zoom to data
    const visibleDataCount = Math.ceil(behaviorTimelineData.length / behaviorZoomLevel);
    const visibleData = behaviorTimelineData.slice(0, visibleDataCount);

    // Create timeline visualization similar to Event Timeline
    const containerWidth = container.clientWidth || 800;
    const containerHeight = 300;
    const margin = {top: 20, right: 20, bottom: 50, left: 100};
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    // Create SVG
    const svg = d3.select(container)
        .append('svg')
        .attr('width', containerWidth)
        .attr('height', containerHeight)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Define categories and colors for behavior timeline (based on legacy SliceDroid code)
    const categories = ['camera', 'audio_in', 'TCP', 'bluetooth', 'nfc', 'gnss', 'contacts', 'sms', 'calendar', 'call_logs'];
    const categoryColors = {
        'camera': '#007bff',      // Blue
        'audio_in': '#dc3545',    // Red
        'TCP': '#28a745',         // Green  
        'bluetooth': '#6c757d',   // Grey
        'nfc': '#e83e8c',         // Magenta/Pink
        'gnss': '#343a40',        // Black/Dark
        'contacts': '#fd7e14',    // Orange
        'sms': '#ffc107',         // Yellow
        'calendar': '#17a2b8',    // Cyan
        'call_logs': '#6f42c1',   // Purple
    };

    // Set up scales
    const timeScale = d3.scaleLinear()
        .domain([0, visibleData.length - 1])
        .range([0, width]);

    const categoryScale = d3.scaleBand()
        .domain(categories)
        .range([0, height])
        .padding(0.1);

    // Add background stripes for categories
    categories.forEach(category => {
        svg.append('rect')
            .attr('x', 0)
            .attr('y', categoryScale(category))
            .attr('width', width)
            .attr('height', categoryScale.bandwidth())
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
        .attr('y', d => categoryScale(d) + categoryScale.bandwidth() / 2)
        .attr('text-anchor', 'end')
        .attr('dominant-baseline', 'middle')
        .style('font-size', '12px')
        .style('font-weight', 'bold')
        .text(d => d.charAt(0).toUpperCase() + d.slice(1));

    // Add events as circles
    svg.selectAll('.event-dot')
        .data(visibleData)
        .enter()
        .append('circle')
        .attr('class', 'event-dot')
        .attr('cx', (d, i) => timeScale(i))
        .attr('cy', d => categoryScale(d.category) + categoryScale.bandwidth() / 2)
        .attr('r', 4)
        .attr('fill', d => categoryColors[d.category] || '#6c757d')
        .attr('stroke', '#fff')
        .attr('stroke-width', 1)
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            // Show tooltip
            const tooltip = d3.select('body').append('div')
                .attr('class', 'timeline-tooltip')
                .style('position', 'absolute')
                .style('background', '#333')
                .style('color', '#fff')
                .style('padding', '8px')
                .style('border-radius', '4px')
                .style('font-size', '12px')
                .style('pointer-events', 'none')
                .style('z-index', '1000')
                .html(`
                    <strong>${d.details}</strong><br>
                    Category: ${d.category}<br>
                    Process: ${d.process}<br>
                    Timestamp: ${d.timestamp.toFixed(6)}
                `);

            tooltip.style('left', (event.pageX + 10) + 'px')
                   .style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', function() {
            d3.selectAll('.timeline-tooltip').remove();
        });

    // Add x-axis
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(timeScale).ticks(10).tickFormat(d => `Window ${Math.floor(d)}`));

    // Add title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', -5)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('font-weight', 'bold')
        .text(`Behavior Timeline (${behaviorTimelineData.length} events, showing ${visibleData.length})`);
}

// Statistics functions
function loadDeviceStats() {
    $.getJSON('/api/device_stats', function(data) {
        if (data && data.error) {
            $('#device-stats-table tbody').html(`<tr><td colspan="5" class="text-center text-danger">Error: ${data.error}</td></tr>`);
            return;
        }
        renderDeviceStats(data);
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load device statistics';
        $('#device-stats-table tbody').html(`<tr><td colspan="5" class="text-center text-danger">Error: ${errorMsg}</td></tr>`);
        console.error('Device stats error:', errorMsg);
    });
}

function renderDeviceStats(data) {
    const tableBody = $('#device-stats-table tbody');

    if (tableBody.length === 0) {
        console.error('Device stats table body not found!');
        return;
    }

    tableBody.empty();

    if (!data || !Array.isArray(data) || data.length === 0) {
        tableBody.html('<tr><td colspan="5" class="text-center">No data found</td></tr>');
        return;
    }

    // Calculate total events for percentage calculation
    const totalEvents = data.reduce((sum, item) => sum + (item.count || 0), 0);

    let html = '';
    data.forEach(item => {
        const paths = Array.isArray(item.paths) ? item.paths.join(', ') : '';
        const pathCount = Array.isArray(item.paths) ? item.paths.length : 0;
        const eventCount = item.count || 0;
        const percentage = totalEvents > 0 ? ((eventCount / totalEvents) * 100).toFixed(1) : '0.0';
        
        html += `
            <tr>
                <td>${item.device || 'Unknown'}</td>
                <td>${eventCount}</td>
                <td>${percentage}%</td>
                <td>${pathCount}</td>
                <td title="${paths}">${paths.length > 50 ? paths.substring(0, 50) + '...' : paths}</td>
            </tr>
        `;
    });
    tableBody.html(html);
}

function loadEventStats() {
    $.getJSON('/api/event_stats', function(data) {
        if (data && data.error) {
            $('#event-stats-table tbody').html(`<tr><td colspan="3" class="text-center text-danger">Error: ${data.error}</td></tr>`);
            return;
        }
        renderEventStats(data);
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load event statistics';
        $('#event-stats-table tbody').html(`<tr><td colspan="3" class="text-center text-danger">Error: ${errorMsg}</td></tr>`);
        console.error('Event stats error:', errorMsg);
    });
}

function renderEventStats(data) {
    const tableBody = $('#event-stats-table tbody');

    if (tableBody.length === 0) {
        console.error('Event stats table body not found!');
        return;
    }

    tableBody.empty();

    if (!data || !Array.isArray(data) || data.length === 0) {
        tableBody.html('<tr><td colspan="3" class="text-center">No data found</td></tr>');
        return;
    }

    const totalEvents = data.reduce((sum, item) => sum + (item.count || 0), 0);

    let html = '';
    data.forEach(item => {
        const count = item.count || 0;
        const percentage = totalEvents > 0 ? ((count / totalEvents) * 100).toFixed(2) : '0.00';
        html += `
            <tr>
                <td>${item.event || 'Unknown'}</td>
                <td>${count}</td>
                <td>${percentage}%</td>
            </tr>
        `;
    });
    tableBody.html(html);
}

// Chart functions
function loadDevicePieChart() {
    $.getJSON('/api/device_stats', function(data) {
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
    
    // Create more meaningful labels for devices
    const chartData = topDevices.map(item => {
        let deviceLabel = `Device ${item.device}`;
        
        // Try to infer device type from paths if available
        if (item.paths && Array.isArray(item.paths) && item.paths.length > 0) {
            const paths = item.paths;
            if (paths.some(path => path.includes('/dev/video'))) {
                deviceLabel = `Camera (${item.device})`;
            } else if (paths.some(path => path.includes('/dev/snd'))) {
                deviceLabel = `Audio (${item.device})`;
            } else if (paths.some(path => path.includes('/dev/input'))) {
                deviceLabel = `Input (${item.device})`;
            } else if (paths.some(path => path.includes('/dev/block'))) {
                deviceLabel = `Storage (${item.device})`;
            } else if (paths.some(path => path.includes('/dev/net'))) {
                deviceLabel = `Network (${item.device})`;
            }
        }
        
        return {
            label: deviceLabel,
            value: item.count
        };
    });

    createPieChart('device-chart-container', chartData, 'Device Usage Distribution');
}

function loadEventPieChart() {
    $.getJSON('/api/event_stats', function(data) {
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
    
    // Create more readable labels for event types
    const chartData = topEvents.map(item => {
        let eventLabel = item.event;
        
        // Format event names to be more readable
        if (eventLabel) {
            eventLabel = eventLabel
                .replace(/_/g, ' ')  // Replace underscores with spaces
                .replace(/\b\w/g, l => l.toUpperCase());  // Capitalize first letter of each word
        }
        
        return {
            label: eventLabel,
            value: item.count
        };
    });

    createPieChart('event-chart-container', chartData, 'Event Type Distribution');
}

// Upload functionality is now handled in inline script

function loadAdvancedAnalytics() {
    let url = '/api/advanced-analytics';

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

    try {
        // Render summary cards
        renderAnalyticsSummary(data);

        // Render charts
        renderAnalyticsCharts(data.charts, data);

        // Render detailed insights
        renderDetailedInsights(data);

    } catch (error) {
        console.error('Error rendering analytics:', error);
        showToast('Rendering Error', 'Failed to display some analytics results', 'error');
    }
}

function renderAnalyticsSummary(data) {
    const summaryContainer = $('#analytics-summary');
    summaryContainer.empty();

    // Create summary cards
    const summaryCards = [
        {
            title: 'Analyzed PID',
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
            title: 'Processes',
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

function renderAnalyticsCharts(charts, analysisData) {
    if (!charts) return;

    // Render behavior timeline similar to event timeline
    renderBehaviorTimeline(analysisData || {})

    if (charts.category_distribution) {
        $('#category-chart').html(`<img src="${charts.category_distribution}" class="img-fluid" alt="Category Distribution" style="max-height: 350px; max-width: 100%; object-fit: contain;">`);
    } else {
        $('#category-chart').html('<div class="alert alert-info">No category data available</div>');
    }
    if (charts.network_activity) {
        $('#network-chart').html(`<img src="${charts.network_activity}" class="img-fluid" alt="Network Activity" style="max-width: 100%; max-height: 100%; object-fit: contain;">`);
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

    let insights = '';

    // Render insights from backend directly without accordion structure
    Object.entries(data.detailed_insights).forEach(([key, insightData]) => {
        insights += `
            <div class="mb-4">
                <div class="insight-content">
                    ${generateInsightContent(insightData.insights)}
                </div>
            </div>
        `;
    });

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
                <button class="accordion-button" type="button" data-bs-toggle="collapse"
                        data-bs-target="#collapse${id}" aria-expanded="true">
                    ${title}
                </button>
            </h2>
            <div id="collapse${id}" class="accordion-collapse collapse show" data-bs-parent="#insightsAccordion">
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

function loadAdvancedAnalyticsWithConfig() {
    const windowSize = $('#analytics-window-size').val();
    const overlap = $('#analytics-overlap').val();
    
    // Validation
    if (parseInt(overlap) >= parseInt(windowSize)) {
        showToast('Configuration Error', 'Overlap must be less than window size', 'error');
        return;
    }
    
    // Build URL with parameters
    let url = '/api/advanced-analytics';
    let params = [];
    if (windowSize) params.push(`window_size=${windowSize}`);
    if (overlap) params.push(`overlap=${overlap}`);
    
    if (params.length > 0) {
        url += '?' + params.join('&');
    }
    
    // Show loading
    updateAppStatus('loading', 'Running Custom Analysis...');
    $('#analytics-loading').show();
    $('#analytics-content').hide();
    $('#analytics-error').hide();
    
    $.getJSON(url, function(data) {
        if (data.error) {
            showAnalyticsError(data.error);
        } else {
            renderAdvancedAnalytics(data);
            showToast('Custom Analysis Complete', `Analysis with window size ${windowSize} completed`, 'success');
            // Collapse the config panel after successful run
            $('#analytics-config').collapse('hide');
        }
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load custom analytics';
        showAnalyticsError(errorMsg);
    }).always(function() {
        $('#analytics-loading').hide();
        updateAppStatus('success', 'System Ready');
    });
}


// Enhanced Network Analysis Functions
function loadNetworkAnalysis() {
    let url = '/api/network-analysis';

    // Show loading
    $('#network-loading').show();
    $('#network-content').hide();
    $('#network-error').hide();

    $.getJSON(url, function(data) {
        if (data.error) {
            showNetworkError(data.error);
        } else {
            networkData = data;
            renderNetworkAnalysis(data);
        }
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'No network analysis data available';
        showNetworkError(errorMsg);
    }).always(function() {
        $('#network-loading').hide();
    });
}

function renderNetworkAnalysis(data) {
    $('#network-content').show();
    $('#network-error').hide();
    $('#network-loading').hide();

    // Wait for container to be fully visible before rendering charts
    setTimeout(() => {
        // Render summary cards
        renderNetworkSummary(data);

        // Render MB transferred per protocol chart
        if (document.getElementById('mb-per-protocol-chart') && 
            document.getElementById('mb-per-protocol-chart').offsetWidth > 0) {
            renderMBPerProtocolChart(data.network_analysis);
        } else {
            setTimeout(() => renderMBPerProtocolChart(data.network_analysis), 500);
        }
        
        // Render connection tables
        renderConnectionTables(data.network_analysis);
    }, 200);
}

function renderNetworkSummary(data) {
    const summaryContainer = $('#network-summary');
    summaryContainer.empty();

    if (!data.network_analysis || !data.network_analysis.summary) {
        summaryContainer.html('<div class="col-12"><div class="alert alert-info">No network summary available</div></div>');
        return;
    }

    const summary = data.network_analysis.summary;
    const summaryCards = [
        {
            title: 'TCP Events',
            value: summary.total_tcp_events || 0,
            type: 'info',
            icon: 'fas fa-exchange-alt'
        },
        {
            title: 'UDP Events',
            value: summary.total_udp_events || 0,
            type: 'info',
            icon: 'fas fa-broadcast-tower'
        },
    ];

    summaryCards.forEach(card => {
        summaryContainer.append(`
            <div class="col-md-5 mb-2">
                <div class="summary-card ${card.type}">
                    <div class="card-value">${card.value}</div>
                    <div class="card-label">${card.title}</div>
                </div>
            </div>
        `);
    });
}



function renderMBPerProtocolChart(networkAnalysis) {
    const container = d3.select('#mb-per-protocol-chart');
    container.selectAll('*').remove();
    
    if (!networkAnalysis) {
        container.append('div')
            .attr('class', 'alert alert-info')
            .text('No network analysis data available');
        return;
    }
    
    // Calculate data transfer from network events
    const data = calculateDataTransfer(networkAnalysis);
    
    // Ensure container has proper width before calculating dimensions
    const containerElement = document.getElementById('mb-per-protocol-chart');
    const containerWidth = containerElement.clientWidth || containerElement.offsetWidth || 400;
    
    const margin = {top: 30, right: 30, bottom: 70, left: 60};
    const width = Math.max(300, containerWidth - margin.left - margin.right);
    const height = 400 - margin.top - margin.bottom;
    
    const svg = container.append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom);
        
    const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Prepare data for chart - group by protocol instead of sent/received
    const chartData = [];
    
    // Add TCP data if available
    if (data.tcp) {
        chartData.push({
            protocol: 'TCP', 
            sent: data.tcp.sent_mb || 0, 
            received: data.tcp.received_mb || 0,
            total: (data.tcp.sent_mb || 0) + (data.tcp.received_mb || 0),
            color: '#007bff'
        });
    }
    
    // Add UDP data if available
    if (data.udp) {
        chartData.push({
            protocol: 'UDP', 
            sent: data.udp.sent_mb || 0, 
            received: data.udp.received_mb || 0,
            total: (data.udp.sent_mb || 0) + (data.udp.received_mb || 0),
            color: '#28a745'
        });
    }
    
    
    // Add Bluetooth data if available
    if (data.bluetooth) {
        chartData.push({
            protocol: 'Bluetooth', 
            sent: data.bluetooth.sent_mb || 0, 
            received: data.bluetooth.received_mb || 0,
            total: (data.bluetooth.sent_mb || 0) + (data.bluetooth.received_mb || 0),
            color: '#6f42c1'
        });
    }
    
    if (chartData.length === 0) {
        // Check if we have any network events at all
        if (networkAnalysis.summary && 
            (networkAnalysis.summary.total_tcp_events > 0 || 
             networkAnalysis.summary.total_udp_events > 0)) {
            // We have events but no calculated data transfer
            container.append('div')
                .attr('class', 'alert alert-info')
                .text('Network activity detected but no data size information available');
        } else {
            // No events at all
            container.append('div')
                .attr('class', 'alert alert-info')
                .text('No protocol data transfer detected');
        }
        return;
    }
    
    // Sort by total MB transferred
    chartData.sort((a, b) => b.total - a.total);
    
    const maxValue = d3.max(chartData, d => Math.max(d.sent, d.received)) || 1;
    
    const xScale = d3.scaleBand()
        .domain(chartData.map(d => d.protocol))
        .range([0, width])
        .padding(0.2);
        
    const yScale = d3.scaleLinear()
        .domain([0, maxValue])
        .range([height, 0]);
    
    // Create a grouped bar chart
    const subgroups = ['sent', 'received'];
    const xSubgroup = d3.scaleBand()
        .domain(subgroups)
        .range([0, xScale.bandwidth()])
        .padding(0.05);
    
    const colors = {
        sent: '#007bff',
        received: '#17a2b8'
    };
    
    // Add grouped bars
    g.selectAll('.protocol-group')
        .data(chartData)
        .enter()
        .append('g')
        .attr('class', 'protocol-group')
        .attr('transform', d => `translate(${xScale(d.protocol)},0)`)
        .selectAll('rect')
        .data(d => subgroups.map(key => ({key: key, value: d[key], protocol: d.protocol})))
        .enter()
        .append('rect')
        .attr('x', d => xSubgroup(d.key))
        .attr('y', d => yScale(d.value))
        .attr('width', xSubgroup.bandwidth())
        .attr('height', d => height - yScale(d.value))
        .attr('fill', d => colors[d.key])
        .on('mouseover', function(event, d) {
            const tooltip = d3.select('body').append('div')
                .attr('class', 'protocol-tooltip')
                .style('position', 'absolute')
                .style('background', 'rgba(0,0,0,0.8)')
                .style('color', 'white')
                .style('padding', '8px')
                .style('border-radius', '4px')
                .style('font-size', '12px')
                .style('pointer-events', 'none')
                .style('z-index', '1000');
            
            tooltip.html(`
                <strong>${d.protocol}</strong><br>
                ${d.key === 'sent' ? 'Sent' : 'Received'}: ${d.value.toFixed(2)} MB
            `)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', function() {
            d3.selectAll('.protocol-tooltip').remove();
        });
    
    // Add x axis
    g.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(xScale))
        .selectAll('text')
        .style('font-size', '10px')
        .style('text-anchor', 'end')
        .attr('dx', '-.8em')
        .attr('dy', '.15em')
        .attr('transform', 'rotate(-25)');
    
    // Add y axis
    g.append('g')
        .call(d3.axisLeft(yScale))
        .selectAll('text')
        .style('font-size', '10px');
        
    // Add y axis label
    g.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', 0 - margin.left)
        .attr('x', 0 - (height / 2))
        .attr('dy', '1em')
        .style('text-anchor', 'middle')
        .style('font-size', '12px')
        .text('Data (MB)');
    
    // Add legend
    const legend = svg.append('g')
        .attr('transform', `translate(${width - 80}, 10)`);
    
    const legendItems = [
        {label: 'Sent', color: colors.sent},
        {label: 'Received', color: colors.received}
    ];
    
    legendItems.forEach((item, i) => {
        const legendRow = legend.append('g')
            .attr('transform', `translate(0, ${i * 20})`);
        
        legendRow.append('rect')
            .attr('width', 10)
            .attr('height', 10)
            .attr('fill', item.color);
        
        legendRow.append('text')
            .attr('x', 15)
            .attr('y', 10)
            .attr('text-anchor', 'start')
            .style('font-size', '12px')
            .text(item.label);
    });
}

// Calculate data transfer from network events
function calculateDataTransfer(networkAnalysis) {
    const result = {
        tcp: { sent_mb: 0, received_mb: 0 },
        udp: { sent_mb: 0, received_mb: 0 },
        bluetooth: { sent_mb: 0, received_mb: 0 }
    };
    
    // Process TCP connections
    if (networkAnalysis.tcp_connections && networkAnalysis.tcp_connections.length > 0) {
        networkAnalysis.tcp_connections.forEach(conn => {
            // For TCP send events, use the 'size' field
            if (conn.direction === 'send') {
                // Convert bytes to MB
                const sizeMB = conn.size ? parseFloat(conn.size) / (1024 * 1024) : 0;
                result.tcp.sent_mb += sizeMB;
            } 
            // For TCP receive events, use the 'len' field
            else if (conn.direction === 'receive') {
                // Convert bytes to MB
                const sizeMB = conn.len ? parseFloat(conn.len) / (1024 * 1024) : 0;
                result.tcp.received_mb += sizeMB;
            }
        });
    }
    
    // Process UDP communications
    if (networkAnalysis.udp_communications && networkAnalysis.udp_communications.length > 0) {
        networkAnalysis.udp_communications.forEach(comm => {
            // UDP uses 'len' field for both send and receive
            const sizeMB = comm.len ? parseFloat(comm.len) / (1024 * 1024) : 0;
            
            if (comm.direction === 'send') {
                result.udp.sent_mb += sizeMB;
            } else if (comm.direction === 'receive') {
                result.udp.received_mb += sizeMB;
            }
        });
    }
      
    // Process Bluetooth activity if available
    if (networkAnalysis.bluetooth_activity && networkAnalysis.bluetooth_activity.length > 0) {
        networkAnalysis.bluetooth_activity.forEach(activity => {
            // Check for size information in the bluetooth activity
            let sizeMB = 0;
            if (activity.details && activity.details.size) {
                sizeMB = parseFloat(activity.details.size) / (1024 * 1024);
            } else if (activity.details && activity.details.len) {
                sizeMB = parseFloat(activity.details.len) / (1024 * 1024);
            }
            
            if (activity.direction === 'send') {
                result.bluetooth.sent_mb += sizeMB;
            } else if (activity.direction === 'receive') {
                result.bluetooth.received_mb += sizeMB;
            }
        });
    }
    
    return result;
}


function renderConnectionTables(networkAnalysis) {
    console.log('Rendering connection tables with data:', networkAnalysis);
    
    // 1. Render TCP connections table
    renderTcpConnections(networkAnalysis);
    
    // 2. Render UDP communications table 
    renderUdpCommunications(networkAnalysis);
}

function renderTcpConnections(networkAnalysis) {
    console.log('renderTcpConnections called with:', networkAnalysis);
    console.log('TCP connections data:', networkAnalysis?.tcp_connections);
    
    if (networkAnalysis && networkAnalysis.tcp_connections && networkAnalysis.tcp_connections.length > 0) {
        let tcpHtml = '<div class="table-responsive" style="max-height: 300px; overflow-y: auto;"><table class="table table-sm table-striped">';
        tcpHtml += '<thead class="table-dark sticky-top"><tr><th>Time</th><th>Direction</th><th>Source</th><th>Destination</th><th>Size</th><th>Process</th></tr></thead><tbody>';
        
        networkAnalysis.tcp_connections.forEach(conn => {
            const time = new Date(conn.timestamp * 1000).toLocaleTimeString();
            const directionIcon = conn.direction === 'send' ? '→' : (conn.direction === 'connect' ? '🔗' : '←');
            const directionBadge = conn.direction === 'send' ? 'bg-primary' : (conn.direction === 'connect' ? 'bg-warning' : 'bg-success');
            
            // Use readable IP addresses if available, fallback to raw IPs
            let srcIP = 'N/A';
            let dstIP = 'N/A';
            
            // Debug logging (only first connection)
            if (networkAnalysis.tcp_connections.indexOf(conn) === 0) {
                console.log('TCP Connection sample:', {
                    src_ip_readable: conn.src_ip_readable,
                    src_ip: conn.src_ip,
                    dst_ip_readable: conn.dst_ip_readable,
                    dst_ip: conn.dst_ip
                });
            }
            
            if (conn.src_ip_readable) {
                srcIP = conn.src_ip_readable;
            } else if (conn.src_ip !== undefined && conn.src_ip !== null) {
                srcIP = conn.src_ip.toString();
            }
            
            if (conn.dst_ip_readable) {
                dstIP = conn.dst_ip_readable;
            } else if (conn.dst_ip !== undefined && conn.dst_ip !== null) {
                dstIP = conn.dst_ip.toString();
            }
            const srcPort = conn.src_port || '';
            const dstPort = conn.dst_port || '';
            
            // Format source and destination with ports
            const source = srcPort ? `${srcIP}:${srcPort}` : srcIP;
            const destination = dstPort ? `${dstIP}:${dstPort}` : dstIP;
            
            // Use formatted size if available, fallback to raw size, or show "N/A" for connect events
            const sizeDisplay = conn.direction === 'connect' ? 'N/A' : (conn.size_formatted || conn.len_formatted || `${conn.size || conn.len || 0}B`);
            
            tcpHtml += `<tr>
                <td><small>${time}</small></td>
                <td><span class="badge ${directionBadge}">${directionIcon} ${conn.direction}</span></td>
                <td><small><code>${source}</code></small></td>
                <td><small><code>${destination}</code></small></td>
                <td><strong>${sizeDisplay}</strong></td>
                <td><small>${conn.process}</small></td>
            </tr>`;
        });
        
        tcpHtml += '</tbody></table></div>';
        tcpHtml += `<small class="text-muted mt-2 d-block">Total: ${networkAnalysis.tcp_connections.length} TCP connections</small>`;
        $('#tcp-connections-table').html(tcpHtml);
    } else {
        $('#tcp-connections-table').html('<div class="alert alert-info">No TCP connections found</div>');
    }
}

function renderUdpCommunications(networkAnalysis) {
    if (networkAnalysis && networkAnalysis.udp_communications && networkAnalysis.udp_communications.length > 0) {
        let udpHtml = '<div class="table-responsive" style="max-height: 300px; overflow-y: auto;"><table class="table table-sm table-striped">';
        udpHtml += '<thead class="table-dark sticky-top"><tr><th>Time</th><th>Direction</th><th>Source</th><th>Destination</th><th>Size</th><th>Process</th></tr></thead><tbody>';
        
        networkAnalysis.udp_communications.forEach(comm => {
            const time = new Date(comm.timestamp * 1000).toLocaleTimeString();
            const directionIcon = comm.direction === 'send' ? '→' : '←';
            const directionBadge = comm.direction === 'send' ? 'bg-warning' : 'bg-info';
            
            // Use readable IP addresses if available, fallback to raw IPs
            let srcIP = 'N/A';
            let dstIP = 'N/A';
            
            // Debug logging (only first communication)
            if (networkAnalysis.udp_communications.indexOf(comm) === 0) {
                console.log('UDP Communication sample:', {
                    src_ip_readable: comm.src_ip_readable,
                    src_ip: comm.src_ip,
                    dst_ip_readable: comm.dst_ip_readable,
                    dst_ip: comm.dst_ip
                });
            }
            
            if (comm.src_ip_readable) {
                srcIP = comm.src_ip_readable;
            } else if (comm.src_ip !== undefined && comm.src_ip !== null) {
                srcIP = comm.src_ip.toString();
            }
            
            if (comm.dst_ip_readable) {
                dstIP = comm.dst_ip_readable;
            } else if (comm.dst_ip !== undefined && comm.dst_ip !== null) {
                dstIP = comm.dst_ip.toString();
            }
            const srcPort = comm.src_port || '';
            const dstPort = comm.dst_port || '';
            
            // Format source and destination with ports
            const source = srcPort ? `${srcIP}:${srcPort}` : srcIP;
            const destination = dstPort ? `${dstIP}:${dstPort}` : dstIP;
            
            // Use formatted size if available, fallback to raw size
            const sizeDisplay = comm.len_formatted || `${comm.len || 0}B`;
            
            udpHtml += `<tr>
                <td><small>${time}</small></td>
                <td><span class="badge ${directionBadge}">${directionIcon} ${comm.direction}</span></td>
                <td><small><code>${source}</code></small></td>
                <td><small><code>${destination}</code></small></td>
                <td><strong>${sizeDisplay}</strong></td>
                <td><small>${comm.process}</small></td>
            </tr>`;
        });
        
        udpHtml += '</tbody></table></div>';
        udpHtml += `<small class="text-muted mt-2 d-block">Total: ${networkAnalysis.udp_communications.length} UDP communications</small>`;
        $('#udp-communications-table').html(udpHtml);
    } else {
        $('#udp-communications-table').html('<div class="alert alert-info">No UDP communications found</div>');
    }
}





function showNetworkError(error) {
    $('#network-error').html(`<strong>Error:</strong> ${error}`).show();
}

// Make behavior timeline functions globally available for button event handlers
window.behaviorZoomIn = behaviorZoomIn;
window.behaviorZoomOut = behaviorZoomOut;
window.behaviorResetZoom = behaviorResetZoom;