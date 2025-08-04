/**
 * APIService - Unified service layer for API communications
 * Handles all HTTP requests with consistent error handling and response formatting
 */
class APIService {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
        
        // Request interceptors
        this.requestInterceptors = [];
        this.responseInterceptors = [];
        
        // Cache for GET requests
        this.cache = new Map();
        this.cacheExpiration = 5 * 60 * 1000; // 5 minutes
        
        // Setup default error handling
        this.setupErrorHandling();
    }
    
    /**
     * Setup default error handling
     */
    setupErrorHandling() {
        // Global AJAX error handler
        $(document).ajaxError((event, jqXHR, ajaxSettings, thrownError) => {
            console.error('API Error:', {
                url: ajaxSettings.url,
                status: jqXHR.status,
                error: thrownError,
                response: jqXHR.responseText
            });
            
            this.handleGlobalError(jqXHR, ajaxSettings, thrownError);
        });
    }
    
    /**
     * Handle global errors
     */
    handleGlobalError(jqXHR, ajaxSettings, thrownError) {
        let message = 'An error occurred';
        
        switch (jqXHR.status) {
            case 0:
                message = 'Connection lost. Please check your network.';
                break;
            case 400:
                message = 'Bad request. Please check your input.';
                break;
            case 401:
                message = 'Unauthorized. Please log in again.';
                break;
            case 403:
                message = 'Access forbidden.';
                break;
            case 404:
                message = 'Resource not found.';
                break;
            case 429:
                message = 'Too many requests. Please wait and try again.';
                break;
            case 500:
                message = 'Server error. Please try again later.';
                break;
            case 503:
                message = 'Service unavailable. Please try again later.';
                break;
            default:
                if (jqXHR.status >= 500) {
                    message = 'Server error occurred.';
                } else if (jqXHR.status >= 400) {
                    message = 'Client error occurred.';
                }
        }
        
        // Emit error event
        this.emitEvent('apiError', {
            status: jqXHR.status,
            message,
            url: ajaxSettings.url,
            error: thrownError
        });
    }
    
    /**
     * Add request interceptor
     */
    addRequestInterceptor(interceptor) {
        this.requestInterceptors.push(interceptor);
    }
    
    /**
     * Add response interceptor
     */
    addResponseInterceptor(interceptor) {
        this.responseInterceptors.push(interceptor);
    }
    
    /**
     * Apply request interceptors
     */
    applyRequestInterceptors(options) {
        let modifiedOptions = { ...options };
        
        for (const interceptor of this.requestInterceptors) {
            modifiedOptions = interceptor(modifiedOptions) || modifiedOptions;
        }
        
        return modifiedOptions;
    }
    
    /**
     * Apply response interceptors
     */
    applyResponseInterceptors(response) {
        let modifiedResponse = response;
        
        for (const interceptor of this.responseInterceptors) {
            modifiedResponse = interceptor(modifiedResponse) || modifiedResponse;
        }
        
        return modifiedResponse;
    }
    
    /**
     * Make HTTP request
     */
    async request(url, options = {}) {
        const fullUrl = this.baseURL + url;
        
        // Apply request interceptors
        const requestOptions = this.applyRequestInterceptors({
            url: fullUrl,
            method: 'GET',
            headers: { ...this.defaultHeaders },
            cache: false,
            ...options
        });
        
        // Check cache for GET requests
        if (requestOptions.method === 'GET' && this.cache.has(fullUrl)) {
            const cached = this.cache.get(fullUrl);
            if (Date.now() - cached.timestamp < this.cacheExpiration) {
                return Promise.resolve(cached.data);
            }
        }
        
        try {
            const response = await $.ajax(requestOptions);
            
            // Apply response interceptors
            const processedResponse = this.applyResponseInterceptors(response);
            
            // Cache GET requests
            if (requestOptions.method === 'GET') {
                this.cache.set(fullUrl, {
                    data: processedResponse,
                    timestamp: Date.now()
                });
            }
            
            return processedResponse;
        } catch (error) {
            throw this.formatError(error, fullUrl);
        }
    }
    
    /**
     * GET request
     */
    async get(url, params = {}) {
        const queryString = Object.keys(params).length > 0 ? 
            '?' + new URLSearchParams(params).toString() : '';
        
        return this.request(url + queryString, {
            method: 'GET'
        });
    }
    
    /**
     * POST request
     */
    async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            data: JSON.stringify(data)
        });
    }
    
    /**
     * PUT request
     */
    async put(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            data: JSON.stringify(data)
        });
    }
    
    /**
     * DELETE request
     */
    async delete(url) {
        return this.request(url, {
            method: 'DELETE'
        });
    }
    
    /**
     * Upload file
     */
    async upload(url, file, onProgress = null) {
        const formData = new FormData();
        formData.append('file', file);
        
        return new Promise((resolve, reject) => {
            $.ajax({
                url: this.baseURL + url,
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                xhr: function() {
                    const xhr = new window.XMLHttpRequest();
                    
                    if (onProgress) {
                        xhr.upload.addEventListener('progress', function(e) {
                            if (e.lengthComputable) {
                                const percentComplete = (e.loaded / e.total) * 100;
                                onProgress(percentComplete);
                            }
                        }, false);
                    }
                    
                    return xhr;
                },
                success: resolve,
                error: (jqXHR, textStatus, errorThrown) => {
                    reject(this.formatError({ 
                        status: jqXHR.status, 
                        statusText: textStatus, 
                        responseText: jqXHR.responseText 
                    }, url));
                }
            });
        });
    }
    
    /**
     * Format error response
     */
    formatError(error, url) {
        return {
            status: error.status || 0,
            statusText: error.statusText || 'Unknown Error',
            message: error.responseText || error.message || 'Request failed',
            url: url,
            timestamp: new Date()
        };
    }
    
    /**
     * Clear cache
     */
    clearCache(url = null) {
        if (url) {
            this.cache.delete(this.baseURL + url);
        } else {
            this.cache.clear();
        }
    }
    
    /**
     * Set default header
     */
    setHeader(name, value) {
        this.defaultHeaders[name] = value;
    }
    
    /**
     * Remove default header
     */
    removeHeader(name) {
        delete this.defaultHeaders[name];
    }
    
    /**
     * Emit custom event
     */
    emitEvent(eventName, detail) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }
    
    // Specific API methods for the application
    
    /**
     * Get system configuration
     */
    async getConfiguration() {
        return this.get('/api/system/configuration');
    }
    
    /**
     * Get available apps
     */
    async getApps() {
        return this.get('/api/apps');
    }
    
    /**
     * Analyze app
     */
    async analyzeApp(appId, options = {}) {
        return this.post('/api/analysis/analyze', { app_id: appId, ...options });
    }
    
    /**
     * Get timeline data
     */
    async getTimelineData(params = {}) {
        return this.get('/api/data/timeline', params);
    }
    
    /**
     * Get statistics data
     */
    async getStatistics(params = {}) {
        return this.get('/api/analysis/statistics', params);
    }
    
    /**
     * Get advanced analytics
     */
    async getAdvancedAnalytics(config = {}) {
        return this.post('/api/analysis/advanced', config);
    }
    
    /**
     * Get network analysis
     */
    async getNetworkAnalysis(params = {}) {
        return this.get('/api/analysis/network', params);
    }
    
    /**
     * Get process analysis
     */
    async getProcessAnalysis(params = {}) {
        return this.get('/api/analysis/process', params);
    }
    
    /**
     * Upload trace file
     */
    async uploadTrace(file, onProgress = null) {
        return this.upload('/api/upload/trace', file, onProgress);
    }
    
    /**
     * Export data
     */
    async exportData(format, params = {}) {
        return this.get(`/api/export/${format}`, params);
    }
    
    /**
     * Get system status
     */
    async getSystemStatus() {
        return this.get('/api/system/status');
    }
    
    /**
     * Batch request - execute multiple requests in parallel
     */
    async batch(requests) {
        const promises = requests.map(request => {
            const { url, method = 'GET', data = {}, params = {} } = request;
            
            switch (method.toUpperCase()) {
                case 'GET':
                    return this.get(url, params);
                case 'POST':
                    return this.post(url, data);
                case 'PUT':
                    return this.put(url, data);
                case 'DELETE':
                    return this.delete(url);
                default:
                    return this.get(url, params);
            }
        });
        
        try {
            const results = await Promise.allSettled(promises);
            return results.map((result, index) => ({
                request: requests[index],
                success: result.status === 'fulfilled',
                data: result.status === 'fulfilled' ? result.value : null,
                error: result.status === 'rejected' ? result.reason : null
            }));
        } catch (error) {
            throw new Error('Batch request failed: ' + error.message);
        }
    }
    
    /**
     * Health check - ping the server
     */
    async healthCheck() {
        try {
            await this.get('/api/health', {}, { timeout: 5000 });
            return true;
        } catch (error) {
            return false;
        }
    }
    
    /**
     * Retry request with exponential backoff
     */
    async retryRequest(requestFn, maxRetries = 3, initialDelay = 1000) {
        let delay = initialDelay;
        
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                return await requestFn();
            } catch (error) {
                if (attempt === maxRetries) {
                    throw error;
                }
                
                // Don't retry client errors (4xx), only server errors (5xx) and network errors
                if (error.status >= 400 && error.status < 500) {
                    throw error;
                }
                
                console.warn(`Request failed (attempt ${attempt}/${maxRetries}), retrying in ${delay}ms...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                delay *= 2; // Exponential backoff
            }
        }
    }
}

// Create global API service instance
const apiService = new APIService();

// Add default request interceptor for loading states
apiService.addRequestInterceptor((options) => {
    // Emit loading start event
    apiService.emitEvent('apiLoadingStart', { url: options.url });
    return options;
});

// Add default response interceptor for loading states
apiService.addResponseInterceptor((response) => {
    // Emit loading end event
    apiService.emitEvent('apiLoadingEnd', { response });
    return response;
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { APIService, apiService };
} else {
    window.APIService = APIService;
    window.apiService = apiService;
}