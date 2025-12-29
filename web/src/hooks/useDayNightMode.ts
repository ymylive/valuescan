import { useState, useEffect } from 'react'

export type ThemeMode = 'day' | 'night'

export function useDayNightMode() {
  const [mode, setMode] = useState<ThemeMode>('night')

  useEffect(() => {
    const checkTime = () => {
      const now = new Date()
      const currentMinutes = now.getHours() * 60 + now.getMinutes()
      
      // 07:30 = 7 * 60 + 30 = 450 minutes
      const morningThreshold = 7 * 60 + 30
      // 19:30 = 19 * 60 + 30 = 1170 minutes
      const eveningThreshold = 19 * 60 + 30

      if (currentMinutes >= morningThreshold && currentMinutes < eveningThreshold) {
        setMode('day')
      } else {
        setMode('night')
      }
    }

    // Check immediately
    checkTime()

    // Check every minute to auto-switch without reload
    const interval = setInterval(checkTime, 60000)

    return () => clearInterval(interval)
  }, [])

  return mode
}
