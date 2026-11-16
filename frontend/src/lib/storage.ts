/** Per-browser conveniences (history, presets, theme). Every access is guarded: storage may be unavailable. */

export interface HistoryEntry {
  id: string
  token: string
  kind: string
  created_at: number
  expires_at: number
  completed: number
  failed: number
  total: number
  outputs: { id: string; filename: string; size: number }[]
}

export interface Preset {
  id: string
  name: string
  /** Target per input format id ("*" = any format that supports it). */
  map: Record<string, string>
  builtin?: boolean
}

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function write(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* storage full or blocked: non-essential */
  }
}

const HISTORY = 'zekrom-history'
const PRESETS = 'zekrom-presets'

export const history = {
  list: (): HistoryEntry[] => read<HistoryEntry[]>(HISTORY, []),
  add(entry: HistoryEntry) {
    const items = history.list().filter((h) => h.id !== entry.id)
    write(HISTORY, [entry, ...items].slice(0, 20))
  },
  remove(id: string) {
    write(HISTORY, history.list().filter((h) => h.id !== id))
  },
  clear() {
    write(HISTORY, [])
  },
}

export const BUILTIN_PRESETS: Preset[] = [
  { id: 'all-pdf', name: 'Everything → PDF', map: { '*': 'pdf' }, builtin: true },
  { id: 'web-images', name: 'Web-ready images', map: { jpg: 'webp', png: 'webp', bmp: 'webp', tiff: 'webp', gif: 'webp', svg: 'png' }, builtin: true },
  { id: 'sheets-csv', name: 'Spreadsheets → CSV', map: { xlsx: 'csv', xls: 'csv', ods: 'csv', json: 'csv' }, builtin: true },
  { id: 'data-excel', name: 'Data → Excel', map: { csv: 'xlsx', json: 'xlsx', xls: 'xlsx', ods: 'xlsx' }, builtin: true },
  { id: 'editable', name: 'Make editable (→ DOCX)', map: { pdf: 'docx', doc: 'docx', odt: 'docx', rtf: 'docx', txt: 'docx' }, builtin: true },
]

export const presets = {
  custom: (): Preset[] => read<Preset[]>(PRESETS, []),
  save(p: Preset) {
    write(PRESETS, [p, ...presets.custom().filter((x) => x.id !== p.id)].slice(0, 12))
  },
  remove(id: string) {
    write(PRESETS, presets.custom().filter((x) => x.id !== id))
  },
}

export function getTheme(): 'dark' | 'light' {
  try {
    return localStorage.getItem('zekrom-theme') === 'light' ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

export function setTheme(t: 'dark' | 'light') {
  document.documentElement.dataset.theme = t
  try {
    localStorage.setItem('zekrom-theme', t)
  } catch {
    /* ignore */
  }
}
