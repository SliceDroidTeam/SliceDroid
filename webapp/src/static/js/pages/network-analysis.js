/**
 * Network Analysis Module - Handles network analysis visualization and interaction
 */

/**
 * Load network analysis from API
 */
function loadNetworkAnalysis() {
    const pid = $('#network-pid').val();
    
    showSectionLoading('network-section', 'Running network analysis...');
    
    const params = new URLSearchParams();
    if (pid) params.append('pid', pid);
    
    return $.ajax({
        url: `/api/network-analysis?${params.toString()}`,
        method: 'GET',
        timeout: 45000,
        dataType: 'json'
    })
    .done(function(data) {
        console.log('Network analysis loaded:', data);
        networkData = data;
        renderNetworkAnalysis(data);
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load network analysis:', textStatus, errorThrown);
        showNetworkError(`Failed to load network analysis: ${textStatus}`);
    });
}

/**
 * Main network analysis rendering function
 */
function renderNetworkAnalysis(data) {
    const container = $('#network-section');
    
    if (!data || data.error) {
        showNetworkError(data?.error || 'No network analysis data available');
        return;
    }
    
    // Wait for container to be fully visible before rendering charts
    setTimeout(() => {
        // Update intensity badge
        updateNetworkIntensityBadge(data.network_analysis);

        // Render summary cards
        renderNetworkSummary(data);

        // Render network flow chart
        if (document.getElementById('network-flow-chart') && 
            document.getElementById('network-flow-chart').offsetWidth > 0) {
            renderNetworkFlowChart(data.network_analysis);
        } else {
            setTimeout(() => renderNetworkFlowChart(data.network_analysis), 500);
        }
        
        // Render network communication heatmap
        if (document.getElementById('network-heatmap-chart') && 
            document.getElementById('network-heatmap-chart').offsetWidth > 0) {
            renderNetworkHeatmap(data.network_analysis);
        } else {
            setTimeout(() => renderNetworkHeatmap(data.network_analysis), 500);
        }

        // Render MB charts
        renderNetworkProtocolCharts(data.network_analysis);

        // Render connection tables
        renderConnectionTables(data.network_analysis);
    }, 200);
}

/**
 * Update network intensity badge
 */
function updateNetworkIntensityBadge(networkAnalysis) {
    const badge = $('#network-intensity-badge');
    if (!networkAnalysis || !networkAnalysis.summary) {
        badge.text('No Data').removeClass().addClass('badge');
        return;
    }

    const intensity = networkAnalysis.summary.communication_intensity || 'LOW';
    badge.text(intensity)
         .removeClass()
         .addClass(`badge security-badge intensity-${intensity.toLowerCase()}`);
}

/**
 * Render network summary cards
 */
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
        {
            title: 'Socket Operations',
            value: summary.total_socket_operations || 0,
            type: 'success',
            icon: 'fas fa-plug'
        },
        {
            title: 'Protocols',
            value: summary.active_protocols ? summary.active_protocols.length : 0,
            type: 'warning',
            icon: 'fas fa-layer-group'
        }
    ];

    summaryCards.forEach(card => {
        summaryContainer.append(`
            <div class="col-md-3 mb-2">
                <div class="summary-card ${card.type}">
                    <div class="card-value">${card.value}</div>
                    <div class="card-label">${card.title}</div>
                </div>
            </div>
        `);
    });
}

/**
 * Render network flow chart
 */
function renderNetworkFlowChart(networkAnalysis) {
    if (!networkAnalysis || !networkAnalysis.flow_relationships) {
        $('#network-flow-chart').html('<div class="alert alert-info">No network flow data available</div>');
        return;
    }

    // Use the existing chart helper from charts.js
    createNetworkFlowChart('network-flow-chart', networkAnalysis, 'Network Communication Flow');
}

/**
 * Render network protocol charts (MB sent, received, total)
 */
