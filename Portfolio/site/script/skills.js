// Typing effect for the terminal prompt
(function typeCommand() {
  const target = document.getElementById('typedCmd');
  if (!target) return;

  const command = 'cat skills.json';
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (reduceMotion) {
    target.textContent = command;
    return;
  }

  let i = 0;
  function step() {
    if (i <= command.length) {
      target.textContent = command.slice(0, i);
      i++;
      setTimeout(step, 38 + Math.random() * 40);
    }
  }
  step();
})();

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
  }, { threshold: 0.2, rootMargin: '0px 0px -60px 0px' });

  blocks.forEach(b => observer.observe(b));
})();
