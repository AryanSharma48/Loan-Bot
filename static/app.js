// Wait for the DOM to be fully loaded before running the script
document.addEventListener('DOMContentLoaded', () => {

    // --- Get references to all the HTML elements we'll need ---
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');
    const typingIndicator = document.getElementById('typing-indicator');

    // --- This is the "memory" of the conversation ---
    // We must send this history back to the AI every time
    // so it remembers what was said.
    let chatHistory = [];

    // --- BONUS: Voice-to-Text (Speech Recognition) ---
    // Check if the browser supports the Web Speech API
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false; // Stop recording after a pause
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        micBtn.addEventListener('click', () => {
            micBtn.classList.toggle('recording');
            recognition.start();
        });

        // When speech is recognized
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            chatInput.value = transcript; // Put the spoken text into the input
            sendMessage(); // Automatically send the message
        };

        recognition.onend = () => {
            micBtn.classList.remove('recording');
        };

    } else {
        micBtn.style.display = 'none'; // Hide the mic button if not supported
    }

    // --- BONUS: Text-to-Speech (Bot Talking) ---
    function speak(text) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        // You can pick a voice.
        // let voices = window.speechSynthesis.getVoices();
        // utterance.voice = voices.find(v => v.name === "Google US English");
        window.speechSynthesis.speak(utterance);
    }


    // --- Main function to send a message ---
    const sendMessage = async () => {
        const messageText = chatInput.value.trim();
        if (!messageText) return; // Don't send empty messages

        // 1. Display the user's message immediately
        addMessage(messageText, 'user');

        // Add user message to history
        chatHistory.push({ role: "user", parts: [{ text: messageText }] });

        // Clear the input and show typing indicator
        chatInput.value = '';
        typingIndicator.classList.remove('hidden');
        sendBtn.disabled = true;

        try {
            // 2. Send the message and the *entire* history to our Python server
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: messageText,
                    history: chatHistory
                })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            const botReply = data.reply;

            // 3. Add the bot's reply to the chat
            addMessage(botReply, 'bot');

            // 4. Add the bot's reply to our history
            chatHistory.push({ role: "model", parts: [{ text: botReply }] });

            // 5. BONUS: Speak the bot's reply
            speak(botReply);

        } catch (error) {
            console.error('Error:', error);
            addMessage('Error: Could not get a response from the server.', 'bot');
        } finally {
            // Hide typing indicator
            typingIndicator.classList.add('hidden');
            sendBtn.disabled = false;
        }
    };

    // --- Helper function to add a message to the chat window ---
    function addMessage(text, sender) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender}`;

        // This is a small security measure to prevent HTML injection
        // messageElement.innerText = text; 

        // We need to allow HTML for the download link.
        // In a real app, you'd "sanitize" this.
        messageElement.innerHTML = text;

        chatMessages.appendChild(messageElement);

        // Scroll to the bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // --- Event Listeners ---
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Send a welcome message when the chat loads
    const welcomeMessage = "Hi there! I'm Fin, your personal loan assistant. To get started, could you please tell me your first name (e.g., Alice, Bob, Charlie...)?";
    addMessage(welcomeMessage, 'bot');
    chatHistory.push({ role: "model", parts: [{ text: welcomeMessage }] });
    speak(welcomeMessage);
});
