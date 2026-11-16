import { createContext, useCallback, useContext, useId, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  AlertTriangle, CheckCircle2, ChevronDown, File, FileArchive, FileCode2, FileImage, FileSpreadsheet,
  FileText, Info, Presentation, X,
} from 'lucide-react'
import type { Category } from '../lib/api'

export function OrbitMark({ className = 'size-7' }: { className?: string }) {
  const id = useId().replace(/:/g, '')
  return (
    <svg viewBox="0 0 40 40" className={`shrink-0 ${className}`} aria-hidden>
      <defs>
        <linearGradient id={`og-${id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#F5EDFF" />
          <stop offset="0.45" stopColor="#B57BFF" />
          <stop offset="1" stopColor="#6D28D9" />
        </linearGradient>
        <filter id={`ob-${id}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.4" />
        </filter>
      </defs>
      <ellipse cx="20" cy="20" rx="14.5" ry="9.5" transform="rotate(-24 20 20)" fill="none" stroke="#8B5CF6" strokeWidth="6" filter={`url(#ob-${id})`} opacity="0.9" />
      <ellipse cx="20" cy="20" rx="14.5" ry="9.5" transform="rotate(-24 20 20)" fill="none" stroke={`url(#og-${id})`} strokeWidth="4.2" />
      {/* bolt cutting through the orbit */}
      <path d="M22.6 5.5 13.4 21.4h6.1l-2.6 13.1 10.4-17.2h-6.3l1.6-11.8Z" fill="#8B5CF6" filter={`url(#ob-${id})`} opacity="0.85" />
      <path d="M22.6 5.5 13.4 21.4h6.1l-2.6 13.1 10.4-17.2h-6.3l1.6-11.8Z" fill="#fff" stroke="#0b0912" strokeWidth="1.1" strokeLinejoin="round" />
    </svg>
  )
}

/** The ZEKROM name, set in a wide display face with a metallic sheen. */
export function Wordmark({ className = '' }: { className?: string }) {
  return <span className={`wordmark ${className}`}>ZEKROM</span>
}

export function Logo({ className = '', size = 'md' }: { className?: string; size?: 'md' | 'lg' }) {
  return (
    <a href="#top" className={`flex items-center gap-3 font-semibold ${className}`} aria-label="ZEKROM home">
      <OrbitMark className={size === 'lg' ? 'size-11' : 'size-8'} />
      <Wordmark className={size === 'lg' ? 'text-[24px]' : 'hidden text-[14px] sm:inline'} />
    </a>
  )
}

const CATEGORY_STYLE: Record<string, { icon: typeof File; tint: string }> = {
  document: { icon: FileText, tint: 'text-sky-400 bg-sky-400/10 ring-sky-400/20' },
  presentation: { icon: Presentation, tint: 'text-orange-400 bg-orange-400/10 ring-orange-400/20' },
  spreadsheet: { icon: FileSpreadsheet, tint: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20' },
  image: { icon: FileImage, tint: 'text-pink-400 bg-pink-400/10 ring-pink-400/20' },
  pdf: { icon: FileText, tint: 'text-rose-400 bg-rose-400/10 ring-rose-400/20' },
  data: { icon: FileCode2, tint: 'text-amber-400 bg-amber-400/10 ring-amber-400/20' },
  archive: { icon: FileArchive, tint: 'text-lavender bg-violet/10 ring-violet/20' },
}

export function FileIcon({ category, ext, size = 'md' }: { category: Category | null; ext: string; size?: 'sm' | 'md' }) {
  const Icon = (category && CATEGORY_STYLE[category]?.icon) || File
  const box = size === 'sm' ? 'size-8 rounded-lg' : 'size-10 rounded-xl'
  return (
    <div
      className={`relative grid shrink-0 place-items-center bg-gradient-to-b from-white/[0.06] to-white/[0.015] text-lavender ring-1 ring-white/10 light:from-black/[0.03] light:to-transparent light:ring-black/10 ${box}`}
      aria-hidden
    >
      <Icon className={size === 'sm' ? 'size-4' : 'size-[18px]'} strokeWidth={1.5} />
      {ext && size === 'md' && (
        <span className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 rounded-[4px] bg-bg px-1 font-mono text-[8px] leading-[12px] tracking-wider text-fg-3 uppercase ring-1 ring-line">
          {ext.slice(0, 4)}
        </span>
      )}
    </div>
  )
}

export function Select({
  value, onChange, options, label, className = '', disabled, placeholder,
}: {
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string; hint?: string; disabled?: boolean }[]
  label: string
  className?: string
  disabled?: boolean
  placeholder?: string
}) {
  return (
    <div className={`relative ${className}`}>
      <select
        aria-label={label}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full cursor-pointer rounded-lg border border-line bg-card-2 pr-8 pl-3 text-sm font-medium text-fg transition-colors hover:border-line-2 focus:border-violet focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value} disabled={o.disabled}>
            {o.label}{o.hint ? `  ·  ${o.hint}` : ''}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-fg-3" />
    </div>
  )
}

export function SectionHeading({ eyebrow, title, sub }: { eyebrow: string; title: ReactNode; sub?: string }) {
  return (
    <div className="mx-auto mb-12 max-w-2xl text-center">
      <p className="mb-3 text-xs font-semibold tracking-[0.2em] text-lavender uppercase">{eyebrow}</p>
      <h2 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">{title}</h2>
      {sub && <p className="mt-4 text-base text-pretty text-fg-2">{sub}</p>}
    </div>
  )
}

// ---- Toasts -------------------------------------------------------------------------------

type ToastKind = 'success' | 'error' | 'info' | 'warning'
interface Toast { id: number; kind: ToastKind; message: string }
const ToastCtx = createContext<(kind: ToastKind, message: string) => void>(() => {})

export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const push = useCallback((kind: ToastKind, message: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t.slice(-3), { id, kind, message }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === 'error' ? 7000 : 4500)
  }, [])
  const icons = { success: CheckCircle2, error: AlertTriangle, warning: AlertTriangle, info: Info }
  const colors = { success: 'text-success', error: 'text-danger', warning: 'text-warning', info: 'text-lavender' }
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-4 bottom-4 z-[100] flex flex-col items-center gap-2 sm:inset-x-auto sm:right-5 sm:bottom-5 sm:items-end" role="status" aria-live="polite">
        <AnimatePresence initial={false}>
          {toasts.map((t) => {
            const Icon = icons[t.kind]
            return (
              <motion.div
                key={t.id}
                layout
                initial={{ opacity: 0, y: 16, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 24, transition: { duration: 0.15 } }}
                className="glass pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border border-line p-3.5 pr-2.5 shadow-2xl shadow-black/30"
              >
                <Icon className={`mt-0.5 size-4 shrink-0 ${colors[t.kind]}`} />
                <p className="flex-1 text-sm text-fg">{t.message}</p>
                <button onClick={() => setToasts((x) => x.filter((y) => y.id !== t.id))} className="rounded p-0.5 text-fg-3 hover:text-fg" aria-label="Dismiss notification">
                  <X className="size-4" />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  )
}
