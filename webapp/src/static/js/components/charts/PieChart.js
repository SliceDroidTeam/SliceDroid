/**
 * PieChart - Specialized pie chart component extending BaseChart
 */
class PieChart extends BaseChart {
    constructor(containerId, options = {}) {
        super(containerId, {
            // Default pie chart options
            innerRadius: 0,
            outerRadius: null,
            padAngle: 0.02,
            cornerRadius: 3,
            showLabels: true,
            showPercentages: true,
            showLegend: true,
            legendPosition: 'right',
            donutMode: false,
            sortData: true,
            minSliceAngle: 0.01, // Minimum angle for small slices
            tooltip: {
                enabled: true,
                showValue: true,
                showPercentage: true
            },
            ...options
        });
        
        this.pie = null;
        this.arc = null;
        this.labelArc = null;
    }
    
    /**
     * Render the pie chart
     */
    render() {
        if (!this.data || this.data.length === 0) {
            this.showEmpty('No data available for pie chart');
            return;
        }
        
        this.updateDimensions();
        this.createSVG();
        this.setupPieComponents();
        this.drawChart();
        this.addInteractivity();
        
        if (this.options.title) {
            this.addTitle(this.options.title);
        }
        
        if (this.options.showLegend) {
            this.addLegend(this.getLegendData(), this.options.legendPosition);
        }
    }
    
    /**
     * Setup pie chart components (pie generator, arcs, etc.)
     */
    setupPieComponents() {
        const radius = Math.min(this.dimensions.chart.width, this.dimensions.chart.height) / 2 - 10;
        
        // Calculate radii
        const outerRadius = this.options.outerRadius || radius;
        const innerRadius = this.options.donutMode ? 
            (this.options.innerRadius || outerRadius * 0.4) : 
            (this.options.innerRadius || 0);
        
        // Pie generator
        this.pie = d3.pie()
            .value(d => d.value)
            .padAngle(this.options.padAngle)
            .sortValues(this.options.sortData ? d3.descending : null);
        
        // Arc generators
        this.arc = d3.arc()
            .innerRadius(innerRadius)
            .outerRadius(outerRadius)
            .cornerRadius(this.options.cornerRadius);
        
        this.labelArc = d3.arc()
            .innerRadius(outerRadius + 10)
            .outerRadius(outerRadius + 10);
        
        // Position chart group at center
        this.chartGroup.attr('transform', 
            `translate(${this.dimensions.chart.width / 2}, ${this.dimensions.chart.height / 2})`);
    }
    
    /**
     * Draw the pie chart
     */
    drawChart() {
        const pieData = this.pie(this.processData());
        
        // Create slice groups
        const slices = this.chartGroup.selectAll('.pie-slice')
            .data(pieData)
            .enter()
            .append('g')
            .attr('class', 'pie-slice');
        
        // Draw arcs
        const paths = slices.append('path')
            .attr('class', 'pie-arc')
            .attr('fill', (d, i) => this.getColor(i, 'primary'))
            .attr('stroke', this.getThemeProperties().background)
            .attr('stroke-width', 2);
        
        // Animate arc drawing
        paths.attr('d', this.arc.startAngle(0).endAngle(0))
            .transition()
            .duration(this.options.animation.duration)
            .attrTween('d', (d) => {
                const interpolate = d3.interpolate({ startAngle: 0, endAngle: 0 }, d);
                return (t) => this.arc(interpolate(t));
            });
        
        // Add labels if enabled
        if (this.options.showLabels) {
            this.addLabels(slices, pieData);
        }
    }
    
    /**
     * Add labels to pie slices
     */
    addLabels(slices, pieData) {
        const labels = slices.append('text')
            .attr('class', 'pie-label')
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .style('font-size', '12px')
            .style('font-weight', '500')
            .style('fill', this.getThemeProperties().text)
            .style('pointer-events', 'none');
        
        // Position and show labels with animation
        labels.transition()
            .delay(this.options.animation.duration)
            .duration(500)
            .attr('transform', d => {
                // Only show labels for slices larger than minimum angle
                if (d.endAngle - d.startAngle < this.options.minSliceAngle) {
                    return 'translate(0,0) scale(0)';
                }
                return `translate(${this.labelArc.centroid(d)})`;
            })
            .text(d => {
                if (d.endAngle - d.startAngle < this.options.minSliceAngle) return '';
                
                let label = d.data.label || d.data.name || '';
                if (this.options.showPercentages) {
                    const percentage = ((d.endAngle - d.startAngle) / (2 * Math.PI) * 100).toFixed(1);
                    label += ` (${percentage}%)`;
                }
                return label;
            })
            .style('opacity', 1);
    }
    
