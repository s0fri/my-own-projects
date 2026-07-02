// Scroll-triggered reveal for each output block
(function revealBlocks() {
  const blocks = document.querySelectorAll('[data-block]');
  if (!blocks.length) return;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) {
    blocks.forEach(b => b.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -60px 0px' });

  blocks.forEach(b => observer.observe(b));
})();
