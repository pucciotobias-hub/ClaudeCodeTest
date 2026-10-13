// Estadio tipo Wimbledon: cielo, cesped, lineas, red, muros, tribunas, techo, publico y utileria.
// Todo lo que no son jugadores ni pelota. Ejes en cancha.js (z=0 es la red, la camara mira desde z>0).
import * as THREE from 'three';
import {
  MEDIO_ANCHO, MEDIO_ANCHO_DOBLES, MEDIO_LARGO, SAQUE,
  RED_CENTRO, RED_POSTE, POSTE_X, alturaRed,
} from './cancha.js';

// ---------------------------------------------------------------- utilidades
// Generador con semilla fija: el estadio sale igual en cada carga.
function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = mulberry32(20261013);
const elegir = (arr) => arr[Math.floor(rnd() * arr.length)];

const matCache = new Map();
function mat(color, extra) {
  if (extra) return new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.85, ...extra });
  if (!matCache.has(color)) matCache.set(color, new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.85 }));
  return matCache.get(color);
}
const geoCache = new Map();
function geoCaja(w, h, d) {
  const k = `${w}|${h}|${d}`;
  if (!geoCache.has(k)) geoCache.set(k, new THREE.BoxGeometry(w, h, d));
  return geoCache.get(k);
}
function caja(w, h, d, color, x, y, z, padre, sombra = true) {
  const m = new THREE.Mesh(geoCaja(w, h, d), typeof color === 'object' ? color : mat(color));
  m.position.set(x, y, z);
  m.castShadow = sombra;
  m.receiveShadow = true;
  padre.add(m);
  return m;
}
// Caja por rangos (x0..x1, y0..y1, z0..z1).
function cajaR(x0, x1, y0, y1, z0, z1, color, padre, sombra = false) {
  return caja(x1 - x0, y1 - y0, z1 - z0, color, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, padre, sombra);
}
function cilindro(rt, rb, h, color, x, y, z, padre, seg = 8) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat(color));
  m.position.set(x, y, z);
  m.castShadow = m.receiveShadow = true;
  padre.add(m);
  return m;
}
function canvasTex(w, h, dibujar, repetir = false) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  dibujar(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 16; // el renderer lo recorta a lo que soporte la GPU
  if (repetir) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

// ---------------------------------------------------------------- cesped
const CAN_W = 1024, CAN_H = 1792;                 // 22 x 38 m
const PX_X = CAN_W / 22, PX_Z = CAN_H / 38;

function texturaCesped() {
  return canvasTex(CAN_W, CAN_H, (ctx, W, H) => {
    // Franjas de corte a lo largo (z), alternando dos verdes.
    const ancho = 2.0 * PX_X;
    for (let k = 0; k * ancho < W; k++) {
      ctx.fillStyle = k % 2 ? '#4f9a3d' : '#5eab49';
      ctx.fillRect(k * ancho, 0, ancho + 1, H);
    }
    // Manchas grandes de tono y hebras finas en el sentido del corte.
    for (let i = 0; i < 2500; i++) {
      ctx.fillStyle = rnd() < 0.5 ? 'rgba(30,80,20,0.05)' : 'rgba(150,200,90,0.05)';
      ctx.beginPath();
      ctx.arc(rnd() * W, rnd() * H, 6 + rnd() * 26, 0, 6.283);
      ctx.fill();
    }
    for (let i = 0; i < 9000; i++) {
      ctx.strokeStyle = rnd() < 0.5 ? 'rgba(25,70,15,0.10)' : 'rgba(170,215,110,0.10)';
      ctx.lineWidth = 1;
      const x = rnd() * W, y = rnd() * H;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + (rnd() - 0.5) * 2, y + 6 + rnd() * 22); ctx.stroke();
    }
    // Desgaste: tierra pisada detras de las lineas de fondo y en la T de saque.
    const mancha = (x, z, rx, rz, rgb, a) => {
      ctx.save();
      ctx.translate((x + 11) * PX_X, (z + 19) * PX_Z);
      ctx.scale(rx * PX_X, rz * PX_Z);
      const g = ctx.createRadialGradient(0, 0, 0, 0, 0, 1);
      g.addColorStop(0, `rgba(${rgb},${a})`);
      g.addColorStop(0.55, `rgba(${rgb},${a * 0.55})`);
      g.addColorStop(1, `rgba(${rgb},0)`);
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(0, 0, 1, 0, 6.283); ctx.fill();
      ctx.restore();
    };
    for (const s of [-1, 1]) {
      mancha(0, s * (MEDIO_LARGO + 0.2), 4.6, 2.6, '170,160,80', 0.35);   // amarillento, mas amplio
      mancha(0, s * (MEDIO_LARGO + 0.35), 3.0, 1.5, '112,84,48', 0.55);   // tierra
      mancha(0, s * (MEDIO_LARGO - 0.6), 2.2, 0.9, '130,110,55', 0.40);
      mancha(0, s * SAQUE, 1.7, 0.9, '125,100,55', 0.35);                 // T de saque
      for (let i = 0; i < 26; i++) {
        mancha((rnd() - 0.5) * 7.5, s * (MEDIO_LARGO + (rnd() - 0.3) * 1.4), 0.3 + rnd() * 0.5, 0.3 + rnd() * 0.4, '105,78,44', 0.25);
      }
    }
    mancha(0, 0, 2.4, 0.9, '140,125,60', 0.18); // pisadas cerca de la red
    // Ruido fino por pixel.
    const img = ctx.getImageData(0, 0, W, H), d = img.data;
    for (let i = 0; i < d.length; i += 4) {
      const n = (rnd() - 0.5) * 18;
      d[i] += n; d[i + 1] += n * 1.1; d[i + 2] += n * 0.6;
    }
    ctx.putImageData(img, 0, 0);
  });
}

