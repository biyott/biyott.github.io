import './vendor/model-viewer.min.js';

const viewer = document.querySelector('#mv');
const views = [
  ['정면', '0deg 80deg auto'],
  ['측면', '90deg 80deg auto'],
  ['후면', '180deg 80deg auto'],
  ['상단', '0deg 5deg auto'],
  ['자동 회전', ''],
];
document.querySelector('#views-bar').append(...views.map(([label, orbit]) => {
  const b = document.createElement('button');
  b.textContent = label;
  b.onclick = () => {
    if (orbit) { viewer.removeAttribute('auto-rotate'); viewer.setAttribute('camera-orbit', orbit); }
    else viewer.setAttribute('auto-rotate', '');
  };
  return b;
}));

// 히어로 이미지 클릭 → 뷰어로 스크롤 후 360° 1회전.
const spin = () => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  viewer.removeAttribute('auto-rotate');
  const t0 = performance.now(), ms = 3500;
  const step = (now) => {
    const k = Math.min((now - t0) / ms, 1), e = k < .5 ? 2 * k * k : 1 - 2 * (1 - k) ** 2;
    viewer.cameraOrbit = `${35 + 360 * e}deg 75deg auto`;
    if (k < 1) requestAnimationFrame(step);
    else viewer.setAttribute('auto-rotate', '');
  };
  requestAnimationFrame(step);
};
document.querySelector('#hero-demo').addEventListener('click', (ev) => {
  ev.preventDefault();
  document.querySelector('#viewer').scrollIntoView({ behavior: 'smooth' });
  setTimeout(spin, 700);
});
