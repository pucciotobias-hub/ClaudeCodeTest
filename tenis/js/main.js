// Arranque, bucle de juego y reglas del punto.
import * as THREE from 'three';
import { MEDIO_ANCHO, MEDIO_LARGO, lado } from './cancha.js';
import { crearEstadio } from './estadio.js';
import { PLANTEL, ATRIBUTOS, Jugador } from './jugadores.js';
import { Pelota, PASO, trayectoria, estadoNuevo, avanzar } from './pelota.js';
import { puedeGolpear, ejecutarGolpe, ejecutarSaque, saqueBueno, pelotaBuena, nombreGolpe, objetivo } from './golpes.js';
import { Control, TECLAS_GOLPE } from './control.js';
import { IA, DIFICULTADES, leerPelota } from './ia.js';
import { Puntaje } from './puntaje.js';
import { sonido } from './sonido.js';

const FORMATOS = {
  corto: { nombre: 'Set corto (a 4)', gamesPorSet: 4, setsParaGanar: 1 },
  set:   { nombre: '1 set', gamesPorSet: 6, setsParaGanar: 1 },
  tres:  { nombre: 'Mejor de 3', gamesPorSet: 6, setsParaGanar: 2 },
};
const params = new URLSearchParams(location.search);
const DEMO = params.has('demo');             // maquina contra maquina, para probar
const ACELERAR = Number(params.get('vel')) || 1;

const $ = (id) => document.getElementById(id);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

// ---------- Escena ----------
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(44, innerWidth / innerHeight, 0.1, 400);
addEventListener('resize', () => {
  renderer.setSize(innerWidth, innerHeight);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
});

const estadio = crearEstadio(scene);
const pelota = new Pelota(scene);
pelota.visible = false;
const control = new Control();

// Aro en el cesped donde va a picar la pelota que viene: sin esto no se llega a leer la profundidad.
const marca = new THREE.Mesh(
  new THREE.RingGeometry(0.22, 0.32, 24),
  new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.55, depthWrite: false }));
marca.rotation.x = -Math.PI / 2;
marca.visible = false;
scene.add(marca);
function marcarPique() {
  const pq = trayectoria(pelota.e).primerPique;
  marca.visible = !!pq && pq.z > 0 && !DEMO;
  if (pq) marca.position.set(pq.x, 0.02, pq.z);
  P.usuario.plan = leerPelota(P.jug[0], pelota.e);
}

// Mira: mientras se arma el golpe, muestra en la cancha rival adonde se esta apuntando.
const mira = new THREE.Mesh(
  new THREE.RingGeometry(0.3, 0.45, 28),
  new THREE.MeshBasicMaterial({ color: 0xffd84a, transparent: true, opacity: 0.8, depthWrite: false }));
mira.rotation.x = -Math.PI / 2;
mira.visible = false;
scene.add(mira);

// ---------- Estado del partido ----------
let P = null;          // partido en curso
let pausado = false;
const eleccion = { yo: 'federer', rival: 'azar', formato: 'corto', dificultad: 'media' };

function nuevoPartido() {
  if (P) P.jug.forEach((j) => scene.remove(j.grupo));
  const datos = (id) => PLANTEL.find((p) => p.id === id);
  const yo = datos(eleccion.yo);
  let rival = datos(eleccion.rival);
  if (!rival) {
    const otros = PLANTEL.filter((p) => p.id !== yo.id);
    rival = otros[Math.floor(Math.random() * otros.length)];
  }
  const dif = DIFICULTADES[eleccion.dificultad];
  const jug = [new Jugador(yo, 0, scene), new Jugador(rival, 1, scene)];
  P = {
    jug,
    ias: [DEMO ? new IA(jug[0], dif) : null, new IA(jug[1], dif)],
    puntaje: new Puntaje({ ...FORMATOS[eleccion.formato], sacaPrimero: Math.random() < 0.5 ? 0 : 1 }),
    estado: 'presaque', t: 0, pausa: 0,
    sacador: 0, segundo: false, repetir: false,
    ultimo: 0, ultimoTipo: 'saque', golpes: 0, esSaque: false, cinta: false,
    usuario: { activo: false, tecla: 'golpe', carga: 0, gracia: 0, apX: 0, apZ: 0, plan: null },
    stats: [0, 1].map(() => ({ puntos: 0, winners: 0, errores: 0, aces: 0, dobles: 0 })),
  };
  pausado = false;
  pelota.visible = true;
  sonido.iniciar();
  ['menu', 'fin', 'pausa'].forEach((id) => $(id).classList.add('oculto'));
  $('hud').classList.remove('oculto');
  $('ayuda').classList.toggle('oculto', DEMO);
  prepararPunto();
}

