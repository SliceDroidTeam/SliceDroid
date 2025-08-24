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
    }
    
    // Start the rendering process
    tryRender();
}


