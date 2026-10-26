import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
const DEG = Math.PI / 180;
// 원안(망원 포트레이트)처럼 늘씬하게: FOV를 좁히고 거리를 같은 비율로 늘려 구도는 유지.
const FOV = 18;
const DIST = Math.tan(15 * DEG) / Math.tan(FOV / 2 * DEG);

// --- 렌더러/씬 ---
const canvas = document.querySelector('#stage');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x192123);
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
const camera = new THREE.PerspectiveCamera(FOV, 2, 0.1, 100);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.autoRotate = !REDUCED;
controls.autoRotateSpeed = 1.8;
scene.add(new THREE.HemisphereLight(0xdfe8ea, 0x2a2f2b, 0.9));
const key = new THREE.DirectionalLight(0xfff2dd, 2.0);
key.position.set(4, 6, 3);
scene.add(key);
scene.add(new THREE.GridHelper(10, 20, 0x465153, 0x232b2c));

// --- 칼뷰 (정면/측면/후면/상단/캐논 확대) ---
const HOME = { target: new THREE.Vector3(0, 2.1, 0), radius: 15 };
const ACTION_HOME = HOME; // 기본 자동회전과 액션/시네마 구도의 줌을 통일
let tween = null;
function orbitCamera(az, pol, target, radius) {
  controls.target.copy(target);
  camera.position.setFromSphericalCoords(radius * DIST, pol * DEG, az * DEG).add(target);
  camera.lookAt(target);
}
function flyTo(az, pol, { target = HOME.target, radius = HOME.radius, spin = 0, resume = true, ms = 900 } = {}) {
  controls.autoRotate = false;
  autoBtn.setAttribute('aria-pressed', 'false');
  const off = camera.position.clone().sub(controls.target);
  const s = new THREE.Spherical().setFromVector3(off);
  tween = {
    t0: performance.now(), ms: spin ? 3500 : ms,
    from: { az: s.theta / DEG, pol: s.phi / DEG, r: s.radius, target: controls.target.clone() },
    to: { az: az + spin, pol, r: radius * DIST, target },
    endAuto: resume && !REDUCED,
  };
}
orbitCamera(35, 75, HOME.target, HOME.radius);
const views = [
  ['정면', 0, 86], ['측면', 90, 86], ['후면', 180, 86], ['상단', 0, 5],
  ['캐논 확대', 25, 78, { target: new THREE.Vector3(0, 3.0, 1.3), radius: 3.8 }],
];
for (const [label, az, pol, opt] of views) {
  const b = document.createElement('button');
  b.textContent = label;
  b.onclick = () => { stopCine(); flyTo(az, pol, opt); };
  document.querySelector('#views-bar').append(b);
}
const autoBtn = document.createElement('button');
autoBtn.textContent = '자동 회전';
autoBtn.setAttribute('aria-pressed', String(!REDUCED));
autoBtn.onclick = () => {
  tween = null;
  stopCine();
  controls.autoRotate = !controls.autoRotate;
  autoBtn.setAttribute('aria-pressed', String(controls.autoRotate));
};
document.querySelector('#views-bar').append(autoBtn);

// 히어로 이미지 클릭 → 뷰어로 스크롤 후 360° 1회전.
document.querySelector('#hero-demo').addEventListener('click', (ev) => {
  ev.preventDefault();
  stopCine();
  document.querySelector('#viewer').scrollIntoView({ behavior: 'smooth' });
  if (!REDUCED) setTimeout(() => flyTo(35, 75, { spin: 360 }), 700);
});

// --- 애니메이션 레이어 상태 ---
const layers = { hydraulics: false, cannon: false, traverse: false };
let actuators = [];
let cannon = null;

// 리그 없는 플랫 GLB이므로, barrel→ram 위치 벡터를 실린더 축으로 삼아
// ram·로드측 클레비스·램측 칼라를 축 방향으로 병진시킨다.
function buildActuators(root) {
  const nodes = [];
  root.traverse((o) => { if (o.name) nodes.push(o); });
  const byName = (p) => nodes.filter((o) => norm(o.name).startsWith(p));
  const groups = [];
  for (const prefix of ['ankleactuator', 'primarylegactuator', 'reversejointactuator']) {
    for (const barrel of byName(prefix + 'barrel')) {
      const suffix = norm(barrel.name).slice((prefix + 'barrel').length);
      const ram = nodes.find((o) => norm(o.name) === prefix + 'chromeram' + suffix);
      if (!ram) continue;
      const axis = ram.position.clone().sub(barrel.position);
      const stroke = axis.length() * 0.6;
      axis.normalize();
      const side = Math.sign(ram.position.x) || 1;
      const movers = [ram];
      for (const o of byName(prefix + 'clevisb')) {
        if (Math.sign(o.position.x) === side) movers.push(o);
      }
      for (const o of byName(prefix + 'collar')) {
        if (Math.sign(o.position.x) !== side) continue;
        if (o.position.distanceTo(ram.position) < o.position.distanceTo(barrel.position)) movers.push(o);
      }
      groups.push({ axis, stroke, movers, bases: movers.map((o) => o.position.clone()), value: 0 });
    }
  }
  return groups;
}

