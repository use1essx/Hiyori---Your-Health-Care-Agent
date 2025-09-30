/**
 * AWS Configuration for Live2D Frontend
 * ====================================
 * 
 * Centralized configuration for AWS services and API endpoints.
 * Automatically detects environment and configures appropriate endpoints.
 */

class AWSConfig {
    constructor() {
        this.environment = this.detectEnvironment();
        this.config = this.loadConfiguration();
    }

    detectEnvironment() {
        const hostname = window.location.hostname;
        
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'development';
        } else if (hostname.includes('cloudfront.net') || hostname.includes('s3-website')) {
            return 'production';
        } else if (hostname.includes('staging') || hostname.includes('test')) {
            return 'staging';
        }
        
        return 'production'; // Default to production
    }

    loadConfiguration() {
        const configs = {
            development: {
                apiGateway: {
                    baseUrl: 'http://localhost:8000/api',
                    region: 'us-east-1',
                    timeout: 30000
                },
                websocket: {
                    url: 'ws://localhost:8000/ws',
                    reconnectInterval: 5000,
                    maxReconnectAttempts: 10
                },
                s3: {
                    region: 'us-east-1',
                    bucket: 'healthcare-ai-dev-assets'
                },
                cloudfront: {
                    domain: null // No CloudFront in development
                }
            },
            staging: {
                apiGateway: {
                    baseUrl: '{{API_GATEWAY_URL}}', // Will be replaced during deployment
                    region: 'us-east-1',
                    timeout: 30000
                },
                websocket: {
                    url: '{{WEBSOCKET_URL}}',
                    reconnectInterval: 5000,
                    maxReconnectAttempts: 10
                },
                s3: {
                    region: 'us-east-1',
                    bucket: 'healthcare-ai-staging-assets'
                },
                cloudfront: {
                    domain: '{{CLOUDFRONT_DOMAIN}}'
                }
            },
            production: {
                apiGateway: {
                    baseUrl: '{{API_GATEWAY_URL}}', // Will be replaced during deployment
                    region: 'us-east-1',
                    timeout: 30000
                },
                websocket: {
                    url: '{{WEBSOCKET_URL}}',
                    reconnectInterval: 3000,
                    maxReconnectAttempts: 5
                },
                s3: {
                    region: 'us-east-1',
                    bucket: 'healthcare-ai-prod-assets'
                },
                cloudfront: {
                    domain: '{{CLOUDFRONT_DOMAIN}}'
                }
            }
        };

        return configs[this.environment];
    }

    // API Gateway endpoints
    getApiEndpoint(path = '') {
        const baseUrl = this.config.apiGateway.baseUrl.replace(/\/$/, '');
        const cleanPath = path.replace(/^\//, '');
        return cleanPath ? `${baseUrl}/${cleanPath}` : baseUrl;
    }

    // Healthcare agent endpoints
    getAgentEndpoints() {
        return {
            router: this.getApiEndpoint('agent-router'),
            illnessMonitor: this.getApiEndpoint('illness-monitor'),
            mentalHealth: this.getApiEndpoint('mental-health'),
            safetyGuardian: this.getApiEndpoint('safety-guardian'),
            wellnessCoach: this.getApiEndpoint('wellness-coach')
        };
    }

    // Speech processing endpoints
    getSpeechEndpoints() {
        return {
            speechToText: this.getApiEndpoint('speech-to-text'),
            textToSpeech: this.getApiEndpoint('text-to-speech')
        };
    }

    // File upload endpoints
    getFileEndpoints() {
        return {
            upload: this.getApiEndpoint('file-upload'),
            download: this.getApiEndpoint('file-download')
        };
    }

    // WebSocket configuration
    getWebSocketConfig() {
        return {
            url: this.config.websocket.url,
            options: {
                reconnectInterval: this.config.websocket.reconnectInterval,
                maxReconnectAttempts: this.config.websocket.maxReconnectAttempts
            }
        };
    }

    // S3 asset URLs
    getAssetUrl(path) {
        if (this.config.cloudfront.domain) {
            return `https://${this.config.cloudfront.domain}/${path}`;
        } else {
            return `https://${this.config.s3.bucket}.s3.${this.config.s3.region}.amazonaws.com/${path}`;
        }
    }

    // Live2D model URLs
    getLive2DModelUrl(modelName, fileName) {
        return this.getAssetUrl(`live2d/models/${modelName}/${fileName}`);
    }

    // Audio file URLs
    getAudioUrl(fileName) {
        return this.getAssetUrl(`audio/${fileName}`);
    }

    // Request configuration
    getRequestConfig() {
        return {
            timeout: this.config.apiGateway.timeout,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include' // Include cookies for authentication
        };
    }

    // Error handling configuration
    getErrorConfig() {
        return {
            retryAttempts: 3,
            retryDelay: 1000,
            retryableStatusCodes: [408, 429, 500, 502, 503, 504]
        };
    }

    // Feature flags
    getFeatureFlags() {
        return {
            speechEnabled: true,
            live2dEnabled: true,
            fileUploadEnabled: true,
            analyticsEnabled: this.environment === 'production',
            debugMode: this.environment === 'development'
        };
    }

    // Performance configuration
    getPerformanceConfig() {
        return {
            live2d: {
                targetFPS: this.environment === 'development' ? 30 : 60,
                enableAntiAliasing: this.environment !== 'development',
                enableMotionSync: true
            },
            audio: {
                enableCompression: this.environment === 'production',
                bitRate: this.environment === 'production' ? 128 : 256
            },
            caching: {
                enableServiceWorker: this.environment === 'production',
                cacheTimeout: 24 * 60 * 60 * 1000 // 24 hours
            }
        };
    }
}

