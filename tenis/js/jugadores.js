// Plantel y figura de cada jugador.
// El cuerpo se anima con poses: cada pose dice donde estan las manos, los pies y hacia donde apunta
// la raqueta, y los codos y rodillas salen solos por cinematica inversa. Asi un golpe se escribe como
// el recorrido de la mano (armado, impacto, terminacion) y no como angulos sueltos.
import * as THREE from 'three';
import { LIMITE_X, LIMITE_Z, lado } from './cancha.js';

// Atributos de 1 a 10. `topspin` multiplica el efecto del drive.
export const PLANTEL = [
  { id: 'federer', nombre: 'Federer', pais: 'SUI', perfil: 'Completo: toque, saque y volea',
    altura: 1.85, zurdo: false, dosManos: false, topspin: 0.9, piel: 0xe0ac8a, pelo: 0x3d2b1c, vincha: 0xffffff,
    attrs: { potencia: 8, velocidad: 8, precision: 9, saque: 9, toque: 10, resistencia: 7 } },
  { id: 'nadal', nombre: 'Nadal', pais: 'ESP', perfil: 'Zurdo, topspin pesado, no se cansa',
    altura: 1.85, zurdo: true, dosManos: true, topspin: 1.7, piel: 0xc48a60, pelo: 0x241810, vincha: 0xffffff, sinMangas: true, muniequera: 0xffffff,
    attrs: { potencia: 9, velocidad: 9, precision: 8, saque: 7, toque: 8, resistencia: 10 } },
  { id: 'djokovic', nombre: 'Djokovic', pais: 'SRB', perfil: 'Contragolpeador, precisión total',
    altura: 1.88, zurdo: false, dosManos: true, topspin: 1.0, piel: 0xd9a684, pelo: 0x1a1512,
    attrs: { potencia: 8, velocidad: 9, precision: 10, saque: 8, toque: 8, resistencia: 10 } },
  { id: 'alcaraz', nombre: 'Alcaraz', pais: 'ESP', perfil: 'El más rápido y el mejor dropshot',
    altura: 1.83, zurdo: false, dosManos: true, topspin: 1.2, piel: 0xc9936c, pelo: 0x1f1611,
    attrs: { potencia: 9, velocidad: 10, precision: 8, saque: 8, toque: 10, resistencia: 9 } },
  { id: 'sinner', nombre: 'Sinner', pais: 'ITA', perfil: 'Potencia plana desde el fondo',
    altura: 1.91, zurdo: false, dosManos: true, topspin: 0.8, piel: 0xeec3a6, pelo: 0xc05a22, gorra: 0xffffff,
    attrs: { potencia: 10, velocidad: 9, precision: 9, saque: 8, toque: 7, resistencia: 8 } },
  { id: 'delpotro', nombre: 'Del Potro', pais: 'ARG', perfil: 'Drive y saque demoledores, más lento',
    altura: 1.98, zurdo: false, dosManos: true, topspin: 0.7, piel: 0xdcab88, pelo: 0x32241a, vincha: 0x8fd0f0, muniequera: 0x8fd0f0,
    attrs: { potencia: 10, velocidad: 6, precision: 8, saque: 10, toque: 7, resistencia: 6 } },
];
export const ATRIBUTOS = [
  ['potencia', 'Potencia'], ['velocidad', 'Velocidad'], ['precision', 'Precisión'],
  ['saque', 'Saque'], ['toque', 'Toque'], ['resistencia', 'Resistencia'],
];

// ---------- Poses ----------
// Coordenadas [lado, alto, frente] en metros para un jugador de 1,85, con origen entre los pies:
// lado + es el lado del brazo de la raqueta (se espeja solo para el zurdo), frente + es hacia la red.
//   hR: mano de la raqueta   rd: hacia donde apunta la raqueta   rn: hacia donde mira el encordado
//   hL: mano libre           ag: la mano libre agarra la raqueta a esa distancia de la otra (0 = suelta)
//   fR, fL: pies             yaw / pyaw: giro de hombros / cadera hacia el lado de la raqueta
//   lean: inclinacion hacia adelante   crouch: cuanto baja la cadera   salto: despegue del piso
const LISTO = {
  hR: [0.12, 1.02, 0.32], rd: [-0.45, 0.55, 0.7], rn: [0.7, 0.2, 0.4], hL: [-0.12, 1.1, 0.36], ag: 0.3,
  fR: [0.25, 0, 0], fL: [-0.25, 0, 0], yaw: 0, pyaw: 0, lean: 0.24, crouch: 0.08, salto: 0,
};
const K = (p) => ({ ...LISTO, ag: 0, rn: [0, 0, 1], ...p });

