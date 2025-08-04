/**
 * UploadModule - Modern file upload functionality
 * Migrated from legacy upload.js with improvements
 */
class UploadModule {
    constructor() {
        this.dropzone = null;
        this.fileInput = null;
        this.initialized = false;
        this.uploadInProgress = false;
        this.supportedFormats = ['.trace'];
        this.maxFileSize = 100 * 1024 * 1024; // 100MB
    }
    
    /**
     * Initialize the upload module
     */
    init() {
        if (this.initialized) return;
        
        try {
            // Check dependencies
            if (!this.checkDependencies()) {
                throw new Error('UploadModule dependencies not satisfied');
            }
            
            this.dropzone = document.getElementById('upload-dropzone');
            this.fileInput = document.getElementById('trace-file-input');
            
            if (!this.dropzone || !this.fileInput) {
                throw new Error('Upload elements not found in DOM');
            }
            
            this.setupDragAndDrop();
            this.setupFileInputHandlers();
            this.setupExportHandlers();
            this.checkPreloadedFile();
            this.initialized = true;
            
            console.log('UploadModule initialized successfully');
        } catch (error) {
            console.error('Failed to initialize UploadModule:', error);
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
            { name: 'FileReader API', check: () => typeof FileReader !== 'undefined' },
            { name: 'FormData API', check: () => typeof FormData !== 'undefined' },
            { name: 'UIModule', check: () => window.uiModule && window.uiModule.initialized }
        ];
        
        const missing = required.filter(dep => !dep.check());
        
        if (missing.length > 0) {
            console.warn('UploadModule missing dependencies:', missing.map(d => d.name));
            return false;
        }
        
        return true;
    }
    