function prepararPunto() {
  const pt = P.puntaje;
  P.sacador = pt.saca;
  const s = P.jug[P.sacador], r = P.jug[1 - P.sacador];
  const Ls = lado(P.sacador);
  // Deuce: el sacador se para a su derecha y saca cruzado.
  const sx = Ls * (pt.ladoSaque === 'deuce' ? 1 : -1);
  s.colocar(sx * 1.2, Ls * (MEDIO_LARGO + 0.45));
  r.colocar(-sx * 3.3, -Ls * (MEDIO_LARGO + 0.9));
  if (!P.repetir) { P.segundo = false; P.jug.forEach((j) => j.descansar(0.3)); }
  P.repetir = false;
  P.estado = 'presaque'; P.t = 0;
  P.golpes = 0; P.esSaque = false; P.cinta = false;
  P.usuario.activo = false; P.usuario.carga = 0; P.usuario.plan = null;
  mira.visible = false;
  P.ias.forEach((ia) => ia?.reiniciar());
  P.jug.forEach((j) => j.soltar());
  pelotaEnMano();
  sonido.murmullo(0.15);
  pintarMarcador();
  P.lanzamiento = medirLanzamiento(s);
  if (!P.ias[P.sacador]) {
    cartel(P.segundo ? 'Segundo saque' : 'Tu saque', 'Espacio lanza la pelota, Espacio de nuevo en la zona verde', 1.8);
    pintarBarraSaque();
  }
}

// Con que sale la pelota de la mano, y hasta donde hay que dejarla bajar para pegarle con el brazo
// estirado: ese es el mejor punto de impacto.
const lanzamiento = (s) => {
  const k = s.datos.altura / 1.85;
  return { k, y: 1.45 * k, vy: 5.6 * Math.sqrt(k), yIdeal: 2.88 * k, ySuelta: 1.1 * k };
};

// Simula el lanzamiento: en que momento pasa por el punto ideal y cuando se cae.
function medirLanzamiento(s) {
  const l = lanzamiento(s);
  const e = { ...estadoNuevo(), y: l.y, vy: l.vy };
  let t = 0, ideal = 0;
  while (t < 3 && !(e.vy < 0 && e.y < l.ySuelta)) {
    avanzar(e, PASO); t += PASO;
    if (!ideal && e.vy < 0 && e.y <= l.yIdeal) ideal = t;
  }
  return { ideal, fin: t };
}

// Que tan bueno sale el saque segun a cuantos segundos del momento ideal se le pega.
const SAQUE_PERFECTO = 0.035, SAQUE_NULO = 0.3;
const calidadSaque = (t) => clamp(1 - (Math.abs(t - P.lanzamiento.ideal) - SAQUE_PERFECTO) / (SAQUE_NULO - SAQUE_PERFECTO), 0, 1);
const notaSaque = (c) => (c >= 0.95 ? 'perfecto' : c >= 0.6 ? 'bueno' : c >= 0.3 ? 'regular' : 'flojo');

// La barra del saque es el tiempo del lanzamiento: verde donde conviene pegar.
function pintarBarraSaque() {
  const { ideal, fin } = P.lanzamiento;
  const p = (dt) => `${(clamp((ideal + dt) / fin, 0, 1) * 100).toFixed(1)}%`;
  const rojo = '#b23a2e', amarillo = '#e8d24a', verde = '#5fd35a';
  $('saque').style.background = `linear-gradient(90deg, ${rojo} ${p(-SAQUE_NULO)}, ${amarillo} ${p(-SAQUE_NULO / 2)}, ` +
    `${verde} ${p(-SAQUE_PERFECTO)}, ${verde} ${p(SAQUE_PERFECTO)}, ${amarillo} ${p(SAQUE_NULO / 2)}, ${rojo} ${p(SAQUE_NULO)})`;
}

