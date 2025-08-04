/**
 * BarChart - Specialized bar chart component extending BaseChart
 */
class BarChart extends BaseChart {
    constructor(containerId, options = {}) {
        super(containerId, {
            // Default bar chart options
            orientation: 'vertical', // 'vertical' or 'horizontal'
            barPadding: 0.1,
            cornerRadius: 4,
            showValues: true,
            showGrid: true,
            gridLines: 'horizontal', // 'horizontal', 'vertical', 'both', 'none'
            xAxis: {
                show: true,
                label: '',
                tickRotation: 0,
                tickFormat: null
            },
            yAxis: {
                show: true,
                label: '',
                tickFormat: null,
                scale: 'linear' // 'linear' or 'log'
            },
            tooltip: {
                enabled: true,
                showValue: true,
                customFormat: null
            },
            gradient: false,
            stacked: false,
            grouped: false,
            ...options
        });
        
        this.xScale = null;
        this.yScale = null;
        this.xAxis = null;
        this.yAxis = null;
    }
    
    /**
     * Render the bar chart
     */
    render() {
        if (!this.data || this.data.length === 0) {
            this.showEmpty('No data available for bar chart');
            return;
        }
        
        this.updateDimensions();
        this.createSVG();
        this.setupScales();
        this.drawGrid();
        this.drawAxes();
        this.drawBars();
        this.addInteractivity();
        
        if (this.options.title) {
            this.addTitle(this.options.title);
        }
    }
    
