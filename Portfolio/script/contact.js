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

// Contact form handling
// NOTE: this is front-end only. It validates the fields and gives terminal-style
// feedback, but nothing is actually sent anywhere yet. To make it functional, wire
// the fetch() call below to a form backend such as Formspree, EmailJS, or your own
// server endpoint.
(function handleContactForm() {
  const form = document.getElementById('contactForm');
  const output = document.getElementById('formOutput');
  if (!form || !output) return;

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    const name = form.name.value.trim();
    const email = form.email.value.trim();
    const message = form.message.value.trim();

    if (!name || !email || !message) {
      output.textContent = 'error: all fields are required.';
      output.classList.add('is-error');
      return;
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(email)) {
      output.textContent = 'error: that email address doesn\'t look right.';
      output.classList.add('is-error');
      return;
    }

    output.classList.remove('is-error');
    output.textContent = 'sending...';

    // Replace this block with a real request once a backend is connected, e.g.:
    // fetch('https://formspree.io/f/your-id', {
    //   method: 'POST',
    //   headers: { 'Accept': 'application/json' },
    //   body: new FormData(form)
    // }).then(...)

    setTimeout(function () {
      output.textContent = 'message ready — connect a form backend (Formspree, EmailJS, etc.) to deliver it. for now, email me directly above.';
      form.reset();
    }, 700);
  });
})();
