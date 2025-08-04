/**
 * StatisticsChart - Advanced statistics visualization component
 * Modernized from legacy statistics.js with full BaseChart integration
 */
class StatisticsChart extends BaseChart {
    constructor(containerId, options = {}) {
        super(containerId, {
            // Default statistics chart options
            type: 'mixed', // 'table', 'chart', 'mixed'
            chartType: 'pie', // 'pie', 'bar', 'donut'
            showTable: true,
            showChart: true,
            maxTableRows: 20,
            showPercentages: true,
            showProgressBars: true,
            tableClasses: 'table table-striped table-hover',
            headerClasses: 'table-dark',
            ...options
        });
        
        this.processedData = null;
        this.tableContainer = null;
        this.chartContainer = null;
    }
    
    /**
     * Render the statistics chart/table
     */
    render() {
        if (!this.data || this.data.length === 0) {
            this.showEmpty('No statistics data available');
            return;
        }
        
        this.processedData = this.processData();
        this.updateDimensions();
        this.createContainers();
        
        if (this.options.showTable) {
            this.renderTable();
        }
        
        if (this.options.showChart) {
            this.renderChart();
        }
        
        if (this.options.title) {
            this.addTitle(this.options.title);
        }
    }
    
    /**
     * Create containers for table and chart
     */
    createContainers() {
        this.container.html('');
        
        // Create title container
        if (this.options.title) {
            this.container.append(`
                <div class="statistics-title mb-3">
                    <h5 class="mb-0">${this.options.title}</h5>
                </div>
            `);
        }
        
        // Create main container
        const mainContainer = this.container.append('div')
            .attr('class', 'statistics-main-container');
        
        if (this.options.type === 'mixed') {
            // Split layout for mixed type
            const row = mainContainer.append('div').attr('class', 'row');
            
            if (this.options.showChart) {
                this.chartContainer = row.append('div')
                    .attr('class', 'col-md-6')
                    .append('div')
                    .attr('class', 'statistics-chart-container');
            }
            
            if (this.options.showTable) {
                this.tableContainer = row.append('div')
                    .attr('class', this.options.showChart ? 'col-md-6' : 'col-12')
                    .append('div')
                    .attr('class', 'statistics-table-container');
            }
        } else {
            // Single layout
            if (this.options.showChart) {
                this.chartContainer = mainContainer.append('div')
                    .attr('class', 'statistics-chart-container mb-3');
            }
            
            if (this.options.showTable) {
                this.tableContainer = mainContainer.append('div')
                    .attr('class', 'statistics-table-container');
            }
        }
    }
    
