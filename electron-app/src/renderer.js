// DOM elements
const authSection = document.getElementById('auth-section');
const chatSection = document.getElementById('chat-section');
const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const messagesDiv = document.getElementById('messages');
const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');

let currentConversationId = null;

// Initialize
async function init() {
    console.log('Renderer initialized');

    // Check auth status
    await updateAuthStatus();

    // Listen to auth status updates from main process
    window.electronAPI.onAuthStatus((data) => {
        console.log('Auth status update:', data);
        handleAuthStatusUpdate(data);
    });

    // Event listeners
    loginBtn.addEventListener('click', handleLogin);
    logoutBtn.addEventListener('click', handleLogout);
    sendBtn.addEventListener('click', handleSendMessage);

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
}

// Update auth status
async function updateAuthStatus() {
    const status = await window.electronAPI.getAuthStatus();
    console.log('Auth status:', status);

    if (status.authenticated) {
        showChatSection();
        updateStatus('connected', 'Připojeno');
    } else {
        showAuthSection();
        updateStatus('disconnected', 'Nepřihlášen');
    }
}

// Handle auth status updates
function handleAuthStatusUpdate(data) {
    const { status, message } = data;

    if (status === 'success') {
        updateStatus('connected', message);
        showChatSection();
        addSystemMessage(message);
    } else if (status === 'error') {
        updateStatus('disconnected', message);
        addSystemMessage(`❌ ${message}`, true);
    } else if (status === 'waiting') {
        updateStatus('waiting', message);
        addSystemMessage(message);
    } else if (status === 'info') {
        updateStatus('disconnected', message);
        showAuthSection();
        addSystemMessage(message);
    }
}

// Update status indicator
function updateStatus(status, text) {
    statusIndicator.className = `status-indicator ${status}`;
    statusText.textContent = text;

    if (status === 'connected') {
        logoutBtn.style.display = 'inline-block';
    } else {
        logoutBtn.style.display = 'none';
    }
}

// Show auth section
function showAuthSection() {
    authSection.style.display = 'flex';
    chatSection.style.display = 'none';
}

// Show chat section
function showChatSection() {
    authSection.style.display = 'none';
    chatSection.style.display = 'flex';
    messageInput.focus();
}

// Handle login
async function handleLogin() {
    console.log('Login button clicked');
    await window.electronAPI.startLogin();
    addSystemMessage('Otevírám prohlížeč pro přihlášení...');
}

// Handle logout
async function handleLogout() {
    console.log('Logout button clicked');
    const result = await window.electronAPI.logout();

    if (result.success) {
        // Clear messages
        messagesDiv.innerHTML = '<div class="system-message">Odhlášeno</div>';
        currentConversationId = null;
        showAuthSection();
    }
}

// Handle send message
async function handleSendMessage() {
    const message = messageInput.value.trim();

    if (!message) {
        return;
    }

    // Disable input
    messageInput.disabled = true;
    sendBtn.disabled = true;

    // Add user message to UI
    addMessage('user', message);

    // Clear input
    messageInput.value = '';

    try {
        // Call API
        const result = await window.electronAPI.sendMessage(message);

        if (result.success) {
            const { response, conversation_id, user_email } = result.data;

            // Update conversation ID
            currentConversationId = conversation_id;

            // Add assistant response
            addMessage('assistant', response, user_email);
        } else {
            addSystemMessage(`❌ Chyba: ${result.error}`, true);
        }
    } catch (error) {
        console.error('Send message error:', error);
        addSystemMessage(`❌ Chyba při odesílání: ${error.message}`, true);
    } finally {
        // Re-enable input
        messageInput.disabled = false;
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

// Add message to UI
function addMessage(role, content, email = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    messageDiv.appendChild(contentDiv);

    // Add info for assistant messages
    if (role === 'assistant' && email) {
        const infoDiv = document.createElement('div');
        infoDiv.className = 'message-info';
        infoDiv.textContent = `User: ${email}`;
        messageDiv.appendChild(infoDiv);
    }

    messagesDiv.appendChild(messageDiv);

    // Scroll to bottom
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Add system message
function addSystemMessage(text, isError = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'system-message';
    messageDiv.textContent = text;

    if (isError) {
        messageDiv.style.color = '#ff6b6b';
    }

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Initialize on load
init();
