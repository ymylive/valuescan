import { useState, useEffect } from 'react'

type Theme = 'day' | 'night'

const getSingaporeHour = (): number => {
  const now = new Date()
  const sgTime = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Singapore',
    hour: 'numeric',
    hour12: false
  }).format(now)
  return parseInt(sgTime, 10)
}

const getThemeForHour = (hour: number): Theme => {
  return hour >= 7 && hour < 19 ? 'day' : 'night'
}

export const useTheme = () => {
  const [theme, setTheme] = useState<Theme>(() => getThemeForHour(getSingaporeHour()))
  const [manualOverride, setManualOverride] = useState(false)

  useEffect(() => {
    const checkAndUpdateTheme = () => {
      const hour = getSingaporeHour()
      const newTheme = getThemeForHour(hour)

      if (newTheme !== theme) {
        setTheme(newTheme)
        setManualOverride(false)
      }
    }

    const interval = setInterval(checkAndUpdateTheme, 60000)
    return () => clearInterval(interval)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'day' ? 'night' : 'day')
    setManualOverride(true)
  }

  return { theme, toggleTheme, isManual: manualOverride }
}