    /**
     * Render statistics table
     */
    renderTable() {
        if (!this.tableContainer) return;
        
        const data = this.processedData.tableData;
        const total = this.processedData.total;
        
        // Create table structure
        let tableHtml = `
            <div class="table-responsive">
                <table class="${this.options.tableClasses}">
                    <thead class="${this.options.headerClasses}">
                        <tr>
                            ${this.getTableHeaders()}
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        // Add table rows
        const displayData = data.slice(0, this.options.maxTableRows);
        displayData.forEach((item, index) => {
            tableHtml += this.createTableRow(item, total, index);
        });
        
        tableHtml += `
                    </tbody>
                </table>
            </div>
        `;
        
        // Add summary info
        if (data.length > this.options.maxTableRows) {
            tableHtml += `
                <p class="text-muted mt-2">
                    <i class="fas fa-info-circle me-1"></i>
                    Showing top ${this.options.maxTableRows} of ${data.length} items
                </p>
            `;
        }
        
        this.tableContainer.html(tableHtml);
        
        // Add interactivity
        this.addTableInteractivity();
    }
    
    /**
     * Get table headers based on data type
     */
    getTableHeaders() {
        const dataType = this.processedData.type;
        
        switch (dataType) {
            case 'device':
                return `
                    <th><i class="fas fa-microchip me-1"></i>Device ID</th>
                    <th><i class="fas fa-counter me-1"></i>Access Count</th>
                    <th><i class="fas fa-folder me-1"></i>Unique Paths</th>
                    <th><i class="fas fa-list me-1"></i>Sample Paths</th>
                `;
            
            case 'event':
                return `
                    <th><i class="fas fa-bolt me-1"></i>Event Type</th>
                    <th><i class="fas fa-counter me-1"></i>Count</th>
                    <th><i class="fas fa-chart-pie me-1"></i>Percentage</th>
                `;
            
            default:
                return `
                    <th>Item</th>
                    <th>Value</th>
                    <th>Percentage</th>
                `;
        }
    }
    
    /**
     * Create table row based on data type
     */
    createTableRow(item, total, index) {
        const dataType = this.processedData.type;
        
        switch (dataType) {
            case 'device':
                return this.createDeviceTableRow(item, index);
            
            case 'event':
                return this.createEventTableRow(item, total, index);
            
            default:
                return this.createGenericTableRow(item, total, index);
        }
    }
    
    /**
     * Create device statistics table row
     */
    createDeviceTableRow(device, index) {
        const samplePaths = device.paths.slice(0, 3).join(', ');
        const morePathsText = device.paths.length > 3 ? ` (+${device.paths.length - 3} more)` : '';
        
        return `
            <tr data-index="${index}" class="statistics-row">
                <td>
                    <code class="device-id">${device.device}</code>
                </td>
                <td>
                    <span class="badge bg-primary">${device.count.toLocaleString()}</span>
                </td>
                <td>
                    <span class="badge bg-secondary">${device.path_count}</span>
                </td>
                <td class="text-truncate" style="max-width: 300px;" title="${device.paths.join(', ')}">
                    <small class="text-muted">${samplePaths}${morePathsText}</small>
                </td>
            </tr>
        `;
    }
    
    /**
     * Create event statistics table row
     */
    createEventTableRow(event, total, index) {
        const percentage = ((event.count / total) * 100).toFixed(2);
        
        let progressBar = '';
        if (this.options.showProgressBars) {
            progressBar = `
                <div class="progress me-2" style="width: 100px; height: 20px;">
                    <div class="progress-bar bg-info" role="progressbar" 
                         style="width: ${percentage}%" 
                         aria-valuenow="${percentage}" 
                         aria-valuemin="0" 
                         aria-valuemax="100">
                    </div>
                </div>
            `;
        }
        
        return `
            <tr data-index="${index}" class="statistics-row">
                <td>
                    <code class="event-type">${event.event}</code>
                </td>
                <td>
                    <span class="badge bg-primary">${event.count.toLocaleString()}</span>
                </td>
                <td class="d-flex align-items-center">
                    ${progressBar}
                    <small class="text-muted">${percentage}%</small>
                </td>
            </tr>
        `;
    }
    
    /**
     * Create generic table row
     */
    createGenericTableRow(item, total, index) {
        const percentage = total > 0 ? ((item.value / total) * 100).toFixed(2) : '0';
        
        return `
            <tr data-index="${index}" class="statistics-row">
                <td>${item.label}</td>
                <td><span class="badge bg-primary">${item.value.toLocaleString()}</span></td>
                <td><small class="text-muted">${percentage}%</small></td>
            </tr>
        `;
    }
    
    /**
     * Add table interactivity
     */
    addTableInteractivity() {
        const rows = this.tableContainer.selectAll('.statistics-row');
        
        rows.on('mouseover', function() {
            d3.select(this).classed('table-active', true);
        })
        .on('mouseout', function() {
            d3.select(this).classed('table-active', false);
        })
        .on('click', (event, d) => {
            const index = parseInt(event.currentTarget.getAttribute('data-index'));
            const item = this.processedData.tableData[index];
            this.handleRowClick(item, index);
        });
    }
    
    /**
     * Render statistics chart
     */
    renderChart() {
        if (!this.chartContainer) return;
        
        const chartData = this.processedData.chartData;
        
        // Create chart based on type
        switch (this.options.chartType) {
            case 'pie':
                this.renderPieChart(chartData);
                break;
            
            case 'donut':
                this.renderDonutChart(chartData);
                break;
            
            case 'bar':
                this.renderBarChart(chartData);
                break;
            
            default:
                this.renderPieChart(chartData);
        }
    }
    
    /**
     * Render pie chart
     */
    renderPieChart(data) {
        // Use the new PieChart component
        const chartId = `${this.containerId}-pie-chart`;
        this.chartContainer.html(`<div id="${chartId}" style="height: 400px;"></div>`);
        
        const pieChart = new PieChart(chartId, {
            title: this.options.chartTitle || 'Distribution',
            showLegend: true,
            showLabels: true,
            showPercentages: true,
            theme: this.options.theme
        });
        
        pieChart.setData(data);
    }
    
    /**
     * Render donut chart
     */
    renderDonutChart(data) {
        const chartId = `${this.containerId}-donut-chart`;
        this.chartContainer.html(`<div id="${chartId}" style="height: 400px;"></div>`);
        
        const donutChart = new PieChart(chartId, {
            title: this.options.chartTitle || 'Distribution',
            donutMode: true,
            innerRadius: 80,
            showLegend: true,
            showLabels: false,
            showPercentages: true,
            theme: this.options.theme
        });
        
        donutChart.setData(data);
    }
    
    /**
     * Render bar chart
     */
    renderBarChart(data) {
        const chartId = `${this.containerId}-bar-chart`;
        this.chartContainer.html(`<div id="${chartId}" style="height: 400px;"></div>`);
        
        const barChart = new BarChart(chartId, {
            title: this.options.chartTitle || 'Distribution',
            orientation: 'vertical',
            showValues: true,
            showGrid: true,
            xAxis: { label: 'Items' },
            yAxis: { label: 'Count' },
            theme: this.options.theme
        });
        
        barChart.setData(data);
    }
    
    /**
     * Handle table row click
     */
    handleRowClick(item, index) {
        const clickEvent = new CustomEvent('statisticsRowClick', {
            detail: { item, index, chart: this }
        });
        
        document.dispatchEvent(clickEvent);
        
        if (this.options.onRowClick) {
            this.options.onRowClick(item, index, this);
        }
    }
    
    /**
     * Process data for statistics display
     */
    processData() {
        if (!this.data) return null;
        
        // Detect data type
        const dataType = this.detectDataType();
        
        let tableData = [];
        let chartData = [];
        let total = 0;
        
        if (Array.isArray(this.data)) {
            tableData = [...this.data];
            
            // Convert to chart format
            chartData = this.data.map(item => {
                if (dataType === 'device') {
                    return {
                        label: item.device || item.name || 'Unknown',
                        value: item.count || item.value || 0
                    };
                } else if (dataType === 'event') {
                    return {
                        label: item.event || item.name || 'Unknown',
                        value: item.count || item.value || 0
                    };
                } else {
                    return {
                        label: item.label || item.name || 'Unknown',
                        value: item.value || item.count || 0
                    };
                }
            });
            
            total = chartData.reduce((sum, item) => sum + item.value, 0);
        }
        
        return {
            type: dataType,
            tableData,
            chartData,
            total
        };
    }
    
    /**
     * Detect data type based on structure
     */
    detectDataType() {
        if (!Array.isArray(this.data) || this.data.length === 0) {
            return 'generic';
        }
        
        const firstItem = this.data[0];
        
        if (firstItem.device && firstItem.paths) {
            return 'device';
        } else if (firstItem.event && firstItem.count) {
            return 'event';
        }
        
        return 'generic';
    }
    
    /**
     * Update chart type
     */
    setChartType(type) {
        this.options.chartType = type;
        if (this.options.showChart) {
            this.renderChart();
        }
    }
    
    /**
     * Toggle table visibility
     */
    toggleTable() {
        this.options.showTable = !this.options.showTable;
        this.render();
    }
    
    /**
     * Toggle chart visibility
     */
    toggleChart() {
        this.options.showChart = !this.options.showChart;
        this.render();
    }
    
    /**
     * Export statistics data
     */
    exportData(format = 'json') {
        if (!this.processedData) return null;
        
        switch (format) {
            case 'csv':
                const csvHeader = this.processedData.type === 'device' ?
                    'device,count,path_count,paths\n' :
                    'item,count,percentage\n';
                
                const csvRows = this.processedData.tableData.map(item => {
                    if (this.processedData.type === 'device') {
                        return `"${item.device}",${item.count},${item.path_count},"${item.paths.join(';')}"`;
                    } else {
                        const percentage = ((item.count / this.processedData.total) * 100).toFixed(2);
                        return `"${item.event || item.label}",${item.count},${percentage}`;
                    }
                }).join('\n');
                
                return csvHeader + csvRows;
            
            case 'json':
            default:
                return JSON.stringify(this.processedData, null, 2);
        }
    }
}

// Register with ChartFactory
if (typeof chartRegistry !== 'undefined') {
    chartRegistry.register('statistics', StatisticsChart);
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StatisticsChart;
} else {
    window.StatisticsChart = StatisticsChart;
}