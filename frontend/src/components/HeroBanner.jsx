import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Tag } from 'antd'

export default function HeroBanner({ movies }) {
  const [current, setCurrent] = useState(0)
  const featured = movies?.slice(0, 5) || []

  useEffect(() => {
    if (featured.length === 0) return
    const timer = setInterval(() => {
      setCurrent((c) => (c + 1) % featured.length)
    }, 6000)
    return () => clearInterval(timer)
  }, [featured.length])

  if (!featured.length) {
    return <div className="h-[70vh] bg-surface-container animate-pulse rounded-xl" />
  }

  const movie = featured[current]
  const backdrop = movie.backdrop_url || movie.poster_url

  return (
    <div className="relative h-[75vh] min-h-[500px] rounded-2xl overflow-hidden">
      {/* Background images with crossfade */}
      {featured.map((m, i) => (
        <div
          key={m.id}
          className="absolute inset-0 transition-opacity duration-1000"
          style={{ opacity: i === current ? 1 : 0 }}
        >
          <img
            src={m.backdrop_url || m.poster_url}
            alt={m.title}
            className="w-full h-full object-cover"
          />
        </div>
      ))}

      {/* Gradient overlays */}
      <div className="absolute inset-0 bg-gradient-to-r from-surface via-surface/60 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-surface via-transparent to-transparent" />

      {/* Content */}
      <div className="absolute inset-0 flex items-end pb-12 px-8 md:px-12">
        <div className="max-w-2xl animate-slide-up" key={current}>
          {/* Genres */}
          <div className="flex flex-wrap gap-2 mb-4">
            {movie.genre_ids?.slice(0, 3).map((gid) => (
              <span
                key={gid}
                className="px-3 py-1 rounded-full text-xs font-bold tracking-widest uppercase glass-panel text-primary"
              >
                {gid}
              </span>
            ))}
          </div>

          <h1 className="text-4xl md:text-6xl font-black tracking-tight text-white mb-4 text-shadow-glow leading-tight">
            {movie.title}
          </h1>

          <p className="text-on-surface/70 text-base md:text-lg leading-relaxed mb-6 line-clamp-3">
            {movie.overview}
          </p>

          {/* Meta */}
          <div className="flex items-center gap-4 mb-8">
            <div className="flex items-center gap-1 text-yellow-400 font-bold">
              <span className="material-symbols-outlined text-base">star</span>
              <span>{movie.vote_average?.toFixed(1)}</span>
              <span className="text-on-surface-variant text-sm font-normal">/10</span>
            </div>
            <span className="text-on-surface-variant">•</span>
            <span className="text-on-surface-variant">{movie.release_date?.substring(0, 4)}</span>
            {movie.vote_count && (
              <>
                <span className="text-on-surface-variant">•</span>
                <span className="text-on-surface-variant text-sm">
                  {movie.vote_count.toLocaleString()} đánh giá
                </span>
              </>
            )}
          </div>

          {/* CTA Buttons */}
          <div className="flex gap-3">
            <Link
              to={`/movie/${movie.id}`}
              className="flex items-center gap-2 px-6 py-3 bg-primary-container text-white font-bold rounded-xl hover:bg-red-700 transition-all duration-200 active:scale-95"
            >
              <span className="material-symbols-outlined">play_arrow</span>
              Xem ngay
            </Link>
            <Link
              to={`/movie/${movie.id}`}
              className="flex items-center gap-2 px-6 py-3 glass-panel text-on-surface font-semibold rounded-xl hover:bg-white/15 transition-all duration-200 active:scale-95"
            >
              <span className="material-symbols-outlined">info</span>
              Xem Thêm
            </Link>
          </div>
        </div>
      </div>

      {/* Dots */}
      <div className="absolute bottom-4 right-6 flex gap-2">
        {featured.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrent(i)}
            className={`rounded-full transition-all duration-300 ${
              i === current
                ? 'w-6 h-2 bg-primary-container'
                : 'w-2 h-2 bg-white/30 hover:bg-white/60'
            }`}
          />
        ))}
      </div>
    </div>
  )
}
