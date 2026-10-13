import assert from 'node:assert/strict';
import { Puntaje } from './puntaje.js';

function test(nombre, fn) {
  try {
    fn();
    console.log(`✓ ${nombre}`);
  } catch (e) {
    console.error(`✗ ${nombre}`);
    console.error(e.message);
    process.exit(1);
  }
}

test('game a cero', () => {
  const p = new Puntaje();
  assert.deepEqual(p.puntosTexto, ['0', '0']);
  p.punto(0);
  assert.deepEqual(p.puntosTexto, ['15', '0']);
  p.punto(0);
  assert.deepEqual(p.puntosTexto, ['30', '0']);
  p.punto(0);
  assert.deepEqual(p.puntosTexto, ['40', '0']);
  const res = p.punto(0);
  assert.equal(res.game, true);
  assert.equal(res.ganadorGame, 0);
  assert.deepEqual(p.games, [1, 0]);
  assert.equal(p.terminado, false);
});

test('deuce largo con ventajas ida y vuelta', () => {
  const p = new Puntaje();
  // 0: 15-0
  p.punto(0);
  assert.deepEqual(p.puntosTexto, ['15', '0']);
  // 1: 15-15
  p.punto(1);
  assert.deepEqual(p.puntosTexto, ['15', '15']);
  // 0: 30-15
  p.punto(0);
  assert.deepEqual(p.puntosTexto, ['30', '15']);
  // 1: 30-30
  p.punto(1);
  assert.deepEqual(p.puntosTexto, ['30', '30']);
  // 0: 40-30
  p.punto(0);
  assert.deepEqual(p.puntosTexto, ['40', '30']);
  // 1: 40-40 (deuce)
  p.punto(1);
  assert.deepEqual(p.puntosTexto, ['40', '40']);
  // 0: ventaja 0
  p.punto(0);
  assert.deepEqual(p.puntosTexto, ['Ad', '40']);
  // 1: deuce nuevamente
  p.punto(1);
  assert.deepEqual(p.puntosTexto, ['40', '40']);
  // 0: ventaja 0
  p.punto(0);
  assert.deepEqual(p.puntosTexto, ['Ad', '40']);
  // 0: gana el game
  const res = p.punto(0);
  assert.equal(res.game, true);
  assert.equal(res.ganadorGame, 0);
  assert.deepEqual(p.games, [1, 0]);
});

test('set 6-4', () => {
  const p = new Puntaje({ setsParaGanar: 2 });
  // Simular un set 6-4 ganado por el jugador 0
  // Orden: 0 gana 4, 1 gana 4, 0 gana 2 más → 6-4
  const orden = [0, 0, 0, 0, 1, 1, 1, 1, 0, 0];
  for (const ganador of orden) {
    for (let punto = 0; punto < 4; punto++) {
      p.punto(ganador);
    }
  }
  assert.deepEqual(p.games, [0, 0]); // Nuevo set comenzó
  assert.equal(p.terminado, false);
  assert.deepEqual(p.setsJugados, [[6, 4]]);
  assert.deepEqual(p.setsGanados, [1, 0]);
});

test('set 7-5', () => {
  const p = new Puntaje({ setsParaGanar: 2 });
  // Set 7-5 para jugador 0
  // Orden: 1 gana 5, 0 gana 7 → [7, 5]
  const orden = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0];
  for (const ganador of orden) {
    for (let punto = 0; punto < 4; punto++) {
      p.punto(ganador);
    }
  }
  assert.deepEqual(p.games, [0, 0]); // Nuevo set comenzó
  assert.equal(p.terminado, false);
  assert.deepEqual(p.setsJugados, [[7, 5]]);
});

test('tie-break 7-6 con orden de saque', () => {
  const p = new Puntaje({ setsParaGanar: 3 });
  // Llegar a 6-6 con saca = 0 al inicio del tie-break
  const orden = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]; // alternado
  for (let game = 0; game < 12; game++) {
    for (let punto = 0; punto < 4; punto++) {
      p.punto(orden[game]);
    }
  }
  assert.equal(p.enTiebreak, true);
  assert.deepEqual(p.games, [6, 6]);

  // Verificar orden de saque en tie-break (saca 1, quien sacaba el último game)
  assert.equal(p.saca, 1);
  assert.equal(p.ladoSaque, 'deuce');

  // Punto 1 en TB (saca 1, gana 1)
  p.punto(1);
  assert.equal(p.saca, 0); // Ahora toca 0

  // Punto 2 en TB (saca 0)
  p.punto(0);
  assert.equal(p.saca, 0); // Sigue 0 (alterna cada 2)

  // Punto 3 en TB (saca 0)
  p.punto(0);
  assert.equal(p.saca, 1); // Ahora toca 1 (pasaron 2 de 0)

  // Continuar el TB hasta [7, 5] (el set será 7-6)
  // Actualmente en [2, 1], jugamos para llegar a [7, 5]
  // Siguiente: 0 gana 5 más → [7, 1], pero necesito [7, 5]
  // Así que: 0 gana 4, 1 gana 4, 0 gana 1 más → [7, 5]
  for (let i = 0; i < 4; i++) {
    p.punto(0);
  }
  for (let i = 0; i < 4; i++) {
    p.punto(1);
  }
  p.punto(0);

  assert.equal(p.terminado, false); // setsParaGanar = 3
  assert.deepEqual(p.games, [0, 0]); // Nuevo set comenzó
  assert.deepEqual(p.setsJugados, [[7, 6]]); // El set anterior terminó 7-6 (TB fue 7-5)
  assert.equal(p.enTiebreak, false);
  assert.deepEqual(p.setsGanados, [1, 0]);
});

