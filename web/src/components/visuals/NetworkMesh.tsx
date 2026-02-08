import { useEffect, useRef } from 'react';
import { cn } from '../../utils/cn';

type Node = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  drift: number;
};

const buildNodes = (count: number, width: number, height: number): Node[] => {
  const nodes: Node[] = [];
  for (let i = 0; i < count; i += 1) {
    nodes.push({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      radius: 1.4 + Math.random() * 1.8,
      drift: 40 + Math.random() * 80,
    });
  }
  return nodes;
};

export const NetworkMesh = ({ className }: { className?: string }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const nodesRef = useRef<Node[]>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return undefined;
    }

    const context = canvas.getContext('2d');
    if (!context) {
      return undefined;
    }

    const resize = () => {
      const { clientWidth, clientHeight } = canvas;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.floor(clientWidth * dpr));
      canvas.height = Math.max(1, Math.floor(clientHeight * dpr));
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      const density = Math.max(24, Math.min(70, Math.floor((clientWidth * clientHeight) / 24000)));
      nodesRef.current = buildNodes(density, clientWidth, clientHeight);
    };

    const draw = () => {
      const { clientWidth, clientHeight } = canvas;
      context.clearRect(0, 0, clientWidth, clientHeight);
      context.fillStyle = 'rgba(10, 10, 10, 0.35)';
      context.fillRect(0, 0, clientWidth, clientHeight);

      const nodes = nodesRef.current;
      for (let i = 0; i < nodes.length; i += 1) {
        const node = nodes[i];
        node.x += node.vx;
        node.y += node.vy;

        if (node.x <= 0 || node.x >= clientWidth) {
          node.vx *= -1;
        }
        if (node.y <= 0 || node.y >= clientHeight) {
          node.vy *= -1;
        }
      }

      for (let i = 0; i < nodes.length; i += 1) {
        const node = nodes[i];
        for (let j = i + 1; j < nodes.length; j += 1) {
          const other = nodes[j];
          const dx = node.x - other.x;
          const dy = node.y - other.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < node.drift) {
            const alpha = 1 - dist / node.drift;
            context.strokeStyle = `rgba(180, 180, 180, ${alpha * 0.35})`;
            context.lineWidth = 0.6;
            context.beginPath();
            context.moveTo(node.x, node.y);
            context.lineTo(other.x, other.y);
            context.stroke();
          }
        }
      }

      for (let i = 0; i < nodes.length; i += 1) {
        const node = nodes[i];
        context.fillStyle = 'rgba(220, 220, 220, 0.8)';
        context.beginPath();
        context.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        context.fill();
      }

      rafRef.current = window.requestAnimationFrame(draw);
    };

    resize();
    draw();
    window.addEventListener('resize', resize);

    return () => {
      window.removeEventListener('resize', resize);
      if (rafRef.current) {
        window.cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={cn('pointer-events-none absolute inset-0 h-full w-full', className)}
    />
  );
};

export default NetworkMesh;

