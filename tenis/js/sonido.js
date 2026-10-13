// Módulo de efectos de sonido con WebAudio
// Genera todos los efectos sin archivos de audio externos

export const sonido = {
  // Estado privado
  _ctx: null,
  _master: null,
  _noiseBuffer: null,
  _murmullo: {
    fuente: null,
    ganancia: null,
    lfo: null,
    filtro: null,
    lfoGain: null,
  },
  _osciladores: [], // para limpiar después

  // Crea el AudioContext (idempotente, se inicia tras un gesto del usuario)
  iniciar() {
    if (this._ctx) return; // ya iniciado

    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      this._ctx = ctx;

      // Nodo maestro con volumen ~0.6
      this._master = ctx.createGain();
      this._master.gain.value = 0.6;
      this._master.connect(ctx.destination);

      // Generar buffer de ruido blanco (~2s) reutilizable
      const sampleRate = ctx.sampleRate;
      const bufferLength = sampleRate * 2;
      const buffer = ctx.createBuffer(1, bufferLength, sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferLength; i++) {
        data[i] = Math.random() * 2 - 1;
      }
      this._noiseBuffer = buffer;

      // Iniciar murmullo de fondo
      this._iniciarMurmullo(0.15);
    } catch (e) {
      // WebAudio no disponible o error
    }
  },

  // Genera un buffer de ruido blanco
  _generarRuido(duracion) {
    if (!this._ctx) return null;
    const sampleRate = this._ctx.sampleRate;
    const bufferLength = Math.ceil(sampleRate * duracion);
    const buffer = this._ctx.createBuffer(1, bufferLength, sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferLength; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    return buffer;
  },

  // Reproductor de ruido filtrado genérico (helper)
  _reproducirRuido(duracion, filterConfig, gainEnv) {
    if (!this._ctx) return;

    const ctx = this._ctx;
    const now = ctx.currentTime;

    // Crear source con el buffer de ruido
    const source = ctx.createBufferSource();
    source.buffer = this._noiseBuffer;
    source.loop = false;

    // Filtro
    const filter = ctx.createBiquadFilter();
    filter.type = filterConfig.type; // 'lowpass', 'bandpass', 'highpass'
    filter.frequency.value = filterConfig.freq;
    filter.Q.value = filterConfig.q || 1;

    // Ganancia con envolvente
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(gainEnv.start, now);
    if (gainEnv.attack !== undefined) {
      gain.gain.linearRampToValueAtTime(gainEnv.peak, now + gainEnv.attack);
      gain.gain.linearRampToValueAtTime(gainEnv.end, now + gainEnv.attack + gainEnv.release);
    } else {
      gain.gain.linearRampToValueAtTime(gainEnv.end, now + duracion);
    }

    source.connect(filter);
    filter.connect(gain);
    gain.connect(this._master);

    source.start(now);
    source.stop(now + duracion);

    // Guardar referencia para limpiar (aunque stop ya detiene)
    this._osciladores.push({ fuente: source, fin: now + duracion });
  },

  // Raquetazo (golpe)
  golpe(fuerza) {
    if (!this._ctx) return;

    fuerza = Math.max(0, Math.min(1, fuerza || 0)); // clamp 0..1
    const ctx = this._ctx;
    const now = ctx.currentTime;

    // Pop corto de ruido filtrado + cuerpo tonal
    const duracion = 0.15 + fuerza * 0.1;

    // Ruido percusivo en altos-medios
    this._reproducirRuido(duracion * 0.7, {
      type: 'highpass',
      freq: 1500 + fuerza * 2000,
      q: 2,
    }, {
      start: 0.15 * fuerza,
      peak: 0.15 * (1 + fuerza),
      attack: 0.01,
      release: 0.08,
      end: 0.01,
    });

    // Cuerpo tonal: oscilador en 200-350 Hz según fuerza
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(180 + fuerza * 170, now);
    osc.frequency.linearRampToValueAtTime(120, now + duracion * 0.6);

    const oscGain = ctx.createGain();
    oscGain.gain.setValueAtTime(0.1 * fuerza, now);
    oscGain.gain.linearRampToValueAtTime(0, now + duracion);

    osc.connect(oscGain);
    oscGain.connect(this._master);
    osc.start(now);
    osc.stop(now + duracion);

    this._osciladores.push({ fuente: osc, fin: now + duracion });
  },

  // Golpe suave (dropshot/volea)
  toque() {
    if (!this._ctx) return;

    const ctx = this._ctx;
    const now = ctx.currentTime;
    const duracion = 0.08;

    // Ruido apagado y corto en graves-medios
    this._reproducirRuido(duracion, {
      type: 'lowpass',
      freq: 800,
      q: 0.8,
    }, {
      start: 0.08,
      peak: 0.1,
      attack: 0.005,
      release: 0.05,
      end: 0,
    });

    // Cuerpo tonal suave en ~150 Hz
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = 150;

    const oscGain = ctx.createGain();
    oscGain.gain.setValueAtTime(0.05, now);
    oscGain.gain.linearRampToValueAtTime(0, now + duracion);

    osc.connect(oscGain);
    oscGain.connect(this._master);
    osc.start(now);
    osc.stop(now + duracion);

    this._osciladores.push({ fuente: osc, fin: now + duracion });
  },

  // Pelota contra el césped
  pique(fuerza) {
    if (!this._ctx) return;

    fuerza = Math.max(0, Math.min(1, fuerza || 0)); // clamp 0..1
    const ctx = this._ctx;
    const now = ctx.currentTime;
    const duracion = 0.12;

    // Tup sordo y grave: ruido filtrado en graves
    this._reproducirRuido(duracion, {
      type: 'lowpass',
      freq: 250 + fuerza * 150,
      q: 1,
    }, {
      start: 0.12 * (1 - fuerza * 0.3),
      peak: 0.12 * (1 + fuerza * 0.4),
      attack: 0.008,
      release: 0.08,
      end: 0,
    });

    // Cuerpo tonal grave en ~120 Hz
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(120, now);
    osc.frequency.linearRampToValueAtTime(80, now + duracion * 0.7);

    const oscGain = ctx.createGain();
    oscGain.gain.setValueAtTime(0.08 * fuerza, now);
    oscGain.gain.linearRampToValueAtTime(0, now + duracion);

    osc.connect(oscGain);
    oscGain.connect(this._master);
    osc.start(now);
    osc.stop(now + duracion);

    this._osciladores.push({ fuente: osc, fin: now + duracion });
  },

  // Pelota en la red
  red() {
    if (!this._ctx) return;

    const ctx = this._ctx;
    const now = ctx.currentTime;
    const duracion = 0.2;

    // Roce apagado de ruido en graves
    this._reproducirRuido(duracion, {
      type: 'lowpass',
      freq: 400,
      q: 1.5,
    }, {
      start: 0.06,
      peak: 0.1,
      attack: 0.03,
      release: 0.14,
      end: 0,
    });
  },

  // Aplauso del público
  aplauso(intensidad) {
    if (!this._ctx) return;

    intensidad = Math.max(0, Math.min(1, intensidad || 0)); // clamp 0..1
    const ctx = this._ctx;
    const now = ctx.currentTime;

    // Duración: 2-4 segundos según intensidad
    const duracion = 2 + intensidad * 2;

    // Ráfagas de ruido pasabanda simulando palmadas
    const numRafagas = Math.ceil(4 + intensidad * 8);
    const intervaloRafaga = duracion / numRafagas;

    for (let i = 0; i < numRafagas; i++) {
      const tiempoRafaga = now + i * intervaloRafaga;
      const duracionRafaga = intervaloRafaga * 0.6;

      // Ruido pasabanda para palmada
      const source = ctx.createBufferSource();
      source.buffer = this._noiseBuffer;
      source.loop = false;

      const filter = ctx.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.value = 2000 + Math.random() * 2000; // 2-4 kHz
      filter.Q.value = 2;

      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0, tiempoRafaga);
      gain.gain.linearRampToValueAtTime(0.08 * intensidad, tiempoRafaga + 0.01);
      gain.gain.linearRampToValueAtTime(0, tiempoRafaga + duracionRafaga);

      source.connect(filter);
      filter.connect(gain);
      gain.connect(this._master);

      source.start(tiempoRafaga);
      source.stop(tiempoRafaga + duracionRafaga);

      this._osciladores.push({ fuente: source, fin: tiempoRafaga + duracionRafaga });
    }

    // Ovación suave si intensidad > 0.7
    if (intensidad > 0.7) {
      const duracionOvacion = 0.8;
      this._reproducirRuido(duracionOvacion, {
        type: 'bandpass',
        freq: 1500,
        q: 1,
      }, {
        start: 0.03,
        peak: 0.05,
        attack: 0.1,
        release: 0.6,
        end: 0,
      });
    }
  },

  // Uuuh del público (pelota afuera por poco)
  ooh() {
    if (!this._ctx) return;

    const ctx = this._ctx;
    const now = ctx.currentTime;
    const duracion = 0.8;

    // Ruido pasabanda con formante que baja
    const source = ctx.createBufferSource();
    source.buffer = this._noiseBuffer;
    source.loop = false;

    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(800, now);
    filter.frequency.linearRampToValueAtTime(400, now + duracion);
    filter.Q.value = 2;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.06, now);
    gain.gain.linearRampToValueAtTime(0, now + duracion);

    source.connect(filter);
    filter.connect(gain);
    gain.connect(this._master);

    source.start(now);
    source.stop(now + duracion);

    this._osciladores.push({ fuente: source, fin: now + duracion });
  },

  // Inicia el murmullo de fondo
  _iniciarMurmullo(nivel) {
    if (!this._ctx) return;

    const ctx = this._ctx;
    const now = ctx.currentTime;

    // Limpiar murmullo anterior si existe
    if (this._murmullo.fuente) {
      try {
        this._murmullo.fuente.stop(now);
      } catch (e) {
        // ya detenida
      }
    }

    // Source de ruido en loop
    const source = ctx.createBufferSource();
    source.buffer = this._noiseBuffer;
    source.loop = true;

    // Filtro pasabanda: 400-900 Hz
    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = 650;
    filter.Q.value = 2;

    // Ganancia del murmullo
    const gain = ctx.createGain();
    gain.gain.value = nivel * 0.15; // nivel se escala a [0, 0.15]

    // LFO lento sobre la ganancia para no ser plano
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.5; // 0.5 Hz

    const lfoGain = ctx.createGain();
    lfoGain.gain.value = nivel * 0.05; // modulación ~5%

    source.connect(filter);
    filter.connect(gain);

    lfo.connect(lfoGain);
    lfoGain.connect(gain.gain);

    gain.connect(this._master);

    source.start(now);
    lfo.start(now);

    this._murmullo = { fuente: source, ganancia: gain, lfo, filtro: filter, lfoGain };
  },

  // Fija el volumen del murmullo de fondo con rampa suave
  murmullo(nivel) {
    if (!this._ctx) return;

    nivel = Math.max(0, Math.min(1, nivel || 0)); // clamp 0..1

    if (!this._murmullo.ganancia) {
      this._iniciarMurmullo(nivel);
      return;
    }

    const ctx = this._ctx;
    const now = ctx.currentTime;
    const rampaDuracion = 0.3;

    this._murmullo.ganancia.gain.linearRampToValueAtTime(nivel * 0.15, now + rampaDuracion);
    this._murmullo.lfoGain.gain.linearRampToValueAtTime(nivel * 0.05, now + rampaDuracion);
  },

  // Mute general
  silenciar(bool) {
    if (!this._ctx || !this._master) return;

    const ctx = this._ctx;
    const now = ctx.currentTime;
    const rampaDuracion = 0.1;

    if (bool) {
      this._master.gain.linearRampToValueAtTime(0, now + rampaDuracion);
    } else {
      this._master.gain.linearRampToValueAtTime(0.6, now + rampaDuracion);
    }
  },
};
