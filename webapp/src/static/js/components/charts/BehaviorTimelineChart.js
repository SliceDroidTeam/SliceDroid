/**
 * BehaviorTimelineChart - Advanced behavior analysis timeline
 * Modernized from legacy behavior-timeline.js with full BaseChart integration
 */
class BehaviorTimelineChart extends BaseChart {
    constructor(containerId, options = {}) {
        super(containerId, {
            // Default behavior timeline options
            windowSize: 1000,
            windowStep: 800, // 200 overlap
            categories: ['read', 'write', 'ioctl', 'binder', 'network', 'other'],
            colorScheme: 'security',
            showTooltips: true,
            showLegend: true,
            zoom: {
                enabled: true,
                scaleExtent: [1, 10]
            },
            xAxis: {
                show: true,
                label: 'Behavior Windows'
            },
            yAxis: {
                show: true,
                label: 'Event Categories'
            },
            ...options
        });
        
        this.processedData = null;
        this.zoomBehavior = null;
        this.xScale = null;
        this.yScale = null;
        this.colorScale = null;
    }
    
    /**
     * Render the behavior timeline chart
     */
    render() {
        if (!this.data) {
            this.showEmpty('No behavior timeline data available');
            return;
        }
        
        // Process raw data into behavior windows
        this.processedData = this.processData();
        
        if (!this.processedData || this.processedData.windows.length === 0) {
            this.showEmpty('No behavior windows could be generated');
            return;
        }
        
        this.updateDimensions();
        this.createSVG();
        this.setupScales();
        this.drawChart();
        this.addInteractivity();
        
        if (this.options.zoom.enabled) {
            this.setupZoom();
        }
        
        if (this.options.title) {
            this.addTitle(this.options.title);
        }
        
        if (this.options.showLegend) {
            this.addLegend(this.getLegendData());
        }
    }
    
    /**
     * Setup scales for the chart
     */
    setupScales() {
        const { windows, categories } = this.processedData;
        
        // X scale for windows
        this.xScale = d3.scaleLinear()
            .domain([0, windows.length])
            .range([0, this.dimensions.chart.width]);
        
        // Y scale for categories
        this.yScale = d3.scaleBand()
            .domain(categories)
            .range([0, this.dimensions.chart.height])
            .padding(0.1);
        
        // Color scale for categories
        this.colorScale = d3.scaleOrdinal()
            .domain(categories)
            .range(ChartThemes.getColorScheme(this.options.theme, this.options.colorScheme));
    }
    
    /**
     * Draw the behavior timeline chart
     */
    drawChart() {
        const { windows, categories } = this.processedData;
        
        // Add axes
        this.drawAxes();
        
        // Draw category labels
        this.drawCategoryLabels();
        
        // Draw behavior windows
        this.drawBehaviorWindows(windows, categories);
    }
    
    /**
     * Draw axes
     */
    drawAxes() {
        if (this.options.xAxis.show) {
            const xAxis = d3.axisBottom(this.xScale)
                .tickFormat(d => `W${Math.floor(d) + 1}`);
            
            this.chartGroup.append('g')
                .attr('class', 'x-axis')
                .attr('transform', `translate(0, ${this.dimensions.chart.height})`)
                .call(xAxis);
            
            if (this.options.xAxis.label) {
                this.chartGroup.append('text')
                    .attr('x', this.dimensions.chart.width / 2)
                    .attr('y', this.dimensions.chart.height + 40)
                    .attr('text-anchor', 'middle')
                    .style('font-size', '12px')
                    .text(this.options.xAxis.label);
            }
        }
        
        if (this.options.yAxis.show) {
            const yAxis = d3.axisLeft(this.yScale);
            
            this.chartGroup.append('g')
                .attr('class', 'y-axis')
                .call(yAxis);
            
            if (this.options.yAxis.label) {
                this.chartGroup.append('text')
                    .attr('transform', 'rotate(-90)')
                    .attr('y', -40)
                    .attr('x', -this.dimensions.chart.height / 2)
                    .attr('text-anchor', 'middle')
                    .style('font-size', '12px')
                    .text(this.options.yAxis.label);
            }
        }
    }
    
