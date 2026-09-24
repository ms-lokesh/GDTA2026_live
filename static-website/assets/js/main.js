(function ($) {
    "use strict";

    // Detect Windows OS and add class to HTML tag
    if (navigator.platform.indexOf('Win') !== -1 || navigator.userAgent.indexOf('Windows') !== -1) {
        document.documentElement.classList.add('os-windows');
    }

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
        var styleEl = document.createElement('style');
        styleEl.id = 'gdta-hanging-tags-style';
        styleEl.textContent = "\n#gdta-agenda-tag,#gdta-view-speakers-tag{position:fixed;right:-2px;transform:translateY(-50%);transform-origin:top center;z-index:1200;background:#000;color:#fff;text-decoration:none;padding:12px 10px;font-weight:700;letter-spacing:.4px;border-radius:12px 0 0 12px;box-shadow:0 10px 24px rgba(0,0,0,.2);transition:transform .2s ease,box-shadow .2s ease,background .2s ease;animation:swing-cta 3.5s ease-in-out infinite;}\n#gdta-agenda-tag{top:40%;}\n#gdta-view-speakers-tag{top:calc(40% + 115px);}\n#gdta-agenda-tag span,#gdta-view-speakers-tag span{writing-mode:vertical-rl;transform:rotate(180deg);display:block;color:#ffffff !important;text-shadow:0 0 6px rgba(255,255,255,.95),0 0 14px rgba(255,255,255,.8),0 0 24px rgba(255,255,255,.6);animation:blink-text 1.4s step-start infinite;}\n#gdta-agenda-tag:hover,#gdta-view-speakers-tag:hover{transform:translateY(-50%) translateX(-6px);box-shadow:0 12px 28px rgba(0,0,0,.28);background:#1f1f1f;}\n" +
                              "@media (max-width:768px){#gdta-agenda-tag,#gdta-view-speakers-tag{display:block !important;padding:8px 5px !important;right:-1px !important;}#gdta-agenda-tag span,#gdta-view-speakers-tag span{font-size:11px !important;}}\n@keyframes swing-cta{0%,100%{transform:translateY(-50%) rotate(0deg);}25%{transform:translateY(-50%) rotate(4deg);}50%{transform:translateY(-50%) rotate(-4deg);}75%{transform:translateY(-50%) rotate(3deg);}}\n@keyframes blink-text{0%,50%{opacity:1;}50.1%,100%{opacity:0.2;}}\n";
        if (!document.getElementById(styleEl.id)) document.head.appendChild(styleEl);

        if (!document.getElementById('gdta-agenda-tag')) {
            var agendaTag = document.createElement('a');
            agendaTag.id = 'gdta-agenda-tag';
            agendaTag.href = window.location.pathname.indexOf('/hackathon/') !== -1
                ? '../program-schedule.html'
                : './program-schedule.html';
            agendaTag.setAttribute('aria-label', 'Agenda');
            agendaTag.innerHTML = '<span>Agenda</span>';
            document.body.appendChild(agendaTag);
        }

        if (!document.getElementById('gdta-view-speakers-tag')) {
            var speakersTag = document.createElement('a');
            speakersTag.id = 'gdta-view-speakers-tag';
            speakersTag.href = window.location.pathname.indexOf('/hackathon/') !== -1
                ? '../program-sessions.html'
                : './program-sessions.html';
            speakersTag.setAttribute('aria-label', 'View Speakers');
            speakersTag.innerHTML = '<span>View Speakers</span>';
            document.body.appendChild(speakersTag);
        }
    });


    
})(jQuery);
