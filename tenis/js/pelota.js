// Fisica de la pelota. El estado es un objeto plano {x,y,z,vx,vy,vz,spin,curva,piques,rodando}
// para poder copiarlo y simular hacia adelante (lo usan la maquina y el calculo de los golpes).
import * as THREE from 'three';
import { RADIO_PELOTA as R, POSTE_X, alturaRed } from './cancha.js';

export const G = 9.81;
export const ARRASTRE = 0.018; // 1/m: desaceleracion = ARRASTRE * v^2
export const MAGNUS = 0.2;     // spin +1 (topspin) hunde la pelota, -1 (slice) la hace flotar
// curva: efecto lateral del saque. Negativa dobla hacia la izquierda de quien pega, positiva a la derecha.
export const MAGNUS_LATERAL = 0.2;
export const PASO = 1 / 120;

// Cesped: pique bajo y rapido.
const RESTITUCION = 0.70;
const ROCE_PIQUE = 0.82;

export function estadoNuevo() {
  return { x: 0, y: 1, z: 0, vx: 0, vy: 0, vz: 0, spin: 0, curva: 0, piques: 0, rodando: false };
}

// Avanza un paso. Devuelve 'pique', 'red' (queda del mismo lado), 'cinta' (pasa rozando) o null.
export function avanzar(e, dt) {
  if (e.rodando) {
    const f = Math.max(0, 1 - 1.8 * dt);
    e.vx *= f; e.vz *= f;
    const z0 = e.z;
    e.x += e.vx * dt; e.z += e.vz * dt;
    if ((z0 > 0) !== (e.z > 0) && Math.abs(e.x) < POSTE_X) { e.z = z0; e.vz = 0; e.vx = 0; }
    return null;
  }
  const v = Math.hypot(e.vx, e.vy, e.vz);
  const vh = Math.hypot(e.vx, e.vz);
  const k = ARRASTRE * v;
  const c = MAGNUS_LATERAL * (e.curva || 0);
  const vx = e.vx;
  e.vx -= (k * e.vx + c * e.vz) * dt;
  e.vz -= (k * e.vz - c * vx) * dt;
  e.vy -= (G + k * e.vy + MAGNUS * e.spin * vh) * dt;

  const x0 = e.x, y0 = e.y, z0 = e.z;
  e.x += e.vx * dt; e.y += e.vy * dt; e.z += e.vz * dt;
  let evento = null;

  if ((z0 > 0) !== (e.z > 0)) {
    const f = z0 / (z0 - e.z);
    const xc = x0 + (e.x - x0) * f, yc = y0 + (e.y - y0) * f;
    const h = alturaRed(xc);
    if (Math.abs(xc) < POSTE_X && yc < h + R) {
      if (yc > h - 0.025) {
        // De cinta: pierde casi toda la velocidad y cae del otro lado.
        e.y = h + R; e.vz *= 0.5; e.vx *= 0.6; e.vy = Math.abs(e.vy) * 0.3 + 1.0; e.spin = 0; e.curva = 0;
        evento = 'cinta';
      } else {
        e.x = xc; e.y = yc; e.z = z0 > 0 ? 0.06 : -0.06;
        e.vz *= -0.08; e.vx *= 0.2; e.vy = Math.min(e.vy, 0) * 0.3; e.spin = 0; e.curva = 0;
        evento = 'red';
      }
    }
  }

  if (e.y < R && e.vy < 0) {
    e.y = R;
    e.piques++;
    evento = 'pique';
    if (e.vy > -0.9) {
      e.vy = 0; e.rodando = true;
    } else {
      e.vy = -e.vy * RESTITUCION * (1 + 0.15 * e.spin);
      // Mucho efecto hacia atras (dropshot) frena la pelota contra el pasto: pica y se queda.
      // Con menos efecto (slice, volea) pasa lo contrario: patina y sale baja.
      const roce = ROCE_PIQUE * (e.spin < -0.7 ? 1 + 0.3 * e.spin : e.spin < 0 ? 1 - 0.12 * e.spin : 1);
      e.vx *= roce; e.vz *= roce;
      // El efecto lateral muerde el pasto: la pelota sale para el costado al picar.
      if (e.curva) {
        const h = Math.hypot(e.vx, e.vz) || 1;
        const lat = 1.8 * e.curva, vx2 = e.vx;
        e.vx -= lat * e.vz / h;
        e.vz += lat * vx2 / h;
      }
      e.spin *= 0.4;
      e.curva = (e.curva || 0) * 0.3;
    }
  }
  return evento;
}

// Simula hacia adelante sin tocar el estado real. Corta en el segundo pique o en la red.
export function trayectoria(e0, tMax = 5) {
  const e = { ...e0 };
  const muestras = [];
  let primerPique = null, red = false;
  for (let t = 0, i = 0; t < tMax; t += PASO, i++) {
    const ev = avanzar(e, PASO);
    if (ev === 'red') { red = true; break; }
    if (ev === 'pique') {
      if (!primerPique && e.piques === e0.piques + 1) primerPique = { x: e.x, z: e.z, t };
      if (e.piques >= e0.piques + 2) break;
    }
    if (i % 2 === 0) muestras.push({ t, x: e.x, y: e.y, z: e.z, vy: e.vy, piques: e.piques - e0.piques });
  }
  return { muestras, primerPique, red };
}