    /**
     * Draw category labels
     */
    drawCategoryLabels() {
        this.chartGroup.selectAll('.category-label')
            .data(this.options.categories)
            .enter()
            .append('text')
            .attr('class', 'category-label')
            .attr('x', -10)
            .attr('y', d => this.yScale(d) + this.yScale.bandwidth() / 2)
            .attr('text-anchor', 'end')
            .attr('dominant-baseline', 'middle')
            .style('font-size', '12px')
            .style('font-weight', '500')
            .text(d => d.charAt(0).toUpperCase() + d.slice(1));
    }
    
    /**
     * Draw behavior windows
     */
    drawBehaviorWindows(windows, categories) {
        windows.forEach((window, windowIndex) => {
            const windowCategories = window.categories || {};
            const maxCount = Math.max(...Object.values(windowCategories));
            
            categories.forEach(category => {
                const count = windowCategories[category] || 0;
                if (count > 0) {
                    const intensity = maxCount > 0 ? count / maxCount : 0;
                    
                    const rect = this.chartGroup.append('rect')
                        .attr('class', 'behavior-window-cell')
                        .attr('x', this.xScale(windowIndex))
                        .attr('y', this.yScale(category))
                        .attr('width', Math.max(1, this.xScale(1) - this.xScale(0) - 1))
                        .attr('height', this.yScale.bandwidth())
                        .attr('fill', this.colorScale(category))
                        .attr('opacity', 0.3 + (intensity * 0.7))
                        .attr('stroke', this.getThemeProperties().background)
                        .attr('stroke-width', 1)
                        .style('cursor', 'pointer')
                        .datum({ window, category, count, windowIndex, intensity });
                    
                    // Animate appearance
                    rect.style('opacity', 0)
                        .transition()
                        .duration(this.options.animation.duration)
                        .delay(windowIndex * 50)
                        .style('opacity', 0.3 + (intensity * 0.7));
                }
            });
        });
    }
    
    /**
     * Add interactivity
     */
    addInteractivity() {
        const cells = this.chartGroup.selectAll('.behavior-window-cell');
        
        cells.on('mouseover', (event, d) => {
            // Highlight cell
            d3.select(event.currentTarget)
                .transition()
                .duration(200)
                .attr('stroke', this.getThemeProperties().accent)
                .attr('stroke-width', 2);
            
            if (this.options.showTooltips) {
                this.showTooltip(event, d);
            }
        })
        .on('mouseout', (event, d) => {
            // Remove highlight
            d3.select(event.currentTarget)
                .transition()
                .duration(200)
                .attr('stroke', this.getThemeProperties().background)
                .attr('stroke-width', 1);
            
            this.hideTooltip();
        })
        .on('click', (event, d) => {
            this.handleCellClick(event, d);
        });
    }
    
