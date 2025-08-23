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
    const height = Math.min(300, container.clientHeight || 300) - margin.top - margin.bottom;

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