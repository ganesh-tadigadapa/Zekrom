import { useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowLeft, ArrowUpRight, Sparkles } from 'lucide-react'
import type { Capabilities } from '../lib/api'
import { GROUPS, ToolRunner, toolEnabled, type ToolDef } from './Tools'
import { GITHUB_URL, GithubMark } from './Hero'
import { Wordmark } from './ui'

const ease = [0.22, 1, 0.36, 1] as const

interface Props {
  caps: Capabilities | null
  onHistoryChange: () => void
  onFocusChange: (focused: boolean) => void
}

/** Page 2: every standalone tool, with its own hero. */
export function ToolsPage({ caps, onHistoryChange, onFocusChange }: Props) {
  const [groupIndex, setGroupIndex] = useState(0)
  const [active, setActive] = useState<ToolDef | null>(null)
  const group = GROUPS[groupIndex]
  const total = GROUPS.reduce((n, g) => n + g.tools.length, 0)

  const open = (t: ToolDef) => {
    if (caps && !toolEnabled(t, caps)) return
    setActive(t)
    onFocusChange(true)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const close = () => {
    setActive(null)
    onFocusChange(false)
  }

  if (active && caps) {
    return (
      <section className="hero-frame relative min-h-[100svh]">
        <div className="grid-lines pointer-events-none absolute inset-0 opacity-25" aria-hidden />
        <div className="wrap relative pt-24 pb-16">
          <button onClick={close} className="mb-6 inline-flex items-center gap-2 rounded-full px-1 text-sm text-fg-2 transition-colors hover:text-fg">
            <ArrowLeft className="size-4" /> All tools
          </button>
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease }} className="mx-auto max-w-5xl">
            <ToolRunner tool={active} caps={caps} onClose={close} onHistoryChange={onHistoryChange} />
          </motion.div>
        </div>
      </section>
    )
  }

  return (
    <section className="hero-frame relative flex min-h-[100svh] flex-col overflow-clip">
      <div className="grid-lines pointer-events-none absolute inset-0 opacity-25" aria-hidden />

      <div className="wrap relative grid flex-1 items-center gap-14 pt-28 pb-12 lg:grid-cols-[1.05fr_1fr] lg:gap-10 lg:pt-20">
        {/* Copy + tool picker */}
        <div className="mx-auto w-full max-w-xl lg:mx-0">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease }}
            className="inline-flex items-center gap-2 rounded-full border border-line-2 bg-card/40 py-1.5 pr-4 pl-1.5 text-[13px] text-fg-2 backdrop-blur"
          >
            <span className="grid size-6 place-items-center rounded-full bg-violet/20 text-lavender">
              <Sparkles className="size-3" strokeWidth={2.4} />
            </span>
            {total} tools · free · no sign-up
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.05, ease }}
            className="mt-7 text-[46px] leading-[0.98] font-bold tracking-[-0.045em] sm:text-7xl lg:text-[clamp(56px,7.2svh,84px)]"
          >
            Every Tool.
            <br />
            <span className="text-gradient-hero hero-glow-text">One Place.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.12, ease }}
            className="mt-6 max-w-[30rem] text-[17px] leading-relaxed text-fg-2"
          >
            Merge, split and compress PDFs. Resize and shrink images. Turn documents and sheets into the format you need.
          </motion.p>

          {/* Category switch */}
          <div role="tablist" aria-label="Tool categories" className="mt-9 inline-flex gap-0.5 rounded-full sm:gap-1 border border-line bg-card/40 p-1 backdrop-blur">
            {GROUPS.map((g, i) => (
              <button
                key={g.name}
                role="tab"
                aria-selected={i === groupIndex}
                onClick={() => setGroupIndex(i)}
                className={`relative rounded-full px-3 py-1.5 text-[13px] font-medium transition-colors sm:px-4 ${i === groupIndex ? 'text-fg' : 'text-fg-2 hover:text-fg'}`}
              >
                {i === groupIndex && (
                  <motion.span layoutId="tool-cat" className="absolute inset-0 rounded-full bg-violet/20 ring-1 ring-purple/60 shadow-[0_0_20px_-6px_rgba(168,85,247,0.9)]" transition={{ type: 'spring', stiffness: 380, damping: 32 }} />
                )}
                <span className="relative">{g.name.replace(' Tools', '')}</span>
              </button>
            ))}
          </div>

          {/* Tools in the selected category */}
          <div className="mt-5 min-h-[248px]">
            <AnimatePresence mode="wait">
              <motion.ul
                key={group.name}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.25 }}
                className="grid gap-2.5 sm:grid-cols-2"
              >
                {group.tools.map((t) => {
                  const enabled = caps ? toolEnabled(t, caps) : false
                  return (
                    <li key={t.id}>
                      <button
                        onClick={() => open(t)}
                        disabled={!enabled}
                        title={enabled ? undefined : caps ? 'Not available on this server' : 'Loading…'}
                        className="format-tile group flex h-full w-full items-start gap-3.5 rounded-2xl p-4 text-left disabled:pointer-events-none disabled:opacity-40"
                      >
                        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-gradient-to-b from-white/[0.07] to-white/[0.015] text-lavender ring-1 ring-white/10 light:from-black/[0.03] light:ring-black/10">
                          <t.icon className="size-[18px]" strokeWidth={1.6} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="flex items-center justify-between gap-2 text-[15px] font-medium text-fg">
                            {t.name}
                            <ArrowUpRight className="size-4 shrink-0 text-fg-3 transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-lavender" />
                          </span>
                          <span className="mt-1 block text-[13px] leading-snug text-fg-3">{t.desc}</span>
                        </span>
                      </button>
                    </li>
                  )
                })}
              </motion.ul>
            </AnimatePresence>
          </div>
        </div>

        {/* Orbiting tool constellation */}
        <ToolOrbit group={GROUPS[groupIndex]} onPick={open} caps={caps} />
      </div>

      <div className="relative border-t border-line">
        <div className="wrap flex flex-col items-center justify-between gap-3 py-5 text-[13px] text-fg-3 sm:flex-row">
          <p>
            <Wordmark className="text-[12px]" />
            <span className="ml-3">Tools · files auto-delete after {caps?.limits.retention_minutes ?? 60} min</span>
          </p>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 transition-colors hover:text-fg">
            <GithubMark className="size-3.5" /> GitHub
          </a>
        </div>
      </div>
    </section>
  )
}

