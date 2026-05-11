/* WEIIMG site nav: injects hamburger toggle on mobile, handles open/close */
(() => {
  const nav = document.querySelector('.nav');
  if (!nav) return;

  // Inject burger button if not present
  if (!nav.querySelector('.nav-burger')) {
    const btn = document.createElement('button');
    btn.className = 'nav-burger';
    btn.type = 'button';
    btn.setAttribute('aria-label', '選單');
    btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = '<span></span><span></span><span></span>';
    nav.appendChild(btn);
  }

  const burger = nav.querySelector('.nav-burger');
  const navItems = nav.querySelector('.nav-items');
  if (!burger || !navItems) return;

  const close = () => {
    document.body.classList.remove('nav-open');
    if (navItems) navItems.classList.remove('open');
    burger.setAttribute('aria-expanded', 'false');
  };
  const toggle = () => {
    const open = navItems.classList.toggle('open');
    document.body.classList.toggle('nav-open', open);
    burger.setAttribute('aria-expanded', open ? 'true' : 'false');
  };

  burger.addEventListener('click', toggle);
  navItems.querySelectorAll('a').forEach(a => a.addEventListener('click', close));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  window.addEventListener('resize', () => { if (window.innerWidth > 768) close(); });
})();

/* Logo arrow hover (desktop) */
(() => {
  const logo = document.querySelector('.nav-logo');
  const line = logo && logo.querySelector('.arrow-line');
  const navItems = document.querySelector('.nav-items');
  if (!logo || !line || !navItems) return;
  function setArrowWidth() {
    const lR = logo.getBoundingClientRect(), nR = navItems.getBoundingClientRect();
    line.style.width = Math.max(0, nR.left - lR.right - 12) + 'px';
  }
  logo.addEventListener('mouseenter', () => { setArrowWidth(); logo.classList.remove('arrow-out'); logo.classList.add('arrow-in'); });
  logo.addEventListener('mouseleave', () => {
    logo.classList.remove('arrow-in'); logo.classList.add('arrow-out');
    line.addEventListener('transitionend', () => logo.classList.remove('arrow-out'), { once: true });
  });
})();

/* Nav slide-mask (desktop hover dropdown for WORK) */
(() => {
  const wrap = document.querySelector('.nav-slide-wrap');
  const trigger = wrap && wrap.querySelector('.has-dropdown');
  if (!wrap || !trigger) return;
  let timer;
  const show = () => { clearTimeout(timer); wrap.classList.add('open'); };
  const hide = () => { timer = setTimeout(() => wrap.classList.remove('open'), 250); };
  trigger.addEventListener('mouseenter', show);
  wrap.addEventListener('mouseleave', hide);
  wrap.querySelectorAll('.nav-row:last-child a').forEach(a => a.addEventListener('mouseenter', show));
})();
