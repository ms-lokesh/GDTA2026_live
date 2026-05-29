/**
 * GDTA 2026 Chatbot Widget
 * Floating chatbot button that opens the conference assistant
 */

(function() {
    // Create and inject widget HTML
    const widgetHTML = `
        <style>
            .chatbot-widget-container{position:fixed;bottom:20px;right:20px;z-index:9999;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif}.chatbot-button{width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);box-shadow:0 4px 20px rgba(102,126,234,.4);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .3s ease;position:relative;overflow:hidden}.chatbot-button:hover{transform:scale(1.1);box-shadow:0 6px 30px rgba(102,126,234,.6)}.chatbot-button:active{transform:scale(.95)}.chatbot-button-icon{width:30px;height:30px;fill:white;transition:all .3s ease}.chatbot-button.open .chatbot-button-icon{transform:rotate(180deg)}@keyframes pulse{0%,100%{box-shadow:0 4px 20px rgba(102,126,234,.4)}50%{box-shadow:0 4px 30px rgba(102,126,234,.8)}}.chatbot-button.pulse{animation:pulse 2s infinite}.chatbot-window{position:fixed;bottom:90px;right:20px;width:400px;height:600px;background:white;border-radius:15px;box-shadow:0 10px 40px rgba(0,0,0,.2);display:none;flex-direction:column;overflow:hidden;transition:all .3s ease;opacity:0;transform:translateY(20px)}.chatbot-window.open{display:flex;opacity:1;transform:translateY(0)}.chatbot-close-btn{background:rgba(255,255,255,.2);border:none;color:white;width:30px;height:30px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .2s ease}.chatbot-close-btn:hover{background:rgba(255,255,255,.3);transform:rotate(90deg)}.chatbot-iframe{width:100%;height:100%;border:none;flex:1}@media (max-width:768px){.chatbot-window{width:calc(100vw - 40px);height:calc(100vh - 140px);right:20px;bottom:90px}.chatbot-widget-container{bottom:15px;right:15px}.chatbot-button{width:55px;height:55px}}.chatbot-notification-badge{position:absolute;top:-5px;right:-5px;background:#ff4444;color:white;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.7em;font-weight:bold;animation:bounceIn .5s ease}@keyframes bounceIn{0%{transform:scale(0)}50%{transform:scale(1.2)}100%{transform:scale(1)}}
        </style>
        <div class="chatbot-widget-container" id="chatbotWidget">
            <button class="chatbot-button pulse" id="chatbotButton" aria-label="Open GDTA Chatbot">
                <svg class="chatbot-button-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12c0 1.54.36 3 .97 4.29L2 22l5.71-.97C9 21.64 10.46 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm0 18c-1.38 0-2.67-.31-3.83-.86l-.27-.15-2.83.48.48-2.83-.15-.27C4.31 14.67 4 13.38 4 12c0-4.41 3.59-8 8-8s8 3.59 8 8-3.59 8-8 8zm4-10h-2v-2c0-.55-.45-1-1-1s-1 .45-1 1v2H9c-.55 0-1 .45-1 1s.45 1 1 1h3v3c0 .55.45 1 1 1s1-.45 1-1v-3h2c.55 0 1-.45 1-1s-.45-1-1-1z"/>
                </svg>
            </button>
            <div class="chatbot-window" id="chatbotWindow">
                <iframe class="chatbot-iframe" id="chatbotIframe" src="./chatbot.html" title="GDTA 2026 Chatbot" allow="cross-origin"></iframe>
            </div>
        </div>
    `;

    // Inject widget when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidget);
    } else {
        initWidget();
    }

    function initWidget() {
        // Insert widget HTML
        document.body.insertAdjacentHTML('beforeend', widgetHTML);
        
        console.log('Chatbot widget initialized');

        // Initialize functionality
        const chatbotButton = document.getElementById('chatbotButton');
        const chatbotWindow = document.getElementById('chatbotWindow');
        const chatbotIframe = document.getElementById('chatbotIframe');
        
        console.log('Chatbot elements:', { chatbotButton, chatbotWindow, chatbotIframe });
        
        let isOpen = false;

        // Toggle chatbot window
        function toggleChatbot() {
            isOpen = !isOpen;
            console.log('Toggle chatbot, isOpen:', isOpen);
            
            if (isOpen) {
                chatbotWindow.classList.add('open');
                chatbotButton.classList.add('open');
                chatbotButton.classList.remove('pulse');
                console.log('Iframe src:', chatbotIframe.src);
            } else {
                chatbotWindow.classList.remove('open');
                chatbotButton.classList.remove('open');
            }
        }

        // Event Listeners
        if (chatbotButton) chatbotButton.addEventListener('click', toggleChatbot);

        // Close on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && isOpen) {
                toggleChatbot();
            }
        });

        // Stop pulse animation after first interaction
        if (chatbotButton) {
            chatbotButton.addEventListener('click', function() {
                setTimeout(() => {
                    chatbotButton.classList.remove('pulse');
                }, 3000);
            }, { once: true });
        }
    }
})();
