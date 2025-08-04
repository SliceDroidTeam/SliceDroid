/**
 * TimelineChart - Specialized timeline chart component extending BaseChart
 */
class TimelineChart extends BaseChart {
    constructor(containerId, options = {}) {
        super(containerId, {
            // Default timeline options
            showBrush: true,
            showZoom: true,
            eventHeight: 20,
            eventPadding: 2,
            timeFormat: '%H:%M:%S',
            dateFormat: '%Y-%m-%d',
            colorBy: 'category', // 'category', 'severity', 'custom'
            categoryColors: ChartConstants.COLOR_SCHEMES.SECURITY,
            showTooltips: true,
            showLabels: true,
            groupBy: null, // 'category', 'severity', or null
            xAxis: {
                show: true,
                tickFormat: null,
                orientation: 'bottom'
            },
            yAxis: {
                show: true,
                label: 'Events'
            },
            brush: {
                height: 60,
                margin: 20
            },
            zoom: {
                enabled: true,
                scaleExtent: [1, 50]
            },
            ...options
        });
        
        this.xScale = null;
        this.yScale = null;
        this.brush = null;
        this.zoom = null;
        this.processedData = null;
        this.mainChart = null;
        this.contextChart = null;
    }
    
    /**
     * Render the timeline chart
     */
    render() {
        if (!this.data || this.data.length === 0) {
            this.showEmpty('No timeline data available');
            return;
        }
        
        this.updateDimensions();
        this.processedData = this.processData();
        this.adjustDimensionsForBrush();
        this.createSVG();
        this.setupScales();
        this.createChartAreas();
        this.drawMainChart();
        
        if (this.options.showBrush) {
            this.drawContextChart();
            this.setupBrush();
        }
        
        if (this.options.zoom.enabled) {
            this.setupZoom();
        }
        
        this.addInteractivity();
        
        if (this.options.title) {
            this.addTitle(this.options.title);
        }
    }
    
    /**
     * Adjust dimensions to accommodate brush
     */
    adjustDimensionsForBrush() {
        if (this.options.showBrush) {
            this.dimensions.main = {
                width: this.dimensions.chart.width,
                height: this.dimensions.chart.height - this.options.brush.height - this.options.brush.margin
            };
            
            this.dimensions.context = {
                width: this.dimensions.chart.width,
                height: this.options.brush.height,
                y: this.dimensions.main.height + this.options.brush.margin
            };
        } else {
            this.dimensions.main = {
                width: this.dimensions.chart.width,
                height: this.dimensions.chart.height
            };
        }
    }
    
    /**
     * Setup scales
     */
    setupScales() {
        const timeExtent = d3.extent(this.processedData, d => d.timestamp);
        
        // Main chart scales
        this.xScale = d3.scaleTime()
            .domain(timeExtent)
            .range([0, this.dimensions.main.width]);
        
        // Y scale depends on grouping
        if (this.options.groupBy) {
            const groups = [...new Set(this.processedData.map(d => d[this.options.groupBy]))];
            this.yScale = d3.scaleBand()
                .domain(groups)
                .range([0, this.dimensions.main.height])
                .padding(0.1);
        } else {
            // Stack events by time
            this.yScale = d3.scaleLinear()
                .domain([0, this.calculateMaxConcurrentEvents()])
                .range([this.dimensions.main.height, 0]);
        }
        
        // Context chart scales (for brush)
        if (this.options.showBrush) {
            this.xScaleContext = d3.scaleTime()
                .domain(timeExtent)
                .range([0, this.dimensions.context.width]);
            
            this.yScaleContext = d3.scaleLinear()
                .domain([0, this.calculateMaxConcurrentEvents()])
                .range([this.dimensions.context.height, 0]);
        }
    }
    
    /**
     * Create chart areas
     */
    createChartAreas() {
        // Main chart area
        this.mainChart = this.chartGroup.append('g')
            .attr('class', 'main-chart')
            .attr('clip-path', 'url(#timeline-clip)');
        
        // Add clipping path
        this.svg.append('defs')
            .append('clipPath')
            .attr('id', 'timeline-clip')
            .append('rect')
            .attr('width', this.dimensions.main.width)
            .attr('height', this.dimensions.main.height);
        
        // Context chart area (for brush)
        if (this.options.showBrush) {
            this.contextChart = this.chartGroup.append('g')
                .attr('class', 'context-chart')
                .attr('transform', `translate(0, ${this.dimensions.context.y})`);
        }
    }
    
