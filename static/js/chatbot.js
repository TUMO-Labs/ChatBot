const chatToggle       = document.getElementById('chat-toggle');
const chatWidget       = document.getElementById('chat-widget');
const chatWindow       = document.getElementById('chat-window');
const optionsContainer = document.getElementById('options-container');
const usernameGate     = document.getElementById('username-gate');
const usernameInput    = document.getElementById('username-input');
const usernameSubmit   = document.getElementById('username-submit');
const messageInput     = document.getElementById('message-input');

let currentUsername = sessionStorage.getItem('username') || null;
let notificationSent = sessionStorage.getItem('notification_sent') === 'true';
function generateUUID() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
}
let sessionId = sessionStorage.getItem('session_id') || generateUUID();
sessionStorage.setItem('session_id', sessionId);
const socket = io({ transports: ['polling', 'websocket'], upgrade: true });

function _saveMessage(type, text) {
    const msgs = JSON.parse(sessionStorage.getItem('chat_messages') || '[]');
    msgs.push({ type, text });
    sessionStorage.setItem('chat_messages', JSON.stringify(msgs));
}

function _restoreChat() {
    usernameGate.style.display = 'none';
    chatWindow.style.display = '';
    optionsContainer.style.display = '';
    const msgs = JSON.parse(sessionStorage.getItem('chat_messages') || '[]');
    msgs.forEach(m => {
        const div = document.createElement('div');
        div.className = `message ${m.type === 'bot' ? 'bot-msg' : 'user-msg'}`;
        div.innerText = m.text;
        chatWindow.appendChild(div);
    });
    chatWindow.scrollTop = chatWindow.scrollHeight;
    addFreeTextInput();
}

if (notificationSent && currentUsername) {
    _restoreChat();
}

// When owner replies via Telegram → show in chat instantly
socket.on('bot_reply', data => {
    console.log(`[bot_reply] seq=${data.seq} msg=${data.message}`);
    appendBotMessage(data.message);
});

// Rejoin room automatically on reconnect so replies keep working
socket.on('connect', () => {
    if (sessionId) socket.emit('join', { session_id: sessionId });
});

// Server tells us if it recognises this session (e.g. after server restart)
socket.on('session_status', ({ known }) => {
    if (!known && notificationSent) {
        // Server lost state — clear everything and ask for name again
        sessionStorage.clear();
        location.reload();
    }
});


chatToggle.onclick = () => {
    chatWidget.classList.toggle('active');
};

async function sendNotification(message) {
    if (notificationSent) return;
    notificationSent = true;
    sessionStorage.setItem('notification_sent', 'true');
    try {
        const res = await fetch('/notify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: currentUsername, message, session_id: sessionId })
        });
        if (res.status === 429) {
            console.warn('Notification rate limited — chat still active');
        }
    } catch (e) {
        console.warn('Notification failed:', e);
    }
}

function appendBotMessage(text) {
    const div = document.createElement('div');
    div.className = 'message bot-msg';
    div.innerText = text;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    _saveMessage('bot', text);
}

usernameSubmit.onclick = startChat;
usernameInput.addEventListener('keydown', e => { if (e.key === 'Enter') messageInput.focus(); });

function startChat() {
    const name = usernameInput.value.trim();
    if (!name) { usernameInput.focus(); return; }
    currentUsername = name;
    sessionStorage.setItem('username', currentUsername);
    const firstMessage = messageInput.value.trim() || 'Opened chat';
    usernameGate.style.display = 'none';
    chatWindow.style.display = '';
    optionsContainer.style.display = '';
    sendNotification(firstMessage);
    socket.emit('join', { session_id: sessionId });
    appendBotMessage(`Hi ${currentUsername}! Your message has been sent. I'll get back to you shortly! 💬`);
    renderStep('start');
    addFreeTextInput();
}

function addFreeTextInput() {
    const wrapper = document.createElement('div');
    wrapper.className = 'free-text-wrapper';

    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Type a message...';
    input.className = 'free-text-input';

    const btn = document.createElement('button');
    btn.innerText = '➤';
    btn.className = 'free-text-btn';

    async function sendFreeMessage() {
        const text = input.value.trim();
        if (!text) return;
        input.value = '';

        const userDiv = document.createElement('div');
        userDiv.className = 'message user-msg';
        userDiv.innerText = text;
        chatWindow.appendChild(userDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        _saveMessage('user', text);

        await fetch('/send-message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, message: text })
        });
    }

    btn.onclick = sendFreeMessage;
    input.addEventListener('keydown', e => { if (e.key === 'Enter') sendFreeMessage(); });

    wrapper.appendChild(input);
    wrapper.appendChild(btn);
    chatWidget.appendChild(wrapper);
}

async function renderStep(stepKey) {
    optionsContainer.innerHTML = '';

    // Typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-msg typing-indicator';
    typingDiv.innerHTML = '<span></span><span></span><span></span>';
    chatWindow.appendChild(typingDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;

    const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ next: stepKey })
    });
    const data = await response.json();

    // Small delay so typing indicator is visible
    await new Promise(r => setTimeout(r, 600));
    chatWindow.removeChild(typingDiv);

    if (data.bot) {
        const botDiv = document.createElement('div');
        botDiv.className = 'message bot-msg';
        // Linkify /static/... paths
        botDiv.innerHTML = data.bot.replace(
            /\/static\/\S+/g,
            '<a href="$&" target="_blank" style="color:#6366f1;">$&</a>'
        );
        chatWindow.appendChild(botDiv);
        _saveMessage('bot', data.bot);
    }

    data.options.forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'opt-btn';
        btn.innerText = opt.text;
        btn.onclick = () => {
            sendNotification(opt.text);

            const userDiv = document.createElement('div');
            userDiv.className = 'message user-msg';
            userDiv.innerText = opt.text;
            chatWindow.appendChild(userDiv);
            _saveMessage('user', opt.text);

            setTimeout(() => renderStep(opt.next), 400);
        };
        optionsContainer.appendChild(btn);
    });

    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Scroll fade-in for .fade-in elements
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.15 });

document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));