// Cada golpe: `prep` es el armado que se sostiene esperando la pelota; `swing` arranca en el impacto (t = 0).
const GOLPES = {
  drive: {
    prep: K({ hR: [0.5, 1.28, -0.32], rd: [0.15, 0.85, -0.5], hL: [0.28, 1.3, 0.3], yaw: 1.25, pyaw: 0.6,
      lean: 0.12, crouch: 0.12, fR: [0.26, 0, -0.14], fL: [-0.16, 0, 0.2] }),
    swing: [
      K({ t: 0, hR: [0.64, 0.95, 0.42], rd: [0.9, 0.05, 0.3], hL: [-0.3, 1.15, 0.1], yaw: 0.15, pyaw: 0.1,
        lean: 0.2, crouch: 0.05, fR: [0.26, 0, -0.14], fL: [-0.16, 0, 0.2] }),
      K({ t: 0.12, hR: [0.2, 1.42, 0.5], rd: [-0.3, 0.9, 0.3], hL: [-0.3, 1.15, 0.1], yaw: -0.5, pyaw: -0.2,
        lean: 0.18, crouch: 0.02, fR: [0.26, 0.04, -0.08], fL: [-0.16, 0, 0.2] }),
      K({ t: 0.3, hR: [-0.3, 1.5, 0.14], rd: [-0.5, 0.3, -0.8], rn: [0.5, 0.6, 0], hL: [-0.25, 1.2, 0.18], yaw: -0.95,
        pyaw: -0.45, lean: 0.12, crouch: 0, fR: [0.2, 0.03, 0.1], fL: [-0.16, 0, 0.2] }),
    ],
  },
  reves: { // a dos manos
    prep: K({ hR: [-0.45, 1.0, -0.25], rd: [-0.3, 0.65, -0.7], ag: 0.13, yaw: -1.3, pyaw: -0.6, lean: 0.14,
      crouch: 0.12, fR: [0.06, 0, 0.22], fL: [-0.26, 0, -0.12] }),
    swing: [
      K({ t: 0, hR: [-0.36, 0.92, 0.45], rd: [-0.88, 0, 0.35], ag: 0.13, yaw: -0.3, pyaw: -0.15, lean: 0.2,
        crouch: 0.06, fR: [0.06, 0, 0.22], fL: [-0.26, 0, -0.12] }),
      K({ t: 0.12, hR: [0.15, 1.36, 0.45], rd: [0.3, 0.9, 0.3], ag: 0.13, yaw: 0.35, pyaw: 0.15, lean: 0.16,
        crouch: 0.02, fR: [0.06, 0, 0.22], fL: [-0.26, 0.04, -0.06] }),
      K({ t: 0.3, hR: [0.4, 1.55, 0.06], rd: [0.5, 0.4, -0.75], rn: [-0.5, 0.6, 0], ag: 0.13, yaw: 0.85, pyaw: 0.4,
        lean: 0.1, crouch: 0, fR: [0.06, 0, 0.22], fL: [-0.2, 0.03, 0.1] }),
    ],
  },
  reves1: { // a una mano: el brazo libre se queda atras para equilibrar
    prep: K({ hR: [-0.45, 1.05, -0.28], rd: [-0.3, 0.7, -0.65], ag: 0.3, yaw: -1.4, pyaw: -0.65, lean: 0.14,
      crouch: 0.12, fR: [0.06, 0, 0.24], fL: [-0.26, 0, -0.12] }),
    swing: [
      K({ t: 0, hR: [-0.3, 0.95, 0.5], rd: [-0.9, 0.05, 0.3], hL: [-0.35, 1.0, -0.25], yaw: -0.75, pyaw: -0.4,
        lean: 0.2, crouch: 0.06, fR: [0.06, 0, 0.24], fL: [-0.26, 0, -0.12] }),
      K({ t: 0.12, hR: [0.3, 1.45, 0.42], rd: [0.2, 0.95, 0.2], hL: [-0.45, 0.95, -0.35], yaw: -0.3, pyaw: -0.2,
        lean: 0.14, crouch: 0.02, fR: [0.06, 0, 0.24], fL: [-0.26, 0, -0.12] }),
      K({ t: 0.3, hR: [0.58, 1.68, 0.15], rd: [0.35, 0.9, -0.2], rn: [-0.4, 0.3, 0.8], hL: [-0.5, 0.92, -0.38], yaw: 0.1,
        pyaw: 0, lean: 0.08, crouch: 0, fR: [0.06, 0, 0.24], fL: [-0.26, 0, -0.12] }),
    ],
  },
  dropshot: { // slice corto de arriba hacia abajo, con la cara abierta
    prep: K({ hR: [0.45, 1.48, -0.05], rd: [0.1, 0.95, -0.3], hL: [-0.2, 1.15, 0.3], yaw: 0.85, pyaw: 0.4,
      lean: 0.14, crouch: 0.1, fR: [0.26, 0, -0.1], fL: [-0.16, 0, 0.2] }),
    swing: [
      K({ t: 0, hR: [0.52, 1.0, 0.4], rd: [0.75, 0.45, 0.2], rn: [0, 0.5, 0.85], hL: [-0.3, 1.1, 0.15], yaw: 0.3,
        pyaw: 0.15, lean: 0.24, crouch: 0.1, fR: [0.26, 0, -0.1], fL: [-0.16, 0, 0.2] }),
      K({ t: 0.16, hR: [0.3, 0.88, 0.58], rd: [0.55, 0.3, 0.75], rn: [-0.3, 0.9, 0.3], hL: [-0.32, 1.05, 0.05], yaw: 0.05,
        pyaw: 0.05, lean: 0.28, crouch: 0.12, fR: [0.26, 0, -0.1], fL: [-0.16, 0, 0.2] }),
      K({ t: 0.34, hR: [0.2, 0.9, 0.6], rd: [0.35, 0.3, 0.9], rn: [-0.3, 0.9, 0.2], hL: [-0.32, 1.05, 0.05], yaw: -0.05,
        lean: 0.26, crouch: 0.1, fR: [0.26, 0, -0.1], fL: [-0.16, 0, 0.2] }),
    ],
  },
  dropshot_r: {
    prep: K({ hR: [-0.3, 1.5, -0.05], rd: [-0.2, 0.9, -0.4], ag: 0.3, yaw: -1.15, pyaw: -0.5, lean: 0.14,
      crouch: 0.1, fR: [0.06, 0, 0.22], fL: [-0.26, 0, -0.12] }),
    swing: [
      K({ t: 0, hR: [-0.36, 1.0, 0.42], rd: [-0.8, 0.4, 0.3], rn: [0, 0.5, 0.85], hL: [-0.4, 1.05, -0.2], yaw: -0.7,
        pyaw: -0.35, lean: 0.24, crouch: 0.1, fR: [0.06, 0, 0.22], fL: [-0.26, 0, -0.12] }),
      K({ t: 0.16, hR: [0.05, 0.88, 0.58], rd: [-0.2, 0.25, 0.9], rn: [0.3, 0.9, 0.2], hL: [-0.45, 1.0, -0.3], yaw: -0.5,
        pyaw: -0.3, lean: 0.28, crouch: 0.12, fR: [0.06, 0, 0.22], fL: [-0.26, 0, -0.12] }),
      K({ t: 0.34, hR: [0.25, 0.88, 0.52], rd: [0.4, 0.2, 0.85], rn: [0.3, 0.9, 0.2], hL: [-0.45, 1.0, -0.3], yaw: -0.4,
        pyaw: -0.25, lean: 0.26, crouch: 0.1, fR: [0.06, 0, 0.22], fL: [-0.26, 0, -0.12] }),
    ],
  },
  globo: { // de abajo hacia arriba, terminando alto
    prep: K({ hR: [0.48, 0.72, -0.28], rd: [0.3, -0.45, -0.8], rn: [0, 0.8, 0.5], hL: [0.2, 1.2, 0.3], yaw: 1.0, pyaw: 0.5,
      lean: 0.2, crouch: 0.18, fR: [0.26, 0, -0.14], fL: [-0.16, 0, 0.2] }),
    swing: [
      K({ t: 0, hR: [0.58, 0.9, 0.4], rd: [0.85, -0.1, 0.4], rn: [0, 0.6, 0.8], hL: [-0.3, 1.15, 0.1], yaw: 0.2,
        pyaw: 0.1, lean: 0.12, crouch: 0.1, fR: [0.26, 0, -0.14], fL: [-0.16, 0, 0.2] }),
      K({ t: 0.16, hR: [0.35, 1.5, 0.45], rd: [0.3, 0.9, 0.3], rn: [0, 0.4, 0.9], hL: [-0.3, 1.1, 0.05], yaw: -0.2,
        lean: 0, crouch: 0, fR: [0.26, 0, -0.14], fL: [-0.16, 0, 0.2] }),
      K({ t: 0.34, hR: [0.15, 1.85, 0.3], rd: [-0.1, 0.98, 0.1], hL: [-0.3, 1.05, 0.05], yaw: -0.45, lean: -0.06,
        crouch: -0.02, fR: [0.26, 0, -0.14], fL: [-0.16, 0, 0.2] }),
    ],
  },
  globo_r: {
    prep: K({ hR: [-0.42, 0.72, -0.22], rd: [-0.3, -0.45, -0.8], rn: [0, 0.8, 0.5], ag: 0.13, yaw: -1.1, pyaw: -0.5,
      lean: 0.2, crouch: 0.18, fR: [0.06, 0, 0.22], fL: [-0.26, 0, -0.12] }),
    swing: [
      K({ t: 0, hR: [-0.4, 0.9, 0.42], rd: [-0.85, -0.1, 0.4], rn: [0, 0.6, 0.8], ag: 0.13, yaw: -0.3, pyaw: -0.15,
        lean: 0.12, crouch: 0.1, fR: [0.06, 0, 0.22], fL: [-0.26, 0, -0.12] }),
      K({ t: 0.16, hR: [-0.05, 1.5, 0.45], rd: [-0.2, 0.9, 0.3], rn: [0, 0.4, 0.9], ag: 0.13, yaw: 0.2, lean: 0,
        crouch: 0, fR: [0.06, 0, 0.22], fL: [-0.26, 0, -0.12] }),
      K({ t: 0.34, hR: [0.25, 1.82, 0.25], rd: [0.2, 0.96, 0.1], ag: 0.13, yaw: 0.5, lean: -0.06, crouch: -0.02,
        fR: [0.06, 0, 0.22], fL: [-0.26, 0, -0.12] }),
    ],
  },
  volea: { // golpe corto de bloqueo, con paso adelante
    prep: K({ hR: [0.42, 1.28, 0.25], rd: [0.3, 0.9, 0], hL: [-0.15, 1.15, 0.35], yaw: 0.5, lean: 0.22,
      crouch: 0.12 }),
    swing: [
      K({ t: 0, hR: [0.52, 1.15, 0.52], rd: [0.6, 0.75, 0.1], rn: [0, 0.3, 0.95], hL: [-0.3, 1.1, 0.15], yaw: 0.25,
        lean: 0.28, crouch: 0.14, fR: [0.25, 0, -0.1], fL: [-0.12, 0, 0.32] }),
      K({ t: 0.18, hR: [0.42, 1.0, 0.62], rd: [0.5, 0.6, 0.5], rn: [0, 0.6, 0.8], hL: [-0.3, 1.1, 0.15], yaw: 0.1,
        lean: 0.3, crouch: 0.16, fR: [0.25, 0, -0.1], fL: [-0.12, 0, 0.36] }),
    ],
  },
  volea_r: {
    prep: K({ hR: [-0.2, 1.28, 0.3], rd: [-0.5, 0.85, 0], ag: 0.3, yaw: -0.6, lean: 0.22, crouch: 0.12 }),
    swing: [
      K({ t: 0, hR: [-0.3, 1.15, 0.52], rd: [-0.7, 0.7, 0.1], rn: [0, 0.3, 0.95], hL: [-0.4, 1.05, -0.1], yaw: -0.5,
        lean: 0.28, crouch: 0.14, fR: [0.1, 0, 0.32], fL: [-0.25, 0, -0.1] }),
      K({ t: 0.18, hR: [-0.12, 1.0, 0.62], rd: [-0.5, 0.6, 0.5], rn: [0, 0.6, 0.8], hL: [-0.42, 1.0, -0.2], yaw: -0.4,
        lean: 0.3, crouch: 0.16, fR: [0.1, 0, 0.36], fL: [-0.25, 0, -0.1] }),
    ],
  },
  saque: { // pose de trofeo, impacto arriba con salto, y terminacion cruzando el cuerpo
    prep: K({ hR: [0.32, 1.6, -0.22], rd: [-0.2, 0.95, -0.15], hL: [-0.05, 2.12, 0.33], yaw: 1.05, pyaw: 0.7,
      lean: -0.14, crouch: 0.16, fR: [0.16, 0, -0.16], fL: [-0.06, 0, 0.2] }),
    swing: [
      K({ t: 0, hR: [0.16, 2.3, 0.3], rd: [0, 1, 0.12], hL: [-0.2, 1.2, 0.18], yaw: 0.1, pyaw: 0.1, lean: 0.1,
        crouch: -0.04, salto: 0.14, fR: [0.16, 0, -0.2], fL: [-0.06, 0, 0.2] }),
      K({ t: 0.14, hR: [-0.05, 1.35, 0.62], rd: [-0.3, -0.45, 0.85], rn: [0, 0.8, 0.5], hL: [-0.22, 1.1, 0.15], yaw: -0.55,
        pyaw: -0.2, lean: 0.48, crouch: 0.02, salto: 0.1, fR: [0.2, 0.25, -0.35], fL: [-0.06, 0, 0.3] }),
      K({ t: 0.36, hR: [-0.36, 0.82, 0.25], rd: [-0.5, -0.6, -0.3], rn: [0.6, 0.6, 0], hL: [-0.22, 1.05, 0.15], yaw: -0.8,
        pyaw: -0.3, lean: 0.42, crouch: 0.1, fR: [0.22, 0.1, -0.3], fL: [-0.06, 0, 0.35] }),
    ],
  },
};
GOLPES.smash = GOLPES.saque;

