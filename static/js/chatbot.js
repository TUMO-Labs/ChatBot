const chatToggle = document.getElementById('chat-toggle');
const chatWidget = document.getElementById('chat-widget');
const chatWindow = document.getElementById('chat-window');
const optionsContainer = document.getElementById('options-container');

chatToggle.onclick = () => {
    chatWidget.classList.toggle('active');
};

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

renderStep('start');