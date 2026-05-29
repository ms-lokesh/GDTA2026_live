// GDTA 2026 Reusable Success Modal
function showSuccessModal(title, message, onCloseCallback) {
    if (!document.getElementById('gdta-modal-styles')) {
        const style = document.createElement('style');
        style.id = 'gdta-modal-styles';
        style.innerHTML = `
            .gdta-modal-overlay {
                position: fixed;
                top: 0; left: 0;
                width: 100%; height: 100%;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center; justify-content: center;
                z-index: 11000;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            .gdta-modal-box {
                background: #1e1b4b;
                border: 2px solid #F59E0B;
                border-radius: 15px;
                padding: 30px;
                max-width: 500px;
                width: 90%;
                color: #ffffff;
                text-align: center;
                box-shadow: 0 10px 30px rgba(245, 158, 11, 0.3);
                transform: translateY(-20px);
                transition: transform 0.3s ease;
                font-family: 'Montserrat', sans-serif;
            }
            .gdta-modal-title {
                color: #F59E0B;
                font-size: 24px;
                font-weight: 800;
                margin-bottom: 15px;
                text-transform: uppercase;
            }
            .gdta-modal-message {
                font-size: 16px;
                line-height: 1.5;
                margin-bottom: 25px;
                color: #e2e8f0;
            }
            .gdta-modal-close-btn {
                background: linear-gradient(135deg, #0D9488 0%, #1E1B4B 100%);
                color: #ffffff;
                border: none;
                padding: 10px 25px;
                font-weight: 700;
                border-radius: 25px;
                cursor: pointer;
                text-transform: uppercase;
                transition: all 0.3s ease;
            }
            .gdta-modal-close-btn:hover {
                transform: scale(1.05);
                box-shadow: 0 5px 15px rgba(13, 148, 136, 0.4);
            }
        `;
        document.head.appendChild(style);
    }

    const overlay = document.createElement('div');
    overlay.className = 'gdta-modal-overlay';
    
    const box = document.createElement('div');
    box.className = 'gdta-modal-box';
    
    const titleEl = document.createElement('h3');
    titleEl.className = 'gdta-modal-title';
    titleEl.textContent = title;
    
    const msgEl = document.createElement('p');
    msgEl.className = 'gdta-modal-message';
    msgEl.textContent = message;
    
    const btn = document.createElement('button');
    btn.className = 'gdta-modal-close-btn';
    btn.textContent = 'Close';
    
    box.appendChild(titleEl);
    box.appendChild(msgEl);
    box.appendChild(btn);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    
    setTimeout(() => {
        overlay.style.opacity = '1';
        box.style.transform = 'translateY(0)';
    }, 10);
    
    function closeModal() {
        overlay.style.opacity = '0';
        box.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            overlay.remove();
            if (onCloseCallback) onCloseCallback();
        }, 300);
    }
    
    btn.addEventListener('click', closeModal);
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
            closeModal();
        }
    });
}