const CAMPOS_V = ['hR', 'rd', 'rn', 'hL', 'fR', 'fL'];
const CAMPOS_N = ['ag', 'yaw', 'pyaw', 'lean', 'crouch', 'salto'];
function copiarPose(p) {
  const c = {};
  for (const k of CAMPOS_V) c[k] = [...p[k]];
  for (const k of CAMPOS_N) c[k] = p[k];
  return c;
}
function mezclar(dst, a, b, f) {
  for (const k of CAMPOS_V) for (let i = 0; i < 3; i++) dst[k][i] = a[k][i] + (b[k][i] - a[k][i]) * f;
  for (const k of CAMPOS_N) dst[k] = a[k] + (b[k] - a[k]) * f;
}

// ---------- Mallas ----------
const EJE_Y = new THREE.Vector3(0, 1, 0);
const liso = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.75, ...extra });

function malla(geo, material, padre) {
  const m = new THREE.Mesh(geo, material);
  m.castShadow = true;
  padre.add(m);
  return m;
}
function capsula(radio, largo, material, padre) {
  const m = malla(new THREE.CapsuleGeometry(radio, largo, 5, 12), material, padre);
  m.userData.largo = largo;
  return m;
}
// Hueso con perfil: `radios` va del extremo cercano al lejano, repartido parejo a lo largo.
function hueso(radios, largo, material, padre) {
  const n = radios.length - 1;
  const pts = radios.map((r, i) => new THREE.Vector2(r, (i / n - 0.5) * largo));
  pts.unshift(new THREE.Vector2(0.001, -0.5 * largo));
  pts.push(new THREE.Vector2(0.001, 0.5 * largo));
  const m = malla(new THREE.LatheGeometry(pts, 14), material, padre);
  m.userData.largo = largo;
  return m;
}
const _d = new THREE.Vector3();
// Estira una capsula o un hueso entre dos puntos.
function tender(m, a, b) {
  _d.subVectors(b, a);
  const len = _d.length() || 0.001;
  m.position.addVectors(a, b).multiplyScalar(0.5);
  m.quaternion.setFromUnitVectors(EJE_Y, _d.divideScalar(len));
  m.scale.y = len / m.userData.largo;
}

