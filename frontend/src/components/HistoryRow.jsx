import { Link } from 'react-router-dom'
import { ChevronRight, ImageOff } from 'lucide-react'
import { useState } from 'react'
import VerdictBadge from './VerdictBadge.jsx'
import { withToken } from '../lib/files.js'
import { formatDate, round } from '../lib/format.js'
import { scoreColor } from '../lib/verdict.js'

export function Thumb({ url, alt, className = 'h-12 w-12' }) {
  const [err, setErr] = useState(false)
  if (!url || err) {
    return (
      <div className={`flex shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-400 ${className}`}>
        <ImageOff className="h-5 w-5" aria-hidden />
      </div>
    )
  }
  return <img src={withToken(url)} alt={alt} loading="lazy" onError={() => setErr(true)} className={`shrink-0 rounded-lg object-cover ring-1 ring-slate-200 ${className}`} />
}

export default function HistoryRow({ item }) {
  return (
    <Link
      to={`/analyses/${item.analysis_id}`}
      className="group flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-slate-50 focus-visible:bg-slate-50"
    >
      <Thumb url={item.thumbnail_url} alt={item.original_filename} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-slate-800">{item.original_filename}</p>
        <p className="text-xs text-slate-500">{formatDate(item.created_at)}</p>
      </div>
      <div className="hidden text-right sm:block">
        <span className="font-serif text-lg font-bold tabular-nums" style={{ color: scoreColor(item.authenticity_score) }}>
          {round(item.authenticity_score)}
        </span>
        <span className="text-xs text-slate-400">/100</span>
      </div>
      <VerdictBadge verdict={item.verdict} size="sm" />
      <ChevronRight className="h-4 w-4 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-slate-500" aria-hidden />
    </Link>
  )
}