function ToolOrbit({ group, onPick, caps }: { group: (typeof GROUPS)[number]; onPick: (t: ToolDef) => void; caps: Capabilities | null }) {
  const tools = group.tools
  // Place tools evenly on the orbit, starting at the top.
  const positions = useMemo(
    () => tools.map((_, i) => (i / tools.length) * Math.PI * 2 - Math.PI / 2),
    [tools],
  )
  const GroupIcon = group.icon

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.9, delay: 0.1, ease }}
      className="relative mx-auto hidden aspect-square w-full max-w-[min(520px,64svh)] lg:block"
      aria-hidden
    >
      <div className="orb-haze" />
      {/* Guide rings */}
      <div className="absolute inset-[4%] rounded-full border border-dashed border-white/[0.07] light:border-black/10" />
      <div className="absolute inset-[18%] rounded-full border border-white/[0.06] light:border-black/[0.08]" />

      {/* Core */}
      <div className="orb-ring absolute inset-[31%] grid place-items-center rounded-full">
        <AnimatePresence mode="wait">
          <motion.div
            key={group.name}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.3 }}
            className="text-center"
          >
            <GroupIcon className="mx-auto size-9 text-[#C4B5FD] drop-shadow-[0_0_18px_rgba(168,85,247,0.6)]" strokeWidth={1.4} />
            <p className="mt-2 text-xs font-medium tracking-[0.16em] text-fg-2 uppercase">{group.name.replace(' Tools', '')}</p>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Tools travelling on the outer orbit */}
      <AnimatePresence mode="wait">
        <motion.div
          key={group.name}
          initial={{ opacity: 0, rotate: -20 }}
          animate={{ opacity: 1, rotate: 0 }}
          exit={{ opacity: 0, rotate: 20 }}
          transition={{ duration: 0.5, ease }}
          className="absolute inset-0"
        >
          <div className="tool-orbit absolute inset-0">
            {tools.map((t, i) => {
              const a = positions[i]
              const enabled = caps ? toolEnabled(t, caps) : false
              return (
                <button
                  key={t.id}
                  tabIndex={-1}
                  onClick={() => onPick(t)}
                  disabled={!enabled}
                  className="pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2"
                  style={{ left: `${50 + 41 * Math.cos(a)}%`, top: `${50 + 41 * Math.sin(a)}%` }}
                >
                  <span className="tool-orbit-item group flex flex-col items-center gap-2">
                    <span className="grid size-14 place-items-center rounded-2xl border border-white/10 bg-[#0d0b16]/90 text-lavender shadow-[0_0_30px_-8px_rgba(168,85,247,0.7)] backdrop-blur transition-all group-hover:scale-110 group-hover:border-purple/60 light:border-black/10 light:bg-white/90">
                      <t.icon className="size-6" strokeWidth={1.5} />
                    </span>
                    <span className="text-[11px] font-medium whitespace-nowrap text-fg-2 opacity-0 transition-opacity group-hover:opacity-100">{t.name}</span>
                  </span>
                </button>
              )
            })}
          </div>
        </motion.div>
      </AnimatePresence>
    </motion.div>
  )
}
