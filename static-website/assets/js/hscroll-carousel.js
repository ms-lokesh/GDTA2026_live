/* Horizontal Auto-Scroll Carousel - shared component
   Usage: <div class="hscroll-carousel">
            <button class="hscroll-arrow hscroll-arrow-left"><i class="fas fa-chevron-left"></i></button>
            <div class="hscroll-track"> ...cards... </div>
            <button class="hscroll-arrow hscroll-arrow-right"><i class="fas fa-chevron-right"></i></button>
          </div>
*/
(function () {
    function initCarousel(root) {
        if (root.dataset.hscrollInitialized) return;

        const track = root.querySelector('.hscroll-track');
        const prevBtn = root.querySelector('.hscroll-arrow-left');
        const nextBtn = root.querySelector('.hscroll-arrow-right');
        if (!track) return;

        const originalCards = Array.from(track.children);
        if (originalCards.length === 0) return;

        root.dataset.hscrollInitialized = 'true';

        // Duplicate cards once so the auto-scroll loop can wrap seamlessly
        originalCards.forEach(card => {
            track.appendChild(card.cloneNode(true));
        });

        const speed = parseFloat(root.dataset.speed) || 0.6;
        let paused = false;
        let resumeTimeout = null;

        function pauseAwhile(ms) {
            paused = true;
            if (resumeTimeout) clearTimeout(resumeTimeout);
            resumeTimeout = setTimeout(() => { paused = false; }, ms);
        }

        function tick() {
            if (!paused) {
                const half = track.scrollWidth / 2;
                track.scrollLeft += speed;
                if (track.scrollLeft >= half) {
                    track.scrollLeft -= half;
                }
            }
            requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);

        root.addEventListener('mouseenter', () => { paused = true; });
        root.addEventListener('mouseleave', () => {
            if (resumeTimeout) clearTimeout(resumeTimeout);
            paused = false;
        });
        track.addEventListener('touchstart', () => { paused = true; }, { passive: true });
        track.addEventListener('touchend', () => pauseAwhile(3000), { passive: true });

        function cardStep() {
            const firstCard = track.querySelector(':scope > *');
            const gap = 24;
            return firstCard ? firstCard.getBoundingClientRect().width + gap : 300;
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                track.scrollBy({ left: -cardStep() * 2, behavior: 'smooth' });
                pauseAwhile(3000);
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                track.scrollBy({ left: cardStep() * 2, behavior: 'smooth' });
                pauseAwhile(3000);
            });
        }
    }

    window.initHscrollCarousel = initCarousel;

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.hscroll-carousel').forEach(initCarousel);
    });
})();
