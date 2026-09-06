import { useEffect, useRef } from 'react';

/**
 * Cursor-reactive grid for the login brand panel.
 *
 * Renders a DPR-aware <canvas> that sits behind the panel content and
 * never intercepts pointer or keyboard events (`pointer-events: none`).
 * Pointer tracking is bound to the canvas' parent element (the dark
 * panel), so coordinates stay correct at any panel size or scroll
 * position. All animation state lives in refs and the requestAnimationFrame
 * loop — the component never re-renders after mount.
 *
 * Behaviour:
 *  - idle: a faint emerald grid with a slow ambient "breathing" drift
 *  - hover: nodes near the cursor spring away, intersections brighten,
 *    and a restrained turquoise glow follows the pointer with easing
 *  - leave: everything springs smoothly back to rest
 *  - touch / no-hover devices: a slow automated ripple instead of hover
 *  - prefers-reduced-motion: a static grid, no loop, no pointer tracking
 *  - panel hidden (mobile layout): the loop parks itself until a resize
 *    reports a non-zero box again
 */

const CONFIG = {
  /** px between grid nodes on a normal viewport */
  spacing: 30,
  /** px between grid nodes on small viewports / high-DPR devices */
  spacingCoarse: 42,
  /** viewport width at or below which the coarse spacing is used */
  coarseBelow: 1280,
  /** hard cap on the canvas backing-store scale */
  maxDpr: 1.5,
  /** px radius of the cursor's circular area of influence */
  influenceRadius: 110,
  /** max px a node is pushed away from the cursor */
  pushForce: 18,
  /** spring pull of each node back toward its home position */
  stiffness: 0.085,
  /** per-frame velocity damping (lower = settles faster) */
  damping: 0.78,
  /** interpolation factor toward the true pointer position */
  pointerEase: 0.18,
  /** easing of the overall effect strength (fade in / out) */
  strengthEase: 0.08,
  /** resting alpha of the grid lines */
  lineOpacity: 0.12,
  /** alpha of the lines / dots closest to the cursor */
  lineOpacityHot: 0.5,
  /** heat above which a segment / node is drawn "hot" */
  hotThreshold: 0.05,
  /** px radius of the radial glow under the cursor */
  glowRadius: 140,
  /** peak alpha of the cursor glow */
  glowStrength: 0.16,
  /** px of slow ambient breathing */
  driftAmplitude: 4,
  /** speed of the ambient drift (radians / ms) */
  driftSpeed: 0.00016,
  /** emerald / turquoise line colour (rgb triplet) */
  lineColor: '20, 201, 166',
  /** glow + hot-node colour (rgb triplet) */
  glowColor: '45, 227, 188',
} as const;

interface Node {
  /** home position (grid origin, before drift + push) */
  ox: number;
  oy: number;
  /** current rendered position */
  x: number;
  y: number;
  /** velocity */
  vx: number;
  vy: number;
  /** 0..1 proximity to the cursor this frame */
  heat: number;
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export function InteractiveGrid() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const panel = canvas?.parentElement;
    if (!canvas || !panel) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const hoverQuery = window.matchMedia('(hover: none)');

    let width = 0;
    let height = 0;
    let cols = 0;
    let rows = 0;
    let spacing: number = CONFIG.spacing;
    let nodes: Node[] = [];
    let rafId = 0;
    let startTime = performance.now();

    /** cached radial-glow sprite, redrawn only on resize */
    const glowSprite = document.createElement('canvas');

    // pointer state (all in CSS px, relative to the panel)
    const pointer = { x: 0, y: 0, active: false };
    const smooth = { x: 0, y: 0, strength: 0 };