// Cinematica inversa de dos huesos: dado el hombro (o la cadera) y el objetivo, deja el codo (o la
// rodilla) en `codo` y el extremo alcanzable en `fin`. `polo` dice hacia donde se dobla.
const _p = new THREE.Vector3(), _dir = new THREE.Vector3();
function ik(origen, objetivo, l1, l2, polo, codo, fin) {
  _dir.subVectors(objetivo, origen);
  const dist = Math.max(0.08, Math.min(l1 + l2 - 0.004, _dir.length()));
  _dir.normalize();
  fin.copy(origen).addScaledVector(_dir, dist);
  const a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist);
  const h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
  _p.copy(polo).addScaledVector(_dir, -polo.dot(_dir));
  if (_p.lengthSq() < 1e-6) _p.set(0, 0, 1);
  _p.normalize();
  codo.copy(origen).addScaledVector(_dir, a).addScaledVector(_p, h);
}

const BRAZO = 0.30, ANTEBRAZO = 0.27, MUSLO = 0.46, PIERNA = 0.44, CADERA_Y = 0.96, TOBILLO = 0.075;

let texturaCuerdas = null;
function cuerdas() {
  if (texturaCuerdas) return texturaCuerdas;
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  g.strokeStyle = 'rgba(255,255,255,0.9)';
  g.lineWidth = 1.5;
  for (let i = 4; i < 128; i += 9) {
    g.beginPath(); g.moveTo(i, 0); g.lineTo(i, 128); g.stroke();
    g.beginPath(); g.moveTo(0, i); g.lineTo(128, i); g.stroke();
  }
  texturaCuerdas = new THREE.CanvasTexture(c);
  return texturaCuerdas;
}

