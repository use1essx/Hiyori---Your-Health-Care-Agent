/**
 * Live2D Frontend Integration Example - Healthcare AI V2
 * ======================================================
 * 
 * Complete example of integrating Healthcare AI V2 backend with Live2D frontend.
 * Demonstrates WebSocket communication, emotion/gesture handling, and real-time
 * avatar synchronization.
 * 
 * Features:
 * - WebSocket connection management
 * - Real-time chat integration
 * - Avatar emotion and gesture synchronization
 * - Hong Kong cultural adaptation
 * - Error handling and reconnection
 * - Performance optimization
 */

class HealthcareAILive2DClient {
    constructor(config = {}) {
        // Configuration
        this.config = {
            wsUrl: config.wsUrl || 'ws://localhost:8000/ws/live2d/chat',
            apiUrl: config.apiUrl || 'http://localhost:8000/api/v1',
            language: config.language || 'zh-HK',
            clientType: config.clientType || 'live2d',
            reconnectInterval: config.reconnectInterval || 5000,
            maxReconnectAttempts: config.maxReconnectAttempts || 10,
            heartbeatInterval: config.heartbeatInterval || 30000,
            authToken: config.authToken || null
        };
        
        // State
        this.ws = null;
        this.sessionId = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.heartbeatTimer = null;
        this.messageQueue = [];
        
        // Event handlers
        this.eventHandlers = {
            connected: [],
            disconnected: [],
            message: [],
            agentResponse: [],
            emotionChange: [],
            gestureChange: [],
            emergencyAlert: [],
            error: []
        };
        
        // Agent and avatar state
        this.currentAgent = null;
        this.currentEmotion = 'neutral';
        this.currentGesture = 'default';
        this.avatarState = {};
        
        // Performance tracking
        this.messageCount = 0;
        this.totalResponseTime = 0;
        this.lastMessageTime = null;
        
        // Initialize
        this.init();
    }
    
    /**
     * Initialize the client
     */
    init() {
        console.log('Initializing Healthcare AI Live2D Client...');
        this.connect();
    }
    
    /**
     * Connect to WebSocket
     */
    connect() {
        try {
            const wsUrl = new URL(this.config.wsUrl);
            wsUrl.searchParams.set('language', this.config.language);
            wsUrl.searchParams.set('client_type', this.config.clientType);
            
            if (this.config.authToken) {
                wsUrl.searchParams.set('token', this.config.authToken);
            }
            
            console.log(`Connecting to Healthcare AI WebSocket: ${wsUrl}`);
            
            this.ws = new WebSocket(wsUrl.toString());
            this.setupWebSocketHandlers();
            
        } catch (error) {
            console.error('Error connecting to WebSocket:', error);
            this.handleConnectionError(error);
        }
    }
    
