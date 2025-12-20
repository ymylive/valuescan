import { useRef, useEffect, memo } from 'react'
import { motion } from 'framer-motion'

interface ParticleCanvasProps {
  mode: 'day' | 'night'
}

function ParticleCanvasComponent({ mode }: ParticleCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  // Mouse acts as a wave emitter
  const mouseRef = useRef({ x: -1000, y: -1000, vx: 0, vy: 0, lastX: 0, lastY: 0 })
  const timeRef = useRef(0)
  const animationFrameRef = useRef<number>()

  const config = {
    day: {
      bg: '#F9FAFB', 
      color: '99, 102, 241', // Indigo
      baseSize: 1.5,
      waveScale: 4.0, // How much larger particles get on surge
    },
    night: {
      bg: '#050505', 
      color: '255, 255, 255', 
      baseSize: 1.2,
      waveScale: 3.5,
    }
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Grid points
    let points: { 
      x: number, y: number, 
      originX: number, originY: number,
      wave: number // Current wave height (0-1)
    }[] = []

    const initGrid = (width: number, height: number) => {
      points = []
      // Minimalist Grid Spacing
      const gap = width < 768 ? 28 : 38 
      const cols = Math.ceil(width / gap) + 2
      const rows = Math.ceil(height / gap) + 2
      
      // Offset to center and cover edges
      const startX = (width - (cols - 1) * gap) / 2
      const startY = (height - (rows - 1) * gap) / 2

      for (let i = 0; i < cols; i++) {
        for (let j = 0; j < rows; j++) {
          // Slight offset for every other row (Hexagonal feel) -> More organic
          const offsetX = (j % 2 === 0) ? 0 : gap / 2
          const x = startX + i * gap + offsetX
          const y = startY + j * gap
          
          points.push({ 
            x, y, 
            originX: x, originY: y, 
            wave: 0 
          })
        }
      }
    }

    const handleResize = () => {
      if (containerRef.current && canvas) {
        const { width, height } = containerRef.current.getBoundingClientRect()
        const dpr = window.devicePixelRatio || 1
        canvas.width = width * dpr
        canvas.height = height * dpr
        canvas.style.width = `${width}px`
        canvas.style.height = `${height}px`
        ctx.scale(dpr, dpr)
        initGrid(width, height)
      }
    }

    const resizeObserver = new ResizeObserver(handleResize)
    if (containerRef.current) resizeObserver.observe(containerRef.current)

    const onMove = (x: number, y: number) => {
        if (canvas) {
            const rect = canvas.getBoundingClientRect()
            const curX = x - rect.left
            const curY = y - rect.top
            
            mouseRef.current.vx = (curX - mouseRef.current.lastX) * 0.2
            mouseRef.current.vy = (curY - mouseRef.current.lastY) * 0.2
            mouseRef.current.lastX = curX
            mouseRef.current.lastY = curY
            
            mouseRef.current.x = curX
            mouseRef.current.y = curY
        }
    }
    
    window.addEventListener('mousemove', (e) => onMove(e.clientX, e.clientY))
    window.addEventListener('touchmove', (e) => {
        if(e.touches.length > 0) onMove(e.touches[0].clientX, e.touches[0].clientY)
    })

    const animate = () => {
      if (!canvas || !containerRef.current) return
      const width = containerRef.current.clientWidth
      const height = containerRef.current.clientHeight
      const currentConfig = config[mode]
      
      ctx.clearRect(0, 0, width, height)
      timeRef.current += 0.05

      // Mouse momentum decay
      mouseRef.current.vx *= 0.9
      mouseRef.current.vy *= 0.9
      const mouseSpeed = Math.sqrt(mouseRef.current.vx**2 + mouseRef.current.vy**2)

      points.forEach(p => {
        // Distance to mouse
        const dx = mouseRef.current.x - p.originX
        const dy = mouseRef.current.y - p.originY
        const dist = Math.sqrt(dx*dx + dy*dy)
        
        // --- Wave Physics ---
        // 1. Trigger Wave: Mouse movement creates a "pressure wave"
        const interactRadius = 250
        let targetWave = 0
        
        if (dist < interactRadius) {
            const force = (interactRadius - dist) / interactRadius
            // Smooth bell curve force
            const smoothForce = Math.pow(force, 2) 
            
            // Surge amplitude depends on mouse speed + proximity
            // Static mouse has gentle surge, moving mouse has strong surge
            targetWave = smoothForce * (0.3 + Math.min(mouseSpeed * 0.05, 1.0))
        }

        // 2. Ambient Wave (Breathing)
        // Gentle, large-scale sine wave passing through
        const ambientWave = Math.sin(p.originX * 0.005 + p.originY * 0.005 + timeRef.current * 0.5) * 0.15 + 0.15
        
        // Combine waves
        // We use lerp for smooth transition of the 'wave' state
        p.wave += (Math.max(targetWave, ambientWave) - p.wave) * 0.1

        // --- Visual Output ---
        // Surge Effect: Scale up and slight offset
        // Instead of moving x/y wildly, we primarily change SCALE to simulate Z-axis surge
        
        const scale = 1 + p.wave * currentConfig.waveScale
        const size = currentConfig.baseSize * scale
        
        // Minimal offset to feel fluid (dragged by wave)
        // Particles move slightly AWAY from high pressure (mouse) to simulate displacement
        // OR slightly towards movement direction
        const moveX = (mouseRef.current.vx * p.wave * 2) 
        const moveY = (mouseRef.current.vy * p.wave * 2)
        
        p.x += (p.originX + moveX - p.x) * 0.1
        p.y += (p.originY + moveY - p.y) * 0.1

        // Draw
        ctx.beginPath()
        ctx.arc(p.x, p.y, size, 0, Math.PI * 2)
        
        // Alpha helps surge feel "glowing"
        const alpha = Math.min(0.8, 0.2 + p.wave * 0.6)
        ctx.fillStyle = `rgba(${currentConfig.color}, ${alpha})`
        ctx.fill()
      })

      animationFrameRef.current = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      resizeObserver.disconnect()
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current)
    }
  }, [mode])

  return (
    <motion.div
      ref={containerRef}
      className="fixed inset-0 -z-10"
      animate={{ background: config[mode].bg }}
      transition={{ duration: 1.2 }}
    >
      <canvas ref={canvasRef} className="block w-full h-full" />
      {/* Subtle Vignette for depth */}
      <div 
        className="absolute inset-0 pointer-events-none"
        style={{
            background: mode === 'day'
                ? 'radial-gradient(circle at center, transparent 0%, rgba(255,255,255,0.6) 100%)' 
                : 'radial-gradient(circle at center, transparent 0%, rgba(0,0,0,0.7) 100%)'
        }}
      />
    </motion.div>
  )
}

export const ParticleCanvas = memo(ParticleCanvasComponent)
