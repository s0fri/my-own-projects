// Typewriter effect for ".typing-txt span"
(function typeRoles() {
  const target = document.querySelector('.typing-txt span');
  if (!target) return;

  const roles = [
    'Web Developer',
    'Software Developer',
    'Web Designer',
    'Ai Workflow Developer',
    'Security Engineering'
  ];

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) {
    target.textContent = roles[0];
    return;
  }

  const TYPE_SPEED = 60;
  const DELETE_SPEED = 35;
  const HOLD_TIME = 1400;
  const GAP_TIME = 400;

  let roleIndex = 0;
  let charIndex = 0;

  function type() {
    const current = roles[roleIndex];
    charIndex++;
    target.textContent = current.slice(0, charIndex);

    if (charIndex < current.length) {
      setTimeout(type, TYPE_SPEED);
    } else {
      setTimeout(erase, HOLD_TIME);
    }
  }

  function erase() {
    const current = roles[roleIndex];
    charIndex--;
    target.textContent = current.slice(0, charIndex);

    if (charIndex > 0) {
      setTimeout(erase, DELETE_SPEED);
    } else {
      roleIndex = (roleIndex + 1) % roles.length;
      setTimeout(type, GAP_TIME);
    }
  }

  type();
})();