    /**
     * Add interactivity (hover effects, tooltips)
     */
    addInteractivity() {
        const slices = this.chartGroup.selectAll('.pie-slice');
        
        slices.on('mouseover', (event, d) => {
            // Highlight slice
            d3.select(event.currentTarget).select('.pie-arc')
                .transition()
                .duration(200)
                .attr('transform', 'scale(1.05)');
            
            // Show tooltip
            if (this.options.tooltip.enabled) {
                this.showTooltip(event, d);
            }
        })
        .on('mouseout', (event, d) => {
            // Remove highlight
            d3.select(event.currentTarget).select('.pie-arc')
                .transition()
                .duration(200)
                .attr('transform', 'scale(1)');
            
            // Hide tooltip
            this.hideTooltip();
        })
        .on('click', (event, d) => {
            this.handleSliceClick(event, d);
        });
        
        // Add keyboard navigation
        slices.attr('tabindex', 0)
            .on('keydown', (event, d) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    this.handleSliceClick(event, d);
                }
            });
    }
    
    /**
     * Show tooltip for pie slice
     */
    showTooltip(event, d) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'pie-chart-tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(0,0,0,0.8)')
            .style('color', 'white')
            .style('padding', '8px 12px')
            .style('border-radius', '4px')
            .style('pointer-events', 'none')
            .style('z-index', 1000)
            .style('font-size', '12px')
            .style('opacity', 0);
        
        let content = `<strong>${d.data.label || d.data.name}</strong><br>`;
        
        if (this.options.tooltip.showValue) {
            content += `Value: ${d.data.value}<br>`;
        }
        
        if (this.options.tooltip.showPercentage) {
            const percentage = ((d.endAngle - d.startAngle) / (2 * Math.PI) * 100).toFixed(1);
            content += `Percentage: ${percentage}%`;
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
        d3.selectAll('.pie-chart-tooltip').remove();
    }
    
    /**
     * Handle slice click
     */
    handleSliceClick(event, d) {
        // Emit custom event
        const clickEvent = new CustomEvent('pieSliceClick', {
            detail: {
                data: d.data,
                slice: d,
                chart: this
            }
        });
        
        document.dispatchEvent(clickEvent);
        
        // Call callback if provided
        if (this.options.onSliceClick) {
            this.options.onSliceClick(d.data, d, this);
        }
    }
    
    /**
     * Process raw data for pie chart
     */
    processData() {
        if (!this.data) return [];
        
        // Handle different data formats
        let processedData = [];
        
        if (Array.isArray(this.data)) {
            processedData = this.data.map(item => {
                if (typeof item === 'object' && item.value !== undefined) {
                    return item;
                } else if (typeof item === 'object') {
                    // Try to extract value from common property names
                    const value = item.count || item.size || item.amount || item.y || 0;
                    const label = item.label || item.name || item.key || item.x || 'Unknown';
                    return { label, value };
                }
                return { label: 'Item', value: item };
            });
        } else if (typeof this.data === 'object') {
            // Convert object to array
            processedData = Object.entries(this.data).map(([key, value]) => ({
                label: key,
                value: typeof value === 'object' ? (value.value || 0) : value
            }));
        }
        
        // Filter out zero/negative values
        processedData = processedData.filter(d => d.value > 0);
        
        // Sort if enabled
        if (this.options.sortData) {
            processedData.sort((a, b) => b.value - a.value);
        }
        
        return processedData;
    }
    
    /**
     * Get legend data
     */
    getLegendData() {
        const processedData = this.processData();
        return processedData.map((item, index) => ({
            label: item.label,
            color: this.getColor(index, 'primary')
        }));
    }
    
    /**
     * Get theme properties
     */
    getThemeProperties() {
        return ChartThemes.getThemeProperties(this.options.theme);
    }
    
    /**
     * Update chart with new data
     */
    setData(data) {
        super.setData(data);
    }
    
    /**
     * Convert to donut chart
     */
    convertToDonut(innerRadius = null) {
        this.options.donutMode = true;
        this.options.innerRadius = innerRadius;
        this.render();
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
    chartRegistry.register('pie', PieChart);
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PieChart;
} else {
    window.PieChart = PieChart;
}