function pelotaEnMano() {
  const s = P.jug[P.sacador], L = lado(P.sacador);
  pelota.poner(s.x, 1.1 * s.datos.altura / 1.85, s.z - L * 0.35);
}

function lanzar() {
  const s = P.jug[P.sacador], l = lanzamiento(s);
  pelotaEnMano();
  pelota.e.y = l.y;
  pelota.e.vy = l.vy;
  s.preparar('saque');
  P.estado = 'lanzada'; P.t = 0;
}

function sacar(op) {
  const s = P.jug[P.sacador];
  const r = ejecutarSaque(s, pelota, { ...op, segundo: P.segundo });
  s.pegar('saque');
  sonido.golpe(1);
  P.xSaque = s.x;
  P.ultimo = P.sacador; P.ultimoTipo = 'saque';
  P.golpes = 1; P.esSaque = true; P.cinta = false;
  P.estado = 'peloteo'; P.t = 0;
  P.ias[1 - P.sacador]?.alGolpeRival();
  P.jug[1 - P.sacador].split();
  if (P.sacador === 1) marcarPique();
  mostrarVelocidad(`Saque <b>${r.kmh}</b> km/h` + (op.nota ? ` · ${op.nota}` : ''));
}

// La unica puerta para pegarle a la pelota en el peloteo, la usan el usuario y la maquina.
function golpear(j, op) {
  const e = pelota.e;
  if (P.estado !== 'peloteo' || P.ultimo === j.indice) return false;
  if (e.piques > 1 || e.rodando) return false;
  if (P.esSaque && e.piques === 0) return false; // el saque no se volea
  const c = puedeGolpear(j, e);
  if (!c) return false;
  const r = ejecutarGolpe(j, pelota, c, op);
  j.pegar(r.tipo, c.derecha === !!j.datos.zurdo);
  if (r.tipo === 'dropshot' || r.tipo === 'volea') sonido.toque();
  else sonido.golpe(r.tipo === 'slice' ? 0.4 : op.potencia ?? 0.6);
  P.ultimo = j.indice; P.ultimoTipo = r.tipo;
  P.golpes++; P.esSaque = false; P.cinta = false;
  P.ias[1 - j.indice]?.alGolpeRival(r.tipo);
  P.jug[1 - j.indice].split();
  if (j.indice === 1) marcarPique(); else { marca.visible = false; P.usuario.plan = null; }
  if (r.tipo !== 'dropshot' && r.tipo !== 'globo') mostrarVelocidad(`${nombreGolpe(r.tipo)} <b>${r.kmh}</b> km/h`);
  else mostrarVelocidad(nombreGolpe(r.tipo));
  return true;
}

function alPique() {
  const e = pelota.e;
  marca.visible = false;
  sonido.pique(clamp(Math.abs(e.vy) / 6, 0.2, 1));
  if (P.estado !== 'peloteo') return;
  if (e.piques === 1) {
    const propio = e.z * lado(P.ultimo) > 0; // quedo de su lado: se fue a la red
    if (P.esSaque) {
      if (!saqueBueno(e.x, e.z, P.sacador, P.xSaque)) return falta(propio ? 'Red' : 'Falta');
      if (P.cinta) return repetirSaque('Let');
    } else if (!pelotaBuena(e.x, e.z, P.ultimo)) {
      const porPoco = !propio && Math.abs(e.x) < MEDIO_ANCHO + 0.45 && Math.abs(e.z) < MEDIO_LARGO + 0.45;
      if (porPoco) sonido.ooh();
      return finPunto(1 - P.ultimo, propio ? 'Red' : 'Out', 'error');
    }
  } else if (e.piques === 2) {
    if (P.golpes === 1) finPunto(P.ultimo, 'Ace', 'ace');
    else finPunto(P.ultimo, `Winner de ${nombreGolpe(P.ultimoTipo).toLowerCase()}`, 'winner');
  }
}

