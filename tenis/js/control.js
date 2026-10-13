// Teclado del usuario: flechas para moverse y apuntar, Espacio / Z / X para pegar.
const MAPA = {
  ArrowLeft: 'izq', ArrowRight: 'der', ArrowUp: 'arriba', ArrowDown: 'abajo',
  Space: 'golpe', KeyZ: 'dropshot', KeyX: 'globo',
  KeyP: 'pausa', Escape: 'pausa',
};
export const TECLAS_GOLPE = ['golpe', 'dropshot', 'globo'];

export class Control {
  constructor() {
    this.abajo = {};      // teclas apretadas ahora
    this.recien = {};     // apretadas desde la ultima lectura
    this.soltadas = {};   // soltadas desde la ultima lectura
    this.ultimaGolpe = null;
    addEventListener('keydown', (ev) => {
      const k = MAPA[ev.code];
      if (!k) return;
      ev.preventDefault();
      if (ev.repeat) return;
      this.abajo[k] = true;
      this.recien[k] = true;
      if (TECLAS_GOLPE.includes(k)) this.ultimaGolpe = k;
    });
    addEventListener('keyup', (ev) => {
      const k = MAPA[ev.code];
      if (!k) return;
      this.abajo[k] = false;
      this.soltadas[k] = true;
    });
    addEventListener('blur', () => { this.abajo = {}; });
  }

  get dirX() { return (this.abajo.der ? 1 : 0) - (this.abajo.izq ? 1 : 0); }
  // +1 hacia la red / profundo.
  get dirZ() { return (this.abajo.arriba ? 1 : 0) - (this.abajo.abajo ? 1 : 0); }

  // Tecla de golpe que se esta manteniendo (la ultima apretada manda).
  get golpeApretado() {
    if (this.ultimaGolpe && this.abajo[this.ultimaGolpe]) return this.ultimaGolpe;
    return TECLAS_GOLPE.find((k) => this.abajo[k]) ?? null;
  }

  // Devuelve y limpia los flancos acumulados.
  flancos() {
    const f = { recien: this.recien, soltadas: this.soltadas };
    this.recien = {}; this.soltadas = {};
    return f;
  }
}
