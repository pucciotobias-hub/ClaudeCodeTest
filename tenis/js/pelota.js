// Fisica de la pelota. El estado es un objeto plano {x,y,z,vx,vy,vz,spin,piques,rodando}
// para poder copiarlo y simular hacia adelante (lo usan la maquina y el calculo de los golpes).
import * as THREE from 'three';
import { RADIO_PELOTA as R, POSTE_X, alturaRed } from './cancha.js';

export const G = 9.81;
export const ARRASTRE = 0.018; // 1/m: desaceleracion = ARRASTRE * v^2
export const MAGNUS = 0.2;     // spin +1 (topspin) hunde la pelota, -1 (slice) la hace flotar
export const PASO = 1 / 120;

// Cesped: pique bajo y rapido.
const RESTITUCION = 0.70;
const ROCE_PIQUE = 0.82;

export function estadoNuevo() {
  return { x: 0, y: 1, z: 0, vx: 0, vy: 0, vz: 0, spin: 0, piques: 0, rodando: false };
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
  e.vx -= k * e.vx * dt;
  e.vz -= k * e.vz * dt;
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
        e.y = h + R; e.vz *= 0.5; e.vx *= 0.6; e.vy = Math.abs(e.vy) * 0.3 + 1.0; e.spin = 0;
        evento = 'cinta';
      } else {
        e.x = xc; e.y = yc; e.z = z0 > 0 ? 0.06 : -0.06;
        e.vz *= -0.08; e.vx *= 0.2; e.vy = Math.min(e.vy, 0) * 0.3; e.spin = 0;
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
      e.vx *= ROCE_PIQUE; e.vz *= ROCE_PIQUE;
      e.spin *= 0.4;
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

export class Pelota {
  constructor(scene) {
    this.e = estadoNuevo();
    this.malla = new THREE.Mesh(
      new THREE.SphereGeometry(R * 1.6, 14, 10), // algo mas grande que la real para que se lea
      new THREE.MeshStandardMaterial({ color: 0xd8f03a, emissive: 0x5a6a10, roughness: 0.6 }));
    this.malla.castShadow = true;
    // Sombra falsa: es lo que deja leer la altura de la pelota desde la camara.
    this.sombra = new THREE.Mesh(
      new THREE.CircleGeometry(0.11, 16),
      new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35, depthWrite: false }));
    this.sombra.rotation.x = -Math.PI / 2;
    scene.add(this.malla, this.sombra);
    this.visible = true;
  }

  poner(x, y, z) {
    Object.assign(this.e, estadoNuevo(), { x, y, z });
  }

  avanzar(dt) { return avanzar(this.e, dt); }

  dibujar() {
    const e = this.e;
    this.malla.visible = this.sombra.visible = this.visible;
    this.malla.position.set(e.x, e.y, e.z);
    this.sombra.position.set(e.x, 0.012, e.z);
    const s = 1 + Math.min(e.y, 6) * 0.25;
    this.sombra.scale.setScalar(s);
    this.sombra.material.opacity = 0.4 / s + 0.05;
  }
}