    /**
     * Setup WebSocket event handlers
     */
    setupWebSocketHandlers() {
        this.ws.onopen = (event) => {
            console.log('WebSocket connected to Healthcare AI');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.startHeartbeat();
            this.processMessageQueue();
            this.emit('connected', { event });
        };
        
        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
                this.emit('error', { type: 'parse_error', error, data: event.data });
            }
        };
        
        this.ws.onclose = (event) => {
            console.log('WebSocket disconnected from Healthcare AI');
            this.isConnected = false;
            this.stopHeartbeat();
            this.emit('disconnected', { event });
            
            // Attempt reconnection if not manually closed
            if (event.code !== 1000 && this.reconnectAttempts < this.config.maxReconnectAttempts) {
                this.scheduleReconnect();
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.emit('error', { type: 'websocket_error', error });
        };
    }
    
    /**
     * Handle incoming messages
     */
    handleMessage(message) {
        console.log('Received message from Healthcare AI:', message);
        
        // Calculate response time if applicable
        if (this.lastMessageTime && message.type === 'agent_response') {
            const responseTime = Date.now() - this.lastMessageTime;
            this.totalResponseTime += responseTime;
            this.messageCount++;
            console.log(`Response time: ${responseTime}ms (avg: ${this.getAverageResponseTime()}ms)`);
        }
        
        switch (message.type) {
            case 'welcome':
                this.handleWelcomeMessage(message);
                break;
            case 'agent_response':
                this.handleAgentResponse(message);
                break;
            case 'agent_thinking':
                this.handleAgentThinking(message);
                break;
            case 'system_status':
                this.handleSystemStatus(message);
                break;
            case 'emergency_alert':
                this.handleEmergencyAlert(message);
                break;
            case 'error':
                this.handleError(message);
                break;
            case 'pong':
                // Heartbeat response
                break;
            default:
                console.warn('Unknown message type:', message.type);
        }
        
        this.emit('message', message);
    }
    
    /**
     * Handle welcome message
     */
    handleWelcomeMessage(message) {
        this.sessionId = message.session_id;
        console.log(`Healthcare AI session established: ${this.sessionId}`);
        console.log('Available agents:', message.available_agents);
        console.log('Supported languages:', message.supported_languages || ['en', 'zh-HK']);
    }
    
    /**
     * Handle agent response
     */
    handleAgentResponse(message) {
        // Update current agent state
        this.currentAgent = message.agent_type;
        
        // Handle emotion change
        if (message.emotion && message.emotion !== this.currentEmotion) {
            this.handleEmotionChange(message.emotion, message.agent_type);
        }
        
        // Handle gesture change
        if (message.gesture && message.gesture !== this.currentGesture) {
            this.handleGestureChange(message.gesture, message.agent_type);
        }
        
        // Update avatar state
        if (message.avatar_state) {
            this.updateAvatarState(message.avatar_state);
        }
        
        // Handle voice settings
        if (message.voice_settings) {
            this.updateVoiceSettings(message.voice_settings);
        }
        
        // Handle animation cues
        if (message.animation_cues && message.animation_cues.length > 0) {
            this.processAnimationCues(message.animation_cues);
        }
        
        // Handle HK facilities data
        if (message.hk_facilities && message.hk_facilities.length > 0) {
            this.displayHKFacilities(message.hk_facilities);
        }
        
        // Emit agent response event
        this.emit('agentResponse', {
            message: message.message,
            agentType: message.agent_type,
            agentName: message.agent_name,
            emotion: message.emotion,
            gesture: message.gesture,
            urgency: message.urgency,
            language: message.language,
            confidence: message.confidence,
            hkFacilities: message.hk_facilities,
            emergencyInfo: message.emergency_info
        });
    }
    
    /**
     * Handle emotion change
     */
    handleEmotionChange(newEmotion, agentType) {
        console.log(`Emotion change: ${this.currentEmotion} → ${newEmotion} (${agentType})`);
        
        const oldEmotion = this.currentEmotion;
        this.currentEmotion = newEmotion;
        
        // Apply emotion to Live2D avatar
        this.applyEmotionToAvatar(newEmotion, agentType);
        
        this.emit('emotionChange', {
            oldEmotion,
            newEmotion,
            agentType
        });
    }
    
    /**
     * Handle gesture change
     */
    handleGestureChange(newGesture, agentType) {
        console.log(`Gesture change: ${this.currentGesture} → ${newGesture} (${agentType})`);
        
        const oldGesture = this.currentGesture;
        this.currentGesture = newGesture;
        
        // Apply gesture to Live2D avatar
        this.applyGestureToAvatar(newGesture, agentType);
        
        this.emit('gestureChange', {
            oldGesture,
            newGesture,
            agentType
        });
    }
    
    /**
     * Apply emotion to Live2D avatar
     */
    applyEmotionToAvatar(emotion, agentType) {
        // This would integrate with your Live2D avatar system
        console.log(`Applying emotion '${emotion}' to ${agentType} avatar`);
        
        // Example Live2D integration
        if (window.live2dAvatar) {
            // Map Healthcare AI emotions to Live2D expressions
            const emotionMap = {
                'professional_caring': 'gentle_smile',
                'concerned_medical': 'worried_expression',
                'gentle_supportive': 'soft_caring',
                'encouraging_youthful': 'bright_smile',
                'alert_focused': 'serious_attention',
                'energetic_positive': 'excited_smile'
            };
            
            const live2dExpression = emotionMap[emotion] || 'neutral';
            window.live2dAvatar.setExpression(live2dExpression);
            
            // Adjust based on agent personality
            if (agentType === 'mental_health') {
                window.live2dAvatar.setEyeColor('soft_purple');
            } else if (agentType === 'safety_guardian') {
                window.live2dAvatar.setEyeColor('alert_orange');
            }
        }
    }
    
    /**
     * Apply gesture to Live2D avatar
     */
    applyGestureToAvatar(gesture, agentType) {
        console.log(`Applying gesture '${gesture}' to ${agentType} avatar`);
        
        // Example Live2D gesture integration
        if (window.live2dAvatar) {
            // Map Healthcare AI gestures to Live2D motions
            const gestureMap = {
                'respectful_bow': 'bow_motion',
                'medical_consultation': 'explaining_gesture',
                'encouraging_smile': 'happy_wave',
                'emergency_stance': 'alert_posture',
                'heart_hands': 'heart_gesture',
                'tea_offering_gesture': 'welcoming_gesture'
            };
            
            const live2dMotion = gestureMap[gesture] || 'idle';
            window.live2dAvatar.playMotion(live2dMotion);
            
            // Cultural adaptation
            if (gesture.includes('cantonese') || gesture.includes('traditional')) {
                window.live2dAvatar.enableCulturalMode('hong_kong');
            }
        }
    }
    
    /**
     * Update avatar state
     */
    updateAvatarState(avatarState) {
        this.avatarState = { ...this.avatarState, ...avatarState };
        console.log('Avatar state updated:', this.avatarState);
        
        // Apply state to Live2D avatar
        if (window.live2dAvatar) {
            window.live2dAvatar.setState({
                energy: avatarState.energy_level || 0.5,
                speaking: avatarState.is_speaking || false,
                urgency: avatarState.urgency_level || 'low'
            });
        }
    }
    
    /**
     * Update voice settings
     */
    updateVoiceSettings(voiceSettings) {
        console.log('Voice settings updated:', voiceSettings);
        
        // Apply to TTS system
        if (window.speechSynthesis && window.currentVoice) {
            // Map Healthcare AI voice settings to Web Speech API
            const voice = window.speechSynthesis.getVoices().find(v => 
                v.lang.includes(this.config.language === 'zh-HK' ? 'zh' : 'en')
            );
            
            if (voice) {
                window.currentVoice.voice = voice;
                window.currentVoice.rate = this.mapPaceToRate(voiceSettings.pace);
                window.currentVoice.pitch = this.mapPitchToValue(voiceSettings.pitch);
                window.currentVoice.volume = this.mapVolumeToValue(voiceSettings.volume);
            }
        }
    }
    
    /**
     * Process animation cues
     */
    processAnimationCues(animationCues) {
        console.log('Processing animation cues:', animationCues);
        
        animationCues.forEach((cue, index) => {
            setTimeout(() => {
                this.executeAnimationCue(cue);
            }, index * 200); // Stagger animations
        });
    }
    
    /**
     * Execute single animation cue
     */
    executeAnimationCue(cue) {
        console.log(`Executing animation cue: ${cue}`);
        
        if (window.live2dAvatar) {
            switch (cue) {
                case 'alert_posture':
                    window.live2dAvatar.setPosture('alert');
                    break;
                case 'urgent_expression':
                    window.live2dAvatar.setExpression('urgent');
                    break;
                case 'attention_grabbing':
                    window.live2dAvatar.playEffect('attention_flash');
                    break;
                case 'medical_consultation_mode':
                    window.live2dAvatar.setMode('professional');
                    break;
                case 'supportive_mode':
                    window.live2dAvatar.setMode('caring');
                    break;
                default:
                    console.warn(`Unknown animation cue: ${cue}`);
            }
        }
    }
    
    /**
     * Display Hong Kong facilities
     */
    displayHKFacilities(facilities) {
        console.log('Displaying HK healthcare facilities:', facilities);
        
        // Example UI integration
        if (window.facilityDisplay) {
            const facilitiesHTML = facilities.map(facility => `
                <div class="facility-card" style="border-left: 4px solid ${facility.live2d_display.color}">
                    <div class="facility-header">
                        <span class="facility-icon">${facility.live2d_display.icon}</span>
                        <h3>${facility.name_zh || facility.name_en}</h3>
                        <span class="urgency-indicator urgency-${facility.live2d_display.urgency_indicator}">
                            ${facility.waiting_time || 'N/A'}
                        </span>
                    </div>
                    <p class="facility-address">${facility.address}</p>
                    <p class="facility-phone">${facility.phone}</p>
                </div>
            `).join('');
            
            window.facilityDisplay.innerHTML = facilitiesHTML;
        }
    }
    
    /**
     * Handle agent thinking indicator
     */
    handleAgentThinking(message) {
        console.log('Agent is thinking...');
        
        // Show thinking animation
        if (window.live2dAvatar) {
            window.live2dAvatar.showThinkingAnimation();
        }
        
        // Show typing indicator in UI
        if (window.chatInterface) {
            window.chatInterface.showTypingIndicator(message.agent_type || 'AI');
        }
    }
    
    /**
     * Handle system status
     */
    handleSystemStatus(message) {
        console.log('System status:', message.status);
        console.log('Available agents:', message.available_agents);
    }
    
    /**
     * Handle emergency alert
     */
    handleEmergencyAlert(message) {
        console.error('Emergency alert received:', message);
        
        // Show emergency UI
        this.showEmergencyAlert(message);
        
        // Apply emergency avatar state
        if (window.live2dAvatar) {
            window.live2dAvatar.setEmergencyMode(true);
            window.live2dAvatar.setExpression('urgent_concern');
            window.live2dAvatar.playMotion('alert_gesture');
        }
        
        this.emit('emergencyAlert', message);
    }
    
    /**
     * Show emergency alert UI
     */
    showEmergencyAlert(alertData) {
        // Create emergency alert overlay
        const alertOverlay = document.createElement('div');
        alertOverlay.className = 'emergency-alert-overlay';
        alertOverlay.innerHTML = `
            <div class="emergency-alert">
                <div class="alert-header">
                    <span class="alert-icon">🚨</span>
                    <h2>緊急警示 / Emergency Alert</h2>
                </div>
                <div class="alert-content">
                    <p class="alert-message">${alertData.message}</p>
                    <div class="alert-actions">
                        <h3>即時行動 / Immediate Actions:</h3>
                        <ul>
                            ${(alertData.immediate_actions || []).map(action => `<li>${action}</li>`).join('')}
                        </ul>
                    </div>
                    <div class="emergency-contacts">
                        <h3>緊急聯絡 / Emergency Contacts:</h3>
                        <div class="contact-buttons">
                            <button onclick="window.open('tel:999')" class="emergency-button">
                                📞 致電 999 / Call 999
                            </button>
                        </div>
                    </div>
                </div>
                <button onclick="this.parentElement.remove()" class="close-alert">關閉 / Close</button>
            </div>
        `;
        
        document.body.appendChild(alertOverlay);
        
        // Auto-remove after 30 seconds (but keep the call button accessible)
        setTimeout(() => {
            if (alertOverlay.parentElement) {
                alertOverlay.style.opacity = '0.8';
            }
        }, 30000);
    }
    
    /**
     * Handle error messages
     */
    handleError(message) {
        console.error('Healthcare AI error:', message);
        this.emit('error', { type: 'ai_error', message: message.message, code: message.error_code });
    }
    
    /**
     * Send message to Healthcare AI
     */
    sendMessage(text, options = {}) {
        if (!this.isConnected) {
            console.warn('Not connected to Healthcare AI. Queueing message.');
            this.messageQueue.push({ text, options });
            return;
        }
        
        const message = {
            type: 'user_message',
            message: text,
            language: options.language || this.config.language,
            session_id: this.sessionId,
            user_context: options.userContext || {},
            timestamp: new Date().toISOString()
        };
        
        console.log('Sending message to Healthcare AI:', message);
        this.ws.send(JSON.stringify(message));
        this.lastMessageTime = Date.now();
    }
    
    /**
     * Send typing start indicator
     */
    sendTypingStart() {
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'typing_start',
                session_id: this.sessionId,
                timestamp: new Date().toISOString()
            }));
        }
    }
    
    /**
     * Send typing stop indicator
     */
    sendTypingStop() {
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'typing_stop',
                session_id: this.sessionId,
                timestamp: new Date().toISOString()
            }));
        }
    }
    
    /**
     * Authenticate with token
     */
    authenticate(token) {
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'auth',
                token: token,
                timestamp: new Date().toISOString()
            }));
        }
        this.config.authToken = token;
    }
    
    /**
     * Get agent information via REST API
     */
    async getAgentInfo(agentType = null) {
        try {
            const url = agentType 
                ? `${this.config.apiUrl}/live2d/agents/${agentType}`
                : `${this.config.apiUrl}/live2d/agents`;
            
            const response = await fetch(url, {
                headers: {
                    'Accept': 'application/json',
                    'Accept-Language': this.config.language
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error fetching agent info:', error);
            throw error;
        }
    }
    
    /**
     * Get emotion mappings via REST API
     */
    async getEmotionMappings(agentType = null) {
        try {
            const url = agentType
                ? `${this.config.apiUrl}/live2d/emotions/${agentType}`
                : `${this.config.apiUrl}/live2d/emotions`;
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error fetching emotion mappings:', error);
            throw error;
        }
    }
    
    /**
     * Get gesture mappings via REST API
     */
    async getGestureMappings(filters = {}) {
        try {
            const params = new URLSearchParams(filters);
            const url = `${this.config.apiUrl}/live2d/gestures?${params}`;
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error fetching gesture mappings:', error);
            throw error;
        }
    }
    
    /**
     * Get system status via REST API
     */
    async getSystemStatus() {
        try {
            const response = await fetch(`${this.config.apiUrl}/live2d/status`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error fetching system status:', error);
            throw error;
        }
    }
    
    /**
     * Process queued messages
     */
    processMessageQueue() {
        while (this.messageQueue.length > 0) {
            const { text, options } = this.messageQueue.shift();
            this.sendMessage(text, options);
        }
    }
    
    /**
     * Start heartbeat
     */
    startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            if (this.isConnected) {
                this.ws.send(JSON.stringify({
                    type: 'ping',
                    timestamp: new Date().toISOString()
                }));
            }
        }, this.config.heartbeatInterval);
    }
    
    /**
     * Stop heartbeat
     */
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    /**
     * Schedule reconnection
     */
    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = Math.min(this.config.reconnectInterval * this.reconnectAttempts, 30000);
        
        console.log(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            if (!this.isConnected) {
                console.log(`Reconnection attempt ${this.reconnectAttempts}`);
                this.connect();
            }
        }, delay);
    }
    
    /**
     * Handle connection error
     */
    handleConnectionError(error) {
        console.error('Connection error:', error);
        this.emit('error', { type: 'connection_error', error });
        
        if (this.reconnectAttempts < this.config.maxReconnectAttempts) {
            this.scheduleReconnect();
        }
    }
    
    /**
     * Add event listener
     */
    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);
    }
    
    /**
     * Remove event listener
     */
    off(event, handler) {
        if (this.eventHandlers[event]) {
            const index = this.eventHandlers[event].indexOf(handler);
            if (index > -1) {
                this.eventHandlers[event].splice(index, 1);
            }
        }
    }
    
    /**
     * Emit event
     */
    emit(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }
    
    /**
     * Disconnect
     */
    disconnect() {
        if (this.ws) {
            this.ws.close(1000, 'Manual disconnect');
        }
        this.stopHeartbeat();
        this.isConnected = false;
    }
    
    /**
     * Get connection statistics
     */
    getStats() {
        return {
            isConnected: this.isConnected,
            sessionId: this.sessionId,
            messageCount: this.messageCount,
            averageResponseTime: this.getAverageResponseTime(),
            reconnectAttempts: this.reconnectAttempts,
            queuedMessages: this.messageQueue.length,
            currentAgent: this.currentAgent,
            currentEmotion: this.currentEmotion,
            currentGesture: this.currentGesture
        };
    }
    
    /**
     * Get average response time
     */
    getAverageResponseTime() {
        return this.messageCount > 0 ? Math.round(this.totalResponseTime / this.messageCount) : 0;
    }
    
    /**
     * Utility: Map pace to speech rate
     */
    mapPaceToRate(pace) {
        const paceMap = {
            'slow': 0.7,
            'moderate': 1.0,
            'moderate_fast': 1.2,
            'fast': 1.5,
            'upbeat': 1.3
        };
        return paceMap[pace] || 1.0;
    }
    
    /**
     * Utility: Map pitch to speech pitch
     */
    mapPitchToValue(pitch) {
        const pitchMap = {
            'soft_high': 1.2,
            'bright_high': 1.3,
            'medium': 1.0,
            'strong_medium': 0.9
        };
        return pitchMap[pitch] || 1.0;
    }
    
    /**
     * Utility: Map volume to speech volume
     */
    mapVolumeToValue(volume) {
        const volumeMap = {
            'quiet': 0.6,
            'normal': 0.8,
            'normal_high': 0.9,
            'loud': 1.0,
            'cheerful': 0.9
        };
        return volumeMap[volume] || 0.8;
    }
}

