import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, ChevronDown, FileText, Image as ImageIcon, LayoutGrid, Lock, RefreshCw } from 'lucide-react'
import type { Capabilities } from '../lib/api'
import { Converter } from './Converter'

export const GITHUB_URL = 'https://github.com/ganesh-tadigadapa/Snipex'

function LetterGlyph({ letter }: { letter: string }) {
  return (
    <span className="grid size-[22px] place-items-center rounded-[5px] border-[1.6px] border-current text-[11px] leading-none font-bold" aria-hidden>
      {letter}
    </span>
  )
}

const TILES = [
  { label: 'PDF', icon: <FileText className="size-[22px]" strokeWidth={1.6} /> },
  { label: 'DOCX', icon: <LetterGlyph letter="W" /> },
  { label: 'PPTX', icon: <LetterGlyph letter="P" /> },
  { label: 'XLSX', icon: <LetterGlyph letter="X" /> },
  { label: 'JPG', icon: <ImageIcon className="size-[22px]" strokeWidth={1.6} /> },
  { label: 'More', icon: <LayoutGrid className="size-[20px]" strokeWidth={1.6} /> },
]

export function GithubMark({ className = 'size-[18px]' }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className} fill="currentColor" aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  )
}

interface Props {
  caps: Capabilities | null
  error: string | null
  onRetry: () => void
  onHistoryChange: () => void
  onFocusChange?: (focused: boolean) => void
}

const ease = [0.22, 1, 0.36, 1] as const

export function Hero({ caps, error, onRetry, onHistoryChange, onFocusChange }: Props) {
  const [active, setActive] = useState(false)
  useEffect(() => {
    onFocusChange?.(active)
    if (active) window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [active, onFocusChange])

  return (
    <section id="convert" className="hero-frame relative flex min-h-[100svh] flex-col overflow-clip">
      <div className="grid-lines pointer-events-none absolute inset-0 opacity-25" aria-hidden />

      <div
        className={`wrap relative grid flex-1 items-center gap-12 pt-28 pb-16 lg:gap-10 ${
          active ? 'grid-cols-1 content-start gap-6 pt-20 pb-6 lg:pt-20' : 'lg:grid-cols-2 lg:pt-24 lg:pb-20'
        }`}
      >
        {/* Copy */}
        <motion.div
          layout="position"
          className={active ? 'text-center' : 'mx-auto w-full max-w-xl text-center lg:order-2 lg:mx-0 lg:justify-self-end lg:text-left'}
        >
          <AnimatePresence initial={false} mode="popLayout">
            {!active && (
              <motion.a
                key="badge"
                href="#faq"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.6, ease }}
                className="inline-flex items-center gap-2 rounded-full border border-line-2 bg-card/40 py-1.5 pr-4 pl-1.5 text-[13px] text-fg-2 backdrop-blur transition-colors hover:border-violet/50 hover:text-fg"
              >
                <span className="grid size-6 place-items-center rounded-full bg-violet/20 text-lavender">
                  <Lock className="size-3" strokeWidth={2.4} />
                </span>
                Private by design · files auto-delete
              </motion.a>
            )}
          </AnimatePresence>

          <motion.h1
            layout="position"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.05, ease }}
            className={`font-bold tracking-[-0.045em] ${
              active ? 'text-[26px] leading-tight sm:text-[32px]' : 'mt-7 text-[48px] leading-[0.98] sm:text-7xl lg:text-[clamp(60px,7.6svh,88px)]'
            }`}
          >
            Convert Files{active ? ' ' : <br />}
            <span className="text-gradient-hero hero-glow-text">Effortlessly.</span>
          </motion.h1>

          <AnimatePresence initial={false}>
            {!active && (
              <motion.div key="details" exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.25 }}>
                <motion.p
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.7, delay: 0.12, ease }}
                  className="mx-auto mt-6 max-w-[30rem] text-[17px] leading-relaxed text-pretty text-fg-2 lg:mx-0"
                >
                  Documents, presentations, spreadsheets, images and more. Drop up to {caps?.limits.max_files ?? 30} files and convert
                  them all in one go.
                </motion.p>

                <div className="mx-auto mt-10 hidden max-w-[30rem] grid-cols-6 gap-2.5 sm:grid sm:gap-3 lg:mx-0 lg:max-w-none">
                  {TILES.map((t, i) => (
                    <motion.a
                      key={t.label}
                      href="#formats"
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5, delay: 0.2 + i * 0.05, ease }}
                      className="format-tile flex aspect-square flex-col items-center justify-center gap-1.5 rounded-2xl text-fg sm:gap-2"
                      aria-label={t.label === 'More' ? 'All supported formats' : `${t.label} conversions`}
                    >
                      {t.icon}
                      <span className="text-[10.5px] font-medium tracking-wide text-fg-2 sm:text-[12px]">{t.label === 'More' ? '+ More' : t.label}</span>
                    </motion.a>
                  ))}
                </div>

                <motion.dl
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.8, delay: 0.55 }}
                  className="mx-auto mt-10 hidden max-w-[30rem] grid-cols-3 divide-x sm:grid lg:max-w-none divide-line border-t border-line pt-6 lg:mx-0"
                >
                  {[
                    [caps ? String(caps.conversions.length) : '110', 'Tested routes'],
                    [`${caps?.limits.max_files ?? 30}`, 'Files per batch'],
                    ['0', 'Sign-ups needed'],
                  ].map(([value, label], i) => (
                    <div key={label} className={i === 0 ? 'pr-4' : 'px-4'}>
                      <dt className="sr-only">{label}</dt>
                      <dd className="text-2xl font-semibold tracking-tight tabular-nums">{value}</dd>
                      <dd className="mt-0.5 text-xs text-fg-3">{label}</dd>
                    </div>
                  ))}
                </motion.dl>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Converter / orb */}
        <motion.div
          layout="position"
          initial={{ opacity: 0, scale: 0.94 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.9, delay: 0.1, ease }}
          className={active ? 'mx-auto w-full max-w-4xl' : 'w-full lg:order-1'}
        >
          {caps ? (
            <Converter caps={caps} onHistoryChange={onHistoryChange} onActiveChange={setActive} />
          ) : error ? (
            <div className="mx-auto max-w-md rounded-[28px] border border-danger/30 bg-card/80 p-10 text-center">
              <AlertTriangle className="mx-auto mb-3 size-8 text-danger" />
              <p className="font-semibold">{error}</p>
              <p className="mt-1 text-sm text-fg-2">Make sure the Zekrom API is running, then try again.</p>
              <button onClick={onRetry} className="mt-5 inline-flex h-10 items-center gap-2 rounded-xl border border-line bg-card-2 px-4 text-sm font-medium hover:border-line-2">
                <RefreshCw className="size-4" /> Retry
              </button>
            </div>
          ) : (
            <div className="mx-auto aspect-square w-full max-w-[min(540px,62svh)] p-[7%]" aria-busy="true" aria-label="Loading converter">
              <div className="skeleton size-full rounded-full" />
            </div>
          )}
        </motion.div>
      </div>

      {!active && (
        <a href="#formats" className="relative mx-auto mb-7 hidden flex-col items-center gap-1 text-[11px] tracking-[0.2em] text-fg-3 uppercase transition-colors hover:text-fg-2 lg:flex" aria-label="Scroll to supported formats">
          Explore
          <ChevronDown className="scroll-cue size-4" />
        </a>
      )}
      <div className="hero-fade pointer-events-none absolute inset-x-0 bottom-0 h-24" aria-hidden />
    </section>
  )
}