    /**
     * Setup drag and drop functionality
     */
    setupDragAndDrop() {
        // Prevent default drag behaviors on document
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, this.preventDefaults, false);
        });
        
        // Highlight drop zone when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            this.dropzone.addEventListener(eventName, () => {
                this.dropzone.classList.add('dragover');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            this.dropzone.addEventListener(eventName, () => {
                this.dropzone.classList.remove('dragover');
            }, false);
        });
        
        // Handle dropped files
        this.dropzone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            this.handleFiles(files);
        }, false);
        
        // Handle click on dropzone
        this.dropzone.addEventListener('click', (e) => {
            // Only trigger file input if not clicking on the select button
            if (!e.target.closest('#select-file-btn')) {
                this.fileInput.click();
            }
        });
        
        // Handle select file button
        document.getElementById('select-file-btn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.fileInput.click();
        });
    }
    
    /**
     * Setup file input handlers
     */
    setupFileInputHandlers() {
        this.fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
    }
    
    /**
     * Setup export handlers
     */
    setupExportHandlers() {
        // Export JSON button
        $(document).off('click.upload', '[onclick*="exportEvents"]').on('click.upload', '[onclick*="exportEvents"]', (e) => {
            e.preventDefault();
            const format = e.currentTarget.getAttribute('onclick').match(/exportEvents\('(\w+)'\)/)?.[1];
            if (format) {
                this.exportEvents(format);
            }
        });
    }
    
    /**
     * Prevent default drag behaviors
     */
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    /**
     * Handle selected or dropped files
     */
    handleFiles(files) {
        if (!files || files.length === 0) return;
        
        const file = files[0]; // Only handle first file
        
        // Validate file
        const validation = this.validateFile(file);
        if (!validation.valid) {
            this.showError(validation.error);
            return;
        }
        
        // Update UI to show selected file
        this.showSelectedFile(file);
        
        // Start upload automatically or show upload button
        this.uploadFile(file);
    }
    
    /**
     * Validate file before upload
     */
    validateFile(file) {
        // Check file extension
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.supportedFormats.includes(extension)) {
            return {
                valid: false,
                error: `Unsupported file format. Supported formats: ${this.supportedFormats.join(', ')}`
            };
        }
        
        // Check file size
        if (file.size > this.maxFileSize) {
            const maxSizeMB = this.maxFileSize / (1024 * 1024);
            return {
                valid: false,
                error: `File size exceeds ${maxSizeMB}MB limit`
            };
        }
        
        return { valid: true };
    }
    
    /**
     * Show selected file information
     */
    showSelectedFile(file) {
        const fileSize = this.formatFileSize(file.size);
        const fileName = file.name;
        
        // Update dropzone to show selected file
        this.dropzone.innerHTML = `
            <div class="selected-file">
                <div class="file-icon">
                    <i class="fas fa-file-alt"></i>
                </div>
                <h5>${fileName}</h5>
                <p class="text-muted">Size: ${fileSize}</p>
                <button class="btn btn-modern mt-2" id="change-file-btn">
                    <i class="fas fa-exchange-alt"></i> Change File
                </button>
            </div>
        `;
        
        // Setup change file button
        document.getElementById('change-file-btn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.resetUploadArea();
            this.fileInput.click();
        });
    }
    
    /**
     * Upload file to server
     */
    async uploadFile(file) {
        if (this.uploadInProgress) return;
        
        this.uploadInProgress = true;
        this.showUploadProgress(0, 'Preparing upload...');
        
        try {
            // Use APIService for upload with progress tracking
            const response = await apiService.upload('/api/upload/trace', file, (progress) => {
                this.showUploadProgress(progress, 'Uploading...');
            });
            
            this.showUploadProgress(100, 'Processing...');
            
            if (response.success) {
                this.showUploadSuccess(response);
                this.emitEvent('uploadSuccess', { file, response });
            } else {
                throw new Error(response.error || 'Upload failed');
            }
            
        } catch (error) {
            console.error('Upload failed:', error);
            this.showUploadError(error.message);
            this.emitEvent('uploadError', { file, error });
        } finally {
            this.uploadInProgress = false;
        }
    }
    
    /**
     * Show upload progress
     */
    showUploadProgress(percentage, status) {
        const progressContainer = document.getElementById('upload-progress');
        const progressBar = document.getElementById('progress-bar');
        const progressPercentage = document.getElementById('progress-percentage');
        const uploadStatus = document.getElementById('upload-status');
        
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
        
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }
        
        if (progressPercentage) {
            progressPercentage.textContent = `${Math.round(percentage)}%`;
        }
        
        if (uploadStatus) {
            uploadStatus.textContent = status;
        }
    }
    
    /**
     * Show upload success
     */
    showUploadSuccess(response) {
        const resultContainer = document.getElementById('upload-result');
        const uploadAlert = document.getElementById('upload-alert');
        
        if (resultContainer && uploadAlert) {
            uploadAlert.className = 'alert alert-success';
            uploadAlert.innerHTML = `
                <i class="fas fa-check-circle me-2"></i>
                <strong>Upload successful!</strong> 
                ${response.message || 'File uploaded and processed successfully.'}
            `;
            resultContainer.style.display = 'block';
        }
        
        // Hide progress after delay
        setTimeout(() => {
            const progressContainer = document.getElementById('upload-progress');
            if (progressContainer) {
                progressContainer.style.display = 'none';
            }
        }, 2000);
        
        // Show toast notification
        if (window.uiModule) {
            uiModule.showToast('File uploaded successfully!', 'success');
        }
    }
    
    /**
     * Show upload error
     */
    showUploadError(errorMessage) {
        const resultContainer = document.getElementById('upload-result');
        const uploadAlert = document.getElementById('upload-alert');
        
        if (resultContainer && uploadAlert) {
            uploadAlert.className = 'alert alert-danger';
            uploadAlert.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Upload failed!</strong> 
                ${errorMessage}
            `;
            resultContainer.style.display = 'block';
        }
        
        // Hide progress
        const progressContainer = document.getElementById('upload-progress');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
        
        // Show toast notification
        if (window.uiModule) {
            uiModule.showToast(`Upload failed: ${errorMessage}`, 'error');
        }
        
        // Reset upload area after delay
        setTimeout(() => {
            this.resetUploadArea();
        }, 5000);
    }
    
    /**
     * Show general error
     */
    showError(errorMessage) {
        if (window.uiModule) {
            uiModule.showToast(errorMessage, 'error');
        } else {
            alert(errorMessage);
        }
    }
    
    /**
     * Reset upload area to initial state
     */
    resetUploadArea() {
        this.dropzone.innerHTML = `
            <div class="upload-icon">
                <i class="fas fa-file-upload"></i>
            </div>
            <h4>Drop your trace file here</h4>
            <p class="text-muted">Supports .trace files for analysis</p>
            <button class="btn btn-modern mt-3" id="select-file-btn">
                <i class="fas fa-folder-open"></i> Select File
            </button>
        `;
        
        // Re-setup select button
        document.getElementById('select-file-btn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.fileInput.click();
        });
        
        // Clear file input
        this.fileInput.value = '';
        
        // Hide progress and result containers
        ['upload-progress', 'upload-result'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.style.display = 'none';
        });
    }
    
    /**
     * Check for preloaded file (if any)
     */
    checkPreloadedFile() {
        // Check if there's already a file in the input
        if (this.fileInput.files && this.fileInput.files.length > 0) {
            this.handleFiles(this.fileInput.files);
        }
    }
    
    /**
     * Export events in specified format
     */
    async exportEvents(format) {
        try {
            const response = await apiService.get(`/api/export/${format}`);
            
            if (response.success) {
                // Create download link
                const blob = new Blob([response.data], {
                    type: format === 'json' ? 'application/json' : 'text/csv'
                });
                
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `slicedroid-events.${format}`;
                link.style.display = 'none';
                
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                URL.revokeObjectURL(url);
                
                if (window.uiModule) {
                    uiModule.showToast(`Events exported as ${format.toUpperCase()}`, 'success');
                }
                
            } else {
                throw new Error(response.error || 'Export failed');
            }
            
        } catch (error) {
            console.error('Export failed:', error);
            
            if (window.uiModule) {
                uiModule.showToast(`Export failed: ${error.message}`, 'error');
            }
        }
    }
    
    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    /**
     * Get upload status
     */
    getUploadStatus() {
        return {
            inProgress: this.uploadInProgress,
            hasFile: this.fileInput && this.fileInput.files && this.fileInput.files.length > 0
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
     * Cleanup and destroy
     */
    destroy() {
        // Remove event listeners
        $(document).off('.upload');
        
        // Remove drag and drop listeners
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.removeEventListener(eventName, this.preventDefaults, false);
        });
        
        this.initialized = false;
        console.log('UploadModule destroyed');
    }
}

// Create global instance
const uploadModule = new UploadModule();

// Don't auto-initialize - let main.js handle initialization order
// This prevents race conditions with other modules

// Export global functions for backward compatibility
window.exportEvents = (format) => uploadModule.exportEvents(format);
window.initializeUploadFunctionality = () => uploadModule.init();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { UploadModule, uploadModule };
} else {
    window.UploadModule = UploadModule;
    window.uploadModule = uploadModule;
}

console.log('UploadModule loaded (waiting for initialization)');