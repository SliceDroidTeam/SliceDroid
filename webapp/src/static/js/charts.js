// Chart helper functions using D3.js

// Loading state management
function showChartLoading(containerId, message = 'Loading...') {
    d3.select(`#${containerId}`).html(`
        <div class="d-flex flex-column align-items-center justify-content-center h-100 p-4">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="sr-only">Loading...</span>
            </div>
            <div class="text-muted">${message}</div>
        </div>
    `);
}

function hideChartLoading(containerId) {
    d3.select(`#${containerId}`).html("");
}

// Enhanced color schemes for different chart types
const categoryColorSchemes = {
    security: ['#dc3545', '#fd7e14', '#ffc107', '#28a745', '#6c757d'],
    network: ['#007bff', '#17a2b8', '#6610f2', '#6f42c1', '#e83e8c'],
    process: ['#28a745', '#20c997', '#17a2b8', '#6f42c1', '#fd7e14'],
    filesystem: ['#343a40', '#495057', '#6c757d', '#adb5bd', '#ced4da'],
    default: d3.schemeCategory10
};

function createPieChart(containerId, data, title) {
    // Clear any existing content
    d3.select(`#${containerId}`).html("");

    if (!data || data.length === 0) {
        d3.select(`#${containerId}`)
            .append('div')
            .attr('class', 'alert alert-info')
            .text('No data available for chart');
        return;
    }

    // Check if container exists and is visible
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Chart container '${containerId}' not found`);
        return;
    }
    
    // Wait for container to be visible (with timeout)
    let retryCount = 0;
    const maxRetries = 10;
    
    function tryRender() {
        if (container.offsetWidth === 0 || container.offsetHeight === 0) {
            retryCount++;
            if (retryCount < maxRetries) {
                console.warn(`Chart container '${containerId}' is not visible, retrying... (${retryCount}/${maxRetries})`);
                setTimeout(tryRender, 200);
                return;
            } else {
                console.error(`Chart container '${containerId}' never became visible, using default dimensions`);
                // Force render with default dimensions
            }
        }
        renderChart();
    }
    
    function renderChart() {
        const width = container.clientWidth || 600;
        const height = Math.min(container.clientHeight || 350, 350);
        
        // Adjust layout for legend
        const chartWidth = width * 0.6; // 60% for chart
        const legendWidth = width * 0.4; // 40% for legend
        const chartHeight = height - 40; // Leave space for title
        const radius = Math.min(chartWidth, chartHeight) / 2 - 20;

        // Create main container
        const mainSvg = d3.select(`#${containerId}`)
            .append("svg")
            .attr("width", width)
            .attr("height", height);

        // Add title
        mainSvg.append("text")
            .attr("x", width / 2)
            .attr("y", 20)
            .attr("text-anchor", "middle")
            .attr("font-size", "16px")
            .attr("font-weight", "bold")
            .text(title);

        // Chart group
        const chartGroup = mainSvg.append("g")
            .attr("transform", `translate(${chartWidth / 2}, ${height / 2})`);

        const color = d3.scaleOrdinal(d3.schemeCategory10);

        const pie = d3.pie()
            .value(d => d.value)
            .sort(null);

        const arc = d3.arc()
            .innerRadius(0)
            .outerRadius(radius);

        const labelArc = d3.arc()
            .innerRadius(radius * 0.7)
            .outerRadius(radius * 0.7);

        const arcs = chartGroup.selectAll(".arc")
            .data(pie(data))
            .enter()
            .append("g")
            .attr("class", "arc");

        arcs.append("path")
            .attr("d", arc)
            .attr("fill", (d, i) => color(i))
            .attr("stroke", "white")
            .style("stroke-width", "2px")
            .style("cursor", "pointer")
            .on("mouseover", function(event, d) {
                // Highlight the hovered slice
                d3.select(this).style("opacity", 0.8);
                
                // Create tooltip
                const tooltip = d3.select("body").append("div")
                    .attr("class", "chart-tooltip")
                    .style("position", "absolute")
                    .style("background", "rgba(0,0,0,0.9)")
                    .style("color", "white")
                    .style("padding", "10px 15px")
                    .style("border-radius", "6px")
                    .style("font-size", "13px")
                    .style("pointer-events", "none")
                    .style("z-index", "1000")
                    .style("box-shadow", "0 4px 8px rgba(0,0,0,0.3)")
                    .style("opacity", 0);

                const percent = ((d.data.value / d3.sum(data, d => d.value)) * 100).toFixed(1);
                tooltip.html(`<strong>${d.data.label}</strong><br>Count: ${d.data.value.toLocaleString()}<br>Percentage: ${percent}%`)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 10) + "px")
                    .transition().duration(200).style("opacity", 1);
            })
            .on("mouseout", function() {
                // Remove highlight
                d3.select(this).style("opacity", 1);
                // Remove tooltip
                d3.selectAll(".chart-tooltip").remove();
            });

        // Add percentage labels on slices (only for larger slices)
        arcs.append("text")
            .attr("transform", d => `translate(${labelArc.centroid(d)})`)
            .attr("text-anchor", "middle")
            .attr("font-size", "11px")
            .attr("font-weight", "bold")
            .attr("fill", "white")
            .text(d => {
                const percent = ((d.data.value / d3.sum(data, d => d.value)) * 100).toFixed(1);
                return percent > 8 ? `${percent}%` : ''; // Only show label if slice is > 8%
            });

        // Create legend
        const legendGroup = mainSvg.append("g")
            .attr("transform", `translate(${chartWidth + 20}, 40)`);

        const legendItems = legendGroup.selectAll(".legend-item")
            .data(data)
            .enter()
            .append("g")
            .attr("class", "legend-item")
            .attr("transform", (d, i) => `translate(0, ${i * 25})`);

        // Legend color boxes
        legendItems.append("rect")
            .attr("width", 15)
            .attr("height", 15)
            .attr("fill", (d, i) => color(i))
            .attr("stroke", "#ccc")
            .attr("stroke-width", 1);

        // Legend text
        legendItems.append("text")
            .attr("x", 20)
            .attr("y", 12)
            .attr("font-size", "12px")
            .attr("text-anchor", "start")
            .text(d => {
                const percent = ((d.value / d3.sum(data, d => d.value)) * 100).toFixed(1);
                // Truncate long labels
                const label = d.label.length > 15 ? d.label.substring(0, 15) + '...' : d.label;
                return `${label} (${percent}%)`;
            })
            .append("title") // Add full text as tooltip
            .text(d => {
                const percent = ((d.value / d3.sum(data, d => d.value)) * 100).toFixed(1);
                return `${d.label}: ${d.value.toLocaleString()} (${percent}%)`;
            });

        // Add legend interaction
        legendItems
            .style("cursor", "pointer")
            .on("mouseover", function(event, d) {
                // Highlight corresponding pie slice
                const index = data.indexOf(d);
                arcs.filter((arcData, i) => i === index)
                    .select("path")
                    .style("opacity", 0.8);
            })
            .on("mouseout", function() {
                // Remove highlight from all slices
                arcs.selectAll("path").style("opacity", 1);
            });
    }
    
    // Start the rendering process
    tryRender();
}

