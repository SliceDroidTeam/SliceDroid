/**
 * AppSelectionModule - Modern app selection functionality
 * Migrated from legacy app_selection.js with improvements
 */
class AppSelectionModule {
    constructor() {
        this.allApps = [];
        this.selectedApp = null;
        this.lastAnalyzedApp = null;
        this.initialized = false;
    }
    
    /**
     * Initialize the app selection module
     */
    init() {
        if (this.initialized) return;
        
        try {
            // Check dependencies
            if (!this.checkDependencies()) {
                throw new Error('AppSelectionModule dependencies not satisfied');
            }
            
            this.setupEventListeners();
            this.loadApps();
            this.initialized = true;
            
            console.log('AppSelectionModule initialized successfully');
        } catch (error) {
            console.error('Failed to initialize AppSelectionModule:', error);
            this.initialized = false;
            throw error;
        }
    }
    
    /**
     * Check module dependencies
     */
    checkDependencies() {
        const required = [
            { name: 'jQuery', check: () => typeof $ !== 'undefined' },
            { name: 'App Select Element', check: () => document.getElementById('app-select') !== null },
            { name: 'Analyze Button', check: () => document.getElementById('analyze-app') !== null }
        ];
        
        const missing = required.filter(dep => !dep.check());
        
        if (missing.length > 0) {
            console.warn('AppSelectionModule missing dependencies:', missing.map(d => d.name));
            return false;
        }
        
        return true;
    }
    
    /**
     * Setup event listeners for app selection
     */
    setupEventListeners() {
        // App selection dropdown
        $('#app-select').off('change.appSelection').on('change.appSelection', (e) => {
            this.handleAppSelection($(e.target).val());
        });
        
        // Analyze app button
        $('#analyze-app').off('click.appSelection').on('click.appSelection', (e) => {
            e.preventDefault();
            this.analyzeSelectedApp();
        });
    }
    
    /**
     * Handle app selection change
     */
    handleAppSelection(selectedPackage) {
        this.selectedApp = selectedPackage;
        
        if (selectedPackage) {
            const hasAppChanged = selectedPackage !== this.lastAnalyzedApp;
            $('#analyze-app').prop('disabled', !hasAppChanged);
            
            const app = this.allApps.find(a => a.package_name === selectedPackage);
            if (app) {
                this.updateAppStatus(app, hasAppChanged);
            }
        } else {
            $('#analyze-app').prop('disabled', true);
            this.showDefaultStatus();
        }
        
        // Emit app selection event
        this.emitEvent('appSelected', {
            app: this.selectedApp,
            hasChanged: selectedPackage !== this.lastAnalyzedApp
        });
    }
    
    /**
     * Update app status display
     */
    updateAppStatus(app, hasAppChanged) {
        const statusElement = $('#app-status');
        
        if (hasAppChanged) {
            statusElement
                .removeClass('alert-info alert-warning alert-danger')
                .addClass('alert-success')
                .html(`
                    <i class="fas fa-check-circle me-2"></i>
                    <span><strong>${app.commercial_name}</strong> selected and ready for analysis</span>
                `);
        } else {
            statusElement
                .removeClass('alert-info alert-warning alert-danger')
                .addClass('alert-warning')
                .html(`
                    <i class="fas fa-info-circle me-2"></i>
                    <span><strong>${app.commercial_name}</strong> already analyzed. Select a different app to enable analysis.</span>
                `);
        }
    }
    
    /**
     * Show default status message
     */
    showDefaultStatus() {
        $('#app-status')
            .removeClass('alert-success alert-warning alert-danger')
            .addClass('alert-info')
            .html(`
                <i class="fas fa-info-circle me-2"></i>
                <span>Select an application from the dropdown to begin analysis</span>
            `);
    }
    
    /**
     * Load available apps from API
     */
    async loadApps() {
        try {
            const response = await apiService.get('/api/apps');
            this.allApps = response.apps || [];
            this.populateAppDropdown();
            
            console.log(`Loaded ${this.allApps.length} apps`);
        } catch (error) {
            console.error('Failed to load apps:', error);
            this.showAppLoadError();
        }
    }
    
    /**
     * Populate the app dropdown with loaded apps
     */
    populateAppDropdown() {
        const appSelect = $('#app-select');
        appSelect.empty();
        
        if (this.allApps.length === 0) {
            appSelect.html('<option value="">No apps available</option>');
            return;
        }
        
        appSelect.html('<option value="">Select an application...</option>');
        
        this.allApps.forEach(app => {
            const option = $('<option>')
                .val(app.package_name)
                .text(`${app.commercial_name} (${app.package_name})`)
                .data('app', app);
            
            appSelect.append(option);
        });
        
        // Re-select previously selected app if available
        if (this.selectedApp && this.allApps.find(a => a.package_name === this.selectedApp)) {
            appSelect.val(this.selectedApp).trigger('change');
        }
    }
    
