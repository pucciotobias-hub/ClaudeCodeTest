// Plantel y figura articulada de cada jugador (low-poly, armada con cajas y cilindros).
import * as THREE from 'three';
import { LIMITE_X, LIMITE_Z, lado } from './cancha.js';

// Atributos de 1 a 10. `topspin` multiplica el efecto del drive.
export const PLANTEL = [
  { id: 'federer', nombre: 'Federer', pais: 'SUI', perfil: 'Completo: toque, saque y volea',
    altura: 1.85, zurdo: false, dosManos: false, topspin: 0.9, piel: 0xe6b894, pelo: 0x4a3524, vincha: 0xffffff,
    attrs: { potencia: 8, velocidad: 8, precision: 9, saque: 9, toque: 10, resistencia: 7 } },
  { id: 'nadal', nombre: 'Nadal', pais: 'ESP', perfil: 'Zurdo, topspin pesado, no se cansa',
    altura: 1.85, zurdo: true, dosManos: true, topspin: 1.7, piel: 0xc98f66, pelo: 0x2a1d14, vincha: 0xffffff, sinMangas: true,
    attrs: { potencia: 9, velocidad: 9, precision: 8, saque: 7, toque: 8, resistencia: 10 } },
  { id: 'djokovic', nombre: 'Djokovic', pais: 'SRB', perfil: 'Contragolpeador, precisión total',
    altura: 1.88, zurdo: false, dosManos: true, topspin: 1.0, piel: 0xe0b08c, pelo: 0x1e1814,
    attrs: { potencia: 8, velocidad: 9, precision: 10, saque: 8, toque: 8, resistencia: 10 } },
  { id: 'alcaraz', nombre: 'Alcaraz', pais: 'ESP', perfil: 'El más rápido y el mejor dropshot',
    altura: 1.83, zurdo: false, dosManos: true, topspin: 1.2, piel: 0xcf9a72, pelo: 0x231a14,
    attrs: { potencia: 9, velocidad: 10, precision: 8, saque: 8, toque: 10, resistencia: 9 } },
  { id: 'sinner', nombre: 'Sinner', pais: 'ITA', perfil: 'Potencia plana desde el fondo',
    altura: 1.91, zurdo: false, dosManos: true, topspin: 0.8, piel: 0xf0c8ac, pelo: 0xc8642a, gorra: 0xffffff,
    attrs: { potencia: 10, velocidad: 9, precision: 9, saque: 8, toque: 7, resistencia: 8 } },
  { id: 'delpotro', nombre: 'Del Potro', pais: 'ARG', perfil: 'Drive y saque demoledores, más lento',
    altura: 1.98, zurdo: false, dosManos: true, topspin: 0.7, piel: 0xe2b592, pelo: 0x3a2a1c, vincha: 0x8fd0f0, muniequera: 0x8fd0f0,
    attrs: { potencia: 10, velocidad: 6, precision: 8, saque: 10, toque: 7, resistencia: 6 } },
];
export const ATRIBUTOS = [
  ['potencia', 'Potencia'], ['velocidad', 'Velocidad'], ['precision', 'Precisión'],
  ['saque', 'Saque'], ['toque', 'Toque'], ['resistencia', 'Resistencia'],
];

const mat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.85, ...extra });
function caja(w, h, d, color, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), typeof color === 'object' ? color : mat(color));
  m.position.set(x, y, z);
  m.castShadow = true;
  return m;
}

// Poses del brazo de la raqueta y del torso en tres momentos: preparacion, contacto y final.
// [torsoY, brazoX, brazoZ]; los signos estan pensados para un diestro y se espejan para el zurdo.
// brazoX negativo lleva el brazo hacia adelante/arriba; brazoZ positivo lo abre hacia el lado de la raqueta.
const POSES = {
  reposo:   [[0, -0.5, 0.25]],
  drive:    [[0.9, 0.7, 1.1], [0.1, -0.9, 0.9], [-0.7, -2.0, -0.6]],
  reves:    [[-1.0, -0.5, -0.9], [-0.2, -0.9, 0.3], [0.5, -1.3, 1.4]],
  dropshot: [[0.5, -1.9, 0.8], [0.1, -1.0, 0.5], [-0.3, -0.5, -0.2]],
  globo:    [[0.6, 0.6, 0.6], [0.1, -1.0, 0.5], [-0.3, -2.7, 0.2]],
  volea:    [[0.3, -1.3, 0.9], [0, -1.2, 0.5], [-0.2, -0.9, 0.1]],
  smash:    [[0.5, -3.7, 0.3], [0, -3.0, 0.1], [-0.4, -0.6, -0.5]],
  saque:    [[0.6, -3.8, 0.3], [0, -3.0, 0.1], [-0.4, -0.5, -0.5]],
};

export class Jugador {
  constructor(datos, indice, scene) {
    this.datos = datos;
    this.indice = indice;
    this.x = 0; this.z = lado(indice) * 12.5;
    this.vx = 0; this.vz = 0;
    this.energia = 1;
    this.velMax = 5.2 + datos.attrs.velocidad * 0.32;
    this.anim = { tipo: 'reposo', fase: 0, t: 0 }; // fase 0: preparado, 1: pegando
    this.paso = 0;
    this.pose = [0, -0.5, 0.25];
    this.#armar(scene);
  }

  #armar(scene) {
    const d = this.datos;
    const k = d.altura / 1.85;
    const s = d.zurdo ? 1 : -1; // en el modelo, que mira a +z, la derecha es -x
    const blanco = mat(0xf7f7f2), piel = mat(d.piel);
    const g = this.grupo = new THREE.Group();
    g.scale.setScalar(k);
    if (this.indice === 0) g.rotation.y = Math.PI; // el usuario mira hacia la red, de espaldas a la camara