function repetirSaque(texto) {
  mira.visible = false;
  cartel(texto, '', 1.2);
  P.repetir = true;
  P.estado = 'punto'; P.t = 0; P.pausa = 1.4;
}

function falta(texto) {
  if (P.segundo) return finPunto(1 - P.sacador, 'Doble falta', 'doble');
  P.segundo = true;
  repetirSaque(texto === 'Red' ? 'Red · segundo saque' : 'Falta');
}

function finPunto(ganador, texto, tipo) {
  mira.visible = false;
  const autor = tipo === 'error' || tipo === 'doble' ? 1 - ganador : ganador;
  const st = P.stats;
  st[ganador].puntos++;
  if (tipo === 'winner') st[autor].winners++;
  if (tipo === 'ace') { st[autor].aces++; st[autor].winners++; }
  if (tipo === 'error') st[autor].errores++;
  if (tipo === 'doble') st[autor].dobles++;
  if (DEMO) registrarDemo(tipo, texto);

  const r = P.puntaje.punto(ganador);
  let fuerza = 0.4 + (P.golpes > 6 ? 0.2 : 0) + (tipo === 'winner' || tipo === 'ace' ? 0.1 : 0);
  let sub = `Punto de ${P.jug[ganador].datos.nombre}`;
  if (r.game) { fuerza = 0.65; sub = `Game de ${P.jug[ganador].datos.nombre}`; }
  if (r.set) { fuerza = 0.85; sub = `Set de ${P.jug[ganador].datos.nombre}`; }
  if (r.partido) { fuerza = 1; sub = `Partido de ${P.jug[ganador].datos.nombre}`; }
  cartel(texto, sub, 2.1);
  estadio.festejar(fuerza);
  sonido.aplauso(fuerza);
  sonido.murmullo(0.5);
  pintarMarcador();
  P.estado = 'punto'; P.t = 0; P.pausa = r.partido ? 3.2 : 2.4;
  P.segundo = false; P.repetir = false;
}

function terminarPartido() {
  P.estado = 'fin';
  if (DEMO) return nuevoPartido();
  const pt = P.puntaje, g = pt.ganador;
  $('finTitulo').innerHTML = g === 0 ? '¡<b>Ganaste</b>!' : `Ganó <b>${P.jug[1].datos.nombre}</b>`;
  $('finResultado').textContent = pt.setsJugados.map((s) => `${s[0]}-${s[1]}`).join('   ');
  const filas = [['Puntos', 'puntos'], ['Winners', 'winners'], ['Aces', 'aces'], ['Errores', 'errores'], ['Dobles faltas', 'dobles']];
  $('finStats').innerHTML =
    `<tr><th>${P.jug[0].datos.nombre}</th><td></td><th>${P.jug[1].datos.nombre}</th></tr>` +
    filas.map(([n, k]) => `<tr><td>${P.stats[0][k]}</td><td>${n}</td><td>${P.stats[1][k]}</td></tr>`).join('');
  $('fin').classList.remove('oculto');
  $('hud').classList.add('oculto');
}