// Raqueta armada a lo largo de +Y desde la mano; el encordado mira a +Z.
function crearRaqueta(padre) {
  const r = new THREE.Group();
  const marco = liso(0x18181c, { roughness: 0.35, metalness: 0.3 });
  const grip = malla(new THREE.CylinderGeometry(0.017, 0.019, 0.2, 10), liso(0xf2f2f2), r);
  grip.position.y = 0.04;
  for (const s of [-1, 1]) {
    const v = malla(new THREE.CylinderGeometry(0.009, 0.011, 0.2, 8), marco, r);
    v.position.set(s * 0.032, 0.235, 0);
    v.rotation.z = -s * 0.33;
  }
  const aro = malla(new THREE.TorusGeometry(0.13, 0.011, 8, 28), marco, r);
  aro.scale.set(0.9, 1.25, 1);
  aro.position.y = 0.49;
  const red = new THREE.Mesh(new THREE.CircleGeometry(0.125, 24),
    new THREE.MeshBasicMaterial({ map: cuerdas(), transparent: true, side: THREE.DoubleSide, depthWrite: false }));
  red.scale.set(0.9, 1.25, 1);
  red.position.y = 0.49;
  r.add(red);
  padre.add(r);
  return r;
}

export class Jugador {
  constructor(datos, indice, scene) {
    this.datos = datos;
    this.indice = indice;
    this.x = 0; this.z = lado(indice) * 12.5;
    this.vx = 0; this.vz = 0;
    this.energia = 1;
    this.velMax = 4.7 + datos.attrs.velocidad * 0.29;
    this.anim = null;                 // { clave, fase: 'prep' | 'swing', t }
    this.pose = copiarPose(LISTO);    // pose actual, suavizada
    this.meta = copiarPose(LISTO);
    this.paso = 0; this.correr = 0; this.reloj = Math.random() * 10;
    this.s = datos.zurdo ? 1 : -1;    // el modelo mira a +z, asi que su derecha es -x
    this.#armar(scene);
    this.dibujar(0);
  }

  #armar(scene) {
    const d = this.datos, s = this.s;
    const piel = liso(d.piel, { roughness: 0.6 });
    const remera = liso(0xffffff), short = liso(0xf1f1ec), zapa = liso(0xfafafa, { roughness: 0.5 });
    const g = this.grupo = new THREE.Group();
    g.scale.setScalar(d.altura / 1.85);
    if (this.indice === 0) g.rotation.y = Math.PI; // el usuario mira a la red, de espaldas a la camara

