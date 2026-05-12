import { useRef } from 'react'
import MovieCard from './MovieCard'

export default function MovieSection({ title, icon, movies, loading }) {
  const scrollRef = useRef(null)

  const scroll = (dir) => {
    if (scrollRef.current) {
      scrollRef.current.scrollBy({ left: dir * 280, behavior: 'smooth' })
    }
  }

  return (
    <section className="mb-10">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          {icon && (
            <span className="material-symbols-outlined text-primary-container">{icon}</span>
          )}
          <h2 className="font-bold text-xl text-on-surface">{title}</h2>
        </div>
        <div className="flex gap-2">
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

      {loading ? (
        <div className="flex gap-4 overflow-hidden">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex-shrink-0 w-40 rounded-xl overflow-hidden bg-surface-container animate-pulse">
              <div className="aspect-[2/3] bg-surface-bright" />
              <div className="p-3 space-y-2">
                <div className="h-3 bg-surface-bright rounded w-3/4" />
                <div className="h-2 bg-surface-bright rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div
          ref={scrollRef}
          className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          {movies?.map((movie) => (
            <div key={movie.id} className="flex-shrink-0 w-40">
              <MovieCard movie={movie} size="sm" />
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