function createBarChart(containerId, data, title, xLabel, yLabel) {
    // Clear any existing content
    d3.select(`#${containerId}`).html("");

    if (!data || data.length === 0) {
        d3.select(`#${containerId}`)
            .append('div')
            .attr('class', 'alert alert-info')
            .text('No data available for chart');
        return;
    }

    const margin = { top: 30, right: 30, bottom: 70, left: 60 };
    const width = document.getElementById(containerId).clientWidth - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left}, ${margin.top})`);

    // Add title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', -10)
        .attr('text-anchor', 'middle')
        .style('font-size', '16px')
        .style('font-weight', 'bold')
        .text(title);

    // X scale
    const x = d3.scaleBand()
        .domain(data.map(d => d.label))
        .range([0, width])
        .padding(0.2);

    // Y scale
    const y = d3.scaleLinear()
        .domain([0, d3.max(data, d => d.value) * 1.1])
        .range([height, 0]);

    // Add X axis
    svg.append('g')
        .attr('transform', `translate(0, ${height})`)
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
        .attr('x', width / 2)
        .attr('y', height + margin.bottom - 5)
        .attr('text-anchor', 'middle')
        .text(xLabel);

    // Add Y axis label
    svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', -margin.left + 15)
        .attr('x', -height / 2)
        .attr('text-anchor', 'middle')
        .text(yLabel);

    // Add bars
    svg.selectAll('rect')
        .data(data)
        .enter()
        .append('rect')
        .attr('x', d => x(d.label))
        .attr('y', d => y(d.value))
        .attr('width', x.bandwidth())
        .attr('height', d => height - y(d.value))
        .attr('fill', '#4682B4')
        .attr('stroke', 'black')
        .attr('stroke-width', 1);

    // Add value labels on top of bars
    svg.selectAll('.label')
        .data(data)
        .enter()
        .append('text')
        .attr('class', 'label')
        .attr('x', d => x(d.label) + x.bandwidth() / 2)
        .attr('y', d => y(d.value) - 5)
        .attr('text-anchor', 'middle')
        .text(d => d.value);
}

// Enhanced pie chart with category-specific colors
function createCategoryPieChart(containerId, data, title, category = 'default') {
    d3.select(`#${containerId}`).html("");

    if (!data || data.length === 0) {
        d3.select(`#${containerId}`)
            .append('div')
            .attr('class', 'alert alert-info')
            .text('No data available for chart');
        return;
    }

    const container = document.getElementById(containerId);
    const width = container.clientWidth;
    const height = Math.min(container.clientHeight, 350);
    const radius = Math.min(width, height) / 2 - 20;

    const svg = d3.select(`#${containerId}`)
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", `translate(${width / 2}, ${height / 2})`);

    const colors = categoryColorSchemes[category] || categoryColorSchemes.default;
    const color = d3.scaleOrdinal(colors);

    const pie = d3.pie()
        .value(d => d.value)
        .sort(null);

    const arc = d3.arc()
        .innerRadius(0)
        .outerRadius(radius);

    const labelArc = d3.arc()
        .innerRadius(radius * 0.6)
        .outerRadius(radius * 0.6);

    // Add title
    svg.append("text")
        .attr("text-anchor", "middle")
        .attr("y", -height/2 + 20)
        .attr("font-size", "16px")
        .attr("font-weight", "bold")
        .text(title);

    const arcs = svg.selectAll(".arc")
        .data(pie(data))
        .enter()
        .append("g")
        .attr("class", "arc");

    arcs.append("path")
        .attr("d", arc)
        .attr("fill", (d, i) => color(i))
        .attr("stroke", "white")
        .style("stroke-width", "2px")
        .style("cursor", "pointer")
        .on("mouseover", function(event, d) {
            const tooltip = d3.select("body").append("div")
                .attr("class", "chart-tooltip")
                .style("position", "absolute")
                .style("background", "rgba(0,0,0,0.8)")
                .style("color", "white")
                .style("padding", "8px 12px")
                .style("border-radius", "4px")
                .style("font-size", "12px")
                .style("pointer-events", "none")
                .style("z-index", "1000")
                .style("opacity", 0);

            const percent = ((d.data.value / d3.sum(data, d => d.value)) * 100).toFixed(1);
            tooltip.html(`<strong>${d.data.label}</strong><br>Count: ${d.data.value}<br>Percentage: ${percent}%`)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px")
                .transition().duration(200).style("opacity", 1);
        })
        .on("mouseout", function() {
            d3.selectAll(".chart-tooltip").remove();
        });

    // Add labels for larger slices
    arcs.append("text")
        .attr("transform", d => `translate(${labelArc.centroid(d)})`)
        .attr("text-anchor", "middle")
        .attr("font-size", "12px")
        .text(d => {
            const percent = ((d.data.value / d3.sum(data, d => d.value)) * 100).toFixed(1);
            return percent > 8 ? `${percent}%` : '';
        });
}

