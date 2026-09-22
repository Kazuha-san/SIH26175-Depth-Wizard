import React, { useEffect, useRef } from "react";

/**
 * Full-bleed canvas background: a field of particles that drift slowly
 * on their own (small random-walk acceleration), connect with a line
 * when close to each other, and quietly fade out + respawn elsewhere
 * once their lifetime is up. Not mouse-reactive -- purely ambient. A
 * light separation force keeps them from drifting into a single clump.
 */
const DOT_COLOR = "29, 111, 214"; // blue
const LINE_COLOR = "20, 184, 166"; // teal
const CONNECTION_DIST = 150;
const DENSITY = 28000; // px^2 per particle -- lower is denser
const MAX_SPEED = 0.18;
const SEPARATION_DIST = 46;
const SEPARATION_STRENGTH = 0.004;

const rand = (min, max) => min + Math.random() * (max - min);

const AnimatedBackground = ({ className = "" }) => {
  const canvasRef = useRef(null);
  const particlesRef = useRef([]);
  const rafRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    let width = 0;
    let height = 0;

    const spawn = () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: rand(-MAX_SPEED, MAX_SPEED),
      vy: rand(-MAX_SPEED, MAX_SPEED),
      r: rand(1, 2.6),
      age: 0,
      life: rand(700, 1400), // frames before fading out + respawning
    });

    const initParticles = () => {
      const count = Math.max(28, Math.floor((width * height) / DENSITY));
      particlesRef.current = Array.from({ length: count }, spawn);
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.parentElement.clientWidth;
      height = canvas.parentElement.clientHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      initParticles();
    };

    const lifeAlpha = (p) => {
      const fadeIn = Math.min(1, p.age / 60);
      const fadeOut = Math.min(1, (p.life - p.age) / 60);
      return Math.max(0, Math.min(fadeIn, fadeOut));
    };

    const draw = () => {
      const particles = particlesRef.current;
      ctx.clearRect(0, 0, width, height);

      // gentle separation so particles don't drift into one clump
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < SEPARATION_DIST * SEPARATION_DIST && d2 > 0.01) {
            const d = Math.sqrt(d2);
            const f = (1 - d / SEPARATION_DIST) * SEPARATION_STRENGTH;
            const nx = dx / d;
            const ny = dy / d;
            a.vx += nx * f;
            a.vy += ny * f;
            b.vx -= nx * f;
            b.vy -= ny * f;
          }
        }
      }

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        p.vx += rand(-0.006, 0.006);
        p.vy += rand(-0.006, 0.006);

        const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
        if (speed > MAX_SPEED) {
          p.vx = (p.vx / speed) * MAX_SPEED;
          p.vy = (p.vy / speed) * MAX_SPEED;
        }

        p.x += p.vx;
        p.y += p.vy;
        p.age += 1;

        if (p.x < -10) p.x = width + 10;
        if (p.x > width + 10) p.x = -10;
        if (p.y < -10) p.y = height + 10;
        if (p.y > height + 10) p.y = -10;

        if (p.age >= p.life) {
          particles[i] = spawn();
          continue;
        }

        const alpha = lifeAlpha(p);
        if (alpha <= 0) continue;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${DOT_COLOR}, ${0.55 * alpha})`;
        ctx.fill();
      }

      ctx.lineWidth = 0.8;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i];
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < CONNECTION_DIST * CONNECTION_DIST) {
            const distAlpha = 1 - Math.sqrt(d2) / CONNECTION_DIST;
            const alpha = distAlpha * 0.5 * lifeAlpha(a) * lifeAlpha(b);
            if (alpha <= 0.01) continue;
            ctx.strokeStyle = `rgba(${LINE_COLOR}, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }
    };

    const loop = () => {
      draw();
      rafRef.current = requestAnimationFrame(loop);
    };

    resize();
    window.addEventListener("resize", resize);

    if (prefersReducedMotion) {
      draw();
    } else {
      rafRef.current = requestAnimationFrame(loop);
    }

    return () => {
      window.removeEventListener("resize", resize);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <div className={`pointer-events-none fixed inset-0 z-0 overflow-hidden ${className}`}>
      <canvas ref={canvasRef} className="block" />
    </div>
  );
};

export default AnimatedBackground;