    /**
     * Draw main chart
     */
    drawMainChart() {
        this.drawAxes();
        this.drawEvents();
    }
    
    /**
     * Draw axes
     */
    drawAxes() {
        // X axis
        if (this.options.xAxis.show) {
            const xAxis = d3.axisBottom(this.xScale);
            
            if (this.options.xAxis.tickFormat) {
                xAxis.tickFormat(this.options.xAxis.tickFormat);
            } else {
                xAxis.tickFormat(d3.timeFormat(this.options.timeFormat));
            }
            
            this.mainChart.append('g')
                .attr('class', 'x-axis')
                .attr('transform', `translate(0, ${this.dimensions.main.height})`)
                .call(xAxis);
        }
        
        // Y axis
        if (this.options.yAxis.show && this.options.groupBy) {
            const yAxis = d3.axisLeft(this.yScale);
            
            this.mainChart.append('g')
                .attr('class', 'y-axis')
                .call(yAxis);
            
            // Add axis label
            if (this.options.yAxis.label) {
                this.mainChart.append('text')
                    .attr('transform', 'rotate(-90)')
                    .attr('y', -40)
                    .attr('x', -this.dimensions.main.height / 2)
                    .attr('text-anchor', 'middle')
                    .style('font-size', '12px')
                    .text(this.options.yAxis.label);
            }
        }
    }
    
    /**
     * Draw timeline events
     */
    drawEvents() {
        if (this.options.groupBy) {
            this.drawGroupedEvents();
        } else {
            this.drawStackedEvents();
        }
    }
    
    /**
     * Draw events grouped by category
     */
    drawGroupedEvents() {
        const groups = this.mainChart.selectAll('.event-group')
            .data(d3.group(this.processedData, d => d[this.options.groupBy]))
            .enter()
            .append('g')
            .attr('class', 'event-group');
        
        groups.each((groupData, groupKey, nodes) => {
            const group = d3.select(nodes[0]);
            const events = Array.from(groupData[1]);
            
            const eventRects = group.selectAll('.timeline-event')
                .data(events)
                .enter()
                .append('rect')
                .attr('class', 'timeline-event')
                .attr('x', d => this.xScale(d.timestamp))
                .attr('y', this.yScale(groupKey))
                .attr('width', 3)
                .attr('height', this.yScale.bandwidth())
                .attr('fill', (d, i) => this.getEventColor(d, i))
                .attr('opacity', 0);
            
            // Animate events
            eventRects.transition()
                .duration(this.options.animation.duration)
                .delay((d, i) => i * 50)
                .attr('opacity', 0.8);
        });
    }
    
    /**
     * Draw events stacked by time
     */
    drawStackedEvents() {
        // Group events by time buckets to handle overlapping
        const timeBuckets = this.createTimeBuckets();
        
        const events = this.mainChart.selectAll('.timeline-event')
            .data(this.processedData)
            .enter()
            .append('g')
            .attr('class', 'timeline-event-group');
        
        const eventRects = events.append('rect')
            .attr('class', 'timeline-event')
            .attr('x', d => this.xScale(d.timestamp))
            .attr('y', d => this.getEventY(d, timeBuckets))
            .attr('width', 4)
            .attr('height', this.options.eventHeight)
            .attr('rx', 2)
            .attr('fill', (d, i) => this.getEventColor(d, i))
            .attr('stroke', this.getThemeProperties().background)
            .attr('stroke-width', 1)
            .attr('opacity', 0);
        
        // Animate events
        eventRects.transition()
            .duration(this.options.animation.duration)
            .delay((d, i) => i * 20)
            .attr('opacity', 0.8);
        
        // Add event labels if enabled
        if (this.options.showLabels) {
            this.addEventLabels(events);
        }
    }
    