    /**
     * Show tooltip for behavior window cell
     */
    showTooltip(event, d) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'behavior-timeline-tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(0,0,0,0.8)')
            .style('color', 'white')
            .style('padding', '8px 12px')
            .style('border-radius', '4px')
            .style('pointer-events', 'none')
            .style('z-index', 1000)
            .style('font-size', '12px')
            .style('opacity', 0);
        
        const content = `
            <strong>Window ${d.windowIndex + 1}</strong><br>
            Category: ${d.category}<br>
            Events: ${d.count}<br>
            Range: ${d.window.start_event}-${d.window.end_event}<br>
            ${d.window.sensitive_accesses ? `Sensitive: ${d.window.sensitive_accesses}<br>` : ''}
            ${d.window.network_activity ? `Network: ${d.window.network_activity}` : ''}
        `;
        
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
        d3.selectAll('.behavior-timeline-tooltip').remove();
    }
    
    /**
     * Handle cell click
     */
    handleCellClick(event, d) {
        const clickEvent = new CustomEvent('behaviorCellClick', {
            detail: { data: d, chart: this }
        });
        
        document.dispatchEvent(clickEvent);
        
        if (this.options.onCellClick) {
            this.options.onCellClick(d, this);
        }
    }
    
    /**
     * Setup zoom behavior
     */
    setupZoom() {
        this.zoomBehavior = d3.zoom()
            .scaleExtent(this.options.zoom.scaleExtent)
            .on('zoom', (event) => this.handleZoom(event));
        
        this.chartGroup.call(this.zoomBehavior);
        
        // Add zoom controls
        this.addZoomControls();
    }
    
    /**
     * Handle zoom
     */
    handleZoom(event) {
        const { transform } = event;
        const newXScale = transform.rescaleX(this.xScale);
        
        // Update cells
        this.chartGroup.selectAll('.behavior-window-cell')
            .attr('x', d => newXScale(d.windowIndex))
            .attr('width', Math.max(1, newXScale(1) - newXScale(0) - 1));
        
        // Update axis
        this.chartGroup.select('.x-axis')
            .call(d3.axisBottom(newXScale).tickFormat(d => `W${Math.floor(d) + 1}`));
    }
    
    /**
     * Add zoom controls
     */
    addZoomControls() {
        const controls = this.svg.append('g')
            .attr('class', 'zoom-controls')
            .attr('transform', `translate(${this.dimensions.total.width - 100}, 10)`);
        
        // Zoom in
        controls.append('rect')
            .attr('width', 25).attr('height', 25)
            .attr('fill', this.getThemeProperties().background)
            .attr('stroke', this.getThemeProperties().grid)
            .style('cursor', 'pointer')
            .on('click', () => this.zoomIn());
        
        controls.append('text')
            .attr('x', 12.5).attr('y', 17)
            .attr('text-anchor', 'middle')
            .style('pointer-events', 'none')
            .text('+');
        
        // Zoom out
        controls.append('rect')
            .attr('x', 30).attr('width', 25).attr('height', 25)
            .attr('fill', this.getThemeProperties().background)
            .attr('stroke', this.getThemeProperties().grid)
            .style('cursor', 'pointer')
            .on('click', () => this.zoomOut());
        
        controls.append('text')
            .attr('x', 42.5).attr('y', 17)
            .attr('text-anchor', 'middle')
            .style('pointer-events', 'none')
            .text('-');
        
        // Reset
        controls.append('rect')
            .attr('x', 60).attr('width', 25).attr('height', 25)
            .attr('fill', this.getThemeProperties().background)
            .attr('stroke', this.getThemeProperties().grid)
            .style('cursor', 'pointer')
            .on('click', () => this.resetZoom());
        
        controls.append('text')
            .attr('x', 72.5).attr('y', 17)
            .attr('text-anchor', 'middle')
            .style('pointer-events', 'none')
            .text('⟲');
    }
    
    /**
     * Zoom controls
     */
    zoomIn() {
        this.chartGroup.transition().duration(300)
            .call(this.zoomBehavior.scaleBy, 1.5);
    }
    
    zoomOut() {
        this.chartGroup.transition().duration(300)
            .call(this.zoomBehavior.scaleBy, 1 / 1.5);
    }
    
    resetZoom() {
        this.chartGroup.transition().duration(750)
            .call(this.zoomBehavior.transform, d3.zoomIdentity);
    }
    
    /**
     * Process data into behavior windows
     */
    processData() {
        if (!this.data) return null;
        
        // Extract trace data from input
        const kdevsTrace = this.data.kdevs_trace || this.data.events || this.data;
        const tcpTrace = this.data.tcp_trace || [];
        const sensitiveTrace = this.data.sensitive_trace || [];
        const dev2cat = this.data.dev2cat || {};
        
        if (!Array.isArray(kdevsTrace) || kdevsTrace.length === 0) {
            return null;
        }
        
        const processedData = {
            windows: [],
            categories: this.options.categories,
            total_events: kdevsTrace.length
        };
        
        // Create time windows for behavior analysis
        for (let i = 0; i < kdevsTrace.length; i += this.options.windowStep) {
            const window = kdevsTrace.slice(i, i + this.options.windowSize);
            if (window.length < this.options.windowSize / 2) break;
            
            const windowAnalysis = this.analyzeWindow(window, tcpTrace, sensitiveTrace, dev2cat);
            windowAnalysis.window_id = Math.floor(i / this.options.windowStep);
            windowAnalysis.start_event = i;
            windowAnalysis.end_event = Math.min(i + this.options.windowSize, kdevsTrace.length);
            
            processedData.windows.push(windowAnalysis);
        }
        
        return processedData;
    }
    
    /**
     * Analyze a single behavior window
     */
    analyzeWindow(window, tcpTrace, sensitiveTrace, dev2cat) {
        const analysis = {
            event_count: window.length,
            categories: {},
            devices: new Set(),
            sensitive_accesses: 0,
            network_activity: 0
        };
        
        // Initialize categories
        this.options.categories.forEach(cat => {
            analysis.categories[cat] = 0;
        });
        
        // Analyze events in window
        window.forEach(event => {
            const category = this.categorizeEvent(event.event || event.type);
            if (analysis.categories[category] !== undefined) {
                analysis.categories[category]++;
            } else {
                analysis.categories.other++;
            }
            
            // Track devices
            if (event.device || event.k_dev) {
                analysis.devices.add(event.device || event.k_dev);
            }
            
            // Check for sensitive data access
            if (sensitiveTrace && this.isSensitiveAccess(event, sensitiveTrace)) {
                analysis.sensitive_accesses++;
            }
        });
        
        // Check for network activity in this time window
        if (tcpTrace && tcpTrace.length > 0) {
            const windowStart = window[0]?.timestamp || 0;
            const windowEnd = window[window.length - 1]?.timestamp || 0;
            
            analysis.network_activity = tcpTrace.filter(tcp => 
                tcp.timestamp >= windowStart && tcp.timestamp <= windowEnd
            ).length;
        }
        
        // Convert sets to counts
        analysis.unique_devices = analysis.devices.size;
        analysis.devices = Array.from(analysis.devices);
        
        // Determine dominant category
        analysis.dominant_category = Object.entries(analysis.categories)
            .reduce((a, b) => analysis.categories[a[0]] > analysis.categories[b[0]] ? a : b)[0];
        
        return analysis;
    }
    
    /**
     * Categorize an event type
     */
    categorizeEvent(eventType) {
        if (!eventType) return 'other';
        
        const type = eventType.toLowerCase();
        
        if (type.includes('read') || type.includes('pread')) return 'read';
        if (type.includes('write') || type.includes('pwrite')) return 'write';
        if (type.includes('ioctl')) return 'ioctl';
        if (type.includes('binder')) return 'binder';
        if (type.includes('tcp') || type.includes('udp') || type.includes('socket') || type.includes('inet')) return 'network';
        
        return 'other';
    }
    
    /**
     * Check if event is a sensitive data access
     */
    isSensitiveAccess(event, sensitiveTrace) {
        const pathname = event.pathname || event.path || '';
        const sensitivePatterns = ['/data/data/', '/system/', '/proc/', '/dev/'];
        
        return sensitivePatterns.some(pattern => pathname.includes(pattern));
    }
    
    /**
     * Get legend data
     */
    getLegendData() {
        return this.options.categories.map((category, index) => ({
            label: category.charAt(0).toUpperCase() + category.slice(1),
            color: this.colorScale(category)
        }));
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
        if (!this.processedData) return null;
        
        switch (format) {
            case 'csv':
                const csvHeader = 'window,category,count,start_event,end_event\n';
                const csvRows = [];
                
                this.processedData.windows.forEach((window, index) => {
                    Object.entries(window.categories).forEach(([category, count]) => {
                        if (count > 0) {
                            csvRows.push(`${index},${category},${count},${window.start_event},${window.end_event}`);
                        }
                    });
                });
                
                return csvHeader + csvRows.join('\n');
            
            case 'json':
            default:
                return JSON.stringify(this.processedData, null, 2);
        }
    }
}

// Register with ChartFactory
if (typeof chartRegistry !== 'undefined') {
    chartRegistry.register('behavior-timeline', BehaviorTimelineChart);
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BehaviorTimelineChart;
} else {
    window.BehaviorTimelineChart = BehaviorTimelineChart;
}