test('tie-break largo 10-8', () => {
  const p = new Puntaje();
  // Llegar a 6-6
  for (let game = 0; game < 12; game++) {
    for (let punto = 0; punto < 4; punto++) {
      p.punto(game % 2);
    }
  }

  // En TB, alternar para llegar a 8-8, luego 0 gana 10-8
  for (let i = 0; i < 16; i++) {
    p.punto(i % 2);
  }
  // 8-8 en TB
  assert.equal(p.enTiebreak, true);
  assert.deepEqual(p.puntosCrudos, [8, 8]);

  // 0 gana 2 seguidos
  p.punto(0);
  p.punto(0);

  assert.equal(p.terminado, true);
  assert.equal(p.ganador, 0);
  assert.deepEqual(p.games, [7, 6]);
});

test('set corto 5-4 con tie-break a 4-4', () => {
  const p = new Puntaje({ gamesPorSet: 4 });
  // Llegar a 4-4
  for (let game = 0; game < 8; game++) {
    for (let punto = 0; punto < 4; punto++) {
      p.punto(game % 2);
    }
  }
  assert.deepEqual(p.games, [4, 4]);
  assert.equal(p.enTiebreak, true);

  // Ganar TB
  for (let i = 0; i < 7; i++) {
    p.punto(0);
  }

  assert.equal(p.terminado, true);
  assert.equal(p.ganador, 0);
  assert.deepEqual(p.games, [5, 4]);
  assert.deepEqual(p.setsJugados, [[5, 4]]);
});

test('partido al mejor de 3, termina 2-1', () => {
  const p = new Puntaje({ setsParaGanar: 2 });

  // Set 1: gana 0 (6-4)
  for (let game = 0; game < 10; game++) {
    const ganador = game < 6 ? 0 : 1;
    for (let punto = 0; punto < 4; punto++) {
      p.punto(ganador);
    }
  }
  assert.deepEqual(p.setsGanados, [1, 0]);
  assert.equal(p.terminado, false);

  // Set 2: gana 1 (4-6)
  for (let game = 0; game < 10; game++) {
    const ganador = game < 4 ? 0 : 1;
    for (let punto = 0; punto < 4; punto++) {
      p.punto(ganador);
    }
  }
  assert.deepEqual(p.setsGanados, [1, 1]);
  assert.equal(p.terminado, false);

  // Set 3: gana 0 (6-3)
  for (let game = 0; game < 9; game++) {
    const ganador = game < 6 ? 0 : 1;
    for (let punto = 0; punto < 4; punto++) {
      p.punto(ganador);
    }
  }
  assert.deepEqual(p.setsGanados, [2, 1]);
  assert.equal(p.terminado, true);
  assert.equal(p.ganador, 0);
});

test('alternancia de saca y ladoSaque', () => {
  const p = new Puntaje({ sacaPrimero: 0 });

  assert.equal(p.saca, 0);
  assert.equal(p.ladoSaque, 'deuce');

  p.punto(0); // [1, 0]
  assert.equal(p.saca, 0);
  assert.equal(p.ladoSaque, 'ad');

  p.punto(1); // [1, 1]
  assert.equal(p.saca, 0);
  assert.equal(p.ladoSaque, 'deuce');

  p.punto(0); // [2, 1]
  assert.equal(p.saca, 0);
  assert.equal(p.ladoSaque, 'ad');

  p.punto(0); // [3, 1]
  assert.equal(p.saca, 0);
  assert.equal(p.ladoSaque, 'deuce');

  p.punto(0); // [4, 1] - game termina
  assert.equal(p.saca, 1);
  assert.equal(p.ladoSaque, 'deuce');
});

test('punto() después de terminado no cambia nada', () => {
  const p = new Puntaje();

  // Ganar un match simple (6 games = 1 set, con setsParaGanar = 1 = match)
  for (let game = 0; game < 6; game++) {
    for (let punto = 0; punto < 4; punto++) {
      p.punto(0);
    }
  }

  assert.equal(p.terminado, true);
  assert.equal(p.ganador, 0);
  const games_antes = p.games[0];

  // Intentar anotar más puntos
  const res1 = p.punto(0);
  const res2 = p.punto(1);

  assert.equal(res1.game, false);
  assert.equal(res1.set, false);
  assert.equal(res1.partido, false);
  assert.equal(res1.ganadorGame, null);
  assert.deepEqual(res2, res1);

  assert.equal(p.terminado, true);
  assert.equal(p.ganador, 0);
  assert.equal(p.games[0], games_antes);
});

test('orden de saque después de tie-break', () => {
  const p = new Puntaje({ sacaPrimero: 0, setsParaGanar: 2 });

  // Llegar a 6-6
  for (let game = 0; game < 12; game++) {
    for (let punto = 0; punto < 4; punto++) {
      p.punto(game % 2);
    }
  }

  // En TB, saca 1 (quien venía sacando después de 12 games alternados)
  assert.equal(p.saca, 1);

  // Ganar TB para 0
  for (let i = 0; i < 7; i++) {
    p.punto(0);
  }

  // Nuevo set: el que RECIBIÓ el primer punto del TB (0) saca ahora
  assert.equal(p.saca, 0);
  assert.deepEqual(p.games, [0, 0]); // Nuevo set
});

console.log('OK');