    /**
     * Add event labels
     */
    addEventLabels(events) {
        const labels = events.append('text')
            .attr('class', 'event-label')
            .attr('x', d => this.xScale(d.timestamp) + 6)
            .attr('y', d => this.getEventY(d, this.createTimeBuckets()) + this.options.eventHeight / 2)
            .attr('dominant-baseline', 'middle')
            .style('font-size', '10px')
            .style('font-weight', '500')
            .style('fill', this.getThemeProperties().text)
            .style('pointer-events', 'none')
            .style('opacity', 0)
            .text(d => d.label || d.event || '');
        
        // Show labels on hover
        events.on('mouseover', function() {
            d3.select(this).select('.event-label')
                .transition()
                .duration(200)
                .style('opacity', 1);
        })
        .on('mouseout', function() {
            d3.select(this).select('.event-label')
                .transition()
                .duration(200)
                .style('opacity', 0);
        });
    }
    
    /**
     * Draw context chart for brush
     */
    drawContextChart() {
        // Draw simplified version of events for context
        const contextEvents = this.contextChart.selectAll('.context-event')
            .data(this.processedData)
            .enter()
            .append('rect')
            .attr('class', 'context-event')
            .attr('x', d => this.xScaleContext(d.timestamp))
            .attr('y', this.dimensions.context.height - 5)
            .attr('width', 2)
            .attr('height', 5)
            .attr('fill', (d, i) => this.getEventColor(d, i))
            .attr('opacity', 0.6);
        
        // Add context axis
        const contextAxis = d3.axisBottom(this.xScaleContext)
            .tickFormat(d3.timeFormat(this.options.dateFormat));
        
        this.contextChart.append('g')
            .attr('class', 'context-axis')
            .attr('transform', `translate(0, ${this.dimensions.context.height})`)
            .call(contextAxis);
    }
    
    /**
     * Setup brush
     */
    setupBrush() {
        this.brush = d3.brushX()
            .extent([[0, 0], [this.dimensions.context.width, this.dimensions.context.height]])
            .on('brush end', (event) => this.handleBrush(event));
        
        const brushGroup = this.contextChart.append('g')
            .attr('class', 'brush')
            .call(this.brush);
        
        // Style brush
        brushGroup.select('.overlay')
            .style('cursor', 'crosshair');
        
        brushGroup.selectAll('.selection')
            .style('fill', this.getThemeProperties().accent)
            .style('opacity', 0.3);
    }
    
    /**
     * Handle brush events
     */
    handleBrush(event) {
        if (!event.selection) return;
        
        const [x0, x1] = event.selection;
        const newDomain = [this.xScaleContext.invert(x0), this.xScaleContext.invert(x1)];
        
        // Update main chart x scale
        this.xScale.domain(newDomain);
        
        // Update main chart
        this.updateMainChart();
    }
    
    /**
     * Update main chart after brush/zoom
     */
    updateMainChart() {
        // Update axis
        this.mainChart.select('.x-axis')
            .transition()
            .duration(300)
            .call(d3.axisBottom(this.xScale).tickFormat(d3.timeFormat(this.options.timeFormat)));
        
        // Update events
        this.mainChart.selectAll('.timeline-event')
            .transition()
            .duration(300)
            .attr('x', d => this.xScale(d.timestamp));
        
        // Update labels
        this.mainChart.selectAll('.event-label')
            .transition()
            .duration(300)
            .attr('x', d => this.xScale(d.timestamp) + 6);
    }
    
    /**
     * Setup zoom
     */
    setupZoom() {
        this.zoom = d3.zoom()
            .scaleExtent(this.options.zoom.scaleExtent)
            .translateExtent([[0, 0], [this.dimensions.main.width, this.dimensions.main.height]])
            .on('zoom', (event) => this.handleZoom(event));
        
        this.mainChart.call(this.zoom);
        
        // Add zoom controls
        this.addZoomControls();
    }
    
    /**
     * Handle zoom events
     */
    handleZoom(event) {
        const { transform } = event;
        const newScale = transform.rescaleX(this.xScale);
        
        // Update main chart
        this.mainChart.select('.x-axis')
            .call(d3.axisBottom(newScale).tickFormat(d3.timeFormat(this.options.timeFormat)));
        
        this.mainChart.selectAll('.timeline-event')
            .attr('x', d => newScale(d.timestamp));
        
        this.mainChart.selectAll('.event-label')
            .attr('x', d => newScale(d.timestamp) + 6);
    }
    
