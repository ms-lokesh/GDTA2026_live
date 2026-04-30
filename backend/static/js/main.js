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
        styleEl.textContent = "\n#gdta-register-tag{position:fixed;right:-2px;top:50%;transform:translateY(-50%);z-index:1200;background:#000;color:#fff;text-decoration:none;padding:12px 10px;font-weight:700;letter-spacing:.4px;border-radius:12px 0 0 12px;box-shadow:0 10px 24px rgba(0,0,0,.2);transition:transform .2s ease,box-shadow .2s ease,background .2s ease;}\n#gdta-register-tag span{writing-mode:vertical-rl;transform:rotate(180deg);display:block;}\n#gdta-register-tag:hover{transform:translateY(-50%) translateX(-6px);box-shadow:0 12px 28px rgba(0,0,0,.28);background:#1f1f1f;}\n@media (max-width:768px){#gdta-register-tag{display:none;}}\n";
        document.head.appendChild(styleEl);

        var tag = document.createElement('a');
        tag.id = 'gdta-register-tag';
        tag.href = '/registration-coming-soon.html';
        tag.setAttribute('aria-label', 'Register Now');
        tag.innerHTML = '<span>Register Now</span>';
        document.body.appendChild(tag);
    });

    
})(jQuery);

