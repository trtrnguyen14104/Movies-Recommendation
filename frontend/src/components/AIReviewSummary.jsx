import { useState } from 'react'
import { Spin, Alert, Tooltip, Progress } from 'antd'
import { RadialBarChart, RadialBar, ResponsiveContainer, PieChart, Pie, Cell, Tooltip as ReTooltip } from 'recharts'
import { getAISummary } from '../services/api'

const VERDICT_CONFIG = {
  'KHUYẾN NGHỊ': {
    icon: 'thumb_up',
    label: 'KHUYẾN NGHỊED',
    color: '#22c55e',
    bg: 'bg-green-500/15',
    border: 'border-green-500/30',
    text: 'text-green-400',
    description: 'Critics and audiences agree — this film is worth your time.',
  },
  'BỎ QUA': {
    icon: 'thumb_down',
    label: 'BỎ QUA IT',
    color: '#ef4444',
    bg: 'bg-red-600/15',
    border: 'border-red-500/30',
    text: 'text-red-400',
    description: 'Most reviewers found this film disappointing.',
  },
  'HỖN HỢP': {
    icon: 'thumbs_up_down',
    label: 'HỖN HỢP VERDICT',
    color: '#eab308',
    bg: 'bg-yellow-500/15',
    border: 'border-yellow-500/30',
    text: 'text-yellow-400',
    description: 'Opinions are divided — it depends on your taste.',
  },
}

const SENTIMENT_COLORS = {
  positive: '#22c55e',
  neutral: '#a7c8ff',
  negative: '#ef4444',
}

