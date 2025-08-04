/**
 * ChartThemes - Centralized theme and color management for charts
 */
class ChartThemes {
    static themes = {
        default: {
            name: 'Default',
            background: '#ffffff',
            text: '#333333',
            grid: '#e0e0e0',
            accent: '#007bff',
            colors: {
                primary: ['#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6f42c1', '#fd7e14', '#6c757d'],
                security: ['#dc3545', '#fd7e14', '#ffc107', '#28a745', '#6c757d'],
                network: ['#007bff', '#17a2b8', '#6610f2', '#6f42c1', '#e83e8c'],
                process: ['#28a745', '#20c997', '#17a2b8', '#6f42c1', '#fd7e14'],
                filesystem: ['#343a40', '#495057', '#6c757d', '#adb5bd', '#ced4da'],
                categorical: d3.schemeCategory10
            }
        },
        
        dark: {
            name: 'Dark',
            background: '#1a1a1a',
            text: '#ffffff',
            grid: '#404040',
            accent: '#4dabf7',
            colors: {
                primary: ['#4dabf7', '#51cf66', '#ff6b6b', '#ffd43b', '#74c0fc', '#9775fa', '#ff922b', '#868e96'],
                security: ['#ff6b6b', '#ff922b', '#ffd43b', '#51cf66', '#868e96'],
                network: ['#4dabf7', '#74c0fc', '#9775fa', '#d0bfff', '#fcc2d7'],
                process: ['#51cf66', '#69db7c', '#74c0fc', '#9775fa', '#ff922b'],
                filesystem: ['#495057', '#6c757d', '#868e96', '#adb5bd', '#ced4da'],
                categorical: d3.schemeSet3
            }
        },
        
        security: {
            name: 'Security Focus',
            background: '#f8f9fa',
            text: '#212529',
            grid: '#dee2e6',
            accent: '#dc3545',
            colors: {
                primary: ['#dc3545', '#fd7e14', '#ffc107', '#198754', '#0dcaf0', '#6f42c1'],
                security: ['#dc3545', '#fd7e14', '#ffc107', '#198754', '#0dcaf0'],
                network: ['#0d6efd', '#0dcaf0', '#6610f2', '#d63384', '#fd7e14'],
                process: ['#198754', '#20c997', '#0dcaf0', '#6610f2', '#fd7e14'],
                filesystem: ['#6c757d', '#495057', '#343a40', '#adb5bd', '#ced4da'],
                categorical: ['#dc3545', '#fd7e14', '#ffc107', '#198754', '#0dcaf0', '#6f42c1', '#d63384', '#6c757d']
            }
        },
        
        minimal: {
            name: 'Minimal',
            background: '#ffffff',
            text: '#2c3e50',
            grid: '#ecf0f1',
            accent: '#3498db',
            colors: {
                primary: ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c'],
                security: ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71', '#95a5a6'],
                network: ['#3498db', '#1abc9c', '#9b59b6', '#8e44ad', '#e91e63'],
                process: ['#2ecc71', '#1abc9c', '#3498db', '#9b59b6', '#f39c12'],
                filesystem: ['#34495e', '#7f8c8d', '#95a5a6', '#bdc3c7', '#ecf0f1'],
                categorical: ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c']
            }
        }
    };
    
    static currentTheme = 'default';
    
    /**
     * Get current theme
     */
    static getCurrentTheme() {
        return this.themes[this.currentTheme] || this.themes.default;
    }
    
    /**
     * Set current theme
     */
    static setTheme(themeName) {
        if (this.themes[themeName]) {
            this.currentTheme = themeName;
            this.applyGlobalTheme();
            this.notifyThemeChange();
            return true;
        }
        console.warn(`Theme '${themeName}' not found`);
        return false;
    }
    
    /**
     * Get available themes
     */
    static getAvailableThemes() {
        return Object.keys(this.themes).map(key => ({
            key,
            name: this.themes[key].name
        }));
    }
    
    /**
     * Get color scheme for category
     */
    static getColorScheme(themeName = null, category = 'primary') {
        const theme = this.themes[themeName || this.currentTheme] || this.themes.default;
        return theme.colors[category] || theme.colors.primary;
    }
    
    /**
     * Get single color from scheme
     */
    static getColor(index = 0, themeName = null, category = 'primary') {
        const scheme = this.getColorScheme(themeName, category);
        return scheme[index % scheme.length];
    }
    
    /**
     * Get theme properties
     */
    static getThemeProperties(themeName = null) {
        const theme = this.themes[themeName || this.currentTheme] || this.themes.default;
        return {
            background: theme.background,
            text: theme.text,
            grid: theme.grid,
            accent: theme.accent
        };
    }
    
    /**
     * Generate gradient colors
     */
    static generateGradient(color1, color2, steps = 10) {
        const start = d3.color(color1);
        const end = d3.color(color2);
        
        if (!start || !end) {
            console.warn('Invalid colors for gradient');
            return [color1, color2];
        }
        
        const colors = [];
        for (let i = 0; i < steps; i++) {
            const t = i / (steps - 1);
            colors.push(d3.interpolate(start, end)(t));
        }
        
        return colors;
    }
    