// Create global configuration instance
window.AWSConfig = new AWSConfig();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AWSConfig;
}

// Utility functions for common operations
window.HealthcareAPI = {
    // Make authenticated API request
    async makeRequest(endpoint, options = {}) {
        const config = window.AWSConfig.getRequestConfig();
        const errorConfig = window.AWSConfig.getErrorConfig();
        
        const requestOptions = {
            ...config,
            ...options,
            headers: {
                ...config.headers,
                ...options.headers
            }
        };

        let lastError;
        
        for (let attempt = 0; attempt <= errorConfig.retryAttempts; attempt++) {
            try {
                const response = await fetch(endpoint, requestOptions);
                
                if (response.ok) {
                    return await response.json();
                }
                
                // Check if error is retryable
                if (errorConfig.retryableStatusCodes.includes(response.status) && 
                    attempt < errorConfig.retryAttempts) {
                    await this.delay(errorConfig.retryDelay * Math.pow(2, attempt));
                    continue;
                }
                
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                
            } catch (error) {
                lastError = error;
                
                if (attempt < errorConfig.retryAttempts) {
                    await this.delay(errorConfig.retryDelay * Math.pow(2, attempt));
                    continue;
                }
                
                break;
            }
        }
        
        throw lastError;
    },

    // Send message to healthcare agent
    async sendMessage(message, agentType = null, conversationId = null) {
        const endpoints = window.AWSConfig.getAgentEndpoints();
        const endpoint = agentType ? endpoints[agentType] : endpoints.router;
        
        return await this.makeRequest(endpoint, {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId,
                user_id: this.getUserId(),
                language_preference: this.getLanguagePreference()
            })
        });
    },

    // Convert text to speech
    async textToSpeech(text, agentType = 'wellness_coach') {
        const endpoints = window.AWSConfig.getSpeechEndpoints();
        
        return await this.makeRequest(endpoints.textToSpeech, {
            method: 'POST',
            body: JSON.stringify({
                action: 'synthesize',
                text: text,
                agent_type: agentType,
                language: this.getLanguagePreference(),
                output_format: 'mp3'
            })
        });
    },

    // Convert speech to text
    async speechToText(audioData) {
        const endpoints = window.AWSConfig.getSpeechEndpoints();
        
        return await this.makeRequest(endpoints.speechToText, {
            method: 'POST',
            body: JSON.stringify({
                action: 'start_transcription',
                audio_data: audioData,
                language_preference: this.getLanguagePreference(),
                user_id: this.getUserId()
            })
        });
    },

    // Utility functions
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    getUserId() {
        return localStorage.getItem('healthcare_user_id') || 'anonymous';
    },

    getLanguagePreference() {
        return localStorage.getItem('language_preference') || 'zh-HK';
    },

    setLanguagePreference(language) {
        localStorage.setItem('language_preference', language);
    },

    // Initialize application
    async initialize() {
        console.log('Initializing Healthcare AI Frontend...');
        console.log('Environment:', window.AWSConfig.environment);
        console.log('API Base URL:', window.AWSConfig.config.apiGateway.baseUrl);
        
        // Test API connectivity
        try {
            const healthCheck = await this.makeRequest(
                window.AWSConfig.getApiEndpoint('health'),
                { method: 'GET' }
            );
            console.log('API Health Check:', healthCheck);
        } catch (error) {
            console.warn('API Health Check failed:', error);
        }
        
        // Initialize feature flags
        const features = window.AWSConfig.getFeatureFlags();
        console.log('Feature Flags:', features);
        
        return {
            environment: window.AWSConfig.environment,
            features: features,
            endpoints: window.AWSConfig.getAgentEndpoints()
        };
    }
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.HealthcareAPI.initialize();
    });
} else {
    window.HealthcareAPI.initialize();
}