    const buildGlowSprite = () => {
      const s = CONFIG.glowRadius * 2;
      glowSprite.width = s;
      glowSprite.height = s;
      const g = glowSprite.getContext('2d');
      if (!g) return;
      const grad = g.createRadialGradient(
        CONFIG.glowRadius,
        CONFIG.glowRadius,
        0,
        CONFIG.glowRadius,
        CONFIG.glowRadius,
        CONFIG.glowRadius,
      );
      grad.addColorStop(0, `rgba(${CONFIG.glowColor}, ${CONFIG.glowStrength})`);
      grad.addColorStop(0.5, `rgba(${CONFIG.glowColor}, ${CONFIG.glowStrength * 0.35})`);
      grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      g.fillStyle = grad;
      g.fillRect(0, 0, s, s);
    };

    const buildGrid = () => {
      spacing =
        width <= CONFIG.coarseBelow ? CONFIG.spacingCoarse : CONFIG.spacing;

      cols = Math.ceil(width / spacing) + 2;
      rows = Math.ceil(height / spacing) + 2;

      nodes = [];
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const ox = (c - 1) * spacing;
          const oy = (r - 1) * spacing;
          nodes.push({ ox, oy, x: ox, y: oy, vx: 0, vy: 0, heat: 0 });
        }
      }
    };

    const resize = () => {
      const rect = panel.getBoundingClientRect();
      width = Math.round(rect.width);
      height = Math.round(rect.height);
      const dpr = Math.min(window.devicePixelRatio || 1, CONFIG.maxDpr);

      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      if (width > 0 && height > 0) {
        buildGrid();
        smooth.x = width / 2;
        smooth.y = height / 2;
        if (motionQuery.matches) drawStatic();
      }
    };

    /** Static, elegant grid for reduced-motion users. */
    const drawStatic = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.lineWidth = 1;
      ctx.strokeStyle = `rgba(${CONFIG.lineColor}, ${CONFIG.lineOpacity})`;
      ctx.beginPath();
      for (let c = 0; c < cols; c++) {
        const x = (c - 1) * spacing;
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
      }
      for (let r = 0; r < rows; r++) {
        const y = (r - 1) * spacing;
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
      }
      ctx.stroke();
    };

    const frame = (now: number) => {
      rafId = requestAnimationFrame(frame);
      if (width === 0 || height === 0) return;

      const t = now - startTime;
      const auto = hoverQuery.matches;

      const wantStrength = auto ? 0.5 : pointer.active ? 1 : 0;
      smooth.strength = lerp(smooth.strength, wantStrength, CONFIG.strengthEase);

      let targetX = pointer.x;
      let targetY = pointer.y;
      if (auto) {
        targetX = width * 0.5 + width * 0.3 * Math.sin(t * 0.00022);
        targetY = height * 0.5 + height * 0.24 * Math.sin(t * 0.00017 + 1.2);
      }
      if (auto || pointer.active) {
        smooth.x = lerp(smooth.x, targetX, auto ? 0.04 : CONFIG.pointerEase);
        smooth.y = lerp(smooth.y, targetY, auto ? 0.04 : CONFIG.pointerEase);
      }

      const sx = smooth.x;
      const sy = smooth.y;
      const strength = smooth.strength;
      const R = CONFIG.influenceRadius;
      const R2 = R * R;

      ctx.clearRect(0, 0, width, height);

      // ── cursor glow (cached sprite — one drawImage)
      if (strength > 0.01) {
        ctx.globalAlpha = strength;
        ctx.drawImage(
          glowSprite,
          sx - CONFIG.glowRadius,
          sy - CONFIG.glowRadius,
          CONFIG.glowRadius * 2,
          CONFIG.glowRadius * 2,
        );
        ctx.globalAlpha = 1;
      }

      // ── integrate nodes: spring toward (drifting home + push-away offset)
      const pushing = strength > 0.01;
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];

        let homeX = n.ox + Math.sin(t * CONFIG.driftSpeed + n.oy * 0.012) * CONFIG.driftAmplitude;
        let homeY = n.oy + Math.cos(t * CONFIG.driftSpeed + n.ox * 0.012) * CONFIG.driftAmplitude;

        n.heat = 0;
        if (pushing) {
          const dx = n.x - sx;
          const dy = n.y - sy;
          const d2 = dx * dx + dy * dy;
          if (d2 < R2) {
            const dist = Math.sqrt(d2);
            const f = 1 - dist / R;
            const push = f * f * CONFIG.pushForce * strength;
            const inv = dist === 0 ? 0 : 1 / dist;
            homeX += dx * inv * push;
            homeY += dy * inv * push;
            n.heat = f * strength;
          }
        }

        n.vx = (n.vx + (homeX - n.x) * CONFIG.stiffness) * CONFIG.damping;
        n.vy = (n.vy + (homeY - n.y) * CONFIG.stiffness) * CONFIG.damping;
        n.x += n.vx;
        n.y += n.vy;
      }

      // ── grid lines: two batched strokes (resting + hot near the cursor)
      const base = new Path2D();
      const hot = new Path2D();
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const n = nodes[r * cols + c];
          if (c < cols - 1) {
            const right = nodes[r * cols + c + 1];
            const p = Math.max(n.heat, right.heat) > CONFIG.hotThreshold ? hot : base;
            p.moveTo(n.x, n.y);
            p.lineTo(right.x, right.y);
          }
          if (r < rows - 1) {
            const below = nodes[(r + 1) * cols + c];
            const p = Math.max(n.heat, below.heat) > CONFIG.hotThreshold ? hot : base;
            p.moveTo(n.x, n.y);
            p.lineTo(below.x, below.y);
          }
        }
      }

      ctx.lineWidth = 1;
      ctx.strokeStyle = `rgba(${CONFIG.lineColor}, ${CONFIG.lineOpacity})`;
      ctx.stroke(base);
      if (strength > 0.01) {
        ctx.strokeStyle = `rgba(${CONFIG.lineColor}, ${CONFIG.lineOpacityHot * strength})`;
        ctx.stroke(hot);

        // ── intersection dots, brightest right under the cursor
        for (let i = 0; i < nodes.length; i++) {
          const n = nodes[i];
          if (n.heat < CONFIG.hotThreshold) continue;
          ctx.fillStyle = `rgba(${CONFIG.glowColor}, ${0.1 + n.heat * 0.5})`;
          ctx.beginPath();
          ctx.arc(n.x, n.y, 1 + n.heat * 1.6, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    };

    // ── pointer tracking on the panel (ignores touch — see hoverQuery)
    const onPointerMove = (e: PointerEvent) => {
      if (e.pointerType === 'touch') return;
      const rect = panel.getBoundingClientRect();
      pointer.x = e.clientX - rect.left;
      pointer.y = e.clientY - rect.top;
      pointer.active = true;
    };
    const onPointerLeave = () => {
      pointer.active = false;
    };

    const start = () => {
      cancelAnimationFrame(rafId);
      startTime = performance.now();
      rafId = requestAnimationFrame(frame);
    };
    const stop = () => cancelAnimationFrame(rafId);

    const applyMotionPreference = () => {
      stop();
      if (motionQuery.matches) {
        panel.removeEventListener('pointermove', onPointerMove);
        panel.removeEventListener('pointerleave', onPointerLeave);
        if (width > 0 && height > 0) drawStatic();
      } else {
        panel.addEventListener('pointermove', onPointerMove);
        panel.addEventListener('pointerleave', onPointerLeave);
        start();
      }
    };

    const ro = new ResizeObserver(() => {
      resize();
      if (!motionQuery.matches && !rafId) start();
    });
    ro.observe(panel);

    buildGlowSprite();
    resize();
    applyMotionPreference();

    const onHoverChange = () => {
      pointer.active = false;
    };
    motionQuery.addEventListener('change', applyMotionPreference);
    hoverQuery.addEventListener('change', onHoverChange);

    return () => {
      stop();
      ro.disconnect();
      panel.removeEventListener('pointermove', onPointerMove);
      panel.removeEventListener('pointerleave', onPointerLeave);
      motionQuery.removeEventListener('change', applyMotionPreference);
      hoverQuery.removeEventListener('change', onHoverChange);
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden="true" className="auth-grid-canvas" />;
}