// Security timeline chart
function createSecurityTimelineChart(containerId, timelineData, title = 'Security Events Timeline') {
    d3.select(`#${containerId}`).html("");

    if (!timelineData || timelineData.length === 0) {
        d3.select(`#${containerId}`)
            .append('div')
            .attr('class', 'alert alert-info')
            .text('No security events found');
        return;
    }

    const margin = { top: 30, right: 30, bottom: 50, left: 80 };
    const container = document.getElementById(containerId);
    const width = container.clientWidth - margin.left - margin.right;
    const height = 200;

    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left}, ${margin.top})`);

    // Add title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', -10)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('font-weight', 'bold')
        .text(title);

    // Parse timestamps and create scales
    const timeExtent = d3.extent(timelineData, d => new Date(d.timestamp * 1000));
    const x = d3.scaleTime()
        .domain(timeExtent)
        .range([0, width]);

    const severityLevels = ['low', 'medium', 'high'];
    const y = d3.scaleOrdinal()
        .domain(severityLevels)
        .range([height - 20, height/2, 20]);

    // Color scale for severity
    const severityColors = d3.scaleOrdinal()
        .domain(severityLevels)
        .range(['#28a745', '#ffc107', '#dc3545']);

    // Add dots for events
    svg.selectAll('.security-dot')
        .data(timelineData)
        .enter()
        .append('circle')
        .attr('class', 'security-dot')
        .attr('cx', d => x(new Date(d.timestamp * 1000)))
        .attr('cy', d => y(d.severity || 'low'))
        .attr('r', 4)
        .attr('fill', d => severityColors(d.severity || 'low'))
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            const tooltip = d3.select("body").append("div")
                .attr("class", "chart-tooltip")
                .style("position", "absolute")
                .style("background", "rgba(0,0,0,0.9)")
                .style("color", "white")
                .style("padding", "8px 12px")
                .style("border-radius", "4px")
                .style("font-size", "12px")
                .style("pointer-events", "none")
                .style("z-index", "1000")
                .style("opacity", 0);

            const time = new Date(d.timestamp * 1000).toLocaleString();
            tooltip.html(`<strong>${d.event_type}</strong><br>Time: ${time}<br>Severity: ${d.severity || 'low'}<br>Process: ${d.process || 'unknown'}`)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px")
                .transition().duration(200).style("opacity", 1);
        })
        .on('mouseout', function() {
            d3.selectAll(".chart-tooltip").remove();
        });

    // Add axes
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).ticks(5));

    svg.append('g')
        .call(d3.axisLeft(y));
}

// Network flow visualization
function createNetworkFlowChart(containerId, networkData, title = 'Network Communication Flow') {
    d3.select(`#${containerId}`).html("");

    if (!networkData || (!networkData.tcp_connections && !networkData.udp_communications)) {
        d3.select(`#${containerId}`)
            .append('div')
            .attr('class', 'alert alert-info')
            .text('No network flow data available');
        return;
    }

    const container = document.getElementById(containerId);
    const width = container.clientWidth;
    const height = 250;

    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

    // Add title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', 20)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('font-weight', 'bold')
        .text(title);

    // Combine TCP and UDP data for visualization
    const connections = [];
    if (networkData.tcp_connections) {
        connections.push(...networkData.tcp_connections.map(conn => ({...conn, protocol: 'TCP'})));
    }
    if (networkData.udp_communications) {
        connections.push(...networkData.udp_communications.map(conn => ({...conn, protocol: 'UDP'})));
    }

    if (connections.length === 0) {
        svg.append('text')
            .attr('x', width / 2)
            .attr('y', height / 2)
            .attr('text-anchor', 'middle')
            .style('font-size', '12px')
            .text('No connections to display');
        return;
    }

    // Group by direction and protocol
    const sendEvents = connections.filter(c => c.direction === 'send');
    const receiveEvents = connections.filter(c => c.direction === 'receive');

    // Create simple flow visualization
    const margin = 40;
    const barHeight = 20;
    const barSpacing = 30;

    // TCP flows
    if (sendEvents.filter(e => e.protocol === 'TCP').length > 0) {
        svg.append('rect')
            .attr('x', margin)
            .attr('y', 50)
            .attr('width', Math.min(sendEvents.filter(e => e.protocol === 'TCP').length * 5, width - 2 * margin))
            .attr('height', barHeight)
            .attr('fill', '#007bff')
            .attr('opacity', 0.7);

        svg.append('text')
            .attr('x', margin)
            .attr('y', 45)
            .style('font-size', '12px')
            .text(`TCP Send (${sendEvents.filter(e => e.protocol === 'TCP').length} events)`);
    }

    if (receiveEvents.filter(e => e.protocol === 'TCP').length > 0) {
        svg.append('rect')
            .attr('x', margin)
            .attr('y', 50 + barSpacing)
            .attr('width', Math.min(receiveEvents.filter(e => e.protocol === 'TCP').length * 5, width - 2 * margin))
            .attr('height', barHeight)
            .attr('fill', '#17a2b8')
            .attr('opacity', 0.7);

        svg.append('text')
            .attr('x', margin)
            .attr('y', 45 + barSpacing)
            .style('font-size', '12px')
            .text(`TCP Receive (${receiveEvents.filter(e => e.protocol === 'TCP').length} events)`);
    }

    // UDP flows
    if (sendEvents.filter(e => e.protocol === 'UDP').length > 0) {
        svg.append('rect')
            .attr('x', margin)
            .attr('y', 50 + 2 * barSpacing)
            .attr('width', Math.min(sendEvents.filter(e => e.protocol === 'UDP').length * 5, width - 2 * margin))
            .attr('height', barHeight)
            .attr('fill', '#6610f2')
            .attr('opacity', 0.7);

        svg.append('text')
            .attr('x', margin)
            .attr('y', 45 + 2 * barSpacing)
            .style('font-size', '12px')
            .text(`UDP Send (${sendEvents.filter(e => e.protocol === 'UDP').length} events)`);
    }

    if (receiveEvents.filter(e => e.protocol === 'UDP').length > 0) {
        svg.append('rect')
            .attr('x', margin)
            .attr('y', 50 + 3 * barSpacing)
            .attr('width', Math.min(receiveEvents.filter(e => e.protocol === 'UDP').length * 5, width - 2 * margin))
            .attr('height', barHeight)
            .attr('fill', '#6f42c1')
            .attr('opacity', 0.7);

        svg.append('text')
            .attr('x', margin)
            .attr('y', 45 + 3 * barSpacing)
            .style('font-size', '12px')
            .text(`UDP Receive (${receiveEvents.filter(e => e.protocol === 'UDP').length} events)`);
    }
}