// Example usage
const client = new HealthcareAILive2DClient({
    wsUrl: 'ws://localhost:8000/ws/live2d/chat',
    apiUrl: 'http://localhost:8000/api/v1',
    language: 'zh-HK',
    clientType: 'live2d'
});

// Event handlers
client.on('connected', () => {
    console.log('✅ Connected to Healthcare AI');
});

client.on('agentResponse', (data) => {
    console.log(`🤖 ${data.agentName}: ${data.message}`);
    
    // Speak the response if TTS is available
    if (window.speechSynthesis) {
        const utterance = new SpeechSynthesisUtterance(data.message);
        utterance.lang = data.language === 'zh-HK' ? 'zh-HK' : 'en-US';
        window.speechSynthesis.speak(utterance);
    }
});

client.on('emotionChange', (data) => {
    console.log(`😊 Emotion: ${data.oldEmotion} → ${data.newEmotion}`);
});

client.on('gestureChange', (data) => {
    console.log(`👋 Gesture: ${data.oldGesture} → ${data.newGesture}`);
});

client.on('emergencyAlert', (data) => {
    console.log('🚨 Emergency Alert:', data.message);
});

client.on('error', (data) => {
    console.error('❌ Error:', data);
});

// Example functions for UI integration
function sendChatMessage() {
    const input = document.getElementById('chatInput');
    if (input && input.value.trim()) {
        client.sendMessage(input.value.trim());
        input.value = '';
    }
}

function setupTypingIndicators() {
    const input = document.getElementById('chatInput');
    if (input) {
        let typingTimer;
        
        input.addEventListener('input', () => {
            client.sendTypingStart();
            
            clearTimeout(typingTimer);
            typingTimer = setTimeout(() => {
                client.sendTypingStop();
            }, 1000);
        });
    }
}

// Initialize UI integration
document.addEventListener('DOMContentLoaded', () => {
    setupTypingIndicators();
    
    // Add chat input handler
    const chatForm = document.getElementById('chatForm');
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            sendChatMessage();
        });
    }
    
    // Load initial agent info
    client.getAgentInfo().then(agents => {
        console.log('Available agents:', agents);
    }).catch(console.error);
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HealthcareAILive2DClient;
} else if (typeof window !== 'undefined') {
    window.HealthcareAILive2DClient = HealthcareAILive2DClient;
}
