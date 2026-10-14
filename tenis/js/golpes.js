// Los golpes: cuando se puede pegar, a donde se apunta y con que velocidad sale la pelota.
// La velocidad inicial se resuelve simulando el vuelo (hay arrastre y efecto, no hay formula cerrada).
import {
  MEDIO_ANCHO, MEDIO_LARGO, SAQUE, POSTE_X, RADIO_PELOTA as R, alturaRed, lado,
} from './cancha.js';
import { G, ARRASTRE, MAGNUS } from './pelota.js';

// ang0: angulo de salida minimo (grados). El calculo lo sube hasta pasar la red sin exceder la velocidad.
// vBase + vPot * atributo potencia = velocidad maxima (m/s). sigma: dispersion base en metros.
const GOLPES = {
  drive:    { ang0: 3,   vBase: 24, vPot: 1.85, spin: 0.45, sigma: 0.52, margen: 0.22, nombre: 'Drive' },
  reves:    { ang0: 3,   vBase: 23, vPot: 1.6, spin: 0.35,  sigma: 0.56, margen: 0.22, nombre: 'Revés' },
  // Slice: mas lento y seguro, flota y pica bajo. Estirado casi no pierde precision (es el golpe de defensa).
  slice:    { ang0: 5,   vBase: 19.5, vPot: 0.9, spin: -0.55, sigma: 0.44, margen: 0.25, estirado: 0.25, nombre: 'Slice' },
  dropshot: { ang0: 14,  vBase: 20, vPot: 0,   spin: -0.85, sigma: 0.42, margen: 0.22, nombre: 'Dropshot' },
  globo:    { ang0: 46,  vBase: 32, vPot: 0,   spin: 0.3,   sigma: 0.75, margen: 2.0,  nombre: 'Globo' },
  volea:    { ang0: -8,  vBase: 17, vPot: 1.15, spin: -0.25, sigma: 0.50, margen: 0.18, nombre: 'Volea' },
  smash:    { ang0: -32, vBase: 32, vPot: 2.05, spin: 0,    sigma: 0.65, margen: 0.25, nombre: 'Smash' },
};
export const nombreGolpe = (tipo) => GOLPES[tipo]?.nombre ?? 'Saque';

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
function gauss() {
  let u = 0;
  for (let i = 0; i < 4; i++) u += Math.random();
  return (u - 2) * 1.73;
}

// Vuelo en el plano vertical del tiro: devuelve donde cae y a que altura cruza la red.
function vuelo(oy, ang, v, spin, dRed) {
  let s = 0, y = oy, vs = v * Math.cos(ang), vy = v * Math.sin(ang);
  let yRed = dRed <= 0 ? Infinity : null;
  const dt = 1 / 120;
  for (let i = 0; i < 1200; i++) {
    const k = ARRASTRE * Math.hypot(vs, vy);
    vs -= k * vs * dt;
    vy -= (G + k * vy + MAGNUS * spin * vs) * dt;
    const s0 = s, y0 = y;
    s += vs * dt; y += vy * dt;
    if (yRed === null && s >= dRed) yRed = y0 + (y - y0) * (dRed - s0) / (s - s0);
    if (y <= R) return { alcance: s, yRed: yRed ?? -1 };
  }
  return { alcance: s, yRed: yRed ?? -1 };
}

