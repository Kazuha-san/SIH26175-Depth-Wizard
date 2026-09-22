import React, { useEffect, useRef } from "react";

/**
 * Focal animation for the processing screen: a satellite hovers in
 * place above a curved horizon (a big circle's top edge -- reads as a
 * planet surface, not a flat scrolling strip). A grid of "meridian"
 * lines slides along that curve over time, which reads as the surface
 * rotating beneath the satellite. A scan beam drops straight down from
 * the satellite onto the apex of the curve.
 */
const TerrainScanAnimation = () => {
  const canvasRef = useRef(null);
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

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.parentElement.clientWidth;
      height = canvas.parentElement.clientHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const drawSatellite = (cx, cy) => {
      ctx.save();
      ctx.translate(cx, cy);

      const glow = ctx.createRadialGradient(0, 0, 2, 0, 0, 26);
      glow.addColorStop(0, "rgba(58, 160, 232, 0.35)");
      glow.addColorStop(1, "rgba(58, 160, 232, 0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(0, 0, 26, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = "#1d6fd6";
      ctx.fillRect(-22, -4, 12, 8);
      ctx.fillRect(10, -4, 12, 8);
      ctx.strokeStyle = "rgba(15, 41, 66, 0.5)";
      ctx.lineWidth = 0.75;
      for (let i = -20; i <= -6; i += 4) {
        ctx.beginPath();
        ctx.moveTo(i, -4);
        ctx.lineTo(i, 4);
        ctx.stroke();
      }
      for (let i = 12; i <= 20; i += 4) {
        ctx.beginPath();
        ctx.moveTo(i, -4);
        ctx.lineTo(i, 4);
        ctx.stroke();
      }
      ctx.strokeStyle = "#0f2942";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(-10, 0);
      ctx.lineTo(10, 0);
      ctx.stroke();

      ctx.fillStyle = "#0f2942";
      ctx.beginPath();
      ctx.roundRect(-9, -8, 18, 16, 4);
      ctx.fill();
      ctx.fillStyle = "#14b8a6";
      ctx.beginPath();
      ctx.roundRect(-6, -5, 12, 6, 2);
      ctx.fill();

      ctx.strokeStyle = "#0f2942";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(0, -8);
      ctx.lineTo(0, -14);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(0, -14, 2, 0, Math.PI * 2);
      ctx.fillStyle = "#14b8a6";
      ctx.fill();

      ctx.restore();
    };

    const draw = (t) => {
      ctx.clearRect(0, 0, width, height);

      const satX = width * 0.5;
      const bob = Math.sin(t * 0.0022) * 5;
      const satY = height * 0.22 + bob;

      // Big circle: only its top edge is on screen, reading as a
      // planet's curved horizon rather than a flat strip.
      const apexY = height * 0.62;
      const R = width * 0.95;
      const cx = width * 0.5;
      const cy = apexY + R;

      const curveY = (x) => {
        const dx = x - cx;
        const under = R * R - dx * dx;
        if (under < 0) return null;
        return cy - Math.sqrt(under);
      };

      // ---- filled surface ----
      ctx.beginPath();
      ctx.moveTo(0, height);
      for (let x = 0; x <= width; x += 4) {
        const y = curveY(x);
        ctx.lineTo(x, y === null ? height : y);
      }
      ctx.lineTo(width, height);
      ctx.closePath();
      const fillGrad = ctx.createLinearGradient(0, apexY - 40, 0, height);
      fillGrad.addColorStop(0, "rgba(20, 184, 166, 0.18)");
      fillGrad.addColorStop(1, "rgba(29, 111, 214, 0.05)");
      ctx.fillStyle = fillGrad;
      ctx.fill();

      // outline of the horizon
      ctx.beginPath();
      let first = true;
      for (let x = 0; x <= width; x += 4) {
        const y = curveY(x);
        if (y === null) continue;
        if (first) {
          ctx.moveTo(x, y);
          first = false;
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.strokeStyle = "rgba(29, 111, 214, 0.5)";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // ---- rotating "meridian" grid sliding along the curve ----
      // Each tick sits at an angle from the apex; the angle offset grows
      // with time so ticks continuously sweep across, reading as the
      // surface rotating beneath the fixed satellite.
      ctx.save();
      ctx.beginPath();
      first = true;
      for (let x = 0; x <= width; x += 4) {
        const y = curveY(x);
        if (y === null) continue;
        if (first) {
          ctx.moveTo(x, y);
          first = false;
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.lineTo(width, height);
      ctx.lineTo(0, height);
      ctx.closePath();
      ctx.clip();

      const spacing = 0.1; // radians between ticks
      const rotation = (t * 0.00035) % spacing;
      const maxAngle = Math.asin(Math.min(1, (width * 0.62) / R));

      for (let a = -maxAngle; a <= maxAngle; a += spacing) {
        const theta = a + rotation;
        if (Math.abs(theta) > maxAngle) continue;
        const x = cx + R * Math.sin(theta);
        const y = cy - R * Math.cos(theta);
        const centerCloseness = Math.cos(theta); // 1 at apex, less at edges
        const distFromSat = Math.abs(x - satX);
        const scanGlow = Math.max(0, 1 - distFromSat / 150);
        const alpha = 0.08 + centerCloseness * 0.12 + scanGlow * 0.5;

        ctx.strokeStyle = `rgba(20, 184, 166, ${alpha})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      ctx.restore();

      // ---- scan beam from satellite straight down to the apex ----
      const groundHitY = curveY(satX);
      const pulse = 0.5 + Math.sin(t * 0.006) * 0.5;
      const beamGrad = ctx.createLinearGradient(0, satY, 0, groundHitY);
      beamGrad.addColorStop(0, `rgba(20, 184, 166, ${0.28 + pulse * 0.15})`);
      beamGrad.addColorStop(1, "rgba(20, 184, 166, 0)");
      ctx.fillStyle = beamGrad;
      ctx.beginPath();
      ctx.moveTo(satX - 3, satY + 8);
      ctx.lineTo(satX + 3, satY + 8);
      ctx.lineTo(satX + 24, groundHitY);
      ctx.lineTo(satX - 24, groundHitY);
      ctx.closePath();
      ctx.fill();

      ctx.beginPath();
      ctx.ellipse(satX, groundHitY, 18, 4, 0, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(127, 227, 214, ${0.35 + pulse * 0.35})`;
      ctx.fill();

      drawSatellite(satX, satY);
    };

    const loop = (t) => {
      draw(t);
      rafRef.current = requestAnimationFrame(loop);
    };

    resize();
    window.addEventListener("resize", resize);

    if (prefersReducedMotion) {
      draw(0);
    } else {
      rafRef.current = requestAnimationFrame(loop);
    }

    return () => {
      window.removeEventListener("resize", resize);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return <canvas ref={canvasRef} className="block h-full w-full" />;
};

export default TerrainScanAnimation;