// Process tree visualization
function createProcessTreeChart(containerId, processTreeData, title = 'Process Genealogy Tree') {
    d3.select(`#${containerId}`).html("");

    if (!processTreeData || !processTreeData.nodes || processTreeData.nodes.length === 0) {
        d3.select(`#${containerId}`)
            .append('div')
            .attr('class', 'alert alert-info')
            .text('No process tree data available');
        return;
    }

    const container = document.getElementById(containerId);
    const width = container.clientWidth;
    const height = Math.min(container.clientHeight, 350);

    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

    // Add title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', 20)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('font-weight', 'bold')
        .text(title);

    // Simple tree layout
    const treeLayout = d3.tree()
        .size([width - 40, height - 60]);

    // Convert flat data to hierarchical
    const root = d3.hierarchy({
        id: 'root',
        children: processTreeData.nodes.filter(n => !n.parent).map(node => ({
            id: node.id,
            name: node.name,
            children: getChildren(node.id, processTreeData.nodes)
        }))
    });

    function getChildren(parentId, nodes) {
        return nodes
            .filter(n => n.parent === parentId)
            .map(node => ({
                id: node.id,
                name: node.name,
                children: getChildren(node.id, nodes)
            }));
    }

    treeLayout(root);

    // Add links
    svg.selectAll('.process-link')
        .data(root.links())
        .enter()
        .append('path')
        .attr('class', 'process-link')
        .attr('d', d3.linkVertical()
            .x(d => d.x + 20)
            .y(d => d.y + 30))
        .style('fill', 'none')
        .style('stroke', '#6c757d')
        .style('stroke-width', 2);

    // Add nodes
    const node = svg.selectAll('.process-node')
        .data(root.descendants())
        .enter()
        .append('g')
        .attr('class', 'process-node')
        .attr('transform', d => `translate(${d.x + 20}, ${d.y + 30})`);

    node.append('circle')
        .attr('r', 8)
        .style('fill', '#28a745')
        .style('stroke', '#fff')
        .style('stroke-width', 2);

    node.append('text')
        .attr('dy', 3)
        .attr('x', d => d.children ? -12 : 12)
        .style('text-anchor', d => d.children ? 'end' : 'start')
        .style('font-size', '10px')
        .text(d => d.data.name || d.data.id);
}