// Velocidad inicial para ir de `o` a `obj` con el tiro mas tendido que pase la red sin superar vmax.
function resolver(o, obj, spin, ang0, vmax, margen) {
  const dx = obj.x - o.x, dz = obj.z - o.z;
  const D = Math.hypot(dx, dz);
  const cruza = (o.z > 0) !== (obj.z > 0);
  const f = cruza ? Math.abs(o.z) / Math.abs(dz) : -1;
  const xRed = o.x + dx * f;
  const dRed = cruza && Math.abs(xRed) < POSTE_X ? D * f : -1;
  const hRed = dRed > 0 ? alturaRed(xRed) + R + margen : -Infinity;

  let elegido = null, reserva = null;
  for (let grados = ang0; grados <= 72; grados += 1.5) {
    const ang = grados * Math.PI / 180;
    let lo = 2, hi = 95;
    for (let i = 0; i < 17; i++) {
      const mid = (lo + hi) / 2;
      if (vuelo(o.y, ang, mid, spin, dRed).alcance < D) lo = mid; else hi = mid;
    }
    const r = vuelo(o.y, ang, hi, spin, dRed);
    if (Math.abs(r.alcance - D) > 0.4) continue;
    if (r.yRed >= hRed) {
      if (hi <= vmax) { elegido = { ang, v: hi }; break; }
      if (!reserva || hi < reserva.v) reserva = { ang, v: hi };
    }
  }
  const s = elegido ?? reserva ?? { ang: 0.6, v: Math.min(vmax, 20) };
  const vh = s.v * Math.cos(s.ang);
  return { vx: vh * dx / D, vy: s.v * Math.sin(s.ang), vz: vh * dz / D, v: s.v };
}

// Devuelve null si la pelota no esta al alcance, o los datos del contacto.
export function puedeGolpear(jug, e) {
  const L = lado(jug.indice);
  if (e.z * L <= 0) return null;
  const alcance = 1.15 + jug.datos.altura * 0.25;
  const dx = e.x - jug.x, dz = e.z - jug.z;
  if (Math.abs(dx) > alcance || Math.abs(dz) > 0.9) return null;
  if (e.y < 0.05 || e.y > 1.05 + jug.datos.altura) return null;
  return {
    derecha: dx * L > 0, // del lado derecho del cuerpo del jugador
    estirado: clamp((Math.abs(dx) - 0.7) / (alcance - 0.7), 0, 1),
    alto: e.y > 2.05,
  };
}

// Punto de la cancha rival al que se apunta, antes de sumarle el error.
export function objetivo(jug, tipo, apX, apZ) {
  let prof;
  if (tipo === 'dropshot') prof = 1.7 + (10 - jug.datos.attrs.toque) * 0.14 + (apZ + 1) * 0.3;
  else if (tipo === 'globo') prof = MEDIO_LARGO - 2.0 + apZ * 0.6;
  else if (tipo === 'smash') prof = MEDIO_LARGO - 4.5 + apZ * 1.5;
  else if (tipo === 'volea') prof = MEDIO_LARGO - 3.6 + apZ * 1.8;
  else prof = MEDIO_LARGO - 2.6 + apZ * 1.5;
  return { x: apX * (MEDIO_ANCHO - 0.8), z: -lado(jug.indice) * prof };
}

