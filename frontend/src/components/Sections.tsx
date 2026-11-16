import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ArrowRight, Clock, Cpu, Download, FileStack, History as HistoryIcon, Layers, Menu, Moon, MousePointerClick,
  Plus, ShieldCheck, Sun, Trash2, UploadCloud, Wand2, X, Zap,
} from 'lucide-react'
import { deleteBatch, fileUrl, zipUrl, type Capabilities } from '../lib/api'
import { CATEGORY_LABEL, CATEGORY_ORDER, bytes } from '../lib/format'
import { getTheme, history, setTheme, type HistoryEntry } from '../lib/storage'
import { GITHUB_URL, GithubMark } from './Hero'
import { Logo, SectionHeading, useToast } from './ui'

export type Page = 'home' | 'tools'

const PAGES: [Page, string, string][] = [
  ['home', 'Converter', '#/'],
  ['tools', 'Tools', '#/tools'],
]
const SECTION_LINKS = [
  ['Formats', '#formats'],
  ['FAQ', '#faq'],
] as const

export function Nav({ focused = false, page }: { focused?: boolean; page: Page }) {
  const [theme, setT] = useState(getTheme)
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    setT(next)
  }
  return (
    <header className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${scrolled || open ? 'glass border-b border-line' : 'border-b border-transparent'}`}>
      <nav className="wrap grid h-[68px] grid-cols-[1fr_auto_1fr] items-center" aria-label="Main">
        <Logo />
        {/* Page switch: page 1 = converter, page 2 = tools */}
        <div
          role="tablist"
          aria-label="Pages"
          className={`flex items-center gap-0.5 rounded-full border border-line bg-card/40 p-1 backdrop-blur-md transition-opacity duration-300 ${focused ? 'invisible opacity-0' : ''}`}
        >
          {PAGES.map(([p, label, href]) => (
            <a
              key={p}
              href={href}
              role="tab"
              aria-selected={page === p}
              className={`relative rounded-full px-4 py-1.5 text-[13.5px] font-medium transition-colors sm:px-5 ${page === p ? 'text-fg' : 'text-fg-2 hover:text-fg'}`}
            >
              {page === p && (
                <motion.span
                  layoutId="page-pill"
                  className="absolute inset-0 rounded-full bg-violet/20 ring-1 ring-purple/60 shadow-[0_0_20px_-6px_rgba(168,85,247,0.9)]"
                  transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                />
              )}
              <span className="relative">{label}</span>
            </a>
          ))}
        </div>
        <div className="flex items-center justify-end gap-1 sm:gap-2">
          <div className={`hidden items-center md:flex ${focused ? 'invisible' : ''}`}>
            {SECTION_LINKS.map(([label, href]) => (
              <a key={href} href={href} className="rounded-full px-3 py-1.5 text-[13.5px] text-fg-2 transition-colors hover:text-fg">{label}</a>
            ))}
          </div>
          <button onClick={toggle} className="grid size-9 place-items-center rounded-full border border-line text-fg-2 transition-colors hover:border-line-2 hover:text-fg" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
            {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
          <button onClick={() => setOpen(!open)} className={`size-9 place-items-center rounded-full border border-line text-fg-2 md:hidden ${focused ? 'hidden' : 'grid'}`} aria-label="Toggle menu" aria-expanded={open}>
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </nav>
      <AnimatePresence>
        {open && (
          <motion.ul initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="wrap overflow-hidden md:hidden">
            {SECTION_LINKS.map(([label, href]) => (
              <li key={href}><a onClick={() => setOpen(false)} href={href} className="block border-t border-line py-3 text-sm text-fg-2">{label}</a></li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </header>
  )
}

export function SupportedFormats({ caps }: { caps: Capabilities | null }) {
  const [active, setActive] = useState<string | null>(null)
  return (
    <section id="formats" className="wrap py-28">
      <SectionHeading
        eyebrow="Supported formats"
        title={<>Every route here is <span className="text-gradient">real and tested</span></>}
        sub="This list is generated live from the conversion engine. If a format is shown, it converts. Pick one to see where it can go."
      />
      {!caps ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 6 }, (_, i) => <div key={i} className="skeleton h-36 rounded-2xl" />)}</div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CATEGORY_ORDER.map((cat) => {
            const formats = caps.formats.filter((f) => f.category === cat && caps.inputs.includes(f.id))
            if (!formats.length) return null
            return (
              <div key={cat} className="card-border rounded-2xl border border-line bg-card/60 p-5">
                <p className="mb-4 text-sm font-semibold">{CATEGORY_LABEL[cat]}</p>
                <div className="flex flex-wrap gap-1.5">
                  {formats.map((f) => (
                    <button
                      key={f.id}
                      onClick={() => setActive(active === f.id ? null : f.id)}
                      aria-pressed={active === f.id}
                      className={`rounded-md px-2 py-1 font-mono text-xs ring-1 transition-colors ${active === f.id ? 'bg-violet/25 text-fg ring-violet/50' : 'bg-card-2 text-fg-2 ring-line hover:text-fg hover:ring-line-2'}`}
                    >
                      {f.extensions.map((e) => e.toUpperCase()).join(' / ')}
                    </button>
                  ))}
                </div>
                <AnimatePresence>
                  {active && formats.some((f) => f.id === active) && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
                      <p className="mt-4 mb-2 text-xs text-fg-3">Converts to</p>
                      <div className="flex flex-wrap gap-1.5">
                        {caps.conversions.filter((c) => c.src === active).map((c) => (
                          <span key={c.dst} title={c.notes || undefined} className="rounded-md bg-violet/10 px-2 py-1 font-mono text-xs text-lavender ring-1 ring-violet/25">
                            {caps.formats.find((f) => f.id === c.dst)?.label ?? c.dst}
                            {c.quality === 'basic' && <span className="ml-1 text-warning">•</span>}
                          </span>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )
          })}
        </div>
      )}
      {caps && (
        <p className="mt-6 text-center text-sm text-fg-3">
          <span className="font-semibold text-fg">{caps.conversions.length}</span> conversion routes across{' '}
          <span className="font-semibold text-fg">{caps.inputs.length}</span> input formats.
          <span className="ml-2 text-warning">•</span> = simplified layout, see notes.
          {caps.unavailable.length > 0 && <> {caps.unavailable.length} routes are disabled on this server (missing {[...new Set(caps.unavailable.flatMap((u) => u.missing))].join(', ')}).</>}
        </p>
      )}
    </section>
  )
}

const FEATURES = [
  { icon: FileStack, title: 'True batch conversion', body: 'Drop up to 30 mixed files. Documents, slides, sheets and images all convert in a single run.' },
  { icon: Wand2, title: 'Smart output selection', body: 'Zekrom only offers formats your files can actually become, and shows exactly which files fit each one.' },
  { icon: Layers, title: 'Purpose-built engines', body: 'LibreOffice for office files, Pillow and MuPDF for images and PDFs, native parsers for data. Each format gets the right tool.' },
  { icon: Zap, title: 'Parallel and resilient', body: 'Controlled parallel workers with automatic retry. One bad file never stops the rest of the batch.' },
  { icon: ShieldCheck, title: 'Private by default', body: 'Every file is checked against its real signature, converted in an isolated process, and deleted automatically.' },
  { icon: Download, title: 'Download your way', body: 'Grab files one by one, or everything in a single ZIP with collision-free filenames.' },
]

export function Features() {
  return (
    <section id="features" className="wrap py-28">
      <SectionHeading eyebrow="Features" title="Built for the files you actually have" sub="Real conversions, done properly, with no fake progress bars." />
      <div className="grid gap-px overflow-hidden rounded-3xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ delay: (i % 3) * 0.06 }}
            className="bg-bg p-7"
          >
            <span className="mb-5 grid size-10 place-items-center rounded-xl bg-violet/12 text-lavender ring-1 ring-violet/30">
              <f.icon className="size-[18px]" />
            </span>
            <h3 className="font-semibold">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-fg-2">{f.body}</p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}

const STEPS = [
  { icon: UploadCloud, title: 'Upload files', body: 'Drag in up to 30 files at once, of any mix of types.' },
  { icon: Cpu, title: 'Select output format', body: 'One format for everything, or a different one per file.' },
  { icon: MousePointerClick, title: 'Click Convert All', body: 'Watch every file move through the queue in real time.' },
  { icon: Download, title: 'Download', body: 'Save files individually or grab one ZIP.' },
]

export function HowItWorks() {
  return (
    <section id="how" className="wrap py-28">
      <SectionHeading eyebrow="How it works" title="Four steps. No account." />
      <ol className="relative grid gap-4 md:grid-cols-4">
        <div className="absolute top-7 right-[12%] left-[12%] hidden h-px bg-gradient-to-r from-transparent via-violet/50 to-transparent md:block" aria-hidden />
        {STEPS.map((s, i) => (
          <motion.li
            key={s.title}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.08 }}
            className="relative text-center"
          >
            <span className="relative mx-auto mb-5 grid size-14 place-items-center rounded-2xl border border-line bg-card text-lavender shadow-[0_0_40px_-10px_var(--glow)]">
              <s.icon className="size-5" />
              <span className="absolute -top-2 -right-2 grid size-6 place-items-center rounded-full bg-violet font-mono text-[11px] font-semibold text-white">{i + 1}</span>
            </span>
            <h3 className="font-semibold">{s.title}</h3>
            <p className="mx-auto mt-1.5 max-w-56 text-sm text-fg-2">{s.body}</p>
          </motion.li>
        ))}
      </ol>
    </section>
  )
}

export function RecentHistory({ version, onChange }: { version: number; onChange: () => void }) {
  const toast = useToast()
  const [items, setItems] = useState<HistoryEntry[]>([])
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    setItems(history.list())
    setNow(Date.now())
  }, [version])
  if (!items.length) return null

  const clear = async () => {
    await Promise.all(items.filter((h) => h.expires_at * 1000 > Date.now()).map((h) => deleteBatch(h.id, h.token).catch(() => {})))
    history.clear()
    onChange()
    toast('info', 'History cleared and files deleted from the server.')
  }

  return (
    <section id="history" className="wrap max-w-5xl pt-10 pb-4">
      <div className="rounded-2xl border border-line bg-card/50 p-4 sm:p-5">
        <div className="mb-3 flex items-center justify-between">
          <p className="flex items-center gap-2 text-sm font-semibold"><HistoryIcon className="size-4 text-lavender" /> Recent conversions</p>
          <button onClick={clear} className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-fg-3 transition-colors hover:bg-danger/10 hover:text-danger">
            <Trash2 className="size-3.5" /> Clear history
          </button>
        </div>
        <ul className="divide-y divide-line">
          {items.slice(0, 6).map((h) => {
            const alive = h.expires_at * 1000 > now
            const mins = Math.max(0, Math.round((h.expires_at * 1000 - now) / 60000))
            return (
              <li key={h.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2.5 text-sm">
                <span className="w-24 shrink-0 text-xs text-fg-3">{new Date(h.created_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                <span className="min-w-0 flex-1 truncate">
                  {h.kind === 'convert' ? 'Batch conversion' : h.kind} · {h.completed}/{h.total} files
                  {h.outputs.length === 1 && <span className="text-fg-3"> · {h.outputs[0].filename}</span>}
                  {h.outputs.length > 1 && <span className="text-fg-3"> · {bytes(h.outputs.reduce((n, o) => n + o.size, 0))}</span>}
                </span>
                {alive && h.outputs.length > 0 ? (
                  <span className="flex items-center gap-3">
                    <span className="flex items-center gap-1 text-xs text-fg-3"><Clock className="size-3" /> {mins}m left</span>
                    <a
                      href={h.outputs.length === 1 ? fileUrl(h.id, h.token, h.outputs[0].id) : zipUrl(h.id, h.token)}
                      className="inline-flex items-center gap-1 text-xs font-medium text-lavender hover:underline"
                      download
                    >
                      <Download className="size-3.5" /> {h.outputs.length === 1 ? 'Download' : 'ZIP'}
                    </a>
                  </span>
                ) : (
                  <span className="text-xs text-fg-3">{alive ? 'Nothing to download' : 'Expired, files deleted'}</span>
                )}
              </li>
            )
          })}
        </ul>
        <p className="mt-3 text-xs text-fg-3">History is stored only in this browser. Converted files stay on the server only until they expire.</p>
      </div>
    </section>
  )
}

export function FAQ({ caps }: { caps: Capabilities | null }) {
  const minutes = caps?.limits.retention_minutes ?? 60
  const items = [
    ['Do I need an account?', 'No. Upload, convert and download without signing up. Fair-use rate limits keep the service fast for everyone.'],
    ['How many files can I convert at once?', `Up to ${caps?.limits.max_files ?? 30} files per batch, ${caps?.limits.max_file_mb ?? 100} MB per file and ${caps?.limits.max_batch_mb ?? 500} MB per batch. Files are processed in parallel with a controlled number of workers.`],
    ['What happens to my files?', `Uploads and converted files are kept in isolated temporary storage and deleted automatically after ${minutes} minutes, or right away when you click “Clear Session”. Each file is converted in its own sandboxed process. Download links only work with a secret token issued to your browser.`],
    ['Are my files encrypted?', 'Files travel over HTTPS when Zekrom is deployed with TLS. They are not end-to-end encrypted: the server has to read a file in order to convert it, which is why files are deleted automatically.'],
    ['What if one file fails?', 'The rest of the batch keeps going. You can download every file that succeeded, and each failure comes with a clear reason, such as a corrupted file, a password-protected PDF, or a format mismatch.'],
    ['How accurate are the conversions?', 'Office documents are rendered by LibreOffice, so they keep their layout faithfully. PDF → DOCX rebuilds an editable layout, so complex pages can shift. HTML and EPUB → PDF give a clean but simplified layout. Each route’s limits are listed under Supported Formats.'],
    ['Why can’t I pick a certain output format?', 'Zekrom only shows conversions it can actually perform for the files you uploaded. If a format is missing, that route isn’t supported, so you won’t get a broken file.'],
  ]
  const [open, setOpen] = useState<number | null>(0)
  return (
    <section id="faq" className="wrap max-w-4xl py-28">
      <SectionHeading eyebrow="FAQ" title="Questions, answered" />
      <div className="divide-y divide-line rounded-2xl border border-line bg-card/50">
        {items.map(([q, a], i) => (
          <div key={q}>
            <button
              onClick={() => setOpen(open === i ? null : i)}
              aria-expanded={open === i}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-[15px] font-medium"
            >
              {q}
              <Plus className={`size-4 shrink-0 text-fg-3 transition-transform duration-200 ${open === i ? 'rotate-45 text-lavender' : ''}`} />
            </button>
            <AnimatePresence initial={false}>
              {open === i && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                  <p className="px-5 pb-5 text-sm leading-relaxed text-fg-2">{a}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </section>
  )
}

export function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="relative wrap overflow-hidden py-24 text-center">
        <div className="ambient pointer-events-none absolute inset-0 rotate-180 opacity-70" aria-hidden />
        <p className="relative text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          Whatever your file. Whatever your format.
          <br />
          <span className="text-gradient">Zekrom gets it converted.</span>
        </p>
        <a href="#/" className="btn-primary relative mt-8 inline-flex h-12 items-center gap-2 rounded-xl px-6 font-semibold">
          Start converting <ArrowRight className="size-4" />
        </a>
      </div>
      <div className="wrap flex flex-col items-center justify-between gap-4 border-t border-line py-6 text-sm text-fg-3 sm:flex-row">
        <div className="flex items-center gap-3">
          <Logo className="text-fg" />
          <span className="text-fg-3">v1.0.0</span>
        </div>
        <nav className="flex items-center gap-6" aria-label="Footer">
          <a href="#/tools" className="transition-colors hover:text-fg">Tools</a>
          <a href="#formats" className="transition-colors hover:text-fg">Supported Formats</a>
          <a href="#faq" className="transition-colors hover:text-fg">Privacy</a>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 transition-colors hover:text-fg">
            <GithubMark className="size-4" /> GitHub
          </a>
        </nav>
      </div>
    </footer>
  )
}
