const chatToggle       = document.getElementById('chat-toggle');
const chatWidget       = document.getElementById('chat-widget');
const chatWindow       = document.getElementById('chat-window');
const optionsContainer = document.getElementById('options-container');
const usernameGate     = document.getElementById('username-gate');
const usernameInput    = document.getElementById('username-input');
const usernameSubmit   = document.getElementById('username-submit');
const messageInput     = document.getElementById('message-input');

let currentUsername = null;
let notificationSent = false;

chatToggle.onclick = () => {
    chatWidget.classList.toggle('active');
};

async function sendNotification(message) {
    if (notificationSent) return;
    notificationSent = true;
    try {
        await fetch('/notify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: currentUsername, message })
        });
    } catch (e) {
        console.warn('Notification failed:', e);
    }
}

usernameSubmit.onclick = startChat;
usernameInput.addEventListener('keydown', e => { if (e.key === 'Enter') messageInput.focus(); });

function startChat() {
    const name = usernameInput.value.trim();
    if (!name) { usernameInput.focus(); return; }
    currentUsername = name;
    const firstMessage = messageInput.value.trim() || 'Opened chat';
    usernameGate.style.display = 'none';
    chatWindow.style.display = '';
    optionsContainer.style.display = '';
    sendNotification(firstMessage);
    renderStep('start');
}

async function renderStep(stepKey) {
    optionsContainer.innerHTML = ''; 

    const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ next: stepKey })
    });
    const data = await response.json();

    const botDiv = document.createElement('div');
    botDiv.className = 'message bot-msg';
    botDiv.innerText = data.bot;
    chatWindow.appendChild(botDiv);

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

            setTimeout(() => renderStep(opt.next), 400);
        };
        optionsContainer.appendChild(btn);
    });

    chatWindow.scrollTop = chatWindow.scrollHeight;
}