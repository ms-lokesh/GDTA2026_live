(function () {
    'use strict';

    const phoneDisplay = '9840819991';
    const whatsappUrl = 'https://wa.me/919840819991';
    const locationUrl = 'https://maps.app.goo.gl/UZyU6BnXNwUskeCq8';
    const currentPath = window.location.pathname.replace(/\/$/, '');
    const isHomePage = currentPath === '' || currentPath.endsWith('/index') || currentPath.endsWith('/index.html');

    const style = document.createElement('style');
    style.textContent = `
        .gdta-whatsapp-widget { position: fixed; right: 24px; bottom: 24px; z-index: 1250; font-family: inherit; }
        .gdta-whatsapp-widget.gdta-home-actions { display: flex; align-items: center; gap: 12px; }
        .gdta-whatsapp-link, .gdta-whatsapp-toggle { display: flex; align-items: center; justify-content: center; gap: 12px; border: 0; border-radius: 999px; background: #25d366; color: #073b1d; box-shadow: 0 8px 24px rgba(0,0,0,.24); text-decoration: none; cursor: pointer; transition: transform .2s ease, box-shadow .2s ease; }
        .gdta-whatsapp-link:hover, .gdta-whatsapp-toggle:hover { color: #073b1d; transform: translateY(-3px); box-shadow: 0 12px 28px rgba(0,0,0,.28); }
        .gdta-whatsapp-link:focus-visible, .gdta-whatsapp-toggle:focus-visible, .gdta-whatsapp-card a:focus-visible { outline: 3px solid #128c4a; outline-offset: 3px; }
        .gdta-whatsapp-link { width: 58px; height: 58px; padding: 0; color: #fff; }
        .gdta-whatsapp-icon { font-size: 34px; line-height: 1; animation: gdta-whatsapp-flash 2.4s ease-in-out infinite; }
        .gdta-whatsapp-link:hover { color: #fff; }
        .gdta-whatsapp-toggle { position: relative; isolation: isolate; width: 58px; height: 58px; padding: 0; font-size: 32px; }
        .gdta-whatsapp-toggle .fa-whatsapp { animation: gdta-whatsapp-flash 2.4s ease-in-out infinite; }
        .gdta-whatsapp-toggle::before, .gdta-whatsapp-toggle::after { content: ''; position: absolute; z-index: -1; inset: -5px; border: 3px solid #25d366; border-radius: 50%; pointer-events: none; animation: gdta-whatsapp-ring 1.8s ease-out infinite; }
        .gdta-whatsapp-toggle::after { animation-delay: .9s; }
        .gdta-location-link { display: flex; width: 58px; height: 58px; align-items: center; justify-content: center; border-radius: 50%; background: #fff; color: #d93025; box-shadow: 0 8px 24px rgba(0,0,0,.24); font-size: 27px; text-decoration: none; transition: transform .2s ease, box-shadow .2s ease; }
        .gdta-location-link:hover { color: #b3261e; transform: translateY(-3px); box-shadow: 0 12px 28px rgba(0,0,0,.28); }
        .gdta-location-link:focus-visible { outline: 3px solid #d93025; outline-offset: 3px; }
        .gdta-whatsapp-card { position: absolute; right: 0; bottom: 72px; width: 260px; padding: 18px; border: 1px solid #e5e7eb; border-radius: 16px; background: #fff; color: #1f2937; box-shadow: 0 12px 35px rgba(0,0,0,.2); }
        .gdta-whatsapp-card[hidden] { display: none; }
        .gdta-whatsapp-card p { margin: 0 0 12px; font-weight: 600; }
        .gdta-whatsapp-card a { display: block; color: #128c4a; font-size: 18px; font-weight: 800; text-decoration: none; }
        .gdta-whatsapp-card a:hover { text-decoration: underline; }
        @keyframes gdta-whatsapp-flash { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: .78; transform: scale(1.06); } }
        @keyframes gdta-whatsapp-ring { 0% { transform: scale(.86); opacity: .95; } 75%, 100% { transform: scale(1.55); opacity: 0; } }
        @media (max-width: 575px) { .gdta-whatsapp-widget { right: 16px; bottom: 16px; } .gdta-whatsapp-widget.gdta-home-actions { gap: 10px; } .gdta-whatsapp-card { width: min(260px, calc(100vw - 32px)); } }
        @media (prefers-reduced-motion: reduce) { .gdta-whatsapp-link, .gdta-whatsapp-toggle, .gdta-location-link { transition: none; } .gdta-whatsapp-icon, .gdta-whatsapp-toggle .fa-whatsapp, .gdta-whatsapp-toggle::before, .gdta-whatsapp-toggle::after { animation: none; } }
    `;
    document.head.appendChild(style);

    function addWidget() {
        if (document.querySelector('.gdta-whatsapp-widget')) return;

        const widget = document.createElement('div');
        widget.className = 'gdta-whatsapp-widget';

        if (isHomePage) {
            widget.classList.add('gdta-home-actions');
            widget.innerHTML = '<button class="gdta-whatsapp-toggle gdta-whatsapp-link" type="button" aria-label="Show contact number" aria-expanded="false" aria-controls="gdta-whatsapp-card"><i class="fa-brands fa-whatsapp gdta-whatsapp-icon" aria-hidden="true"></i></button><a class="gdta-location-link" href="' + locationUrl + '" target="_blank" rel="noopener noreferrer" aria-label="Open GDTA event location in Google Maps"><i class="fa-solid fa-location-dot" aria-hidden="true"></i></a><div class="gdta-whatsapp-card" id="gdta-whatsapp-card" hidden><p>Contact us</p><a href="' + whatsappUrl + '" target="_blank" rel="noopener noreferrer">' + phoneDisplay + '</a></div>';
        } else {
            widget.innerHTML = '<button class="gdta-whatsapp-toggle" type="button" aria-label="Show contact number" aria-expanded="false" aria-controls="gdta-whatsapp-card"><i class="fa-brands fa-whatsapp" aria-hidden="true"></i></button><div class="gdta-whatsapp-card" id="gdta-whatsapp-card" hidden><p>Contact us</p><a href="' + whatsappUrl + '" target="_blank" rel="noopener noreferrer">' + phoneDisplay + '</a></div>';
        }

        const toggle = widget.querySelector('.gdta-whatsapp-toggle');
        const card = widget.querySelector('.gdta-whatsapp-card');

        toggle.addEventListener('click', function () {
            const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
            toggle.setAttribute('aria-expanded', String(!isExpanded));
            card.hidden = isExpanded;
        });
        document.addEventListener('click', function (event) {
            if (!widget.contains(event.target)) {
                toggle.setAttribute('aria-expanded', 'false');
                card.hidden = true;
            }
        });
        widget.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                toggle.setAttribute('aria-expanded', 'false');
                card.hidden = true;
                toggle.focus();
            }
        });

        document.body.appendChild(widget);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addWidget, { once: true });
    } else {
        addWidget();
    }
})();