    this.cadera = new THREE.Group();
    this.cadera.position.y = 0.92;
    g.add(this.cadera);

    this.piernas = [-1, 1].map((i) => {
      const p = new THREE.Group();
      p.position.set(i * 0.11, 0, 0);
      p.add(caja(0.15, 0.22, 0.17, blanco, 0, -0.1, 0));     // short
      p.add(caja(0.11, 0.62, 0.12, piel, 0, -0.5, 0));       // pierna
      p.add(caja(0.12, 0.09, 0.27, blanco, 0, -0.875, 0.05)); // zapatilla
      this.cadera.add(p);
      return p;
    });

    this.torso = new THREE.Group();
    this.cadera.add(this.torso);
    this.torso.add(caja(0.40, 0.56, 0.22, blanco, 0, 0.30, 0));
    this.torso.add(caja(0.10, 0.08, 0.10, piel, 0, 0.61, 0));
    const cabeza = new THREE.Group();
    cabeza.position.y = 0.76;
    cabeza.add(caja(0.20, 0.23, 0.21, piel));
    cabeza.add(caja(0.215, 0.09, 0.225, d.pelo, 0, 0.10, -0.005));
    cabeza.add(caja(0.215, 0.14, 0.06, d.pelo, 0, 0.02, -0.085));
    if (d.vincha) cabeza.add(caja(0.225, 0.045, 0.235, d.vincha, 0, 0.055, 0));
    if (d.gorra) {
      cabeza.add(caja(0.225, 0.07, 0.235, d.gorra, 0, 0.115, 0.01));
      cabeza.add(caja(0.19, 0.02, 0.12, d.gorra, 0, 0.085, 0.16));
    }
    this.torso.add(cabeza);

    const brazo = (signo, conRaqueta) => {
      const b = new THREE.Group();
      b.position.set(signo * 0.25, 0.53, 0);
      if (!d.sinMangas) b.add(caja(0.12, 0.2, 0.13, blanco, 0, -0.08, 0));
      b.add(caja(0.085, 0.60, 0.09, piel, 0, -0.30, 0));
      if (conRaqueta && d.muniequera) b.add(caja(0.10, 0.07, 0.10, d.muniequera, 0, -0.50, 0));
      this.torso.add(b);
      return b;
    };
    this.brazo = brazo(s, true);
    this.brazoLibre = brazo(-s, false);

    const raqueta = new THREE.Group();
    raqueta.position.y = -0.60;
    raqueta.add(caja(0.03, 0.26, 0.03, 0x222222, 0, -0.13, 0));
    const aro = new THREE.Mesh(new THREE.TorusGeometry(0.14, 0.014, 6, 16), mat(0x1c1c22));
    aro.scale.set(0.82, 1.15, 1);
    aro.position.y = -0.41;
    aro.castShadow = true;
    const cuerdas = new THREE.Mesh(new THREE.CircleGeometry(0.13, 16),
      new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35, side: THREE.DoubleSide }));
    cuerdas.scale.copy(aro.scale);
    cuerdas.position.y = -0.41;
    raqueta.add(aro, cuerdas);
    raqueta.rotation.y = Math.PI / 2; // la cara mira hacia adelante al pegar
    this.brazo.add(raqueta);

    this.mano = s;
    scene.add(g);
  }

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

  preparar(tipo) {
    if (this.anim.fase === 1) return;
    this.anim = { tipo, fase: 0, t: 0 };
  }

  pegar(tipo) { this.anim = { tipo, fase: 1, t: 0 }; }

  soltar() { if (this.anim.fase === 0) this.anim = { tipo: 'reposo', fase: 0, t: 0 }; }

  dibujar(dt) {
    const g = this.grupo;
    g.position.set(this.x, 0, this.z);

    // Piernas: zancada segun la velocidad.
    const v = Math.hypot(this.vx, this.vz);
    this.paso += v * dt * 2.3;
    const amp = Math.min(0.85, v * 0.14);
    this.piernas[0].rotation.x = Math.sin(this.paso) * amp;
    this.piernas[1].rotation.x = -Math.sin(this.paso) * amp;
    this.cadera.position.y = 0.92 - (this.anim.fase === 0 && this.anim.tipo !== 'reposo' ? 0.05 : 0)
      + Math.abs(Math.cos(this.paso)) * amp * 0.05;

    // Brazo y torso: interpolar entre las poses del golpe.
    const a = this.anim;
    const p = POSES[a.tipo] ?? POSES.reposo;
    let objetivo = p[0], rapidez = 12;
    if (a.fase === 1) {
      a.t += dt;
      const u = a.t / 0.34;
      if (u < 0.3) { objetivo = p[1]; rapidez = 45; } else { objetivo = p[2]; rapidez = 22; }
      if (u >= 1.25) this.anim = { tipo: 'reposo', fase: 0, t: 0 };
    }
    const f = Math.min(1, rapidez * dt);
    for (let i = 0; i < 3; i++) this.pose[i] += (objetivo[i] - this.pose[i]) * f;
    const s = this.mano;
    this.torso.rotation.y = this.pose[0] * s;
    this.brazo.rotation.x = this.pose[1];
    this.brazo.rotation.z = this.pose[2] * s;
    const dosManos = this.datos.dosManos && a.tipo === 'reves';
    this.brazoLibre.rotation.x = dosManos ? this.pose[1] : -0.4 + Math.sin(this.paso) * amp * 0.6;
    this.brazoLibre.rotation.z = dosManos ? this.pose[2] * s + s * 0.5 : -s * 0.2;
  }
}