function SentimentDonut({ sentiment }) {
  const data = [
    { name: 'Tích Cực', value: sentiment.positive_count, color: SENTIMENT_COLORS.positive },
    { name: 'Trung Lập', value: sentiment.neutral_count, color: SENTIMENT_COLORS.neutral },
    { name: 'Tiêu Cực', value: sentiment.negative_count, color: SENTIMENT_COLORS.negative },
  ].filter((d) => d.value > 0)

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-36 h-36">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={42}
              outerRadius={62}
              paddingAngle={2}
              dataKey="value"
              strokeWidth={0}
            >
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <ReTooltip
              contentStyle={{
                background: '#1e2020',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
                color: '#e2e2e2',
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-lg font-black text-green-400">{sentiment.positive_pct}%</span>
          <span className="text-[10px] text-on-surface-variant uppercase tracking-wider">Tích Cực</span>
        </div>
      </div>
      {/* Legend */}
      <div className="flex gap-3 mt-2">
        {data.map((d) => (
          <div key={d.name} className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full" style={{ background: d.color }} />
            <span className="text-xs text-on-surface-variant">{d.name}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ConfidenceMeter({ score }) {
  const pct = Math.round(score * 100)
  const color = pct >= 70 ? '#22c55e' : pct >= 40 ? '#eab308' : '#ef4444'
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-on-surface-variant uppercase tracking-wider whitespace-nowrap">
        AI Độ Tin Cậy
      </span>
      <div className="flex-1">
        <Progress
          percent={pct}
          showInfo={false}
          size="small"
          strokeColor={color}
          trailColor="rgba(255,255,255,0.1)"
        />
      </div>
      <span className="text-xs font-bold" style={{ color }}>{pct}%</span>
    </div>
  )
}

export default function AIReviewSummary({ movieId, movieTitle }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(false)

  const fetchSummary = async () => {
    if (data) { setExpanded(true); return }
    setLoading(true)
    setError(null)
    try {
      const res = await getAISummary(movieId)
      setData(res.data)
      setExpanded(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate AI summary. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const verdict = data ? VERDICT_CONFIG[data.verdict] || VERDICT_CONFIG['HỖN HỢP'] : null

  return (
    <div className="rounded-2xl bg-surface-container border border-white/8 overflow-hidden">
      {/* Header / Trigger */}
      <button
        onClick={() => expanded ? setExpanded(false) : fetchSummary()}
        className="w-full flex items-center justify-between p-5 hover:bg-white/5 transition-colors group"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary-container/20 border border-primary-container/30 flex items-center justify-center">
            <span className="material-symbols-outlined text-primary-container text-xl">auto_awesome</span>
          </div>
          <div className="text-left">
            <div className="font-bold text-on-surface text-sm">Tóm Tắt AI</div>
            <div className="text-xs text-on-surface-variant">
              Powered by Gemini AI · RAG-enhanced analysis
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!data && !loading && (
            <span className="text-xs text-primary px-3 py-1 rounded-full bg-primary-container/10 border border-primary-container/20 font-semibold">
              Generate
            </span>
          )}
          {loading && <Spin size="small" />}
          {data && (
            <span
              className={`text-xs font-bold px-3 py-1 rounded-full border ${verdict.bg} ${verdict.border} ${verdict.text}`}
            >
              {verdict.label}
            </span>
          )}
          <span className="material-symbols-outlined text-on-surface-variant transition-transform duration-200"
            style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
          >
            expand_more
          </span>
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-white/8 animate-slide-up">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12 gap-4">
              <Spin size="large" />
              <div className="text-center">
                <p className="text-on-surface font-medium">Đang phân tích đánh giá bằng AI...</p>
                <p className="text-on-surface-variant text-sm mt-1">
                  Fetching and indexing reviews via RAG pipeline
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="p-5">
              <Alert
                message={error}
                type="error"
                showIcon
                action={
                  <button
                    onClick={fetchSummary}
                    className="text-xs text-primary-container underline"
                  >
                    Retry
                  </button>
                }
              />
            </div>
          )}

          {data && verdict && (
            <div className="p-5 space-y-6">
              {/* Verdict Banner */}
              <div className={`rounded-xl p-4 ${verdict.bg} border ${verdict.border} flex items-start gap-4`}>
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0`}
                  style={{ background: `${verdict.color}20` }}
                >
                  <span
                    className="material-symbols-outlined text-2xl"
                    style={{ color: verdict.color }}
                  >
                    {verdict.icon}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className={`font-black text-lg tracking-tight ${verdict.text}`}>
                    {verdict.label}
                  </div>
                  <p className="text-on-surface-variant text-sm mt-1">{data.verdict_reason}</p>
                  <div className="mt-3">
                    <ConfidenceMeter score={data.confidence_score} />
                  </div>
                </div>
              </div>

              {/* Summary text */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <span className="material-symbols-outlined text-tertiary text-base">summarize</span>
                  <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant">
                    AI Summary
                  </h4>
                </div>
                <p className="text-on-surface leading-relaxed text-sm">{data.summary}</p>
              </div>

              {/* Sentiment + Stats */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Donut Chart */}
                <div className="bg-surface-container-low rounded-xl p-4">
                  <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-4 flex items-center gap-2">
                    <span className="material-symbols-outlined text-base">sentiment_satisfied</span>
                    Sentiment
                  </h4>
                  <div className="flex items-center justify-center">
                    <SentimentDonut sentiment={data.sentiment} />
                  </div>
                  <div className="mt-4 text-center text-xs text-on-surface-variant">
                    Based on {data.total_reviews_analyzed} reviews
                  </div>
                </div>

                {/* Sentiment Bars */}
                <div className="bg-surface-container-low rounded-xl p-4">
                  <h4 className="font-bold text-sm uppercase tracking-widest text-on-surface-variant mb-4 flex items-center gap-2">
                    <span className="material-symbols-outlined text-base">bar_chart</span>
                    Breakdown
                  </h4>
                  <div className="space-y-3">
                    {[
                      { label: 'Tích Cực', pct: data.sentiment.positive_pct, count: data.sentiment.positive_count, color: SENTIMENT_COLORS.positive },
                      { label: 'Trung Lập', pct: data.sentiment.neutral_pct, count: data.sentiment.neutral_count, color: SENTIMENT_COLORS.neutral },
                      { label: 'Tiêu Cực', pct: data.sentiment.negative_pct, count: data.sentiment.negative_count, color: SENTIMENT_COLORS.negative },
                    ].map((item) => (
                      <div key={item.label}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-on-surface-variant font-medium">{item.label}</span>
                          <span className="font-bold" style={{ color: item.color }}>
                            {item.pct}% <span className="text-on-surface-variant font-normal">({item.count})</span>
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-1000"
                            style={{ width: `${item.pct}%`, background: item.color }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Pros & Cons */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Tích Cựcs */}
                <div className="bg-green-500/5 border border-green-500/15 rounded-xl p-4">
                  <h4 className="font-bold text-sm text-green-400 mb-3 flex items-center gap-2">
                    <span className="material-symbols-outlined text-base">add_circle</span>
                    What Works
                  </h4>
                  <ul className="space-y-2">
                    {data.key_positives.map((p, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-on-surface/80">
                        <span className="text-green-400 mt-0.5 flex-shrink-0">✓</span>
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Tiêu Cựcs */}
                <div className="bg-red-500/5 border border-red-500/15 rounded-xl p-4">
                  <h4 className="font-bold text-sm text-red-400 mb-3 flex items-center gap-2">
                    <span className="material-symbols-outlined text-base">remove_circle</span>
                    What Doesn't
                  </h4>
                  <ul className="space-y-2">
                    {data.key_negatives.length > 0 ? (
                      data.key_negatives.map((n, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-on-surface/80">
                          <span className="text-red-400 mt-0.5 flex-shrink-0">✗</span>
                          {n}
                        </li>
                      ))
                    ) : (
                      <li className="text-sm text-on-surface-variant italic">Không có điểm tiêu cực đáng kể</li>
                    )}
                  </ul>
                </div>
              </div>

              {/* Footer note */}
              <div className="flex items-center gap-2 pt-2 border-t border-white/8">
                <span className="material-symbols-outlined text-xs text-on-surface-variant">info</span>
                <p className="text-xs text-on-surface-variant">
                  Summary generated by Gemini AI from {data.total_reviews_analyzed} TMDB reviews using RAG retrieval.
                  Results may not reflect all opinions.
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
