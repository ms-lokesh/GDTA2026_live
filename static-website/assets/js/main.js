(function ($) {
    "use strict";

    // Spinner
    var spinner = function () {
        setTimeout(function () {
            if ($('#spinner').length > 0) {
                $('#spinner').removeClass('show');
            }
        }, 1);
    };
    spinner();
    
    
    // Initiate the wowjs
    new WOW().init();


    // Smooth scrolling for anchor links - DISABLED for multi-page navigation
    // Multi-page website uses separate HTML files instead of anchor scrolling
    /*
    $('a[href^="#"]').on('click', function (e) {
        var target = $(this.hash);
        if (target.length) {
            e.preventDefault();
            $('html, body').animate({
                scrollTop: target.offset().top - 70
            }, 1000, 'easeInOutExpo');
        }
    });
    */


    // Sticky Navbar
    $(window).scroll(function () {
        if ($(this).scrollTop() > 0) {
            $('.navbar').addClass('position-fixed bg-dark shadow-sm');
        } else {
            $('.navbar').removeClass('position-fixed bg-dark shadow-sm');
        }
    });
    
    
    // Back to top button
    $(window).scroll(function () {
        if ($(this).scrollTop() > 300) {
            $('.back-to-top').fadeIn('slow');
        } else {
            $('.back-to-top').fadeOut('slow');
        }
    });
    $('.back-to-top').click(function () {
        $('html, body').animate({scrollTop: 0}, 1500, 'easeInOutExpo');
        return false;
    });


    // Testimonials carousel (only if OwlCarousel plugin is loaded)
    if ($.fn && typeof $.fn.owlCarousel === 'function' && $('.testimonial-carousel').length) {
        $('.testimonial-carousel').owlCarousel({
            autoplay: true,
            smartSpeed: 1000,
            loop: true,
            nav: false,
            dots: true,
            items: 1,
            dotsData: true,
        });
    }

    // Floating register tag (sitewide)
    $(function () {
        if (document.getElementById('gdta-register-tag')) return;

        var styleEl = document.createElement('style');
        styleEl.textContent = "\n#gdta-register-tag{position:fixed;right:-2px;top:50%;transform:translateY(-50%);transform-origin:top center;z-index:1200;background:#000;color:#fff;text-decoration:none;padding:12px 10px;font-weight:700;letter-spacing:.4px;border-radius:12px 0 0 12px;box-shadow:0 10px 24px rgba(0,0,0,.2);transition:transform .2s ease,box-shadow .2s ease,background .2s ease;animation:swing-cta 3.5s ease-in-out infinite;}\n#gdta-register-tag span{writing-mode:vertical-rl;transform:rotate(180deg);display:block;color:#ffffff !important;text-shadow:0 0 6px rgba(255,255,255,.95),0 0 14px rgba(255,255,255,.8),0 0 24px rgba(255,255,255,.6);animation:blink-text 1.4s step-start infinite;}\n#gdta-register-tag:hover{transform:translateY(-50%) translateX(-6px);box-shadow:0 12px 28px rgba(0,0,0,.28);background:#1f1f1f;}\n@media (max-width:768px){#gdta-register-tag{display:block !important;padding:8px 5px !important;right:-1px !important;}#gdta-register-tag span{font-size:11px !important;}}\n@keyframes swing-cta{0%,100%{transform:translateY(-50%) rotate(0deg);}25%{transform:translateY(-50%) rotate(4deg);}50%{transform:translateY(-50%) rotate(-4deg);}75%{transform:translateY(-50%) rotate(3deg);}}\n@keyframes blink-text{0%,50%{opacity:1;}50.1%,100%{opacity:0.2;}}\n";
        document.head.appendChild(styleEl);

        var tag = document.createElement('a');
        tag.id = 'gdta-register-tag';
        // Always point the floating register tag to the external registration URL
        tag.href = 'https://register.gdta2026.com/#/tickets';
        tag.setAttribute('target', '_blank');
        tag.setAttribute('rel', 'noopener noreferrer');
        tag.setAttribute('aria-label', 'Register Now');
        tag.innerHTML = '<span>Register Now</span>';
        document.body.appendChild(tag);
    });

    // Floating call for speakers tag (sitewide)
    $(function () {
        if (document.getElementById('gdta-speakers-tag')) return;

        var speakersStyle = document.createElement('style');
        speakersStyle.textContent = "\n#gdta-speakers-tag{position:fixed;right:-2px;top:calc(50% + 180px);transform:translateY(-50%);transform-origin:top center;z-index:1200;background:#000;color:#fff;text-decoration:none;padding:12px 10px;font-weight:700;letter-spacing:.4px;border-radius:12px 0 0 12px;box-shadow:0 10px 24px rgba(0,0,0,.2);transition:transform .2s ease,box-shadow .2s ease,background .2s ease;animation:swing-cta 3.5s ease-in-out infinite;}\n#gdta-speakers-tag span{writing-mode:vertical-rl;transform:rotate(180deg);display:block;color:#ffffff !important;text-shadow:0 0 6px rgba(255,255,255,.95),0 0 14px rgba(255,255,255,.8),0 0 24px rgba(255,255,255,.6);animation:blink-text 1.4s step-start infinite;}\n#gdta-speakers-tag:hover{transform:translateY(-50%) translateX(-6px);box-shadow:0 12px 28px rgba(0,0,0,.28);background:#1f1f1f;}\n@media (max-width:768px){#gdta-speakers-tag{display:block !important;padding:8px 5px !important;right:-1px !important;}#gdta-speakers-tag span{font-size:11px !important;}}\n@keyframes swing-cta{0%,100%{transform:translateY(-50%) rotate(0deg);}25%{transform:translateY(-50%) rotate(4deg);}50%{transform:translateY(-50%) rotate(-4deg);}75%{transform:translateY(-50%) rotate(3deg);}}\n@keyframes blink-text{0%,50%{opacity:1;}50.1%,100%{opacity:0.2;}}\n";
        document.head.appendChild(speakersStyle);

        var speakersTag = document.createElement('a');
        speakersTag.id = 'gdta-speakers-tag';
        speakersTag.href = 'https://docs.google.com/forms/d/e/1FAIpQLScQwknFSsZ3SbRWaoaAJ6Ts96dBf_xNCYmWdt5TrCfRz9Lknw/viewform';
        speakersTag.setAttribute('target', '_blank');
        speakersTag.setAttribute('rel', 'noopener noreferrer');
        speakersTag.setAttribute('aria-label', 'Call for Speakers');
        speakersTag.innerHTML = '<span>Call for Speakers</span>';
        document.body.appendChild(speakersTag);
    });

    
})(jQuery);

