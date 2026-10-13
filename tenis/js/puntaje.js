export class Puntaje {
  constructor({ gamesPorSet = 6, setsParaGanar = 1, sacaPrimero = 0 } = {}) {
    this.gamesPorSet = gamesPorSet;
    this.setsParaGanar = setsParaGanar;

    this._puntosCrudos = [0, 0];
    this._games = [0, 0];
    this._setsJugados = [];
    this._setsGanados = [0, 0];
    this._terminado = false;
    this._ganador = null;
    this._sacaActual = sacaPrimero;
    this._enTiebreak = false;
    this._primerSacadoTB = null; // Quién sacó el primer punto del tie-break
  }

  punto(ganador) {
    // Si ya terminó, no hacer nada
    if (this._terminado) {
      return { game: false, set: false, partido: false, ganadorGame: null };
    }

    this._puntosCrudos[ganador]++;

    let gameTerminado = false;
    let ganadorGame = null;
    let setTerminado = false;
    let partidoTerminado = false;

    // Verificar si se termina el game/tie-break
    if (this._enTiebreak) {
      // Tie-break: 7 puntos con diferencia de 2
      if (
        this._puntosCrudos[ganador] >= 7 &&
        this._puntosCrudos[ganador] - this._puntosCrudos[1 - ganador] >= 2
      ) {
        gameTerminado = true;
        ganadorGame = ganador;
        this._games[ganador]++;

        // El tie-break termina el set
        this._setsJugados.push([...this._games]);
        this._setsGanados[ganador]++;
        setTerminado = true;
        this._enTiebreak = false;

        // Verificar si se termina el partido
        if (this._setsGanados[ganador] >= this.setsParaGanar) {
          this._terminado = true;
          this._ganador = ganador;
          partidoTerminado = true;
        } else {
          // Nuevo set: el que recibió el primer punto del tie-break saca ahora
          this._games = [0, 0];
          this._puntosCrudos = [0, 0];
          this._sacaActual = 1 - this._primerSacadoTB;
        }
      }
    } else {
      // Game normal: 4 puntos con diferencia de 2
      if (
        this._puntosCrudos[ganador] >= 4 &&
        this._puntosCrudos[ganador] - this._puntosCrudos[1 - ganador] >= 2
      ) {
        gameTerminado = true;
        ganadorGame = ganador;
        this._games[ganador]++;

        // Verificar si se termina el set o entra tie-break
        if (
          this._games[ganador] >= this.gamesPorSet &&
          this._games[ganador] - this._games[1 - ganador] >= 2
        ) {
          // Set terminado normalmente
          this._setsJugados.push([...this._games]);
          this._setsGanados[ganador]++;
          setTerminado = true;

          // Verificar si se termina el partido
          if (this._setsGanados[ganador] >= this.setsParaGanar) {
            this._terminado = true;
            this._ganador = ganador;
            partidoTerminado = true;
          } else {
            // Nuevo set
            this._games = [0, 0];
            this._puntosCrudos = [0, 0];
            this._sacaActual = 1 - this._sacaActual;
          }
        } else if (this._games[0] === this.gamesPorSet && this._games[1] === this.gamesPorSet) {
          // Empate en gamesPorSet-gamesPorSet, entra tie-break
          this._enTiebreak = true;
          this._primerSacadoTB = this._sacaActual;
          this._puntosCrudos = [0, 0];
        } else {
          // Game normal terminado, sigue el set
          this._puntosCrudos = [0, 0];
          this._sacaActual = 1 - this._sacaActual;
        }
      }
    }

    return {
      game: gameTerminado,
      set: setTerminado,
      partido: partidoTerminado,
      ganadorGame: ganadorGame
    };
  }

  get saca() {
    if (this._enTiebreak) {
      const totalPuntos = this._puntosCrudos[0] + this._puntosCrudos[1];
      if (totalPuntos === 0) {
        return this._primerSacadoTB;
      }
      const bloque = Math.floor((totalPuntos - 1) / 2);
      return bloque % 2 === 0 ? (1 - this._primerSacadoTB) : this._primerSacadoTB;
    }
    return this._sacaActual;
  }

  get ladoSaque() {
    const totalPuntos = this._puntosCrudos[0] + this._puntosCrudos[1];
    return totalPuntos % 2 === 0 ? 'deuce' : 'ad';
  }

  get enTiebreak() {
    return this._enTiebreak;
  }

  get terminado() {
    return this._terminado;
  }

  get ganador() {
    return this._ganador;
  }

  get puntosTexto() {
    if (this._enTiebreak) {
      return [String(this._puntosCrudos[0]), String(this._puntosCrudos[1])];
    }

    const mapeo = ['0', '15', '30', '40'];
    const p0 = this._puntosCrudos[0];
    const p1 = this._puntosCrudos[1];

    if (p0 >= 3 && p1 >= 3) {
      if (p0 === p1) {
        return ['40', '40'];
      } else if (p0 > p1) {
        return ['Ad', '40'];
      } else {
        return ['40', 'Ad'];
      }
    }

    const t0 = mapeo[Math.min(p0, 3)];
    const t1 = mapeo[Math.min(p1, 3)];
    return [t0, t1];
  }

  get games() {
    return [...this._games];
  }

  get setsJugados() {
    return this._setsJugados.map(s => [...s]);
  }

  get setsGanados() {
    return [...this._setsGanados];
  }

  get puntosCrudos() {
    return [...this._puntosCrudos];
  }
}
