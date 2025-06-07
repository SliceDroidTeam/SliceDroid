// Chart helper functions using D3.js

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