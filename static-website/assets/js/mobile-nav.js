/*
  Mobile navigation + touch helpers (vanilla JS)
  - Only activates on <= 768px
  - Does not rely on Bootstrap collapse JS
  - Accessible: updates aria-expanded and supports ESC + outside click
*/

(function () {
  const MOBILE_MAX = 991.98;

  function isMobile() {
    return window.matchMedia(`(max-width: ${MOBILE_MAX}px)`).matches;
  }

  function getNavTop() {
    // Try to measure the fixed navbar container height if present
    const navContainer = document.querySelector('.navbar-container');
    if (navContainer) return Math.max(56, Math.round(navContainer.getBoundingClientRect().height));

    const navbar = document.querySelector('.navbar');
    if (navbar) return Math.max(56, Math.round(navbar.getBoundingClientRect().height));

    return 86;
  }

  function ensureBackdrop() {
    let backdrop = document.querySelector('.mobile-nav-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.className = 'mobile-nav-backdrop';
      backdrop.setAttribute('aria-hidden', 'true');
      document.body.appendChild(backdrop);
    }
    return backdrop;
  }

  function setupMobileNav() {
    const toggler = document.querySelector('.navbar-toggler');
    if (!toggler) return;

    // Determine collapse element
    const targetSelector = toggler.getAttribute('data-bs-target') || toggler.getAttribute('data-target') || '#navbarCollapse';
    const collapse = document.querySelector(targetSelector) || document.getElementById('navbarCollapse') || document.querySelector('.navbar-collapse');
    if (!collapse) return;
    const bootstrapToggle = toggler.getAttribute('data-bs-toggle');
    const bootstrapTarget = toggler.getAttribute('data-bs-target');
    const hadBootstrapCollapseClass = collapse.classList.contains('collapse');

    function isMobileNavActive() {
      return isMobile() || window.getComputedStyle(toggler).display !== 'none';
    }

    // Set CSS variable for top offset
    document.documentElement.style.setProperty('--gdta-mobile-nav-top', `${getNavTop()}px`);

    // Accessibility defaults
    toggler.setAttribute('aria-controls', collapse.id || 'navbarCollapse');
    toggler.setAttribute('aria-expanded', 'false');
    toggler.setAttribute('aria-label', toggler.getAttribute('aria-label') || 'Toggle navigation');

    const backdrop = ensureBackdrop();

    function syncBootstrapControl() {
      if (isMobileNavActive()) {
        toggler.removeAttribute('data-bs-toggle');
        toggler.removeAttribute('data-bs-target');
        collapse.classList.remove('collapse');

        if (window.bootstrap && window.bootstrap.Collapse) {
          const instance = window.bootstrap.Collapse.getInstance(collapse);
          if (instance) instance.dispose();
        }
        return;
      }

      if (bootstrapToggle) toggler.setAttribute('data-bs-toggle', bootstrapToggle);
      if (bootstrapTarget) toggler.setAttribute('data-bs-target', bootstrapTarget);
      if (hadBootstrapCollapseClass) collapse.classList.add('collapse');
    }

    function clearBootstrapOpenState() {
      collapse.classList.remove('show', 'collapsing');
      collapse.style.removeProperty('display');
      collapse.style.removeProperty('height');
      collapse.style.removeProperty('visibility');
    }

    function open() {
      clearBootstrapOpenState();
      collapse.classList.add('is-open');
      toggler.classList.add('is-open');
      backdrop.classList.add('is-open');
      document.body.classList.add('mobile-nav-open');
      toggler.setAttribute('aria-expanded', 'true');
    }

    function close() {
      clearBootstrapOpenState();
      collapse.classList.remove('is-open');
      toggler.classList.remove('is-open');
      collapse.querySelectorAll('.dropdown-menu.show').forEach(function (menu) {
        menu.classList.remove('show');
      });
      collapse.querySelectorAll('.dropdown-toggle[aria-expanded="true"]').forEach(function (link) {
        link.setAttribute('aria-expanded', 'false');
      });
      backdrop.classList.remove('is-open');
      document.body.classList.remove('mobile-nav-open');
      toggler.setAttribute('aria-expanded', 'false');
    }

    function toggle() {
      const openNow = collapse.classList.contains('is-open');
      if (openNow) close();
      else open();
    }

    // Avoid double-binding
    if (toggler.__gdtaMobileNavBound) return;
    toggler.__gdtaMobileNavBound = true;

    toggler.addEventListener('click', function (e) {
      if (!isMobileNavActive()) return;
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      toggle();
    }, true);

    document.addEventListener('click', function (e) {
      if (!isMobileNavActive()) return;
      const target = e.target;
      if (!target) return;
      if (toggler.contains(target)) return;
      if (collapse.contains(target)) return;
      close();
    });

    document.addEventListener('keydown', function (e) {
      if (!isMobileNavActive()) return;
      if (e.key === 'Escape') close();
    });

    // Handle dropdown toggles and items
    collapse.addEventListener('click', function (e) {
      const link = e.target && (e.target.closest('a') || e.target.closest('button'));
      if (!link) return;
      if (!isMobileNavActive()) return;

      // If it's a dropdown toggle, prevent default and toggle the dropdown
      if (link.classList.contains('dropdown-toggle')) {
        e.preventDefault();
        e.stopPropagation();
        // Let Bootstrap's dropdown JS handle it, or add show class manually
        const parent = link.closest('.dropdown');
        if (parent) {
          const menu = parent.querySelector('.dropdown-menu');
          if (menu) {
            menu.classList.toggle('show');
            link.setAttribute('aria-expanded', menu.classList.contains('show'));
          }
        }
        return;
      }

      // If it's a dropdown item, allow the click to go through
      if (link.closest('.dropdown-menu')) {
        // Don't close the menu yet, let the link navigate
        return;
      }

      // For regular nav links, close the menu
      close();
    });

    // Keep nav top in sync on resize
    window.addEventListener('resize', function () {
      document.documentElement.style.setProperty('--gdta-mobile-nav-top', `${getNavTop()}px`);
      syncBootstrapControl();
      if (!isMobileNavActive()) close();
    });

    // Ensure closed initially on mobile
    syncBootstrapControl();
    if (isMobileNavActive()) close();
  }

  function setupFeaturedCarouselSwipe() {
    if (!('ontouchstart' in window)) return;

    const featured = document.querySelector('.featured-article');
    if (!featured) return;

    let startX = 0;
    let startY = 0;
    let tracking = false;

    function onTouchStart(e) {
      if (!isMobile()) return;
      if (!e.touches || e.touches.length !== 1) return;
      tracking = true;
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    }

    function onTouchMove(e) {
      if (!tracking) return;
      if (!e.touches || e.touches.length !== 1) return;

      const dx = e.touches[0].clientX - startX;
      const dy = e.touches[0].clientY - startY;

      // Let vertical scroll pass through
      if (Math.abs(dy) > Math.abs(dx)) return;

      // Prevent horizontal scroll jitter
      e.preventDefault();
    }

    function onTouchEnd(e) {
      if (!tracking) return;
      tracking = false;

      const touch = (e.changedTouches && e.changedTouches[0]) ? e.changedTouches[0] : null;
      if (!touch) return;

      const dx = touch.clientX - startX;
      const threshold = 50;

      if (Math.abs(dx) < threshold) return;

      // Prefer page-defined functions (existing carousel)
      if (dx < 0 && typeof window.navigateNext === 'function') {
        window.navigateNext();
      } else if (dx > 0 && typeof window.navigatePrev === 'function') {
        window.navigatePrev();
      }
    }

    featured.addEventListener('touchstart', onTouchStart, { passive: true });
    featured.addEventListener('touchmove', onTouchMove, { passive: false });
    featured.addEventListener('touchend', onTouchEnd, { passive: true });
  }

  document.addEventListener('DOMContentLoaded', function () {
    setupMobileNav();
    setupFeaturedCarouselSwipe();
  });
})();
