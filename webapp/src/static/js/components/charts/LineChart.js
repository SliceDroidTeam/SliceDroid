/**
 * LineChart - Specialized line chart component extending BaseChart
 */
class LineChart extends BaseChart {
    constructor(containerId, options = {}) {
        super(containerId, {
            // Default line chart options
            showPoints: true,
            pointRadius: 4,
            lineWidth: 2,
            curveType: 'cardinal', // linear, cardinal, basis, monotone
            showArea: false,
            areaOpacity: 0.3,
            showGrid: true,
            gridLines: 'both',
            multiSeries: false,
            interpolate: true,
            xAxis: {
                show: true,
                label: '',
                type: 'time', // 'time', 'linear', 'ordinal'
                tickFormat: null,
                tickRotation: 0
            },
            yAxis: {
                show: true,
                label: '',
                scale: 'linear', // 'linear' or 'log'
                tickFormat: null,
                domain: null // [min, max] or null for auto
            },
            tooltip: {
                enabled: true,
                showValue: true,
                showTime: true,
                customFormat: null
            },
            legend: {
                show: false,
                position: 'top-right'
            },
            zoom: {
                enabled: false,
                type: 'x' // 'x', 'y', 'xy'
            },
            ...options
        });
        
        this.xScale = null;
        this.yScale = null;
        this.line = null;
        this.area = null;
        this.zoomBehavior = null;
    }
    
    /**
     * Render the line chart
     */
    render() {
        if (!this.data || this.data.length === 0) {
            this.showEmpty('No data available for line chart');
            return;
        }
        
        this.updateDimensions();
        this.createSVG();
        this.setupScales();
        this.drawGrid();
        this.drawAxes();
        this.drawLines();
        this.addInteractivity();
        
        if (this.options.zoom.enabled) {
            this.setupZoom();
        }
        
        if (this.options.title) {
            this.addTitle(this.options.title);
        }
        
        if (this.options.legend.show) {
            this.addLegend(this.getLegendData(), this.options.legend.position);
        }
    }
    
    /**
     * Setup scales
     */
    setupScales() {
        const data = this.processData();
        
        // X Scale
        if (this.options.xAxis.type === 'time') {
            this.xScale = d3.scaleTime()
                .domain(d3.extent(data, d => d.x))
                .range([0, this.dimensions.chart.width]);
        } else if (this.options.xAxis.type === 'linear') {
            this.xScale = d3.scaleLinear()
                .domain(d3.extent(data, d => d.x))
                .range([0, this.dimensions.chart.width])
                .nice();
        } else {
            // Ordinal scale
            this.xScale = d3.scalePoint()
                .domain(data.map(d => d.x))
                .range([0, this.dimensions.chart.width])
                .padding(0.1);
        }
        
        // Y Scale
        const yDomain = this.options.yAxis.domain || d3.extent(data, d => d.y);
        
        this.yScale = this.options.yAxis.scale === 'log' ?
            d3.scaleLog()
                .domain([Math.max(1, yDomain[0]), yDomain[1]])
                .range([this.dimensions.chart.height, 0]) :
            d3.scaleLinear()
                .domain(yDomain)
                .range([this.dimensions.chart.height, 0])
                .nice();
        
        // Setup line and area generators
        this.setupGenerators();
    }
    
    /**
     * Setup line and area generators
     */
    setupGenerators() {
        const curveMap = {
            linear: d3.curveLinear,
            cardinal: d3.curveCardinal,
            basis: d3.curveBasis,
            monotone: d3.curveMonotoneX
        };
        
        const curve = curveMap[this.options.curveType] || d3.curveCardinal;
        
        this.line = d3.line()
            .x(d => this.xScale(d.x))
            .y(d => this.yScale(d.y))
            .curve(curve);
        
        if (this.options.interpolate) {
            this.line.defined(d => d.y !== null && d.y !== undefined && !isNaN(d.y));
        }
        
        if (this.options.showArea) {
            this.area = d3.area()
                .x(d => this.xScale(d.x))
                .y0(this.yScale(0))
                .y1(d => this.yScale(d.y))
                .curve(curve);
                
            if (this.options.interpolate) {
                this.area.defined(d => d.y !== null && d.y !== undefined && !isNaN(d.y));
            }
        }
    }
    