    // Tronco: gira y se inclina entero; la cabeza compensa para seguir mirando al frente.
    this.tronco = new THREE.Group();
    this.tronco.rotation.order = 'YXZ';
    g.add(this.tronco);
    // Torso de una pieza: cintura, pecho mas ancho, hombros que cierran hacia el cuello.
    const perfil = [[0.001, -0.04], [0.118, -0.03], [0.128, 0.04], [0.122, 0.14], [0.136, 0.26], [0.15, 0.36],
      [0.146, 0.43], [0.112, 0.485], [0.058, 0.52], [0.001, 0.53]].map(([r, y]) => new THREE.Vector2(r, y));
    const torso = malla(new THREE.LatheGeometry(perfil, 20), remera, this.tronco);
    torso.scale.set(1.24, 1, 0.74);
    for (const i of [-1, 1]) {
      const h = malla(new THREE.SphereGeometry(0.056, 12, 10), d.sinMangas ? piel : remera, this.tronco);
      h.position.set(i * 0.19, 0.455, 0);
    }
    const cuello = malla(new THREE.CylinderGeometry(0.043, 0.05, 0.12, 10), piel, this.tronco);
    cuello.position.y = 0.56;

    this.cabeza = new THREE.Group();
    this.cabeza.position.y = 0.715;
    this.tronco.add(this.cabeza);
    const craneo = malla(new THREE.SphereGeometry(0.105, 18, 14), piel, this.cabeza);
    craneo.scale.set(0.93, 1.14, 1);
    const pelo = malla(new THREE.SphereGeometry(0.111, 18, 12, 0, Math.PI * 2, 0, Math.PI * 0.56), liso(d.pelo, { roughness: 0.9 }), this.cabeza);
    pelo.scale.set(0.95, 1.14, 1.02);
    pelo.rotation.x = -0.42;
    const nariz = malla(new THREE.ConeGeometry(0.014, 0.04, 6), piel, this.cabeza);
    nariz.position.set(0, -0.012, 0.105);
    nariz.rotation.x = Math.PI / 2;
    for (const i of [-1, 1]) {
      const ojo = malla(new THREE.SphereGeometry(0.011, 6, 6), liso(0x1a1a1a), this.cabeza);
      ojo.position.set(i * 0.038, 0.018, 0.094);
      const oreja = malla(new THREE.SphereGeometry(0.02, 6, 6), piel, this.cabeza);
      oreja.position.set(i * 0.098, 0, 0);
    }
    if (d.vincha) {
      const v = malla(new THREE.TorusGeometry(0.1, 0.014, 6, 20), liso(d.vincha), this.cabeza);
      v.rotation.x = Math.PI / 2 - 0.12;
      v.scale.set(0.95, 1.02, 1.6);
      v.position.y = 0.055;
    }
    if (d.gorra) {
      const copa = malla(new THREE.SphereGeometry(0.115, 16, 10, 0, Math.PI * 2, 0, Math.PI * 0.42), liso(d.gorra), this.cabeza);
      copa.scale.set(0.95, 1.1, 1.02);
      copa.position.y = 0.012;
      const visera = malla(new THREE.CylinderGeometry(0.085, 0.085, 0.012, 14, 1, false, -Math.PI / 2, Math.PI), liso(d.gorra), this.cabeza);
      visera.position.set(0, 0.058, 0.085);
      visera.rotation.y = Math.PI / 2;
    }

    this.caderaMalla = malla(new THREE.SphereGeometry(0.15, 16, 12), short, g);
    this.caderaMalla.scale.set(1.08, 0.72, 0.76);

