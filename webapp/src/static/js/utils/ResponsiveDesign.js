/**
 * ResponsiveDesign - Responsive design system for charts and UI components
 */
class ResponsiveDesign {
    constructor() {
        this.breakpoints = {
            xs: 0,
            sm: 576,
            md: 768,
            lg: 992,
            xl: 1200,
            xxl: 1400
        };
        
        this.currentBreakpoint = this.getCurrentBreakpoint();
        this.observers = new Map();
        this.callbacks = [];
        
        this.init();
    }
    
    /**
     * Initialize responsive design system
     */
    init() {
        this.setupMediaQueries();
        this.setupResizeObserver();
        this.setupIntersectionObserver();
        this.updateCSSVariables();
        
        console.log('Responsive design system initialized');
    }
    
    /**
     * Setup media query listeners
     */
    setupMediaQueries() {
        Object.entries(this.breakpoints).forEach(([name, width]) => {
            if (width > 0) {
                const mediaQuery = window.matchMedia(`(min-width: ${width}px)`);
                
                mediaQuery.addEventListener('change', (e) => {
                    this.handleBreakpointChange();
                });
            }
        });
        
        // Listen for orientation changes
        if (screen.orientation) {
            screen.orientation.addEventListener('change', () => {
                this.handleOrientationChange();
            });
        } else {
            // Fallback for older browsers
            window.addEventListener('orientationchange', () => {
                this.handleOrientationChange();
            });
        }
    }
    
    /**
     * Setup ResizeObserver for element-level responsiveness
     */
    setupResizeObserver() {
        if (!window.ResizeObserver) return;
        
        this.resizeObserver = new ResizeObserver(entries => {
            entries.forEach(entry => {
                const element = entry.target;
                const { width, height } = entry.contentRect;
                
                // Update element size classes
                this.updateElementSizeClasses(element, width, height);
                
                // Notify element-specific callbacks
                this.notifyElementCallbacks(element, { width, height });
            });
        });
    }
    
