import { Link } from 'react-router-dom'
import { Rate } from 'antd'

const PLACEHOLDER = 'https://via.placeholder.com/300x450/1e2020/5e3f3b?text=No+Poster'

export default function MovieCard({ movie, size = 'md' }) {
  const posterUrl = movie.poster_url || PLACEHOLDER
  const rating = (movie.vote_average / 2).toFixed(1)
  const year = movie.release_date?.substring(0, 4) || ''

  const getRatingColor = (r) => {
    const num = parseFloat(r)
    if (num >= 4) return 'text-green-400'
    if (num >= 3) return 'text-yellow-400'
    return 'text-red-400'
  }

  return (
    <Link to={`/movie/${movie.id}`} className="block group">
      <div className={`movie-card-hover rounded-xl overflow-hidden bg-surface-container relative cursor-pointer ${
        size === 'sm' ? 'w-full' : 'w-full'
      }`}>
        {/* Poster */}
        <div className={`relative overflow-hidden ${size === 'sm' ? 'aspect-[2/3]' : 'aspect-[2/3]'}`}>
          <img
            src={posterUrl}
            alt={movie.title}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
            loading="lazy"
            onError={(e) => { e.target.src = PLACEHOLDER }}
          />

          {/* Gradient overlay */}
          <div className="absolute inset-0 gradient-scrim opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

          {/* Rating Badge */}
          <div className="absolute top-2 right-2">
            <div className={`flex items-center gap-1 px-2 py-1 rounded-full glass-panel text-xs font-bold ${getRatingColor(rating)}`}>
              <span className="material-symbols-outlined text-[12px]" style={{ fontSize: 12 }}>star</span>
              {movie.vote_average?.toFixed(1) || 'N/A'}
            </div>
          </div>

          {/* Hover overlay content */}
          <div className="absolute bottom-0 left-0 right-0 p-3 translate-y-full group-hover:translate-y-0 transition-transform duration-300">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-white text-sm">play_arrow</span>
              </div>
              <span className="text-white text-xs font-semibold truncate">Xem Chi Tiết</span>
            </div>
          </div>
        </div>

        {/* Info */}
        <div className="p-3">
          <h3 className={`font-semibold text-on-surface line-clamp-2 leading-tight ${
            size === 'sm' ? 'text-xs' : 'text-sm'
          }`}>
            {movie.title}
          </h3>
          <div className="flex items-center justify-between mt-1">
            {year && (
              <span className="text-xs text-on-surface-variant">{year}</span>
            )}
            {movie.vote_count > 0 && (
              <span className="text-[10px] text-on-surface-variant">
                {movie.vote_count > 1000
                  ? `${(movie.vote_count / 1000).toFixed(1)}k votes`
                  : `${movie.vote_count} votes`}
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  )
}