    /**
     * Add zoom controls
     */
    addZoomControls() {
        const controls = this.svg.append('g')
            .attr('class', 'zoom-controls')
            .attr('transform', `translate(${this.dimensions.total.width - 100}, 10)`);
        
        // Zoom in button
        controls.append('rect')
            .attr('class', 'zoom-btn zoom-in')
            .attr('width', 25)
            .attr('height', 25)
            .attr('fill', this.getThemeProperties().background)
            .attr('stroke', this.getThemeProperties().grid)
            .style('cursor', 'pointer')
            .on('click', () => this.zoomIn());
        
        controls.append('text')
            .attr('x', 12.5)
            .attr('y', 17)
            .attr('text-anchor', 'middle')
            .style('font-size', '16px')
            .style('pointer-events', 'none')
            .text('+');
        
        // Zoom out button
        controls.append('rect')
            .attr('class', 'zoom-btn zoom-out')
            .attr('x', 30)
            .attr('width', 25)
            .attr('height', 25)
            .attr('fill', this.getThemeProperties().background)
            .attr('stroke', this.getThemeProperties().grid)
            .style('cursor', 'pointer')
            .on('click', () => this.zoomOut());
        
        controls.append('text')
            .attr('x', 42.5)
            .attr('y', 17)
            .attr('text-anchor', 'middle')
            .style('font-size', '16px')
            .style('pointer-events', 'none')
            .text('-');
        
        // Reset button
        controls.append('rect')
            .attr('class', 'zoom-btn zoom-reset')
            .attr('x', 60)
            .attr('width', 25)
            .attr('height', 25)
            .attr('fill', this.getThemeProperties().background)
            .attr('stroke', this.getThemeProperties().grid)
            .style('cursor', 'pointer')
            .on('click', () => this.resetZoom());
        
        controls.append('text')
            .attr('x', 72.5)
            .attr('y', 17)
            .attr('text-anchor', 'middle')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .text('⟲');
    }
    
    /**
     * Zoom in
     */
    zoomIn() {
        this.mainChart.transition().duration(300).call(
            this.zoom.scaleBy, 1.5
        );
    }
    
    /**
     * Zoom out
     */
    zoomOut() {
        this.mainChart.transition().duration(300).call(
            this.zoom.scaleBy, 1 / 1.5
        );
    }
    
    /**
     * Reset zoom
     */
    resetZoom() {
        this.mainChart.transition().duration(750).call(
            this.zoom.transform,
            d3.zoomIdentity
        );
    }
    
    /**
     * Add interactivity
     */
    addInteractivity() {
        const events = this.mainChart.selectAll('.timeline-event-group');
        
        events.on('mouseover', (event, d) => {
            // Highlight event
            d3.select(event.currentTarget).select('.timeline-event')
                .transition()
                .duration(200)
                .attr('stroke-width', 2)
                .attr('opacity', 1);
            
            if (this.options.showTooltips) {
                this.showTooltip(event, d);
            }
        })
        .on('mouseout', (event, d) => {
            // Remove highlight
            d3.select(event.currentTarget).select('.timeline-event')
                .transition()
                .duration(200)
                .attr('stroke-width', 1)
                .attr('opacity', 0.8);
            
            this.hideTooltip();
        })
        .on('click', (event, d) => {
            this.handleEventClick(event, d);
        });
    }
    
