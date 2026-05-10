import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Tooltip } from 'antd'
import { getPersonalizedRecommendations } from '../services/api'
import MovieCard from './MovieCard'

export default function PersonalizedSection() {
  const [movies, setMovies] = useState([])
  const [loading, setLoading] = useState(true)
  const [personalized, setPersonalized] = useState(false)
  const [message, setMessage] = useState('')
  const [interactionCount, setInteractionCount] = useState(0)
  const scrollRef = useRef(null)

  useEffect(() => {
    setLoading(true)
    getPersonalizedRecommendations(12)
      .then((r) => {
        setMovies(r.data.results || [])
        setPersonalized(r.data.personalized || false)
        setMessage(r.data.message || '')
        setInteractionCount(r.data.interaction_count || 0)
      })
      .catch(() => {
        setMovies([])
      })
      .finally(() => setLoading(false))
  }, [])

  const scroll = (dir) => {
    if (scrollRef.current) {
      scrollRef.current.scrollBy({ left: dir * 280, behavior: 'smooth' })
    }
  }

  if (!loading && movies.length === 0) return null

  return (
    <section className="mb-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="relative">
            <span className="material-symbols-outlined text-2xl text-primary-container">
              auto_awesome
            </span>
            {personalized && (
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-green-400 border-2 border-surface animate-pulse" />
            )}
          </div>
          <div>
            <h2 className="font-bold text-xl text-on-surface">
              Các phim bạn có thể thích
            </h2>
            <p className="text-xs text-on-surface-variant mt-0.5 flex items-center gap-1.5">
              {personalized ? (
                <>
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-400" />
                  <span>{message} · {interactionCount} tương tác đã ghi nhận</span>
                </>
              ) : (
                <>
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400" />
                  <span>Xem phim để cá nhân hóa gợi ý của bạn</span>
                </>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* AI badge */}
          <Tooltip title="Được hỗ trợ bởi AI · Vector embeddings ChromaDB">
            <div className="flex items-center gap-1 px-2.5 py-1 rounded-full border border-primary-container/30 bg-primary-container/10">
              <span className="material-symbols-outlined text-primary-container" style={{ fontSize: 14 }}>
                psychology
              </span>
              <span className="text-xs font-semibold text-primary-container">AI</span>
            </div>
          </Tooltip>

          {/* Scroll buttons */}
          <button
            onClick={() => scroll(-1)}
            className="w-8 h-8 rounded-full glass-panel flex items-center justify-center hover:bg-white/15 transition-colors"
          >
            <span className="material-symbols-outlined text-sm text-on-surface">chevron_left</span>
          </button>
          <button
            onClick={() => scroll(1)}
            className="w-8 h-8 rounded-full glass-panel flex items-center justify-center hover:bg-white/15 transition-colors"
          >
            <span className="material-symbols-outlined text-sm text-on-surface">chevron_right</span>
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div>
          {/* Shimmer skeleton */}
          <div className="flex gap-4 overflow-hidden">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="flex-shrink-0 w-40 rounded-xl overflow-hidden bg-surface-container animate-pulse"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <div className="aspect-[2/3] bg-surface-bright" />
                <div className="p-3 space-y-2">
                  <div className="h-3 bg-surface-bright rounded w-3/4" />
                  <div className="h-2 bg-surface-bright rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center gap-2 text-on-surface-variant text-xs">
            <span className="material-symbols-outlined animate-spin" style={{ fontSize: 14 }}>
              refresh
            </span>
            <span>Đang phân tích sở thích của bạn...</span>
          </div>
        </div>
      ) : (
        <>
          <div
            ref={scrollRef}
            className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide"
            style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
          >
            {movies.map((movie, idx) => (
              <div key={movie.id} className="flex-shrink-0 w-40 relative">
                {/* Match score indicator for personalized results */}
                {personalized && idx < 3 && (
                  <div className="absolute top-2 left-2 z-10">
                    <div className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-primary-container/90 backdrop-blur-sm">
                      <span className="material-symbols-outlined text-white" style={{ fontSize: 10 }}>
                        favorite
                      </span>
                      <span className="text-[10px] font-bold text-white">
                        {idx === 0 ? 'Tốt nhất' : 'Phù hợp'}
                      </span>
                    </div>
                  </div>
                )}
                <MovieCard movie={movie} size="sm" />
              </div>
            ))}
          </div>

          {/* Info footer */}
          {!personalized && (
            <div className="mt-3 p-3 rounded-xl border border-amber-400/20 bg-amber-400/5 flex items-start gap-3">
              <span className="material-symbols-outlined text-amber-400 flex-shrink-0" style={{ fontSize: 18 }}>
                tips_and_updates
              </span>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                <span className="font-semibold text-on-surface">Mẹo:</span>{' '}
                Nhấp vào các phim để xem chi tiết. Hệ thống AI sẽ ghi nhớ sở thích của bạn
                và cải thiện gợi ý theo thời gian.
              </p>
            </div>
          )}
        </>
      )}
    </section>
  )
}