function crearCesped(scene) {
  const m = new THREE.Mesh(
    new THREE.PlaneGeometry(22, 38),
    new THREE.MeshStandardMaterial({ map: texturaCesped(), roughness: 1 }),
  );
  m.rotation.x = -Math.PI / 2;
  m.receiveShadow = true;
  scene.add(m);
  // Suelo de afuera, un poco mas abajo para no pelear con el cesped.
  const fuera = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), mat(0x5f7d52));
  fuera.rotation.x = -Math.PI / 2;
  fuera.position.y = -0.03;
  fuera.receiveShadow = true;
  scene.add(fuera);
}

// ---------------------------------------------------------------- lineas
function crearLineas(scene) {
  const blanco = new THREE.MeshStandardMaterial({
    color: 0xffffff, roughness: 0.9, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
  });
  const L = MEDIO_LARGO, MA = MEDIO_ANCHO, MAD = MEDIO_ANCHO_DOBLES;
  const g = new THREE.Group();
  const linea = (cx, cz, w, d) => {
    const m = new THREE.Mesh(geoCaja(w, 0.012, d), blanco);
    m.position.set(cx, 0.006, cz);
    m.receiveShadow = true;
    g.add(m);
  };
  for (const s of [-1, 1]) {
    linea(0, s * (L - 0.05), 2 * MAD, 0.10);                 // fondo (10 cm, hacia adentro)
    linea(0, s * (L - 0.15), 0.05, 0.10);                    // marquita central
    linea(0, s * SAQUE, 2 * MA, 0.05);                       // linea de saque
    linea(s * (MAD - 0.025), 0, 0.05, 2 * L);                // lateral de dobles
    linea(s * (MA - 0.025), 0, 0.05, 2 * L);                 // lateral de singles
  }
  linea(0, 0, 0.05, 2 * SAQUE);                              // central de saque
  scene.add(g);
}