// op: { tecla: 'golpe'|'slice'|'dropshot'|'globo', apX: -1..1 (x del mundo), apZ: -1 corto..1 profundo,
//       potencia: 0..1, calidad: 0..1, error: multiplicador de dispersion (maquina) }
export function ejecutarGolpe(jug, pelota, contacto, op) {
  const e = pelota.e, d = jug.datos, a = d.attrs;
  const L = lado(jug.indice);
  const potencia = clamp(op.potencia ?? 0.6, 0, 1);
  const calidad = clamp(op.calidad ?? 1, 0, 1);
  const apX = clamp(op.apX ?? 0, -1, 1), apZ = clamp(op.apZ ?? 0, -1, 1);
  const enRed = Math.abs(jug.z) < 5.5;

  let tipo;
  if (op.tecla === 'dropshot') tipo = 'dropshot';
  else if (op.tecla === 'globo') tipo = 'globo';
  else if (op.tecla === 'slice') tipo = 'slice';
  else if (contacto.alto) tipo = 'smash';
  else if (e.piques === 0 && enRed) tipo = 'volea';
  else tipo = (contacto.derecha !== !!d.zurdo) ? 'drive' : 'reves';
  const g = GOLPES[tipo];

  const obj = objetivo(jug, tipo, apX, apZ);

  const fino = tipo === 'dropshot' || tipo === 'globo' || tipo === 'volea' ? a.toque : a.precision;
  const velEntrada = Math.hypot(e.vx, e.vz);
  const sigma = g.sigma * (1.75 - 0.11 * fino) * (op.error ?? 1) *
    (1 + 0.9 * (1 - calidad) + 0.5 * potencia * potencia + (g.estirado ?? 0.7) * contacto.estirado + velEntrada / 80);
  obj.x += gauss() * sigma;
  obj.z += gauss() * sigma * 1.3;

  const vmax = (g.vBase + g.vPot * a.potencia) *
    (g.vPot ? 0.55 + 0.45 * potencia : 1) * (1 - 0.25 * contacto.estirado);
  let spin = g.spin * (g.spin > 0 ? (d.topspin ?? 1) : 1);
  spin = clamp(spin, -1, 1);
  const s = resolver(e, obj, spin, g.ang0, vmax, g.margen);

  // Error a la red: mas probable con mal timing, estirado o pegando a fondo.
  const pRed = 0.012 * (op.error ?? 1) * (1 + 4 * (1 - calidad) + 2 * contacto.estirado + potencia);
  if (tipo !== 'globo' && Math.random() < pRed) s.vy -= 0.09 * s.v;

  Object.assign(e, { vx: s.vx, vy: s.vy, vz: s.vz, spin, piques: 0, rodando: false });
  return { tipo, kmh: Math.round(s.v * 3.6) };
}

// op: { apX: -1|0|1 (hacia donde, en x del mundo), calidad: 0..1, segundo: bool, fuerza: fraccion de la velocidad (maquina) }
export function ejecutarSaque(jug, pelota, op) {
  const e = pelota.e, a = jug.datos.attrs;
  const L = lado(jug.indice);
  const segundo = !!op.segundo;
  const calidad = clamp(op.calidad ?? 1, 0, 1);
  const sx = Math.sign(jug.x) || 1;
  const borde = segundo ? 0.75 : 0.45;
  const obj = {
    x: -sx * clamp(2.06 - sx * clamp(op.apX ?? 0, -1, 1) * 1.45, borde, MEDIO_ANCHO - borde),
    z: -L * (SAQUE - (segundo ? 1.5 : 0.7)),
  };
  const sigma = (segundo ? 0.36 : 0.6) * (1.7 - 0.1 * a.saque) * (op.error ?? 1) * (1 + 1.3 * (1 - calidad));
  obj.x += gauss() * sigma;
  obj.z += gauss() * sigma * 1.25;

  const vmax = (42 + 2.2 * a.saque) * (segundo ? 0.78 : 1) * (0.72 + 0.28 * calidad) * (op.fuerza ?? 1);
  const spin = segundo ? 0.7 : 0.6;
  const s = resolver(e, obj, spin, -16, vmax, segundo ? 0.3 : 0.06);
  const pRed = (segundo ? 0.025 : 0.09) * (op.error ?? 1) * (1 + 2 * (1 - calidad));
  if (Math.random() < pRed) s.vy -= 0.05 * s.v;

  Object.assign(e, { vx: s.vx, vy: s.vy, vz: s.vz, spin, piques: 0, rodando: false });
  return { tipo: 'saque', kmh: Math.round(s.v * 3.6) };
}

// Donde tiene que picar un saque para ser bueno.
export function saqueBueno(x, z, sacador, xSacador) {
  const L = lado(sacador);
  const sx = Math.sign(xSacador) || 1;
  const t = 0.04; // la linea es buena
  return z * L < 0 && Math.abs(z) <= SAQUE + t && x * sx <= t && Math.abs(x) <= MEDIO_ANCHO + t;
}

export function pelotaBuena(x, z, golpeador) {
  const t = 0.04;
  return z * lado(golpeador) < 0 && Math.abs(z) <= MEDIO_LARGO + t && Math.abs(x) <= MEDIO_ANCHO + t;
}