    /**
     * Draw grid lines
     */
    drawGrid() {
        if (!this.options.showGrid) return;
        
        const gridGroup = this.chartGroup.append('g')
            .attr('class', 'grid')
            .style('stroke', this.getThemeProperties().grid)
            .style('stroke-width', 1)
            .style('opacity', 0.3);
        
        if (this.options.gridLines === 'horizontal' || this.options.gridLines === 'both') {
            gridGroup.selectAll('.horizontal-grid')
                .data(this.yScale.ticks())
                .enter()
                .append('line')
                .attr('class', 'horizontal-grid')
                .attr('x1', 0)
                .attr('x2', this.dimensions.chart.width)
                .attr('y1', d => this.yScale(d))
                .attr('y2', d => this.yScale(d));
        }
        
        if (this.options.gridLines === 'vertical' || this.options.gridLines === 'both') {
            gridGroup.selectAll('.vertical-grid')
                .data(this.xScale.ticks ? this.xScale.ticks() : this.xScale.domain())
                .enter()
                .append('line')
                .attr('class', 'vertical-grid')
                .attr('x1', d => this.xScale(d))
                .attr('x2', d => this.xScale(d))
                .attr('y1', 0)
                .attr('y2', this.dimensions.chart.height);
        }
    }
    
    /**
     * Draw axes
     */
    drawAxes() {
        // X axis
        if (this.options.xAxis.show) {
            let xAxis = d3.axisBottom(this.xScale);
            
            if (this.options.xAxis.tickFormat) {
                xAxis.tickFormat(this.options.xAxis.tickFormat);
            } else if (this.options.xAxis.type === 'time') {
                xAxis.tickFormat(d3.timeFormat('%H:%M'));
            }
            
            const xAxisGroup = this.chartGroup.append('g')
                .attr('class', 'x-axis')
                .attr('transform', `translate(0, ${this.dimensions.chart.height})`)
                .call(xAxis);
            
            // Rotate tick labels if needed
            if (this.options.xAxis.tickRotation) {
                xAxisGroup.selectAll('text')
                    .style('text-anchor', 'end')
                    .attr('dx', '-0.8em')
                    .attr('dy', '0.15em')
                    .attr('transform', `rotate(${this.options.xAxis.tickRotation})`);
            }
            
            // Add axis label
            if (this.options.xAxis.label) {
                xAxisGroup.append('text')
                    .attr('x', this.dimensions.chart.width / 2)
                    .attr('y', 40)
                    .attr('text-anchor', 'middle')
                    .style('font-size', '12px')
                    .text(this.options.xAxis.label);
            }
        }
        
        // Y axis
        if (this.options.yAxis.show) {
            let yAxis = d3.axisLeft(this.yScale);
            
            if (this.options.yAxis.tickFormat) {
                yAxis.tickFormat(this.options.yAxis.tickFormat);
            }
            
            const yAxisGroup = this.chartGroup.append('g')
                .attr('class', 'y-axis')
                .call(yAxis);
            
            // Add axis label
            if (this.options.yAxis.label) {
                yAxisGroup.append('text')
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
     * Draw lines
     */
    drawLines() {
        const data = this.processData();
        
        if (this.options.multiSeries) {
            this.drawMultiSeries(data);
        } else {
            this.drawSingleSeries(data);
        }
    }
    
    /**
     * Draw single series line
     */
    drawSingleSeries(data) {
        // Draw area if enabled
        if (this.options.showArea && this.area) {
            const areaPath = this.chartGroup.append('path')
                .datum(data)
                .attr('class', 'line-area')
                .attr('fill', this.getColor(0, 'primary'))
                .attr('opacity', this.options.areaOpacity)
                .attr('d', this.area);
            
            // Animate area
            const totalAreaLength = areaPath.node().getTotalLength();
            areaPath
                .attr('stroke-dasharray', totalAreaLength + ' ' + totalAreaLength)
                .attr('stroke-dashoffset', totalAreaLength)
                .transition()
                .duration(this.options.animation.duration)
                .attr('stroke-dashoffset', 0);
        }
        
        // Draw line
        const linePath = this.chartGroup.append('path')
            .datum(data)
            .attr('class', 'line-path')
            .attr('fill', 'none')
            .attr('stroke', this.getColor(0, 'primary'))
            .attr('stroke-width', this.options.lineWidth)
            .attr('stroke-linejoin', 'round')
            .attr('stroke-linecap', 'round')
            .attr('d', this.line);
        
        // Animate line drawing
        const totalLength = linePath.node().getTotalLength();
        linePath
            .attr('stroke-dasharray', totalLength + ' ' + totalLength)
            .attr('stroke-dashoffset', totalLength)
            .transition()
            .duration(this.options.animation.duration)
            .attr('stroke-dashoffset', 0);
        
        // Draw points if enabled
        if (this.options.showPoints) {
            this.drawPoints(data, 0);
        }
    }
    
    /**
     * Draw multiple series
     */
    drawMultiSeries(seriesData) {
        seriesData.forEach((series, index) => {
            const color = this.getColor(index, 'primary');
            
            // Draw area if enabled
            if (this.options.showArea && this.area) {
                this.chartGroup.append('path')
                    .datum(series.data)
                    .attr('class', `line-area series-${index}`)
                    .attr('fill', color)
                    .attr('opacity', this.options.areaOpacity)
                    .attr('d', this.area);
            }
            
            // Draw line
            const linePath = this.chartGroup.append('path')
                .datum(series.data)
                .attr('class', `line-path series-${index}`)
                .attr('fill', 'none')
                .attr('stroke', color)
                .attr('stroke-width', this.options.lineWidth)
                .attr('stroke-linejoin', 'round')
                .attr('stroke-linecap', 'round')
                .attr('d', this.line);
            
            // Animate line drawing with delay
            const totalLength = linePath.node().getTotalLength();
            linePath
                .attr('stroke-dasharray', totalLength + ' ' + totalLength)
                .attr('stroke-dashoffset', totalLength)
                .transition()
                .delay(index * 200)
                .duration(this.options.animation.duration)
                .attr('stroke-dashoffset', 0);
            
            // Draw points if enabled
            if (this.options.showPoints) {
                this.drawPoints(series.data, index);
            }
        });
    }
    
    /**
     * Draw points on the line
     */
    drawPoints(data, seriesIndex) {
        const points = this.chartGroup.selectAll(`.point-series-${seriesIndex}`)
            .data(data)
            .enter()
            .append('circle')
            .attr('class', `line-point point-series-${seriesIndex}`)
            .attr('cx', d => this.xScale(d.x))
            .attr('cy', d => this.yScale(d.y))
            .attr('r', 0)
            .attr('fill', this.getColor(seriesIndex, 'primary'))
            .attr('stroke', this.getThemeProperties().background)
            .attr('stroke-width', 2);
        
        // Animate points
        points.transition()
            .delay((d, i) => i * 50 + seriesIndex * 200)
            .duration(300)
            .attr('r', this.options.pointRadius);
    }
    
    /**
     * Add interactivity
     */
    addInteractivity() {
        // Add invisible overlay for mouse tracking
        const overlay = this.chartGroup.append('rect')
            .attr('class', 'line-chart-overlay')
            .attr('width', this.dimensions.chart.width)
            .attr('height', this.dimensions.chart.height)
            .attr('fill', 'none')
            .attr('pointer-events', 'all');
        
        // Add tooltip line
        const tooltipLine = this.chartGroup.append('line')
            .attr('class', 'tooltip-line')
            .style('stroke', this.getThemeProperties().text)
            .style('stroke-width', 1)
            .style('stroke-dasharray', '3,3')
            .style('opacity', 0);
        
        overlay.on('mousemove', (event) => {
            if (this.options.tooltip.enabled) {
                this.handleMouseMove(event, tooltipLine);
            }
        })
        .on('mouseout', () => {
            this.hideTooltip();
            tooltipLine.style('opacity', 0);
        });
    }
    
    /**
     * Handle mouse move for tooltip
     */
    handleMouseMove(event, tooltipLine) {
        const [mouseX] = d3.pointer(event);
        const data = this.processData();
        
        // Find closest data point
        const x0 = this.xScale.invert(mouseX);
        const bisector = d3.bisector(d => d.x).left;
        const i = bisector(data, x0, 1);
        const d0 = data[i - 1];
        const d1 = data[i];
        
        if (!d0 && !d1) return;
        
        const d = d0 && d1 ? (x0 - d0.x > d1.x - x0 ? d1 : d0) : (d0 || d1);
        
        // Update tooltip line
        tooltipLine
            .attr('x1', this.xScale(d.x))
            .attr('x2', this.xScale(d.x))
            .attr('y1', 0)
            .attr('y2', this.dimensions.chart.height)
            .style('opacity', 1);
        
        // Show tooltip
        this.showTooltip({ pageX: event.pageX, pageY: event.pageY }, d);
    }
    
    /**
     * Show tooltip
     */
    showTooltip(event, d) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'line-chart-tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(0,0,0,0.8)')
            .style('color', 'white')
            .style('padding', '8px 12px')
            .style('border-radius', '4px')
            .style('pointer-events', 'none')
            .style('z-index', 1000)
            .style('font-size', '12px')
            .style('opacity', 0);
        
        let content = '';
        
        if (this.options.tooltip.showTime && this.options.xAxis.type === 'time') {
            content += `<strong>${d3.timeFormat('%Y-%m-%d %H:%M')(d.x)}</strong><br>`;
        } else {
            content += `<strong>${d.x}</strong><br>`;
        }
        
        if (this.options.tooltip.showValue) {
            content += `Value: ${this.formatValue(d.y)}`;
        }
        
        if (this.options.tooltip.customFormat) {
            content = this.options.tooltip.customFormat(d);
        }
        
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
        d3.selectAll('.line-chart-tooltip').remove();
    }
    
    /**
     * Setup zoom behavior
     */
    setupZoom() {
        this.zoomBehavior = d3.zoom()
            .scaleExtent([1, 10])
            .translateExtent([[0, 0], [this.dimensions.chart.width, this.dimensions.chart.height]])
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
        
        // Update scales
        const newXScale = transform.rescaleX(this.xScale);
        const newYScale = this.options.zoom.type === 'xy' ? transform.rescaleY(this.yScale) : this.yScale;
        
        // Update axes
        this.chartGroup.select('.x-axis').call(d3.axisBottom(newXScale));
        if (this.options.zoom.type === 'xy') {
            this.chartGroup.select('.y-axis').call(d3.axisLeft(newYScale));
        }
        
        // Update line
        this.line.x(d => newXScale(d.x)).y(d => newYScale(d.y));
        this.chartGroup.selectAll('.line-path').attr('d', this.line);
        
        // Update area if enabled
        if (this.options.showArea && this.area) {
            this.area.x(d => newXScale(d.x)).y1(d => newYScale(d.y)).y0(newYScale(0));
            this.chartGroup.selectAll('.line-area').attr('d', this.area);
        }
        
        // Update points
        this.chartGroup.selectAll('.line-point')
            .attr('cx', d => newXScale(d.x))
            .attr('cy', d => newYScale(d.y));
    }
    
    /**
     * Add zoom controls
     */
    addZoomControls() {
        const controls = this.container.append('div')
            .attr('class', 'line-chart-zoom-controls')
            .style('position', 'absolute')
            .style('top', '10px')
            .style('right', '10px');
        
        controls.append('button')
            .attr('class', 'btn btn-sm btn-outline-secondary')
            .text('Reset Zoom')
            .on('click', () => {
                this.chartGroup.transition()
                    .duration(750)
                    .call(this.zoomBehavior.transform, d3.zoomIdentity);
            });
    }
    
    /**
     * Process data for line chart
     */
    processData() {
        if (!this.data) return [];
        
        if (this.options.multiSeries) {
            // Expect array of series objects
            return this.data.map(series => ({
                name: series.name || series.label || 'Series',
                data: this.processSeriesData(series.data || series.values || [])
            }));
        } else {
            return this.processSeriesData(this.data);
        }
    }
    
    /**
     * Process single series data
     */
    processSeriesData(data) {
        if (!Array.isArray(data)) return [];
        
        return data.map(item => {
            if (typeof item === 'object' && item.x !== undefined && item.y !== undefined) {
                return {
                    x: this.options.xAxis.type === 'time' ? new Date(item.x) : item.x,
                    y: Number(item.y) || 0
                };
            } else if (Array.isArray(item) && item.length >= 2) {
                return {
                    x: this.options.xAxis.type === 'time' ? new Date(item[0]) : item[0],
                    y: Number(item[1]) || 0
                };
            }
            return null;
        }).filter(d => d !== null);
    }
    
    /**
     * Get legend data
     */
    getLegendData() {
        if (this.options.multiSeries) {
            const data = this.processData();
            return data.map((series, index) => ({
                label: series.name,
                color: this.getColor(index, 'primary')
            }));
        } else {
            return [{
                label: this.options.title || 'Data',
                color: this.getColor(0, 'primary')
            }];
        }
    }
    
    /**
     * Format value for display
     */
    formatValue(value) {
        if (this.options.yAxis.tickFormat) {
            return this.options.yAxis.tickFormat(value);
        }
        
        if (typeof value === 'number') {
            return value.toLocaleString();
        }
        
        return value;
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
        const processedData = this.processData();
        
        switch (format) {
            case 'csv':
                if (this.options.multiSeries) {
                    // Multi-series CSV
                    const headers = ['x', ...processedData.map(s => s.name)];
                    const csvHeader = headers.join(',') + '\n';
                    
                    // Get all x values
                    const allXValues = [...new Set(
                        processedData.flatMap(s => s.data.map(d => d.x))
                    )].sort();
                    
                    const csvRows = allXValues.map(x => {
                        const row = [x];
                        processedData.forEach(series => {
                            const point = series.data.find(d => d.x === x);
                            row.push(point ? point.y : '');
                        });
                        return row.join(',');
                    }).join('\n');
                    
                    return csvHeader + csvRows;
                } else {
                    const csvHeader = 'x,y\n';
                    const csvRows = processedData.map(d => `${d.x},${d.y}`).join('\n');
                    return csvHeader + csvRows;
                }
            
            case 'json':
            default:
                return JSON.stringify(processedData, null, 2);
        }
    }
}

// Register with ChartFactory
if (typeof chartRegistry !== 'undefined') {
    chartRegistry.register('line', LineChart);
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LineChart;
} else {
    window.LineChart = LineChart;
}