function renderNetworkProtocolCharts(networkAnalysis) {
    // Render MB sent per protocol chart
    if (document.getElementById('mb-sent-per-protocol-chart') && 
        document.getElementById('mb-sent-per-protocol-chart').offsetWidth > 0) {
        renderMBSentPerProtocolChart(networkAnalysis);
    } else {
        setTimeout(() => renderMBSentPerProtocolChart(networkAnalysis), 500);
    }
    
    // Render MB transferred per protocol chart
    if (document.getElementById('mb-per-protocol-chart') && 
        document.getElementById('mb-per-protocol-chart').offsetWidth > 0) {
        renderMBPerProtocolChart(networkAnalysis);
    } else {
        setTimeout(() => renderMBPerProtocolChart(networkAnalysis), 500);
    }
    
    // Render MB received per protocol chart
    if (document.getElementById('mb-received-per-protocol-chart') && 
        document.getElementById('mb-received-per-protocol-chart').offsetWidth > 0) {
        renderMbReceivedPerProtocolChart(networkAnalysis);
    } else {
        setTimeout(() => renderMbReceivedPerProtocolChart(networkAnalysis), 500);
    }
}

/**
 * Render MB sent per protocol pie chart
 */
function renderMBSentPerProtocolChart(networkAnalysis) {
    if (!networkAnalysis || !networkAnalysis.data_transfer) {
        $('#mb-sent-per-protocol-chart').html('<div class="alert alert-info">No data transfer information available</div>');
        return;
    }

    const dataTransfer = networkAnalysis.data_transfer;
    const chartData = [];
    
    // TCP sent
    if (dataTransfer.tcp_sent_mb > 0) {
        chartData.push({
            label: 'TCP',
            value: dataTransfer.tcp_sent_mb
        });
    }
    
    // UDP sent
    if (dataTransfer.udp_sent_mb > 0) {
        chartData.push({
            label: 'UDP',
            value: dataTransfer.udp_sent_mb
        });
    }
    
    if (chartData.length === 0) {
        $('#mb-sent-per-protocol-chart').html('<div class="alert alert-info">No data sent</div>');
        return;
    }

    createPieChart('mb-sent-per-protocol-chart', chartData, 'Data Sent per Protocol (MB)');
}

/**
 * Render MB per protocol chart (total transfer)
 */
function renderMBPerProtocolChart(networkAnalysis) {
    if (!networkAnalysis || !networkAnalysis.data_transfer) {
        $('#mb-per-protocol-chart').html('<div class="alert alert-info">No data transfer information available</div>');
        return;
    }

    const dataTransfer = networkAnalysis.data_transfer;
    const chartData = [];
    
    // TCP total
    const tcpTotal = (dataTransfer.tcp_sent_mb || 0) + (dataTransfer.tcp_received_mb || 0);
    if (tcpTotal > 0) {
        chartData.push({
            label: 'TCP',
            value: tcpTotal
        });
    }
    
    // UDP total  
    const udpTotal = (dataTransfer.udp_sent_mb || 0) + (dataTransfer.udp_received_mb || 0);
    if (udpTotal > 0) {
        chartData.push({
            label: 'UDP',
            value: udpTotal
        });
    }
    
    if (chartData.length === 0) {
        $('#mb-per-protocol-chart').html('<div class="alert alert-info">No data transfer detected</div>');
        return;
    }

    createPieChart('mb-per-protocol-chart', chartData, 'Total Data Transfer per Protocol (MB)');
}

/**
 * Render MB received per protocol chart
 */
function renderMbReceivedPerProtocolChart(networkAnalysis) {
    if (!networkAnalysis || !networkAnalysis.data_transfer) {
        $('#mb-received-per-protocol-chart').html('<div class="alert alert-info">No data transfer information available</div>');
        return;
    }

    const dataTransfer = networkAnalysis.data_transfer;
    const chartData = [];
    
    // TCP received
    if (dataTransfer.tcp_received_mb > 0) {
        chartData.push({
            label: 'TCP',
            value: dataTransfer.tcp_received_mb
        });
    }
    
    // UDP received
    if (dataTransfer.udp_received_mb > 0) {
        chartData.push({
            label: 'UDP', 
            value: dataTransfer.udp_received_mb
        });
    }
    
    if (chartData.length === 0) {
        $('#mb-received-per-protocol-chart').html('<div class="alert alert-info">No data received</div>');
        return;
    }

    createPieChart('mb-received-per-protocol-chart', chartData, 'Data Received per Protocol (MB)');
}

/**
 * Render network heatmap
 */
function renderNetworkHeatmap(networkAnalysis) {
    if (!networkAnalysis) {
        $('#network-heatmap-chart').html('<div class="alert alert-info">No network activity data available</div>');
        return;
    }

    // Use the existing chart helper from charts.js
    createNetworkHeatmap('network-heatmap-chart', networkAnalysis, 'Network Communication Heatmap');
}