// 캐논: 포탑(요) 그룹 아래 포신 묶음(스핀) 그룹을 두고,
// 스핀 가속/감속·반동·총구 플래시를 독립 레이어로 구동한다.
function buildCannon(root) {
  root.updateMatrixWorld(true);
  const nodes = [];
  root.traverse((o) => { if (o.name) nodes.push(o); });
  const byName = (p) => nodes.filter((o) => norm(o.name).startsWith(p));
  const turret = new THREE.Group();
  turret.position.set(0, 3.05, 0.81); // 회전 베어링 중심
  root.add(turret);
  const spin = new THREE.Group();
  spin.position.set(0, 3.05, 0); // 포신 묶음 중심축 (총열 방향 Z)
  root.add(spin);
  for (const p of ['utilitycannonbarrel', 'utilitycannonmuzzle', 'muzzlebore', 'barrelclamp']) {
    byName(p).forEach((o) => spin.attach(o));
  }
  turret.attach(spin);
  for (const p of ['cannonreceiver', 'cannonundersidemount', 'cannonammunitionfeed']) {
    byName(p).forEach((o) => turret.attach(o));
  }
  const recoilBase = spin.position.clone();

  const tex = (() => {
    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const ctx = c.getContext('2d');
    const grad = ctx.createRadialGradient(32, 32, 2, 32, 32, 32);
    grad.addColorStop(0, 'rgba(255,240,190,1)');
    grad.addColorStop(0.35, 'rgba(255,170,60,0.9)');
    grad.addColorStop(1, 'rgba(255,120,20,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(c);
  })();
  const flashes = byName('muzzlebore').map((m) => {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({
      map: tex, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true,
    }));
    m.getWorldPosition(s.position);
    s.position.z += 0.09;
    s.visible = false;
    spin.attach(s);
    return s;
  });
  const light = new THREE.PointLight(0xffb066, 0, 4, 2);
  light.position.set(0, 0, 2.3);
  spin.add(light);
  return { turret, spin, recoilBase, flashes, light, speed: 0, recoil: 0, shotIdx: -1 };
}

new GLTFLoader().load('downloads/Bastion_Industrial_Walker.glb?v=2', (gltf) => {
  scene.add(gltf.scene);
  actuators = buildActuators(gltf.scene);
  cannon = buildCannon(gltf.scene);
});

// 전체 구동 시 동적 인트로 + 시네마틱 샷 루프. 드래그/다른 버튼 입력 시 즉시 해제.
const INTRO_SHOTS = [
  { az: -60, pol: 75, radius: ACTION_HOME.radius, hold: 0, ms: 1600 }, // 왼쪽 전신
  { az: 120, pol: 65, target: new THREE.Vector3(0, 2.3, 0), radius: 14, hold: 0, ms: 6500 }, // 우측·후면을 휘감는 선회
  { az: 200, pol: 75, radius: ACTION_HOME.radius, hold: 0, ms: 2600 }, // 후면
  { az: 35, pol: 75, radius: ACTION_HOME.radius, hold: 1200, ms: 2200 }, // 정면 3/4로 복귀
];
const CINE_SHOTS = [
  { az: 35, pol: 75, radius: ACTION_HOME.radius, hold: 2300 }, // 전신 3/4
  { az: 20, pol: 80, target: new THREE.Vector3(0, 3.05, 1.3), radius: 4.3, hold: 3000 }, // 캐논 사격
  { az: 95, pol: 80, target: new THREE.Vector3(0, 1.5, 0), radius: 8.4, hold: 3000 }, // 다리 유압
  { az: -40, pol: 70, radius: ACTION_HOME.radius, hold: 2300 }, // 반대편 전신
];
const cine = { active: false, introIdx: null, shot: 0, nextAt: 0 };
function startCine() {
  cine.active = true;
  cine.introIdx = 0;
  cine.shot = 0;
  cine.nextAt = 0;
}
function stopCine() { cine.active = false; cine.introIdx = null; }
controls.addEventListener('start', stopCine);