// ---------------------------------------------------------------- red
function crearRed(scene) {
  const g = new THREE.Group();
  for (const s of [-1, 1]) {
    cilindro(0.05, 0.06, RED_POSTE + 0.06, 0x2b2e33, s * POSTE_X, (RED_POSTE + 0.06) / 2, 0, g);
  }
  const textura = canvasTex(64, 64, (ctx, w, h) => {
    ctx.fillStyle = 'rgba(15,18,22,0.30)';
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = 'rgba(10,12,15,0.95)';
    ctx.lineWidth = 4;
    ctx.strokeRect(0, 0, w, h);
  }, true);
  const CELDA = 0.08, N = 48;
  // Tira entre dos curvas de altura sobre z=0 (la altura sigue alturaRed(x)).
  const tira = (fInf, fSup) => {
    const pos = [], uv = [], idx = [];
    for (let i = 0; i <= N; i++) {
      const x = -POSTE_X + (2 * POSTE_X * i) / N;
      const y0 = fInf(x), y1 = fSup(x);
      pos.push(x, y0, 0, x, y1, 0);
      uv.push((x + POSTE_X) / CELDA, y0 / CELDA, (x + POSTE_X) / CELDA, y1 / CELDA);
      if (i < N) { const a = i * 2; idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    geo.setIndex(idx);
    geo.computeVertexNormals();
    return geo;
  };
  const malla = new THREE.Mesh(
    tira(() => 0.01, (x) => alturaRed(x) - 0.07),
    new THREE.MeshStandardMaterial({ map: textura, transparent: true, side: THREE.DoubleSide, depthWrite: false, roughness: 1 }),
  );
  malla.renderOrder = 2;
  g.add(malla);
  const banda = new THREE.Mesh(
    tira((x) => alturaRed(x) - 0.07, (x) => alturaRed(x)),
    new THREE.MeshStandardMaterial({ color: 0xffffff, side: THREE.DoubleSide, roughness: 0.8 }),
  );
  banda.castShadow = true;
  g.add(banda);
  caja(0.05, RED_CENTRO - 0.07, 0.03, 0xffffff, 0, (RED_CENTRO - 0.07) / 2 + 0.01, 0, g);   // faja central
  scene.add(g);
}

// ---------------------------------------------------------------- cielo y luz
function crearLuces(scene) {
  scene.background = new THREE.Color(0x8ecbf0);
  scene.fog = new THREE.Fog(0xb4d8ee, 70, 300);
  scene.add(new THREE.HemisphereLight(0xdcefff, 0x6a7a55, 1.15));
  const sol = new THREE.DirectionalLight(0xfff0d6, 2.3);
  sol.position.set(16, 24, 10);
  sol.castShadow = true;
  sol.shadow.mapSize.set(2048, 2048);
  sol.shadow.bias = -0.0004;
  sol.shadow.normalBias = 0.03;
  scene.add(sol, sol.target);
  // Ajusta la camara ortografica de sombra a la caja x ±12, z ±20, y 0..4 vista desde el sol.
  const cam = new THREE.OrthographicCamera();
  cam.position.copy(sol.position);
  cam.lookAt(0, 0, 0);
  cam.updateMatrixWorld(true);
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9, d0 = 1e9, d1 = -1e9;
  const v = new THREE.Vector3();
  for (const x of [-12, 12]) for (const y of [0, 4]) for (const z of [-20, 20]) {
    v.set(x, y, z).applyMatrix4(cam.matrixWorldInverse);
    x0 = Math.min(x0, v.x); x1 = Math.max(x1, v.x);
    y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y);
    d0 = Math.min(d0, -v.z); d1 = Math.max(d1, -v.z);
  }
  const sc = sol.shadow.camera;
  sc.left = x0 - 0.5; sc.right = x1 + 0.5; sc.bottom = y0 - 0.5; sc.top = y1 + 0.5;
  sc.near = Math.max(0.5, d0 - 15); sc.far = d1 + 5;
  sc.updateProjectionMatrix();
}

// ---------------------------------------------------------------- muro y carteles
const SPONSORS = [
  ['AQUAVIDA', '#0b4f8a', '#ffffff'], ['NORTEX', '#c8102e', '#ffffff'], ['SOLARIS', '#f2b705', '#1b1b1b'],
  ['PAMPA BANK', '#1c6b3a', '#ffffff'], ['TERRA CAFE', '#4a2c17', '#f4dfc0'], ['VELOZ', '#101820', '#ff5a1f'],
  ['LUMINA', '#6a2c91', '#ffffff'], ['ORIGEN', '#e8e4da', '#1c3d2e'],
];
function atlasCarteles() {
  return canvasTex(2048, 256, (ctx) => {
    SPONSORS.forEach(([txt, bg, fg], k) => {
      const cx = (k % 4) * 512, cy = Math.floor(k / 4) * 128;
      ctx.fillStyle = bg; ctx.fillRect(cx, cy, 512, 128);
      ctx.strokeStyle = fg; ctx.lineWidth = 4; ctx.strokeRect(cx + 8, cy + 8, 496, 112);
      ctx.fillStyle = fg; ctx.font = 'bold 64px sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(txt, cx + 256, cy + 68);
    });
  });
}

function crearMuros(scene) {
  const verde = 0x1d4a30;
  const X = 10.5, Z = 18.5, ALTO = 1.0, G = 0.2;
  // Muros de 1 m: el sur no puede tapar la camara.
  caja(G, ALTO, 2 * Z + G, verde, -X, ALTO / 2, 0, scene);
  caja(G, ALTO, 2 * Z + G, verde, X, ALTO / 2, 0, scene);
  caja(2 * X + G, ALTO, G, verde, 0, ALTO / 2, -Z, scene);
  caja(2 * X + G, ALTO, G, verde, 0, ALTO / 2, Z, scene);

  const atlas = atlasCarteles();
  const material = new THREE.MeshStandardMaterial({ map: atlas, roughness: 0.7 });
  // Cada cartel toma su celda del atlas (la fila 0 esta arriba del canvas).
  const geoCartel = SPONSORS.map((_, k) => {
    const g = new THREE.PlaneGeometry(2.4, 0.62);
    const uv = g.attributes.uv, c = k % 4, r = Math.floor(k / 4);
    for (let i = 0; i < uv.count; i++) {
      uv.setXY(i, (c + uv.getX(i)) / 4, 1 - (r + 1) / 2 + uv.getY(i) / 2);
    }
    return g;
  });
  let n = 0;
  const poner = (x, z, rotY) => {
    const m = new THREE.Mesh(geoCartel[n++ % SPONSORS.length], material);
    m.position.set(x, 0.5, z);
    m.rotation.y = rotY;
    scene.add(m);
  };
  const paso = 2.5;
  for (let z = -Z + 1.4; z < Z - 1; z += paso) {
    poner(-X + G / 2 + 0.01, z, Math.PI / 2);
    poner(X - G / 2 - 0.01, z, -Math.PI / 2);
  }
  for (let x = -X + 1.4; x < X - 1; x += paso) {
    poner(x, -Z + G / 2 + 0.01, 0);
    poner(x, Z - G / 2 - 0.01, Math.PI);
  }
}

// ---------------------------------------------------------------- tribunas
const FILAS = 14, ALZADA = 0.45, PROF = 0.8;
const X_FRENTE = 10.7;   // frente de la fila 0 (lados), justo detras del muro
const Z_NORTE = 18.6;    // frente de la fila 0 al norte
const Z_SUR = 25.0;      // la tribuna sur arranca bien atras de la camara
// Cada lado es un anillo: las esquinas las cierran este/oeste (rectangulos que no se pisan).
const zNorteExt = (i) => Z_NORTE + PROF * (i + 1);
const zSurExt = (i) => Z_SUR + PROF * (i + 1);

function crearTribunas(scene) {
  const g = new THREE.Group();
  const cemento = 0x9b9c96, asiento = 0x2f6b46, trasero = 0x6e7f73;
  for (let i = 0; i < FILAS; i++) {
    const top = ALZADA * (i + 1), fr = X_FRENTE + PROF * i;
    for (const s of [-1, 1]) {
      const a = s * fr, b = s * (fr + PROF);
      cajaR(Math.min(a, b), Math.max(a, b), 0, top, -zNorteExt(i), zSurExt(i), cemento, g);
      const c0 = s * (fr + 0.1), c1 = s * (fr + 0.55);
      cajaR(Math.min(c0, c1), Math.max(c0, c1), top, top + 0.05, -zNorteExt(i) + 0.1, zSurExt(i) - 0.1, asiento, g);
    }
    const zn = -(Z_NORTE + PROF * i), zs = Z_SUR + PROF * i;
    cajaR(-fr, fr, 0, top, zn - PROF, zn, cemento, g);
    cajaR(-fr + 0.1, fr - 0.1, top, top + 0.05, zn - 0.55, zn - 0.1, asiento, g);
    cajaR(-fr, fr, 0, top, zs, zs + PROF, cemento, g);
    cajaR(-fr + 0.1, fr - 0.1, top, top + 0.05, zs + 0.1, zs + 0.55, asiento, g);
  }
  // Muros de fondo que cierran la parte de atras.
  const fondoX = X_FRENTE + PROF * FILAS, alto = ALZADA * FILAS + 1.5;
  for (const s of [-1, 1]) {
    cajaR(Math.min(s * fondoX, s * (fondoX + 0.3)), Math.max(s * fondoX, s * (fondoX + 0.3)), 0, alto, -zNorteExt(FILAS - 1), zSurExt(FILAS - 1), trasero, g);
  }
  const zn = Z_NORTE + PROF * FILAS, zs = Z_SUR + PROF * FILAS;
  cajaR(-fondoX, fondoX, 0, alto, -zn - 0.3, -zn, trasero, g);
  cajaR(-fondoX, fondoX, 0, alto, zs, zs + 0.3, trasero, g);
  scene.add(g);
}

// Techo parcial sobre las tribunas oeste, este y norte (la sur no lleva: esta detras de la camara).
function crearTecho(scene) {
  const blanco = 0xe9e7e0, gris = 0x5c6168;
  const xf = X_FRENTE + PROF * 6, xb = X_FRENTE + PROF * FILAS + 1.1;
  const yf = 8.3, yb = 9.8;
  const largo = Math.hypot(xb - xf, yb - yf), ang = Math.atan2(yb - yf, xb - xf);
  const lado = (dx, dz, mitad) => {
    const g = new THREE.Group();
    g.rotation.y = Math.atan2(-dz, dx);
    const losa = caja(largo, 0.18, 2 * mitad, blanco, (xf + xb) / 2, (yf + yb) / 2, 0, g, false);
    losa.rotation.z = ang;
    const n = Math.ceil((2 * mitad) / 6) + 1;
    for (let k = 0; k < n; k++) {
      const z = -mitad + (2 * mitad * k) / (n - 1);
      const costilla = caja(largo, 0.3, 0.16, gris, (xf + xb) / 2, (yf + yb) / 2 - 0.24, z, g, false);
      costilla.rotation.z = ang;
      caja(0.4, yb - 0.1, 0.4, gris, xb - 0.5, (yb - 0.1) / 2, z, g, false);   // columna trasera
    }
    caja(0.2, 0.3, 2 * mitad, gris, xf, yf - 0.2, 0, g, false);               // viga del frente
    scene.add(g);
  };
  lado(-1, 0, 21);
  lado(1, 0, 21);
  lado(0, -1, X_FRENTE + PROF * 6);
}

function crearMarcador(scene) {
  const g = new THREE.Group();
  g.position.set(X_FRENTE + PROF * 6 + 0.1, 6.9, 0);
  caja(0.3, 2.2, 9.2, 0x14171c, 0, 0, 0, g, false);
  caja(0.06, 0.3, 0.06, 0x333333, 0, 1.25, -3.5, g, false);
  caja(0.06, 0.3, 0.06, 0x333333, 0, 1.25, 3.5, g, false);
  const tex = canvasTex(1024, 256, (ctx, w, h) => {
    ctx.fillStyle = '#0a0d12'; ctx.fillRect(0, 0, w, h);
    ctx.font = 'bold 56px monospace'; ctx.textBaseline = 'middle';
    const fila = (y, nombre, sets, juego, saca) => {
      ctx.fillStyle = '#f6c945'; ctx.textAlign = 'left';
      ctx.fillText((saca ? '● ' : '  ') + nombre, 30, y);
      ctx.fillStyle = '#ffffff'; ctx.textAlign = 'right';
      ctx.fillText(sets, 760, y);
      ctx.fillStyle = '#7dff9a'; ctx.fillText(juego, 990, y);
    };
    fila(80, 'R. MONTERO', '6  4  3', '30', true);
    fila(190, 'T. ALVAREZ', '3  6  2', '15', false);
  });
  const pantalla = new THREE.Mesh(new THREE.PlaneGeometry(8.6, 2.0), new THREE.MeshBasicMaterial({ map: tex }));
  pantalla.position.x = -0.16;
  pantalla.rotation.y = -Math.PI / 2;   // mira hacia la cancha
  g.add(pantalla);
  scene.add(g);
}

// ---------------------------------------------------------------- figuras, silla y bancos
function persona(padre, x, z, rotY, camisa, pantalon, escala = 1) {
  const g = new THREE.Group();
  g.position.set(x, 0, z);
  g.rotation.y = rotY;
  g.scale.setScalar(escala);
  caja(0.2, 0.8, 0.18, pantalon, -0.1, 0.4, 0, g);
  caja(0.2, 0.8, 0.18, pantalon, 0.1, 0.4, 0, g);
  caja(0.42, 0.55, 0.24, camisa, 0, 1.08, 0, g);
  caja(0.1, 0.5, 0.1, camisa, -0.27, 1.05, 0, g);
  caja(0.1, 0.5, 0.1, camisa, 0.27, 1.05, 0, g);
  const cab = new THREE.Mesh(new THREE.IcosahedronGeometry(0.13, 0), mat(0xe0ac82));
  cab.position.y = 1.5; cab.castShadow = true; g.add(cab);
  caja(0.3, 0.07, 0.3, camisa, 0, 1.62, 0.02, g);   // gorra
  padre.add(g);
}

function crearUtileria(scene) {
  // Silla alta del umpire junto al poste izquierdo.
  const g = new THREE.Group();
  g.position.set(-7.3, 0, 0);
  const verde = 0x1e4d2b, SY = 1.9;
  for (const dx of [-0.35, 0.35]) for (const dz of [-0.4, 0.4]) caja(0.08, SY, 0.08, verde, dx, SY / 2, dz, g);
  caja(0.8, 0.07, 0.9, verde, 0, SY, 0, g);                              // asiento
  caja(0.07, 0.55, 0.9, verde, -0.37, SY + 0.3, 0, g);                   // respaldo
  caja(0.6, 0.05, 0.6, verde, 0.5, 0.95, 0, g);                          // escalon
  caja(0.1, 0.05, 0.9, verde, 0.5, 0.35, 0, g);
  caja(0.5, 0.05, 0.5, 0x2b2e33, 0.6, SY + 0.05, 0.42, g);               // mesita
  // Umpire sentado de frente a la cancha (+x).
  const u = new THREE.Group();
  u.rotation.y = Math.PI / 2;
  u.position.set(0, SY + 0.04, 0);
  caja(0.38, 0.5, 0.22, 0x1d2d5a, 0, 0.3, 0, u);                          // saco
  caja(0.3, 0.12, 0.5, 0xeeeeee, -0.09, 0.07, 0.25, u);                   // muslos
  caja(0.3, 0.12, 0.5, 0xeeeeee, 0.09, 0.07, 0.25, u);
  caja(0.12, 0.45, 0.12, 0xeeeeee, -0.09, -0.2, 0.48, u);
  caja(0.12, 0.45, 0.12, 0xeeeeee, 0.09, -0.2, 0.48, u);
  caja(0.1, 0.1, 0.4, 0x1d2d5a, -0.26, 0.4, 0.15, u);
  caja(0.1, 0.1, 0.4, 0x1d2d5a, 0.26, 0.4, 0.15, u);
  const cab = new THREE.Mesh(new THREE.IcosahedronGeometry(0.13, 0), mat(0xe0ac82));
  cab.position.y = 0.72; cab.castShadow = true; u.add(cab);
  caja(0.4, 0.04, 0.4, 0xf3e6b8, 0, 0.83, 0, u);                          // sombrero
  g.add(u);
  scene.add(g);

  // Jueces de linea y alcanzapelotas quietos contra los muros.
  const FP = Math.PI;
  persona(scene, -8.5, -17.9, 0, 0x1d2d5a, 0xdddddd);
  persona(scene, 8.5, -17.9, 0, 0x1d2d5a, 0xdddddd);
  persona(scene, -8.5, 17.9, FP, 0x1d2d5a, 0xdddddd);
  persona(scene, 8.5, 17.9, FP, 0x1d2d5a, 0xdddddd);
  persona(scene, 9.9, -5.5, -Math.PI / 2, 0x1d2d5a, 0xdddddd);
  persona(scene, 9.9, 6.5, -Math.PI / 2, 0x1d2d5a, 0xdddddd);
  persona(scene, -2.5, -17.9, 0, 0x8c2f39, 0x2a2f45, 0.8);                // alcanzapelotas
  persona(scene, 2.5, 17.9, FP, 0x8c2f39, 0x2a2f45, 0.8);

  // Bancos de los jugadores, uno a cada lado de la silla.
  for (const z of [-3.8, 3.8]) {
    const b = new THREE.Group();
    b.position.set(-9.55, 0, z);
    caja(0.45, 0.06, 2.2, 0x23262b, 0, 0.45, 0, b);
    caja(0.06, 0.45, 2.2, 0x23262b, -0.22, 0.75, 0, b);
    caja(0.06, 0.45, 0.4, 0x23262b, 0, 0.22, -0.9, b);
    caja(0.06, 0.45, 0.4, 0x23262b, 0, 0.22, 0.9, b);
    caja(0.3, 0.05, 0.5, 0xffffff, 0.02, 0.5, -0.5, b);                   // toalla
    caja(0.35, 0.3, 0.7, 0x1c3d6b, 0.0, 0.63, 0.5, b);                    // bolso
    scene.add(b);
  }
}

// ---------------------------------------------------------------- publico
const BLANCOS = [0xffffff, 0xfaf6ee, 0xf2f2f2, 0xfffdf5, 0xeeeeee];
const PASTELES = [0xf6c1c9, 0xbfe0f5, 0xfff0a8, 0xc8e8c1, 0xe5c8f0, 0xf9d5b0, 0xa8d8d0];
const FUERTES = [0x3a6ea5, 0xd9534f, 0x2e8b57, 0x1f2f5a, 0xe07b39];
const PIELES = [0xf1c8a5, 0xe0ac82, 0xc68863, 0x8d5a3b, 0x5c3a28, 0xffdbb8];
const SOMBREROS = [0xf3e6b8, 0xffffff, 0x2b4a7a, 0xd94f4f, 0xd8c690];

function crearPublico(scene) {
  const px = [], py = [], pz = [], yaw = [], ropa = [], piel = [], sombrero = [];
  const agregar = (x, y, z, rot) => {
    if (rnd() < 0.08) return;                    // asiento vacio
    px.push(x); py.push(y); pz.push(z); yaw.push(rot);
    const r = rnd();
    ropa.push(r < 0.40 ? elegir(BLANCOS) : r < 0.78 ? elegir(PASTELES) : elegir(FUERTES));
    piel.push(elegir(PIELES));
    sombrero.push(rnd() < 0.13 ? elegir(SOMBREROS) : 0);
  };
  const PASO = 0.55;
  for (let i = 0; i < FILAS; i++) {
    const top = ALZADA * (i + 1) + 0.05, fr = X_FRENTE + PROF * i, c = fr + 0.4;
    for (const s of [-1, 1]) {
      for (let z = -zNorteExt(i) + 0.35; z < zSurExt(i) - 0.3; z += PASO) agregar(s * c, top, z + (rnd() - 0.5) * 0.06, Math.PI / 2);
    }
    const zn = -(Z_NORTE + PROF * i) - 0.4, zs = Z_SUR + PROF * i + 0.4;
    for (let x = -fr + 0.35; x < fr - 0.3; x += PASO) {
      agregar(x + (rnd() - 0.5) * 0.06, top, zn, 0);
      agregar(x + (rnd() - 0.5) * 0.06, top, zs, 0);
    }
  }
  const N = px.length;

  const geoCuerpo = new THREE.BoxGeometry(0.42, 0.6, 0.3);
  geoCuerpo.translate(0, 0.3, 0);
  const geoCabeza = new THREE.IcosahedronGeometry(0.12, 0);
  const material = new THREE.MeshStandardMaterial({ color: 0xffffff, flatShading: true, roughness: 0.9 });
  const cuerpos = new THREE.InstancedMesh(geoCuerpo, material, N);
  const cabezas = new THREE.InstancedMesh(geoCabeza, material, N);
  for (const m of [cuerpos, cabezas]) {
    m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    m.castShadow = false;
    m.receiveShadow = false;
    m.frustumCulled = false;      // las instancias se mueven un poco; la esfera inicial no las cubriria
  }
  const col = new THREE.Color();
  const hsx = new Float32Array(N), hsy = new Float32Array(N), hdy = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    cuerpos.setColorAt(i, col.setHex(ropa[i]));
    const hat = sombrero[i] !== 0;
    cabezas.setColorAt(i, col.setHex(hat ? sombrero[i] : piel[i]));
    hsx[i] = hat ? 1.5 : 1; hsy[i] = hat ? 0.55 : 1; hdy[i] = hat ? 0.05 : 0;
  }
  cuerpos.instanceColor.needsUpdate = cabezas.instanceColor.needsUpdate = true;
  const cs = new Float32Array(N), sn = new Float32Array(N);
  const fase = new Float32Array(N), umbral = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    cs[i] = Math.cos(yaw[i]); sn[i] = Math.sin(yaw[i]);
    fase[i] = rnd() * 6.2832; umbral[i] = rnd();
  }

  const aM = cuerpos.instanceMatrix.array, aH = cabezas.instanceMatrix.array;
  // Matriz con giro en Y, escala (sx,sy,sz) y posicion; escrita directo en el buffer.
  const fijar = (arr, i, c, s, sx, sy, sz, x, y, z) => {
    const o = i * 16;
    arr[o] = c * sx; arr[o + 1] = 0; arr[o + 2] = -s * sx; arr[o + 3] = 0;
    arr[o + 4] = 0; arr[o + 5] = sy; arr[o + 6] = 0; arr[o + 7] = 0;
    arr[o + 8] = s * sz; arr[o + 9] = 0; arr[o + 10] = c * sz; arr[o + 11] = 0;
    arr[o + 12] = x; arr[o + 13] = y; arr[o + 14] = z; arr[o + 15] = 1;
  };

  let festT = 0, festI = 0, activo = false, cuadro = 0;
  const DURACION = 2.5;
  const poner = (i, env, t) => {
    const f = fase[i];
    const parado = env > 0 && umbral[i] < festI ? env : 0;
    let sy = 1, dy = 0.006 * Math.sin(t * 1.3 + f);
    const dx = 0.01 * Math.sin(t * 0.9 + f);
    if (parado > 0) {
      sy += 0.55 * parado;
      dy += parado * 0.22 * Math.abs(Math.sin(t * 9 + f));
    } else if (env > 0) {
      dy += env * 0.03 * Math.abs(Math.sin(t * 7 + f));   // los que quedan sentados aplauden
    }
    const x = px[i] + dx, y = py[i] + dy, z = pz[i];
    fijar(aM, i, cs[i], sn[i], 1, sy, 1, x, y, z);
    fijar(aH, i, cs[i], sn[i], hsx[i], hsy[i], hsx[i], x, y + 0.6 * sy + 0.17 + hdy[i], z);
  };
  const todo = (env, t) => { for (let i = 0; i < N; i++) poner(i, env, t); };
  const marcar = () => { cuerpos.instanceMatrix.needsUpdate = cabezas.instanceMatrix.needsUpdate = true; };

  todo(0, 0);
  marcar();
  scene.add(cuerpos, cabezas);

  return {
    cantidad: N,
    actualizar(dt, t) {
      if (festT > 0) {
        festT = Math.max(0, festT - dt);
        // sube rapido al principio y baja suave al final
        const env = Math.min(1, (DURACION - festT) / 0.15, festT / 0.9);
        todo(Math.max(env, 0), t);
        activo = true;
        marcar();
      } else if (activo) {
        todo(0, t);
        activo = false;
        marcar();
      } else {
        // reposo: balanceo minimo, 1/8 del publico por cuadro
        for (let i = cuadro & 7; i < N; i += 8) poner(i, 0, t);
        marcar();
      }
      cuadro++;
    },
    festejar(intensidad) {
      const k = Math.min(1, Math.max(0, intensidad));
      if (k <= 0) return;
      festI = festT > 0 ? Math.max(festI, k) : k;
      festT = DURACION;
    },
  };
}

// ---------------------------------------------------------------- API
export function crearEstadio(scene) {
  crearLuces(scene);
  crearCesped(scene);
  crearLineas(scene);
  crearRed(scene);
  crearMuros(scene);
  crearTribunas(scene);
  crearTecho(scene);
  crearMarcador(scene);
  crearUtileria(scene);
  const publico = crearPublico(scene);
  return {
    actualizar: (dt, t) => publico.actualizar(dt, t),
    festejar: (intensidad) => publico.festejar(intensidad),
    publico: publico.cantidad,
  };
}