// Fieltro amarillo con la costura blanca en forma de S que da la vuelta a la pelota.
function texturaPelota() {
  const c = document.createElement('canvas');
  c.width = 256; c.height = 128;
  const g = c.getContext('2d');
  g.fillStyle = '#d6ee3c';
  g.fillRect(0, 0, 256, 128);
  for (let i = 0; i < 2600; i++) {
    g.fillStyle = Math.random() < 0.5 ? 'rgba(255,255,190,0.18)' : 'rgba(90,110,10,0.14)';
    g.fillRect(Math.random() * 256, Math.random() * 128, 2, 2);
  }
  g.strokeStyle = '#f6f8ea';
  g.lineWidth = 7;
  g.beginPath();
  for (let x = 0; x <= 256; x += 2) {
    const y = 64 + 38 * Math.sin((x / 256) * Math.PI * 4);
    if (x === 0) g.moveTo(x, y); else g.lineTo(x, y);
  }
  g.stroke();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

const ESTELA = 9;
const _eje = new THREE.Vector3(), _q = new THREE.Quaternion(), ARRIBA = new THREE.Vector3(0, 1, 0);

export class Pelota {
  constructor(scene) {
    this.e = estadoNuevo();
    this.malla = new THREE.Mesh(
      new THREE.SphereGeometry(R * 1.6, 18, 12), // algo mas grande que la real para que se lea
      new THREE.MeshStandardMaterial({ map: texturaPelota(), emissive: 0x4a5a08, roughness: 0.75 }));
    this.malla.castShadow = true;
    // Sombra falsa: es lo que deja leer la altura de la pelota desde la camara.
    this.sombra = new THREE.Mesh(
      new THREE.CircleGeometry(0.11, 16),
      new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35, depthWrite: false }));
    this.sombra.rotation.x = -Math.PI / 2;
    // Estela: copias que se apagan en las posiciones anteriores, solo en los tiros rapidos.
    this.estela = [];
    const geoEstela = new THREE.SphereGeometry(R * 1.45, 10, 8);
    for (let i = 0; i < ESTELA; i++) {
      const m = new THREE.Mesh(geoEstela, new THREE.MeshBasicMaterial({
        color: 0xe8f78a, transparent: true, opacity: 0, depthWrite: false }));
      m.visible = false;
      this.estela.push(m);
      scene.add(m);
    }
    this.pasadas = [];
    this.aplastada = 0;
    scene.add(this.malla, this.sombra);
    this.visible = true;
  }

  poner(x, y, z) {
    Object.assign(this.e, estadoNuevo(), { x, y, z });
    this.pasadas.length = 0;
  }

  avanzar(dt) {
    const ev = avanzar(this.e, dt);
    if (ev === 'pique' && !this.e.rodando) this.aplastada = 1;
    return ev;
  }

  dibujar(dt = 0) {
    const e = this.e;
    this.malla.visible = this.sombra.visible = this.visible;
    this.malla.position.set(e.x, e.y, e.z);
    this.sombra.position.set(e.x, 0.012, e.z);
    const s = 1 + Math.min(e.y, 6) * 0.25;
    this.sombra.scale.setScalar(s);
    this.sombra.material.opacity = 0.4 / s + 0.05;

    // Giro: el topspin la hace rodar hacia adelante, el slice hacia atras, la curva sobre el eje vertical.
    const vh = Math.hypot(e.vx, e.vz);
    if (dt > 0 && vh > 0.05) {
      _eje.set(e.vx / vh, 0, e.vz / vh).cross(ARRIBA).negate(); // eje del topspin
      const w = e.rodando ? vh / R : 25 + 80 * Math.abs(e.spin);
      _q.setFromAxisAngle(_eje, (e.rodando || e.spin >= 0 ? 1 : -1) * w * dt);
      this.malla.quaternion.premultiply(_q);
      if (e.curva) this.malla.quaternion.premultiply(_q.setFromAxisAngle(ARRIBA, -e.curva * 70 * dt));
    }
    // Se aplasta un instante al picar.
    this.aplastada = Math.max(0, this.aplastada - dt * 14);
    const a = this.aplastada;
    this.malla.scale.set(1 + 0.25 * a, 1 - 0.35 * a, 1 + 0.25 * a);
    this.malla.position.y -= 0.35 * a * R * 1.6;

    const v = Math.hypot(e.vx, e.vy, e.vz);
    this.pasadas.unshift([e.x, e.y, e.z]);
    if (this.pasadas.length > ESTELA + 1) this.pasadas.length = ESTELA + 1;
    const fuerza = this.visible && !e.rodando ? Math.max(0, Math.min(1, (v - 14) / 16)) : 0;
    this.estela.forEach((m, i) => {
      const p = this.pasadas[i + 1];
      m.visible = !!p && fuerza > 0;
      if (!m.visible) return;
      m.position.set(p[0], p[1], p[2]);
      const f = 1 - (i + 1) / (ESTELA + 1);
      m.scale.setScalar(0.45 + 0.55 * f);
      m.material.opacity = 0.32 * f * fuerza;
    });
  }
}