// ---------- Control del usuario ----------
function controlUsuario(dt, flancos) {
  const j = P.jug[0], u = P.usuario, e = pelota.e;
  for (const k of TECLAS_GOLPE) {
    if (flancos.recien[k]) { u.activo = true; u.tecla = k; u.carga = 0; u.gracia = 0.22; u.apX = 0; u.apZ = 0; }
  }
  if (u.activo) {
    if (control.abajo[u.tecla]) { u.carga = Math.min(1, u.carga + dt / 0.75); u.gracia = 0.22; }
    else {
      u.gracia -= dt;
      if (u.gracia <= 0) {
        // Solto la tecla sin que llegara la pelota: swing al aire.
        u.activo = false; u.carga = 0;
        if (P.ultimo === 1 && Math.abs(e.z - j.z) < 5) j.pegar(...animacionDe(u.tecla, j)); else j.soltar();
      }
    }
  }
  // Con la tecla de golpe apretada las flechas dejan de mover y pasan a apuntar: el jugador se
  // acomoda solo a la pelota, mas lento que corriendo (conviene llegar primero y armar despues).
  // La ultima flecha tocada queda como direccion, no hace falta tenerla apretada en el impacto.
  const armando = u.activo && P.ultimo === 1 && u.plan;
  if (armando) j.irA(u.plan.x, u.plan.z, dt, 0.75);
  else j.mover(control.dirX, -control.dirZ, dt, 1);
  mira.visible = !!armando;
  if (!u.activo) return;
  if (control.dirX) u.apX = control.dirX;
  if (control.dirZ) u.apZ = control.dirZ;
  if (armando) {
    const o = objetivo(j, u.tecla === 'golpe' ? 'drive' : u.tecla, u.apX, u.apZ);
    mira.position.set(o.x, 0.02, o.z);
  }
  j.preparar(...animacionDe(u.tecla, j));
  const ok = golpear(j, {
    tecla: u.tecla,
    apX: u.apX, apZ: u.apZ,
    potencia: 0.35 + 0.65 * u.carga,
    calidad: clamp(0.3 + u.carga * 2.8, 0, 1), // armar tarde es pegar mal
    error: 0.8,
  });
  if (ok) { u.activo = false; u.carga = 0; mira.visible = false; }
}

// [tipo de animacion, si la pelota viene del lado del reves]
function animacionDe(tecla, j) {
  const derecha = (pelota.e.x - j.x) * lado(j.indice) > 0;
  const deReves = derecha === !!j.datos.zurdo;
  if (tecla !== 'golpe') return [tecla, deReves];
  return [deReves ? 'reves' : 'drive', deReves];
}

// ---------- Paso de simulacion ----------
function paso(dt, flancos) {
  P.t += dt;
  const e = pelota.e;
  const usuarioSaca = !P.ias[P.sacador];
  const ctx = (i) => ({
    pelota, rival: P.jug[1 - i], golpear,
    viene: P.estado === 'peloteo' && P.ultimo === 1 - i && e.piques <= 1,
  });

  if (P.estado === 'presaque') {
    pelotaEnMano();
    if (usuarioSaca) { if (flancos.recien.golpe) lanzar(); }
    else {
      if (P.t > 1.5) lanzar();
      if (!P.ias[0]) P.jug[0].mover(control.dirX, 0, dt, 0.7); // acomodarse para recibir
    }
  } else if (P.estado === 'lanzada') {
    pelota.avanzar(dt);
    const k = P.jug[P.sacador].datos.altura / 1.85;
    if (usuarioSaca) {
      if (flancos.recien.golpe && e.y > 1.6 * k) {
        const calidad = calidadSaque(P.t);
        sacar({ apX: control.dirX, calidad, nota: notaSaque(calidad) });
      }
    } else if (e.vy < 0 && e.y <= 2.9 * k) {
      sacar(P.ias[P.sacador].saque(P.segundo));
    }
    if (P.estado === 'lanzada' && e.vy < 0 && e.y < 1.1 * k) {
      // La dejo caer: la agarra y vuelve a empezar, sin falta.
      P.jug[P.sacador].soltar();
      P.estado = 'presaque'; P.t = 0.6;
    }
  } else if (P.estado === 'peloteo') {
    if (P.ias[0]) P.ias[0].actualizar(dt, ctx(0)); else controlUsuario(dt, flancos);
    P.ias[1].actualizar(dt, ctx(1));
    moverPelota(dt);
  } else if (P.estado === 'punto') {
    P.jug.forEach((j) => j.mover(0, 0, dt));
    moverPelota(dt);
    if (P.t > P.pausa) {
      if (P.puntaje.terminado) terminarPartido(); else prepararPunto();
    }
  }
}

