import { motion } from 'framer-motion'
import { ArrowRight, Play, Github, Sparkles } from 'lucide-react'
import { t, Language } from '../../i18n/translations'
import { useGitHubStats } from '../../hooks/useGitHubStats'
import { useCounterAnimation } from '../../hooks/useCounterAnimation'
import { OFFICIAL_LINKS } from '../../constants/branding'
import { SpotlightBackground } from '../ui/SpotlightBackground'

interface HeroSectionProps {
  language: Language
}

export default function HeroSection({ language }: HeroSectionProps) {
  const { stars, daysOld, isLoading } = useGitHubStats('NoFxAiOS', 'nofx')
  const animatedStars = useCounterAnimation({
    start: 0,
    end: stars,
    duration: 2000,
  })

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20">
      <SpotlightBackground />
      
      {/* Dynamic Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          className="absolute top-1/4 -left-20 w-[500px] h-[500px] bg-white/5 rounded-full blur-[120px]"
          animate={{
            x: [0, 50, 0],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
        />
        <motion.div
          className="absolute bottom-1/4 -right-20 w-[400px] h-[400px] bg-white/5 rounded-full blur-[100px]"
          animate={{
            x: [0, -30, 0],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{ duration: 12, repeat: Infinity, ease: 'linear' }}
        />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 text-center">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-10 glass border-white/10"
        >
          <Sparkles className="w-3.5 h-3.5 text-yellow-400 animate-pulse" />
          <span className="text-xs font-medium tracking-wide text-neutral-300">
            {isLoading ? (
              t('githubStarsInDays', language)
            ) : language === 'zh' ? (
              <>
                {daysOld} 天内获得{' '}
                <span className="text-white font-bold tabular-nums">
                  {(animatedStars / 1000).toFixed(1)}K+
                </span>{' '}
                GitHub Stars
              </>
            ) : (
              <>
                <span className="text-white font-bold tabular-nums">
                  {(animatedStars / 1000).toFixed(1)}K+
                </span>{' '}
                GitHub Stars in {daysOld} days
              </>
            )}
          </span>
        </motion.div>

        {/* Main Title */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="text-5xl sm:text-7xl lg:text-8xl font-bold mb-8 leading-[1.1] tracking-tight"
        >
          <span className="text-white inline-block">{t('heroTitle1', language)}</span>
          <br />
          <span className="text-gradient inline-block mt-2">
            {t('heroTitle2', language)}
          </span>
        </motion.h1>

        {/* Description */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="text-lg sm:text-xl max-w-2xl mx-auto mb-12 leading-relaxed text-neutral-400 font-medium"
        >
          {t('heroDescription', language)}
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-5 mb-20"
        >
          <motion.a
            href="/competition"
            className="group btn-modern btn-modern-primary px-8 py-4 text-lg font-bold min-w-[200px]"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Play className="w-5 h-5 fill-current" />
            {t('liveCompetition', language) || 'Live Competition'}
            <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
          </motion.a>

          <motion.a
            href={OFFICIAL_LINKS.github}
            target="_blank"
            rel="noopener noreferrer"
            className="group btn-modern btn-modern-ghost glass border-white/5 px-8 py-4 text-lg font-bold min-w-[200px]"
            whileHover={{ scale: 1.05, backgroundColor: 'rgba(255,255,255,0.05)' }}
            whileTap={{ scale: 0.95 }}
          >
            <Github className="w-5 h-5" />
            {t('viewSourceCode', language)}
          </motion.a>
        </motion.div>

        {/* Stats Row */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 0.5 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12 max-w-4xl mx-auto"
        >
          {[
            { label: 'GitHub Stars', value: `${(stars / 1000).toFixed(1)}K+` },
            {
              label: language === 'zh' ? '支持交易所' : 'Exchanges',
              value: '5+',
            },
            {
              label: language === 'zh' ? 'AI 模型' : 'AI Models',
              value: '10+',
            },
            {
              label: language === 'zh' ? '开源免费' : 'Open Source',
              value: '100%',
            },
          ].map((stat) => (
            <motion.div
              key={stat.label}
              className="text-center group"
              whileHover={{ y: -5 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              <div className="text-3xl sm:text-4xl font-bold mb-2 text-white group-hover:text-yellow-400 transition-colors">
                {stat.value}
              </div>
              <div className="text-[10px] uppercase tracking-widest text-neutral-500 font-bold">
                {stat.label}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Scroll Indicator */}
      <motion.div
        className="absolute bottom-10 left-1/2 -translate-x-1/2 pointer-events-none"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
      >
        <div className="flex flex-col items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.2em] text-neutral-600 font-bold">Scroll</span>
          <motion.div
            className="w-[1px] h-12 bg-gradient-to-b from-white/20 to-transparent"
            animate={{
              scaleY: [0, 1, 0],
              translateY: [0, 20, 40],
              opacity: [0, 1, 0]
            }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          />
        </div>
      </motion.div>
    </section>
  )
}