    /**
     * Setup IntersectionObserver for lazy loading
     */
    setupIntersectionObserver() {
        if (!window.IntersectionObserver) return;
        
        this.intersectionObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.handleElementVisible(entry.target);
                    } else {
                        this.handleElementHidden(entry.target);
                    }
                });
            },
            {
                rootMargin: '50px',
                threshold: [0, 0.1, 0.5, 1.0]
            }
        );
    }
    
    /**
     * Get current breakpoint
     */
    getCurrentBreakpoint() {
        const width = window.innerWidth;
        
        for (const [name, minWidth] of Object.entries(this.breakpoints).reverse()) {
            if (width >= minWidth) {
                return name;
            }
        }
        
        return 'xs';
    }
    
    /**
     * Handle breakpoint changes
     */
    handleBreakpointChange() {
        const oldBreakpoint = this.currentBreakpoint;
        const newBreakpoint = this.getCurrentBreakpoint();
        
        if (oldBreakpoint !== newBreakpoint) {
            this.currentBreakpoint = newBreakpoint;
            this.updateCSSVariables();
            this.updateBodyClasses();
            this.notifyBreakpointCallbacks(oldBreakpoint, newBreakpoint);
            
            console.log(`Breakpoint changed: ${oldBreakpoint} → ${newBreakpoint}`);
        }
    }
    
    /**
     * Handle orientation changes
     */
    handleOrientationChange() {
        setTimeout(() => {
            this.handleBreakpointChange();
            this.notifyOrientationCallbacks();
        }, 100); // Small delay to ensure dimensions are updated
    }
    
    /**
     * Update CSS custom properties
     */
    updateCSSVariables() {
        const root = document.documentElement;
        
        // Set current breakpoint
        root.style.setProperty('--current-breakpoint', this.currentBreakpoint);
        
        // Set responsive values based on breakpoint
        const responsiveValues = this.getResponsiveValues();
        
        Object.entries(responsiveValues).forEach(([property, value]) => {
            root.style.setProperty(`--${property}`, value);
        });
    }
    
    /**
     * Get responsive values for current breakpoint
     */
    getResponsiveValues() {
        const values = {
            xs: {
                'font-size-base': '14px',
                'chart-margin': '10px',
                'chart-padding': '8px',
                'sidebar-width': '0px',
                'card-padding': '12px',
                'grid-gap': '8px'
            },
            sm: {
                'font-size-base': '14px',
                'chart-margin': '15px',
                'chart-padding': '12px',
                'sidebar-width': '250px',
                'card-padding': '16px',
                'grid-gap': '12px'
            },
            md: {
                'font-size-base': '15px',
                'chart-margin': '20px',
                'chart-padding': '16px',
                'sidebar-width': '280px',
                'card-padding': '20px',
                'grid-gap': '16px'
            },
            lg: {
                'font-size-base': '16px',
                'chart-margin': '24px',
                'chart-padding': '20px',
                'sidebar-width': '320px',
                'card-padding': '24px',
                'grid-gap': '20px'
            },
            xl: {
                'font-size-base': '16px',
                'chart-margin': '30px',
                'chart-padding': '24px',
                'sidebar-width': '350px',
                'card-padding': '28px',
                'grid-gap': '24px'
            },
            xxl: {
                'font-size-base': '17px',
                'chart-margin': '32px',
                'chart-padding': '28px',
                'sidebar-width': '380px',
                'card-padding': '32px',
                'grid-gap': '28px'
            }
        };
        
        return values[this.currentBreakpoint] || values.md;
    }
    
    /**
     * Update body classes
     */
    updateBodyClasses() {
        // Remove old breakpoint classes
        Object.keys(this.breakpoints).forEach(bp => {
            document.body.classList.remove(`bp-${bp}`);
        });
        
        // Add current breakpoint class
        document.body.classList.add(`bp-${this.currentBreakpoint}`);
        
        // Add device type classes
        document.body.classList.remove('is-mobile', 'is-tablet', 'is-desktop');
        
        if (this.isMobile()) {
            document.body.classList.add('is-mobile');
        } else if (this.isTablet()) {
            document.body.classList.add('is-tablet');
        } else {
            document.body.classList.add('is-desktop');
        }
    }
    
    /**
     * Update element size classes
     */
    updateElementSizeClasses(element, width, height) {
        // Remove existing size classes
        element.classList.remove(
            'size-xs', 'size-sm', 'size-md', 'size-lg', 'size-xl',
            'ratio-square', 'ratio-landscape', 'ratio-portrait'
        );
        
        // Add size class based on width
        if (width < 300) {
            element.classList.add('size-xs');
        } else if (width < 500) {
            element.classList.add('size-sm');
        } else if (width < 800) {
            element.classList.add('size-md');
        } else if (width < 1200) {
            element.classList.add('size-lg');
        } else {
            element.classList.add('size-xl');
        }
        
        // Add aspect ratio class
        const aspectRatio = width / height;
        if (Math.abs(aspectRatio - 1) < 0.1) {
            element.classList.add('ratio-square');
        } else if (aspectRatio > 1.2) {
            element.classList.add('ratio-landscape');
        } else if (aspectRatio < 0.8) {
            element.classList.add('ratio-portrait');
        }
    }
    
    /**
     * Handle element becoming visible
     */
    handleElementVisible(element) {
        element.classList.add('is-visible');
        element.classList.remove('is-hidden');
        
        // Trigger lazy loading if needed
        if (element.hasAttribute('data-lazy-load')) {
            this.triggerLazyLoad(element);
        }
        
        // Emit visibility event
        element.dispatchEvent(new CustomEvent('elementVisible', {
            detail: { element }
        }));
    }
    
    /**
     * Handle element becoming hidden
     */
    handleElementHidden(element) {
        element.classList.add('is-hidden');
        element.classList.remove('is-visible');
        
        // Emit visibility event
        element.dispatchEvent(new CustomEvent('elementHidden', {
            detail: { element }
        }));
    }
    
    /**
     * Trigger lazy loading for element
     */
    triggerLazyLoad(element) {
        const lazyType = element.getAttribute('data-lazy-load');
        
        switch (lazyType) {
            case 'chart':
                this.lazyLoadChart(element);
                break;
            case 'image':
                this.lazyLoadImage(element);
                break;
            case 'content':
                this.lazyLoadContent(element);
                break;
        }
    }
    
    /**
     * Lazy load chart
     */
    lazyLoadChart(element) {
        const chartType = element.getAttribute('data-chart-type');
        const dataUrl = element.getAttribute('data-chart-url');
        
        if (chartType && dataUrl) {
            // Load chart data and create chart
            fetch(dataUrl)
                .then(response => response.json())
                .then(data => {
                    if (window.createChart) {
                        window.createChart(element.id, data, { type: chartType });
                    }
                })
                .catch(error => {
                    console.error('Failed to lazy load chart:', error);
                    element.innerHTML = `
                        <div class="alert alert-warning">
                            Failed to load chart data
                        </div>
                    `;
                });
        }
    }
    
    /**
     * Lazy load image
     */
    lazyLoadImage(element) {
        const src = element.getAttribute('data-src');
        if (src) {
            const img = element.querySelector('img') || element;
            img.src = src;
            element.removeAttribute('data-src');
        }
    }
    
    /**
     * Lazy load content
     */
    lazyLoadContent(element) {
        const contentUrl = element.getAttribute('data-content-url');
        if (contentUrl) {
            fetch(contentUrl)
                .then(response => response.text())
                .then(html => {
                    element.innerHTML = html;
                })
                .catch(error => {
                    console.error('Failed to lazy load content:', error);
                });
        }
    }
    
    /**
     * Observe element for responsiveness
     */
    observe(element, callback) {
        if (!element) return;
        
        // Store callback
        if (!this.observers.has(element)) {
            this.observers.set(element, []);
        }
        this.observers.get(element).push(callback);
        
        // Start observing
        if (this.resizeObserver) {
            this.resizeObserver.observe(element);
        }
        
        if (this.intersectionObserver && element.hasAttribute('data-lazy-load')) {
            this.intersectionObserver.observe(element);
        }
    }
    
    /**
     * Stop observing element
     */
    unobserve(element) {
        if (!element) return;
        
        this.observers.delete(element);
        
        if (this.resizeObserver) {
            this.resizeObserver.unobserve(element);
        }
        
        if (this.intersectionObserver) {
            this.intersectionObserver.unobserve(element);
        }
    }
    
    /**
     * Add breakpoint change callback
     */
    onBreakpointChange(callback) {
        this.callbacks.push({
            type: 'breakpoint',
            callback
        });
    }
    
    /**
     * Add orientation change callback
     */
    onOrientationChange(callback) {
        this.callbacks.push({
            type: 'orientation',
            callback
        });
    }
    
    /**
     * Notify breakpoint callbacks
     */
    notifyBreakpointCallbacks(oldBreakpoint, newBreakpoint) {
        this.callbacks
            .filter(cb => cb.type === 'breakpoint')
            .forEach(cb => cb.callback(newBreakpoint, oldBreakpoint));
    }
    
    /**
     * Notify orientation callbacks
     */
    notifyOrientationCallbacks() {
        const orientation = this.getOrientation();
        this.callbacks
            .filter(cb => cb.type === 'orientation')
            .forEach(cb => cb.callback(orientation));
    }
    
    /**
     * Notify element callbacks
     */
    notifyElementCallbacks(element, dimensions) {
        const callbacks = this.observers.get(element) || [];
        callbacks.forEach(callback => callback(dimensions, element));
    }
    
    /**
     * Device type helpers
     */
    isMobile() {
        return ['xs', 'sm'].includes(this.currentBreakpoint);
    }
    
    isTablet() {
        return this.currentBreakpoint === 'md';
    }
    
    isDesktop() {
        return ['lg', 'xl', 'xxl'].includes(this.currentBreakpoint);
    }
    
    /**
     * Get device orientation
     */
    getOrientation() {
        if (screen.orientation) {
            return screen.orientation.angle === 0 || screen.orientation.angle === 180 ? 
                'portrait' : 'landscape';
        }
        
        return window.innerHeight > window.innerWidth ? 'portrait' : 'landscape';
    }
    
    /**
     * Get optimal chart dimensions for container
     */
    getOptimalChartDimensions(container, options = {}) {
        const element = typeof container === 'string' ? 
            document.getElementById(container) : container;
        
        if (!element) {
            return {
                width: 400,
                height: 300
            };
        }
        
        const rect = element.getBoundingClientRect();
        const containerWidth = rect.width || 400;
        const containerHeight = rect.height || 300;
        
        // Apply responsive adjustments
        const responsiveValues = this.getResponsiveValues();
        const margin = parseInt(responsiveValues['chart-margin']) || 20;
        const padding = parseInt(responsiveValues['chart-padding']) || 16;
        
        let width = containerWidth - (margin * 2) - (padding * 2);
        let height = containerHeight - (margin * 2) - (padding * 2);
        
        // Apply minimum dimensions
        width = Math.max(width, options.minWidth || 200);
        height = Math.max(height, options.minHeight || 150);
        
        // Apply aspect ratio if specified
        if (options.aspectRatio) {
            const calculatedHeight = width / options.aspectRatio;
            height = Math.max(calculatedHeight, options.minHeight || 150);
        }
        
        // Adjust for mobile devices
        if (this.isMobile()) {
            width = Math.min(width, window.innerWidth - 40);
            height = Math.min(height, window.innerHeight * 0.4);
        }
        
        return { width, height };
    }
    
    /**
     * Calculate responsive font size
     */
    getResponsiveFontSize(baseSize = 14, scale = 1) {
        const multipliers = {
            xs: 0.85,
            sm: 0.9,
            md: 1,
            lg: 1.1,
            xl: 1.15,
            xxl: 1.2
        };
        
        const multiplier = multipliers[this.currentBreakpoint] || 1;
        return Math.round(baseSize * multiplier * scale);
    }
    
    /**
     * Get responsive spacing
     */
    getResponsiveSpacing(size = 'md') {
        const spacingMap = {
            xs: { xs: 4, sm: 6, md: 8, lg: 12, xl: 16 },
            sm: { xs: 6, sm: 8, md: 12, lg: 16, xl: 20 },
            md: { xs: 8, sm: 12, md: 16, lg: 20, xl: 24 },
            lg: { xs: 12, sm: 16, md: 20, lg: 24, xl: 32 },
            xl: { xs: 16, sm: 20, md: 24, lg: 32, xl: 40 },
            xxl: { xs: 20, sm: 24, md: 32, lg: 40, xl: 48 }
        };
        
        return spacingMap[this.currentBreakpoint]?.[size] || 16;
    }
    
    /**
     * Cleanup observers
     */
    destroy() {
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        
        if (this.intersectionObserver) {
            this.intersectionObserver.disconnect();
        }
        
        this.observers.clear();
        this.callbacks.length = 0;
    }
}

// Create global responsive design instance
const responsiveDesign = new ResponsiveDesign();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ResponsiveDesign, responsiveDesign };
} else {
    window.ResponsiveDesign = ResponsiveDesign;
    window.responsiveDesign = responsiveDesign;
}