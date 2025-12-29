import { useRef, useEffect, memo } from 'react'

interface ParticleCanvasProps {
  mode: 'day' | 'night'
}

// Performance-optimized particle canvas
function ParticleCanvasComponent({ mode }: ParticleCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const mouseRef = useRef({ x: -1000, y: -1000 })
  const animationFrameRef = useRef<number>()
  const lastFrameTime = useRef(0)
  const FPS_LIMIT = 30 // Limit to 30fps for performance
  const FRAME_INTERVAL = 1000 / FPS_LIMIT

  const config = {
    day: {
      bg: '#F9FAFB', 
      color: '99, 102, 241',
      baseSize: 1.5,
      baseAlpha: 0.15,
    },
    night: {
      bg: '#050505', 
      color: '255, 255, 255', 
      baseSize: 1.2,
      baseAlpha: 0.12,
    }
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: false })
    if (!ctx) return

    // Simplified static grid - no wave physics for performance
    let points: { x: number, y: number }[] = []

    const initGrid = (width: number, height: number) => {
      points = []
      // Larger gap = fewer particles = better performance
      const gap = width < 768 ? 45 : 55
      const cols = Math.ceil(width / gap) + 1
      const rows = Math.ceil(height / gap) + 1
      
      const startX = (width - (cols - 1) * gap) / 2
      const startY = (height - (rows - 1) * gap) / 2

      for (let i = 0; i < cols; i++) {
        for (let j = 0; j < rows; j++) {
          const offsetX = (j % 2 === 0) ? 0 : gap / 2
          points.push({ 
            x: startX + i * gap + offsetX,
            y: startY + j * gap
          })
        }
      }
    }

    let width = 0, height = 0
    const handleResize = () => {
      if (containerRef.current && canvas) {
        const rect = containerRef.current.getBoundingClientRect()
        width = rect.width
        height = rect.height
        // Use lower DPR for performance (max 2)
        const dpr = Math.min(window.devicePixelRatio || 1, 2)
        canvas.width = width * dpr
        canvas.height = height * dpr
        canvas.style.width = `${width}px`
        canvas.style.height = `${height}px`
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
        initGrid(width, height)
      }
    }

    const resizeObserver = new ResizeObserver(handleResize)
    if (containerRef.current) resizeObserver.observe(containerRef.current)

    // Throttled mouse handler
    let mouseMoveTimeout: number | null = null
    const onMove = (e: MouseEvent) => {
      if (mouseMoveTimeout) return
      mouseMoveTimeout = window.setTimeout(() => {
        mouseMoveTimeout = null
      }, 50) // Throttle to 20fps
      
      if (canvas) {
        const rect = canvas.getBoundingClientRect()
        mouseRef.current.x = e.clientX - rect.left
        mouseRef.current.y = e.clientY - rect.top
      }
    }
    
    window.addEventListener('mousemove', onMove, { passive: true })

    const animate = (timestamp: number) => {
      // FPS limiting
      const elapsed = timestamp - lastFrameTime.current
      if (elapsed < FRAME_INTERVAL) {
        animationFrameRef.current = requestAnimationFrame(animate)
        return
      }
      lastFrameTime.current = timestamp - (elapsed % FRAME_INTERVAL)

      if (!canvas || !containerRef.current || width === 0) {
        animationFrameRef.current = requestAnimationFrame(animate)
        return
      }
      
      const currentConfig = config[mode]
      
      // Fill background instead of clearRect for non-alpha canvas
      ctx.fillStyle = currentConfig.bg
      ctx.fillRect(0, 0, width, height)

      const mx = mouseRef.current.x
      const my = mouseRef.current.y
      const interactRadius = 150
      const interactRadiusSq = interactRadius * interactRadius

      // Batch draw all points
      ctx.fillStyle = `rgba(${currentConfig.color}, ${currentConfig.baseAlpha})`
      
      for (let i = 0; i < points.length; i++) {
        const p = points[i]
        const dx = mx - p.x
        const dy = my - p.y
        const distSq = dx * dx + dy * dy
        
        let size = currentConfig.baseSize
        let alpha = currentConfig.baseAlpha
        
        // Simple hover effect without complex physics
        if (distSq < interactRadiusSq) {
          const dist = Math.sqrt(distSq)
          const force = 1 - (dist / interactRadius)
          size = currentConfig.baseSize * (1 + force * 2)
          alpha = currentConfig.baseAlpha + force * 0.4
          ctx.fillStyle = `rgba(${currentConfig.color}, ${alpha})`
        } else {
          ctx.fillStyle = `rgba(${currentConfig.color}, ${currentConfig.baseAlpha})`
        }
        
        ctx.beginPath()
        ctx.arc(p.x, p.y, size, 0, Math.PI * 2)
        ctx.fill()
      }

      animationFrameRef.current = requestAnimationFrame(animate)
    }

    animationFrameRef.current = requestAnimationFrame(animate)

    return () => {
      resizeObserver.disconnect()
      window.removeEventListener('mousemove', onMove)
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current)
      if (mouseMoveTimeout) clearTimeout(mouseMoveTimeout)
    }
  }, [mode])

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 -z-10"
      style={{ background: config[mode].bg }}
    >
      <canvas ref={canvasRef} className="block w-full h-full" />
    </div>
  )
}

export const ParticleCanvas = memo(ParticleCanvasComponent)