// 레이어 버튼: 전체 구동 / 유압 신축 / 캐논 사격 / 포탑 선회 (독립 토글, 동시 재생 가능)
// 구동 시작 시 자동 회전을 멈추고 전신이 잘 보이는 3/4 구도로 이동한다.
const layerBtns = {};
function syncLayers() {
  for (const [id, b] of Object.entries(layerBtns)) b.setAttribute('aria-pressed', String(layers[id]));
  allBtn.setAttribute('aria-pressed', String(Object.values(layers).every(Boolean)));
}
function setLayers(next) {
  stopCine();
  const wasIdle = !Object.values(layers).some(Boolean);
  Object.assign(layers, next);
  const anyOn = Object.values(layers).some(Boolean);
  if (anyOn) {
    controls.autoRotate = false;
    autoBtn.setAttribute('aria-pressed', 'false');
    if (wasIdle) flyTo(35, 75, { radius: ACTION_HOME.radius, resume: false }); // 이미 구도를 보고 있던 중 추가한 레이어는 칼뷰 유지
  }
  syncLayers();
}
const layerBar = document.querySelector('#layers-bar');
const allBtn = document.createElement('button');
allBtn.textContent = '전체 구동';
allBtn.setAttribute('aria-pressed', 'false');
allBtn.onclick = () => {
  const on = !Object.values(layers).some(Boolean); // 하나라도 켜져 있으면 전체 정지
  setLayers({ hydraulics: on, cannon: on, traverse: on });
  if (on) startCine();
};
layerBar.append(allBtn);
for (const [id, label] of [['hydraulics', '유압 신축'], ['cannon', '캐논 사격'], ['traverse', '포탑 선회']]) {
  const b = document.createElement('button');
  b.textContent = label;
  b.onclick = () => setLayers({ [id]: !layers[id] });
  layerBtns[id] = b;
  layerBar.append(b);
}
syncLayers();

new ResizeObserver(([e]) => {
  const { width, height } = e.contentRect;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}).observe(canvas.parentElement);

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;

  for (const a of actuators) {
    const target = layers.hydraulics ? 0.5 - 0.5 * Math.cos(t * 12.8) : 0; // 유압 추가 2배
    a.value += Math.max(-dt * 10, Math.min(dt * 10, target - a.value));
    a.movers.forEach((o, i) => o.position.copy(a.bases[i]).addScaledVector(a.axis, a.value * a.stroke));
  }

  if (cannon) {
    const c = cannon;
    c.speed += Math.max(-dt * 45, Math.min(dt * 45, (layers.cannon ? 42 : 0) - c.speed));
    c.spin.rotation.z -= c.speed * dt;
    const firing = layers.cannon && c.speed > 33;
    c.recoil += Math.max(-dt * 0.4, Math.min(dt * 0.4, (firing ? 0.05 + 0.02 * Math.abs(Math.sin(t * 67.5)) : 0) - c.recoil));
    c.spin.position.copy(c.recoilBase);
    c.spin.position.z -= c.recoil;
    const idx = firing ? Math.floor(t * 36) % c.flashes.length : -1;
    c.flashes.forEach((f, i) => {
      f.visible = i === idx;
      if (f.visible) f.scale.setScalar(0.22 + 0.1 * Math.random());
    });
    c.light.intensity = firing ? 6 + 5 * Math.random() : 0;
    const yaw = layers.traverse ? 0.4 * Math.sin(t * 1.05) : 0;
    c.turret.rotation.y += (yaw - c.turret.rotation.y) * Math.min(dt * 3, 1);
  }

  if (cine.active && !tween && performance.now() >= cine.nextAt) {
    if (cine.introIdx !== null) {
      const s = INTRO_SHOTS[cine.introIdx];
      flyTo(s.az, s.pol, { ...s, resume: false });
      cine.nextAt = performance.now() + s.ms + s.hold;
      if (++cine.introIdx >= INTRO_SHOTS.length) cine.introIdx = null;
    } else {
      const s = CINE_SHOTS[cine.shot % CINE_SHOTS.length];
      flyTo(s.az, s.pol, { ...s, resume: false, ms: 950 });
      cine.nextAt = performance.now() + 950 + s.hold;
      cine.shot++;
    }
  }

  if (tween) {
    const k = Math.min((performance.now() - tween.t0) / tween.ms, 1);
    const e = k < 0.5 ? 2 * k * k : 1 - 2 * (1 - k) ** 2;
    const { from, to } = tween;
    controls.target.lerpVectors(from.target, to.target, e);
    camera.position.setFromSphericalCoords(
      from.r + (to.r - from.r) * e,
      (from.pol + (to.pol - from.pol) * e) * DEG,
      (from.az + (to.az - from.az) * e) * DEG,
    ).add(controls.target);
    camera.lookAt(controls.target);
    if (k === 1) { controls.autoRotate = tween.endAuto; autoBtn.setAttribute('aria-pressed', String(tween.endAuto)); tween = null; }
  }
  controls.update();
  renderer.render(scene, camera);
});
