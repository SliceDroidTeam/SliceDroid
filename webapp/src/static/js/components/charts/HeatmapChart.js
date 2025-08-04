/**
 * HeatmapChart - Specialized heatmap chart component extending BaseChart
 */
class HeatmapChart extends BaseChart {
    constructor(containerId, options = {}) {
        super(containerId, {
            // Default heatmap options
            cellPadding: 2,
            colorScale: 'Blues', // 'Blues', 'Reds', 'Greens', 'Viridis', 'Plasma'
            showLabels: false,
            showValues: true,
            fontSize: 11,
            xAxis: {
                show: true,
                label: '',
                tickRotation: -45
            },
            yAxis: {
                show: true,
                label: '',
                tickRotation: 0
            },
            tooltip: {
                enabled: true,
                showCoordinates: true,
                showValue: true,
                customFormat: null
            },
            legend: {
                show: true,
                position: 'right',
                width: 20,
                height: 200
            },
            valueRange: null, // [min, max] or null for auto
            ...options
        });
        
        this.colorScale = null;
        this.xScale = null;
        this.yScale = null;
        this.processedData = null;
    }
    
    /**
     * Render the heatmap chart
     */
    render() {
        if (!this.data || this.data.length === 0) {
            this.showEmpty('No data available for heatmap');
            return;
        }
        
        this.updateDimensions();
        this.processedData = this.processData();
        this.createSVG();
        this.setupScales();
        this.drawAxes();
        this.drawHeatmap();
        this.addInteractivity();
        
        if (this.options.title) {
            this.addTitle(this.options.title);
        }
        
        if (this.options.legend.show) {
            this.drawLegend();
        }
    }
    
    /**
     * Setup scales for the heatmap
     */
    setupScales() {
        const { xValues, yValues, values } = this.processedData;
        
        // X scale (columns)
        this.xScale = d3.scaleBand()
            .domain(xValues)
            .range([0, this.dimensions.chart.width])
            .padding(0.1);
        
        // Y scale (rows)
        this.yScale = d3.scaleBand()
            .domain(yValues)
            .range([0, this.dimensions.chart.height])
            .padding(0.1);
        
        // Color scale
        const valueExtent = this.options.valueRange || d3.extent(values);
        const colorSchemes = {
            'Blues': d3.interpolateBlues,
            'Reds': d3.interpolateReds,
            'Greens': d3.interpolateGreens,
            'Viridis': d3.interpolateViridis,
            'Plasma': d3.interpolatePlasma,
            'Magma': d3.interpolateMagma,
            'Inferno': d3.interpolateInferno
        };
        
        const colorInterpolator = colorSchemes[this.options.colorScale] || d3.interpolateBlues;
        
        this.colorScale = d3.scaleSequential()
            .domain(valueExtent)
            .interpolator(colorInterpolator);
    }
    