/**
 * Render connection tables for TCP and UDP
 */
function renderConnectionTables(networkAnalysis) {
    renderTcpConnections(networkAnalysis);
    renderUdpCommunications(networkAnalysis);
}

/**
 * Render TCP connections table
 */
function renderTcpConnections(networkAnalysis) {
    const container = $('#tcp-connections-table');
    
    if (!networkAnalysis || !networkAnalysis.tcp_connections) {
        container.html('<div class="alert alert-info">No TCP connections found</div>');
        return;
    }

    const connections = networkAnalysis.tcp_connections;
    if (connections.length === 0) {
        container.html('<div class="alert alert-info">No TCP connections detected</div>');
        return;
    }

    let tableHtml = `
        <div class="table-responsive">
            <table class="table table-striped table-hover table-sm">
                <thead class="table-dark">
                    <tr>
                        <th>Direction</th>
                        <th>Local Address</th>
                        <th>Remote Address</th>
                        <th>State</th>
                        <th>Data (MB)</th>
                        <th>Events</th>
                    </tr>
                </thead>
                <tbody>
    `;

    connections.slice(0, 20).forEach(conn => {
        const dataMB = conn.data_mb ? parseFloat(conn.data_mb).toFixed(3) : '0.000';
        const badgeClass = conn.direction === 'send' ? 'bg-primary' : 'bg-success';
        
        tableHtml += `
            <tr>
                <td><span class="badge ${badgeClass}">${conn.direction}</span></td>
                <td><code>${conn.local_addr || 'N/A'}</code></td>
                <td><code>${conn.remote_addr || 'N/A'}</code></td>
                <td><span class="badge bg-secondary">${conn.state || 'UNKNOWN'}</span></td>
                <td>${dataMB}</td>
                <td>${conn.event_count || 0}</td>
            </tr>
        `;
    });

    tableHtml += `
                </tbody>
            </table>
        </div>
    `;

    if (connections.length > 20) {
        tableHtml += `<p class="text-muted mt-2">Showing top 20 of ${connections.length} TCP connections</p>`;
    }

    container.html(tableHtml);
}

/**
 * Render UDP communications table
 */
function renderUdpCommunications(networkAnalysis) {
    const container = $('#udp-communications-table');
    
    if (!networkAnalysis || !networkAnalysis.udp_communications) {
        container.html('<div class="alert alert-info">No UDP communications found</div>');
        return;
    }

    const communications = networkAnalysis.udp_communications;
    if (communications.length === 0) {
        container.html('<div class="alert alert-info">No UDP communications detected</div>');
        return;
    }

    let tableHtml = `
        <div class="table-responsive">
            <table class="table table-striped table-hover table-sm">
                <thead class="table-dark">
                    <tr>
                        <th>Direction</th>
                        <th>Local Address</th>
                        <th>Remote Address</th>
                        <th>Data (MB)</th>
                        <th>Events</th>
                        <th>Protocol</th>
                    </tr>
                </thead>
                <tbody>
    `;

    communications.slice(0, 20).forEach(comm => {
        const dataMB = comm.data_mb ? parseFloat(comm.data_mb).toFixed(3) : '0.000';
        const badgeClass = comm.direction === 'send' ? 'bg-primary' : 'bg-success';
        
        tableHtml += `
            <tr>
                <td><span class="badge ${badgeClass}">${comm.direction}</span></td>
                <td><code>${comm.local_addr || 'N/A'}</code></td>
                <td><code>${comm.remote_addr || 'N/A'}</code></td>
                <td>${dataMB}</td>
                <td>${comm.event_count || 0}</td>
                <td><span class="badge bg-info">UDP</span></td>
            </tr>
        `;
    });

    tableHtml += `
                </tbody>
            </table>
        </div>
    `;

    if (communications.length > 20) {
        tableHtml += `<p class="text-muted mt-2">Showing top 20 of ${communications.length} UDP communications</p>`;
    }

    container.html(tableHtml);
}

/**
 * Show network analysis error
 */
function showNetworkError(error) {
    const container = $('#network-section');
    container.html(`
        <div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>Network Analysis Error:</strong> ${error}
        </div>
    `);
}