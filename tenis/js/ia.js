// Jugador manejado por la maquina: lee la trayectoria, corre al punto de impacto y elige el golpe.
import { MEDIO_ANCHO, MEDIO_LARGO, LIMITE_X, LIMITE_Z, lado } from './cancha.js';
import { trayectoria } from './pelota.js';
import { puedeGolpear } from './golpes.js';

// reaccion: segundos hasta que empieza a moverse. error: multiplica la dispersion de sus golpes.
// noForzado: probabilidad de pifiar un golpe comodo. velocidad y potencia: fraccion del maximo del jugador.
export const DIFICULTADES = {
  facil:   { nombre: 'Fácil',   reaccion: 0.42, error: 1.7,  noForzado: 0.10, velocidad: 0.84, potencia: 0.50, astucia: 0.3 },
  media:   { nombre: 'Media',   reaccion: 0.28, error: 1.25, noForzado: 0.05, velocidad: 0.94, potencia: 0.70, astucia: 0.6 },
  dificil: { nombre: 'Difícil', reaccion: 0.16, error: 1.0,  noForzado: 0.02, velocidad: 1.0,  potencia: 0.88, astucia: 1.0 },
};

const azar = (a, b) => a + Math.random() * (b - a);

export class IA {
  constructor(jugador, dificultad) {
    this.j = jugador;
    this.dif = dificultad;
    this.L = lado(jugador.indice);
    this.plan = null;
    this.espera = 0;
    this.pendiente = false;
  }

  reiniciar() { this.plan = null; this.pendiente = false; }

  // El rival acaba de pegar: despues del tiempo de reaccion lee la pelota.
  alGolpeRival() {
    this.plan = null;
    this.pendiente = true;
    this.espera = this.dif.reaccion * azar(0.8, 1.25);
  }

  #leer(pelota) {
    const { muestras, primerPique, red } = trayectoria(pelota.e);
    const L = this.L, j = this.j;
    if (red || !primerPique || primerPique.z * L <= 0) return { dejar: true, x: j.x, z: j.z };
    // La deja pasar si la ve claramente afuera (los mas flojos leen peor).
    const margen = 0.12 + (1 - this.dif.astucia) * 0.5;
    const afuera = Math.abs(primerPique.x) > MEDIO_ANCHO + margen || Math.abs(primerPique.z) > MEDIO_LARGO + margen;

    const adentro = (m) => m.z * L > 0.8 && Math.abs(m.z) < LIMITE_Z - 0.4 && Math.abs(m.x) < LIMITE_X - 0.4;
    let punto = null;
    // En la red: volea donde la pelota pasa a su altura.
    if (Math.abs(j.z) < 5) {
      punto = muestras.find((m) => m.piques === 0 && adentro(m) && m.y > 0.6 && m.y < 2.4 && Math.abs(m.z) >= Math.abs(j.z) - 1.2);
    }
    if (!punto) {
      const tras = muestras.filter((m) => m.piques === 1 && adentro(m));
      punto = tras.find((m) => m.vy < 0 && m.y < 1.15) ?? tras[tras.length - 1];
    }
    if (!punto) return { dejar: true, x: j.x, z: j.z };
    const costado = j.x < punto.x ? 1 : -1;
    return { dejar: afuera, x: punto.x - costado * 0.75, z: punto.z + L * 0.45 };
  }

  // ctx: { pelota, rival, viene (la pelota es para mi), golpear(jugador, op) }
  actualizar(dt, ctx) {
    const j = this.j, L = this.L, dif = this.dif;
    if (!ctx.viene) {
      // Volver al centro, un paso atras de la linea de fondo.
      j.irA(0, L * (MEDIO_LARGO + 0.7), dt, dif.velocidad * 0.8);
      j.soltar();
      return;
    }
    if (this.pendiente) {
      this.espera -= dt;
      if (this.espera <= 0) { this.plan = this.#leer(ctx.pelota); this.pendiente = false; }
    }
    if (!this.plan) { j.mover(0, 0, dt); return; }
    j.irA(this.plan.x, this.plan.z, dt, dif.velocidad);
    if (this.plan.dejar && ctx.pelota.e.piques === 0) return;

    const contacto = puedeGolpear(j, ctx.pelota.e);
    const cerca = Math.hypot(ctx.pelota.e.x - j.x, ctx.pelota.e.z - j.z) < 6;
    if (cerca) j.preparar((ctx.pelota.e.x - j.x) * L > 0 !== !!j.datos.zurdo ? 'drive' : 'reves');
    if (contacto) ctx.golpear(j, this.#elegir(contacto, ctx));
  }

  #elegir(contacto, ctx) {
    const j = this.j, L = this.L, dif = this.dif, a = j.datos.attrs;
    const r = ctx.rival;
    const rivalEnRed = Math.abs(r.z) < 5.5;
    const rivalAtras = Math.abs(r.z) > MEDIO_LARGO + 1.2;
    const lejos = -Math.sign(r.x || (Math.random() - 0.5)); // el lado donde el rival no esta
    const pifia = Math.random() < dif.noForzado * (1 + 2 * contacto.estirado);
    const op = {
      tecla: 'golpe',
      apX: lejos * azar(0.5, 0.95),
      apZ: azar(-0.1, 0.8),
      potencia: Math.min(1, dif.potencia * azar(0.8, 1.15)),
      calidad: pifia ? 0.1 : azar(0.75, 1),
      error: dif.error * (pifia ? 2.4 : 1),
    };
    if (contacto.alto) return { ...op, potencia: 1, apZ: 0 };

    if (rivalEnRed) {
      // Globo o passing.
      if (Math.random() < 0.18 + 0.03 * a.toque * dif.astucia) return { ...op, tecla: 'globo', apX: lejos * azar(0, 0.6) };
      return { ...op, potencia: Math.min(1, op.potencia + 0.15), apX: lejos * azar(0.8, 1), apZ: azar(-0.6, 0.3) };
    }
    if (rivalAtras && Math.abs(j.z) < MEDIO_LARGO + 0.5 && !contacto.estirado &&
        Math.random() < (0.04 + 0.016 * a.toque) * dif.astucia) {
      return { ...op, tecla: 'dropshot', apX: lejos * azar(0.3, 0.9), apZ: -1 };
    }
    // Con el rival centrado, cualquier lado; a veces juega a contrapie o al medio.
    if (Math.abs(r.x) < 1.2) op.apX = (Math.random() < 0.5 ? -1 : 1) * azar(0.45, 0.95);
    else if (Math.random() > 0.55 + 0.3 * dif.astucia) op.apX = -op.apX * azar(0.2, 0.8);
    if (contacto.estirado > 0.6) { op.potencia *= 0.75; op.apX *= 0.5; op.apZ = 0; }
    return op;
  }

  // Saque de la maquina: devuelve las opciones para ejecutarSaque.
  saque(segundo) {
    const dif = this.dif;
    return {
      apX: [-1, 0, 1][Math.floor(Math.random() * 3)] * (0.5 + 0.5 * dif.astucia),
      calidad: Math.min(1, azar(0.55, 0.95) + 0.1 * dif.astucia),
      error: 0.85 + (dif.error - 1) * 0.6,
      segundo,
    };
  }
}