    /**
     * Draw axes
     */
    drawAxes() {
        // X axis
        if (this.options.xAxis.show) {
            const xAxis = d3.axisBottom(this.xScale);
            
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
            const yAxis = d3.axisLeft(this.yScale);
            
            const yAxisGroup = this.chartGroup.append('g')
                .attr('class', 'y-axis')
                .call(yAxis);
            
            // Rotate tick labels if needed
            if (this.options.yAxis.tickRotation) {
                yAxisGroup.selectAll('text')
                    .attr('transform', `rotate(${this.options.yAxis.tickRotation})`);
            }
            
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
     * Draw heatmap cells
     */
    drawHeatmap() {
        const { data } = this.processedData;
        
        // Create cell groups
        const cells = this.chartGroup.selectAll('.heatmap-cell')
            .data(data)
            .enter()
            .append('g')
            .attr('class', 'heatmap-cell');
        
        // Draw cell rectangles
        const rects = cells.append('rect')
            .attr('class', 'cell-rect')
            .attr('x', d => this.xScale(d.x))
            .attr('y', d => this.yScale(d.y))
            .attr('width', this.xScale.bandwidth())
            .attr('height', this.yScale.bandwidth())
            .attr('rx', this.options.cellPadding)
            .attr('ry', this.options.cellPadding)
            .attr('fill', this.getThemeProperties().background)
            .attr('stroke', this.getThemeProperties().grid)
            .attr('stroke-width', 1);
        
        // Animate cell colors
        rects.transition()
            .duration(this.options.animation.duration)
            .delay((d, i) => i * 10)
            .attr('fill', d => this.colorScale(d.value))
            .attr('stroke', 'none');
        
        // Add value labels if enabled
        if (this.options.showValues) {
            this.addValueLabels(cells, data);
        }
        
        // Add cell labels if enabled
        if (this.options.showLabels) {
            this.addCellLabels(cells, data);
        }
    }
    
    /**
     * Add value labels to cells
     */
    addValueLabels(cells, data) {
        const labels = cells.append('text')
            .attr('class', 'cell-value')
            .attr('x', d => this.xScale(d.x) + this.xScale.bandwidth() / 2)
            .attr('y', d => this.yScale(d.y) + this.yScale.bandwidth() / 2)
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .style('font-size', `${this.options.fontSize}px`)
            .style('font-weight', '500')
            .style('pointer-events', 'none')
            .style('opacity', 0);
        
        // Animate labels with delay
        labels.transition()
            .delay(this.options.animation.duration)
            .duration(500)
            .style('opacity', 1)
            .text(d => this.formatValue(d.value))
            .style('fill', d => this.getContrastingTextColor(this.colorScale(d.value)));
    }
    
    /**
     * Add cell labels if enabled
     */
    addCellLabels(cells, data) {
        const labels = cells.append('text')
            .attr('class', 'cell-label')
            .attr('x', d => this.xScale(d.x) + this.xScale.bandwidth() / 2)
            .attr('y', d => this.yScale(d.y) + this.yScale.bandwidth() / 2 + 15)
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .style('font-size', `${this.options.fontSize - 2}px`)
            .style('pointer-events', 'none')
            .style('opacity', 0);
        
        // Animate labels
        labels.transition()
            .delay(this.options.animation.duration + 200)
            .duration(300)
            .style('opacity', 0.8)
            .text(d => d.label || '')
            .style('fill', d => this.getContrastingTextColor(this.colorScale(d.value)));
    }
    
    /**
     * Draw color legend
     */
    drawLegend() {
        const legendWidth = this.options.legend.width;
        const legendHeight = this.options.legend.height;
        const legendX = this.dimensions.chart.width + 20;
        const legendY = (this.dimensions.chart.height - legendHeight) / 2;
        
        const legendGroup = this.chartGroup.append('g')
            .attr('class', 'heatmap-legend')
            .attr('transform', `translate(${legendX}, ${legendY})`);
        
        // Create gradient for legend
        const gradientId = `heatmap-gradient-${this.containerId}`;
        const defs = this.svg.select('defs').empty() ? this.svg.append('defs') : this.svg.select('defs');
        
        const gradient = defs.append('linearGradient')
            .attr('id', gradientId)
            .attr('gradientUnits', 'userSpaceOnUse')
            .attr('x1', 0).attr('y1', legendHeight)
            .attr('x2', 0).attr('y2', 0);
        
        // Add gradient stops
        const stops = 10;
        for (let i = 0; i <= stops; i++) {
            const t = i / stops;
            const value = this.colorScale.domain()[0] + t * (this.colorScale.domain()[1] - this.colorScale.domain()[0]);
            
            gradient.append('stop')
                .attr('offset', `${t * 100}%`)
                .attr('stop-color', this.colorScale(value));
        }
        
        // Draw legend rectangle
        legendGroup.append('rect')
            .attr('width', legendWidth)
            .attr('height', legendHeight)
            .attr('fill', `url(#${gradientId})`)
            .attr('stroke', this.getThemeProperties().grid)
            .attr('stroke-width', 1);
        
        // Add legend scale
        const legendScale = d3.scaleLinear()
            .domain(this.colorScale.domain())
            .range([legendHeight, 0]);
        
        const legendAxis = d3.axisRight(legendScale)
            .tickSize(6)
            .tickFormat(d => this.formatValue(d));
        
        legendGroup.append('g')
            .attr('class', 'legend-axis')
            .attr('transform', `translate(${legendWidth}, 0)`)
            .call(legendAxis)
            .style('font-size', '10px');
        
        // Add legend title
        legendGroup.append('text')
            .attr('x', legendWidth / 2)
            .attr('y', -10)
            .attr('text-anchor', 'middle')
            .style('font-size', '11px')
            .style('font-weight', 'bold')
            .text('Value');
    }
    
    /**
     * Add interactivity
     */
    addInteractivity() {
        const cells = this.chartGroup.selectAll('.heatmap-cell');
        
        cells.on('mouseover', (event, d) => {
            // Highlight cell
            d3.select(event.currentTarget).select('.cell-rect')
                .transition()
                .duration(200)
                .attr('stroke', this.getThemeProperties().accent)
                .attr('stroke-width', 2);
            
            if (this.options.tooltip.enabled) {
                this.showTooltip(event, d);
            }
        })
        .on('mouseout', (event, d) => {
            // Remove highlight
            d3.select(event.currentTarget).select('.cell-rect')
                .transition()
                .duration(200)
                .attr('stroke', 'none')
                .attr('stroke-width', 0);
            
            this.hideTooltip();
        })
        .on('click', (event, d) => {
            this.handleCellClick(event, d);
        });
        
        // Add keyboard navigation
        cells.attr('tabindex', 0)
            .on('keydown', (event, d) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    this.handleCellClick(event, d);
                }
            });
    }
    