    /**
     * Setup scales for the chart
     */
    setupScales() {
        const data = this.processData();
        
        if (this.options.orientation === 'vertical') {
            // X scale for categories
            this.xScale = d3.scaleBand()
                .domain(data.map(d => d.label))
                .range([0, this.dimensions.chart.width])
                .padding(this.options.barPadding);
            
            // Y scale for values
            const yMax = d3.max(data, d => d.value) || 0;
            const yMin = Math.min(0, d3.min(data, d => d.value) || 0);
            
            this.yScale = this.options.yAxis.scale === 'log' ?
                d3.scaleLog()
                    .domain([Math.max(1, yMin), yMax])
                    .range([this.dimensions.chart.height, 0]) :
                d3.scaleLinear()
                    .domain([yMin, yMax])
                    .range([this.dimensions.chart.height, 0])
                    .nice();
        } else {
            // Horizontal orientation
            // Y scale for categories
            this.yScale = d3.scaleBand()
                .domain(data.map(d => d.label))
                .range([0, this.dimensions.chart.height])
                .padding(this.options.barPadding);
            
            // X scale for values
            const xMax = d3.max(data, d => d.value) || 0;
            const xMin = Math.min(0, d3.min(data, d => d.value) || 0);
            
            this.xScale = d3.scaleLinear()
                .domain([xMin, xMax])
                .range([0, this.dimensions.chart.width])
                .nice();
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
            if (this.options.orientation === 'vertical') {
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
        }
        
        if (this.options.gridLines === 'vertical' || this.options.gridLines === 'both') {
            if (this.options.orientation === 'horizontal') {
                gridGroup.selectAll('.vertical-grid')
                    .data(this.xScale.ticks())
                    .enter()
                    .append('line')
                    .attr('class', 'vertical-grid')
                    .attr('x1', d => this.xScale(d))
                    .attr('x2', d => this.xScale(d))
                    .attr('y1', 0)
                    .attr('y2', this.dimensions.chart.height);
            }
        }
    }
    
    /**
     * Draw axes
     */
    drawAxes() {
        if (this.options.orientation === 'vertical') {
            // X axis
            if (this.options.xAxis.show) {
                this.xAxis = d3.axisBottom(this.xScale);
                
                if (this.options.xAxis.tickFormat) {
                    this.xAxis.tickFormat(this.options.xAxis.tickFormat);
                }
                
                const xAxisGroup = this.chartGroup.append('g')
                    .attr('class', 'x-axis')
                    .attr('transform', `translate(0, ${this.dimensions.chart.height})`)
                    .call(this.xAxis);
                
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
                this.yAxis = d3.axisLeft(this.yScale);
                
                if (this.options.yAxis.tickFormat) {
                    this.yAxis.tickFormat(this.options.yAxis.tickFormat);
                }
                
                const yAxisGroup = this.chartGroup.append('g')
                    .attr('class', 'y-axis')
                    .call(this.yAxis);
                
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
        } else {
            // Horizontal orientation axes
            if (this.options.xAxis.show) {
                this.xAxis = d3.axisBottom(this.xScale);
                
                const xAxisGroup = this.chartGroup.append('g')
                    .attr('class', 'x-axis')
                    .attr('transform', `translate(0, ${this.dimensions.chart.height})`)
                    .call(this.xAxis);
                
                if (this.options.xAxis.label) {
                    xAxisGroup.append('text')
                        .attr('x', this.dimensions.chart.width / 2)
                        .attr('y', 40)
                        .attr('text-anchor', 'middle')
                        .style('font-size', '12px')
                        .text(this.options.xAxis.label);
                }
            }
            
            if (this.options.yAxis.show) {
                this.yAxis = d3.axisLeft(this.yScale);
                
                const yAxisGroup = this.chartGroup.append('g')
                    .attr('class', 'y-axis')
                    .call(this.yAxis);
                
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
    }
    
    /**
     * Draw bars
     */
    drawBars() {
        const data = this.processData();
        
        const bars = this.chartGroup.selectAll('.bar')
            .data(data)
            .enter()
            .append('g')
            .attr('class', 'bar-group');
        
        const rects = bars.append('rect')
            .attr('class', 'bar')
            .attr('fill', (d, i) => this.getBarColor(d, i))
            .attr('rx', this.options.cornerRadius)
            .attr('ry', this.options.cornerRadius);
        
        if (this.options.orientation === 'vertical') {
            rects
                .attr('x', d => this.xScale(d.label))
                .attr('width', this.xScale.bandwidth())
                .attr('y', this.dimensions.chart.height)
                .attr('height', 0);
            
            // Animate bars
            rects.transition()
                .duration(this.options.animation.duration)
                .attr('y', d => this.yScale(Math.max(0, d.value)))
                .attr('height', d => Math.abs(this.yScale(d.value) - this.yScale(0)));
        } else {
            rects
                .attr('x', 0)
                .attr('width', 0)
                .attr('y', d => this.yScale(d.label))
                .attr('height', this.yScale.bandwidth());
            
            // Animate bars
            rects.transition()
                .duration(this.options.animation.duration)
                .attr('x', d => this.xScale(Math.min(0, d.value)))
                .attr('width', d => Math.abs(this.xScale(d.value) - this.xScale(0)));
        }
        
        // Add value labels if enabled
        if (this.options.showValues) {
            this.addValueLabels(bars, data);
        }
    }
    
    /**
     * Add value labels to bars
     */
    addValueLabels(bars, data) {
        const labels = bars.append('text')
            .attr('class', 'bar-label')
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .style('font-size', '11px')
            .style('font-weight', '500')
            .style('fill', this.getThemeProperties().text)
            .style('pointer-events', 'none');
        
        if (this.options.orientation === 'vertical') {
            labels
                .attr('x', d => this.xScale(d.label) + this.xScale.bandwidth() / 2)
                .attr('y', this.dimensions.chart.height)
                .text(d => this.formatValue(d.value));
            
            // Animate labels
            labels.transition()
                .delay(this.options.animation.duration / 2)
                .duration(this.options.animation.duration / 2)
                .attr('y', d => {
                    const barY = this.yScale(Math.max(0, d.value));
                    const barHeight = Math.abs(this.yScale(d.value) - this.yScale(0));
                    return barY + (d.value >= 0 ? barHeight / 2 : -barHeight / 2);
                })
                .style('opacity', 1);
        } else {
            labels
                .attr('x', 0)
                .attr('y', d => this.yScale(d.label) + this.yScale.bandwidth() / 2)
                .text(d => this.formatValue(d.value));
            
            // Animate labels
            labels.transition()
                .delay(this.options.animation.duration / 2)
                .duration(this.options.animation.duration / 2)
                .attr('x', d => {
                    const barX = this.xScale(Math.min(0, d.value));
                    const barWidth = Math.abs(this.xScale(d.value) - this.xScale(0));
                    return barX + barWidth / 2;
                })
                .style('opacity', 1);
        }
    }
    
    /**
     * Add interactivity
     */
    addInteractivity() {
        const bars = this.chartGroup.selectAll('.bar-group');
        
        bars.on('mouseover', (event, d) => {
            // Highlight bar
            d3.select(event.currentTarget).select('.bar')
                .transition()
                .duration(200)
                .style('opacity', 0.8);
            
            if (this.options.tooltip.enabled) {
                this.showTooltip(event, d);
            }
        })
        .on('mouseout', (event, d) => {
            // Remove highlight
            d3.select(event.currentTarget).select('.bar')
                .transition()
                .duration(200)
                .style('opacity', 1);
            
            this.hideTooltip();
        })
        .on('click', (event, d) => {
            this.handleBarClick(event, d);
        });
        
        // Add keyboard navigation
        bars.attr('tabindex', 0)
            .on('keydown', (event, d) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    this.handleBarClick(event, d);
                }
            });
    }
    
    /**
     * Show tooltip
     */
    showTooltip(event, d) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'bar-chart-tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(0,0,0,0.8)')
            .style('color', 'white')
            .style('padding', '8px 12px')
            .style('border-radius', '4px')
            .style('pointer-events', 'none')
            .style('z-index', 1000)
            .style('font-size', '12px')
            .style('opacity', 0);
        
        let content = `<strong>${d.label}</strong>`;
        
        if (this.options.tooltip.showValue) {
            content += `<br>Value: ${this.formatValue(d.value)}`;
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
        d3.selectAll('.bar-chart-tooltip').remove();
    }
    
    /**
     * Handle bar click
     */
    handleBarClick(event, d) {
        const clickEvent = new CustomEvent('barClick', {
            detail: { data: d, chart: this }
        });
        
        document.dispatchEvent(clickEvent);
        
        if (this.options.onBarClick) {
            this.options.onBarClick(d, this);
        }
    }
    
    /**
     * Get bar color
     */
    getBarColor(d, index) {
        if (this.options.gradient) {
            const gradient = this.createGradient(index);
            return `url(#${gradient})`;
        }
        
        return d.color || this.getColor(index, 'primary');
    }
    
    /**
     * Create gradient for bar
     */
    createGradient(index) {
        const gradientId = `bar-gradient-${index}`;
        const color = this.getColor(index, 'primary');
        
        const defs = this.svg.select('defs').empty() ? 
            this.svg.append('defs') : this.svg.select('defs');
        
        const gradient = defs.append('linearGradient')
            .attr('id', gradientId)
            .attr('gradientUnits', 'userSpaceOnUse');
        
        if (this.options.orientation === 'vertical') {
            gradient.attr('x1', 0).attr('y1', 0)
                   .attr('x2', 0).attr('y2', this.dimensions.chart.height);
        } else {
            gradient.attr('x1', 0).attr('y1', 0)
                   .attr('x2', this.dimensions.chart.width).attr('y2', 0);
        }
        
        gradient.append('stop')
            .attr('offset', '0%')
            .attr('stop-color', d3.color(color).brighter(0.5));
        
        gradient.append('stop')
            .attr('offset', '100%')
            .attr('stop-color', color);
        
        return gradientId;
    }
    
    /**
     * Process data for bar chart
     */
    processData() {
        if (!this.data) return [];
        
        let processedData = [];
        
        if (Array.isArray(this.data)) {
            processedData = this.data.map(item => {
                if (typeof item === 'object' && item.value !== undefined) {
                    return {
                        label: item.label || item.name || item.key || 'Unknown',
                        value: typeof item.value === 'number' ? item.value : 0,
                        color: item.color
                    };
                } else if (typeof item === 'object') {
                    const value = item.count || item.size || item.amount || item.y || 0;
                    const label = item.label || item.name || item.key || item.x || 'Unknown';
                    return { label, value, color: item.color };
                }
                return { label: 'Item', value: Number(item) || 0 };
            });
        } else if (typeof this.data === 'object') {
            processedData = Object.entries(this.data).map(([key, value]) => ({
                label: key,
                value: typeof value === 'object' ? (value.value || 0) : Number(value) || 0
            }));
        }
        
        return processedData;
    }
    
    /**
     * Format value for display
     */
    formatValue(value) {
        if (this.options.yAxis.tickFormat && this.options.orientation === 'vertical') {
            return this.options.yAxis.tickFormat(value);
        }
        
        if (typeof value === 'number') {
            if (value >= 1000000) {
                return (value / 1000000).toFixed(1) + 'M';
            } else if (value >= 1000) {
                return (value / 1000).toFixed(1) + 'K';
            }
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
                const csvHeader = 'Label,Value\n';
                const csvRows = processedData.map(d => `"${d.label}",${d.value}`).join('\n');
                return csvHeader + csvRows;
            
            case 'json':
            default:
                return JSON.stringify(processedData, null, 2);
        }
    }
}

// Register with ChartFactory
if (typeof chartRegistry !== 'undefined') {
    chartRegistry.register('bar', BarChart);
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BarChart;
} else {
    window.BarChart = BarChart;
}