function moverPelota(dt) {
  const e = pelota.e;
  const ev = pelota.avanzar(dt);
  if (ev === 'cinta') { P.cinta = true; sonido.red(); }
  else if (ev === 'red') sonido.red();
  else if (ev === 'pique') alPique();
  // Muros del estadio.
  if (Math.abs(e.x) > 10.3) { e.x = Math.sign(e.x) * 10.3; e.vx *= -0.3; }
  if (Math.abs(e.z) > 18.3) { e.z = Math.sign(e.z) * 18.3; e.vz *= -0.3; }
}

// ---------- HUD ----------
let tCartel = 0, tVel = 0;
function cartel(texto, sub = '', segundos = 2) {
  $('cartel').innerHTML = texto + (sub ? `<small>${sub}</small>` : '');
  $('cartel').classList.remove('apagado');
  tCartel = segundos;
}
function mostrarVelocidad(html) {
  $('velocidad').innerHTML = html;
  $('velocidad').classList.remove('apagado');
  tVel = 2.2;
}

function pintarMarcador() {
  const pt = P.puntaje;
  const puntos = pt.puntosTexto;
  $('marcador').innerHTML = [0, 1].map((i) =>
    `<tr><td class="saca">${pt.saca === i && !pt.terminado ? '●' : ''}</td>` +
    `<td class="nombre">${P.jug[i].datos.nombre}</td>` +
    pt.setsJugados.map((s) => `<td class="set">${s[i]}</td>`).join('') +
    (pt.terminado ? '' : `<td class="games">${pt.games[i]}</td><td class="puntos">${puntos[i]}</td>`) +
    '</tr>').join('');
}

// ---------- Camara ----------
const depurar = { cam: null };
const camPos = new THREE.Vector3(0, 30, 46), camMira = new THREE.Vector3(0, 0, 0);
function moverCamara(dt, t) {
  let pos, mira;
  if (!P || P.estado === 'fin') {
    // Paseo lento por el estadio detras del menu.
    const a = t * 0.07;
    pos = new THREE.Vector3(Math.sin(a) * 9, 9.5, 23.5);
    mira = new THREE.Vector3(0, 0.5, -2);
  } else {
    const j = P.jug[0];
    const z = clamp(j.z + 9.5, 21, 27);
    pos = new THREE.Vector3(j.x * 0.45 + pelota.e.x * 0.08, 7.6, z);
    mira = new THREE.Vector3(j.x * 0.3 + pelota.e.x * 0.12, 0, z - 17);
  }
  const f = Math.min(1, 3.5 * dt);
  camPos.lerp(pos, f); camMira.lerp(mira, f);
  if (depurar.cam) { camPos.fromArray(depurar.cam[0]); camMira.fromArray(depurar.cam[1]); }
  camera.position.copy(camPos);
  camera.lookAt(camMira);
}

// ---------- Bucle ----------
const reloj = new THREE.Clock();
let acumulado = 0, tiempo = 0;
function cuadro() {
  requestAnimationFrame(cuadro);
  const dt = Math.min(reloj.getDelta(), 0.1);
  tiempo += dt;
  const flancos = control.flancos();
  if (flancos.recien.pausa && P && P.estado !== 'fin' && !DEMO) alternarPausa();

  if (P && !pausado && P.estado !== 'fin') {
    acumulado += dt * ACELERAR;
    let primero = true;
    while (acumulado >= PASO) {
      // Los flancos del teclado valen para un solo paso.
      paso(PASO, primero ? flancos : { recien: {}, soltadas: {} });
      primero = false;
      acumulado -= PASO;
      if (!P || P.estado === 'fin') break;
    }
    P.jug.forEach((j) => j.dibujar(dt * Math.min(ACELERAR, 4)));
    $('potencia').firstElementChild.style.width = `${P.usuario.activo ? P.usuario.carga * 100 : 0}%`;
    const sacando = !P.ias[P.sacador] && (P.estado === 'presaque' || P.estado === 'lanzada');
    $('saque').classList.toggle('oculto', !sacando);
    $('potencia').classList.toggle('oculto', sacando);
    if (sacando) $('saque').firstElementChild.style.left = `${P.estado === 'lanzada' ? clamp(P.t / P.lanzamiento.fin, 0, 1) * 100 : 0}%`;
  }
  pelota.dibujar(pausado ? 0 : dt);
  if (!pausado) {
    estadio.actualizar(dt, tiempo);
    if ((tCartel -= dt) <= 0) $('cartel').classList.add('apagado');
    if ((tVel -= dt) <= 0) $('velocidad').classList.add('apagado');
  }
  moverCamara(dt, tiempo);
  renderer.render(scene, camera);
}