    /**
     * Get contrasting text color
     */
    static getContrastingTextColor(backgroundColor) {
        const color = d3.color(backgroundColor);
        if (!color) return '#000000';
        
        const luminance = (0.299 * color.r + 0.587 * color.g + 0.114 * color.b) / 255;
        return luminance > 0.5 ? '#000000' : '#ffffff';
    }
    
    /**
     * Apply global theme to document
     */
    static applyGlobalTheme() {
        const theme = this.getCurrentTheme();
        const root = document.documentElement;
        
        // Set CSS custom properties
        root.style.setProperty('--chart-bg-color', theme.background);
        root.style.setProperty('--chart-text-color', theme.text);
        root.style.setProperty('--chart-grid-color', theme.grid);
        root.style.setProperty('--chart-accent-color', theme.accent);
        
        // Set primary colors
        theme.colors.primary.forEach((color, index) => {
            root.style.setProperty(`--chart-color-${index}`, color);
        });
        
        // Update body class for theme-specific styles
        document.body.className = document.body.className.replace(/chart-theme-\w+/, '');
        document.body.classList.add(`chart-theme-${this.currentTheme}`);
    }
    
    /**
     * Notify theme change to charts
     */
    static notifyThemeChange() {
        const event = new CustomEvent('chartThemeChanged', {
            detail: {
                theme: this.currentTheme,
                properties: this.getCurrentTheme()
            }
        });
        
        document.dispatchEvent(event);
    }
    
    /**
     * Register custom theme
     */
    static registerTheme(name, themeDefinition) {
        if (!themeDefinition.colors || !themeDefinition.colors.primary) {
            console.warn('Theme must have colors.primary array');
            return false;
        }
        
        this.themes[name] = {
            name: themeDefinition.name || name,
            background: themeDefinition.background || '#ffffff',
            text: themeDefinition.text || '#333333',
            grid: themeDefinition.grid || '#e0e0e0',
            accent: themeDefinition.accent || '#007bff',
            colors: {
                primary: themeDefinition.colors.primary,
                security: themeDefinition.colors.security || themeDefinition.colors.primary,
                network: themeDefinition.colors.network || themeDefinition.colors.primary,
                process: themeDefinition.colors.process || themeDefinition.colors.primary,
                filesystem: themeDefinition.colors.filesystem || themeDefinition.colors.primary,
                categorical: themeDefinition.colors.categorical || themeDefinition.colors.primary
            }
        };
        
        console.log(`Theme '${name}' registered successfully`);
        return true;
    }
    
    /**
     * Create adaptive color palette
     */
    static createAdaptivePalette(baseColor, count = 8) {
        const base = d3.color(baseColor);
        if (!base) return this.getColorScheme();
        
        const hsl = d3.hsl(base);
        const colors = [];
        
        for (let i = 0; i < count; i++) {
            const h = (hsl.h + (i * 360 / count)) % 360;
            const s = Math.max(0.3, hsl.s - (i * 0.1));
            const l = Math.max(0.2, Math.min(0.8, hsl.l + (i % 2 === 0 ? 0.1 : -0.1)));
            
            colors.push(d3.hsl(h, s, l).toString());
        }
        
        return colors;
    }
    
    /**
     * Get accessibility-compliant colors
     */
    static getAccessibleColors(backgroundColor = null) {
        const bg = backgroundColor || this.getCurrentTheme().background;
        const scheme = this.getColorScheme();
        
        return scheme.filter(color => {
            const contrast = this.calculateColorContrast(color, bg);
            return contrast >= 4.5; // WCAG AA standard
        });
    }
    
    /**
     * Calculate color contrast ratio
     */
    static calculateColorContrast(color1, color2) {
        const c1 = d3.color(color1);
        const c2 = d3.color(color2);
        
        if (!c1 || !c2) return 1;
        
        const l1 = this.relativeLuminance(c1);
        const l2 = this.relativeLuminance(c2);
        
        const lighter = Math.max(l1, l2);
        const darker = Math.min(l1, l2);
        
        return (lighter + 0.05) / (darker + 0.05);
    }
    
    /**
     * Calculate relative luminance
     */
    static relativeLuminance(color) {
        const rgb = d3.rgb(color);
        const rsRGB = rgb.r / 255;
        const gsRGB = rgb.g / 255;
        const bsRGB = rgb.b / 255;
        
        const r = rsRGB <= 0.03928 ? rsRGB / 12.92 : Math.pow((rsRGB + 0.055) / 1.055, 2.4);
        const g = gsRGB <= 0.03928 ? gsRGB / 12.92 : Math.pow((gsRGB + 0.055) / 1.055, 2.4);
        const b = bsRGB <= 0.03928 ? bsRGB / 12.92 : Math.pow((bsRGB + 0.055) / 1.055, 2.4);
        
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    }
}

// Initialize with default theme
ChartThemes.applyGlobalTheme();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartThemes;
} else {
    window.ChartThemes = ChartThemes;
}