// Chart helper functions using D3.js

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

    const color = d3.scaleOrdinal(d3.schemeCategory10);

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

            const percent = ((d.data.value / d3.sum(data, d => d.value)) * 100).toFixed(1);
            tooltip.html(`<strong>${d.data.label}</strong><br>Count: ${d.data.value}<br>Percentage: ${percent}%`)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px")
                .transition().duration(200).style("opacity", 1);
        })
        .on("mouseout", function() {
            d3.selectAll(".chart-tooltip").remove();
        });

    // Add labels
    arcs.append("text")
        .attr("transform", d => `translate(${labelArc.centroid(d)})`)
        .attr("text-anchor", "middle")
        .attr("font-size", "12px")
        .text(d => {
            const percent = ((d.data.value / d3.sum(data, d => d.value)) * 100).toFixed(1);
            return percent > 5 ? `${percent}%` : ''; // Only show label if slice is > 5%
        });

    // Skip legend for device/event charts to avoid overlap - rely on hover tooltips instead
    // Legend causes overlap issues in the constrained space of the statistics cards
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