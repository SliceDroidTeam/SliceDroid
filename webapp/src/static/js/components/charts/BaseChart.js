/**
 * BaseChart - Foundation class for all chart components
 * Provides common functionality, responsive design, and consistent API
 */
class BaseChart {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = d3.select(`#${containerId}`);
        this.options = {
            margin: { top: 20, right: 20, bottom: 50, left: 50 },
            width: 800,
            height: 400,
            responsive: true,
            theme: 'default',
            animation: {
                duration: 750,
                easing: 'cubic-in-out'
            },
            accessibility: {
                enabled: true,
                announceChanges: true
            },
            ...options
        };
        
        this.data = null;
        this.svg = null;
        this.dimensions = null;
        
        this.init();
    }
    
    /**
     * Initialize the chart
     */
    init() {
        if (!this.validateContainer()) return;
        
        this.setupResponsive();
        this.setupAccessibility();
        this.render();
    }
    
    /**
     * Validate container exists and is accessible
     */
    validateContainer() {
        const element = document.getElementById(this.containerId);
        if (!element) {
            console.error(`Chart container '${this.containerId}' not found`);
            return false;
        }
        
        if (this.container.empty()) {
            console.error(`Chart container '${this.containerId}' is not accessible via D3`);
            return false;
        }
        
        return true;
    }
    
    /**
     * Setup responsive behavior
     */
    setupResponsive() {
        if (!this.options.responsive) return;
        
        // Calculate responsive dimensions
        this.updateDimensions();
        
        // Setup resize listener
        if (window.ResizeObserver) {
            this.resizeObserver = new ResizeObserver(entries => {
                for (let entry of entries) {
                    if (entry.target.id === this.containerId) {
                        this.handleResize();
                    }
                }
            });
            
            const element = document.getElementById(this.containerId);
            if (element) {
                this.resizeObserver.observe(element);
            }
        } else {
            // Fallback for older browsers
            window.addEventListener('resize', () => this.handleResize());
        }
    }
    
    /**
     * Setup accessibility features
     */
    setupAccessibility() {
        if (!this.options.accessibility.enabled) return;
        
        const element = document.getElementById(this.containerId);
        if (element) {
            element.setAttribute('role', 'img');
            element.setAttribute('aria-label', this.options.title || 'Chart');
            
            // Add keyboard navigation support
            element.setAttribute('tabindex', '0');
            element.addEventListener('keydown', (e) => this.handleKeyboard(e));
        }
    }
    
    /**
     * Update chart dimensions based on container
     */
    updateDimensions() {
        const element = document.getElementById(this.containerId);
        if (!element) return;
        
        const rect = element.getBoundingClientRect();
        const containerWidth = rect.width || this.options.width;
        const containerHeight = rect.height || this.options.height;
        
        this.dimensions = {
            total: {
                width: containerWidth,
                height: containerHeight
            },
            chart: {
                width: containerWidth - this.options.margin.left - this.options.margin.right,
                height: containerHeight - this.options.margin.top - this.options.margin.bottom
            },
            margin: this.options.margin
        };
    }
    
    /**
     * Handle window/container resize
     */
    handleResize() {
        this.updateDimensions();
        this.render();
    }
    
    /**
     * Handle keyboard navigation
     */
    handleKeyboard(event) {
        switch(event.key) {
            case 'Enter':
            case ' ':
                event.preventDefault();
                this.handleInteraction();
                break;
            case 'ArrowLeft':
                event.preventDefault();
                this.navigateLeft();
                break;
            case 'ArrowRight':
                event.preventDefault();
                this.navigateRight();
                break;
        }
    }
    
    /**
     * Show loading state
     */
    showLoading(message = 'Loading...') {
        this.container.html(`
            <div class="chart-loading d-flex flex-column align-items-center justify-content-center h-100 p-4">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="text-muted">${message}</div>
            </div>
        `);
    }
    
    /**
     * Show error state
     */
    showError(message = 'Failed to load chart') {
        this.container.html(`
            <div class="chart-error alert alert-danger d-flex align-items-center" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <div>${message}</div>
            </div>
        `);
    }
    
    /**
     * Show empty state
     */
    showEmpty(message = 'No data available') {
        this.container.html(`
            <div class="chart-empty alert alert-info d-flex align-items-center" role="alert">
                <i class="fas fa-info-circle me-2"></i>
                <div>${message}</div>
            </div>
        `);
    }
    
    /**
     * Create SVG element with responsive dimensions
     */
    createSVG() {
        this.container.selectAll('*').remove();
        
        this.svg = this.container
            .append('svg')
            .attr('width', this.dimensions.total.width)
            .attr('height', this.dimensions.total.height)
            .attr('viewBox', `0 0 ${this.dimensions.total.width} ${this.dimensions.total.height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet')
            .classed('chart-svg', true);
            
        // Create main chart group
        this.chartGroup = this.svg
            .append('g')
            .attr('transform', `translate(${this.dimensions.margin.left},${this.dimensions.margin.top})`)
            .classed('chart-group', true);
            
        return this.svg;
    }
    
    /**
     * Add chart title
     */
    addTitle(title) {
        if (!title || !this.svg) return;
        
        this.svg.append('text')
            .attr('x', this.dimensions.total.width / 2)
            .attr('y', this.dimensions.margin.top / 2)
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .classed('chart-title', true)
            .style('font-size', '16px')
            .style('font-weight', 'bold')
            .text(title);
    }
    
    /**
     * Add chart legend
     */
    addLegend(items, position = 'bottom') {
        if (!items || !this.svg) return;
        
        const legendGroup = this.svg.append('g')
            .classed('chart-legend', true);
            
        const itemWidth = 120;
        const itemHeight = 20;
        const itemsPerRow = Math.floor(this.dimensions.chart.width / itemWidth);
        
        items.forEach((item, i) => {
            const row = Math.floor(i / itemsPerRow);
            const col = i % itemsPerRow;
            
            const x = col * itemWidth;
            const y = row * itemHeight;
            
            const legendItem = legendGroup.append('g')
                .attr('transform', `translate(${x}, ${y})`)
                .classed('legend-item', true);
                
            legendItem.append('rect')
                .attr('width', 12)
                .attr('height', 12)
                .attr('fill', item.color);
                
            legendItem.append('text')
                .attr('x', 18)
                .attr('y', 6)
                .attr('dominant-baseline', 'middle')
                .style('font-size', '12px')
                .text(item.label);
        });
        
        // Position legend
        const legendHeight = Math.ceil(items.length / itemsPerRow) * itemHeight;
        let legendY;
        
        switch(position) {
            case 'top':
                legendY = 5;
                break;
            case 'bottom':
            default:
                legendY = this.dimensions.total.height - legendHeight - 5;
                break;
        }
        
        legendGroup.attr('transform', `translate(${this.dimensions.margin.left}, ${legendY})`);
    }
    
    /**
     * Set chart data
     */
    setData(data) {
        this.data = data;
        this.render();
        
        if (this.options.accessibility.announceChanges) {
            this.announceDataChange();
        }
    }
    
    /**
     * Announce data changes to screen readers
     */
    announceDataChange() {
        const message = `Chart data updated with ${Array.isArray(this.data) ? this.data.length : 'new'} items`;
        
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        setTimeout(() => document.body.removeChild(announcement), 1000);
    }
    
    /**
     * Get color for data point
     */
    getColor(index, category = 'default') {
        const scheme = ChartThemes.getColorScheme(this.options.theme, category);
        return scheme[index % scheme.length];
    }
    
    /**
     * Animate element
     */
    animate(selection, properties, duration = null) {
        const animationDuration = duration || this.options.animation.duration;
        
        return selection
            .transition()
            .duration(animationDuration)
            .ease(d3.easeCubicInOut);
    }
    
    /**
     * Export chart as image
     */
    exportAsImage(format = 'png') {
        if (!this.svg) return;
        
        const svgNode = this.svg.node();
        const serializer = new XMLSerializer();
        const svgString = serializer.serializeToString(svgNode);
        
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        const img = new Image();
        
        return new Promise((resolve, reject) => {
            img.onload = () => {
                canvas.width = this.dimensions.total.width;
                canvas.height = this.dimensions.total.height;
                context.drawImage(img, 0, 0);
                
                canvas.toBlob(resolve, `image/${format}`);
            };
            
            img.onerror = reject;
            img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgString)));
        });
    }
    
    /**
     * Cleanup and destroy chart
     */
    destroy() {
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        
        this.container.selectAll('*').remove();
        
        // Remove event listeners
        const element = document.getElementById(this.containerId);
        if (element) {
            element.removeAttribute('tabindex');
            element.removeEventListener('keydown', this.handleKeyboard);
        }
    }
    
    // Abstract methods to be implemented by subclasses
    render() {
        throw new Error('render() method must be implemented by subclass');
    }
    
    handleInteraction() {
        // Default empty implementation
    }
    
    navigateLeft() {
        // Default empty implementation
    }
    
    navigateRight() {
        // Default empty implementation
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BaseChart;
} else {
    window.BaseChart = BaseChart;
}