    /**
     * Show tooltip
     */
    showTooltip(event, d) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'timeline-tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(0,0,0,0.8)')
            .style('color', 'white')
            .style('padding', '8px 12px')
            .style('border-radius', '4px')
            .style('pointer-events', 'none')
            .style('z-index', 1000)
            .style('font-size', '12px')
            .style('opacity', 0);
        
        const timeStr = d3.timeFormat('%Y-%m-%d %H:%M:%S')(d.timestamp);
        let content = `<strong>${timeStr}</strong><br>`;
        
        if (d.event) content += `Event: ${d.event}<br>`;
        if (d.category) content += `Category: ${d.category}<br>`;
        if (d.severity) content += `Severity: ${d.severity}<br>`;
        if (d.description) content += `Description: ${d.description}`;
        
        tooltip.html(content)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px')
            .transition()
            .duration(200)
            .style('opacity', 1);
    }
    
    /**
     * Hide tooltip
     */
    hideTooltip() {
        d3.selectAll('.timeline-tooltip').remove();
    }
    
    /**
     * Handle event click
     */
    handleEventClick(event, d) {
        const clickEvent = new CustomEvent('timelineEventClick', {
            detail: { data: d, chart: this }
        });
        
        document.dispatchEvent(clickEvent);
        
        if (this.options.onEventClick) {
            this.options.onEventClick(d, this);
        }
    }
    
    /**
     * Process data for timeline
     */
    processData() {
        if (!this.data || !Array.isArray(this.data)) return [];
        
        return this.data.map(item => {
            const timestamp = item.timestamp ? new Date(item.timestamp) : new Date();
            
            return {
                timestamp,
                event: item.event || item.type || 'Unknown',
                category: item.category || 'other',
                severity: item.severity || 'info',
                description: item.description || '',
                label: item.label || item.event || item.type,
                ...item
            };
        }).sort((a, b) => a.timestamp - b.timestamp);
    }
    
    /**
     * Create time buckets for stacking
     */
    createTimeBuckets() {
        const buckets = new Map();
        const bucketSize = 60000; // 1 minute buckets
        
        this.processedData.forEach(d => {
            const bucketKey = Math.floor(d.timestamp.getTime() / bucketSize);
            if (!buckets.has(bucketKey)) {
                buckets.set(bucketKey, []);
            }
            buckets.get(bucketKey).push(d);
        });
        
        return buckets;
    }
    
    /**
     * Calculate maximum concurrent events
     */
    calculateMaxConcurrentEvents() {
        const buckets = this.createTimeBuckets();
        return Math.max(...Array.from(buckets.values()).map(bucket => bucket.length));
    }
    
    /**
     * Get event Y position
     */
    getEventY(event, timeBuckets) {
        const bucketKey = Math.floor(event.timestamp.getTime() / 60000);
        const bucket = timeBuckets.get(bucketKey) || [];
        const index = bucket.indexOf(event);
        
        return this.dimensions.main.height - (index + 1) * (this.options.eventHeight + this.options.eventPadding);
    }
    
    /**
     * Get event color
     */
    getEventColor(event, index) {
        switch (this.options.colorBy) {
            case 'category':
                const categoryIndex = this.options.categoryColors.indexOf(event.category) !== -1 ?
                    this.options.categoryColors.indexOf(event.category) :
                    index % this.options.categoryColors.length;
                return this.options.categoryColors[categoryIndex];
            
            case 'severity':
                const severityColors = {
                    'critical': '#dc3545',
                    'high': '#fd7e14',
                    'medium': '#ffc107',
                    'low': '#28a745',
                    'info': '#17a2b8'
                };
                return severityColors[event.severity] || '#6c757d';
            
            case 'custom':
                return event.color || this.getColor(index, 'primary');
            
            default:
                return this.getColor(index, 'primary');
        }
    }
    
    /**
     * Get theme properties
     */
    getThemeProperties() {
        return ChartThemes.getThemeProperties(this.options.theme);
    }
    
    /**
     * Export chart data
     */
    exportData(format = 'json') {
        switch (format) {
            case 'csv':
                const csvHeader = 'timestamp,event,category,severity,description\n';
                const csvRows = this.processedData.map(d => 
                    `"${d.timestamp.toISOString()}","${d.event}","${d.category}","${d.severity}","${d.description}"`
                ).join('\n');
                return csvHeader + csvRows;
            
            case 'json':
            default:
                return JSON.stringify(this.processedData, null, 2);
        }
    }
}

// Register with ChartFactory
if (typeof chartRegistry !== 'undefined') {
    chartRegistry.register('timeline', TimelineChart);
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TimelineChart;
} else {
    window.TimelineChart = TimelineChart;
}