    // Brazos y piernas: capsulas que se tienden entre las articulaciones calculadas en cada cuadro.
    const brazo = (conRaqueta) => ({
      alto: hueso([0.05, 0.051, 0.046, 0.04], BRAZO, piel, g),
      manga: d.sinMangas ? null : hueso([0.058, 0.06, 0.06], BRAZO * 0.5, remera, g),
      bajo: hueso([0.04, 0.043, 0.036, 0.029], ANTEBRAZO, piel, g),
      codo: malla(new THREE.SphereGeometry(0.04, 10, 8), piel, g),
      mano: malla(new THREE.SphereGeometry(0.042, 10, 8), piel, g),
      banda: conRaqueta && d.muniequera ? capsula(0.045, 0.04, liso(d.muniequera), g) : null,
    });
    this.brazoR = brazo(true);
    this.brazoL = brazo(false);
    const pierna = () => {
      const p = {
        muslo: hueso([0.086, 0.088, 0.078, 0.064, 0.056], MUSLO, piel, g),
        short: hueso([0.098, 0.102, 0.1, 0.098], MUSLO * 0.56, short, g),
        rodilla: malla(new THREE.SphereGeometry(0.056, 10, 8), piel, g),
        canilla: hueso([0.052, 0.062, 0.058, 0.044, 0.036], PIERNA, piel, g),
        media: hueso([0.041, 0.04, 0.042], PIERNA * 0.2, zapa, g),
        pie: new THREE.Group(),
      };
      const z1 = malla(new THREE.CapsuleGeometry(0.052, 0.15, 5, 10), zapa, p.pie);
      z1.rotation.x = Math.PI / 2;
      z1.scale.set(1, 1, 0.78);
      z1.position.set(0, -0.03, 0.05);
      const suela = malla(new THREE.BoxGeometry(0.095, 0.022, 0.25), liso(0xd8d8d2), p.pie);
      suela.position.set(0, -0.064, 0.05);
      g.add(p.pie);
      return p;
    };
    this.piernaR = pierna();
    this.piernaL = pierna();
    this.raqueta = crearRaqueta(g);
    scene.add(g);
  }

  // ---------- Movimiento ----------
  // dx, dz: direccion deseada (no hace falta normalizar). factor: fraccion de la velocidad maxima.
  mover(dx, dz, dt, factor = 1) {
    const n = Math.hypot(dx, dz);
    const vmax = this.velMax * factor * (0.8 + 0.2 * this.energia);
    const ox = n > 0.01 ? dx / n * vmax * Math.min(1, n) : 0;
    const oz = n > 0.01 ? dz / n * vmax * Math.min(1, n) : 0;
    const a = 30 * dt;
    this.vx += Math.max(-a, Math.min(a, ox - this.vx));
    this.vz += Math.max(-a, Math.min(a, oz - this.vz));
    const L = lado(this.indice);
    const x0 = this.x, z0 = this.z;
    this.x = Math.max(-LIMITE_X, Math.min(LIMITE_X, this.x + this.vx * dt));
    this.z = L * Math.max(0.7, Math.min(LIMITE_Z, (this.z + this.vz * dt) * L));
    const dist = Math.hypot(this.x - x0, this.z - z0);
    this.energia = Math.max(0, this.energia - dist * 0.0035 * (1.5 - this.datos.attrs.resistencia / 10));
    return dist;
  }

  // Corre hacia un punto y frena al llegar.
  irA(x, z, dt, factor = 1) {
    const dx = x - this.x, dz = z - this.z;
    const n = Math.hypot(dx, dz);
    if (n < 0.12) return this.mover(0, 0, dt, factor);
    const f = Math.min(1, n / 0.8);
    return this.mover(dx / n * f, dz / n * f, dt, factor);
  }

  colocar(x, z) { this.x = x; this.z = z; this.vx = this.vz = 0; }

  descansar(cuanto) { this.energia = Math.min(1, this.energia + cuanto); }

  // ---------- Animacion ----------
  // tipo: drive, reves, dropshot, globo, volea, smash, saque. deReves: la pelota viene del lado del reves.
  #clave(tipo, deReves) {
    if (tipo === 'reves') return this.datos.dosManos ? 'reves' : 'reves1';
    if (deReves && GOLPES[tipo + '_r']) return tipo + '_r';
    return GOLPES[tipo] ? tipo : 'drive';
  }

  preparar(tipo, deReves = false) {
    if (this.anim?.fase === 'swing') return;
    const clave = this.#clave(tipo, deReves);
    if (this.anim?.clave !== clave) this.anim = { clave, fase: 'prep', t: 0 };
  }

  pegar(tipo, deReves = false) { this.anim = { clave: this.#clave(tipo, deReves), fase: 'swing', t: 0 }; }

  soltar() { if (this.anim?.fase === 'prep') this.anim = null; }

  // Deja la figura clavada en un momento de un golpe (para mirar las poses).
  posar(tipo, deReves, fase, t = 0) {
    this.anim = { clave: this.#clave(tipo, deReves), fase, t };
    this.#meta(0);
    this.pose = copiarPose(this.meta);
    this.#esqueleto(0);
  }

  #meta(dt) {
    const a = this.anim;
    if (!a) { mezclar(this.meta, LISTO, LISTO, 0); return 7; }
    const g = GOLPES[a.clave];
    a.t += dt;
    if (a.fase === 'prep') { mezclar(this.meta, g.prep, g.prep, 0); return 11; }
    const k = g.swing;
    const fin = k[k.length - 1].t;
    if (a.t >= fin + 0.16) { this.anim = null; mezclar(this.meta, LISTO, LISTO, 0); return 7; }
    let i = 0;
    while (i < k.length - 2 && a.t > k[i + 1].t) i++;
    const u = Math.max(0, Math.min(1, (a.t - k[i].t) / (k[i + 1].t - k[i].t)));
    mezclar(this.meta, k[i], k[i + 1], u * u * (3 - 2 * u));
    return a.t < 0.05 ? 60 : 30; // llega al impacto de un latigazo y despues acompania
  }

  dibujar(dt) {
    const rapidez = this.#meta(dt);
    mezclar(this.pose, this.pose, this.meta, Math.min(1, rapidez * dt));
    this.#esqueleto(dt);
  }

  #esqueleto(dt) {
    const g = this.grupo, p = this.pose, s = this.s;
    g.position.set(this.x, 0, this.z);
    this.reloj += dt;

    // Carrera: los pies recorren una zancada en la direccion del movimiento (el cuerpo sigue mirando a la red).
    const giro = this.indice === 0 ? -1 : 1;
    const lvx = this.vx * giro, lvz = this.vz * giro;
    const v = Math.hypot(lvx, lvz);
    this.correr += (Math.min(1, v / 2.5) - this.correr) * Math.min(1, 10 * dt);
    this.paso += v * dt * 2.7;
    const c = this.correr;
    const zancada = Math.min(0.36, 0.065 * v) * c, alza = Math.min(0.2, 0.04 * v) * c;
    const ux = v > 0.01 ? lvx / v : 0, uz = v > 0.01 ? lvz / v : 0;
    const enEspera = !this.anim && c < 0.2;
    const rebote = enEspera ? Math.abs(Math.sin(this.reloj * 5.5)) * 0.018 : 0;

    const salto = p.salto;
    const P = v1.set(0, CADERA_Y - p.crouch + salto + rebote + Math.abs(Math.sin(this.paso)) * 0.03 * c, 0);
    this.tronco.position.copy(P);
    this.tronco.rotation.set(p.lean + 0.1 * c * uz, s * p.yaw, 0.08 * c * ux * -1);
    this.cabeza.rotation.set(-p.lean * 0.7, -s * p.yaw * 0.62, 0);
    this.caderaMalla.position.copy(P).y -= 0.01;
    this.caderaMalla.rotation.y = s * p.pyaw;

    // Brazos.
    const mano = (h) => v2.set(s * h[0], h[1] + salto + rebote, h[2]);
    const rd = v3.set(s * p.rd[0], p.rd[1], p.rd[2]).normalize();
    this.#brazo(this.brazoR, s, mano(p.hR), vManoR);
    this.raqueta.position.copy(vManoR).addScaledVector(rd, -0.02);
    // Base de la raqueta: Y a lo largo, Z lo mas parecido posible a hacia donde mira el encordado.
    const n = v4.set(s * p.rn[0], p.rn[1], p.rn[2]);
    n.addScaledVector(rd, -n.dot(rd));
    if (n.lengthSq() < 1e-4) n.set(0, 1, 0).addScaledVector(rd, -rd.y);
    n.normalize();
    const lateral = v5.crossVectors(rd, n);
    m4.makeBasis(lateral, rd, n);
    this.raqueta.quaternion.setFromRotationMatrix(m4);

    const agarre = Math.min(1, p.ag / 0.1);
    const libre = mano(p.hL);
    if (agarre > 0) libre.lerp(v6.copy(vManoR).addScaledVector(rd, Math.max(p.ag, 0.1)), agarre);
    this.#brazo(this.brazoL, -s, libre, vManoL);

    // Piernas.
    this.#pierna(this.piernaR, s, p.fR, p.pyaw, salto, ux, uz, zancada, alza, this.paso, P);
    this.#pierna(this.piernaL, -s, p.fL, p.pyaw, salto, ux, uz, zancada, alza, this.paso + Math.PI, P);
  }

  #brazo(b, signo, objetivo, manoOut) {
    const hombro = v7.set(signo * 0.2, 0.46, 0).applyEuler(this.tronco.rotation).add(this.tronco.position);
    const polo = v8.set(signo * 0.35, -1, -0.55);
    ik(hombro, objetivo, BRAZO, ANTEBRAZO, polo, vCodo, manoOut);
    tender(b.alto, hombro, vCodo);
    if (b.manga) tender(b.manga, hombro, v9.lerpVectors(hombro, vCodo, 0.5));
    tender(b.bajo, vCodo, manoOut);
    b.codo.position.copy(vCodo);
    b.mano.position.copy(manoOut);
    if (b.banda) tender(b.banda, v9.lerpVectors(vCodo, manoOut, 0.74), v10.lerpVectors(vCodo, manoOut, 0.9));
  }

  #pierna(q, signo, pie, pyaw, salto, ux, uz, zancada, alza, fase, P) {
    const s = this.s;
    const cadera = v7.set(signo * 0.105, -0.03, 0).applyAxisAngle(EJE_Y, s * pyaw).add(P);
    const sube = Math.max(0, Math.sin(fase));
    const tobillo = v8.set(
      s * pie[0] - ux * zancada * Math.cos(fase),
      pie[1] + salto + TOBILLO + sube * alza,
      pie[2] - uz * zancada * Math.cos(fase));
    const polo = v9.set(signo * 0.15, 0.1, 1);
    ik(cadera, tobillo, MUSLO, PIERNA, polo, vCodo, vFin);
    tender(q.muslo, cadera, vCodo);
    tender(q.short, cadera, v10.lerpVectors(cadera, vCodo, 0.56));
    tender(q.canilla, vCodo, vFin);
    tender(q.media, v10.lerpVectors(vCodo, vFin, 0.8), vFin);
    q.rodilla.position.copy(vCodo);
    q.pie.position.copy(vFin);
    q.pie.rotation.set(sube * alza * 3 + Math.min(0.9, (pie[1] + salto) * 3), signo * 0.14, 0);
  }
}

const v1 = new THREE.Vector3(), v2 = new THREE.Vector3(), v3 = new THREE.Vector3(), v4 = new THREE.Vector3(),
  v5 = new THREE.Vector3(), v6 = new THREE.Vector3(), v7 = new THREE.Vector3(), v8 = new THREE.Vector3(),
  v9 = new THREE.Vector3(), v10 = new THREE.Vector3();
const vManoR = new THREE.Vector3(), vManoL = new THREE.Vector3(), vCodo = new THREE.Vector3(), vFin = new THREE.Vector3();
const m4 = new THREE.Matrix4();