    /**
     * Show tooltip
     */
    showTooltip(event, d) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'heatmap-tooltip')
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
        
        if (this.options.tooltip.showCoordinates) {
            content += `<strong>${d.x}, ${d.y}</strong><br>`;
        }
        
        if (this.options.tooltip.showValue) {
            content += `Value: ${this.formatValue(d.value)}`;
        }
        
        if (d.label) {
            content += `<br>Label: ${d.label}`;
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
        d3.selectAll('.heatmap-tooltip').remove();
    }
    
    /**
     * Handle cell click
     */
    handleCellClick(event, d) {
        const clickEvent = new CustomEvent('heatmapCellClick', {
            detail: { data: d, chart: this }
        });
        
        document.dispatchEvent(clickEvent);
        
        if (this.options.onCellClick) {
            this.options.onCellClick(d, this);
        }
    }
    
    /**
     * Process data for heatmap
     */
    processData() {
        if (!this.data || !Array.isArray(this.data)) {
            return { data: [], xValues: [], yValues: [], values: [] };
        }
        
        const processedData = this.data.map(item => {
            if (typeof item === 'object' && item.x !== undefined && item.y !== undefined) {
                return {
                    x: String(item.x),
                    y: String(item.y),
                    value: Number(item.value || item.z || 0),
                    label: item.label
                };
            }
            return null;
        }).filter(d => d !== null);
        
        // Get unique x and y values
        const xValues = [...new Set(processedData.map(d => d.x))].sort();
        const yValues = [...new Set(processedData.map(d => d.y))].sort();
        const values = processedData.map(d => d.value);
        
        return {
            data: processedData,
            xValues,
            yValues,
            values
        };
    }
    
    /**
     * Format value for display
     */
    formatValue(value) {
        if (typeof value === 'number') {
            if (value >= 1000000) {
                return (value / 1000000).toFixed(1) + 'M';
            } else if (value >= 1000) {
                return (value / 1000).toFixed(1) + 'K';
            } else if (value % 1 === 0) {
                return value.toString();
            } else {
                return value.toFixed(2);
            }
        }
        
        return value?.toString() || '0';
    }
    
    /**
     * Get contrasting text color for background
     */
    getContrastingTextColor(backgroundColor) {
        const color = d3.color(backgroundColor);
        if (!color) return '#000000';
        
        const luminance = (0.299 * color.r + 0.587 * color.g + 0.114 * color.b) / 255;
        return luminance > 0.5 ? '#000000' : '#ffffff';
    }
    
    /**
     * Get theme properties
     */
    getThemeProperties() {
        return ChartThemes.getThemeProperties(this.options.theme);
    }
    
    /**
     * Update color scale
     */
    updateColorScale(colorScale) {
        this.options.colorScale = colorScale;
        this.render();
    }
    
    /**
     * Export chart data
     */
    exportData(format = 'json') {
        const { data } = this.processedData;
        
        switch (format) {
            case 'csv':
                const csvHeader = 'x,y,value,label\n';
                const csvRows = data.map(d => 
                    `"${d.x}","${d.y}",${d.value},"${d.label || ''}"`
                ).join('\n');
                return csvHeader + csvRows;
            
            case 'json':
            default:
                return JSON.stringify(data, null, 2);
        }
    }
}

// Register with ChartFactory
if (typeof chartRegistry !== 'undefined') {
    chartRegistry.register('heatmap', HeatmapChart);
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HeatmapChart;
} else {
    window.HeatmapChart = HeatmapChart;
}