function alternarPausa() {
  pausado = !pausado;
  $('pausa').classList.toggle('oculto', !pausado);
  sonido.silenciar(pausado);
}

function alMenu() {
  if (P) P.jug.forEach((j) => scene.remove(j.grupo));
  P = null; pausado = false;
  pelota.visible = marca.visible = mira.visible = false;
  sonido.silenciar(false);
  sonido.murmullo(0.3);
  ['fin', 'pausa', 'hud'].forEach((id) => $(id).classList.add('oculto'));
  $('menu').classList.remove('oculto');
}

// ---------- Menu ----------
function tarjeta(p, chica) {
  const barras = chica ? '' : ATRIBUTOS.map(([k, n]) =>
    `<div class="attr">${n}<i><b style="width:${p.attrs[k] * 10}%"></b></i></div>`).join('');
  return `<div class="tarjeta ${chica ? 'chica' : ''}" data-id="${p.id}">` +
    `<div class="n">${p.nombre}${chica ? '' : `<span>${p.pais}${p.zurdo ? ' · zurdo' : ''}</span>`}</div>` +
    (chica ? '' : `<div class="p">${p.perfil}</div>`) + barras + '</div>';
}

function grupo(idCont, html, clave) {
  const cont = $(idCont);
  cont.innerHTML = html;
  const marcar = () => cont.querySelectorAll('[data-id]').forEach((el) =>
    el.classList.toggle('elegida', el.dataset.id === eleccion[clave]));
  cont.addEventListener('click', (ev) => {
    const el = ev.target.closest('[data-id]');
    if (!el) return;
    eleccion[clave] = el.dataset.id;
    marcar();
  });
  marcar();
}

grupo('elegirYo', PLANTEL.map((p) => tarjeta(p, false)).join(''), 'yo');
grupo('elegirRival',
  '<div class="tarjeta chica" data-id="azar"><div class="n">Al azar</div></div>' +
  PLANTEL.map((p) => tarjeta(p, true)).join(''), 'rival');
grupo('elegirFormato', Object.entries(FORMATOS).map(([k, f]) => `<div class="opcion" data-id="${k}">${f.nombre}</div>`).join(''), 'formato');
grupo('elegirDificultad', Object.entries(DIFICULTADES).map(([k, d]) => `<div class="opcion" data-id="${k}">${d.nombre}</div>`).join(''), 'dificultad');

$('jugar').addEventListener('click', nuevoPartido);
$('revancha').addEventListener('click', nuevoPartido);
$('seguir').addEventListener('click', alternarPausa);
$('salir').addEventListener('click', alMenu);
$('alMenu').addEventListener('click', alMenu);

// ---------- Modo demo (?demo=1&vel=8&dif=dificil): maquina contra maquina, con conteo de como termina cada punto ----------
const demo = { puntos: 0, golpes: 0, tipos: {}, textos: {} };
function registrarDemo(tipo, texto) {
  demo.puntos++; demo.golpes += P.golpes;
  demo.tipos[tipo] = (demo.tipos[tipo] ?? 0) + 1;
  const t = texto.startsWith('Winner') ? 'Winner' : texto;
  demo.textos[t] = (demo.textos[t] ?? 0) + 1;
}
if (DEMO) {
  window.__demo = demo;
  if (DIFICULTADES[params.get('dif')]) eleccion.dificultad = params.get('dif');
  eleccion.yo = PLANTEL[Math.floor(Math.random() * PLANTEL.length)].id;
  nuevoPartido();
}
// Para mirar poses desde la consola: __juego.depurar.cam = [[x, y, z], [x, y, z]] fija la camara.
window.__juego = { get P() { return P; }, pelota, eleccion, scene, depurar };

cuadro();