    /**
     * Show error when apps fail to load
     */
    showAppLoadError() {
        $('#app-select').html('<option value="">Error loading apps</option>');
        $('#app-status')
            .removeClass('alert-info alert-success alert-warning')
            .addClass('alert-danger')
            .html(`
                <i class="fas fa-exclamation-triangle me-2"></i>
                <span>Failed to load applications. Please refresh the page.</span>
            `);
    }
    
    /**
     * Analyze the selected app
     */
    async analyzeSelectedApp() {
        if (!this.selectedApp) {
            console.warn('No app selected for analysis');
            return;
        }
        
        const app = this.allApps.find(a => a.package_name === this.selectedApp);
        if (!app) {
            console.error('Selected app not found in apps list');
            return;
        }
        
        try {
            this.showAnalysisStarted(app);
            
            // Start analysis
            const response = await apiService.post('/api/analysis/analyze', {
                app_id: this.selectedApp,
                generate_targets: true
            });
            
            if (response.success) {
                this.lastAnalyzedApp = this.selectedApp;
                this.showAnalysisCompleted(app);
                
                // Emit analysis completed event
                this.emitEvent('analysisCompleted', {
                    app: this.selectedApp,
                    response: response
                });
                
                // Show analysis sections
                this.showAnalysisSections();
                
            } else {
                throw new Error(response.error || 'Analysis failed');
            }
            
        } catch (error) {
            console.error('Analysis failed:', error);
            this.showAnalysisError(app, error.message);
        }
    }
    
    /**
     * Show analysis started state
     */
    showAnalysisStarted(app) {
        $('#analyze-app')
            .prop('disabled', true)
            .html('<i class="fas fa-spinner fa-spin me-2"></i>Analyzing...');
        
        $('#app-status')
            .removeClass('alert-info alert-warning alert-danger')
            .addClass('alert-info')
            .html(`
                <i class="fas fa-cog fa-spin me-2"></i>
                <span>Analyzing <strong>${app.commercial_name}</strong>...</span>
            `);
    }
    
    /**
     * Show analysis completed state
     */
    showAnalysisCompleted(app) {
        $('#analyze-app')
            .html('<i class="fas fa-chart-line me-2"></i>Start Analysis');
        
        $('#app-status')
            .removeClass('alert-info alert-warning alert-danger')
            .addClass('alert-success')
            .html(`
                <i class="fas fa-check-circle me-2"></i>
                <span><strong>${app.commercial_name}</strong> analysis completed successfully!</span>
            `);
    }
    
    /**
     * Show analysis error state
     */
    showAnalysisError(app, errorMessage) {
        $('#analyze-app')
            .prop('disabled', false)
            .html('<i class="fas fa-chart-line me-2"></i>Start Analysis');
        
        $('#app-status')
            .removeClass('alert-info alert-warning alert-success')
            .addClass('alert-danger')
            .html(`
                <i class="fas fa-exclamation-triangle me-2"></i>
                <span>Analysis of <strong>${app.commercial_name}</strong> failed: ${errorMessage}</span>
            `);
    }
    
    /**
     * Show analysis sections after successful analysis
     */
    showAnalysisSections() {
        $('.analysis-only').fadeIn(300);
        
        // Scroll to first analysis section
        const firstSection = $('.analysis-only').first();
        if (firstSection.length) {
            $('html, body').animate({
                scrollTop: firstSection.offset().top - 100
            }, 800);
        }
    }
    
    /**
     * Get selected app information
     */
    getSelectedApp() {
        if (!this.selectedApp) return null;
        
        return {
            packageName: this.selectedApp,
            app: this.allApps.find(a => a.package_name === this.selectedApp)
        };
    }
    
    /**
     * Emit custom event
     */
    emitEvent(eventName, detail) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }
    
    /**
     * Refresh apps list
     */
    async refreshApps() {
        console.log('Refreshing apps list...');
        await this.loadApps();
    }
    
    /**
     * Reset selection state
     */
    reset() {
        this.selectedApp = null;
        this.lastAnalyzedApp = null;
        $('#app-select').val('').trigger('change');
        $('.analysis-only').hide();
    }
    
    /**
     * Cleanup and destroy
     */
    destroy() {
        $('#app-select').off('.appSelection');
        $('#analyze-app').off('.appSelection');
        this.initialized = false;
        
        console.log('AppSelectionModule destroyed');
    }
}

// Create global instance
const appSelectionModule = new AppSelectionModule();

// Don't auto-initialize - let main.js handle initialization order
// This prevents race conditions with other modules

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AppSelectionModule, appSelectionModule };
} else {
    window.AppSelectionModule = AppSelectionModule;
    window.appSelectionModule = appSelectionModule;
}

console.log('AppSelectionModule loaded (waiting for initialization)');