// Network Communication Heatmap
function createNetworkHeatmap(containerId, networkData, title = 'Network Communication Heatmap') {
    d3.select(`#${containerId}`).html("");

    if (!networkData || !networkData.heatmapData || networkData.heatmapData.length === 0) {
        d3.select(`#${containerId}`)
            .append('div')
            .attr('class', 'alert alert-info')
            .text('No network activity data available for heatmap');
        return;
    }

    // Set up dimensions
    const margin = { top: 30, right: 50, bottom: 60, left: 120 };
    const container = document.getElementById(containerId);
    const width = container.clientWidth - margin.left - margin.right;
    const height = container.clientHeight - margin.top - margin.bottom;

    // Create SVG
    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left}, ${margin.top})`);

    // Add title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', -10)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('font-weight', 'bold')
        .text(title);

    // Define protocols (y-axis)
    const protocols = ['TCP', 'UDP'];
    
    // Get time range (x-axis)
    const timeExtent = d3.extent(networkData.heatmapData, d => d.timeIndex);
    
    // Create scales
    const x = d3.scaleLinear()
        .domain([0, timeExtent[1]])
        .range([0, width]);
    
    const y = d3.scaleBand()
        .domain(protocols)
        .range([0, height])
        .padding(0.1);
    
    // Color scale for intensity
    const colorScale = d3.scaleSequential(d3.interpolateYlOrRd)
        .domain([0, d3.max(networkData.heatmapData, d => d.intensity)]);
    
    // Create heatmap cells
    svg.selectAll('.heatmap-cell')
        .data(networkData.heatmapData)
        .enter()
        .append('rect')
        .attr('class', 'heatmap-cell')
        .attr('x', d => x(d.timeIndex))
        .attr('y', d => y(d.protocol))
        .attr('width', d => Math.max(2, x(1) - x(0))) // Ensure minimum width of 2px
        .attr('height', y.bandwidth())
        .attr('fill', d => colorScale(d.intensity))
        .attr('stroke', '#fff')
        .attr('stroke-width', 0.5)
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            // Create tooltip
            const tooltip = d3.select("body").append("div")
                .attr("class", "chart-tooltip")
                .style("position", "absolute")
                .style("background", "rgba(0,0,0,0.8)")
                .style("color", "white")
                .style("padding", "8px 12px")
                .style("border-radius", "4px")
                .style("font-size", "12px")
                .style("pointer-events", "none")
                .style("z-index", "1000")
                .style("opacity", 0);

            tooltip.html(`
                <strong>${d.protocol}</strong><br>
                Time: ${d.timeFormatted}<br>
                Events: ${d.count}<br>
                Intensity: ${d.intensity.toFixed(2)}
            `)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 10) + "px")
            .transition().duration(200).style("opacity", 1);
        })
        .on('mouseout', function() {
            d3.selectAll(".chart-tooltip").remove();
        });
    
    // Add x-axis with time labels
    const xAxis = d3.axisBottom(x)
        .tickFormat(d => `t=${d}s`)
        .ticks(Math.min(10, timeExtent[1] + 1));
    
    svg.append('g')
        .attr('transform', `translate(0, ${height})`)
        .call(xAxis)
        .selectAll('text')
        .style('text-anchor', 'middle');
    
    // Add x-axis label
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', height + 40)
        .attr('text-anchor', 'middle')
        .text('Time (seconds)');
    
    // Add y-axis
    svg.append('g')
        .call(d3.axisLeft(y));
    
    // Add y-axis label
    svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', -margin.left + 15)
        .attr('x', -height / 2)
        .attr('text-anchor', 'middle')
        .text('Protocol');
    
    // Add legend
    const legendWidth = 200;
    const legendHeight = 15;
    
    const legendX = d3.scaleLinear()
        .domain([0, d3.max(networkData.heatmapData, d => d.intensity)])
        .range([0, legendWidth]);
    
    const legendXAxis = d3.axisBottom(legendX)
        .ticks(5)
        .tickFormat(d => d.toFixed(1));
    
    const legend = svg.append('g')
        .attr('transform', `translate(${width - legendWidth - 10}, -20)`);
    
    // Create gradient for legend
    const defs = svg.append('defs');
    const linearGradient = defs.append('linearGradient')
        .attr('id', 'heatmap-gradient')
        .attr('x1', '0%')
        .attr('y1', '0%')
        .attr('x2', '100%')
        .attr('y2', '0%');
    
    // Add color stops
    linearGradient.selectAll('stop')
        .data([
            {offset: '0%', color: colorScale(0)},
            {offset: '25%', color: colorScale(d3.max(networkData.heatmapData, d => d.intensity) * 0.25)},
            {offset: '50%', color: colorScale(d3.max(networkData.heatmapData, d => d.intensity) * 0.5)},
            {offset: '75%', color: colorScale(d3.max(networkData.heatmapData, d => d.intensity) * 0.75)},
            {offset: '100%', color: colorScale(d3.max(networkData.heatmapData, d => d.intensity))}
        ])
        .enter().append('stop')
        .attr('offset', d => d.offset)
        .attr('stop-color', d => d.color);
    
    // Add legend rectangle
    legend.append('rect')
        .attr('width', legendWidth)
        .attr('height', legendHeight)
        .style('fill', 'url(#heatmap-gradient)');
    
    // Add legend axis
    legend.append('g')
        .attr('transform', `translate(0, ${legendHeight})`)
        .call(legendXAxis)
        .selectAll('text')
        .style('font-size', '10px');
    
    // Add legend title
    legend.append('text')
        .attr('x', 0)
        .attr('y', -5)
        .style('font-size', '10px')
        .style('text-anchor', 'start')
        .text('Activity Intensity');
}

// Multi-line timeline chart for enhanced categories
function createMultiLineTimelineChart(containerId, timelineData, title = 'Event Categories Timeline') {
    d3.select(`#${containerId}`).html("");

    if (!timelineData || !timelineData.timestamps || timelineData.timestamps.length === 0) {
        d3.select(`#${containerId}`)
            .append('div')
            .attr('class', 'alert alert-info')
            .text('No timeline data available');
        return;
    }

    const margin = { top: 30, right: 80, bottom: 50, left: 60 };
    const container = document.getElementById(containerId);
    const width = container.clientWidth - margin.left - margin.right;
    const height = 300;

    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left}, ${margin.top})`);

    // Add title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', -10)
        .attr('text-anchor', 'middle')
        .style('font-size', '16px')
        .style('font-weight', 'bold')
        .text(title);

    // Prepare data
    const categories = ['security_events', 'network_events', 'process_events', 'filesystem_events'];
    const colors = ['#dc3545', '#007bff', '#28a745', '#6c757d'];

    const x = d3.scaleLinear()
        .domain([0, timelineData.timestamps.length - 1])
        .range([0, width]);

    const y = d3.scaleLinear()
        .domain([0, d3.max(categories, cat => d3.max(timelineData[cat] || []))])
        .range([height, 0]);

    const line = d3.line()
        .x((d, i) => x(i))
        .y(d => y(d))
        .curve(d3.curveMonotoneX);

    // Add axes
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x));

    svg.append('g')
        .call(d3.axisLeft(y));

    // Add lines for each category
    categories.forEach((category, index) => {
        if (timelineData[category] && timelineData[category].length > 0) {
            svg.append('path')
                .datum(timelineData[category])
                .attr('fill', 'none')
                .attr('stroke', colors[index])
                .attr('stroke-width', 2)
                .attr('d', line);

            // Add legend item
            svg.append('circle')
                .attr('cx', width + 10)
                .attr('cy', 20 + index * 20)
                .attr('r', 6)
                .style('fill', colors[index]);

            svg.append('text')
                .attr('x', width + 25)
                .attr('y', 20 + index * 20)
                .attr('dy', '0.35em')
                .style('font-size', '12px')
                .text(category.replace('_', ' '));
        }
    });
}