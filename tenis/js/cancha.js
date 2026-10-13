// Medidas de la cancha en metros y sistema de ejes compartido por todos los modulos.
//
//   x: ancho de la cancha (0 en el centro, + a la derecha de la camara)
//   y: altura (0 en el cesped)
//   z: largo de la cancha (0 en la red; + es el lado del usuario, cerca de la camara)
//
// El jugador 0 (usuario) juega en z > 0 y el jugador 1 (maquina) en z < 0.

export const MEDIO_ANCHO = 4.115;        // linea lateral de singles
export const MEDIO_ANCHO_DOBLES = 5.485; // linea lateral de dobles (se dibuja, no se juega)
export const MEDIO_LARGO = 11.885;       // linea de fondo
export const SAQUE = 6.40;               // linea de saque, medida desde la red
export const RED_CENTRO = 0.914;         // altura de la red en el centro
export const RED_POSTE = 1.07;           // altura de la red en los postes
export const POSTE_X = 6.40;             // postes, 0.914 m afuera de la linea de dobles
export const RADIO_PELOTA = 0.033;

// Hasta donde se puede correr sin chocar con los carteles.
export const LIMITE_X = 9.5;
export const LIMITE_Z = 17.5;

// Altura de la red en una posicion x (la faja la baja en el centro).
export function alturaRed(x) {
  const t = Math.min(1, Math.abs(x) / POSTE_X);
  return RED_CENTRO + (RED_POSTE - RED_CENTRO) * t;
}

// Lado de cada jugador: +1 para el usuario (z > 0), -1 para la maquina.
export const lado = (jugador) => (jugador === 0 ? 1 : -1);
