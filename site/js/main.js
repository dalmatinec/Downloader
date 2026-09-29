(() => {
  const $ = (s) => document.querySelector(s);
  const isTouch = matchMedia('(hover: none)').matches;

  /* ---------- Небо: лепестки, сердечки и летучие мыши ---------- */
  const sky = $('#sky');
  const ctx = sky.getContext('2d');
  let W, H, dpr;
  const heartPath = new Path2D('M16 29 13.7 26.9C5.4 19.4 0 14.5 0 8.5 0 3.6 3.8 0 8.8 0c2.8 0 5.5 1.3 7.2 3.4C17.7 1.3 20.4 0 23.2 0 28.2 0 32 3.6 32 8.5c0 6-5.4 10.9-13.7 18.4z');
  const batPath = new Path2D('M50 14 L47 6 L45 16 C38 6 18 2 0 10 C8 14 10 20 8 26 C16 22 22 24 24 30 C30 26 38 26 42 32 L50 40 L58 32 C62 26 70 26 76 30 C78 24 84 22 92 26 C90 20 92 14 100 10 C82 2 62 6 55 16 L53 6 Z');

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = innerWidth; H = innerHeight;
    sky.width = W * dpr; sky.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize();
  addEventListener('resize', resize);

  const rand = (a, b) => a + Math.random() * (b - a);
  const count = W < 600 ? 22 : 40;
  const flakes = Array.from({ length: count }, () => newFlake(true));

  function newFlake(anywhere) {
    return {
      x: rand(0, W),
      y: anywhere ? rand(0, H) : -30,
      size: rand(6, 16),
      speed: rand(0.3, 1),
      sway: rand(0.5, 1.5),
      phase: rand(0, Math.PI * 2),
      rot: rand(0, Math.PI * 2),
      spin: rand(-0.02, 0.02),
      heart: Math.random() < 0.4,
      alpha: rand(0.3, 0.8),
    };
  }

  let bats = [];
  function spawnBat() {
    const fromLeft = Math.random() < 0.5;
    bats.push({
      x: fromLeft ? -60 : W + 60,
      y: rand(H * 0.1, H * 0.5),
      vx: (fromLeft ? 1 : -1) * rand(1.5, 2.5),
      size: rand(24, 40),
      t: 0,
    });
    setTimeout(spawnBat, rand(7000, 14000));
  }
  setTimeout(spawnBat, 3000);

  function draw(time) {
    ctx.clearRect(0, 0, W, H);
    for (const f of flakes) {
      f.y += f.speed;
      f.x += Math.sin(time / 1000 * f.sway + f.phase) * 0.4;
      f.rot += f.spin;
      if (f.y > H + 30) Object.assign(f, newFlake(false));
      ctx.save();
      ctx.translate(f.x, f.y);
      ctx.rotate(f.rot);
      ctx.globalAlpha = f.alpha;
      if (f.heart) {
        const s = f.size / 32;
        ctx.scale(s, s);
        ctx.translate(-16, -14);
        ctx.fillStyle = '#ff2a2a';
        ctx.fill(heartPath);
      } else {
        const g = ctx.createLinearGradient(-f.size, 0, f.size, 0);
        g.addColorStop(0, '#8a0000');
        g.addColorStop(1, '#e01515');
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.ellipse(0, 0, f.size, f.size * 0.55, 0, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }

    bats = bats.filter((b) => b.x > -100 && b.x < W + 100);
    for (const b of bats) {
      b.t += 0.25;
      b.x += b.vx;
      b.y += Math.sin(b.t / 3) * 0.8;
      const s = b.size / 100;
      ctx.save();
      ctx.translate(b.x, b.y);
      ctx.scale(s * (b.vx > 0 ? 1 : -1), s * (0.55 + Math.abs(Math.sin(b.t)) * 0.6));
      ctx.translate(-50, -20);
      ctx.globalAlpha = 0.85;
      ctx.fillStyle = '#000';
      ctx.shadowColor = 'rgba(255,0,0,.6)';
      ctx.shadowBlur = 8;
      ctx.fill(batPath);
      ctx.restore();
    }
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);

  /* ---------- Заставка с конвертом ---------- */
  const envelope = $('#envelope');
  let opened = false;
  envelope.addEventListener('click', () => {
    if (opened) return;
    opened = true;
    envelope.classList.add('open');
    $('#intro').classList.add('opening');
    startAudio();
    setTimeout(() => {
      $('#intro').classList.add('hidden');
      playTrailer();
    }, 2800);
  });

  /* ---------- Трейлер ---------- */
  const trailer = $('#trailer');
  const trailerLine = $('#trailerLine');
  const timers = [];
  let trailerDone = false;

  function playTrailer() {
    trailer.classList.add('on');
    let t = 900;
    TRAILER.forEach((line) => {
      timers.push(setTimeout(() => {
        trailerLine.textContent = line;
        trailerLine.classList.remove('show');
        void trailerLine.offsetWidth;
        trailerLine.classList.add('show');
      }, t));
      t += 2700;
    });
    timers.push(setTimeout(() => {
      trailerLine.classList.remove('show');
      $('#trailerFlash').classList.add('go');
      $('#trailerFinal').classList.add('show');
    }, t));
    timers.push(setTimeout(endTrailer, t + 4200));
  }

  function endTrailer() {
    if (trailerDone) return;
    trailerDone = true;
    timers.forEach(clearTimeout);
    trailer.classList.remove('on');
    $('#main').classList.add('show');
    document.body.classList.remove('locked');
  }
  $('#trailerSkip').addEventListener('click', endTrailer);

  /* ---------- Появление секций при скролле ---------- */
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.15 });
  document.querySelectorAll('.reveal').forEach((el) => io.observe(el));

  /* ---------- Сердечки за курсором или пальцем ---------- */
  const hearts = ['❤', '♥', '❣', '💕'];
  let lastTrail = 0;
  function trail(x, y) {
    const now = performance.now();
    if (now - lastTrail < 50) return;
    lastTrail = now;
    const el = document.createElement('span');
    el.className = 'trail';
    el.textContent = hearts[Math.floor(Math.random() * hearts.length)];
    el.style.left = x - 8 + 'px';
    el.style.top = y - 10 + 'px';
    el.style.fontSize = rand(12, 20) + 'px';
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 1000);
  }
  if (!isTouch) addEventListener('mousemove', (e) => trail(e.clientX, e.clientY));
  addEventListener('touchmove', (e) => trail(e.touches[0].clientX, e.touches[0].clientY), { passive: true });

  /* ---------- Взрыв сердечек по тройному тапу на аватарку ---------- */
  function burst(x, y, n = 30) {
    for (let i = 0; i < n; i++) {
      const el = document.createElement('span');
      el.className = 'burst';
      el.textContent = hearts[i % hearts.length];
      el.style.left = x + 'px';
      el.style.top = y + 'px';
      el.style.fontSize = rand(14, 32) + 'px';
      document.body.appendChild(el);
      const a = rand(0, Math.PI * 2);
      const d = rand(80, 260);
      requestAnimationFrame(() => {
        el.style.transform = `translate(${Math.cos(a) * d}px, ${Math.sin(a) * d}px) rotate(${rand(-60, 60)}deg)`;
        el.style.opacity = '0';
      });
      setTimeout(() => el.remove(), 1300);
    }
  }
  let taps = [];
  $('#avatar').addEventListener('click', (e) => {
    const now = Date.now();
    taps = taps.filter((t) => now - t < 700);
    taps.push(now);
    if (taps.length >= 3) {
      taps = [];
      burst(e.clientX, e.clientY, 40);
    }
  });

  /* ---------- Я тебя люблю на разных языках ---------- */
  const langEl = $('#loveLang');
  let li = 0;
  setInterval(() => {
    langEl.classList.add('out');
    setTimeout(() => {
      li = (li + 1) % LOVE_LANGS.length;
      langEl.textContent = LOVE_LANGS[li];
      langEl.classList.remove('out');
    }, 500);
  }, 2500);

  /* ---------- Love is карточки ---------- */
  const cardsEl = $('#cards');
  CARDS.forEach((c, i) => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="card-inner">
        <div class="card-face card-front">
          <span class="li-head">Love is...</span>
          <span class="li-icon">${c.icon}</span>
          <span class="li-num">№ ${i + 1}</span>
        </div>
        <div class="card-face card-back">
          <span class="li-head">Love is...</span>
          <p>${c.text}</p>
          <span class="li-heart">❤</span>
        </div>
      </div>`;
    card.addEventListener('click', (e) => {
      card.classList.toggle('flipped');
      if (card.classList.contains('flipped')) burst(e.clientX, e.clientY, 8);
    });
    cardsEl.appendChild(card);
  });

  /* ---------- Письмо печатается по буквам ---------- */
  const letterEl = $('#letterText');
  const letterChars = Array.from(LETTER);
  let typed = false;
  const letterIo = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !typed) {
      typed = true;
      let i = 0;
      (function type() {
        if (i >= letterChars.length) return;
        const ch = letterChars[i++];
        letterEl.textContent += ch;
        const pause = ch === '\n' ? 350 : /[.,!?]/.test(ch) ? 220 : rand(25, 60);
        setTimeout(type, pause);
      })();
    }
  }, { threshold: 0.4 });
  letterIo.observe($('.letter'));

  /* ---------- Стиралка ---------- */
  $('#scratchMsg').textContent = SCRATCH;
  const cover = $('#scratchCover');
  const sctx = cover.getContext('2d');
  let scratched = false;

  function paintCover() {
    const w = cover.clientWidth, h = cover.clientHeight;
    cover.width = w * dpr; cover.height = h * dpr;
    sctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const g = sctx.createLinearGradient(0, 0, w, h);
    g.addColorStop(0, '#7a0000');
    g.addColorStop(0.5, '#c21414');
    g.addColorStop(1, '#5c0000');
    sctx.fillStyle = g;
    sctx.fillRect(0, 0, w, h);
    sctx.fillStyle = 'rgba(255,255,255,.08)';
    for (let i = 0; i < 18; i++) {
      sctx.save();
      sctx.translate(rand(0, w), rand(0, h));
      sctx.rotate(rand(-0.5, 0.5));
      sctx.scale(0.5, 0.5);
      sctx.fill(heartPath);
      sctx.restore();
    }
    sctx.fillStyle = 'rgba(255,255,255,.9)';
    sctx.font = '600 16px Montserrat, sans-serif';
    sctx.textAlign = 'center';
    sctx.fillText('сотри меня ✨', w / 2, h / 2 + 6);
  }
  // Ждём шрифты, чтобы надпись на покрытии была нужным шрифтом
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(paintCover);

  let drawing = false, last = null;
  function scratchAt(e) {
    const r = cover.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    sctx.globalCompositeOperation = 'destination-out';
    sctx.lineWidth = 42;
    sctx.lineCap = 'round';
    sctx.beginPath();
    sctx.moveTo(last ? last.x : x, last ? last.y : y);
    sctx.lineTo(x, y);
    sctx.stroke();
    sctx.globalCompositeOperation = 'source-over';
    last = { x, y };
  }
  function clearedShare() {
    const data = sctx.getImageData(0, 0, cover.width, cover.height).data;
    let clear = 0, total = 0;
    for (let i = 3; i < data.length; i += 64) { total++; if (data[i] === 0) clear++; }
    return clear / total;
  }
  cover.addEventListener('pointerdown', (e) => { drawing = true; last = null; cover.setPointerCapture(e.pointerId); scratchAt(e); });
  cover.addEventListener('pointermove', (e) => { if (drawing) scratchAt(e); });
  const stop = (e) => {
    if (!drawing) return;
    drawing = false;
    if (!scratched && clearedShare() > 0.45) {
      scratched = true;
      cover.classList.add('done');
      const r = cover.getBoundingClientRect();
      burst(r.left + r.width / 2, r.top + r.height / 2, 36);
    }
  };
  cover.addEventListener('pointerup', stop);
  cover.addEventListener('pointercancel', stop);

  /* ---------- Кнопка ответить ---------- */
  const replyText = encodeURIComponent(REPLY.text);
  $('#replyBtn').href = REPLY.username
    ? `https://t.me/${REPLY.username.replace('@', '')}?text=${replyText}`
    : `https://t.me/share/url?url=${encodeURIComponent(location.origin)}&text=${replyText}`;

  /* ---------- Бэт-сигнал ---------- */
  const signal = $('#batsignal');
  $('#signalBtn').addEventListener('click', () => signal.classList.add('on'));
  signal.addEventListener('click', () => signal.classList.remove('on'));

  /* ---------- Плеер ---------- */
  const audio = $('#audio');
  const playBtn = $('#playBtn');
  const vinyl = $('#vinyl');
  const tonearm = $('#tonearm');
  const errorEl = $('#playerError');
  const listEl = $('#playlist');
  let current = 0;
  let actx, analyser, freq;

  PLAYLIST.forEach((t, i) => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="num">${i + 1}</span><span><div class="pl-title">${t.title}</div><div class="pl-artist">${t.artist}</div></span>`;
    li.addEventListener('click', () => { load(i); play(); });
    listEl.appendChild(li);
  });

  function load(i) {
    current = (i + PLAYLIST.length) % PLAYLIST.length;
    const t = PLAYLIST[current];
    audio.src = t.src;
    $('#trackTitle').textContent = t.title;
    $('#trackArtist').textContent = t.artist;
    errorEl.textContent = '';
    listEl.querySelectorAll('li').forEach((el, k) => el.classList.toggle('active', k === current));
  }

  function setupAnalyser() {
    if (actx) return;
    try {
      actx = new (window.AudioContext || window.webkitAudioContext)();
      const src = actx.createMediaElementSource(audio);
      analyser = actx.createAnalyser();
      analyser.fftSize = 64;
      freq = new Uint8Array(analyser.frequencyBinCount);
      src.connect(analyser);
      analyser.connect(actx.destination);
    } catch (e) { actx = null; }
  }

  function play() {
    setupAnalyser();
    if (actx && actx.state === 'suspended') actx.resume();
    audio.play().catch(() => {});
  }
  function pause() { audio.pause(); }

  function startAudio() {
    if (!PLAYLIST.length) return;
    play();
  }

  function setPlaying(on) {
    playBtn.classList.toggle('playing', on);
    vinyl.classList.toggle('playing', on);
    tonearm.classList.toggle('on', on);
  }
  audio.addEventListener('play', () => setPlaying(true));
  audio.addEventListener('pause', () => setPlaying(false));
  audio.addEventListener('ended', () => { load(current + 1); play(); });
  audio.addEventListener('error', () => {
    setPlaying(false);
    errorEl.textContent = `Не получилось включить ${PLAYLIST[current].src}`;
  });

  playBtn.addEventListener('click', () => (audio.paused ? play() : pause()));
  $('#nextBtn').addEventListener('click', () => { load(current + 1); play(); });
  $('#prevBtn').addEventListener('click', () => {
    if (audio.currentTime > 3) audio.currentTime = 0;
    else { load(current - 1); play(); }
  });

  const fmt = (s) => {
    if (!isFinite(s)) return '0:00';
    const m = Math.floor(s / 60);
    return m + ':' + String(Math.floor(s % 60)).padStart(2, '0');
  };
  audio.addEventListener('timeupdate', () => {
    const p = audio.duration ? audio.currentTime / audio.duration : 0;
    $('#progressFill').style.width = p * 100 + '%';
    $('#curTime').textContent = fmt(audio.currentTime);
  });
  audio.addEventListener('loadedmetadata', () => { $('#durTime').textContent = fmt(audio.duration); });

  const progress = $('#progress');
  function seek(clientX) {
    const r = progress.getBoundingClientRect();
    if (audio.duration) audio.currentTime = Math.min(Math.max((clientX - r.left) / r.width, 0), 1) * audio.duration;
  }
  progress.addEventListener('click', (e) => seek(e.clientX));
  progress.addEventListener('touchmove', (e) => seek(e.touches[0].clientX), { passive: true });

  const vol = $('#volume');
  audio.volume = vol.value;
  vol.addEventListener('input', () => { audio.volume = vol.value; });

  // Визуализатор
  const viz = $('#visualizer');
  const vctx = viz.getContext('2d');
  function drawViz() {
    const w = viz.clientWidth, h = viz.clientHeight;
    if (viz.width !== w * dpr) { viz.width = w * dpr; viz.height = h * dpr; }
    vctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    vctx.clearRect(0, 0, w, h);
    const bars = 28;
    const gap = 3;
    const bw = (w - gap * (bars - 1)) / bars;
    if (analyser && !audio.paused) analyser.getByteFrequencyData(freq);
    for (let i = 0; i < bars; i++) {
      let v;
      if (analyser && !audio.paused) v = freq[Math.floor(i * freq.length / bars)] / 255;
      else v = 0.06 + Math.sin(performance.now() / 600 + i / 2) * 0.03;
      const bh = Math.max(3, v * h);
      const g = vctx.createLinearGradient(0, h, 0, h - bh);
      g.addColorStop(0, '#5c0000');
      g.addColorStop(1, '#ff2a2a');
      vctx.fillStyle = g;
      vctx.beginPath();
      vctx.roundRect ? vctx.roundRect(i * (bw + gap), h - bh, bw, bh, 3) : vctx.rect(i * (bw + gap), h - bh, bw, bh);
      vctx.fill();
    }
    requestAnimationFrame(drawViz);
  }
  requestAnimationFrame(drawViz);

  if (PLAYLIST.length) load(0);
})();
