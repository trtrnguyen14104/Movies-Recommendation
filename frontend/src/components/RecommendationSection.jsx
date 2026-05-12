import { useState, useEffect } from 'react'
import { buildGenreScoresParam, buildExcludeIdsParam, getInteractions } from '../services/interactions'
import { getRecommendations } from '../services/api'
import MovieCard from './MovieCard'

// Bang ten genre de hien thi "Vi ban thich: Action, Adventure..."
const GENRE_NAMES = {
  28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy',
  80: 'Crime', 99: 'Documentary', 18: 'Drama', 10751: 'Family',
  14: 'Fantasy', 36: 'History', 27: 'Horror', 10402: 'Music',
  9648: 'Mystery', 10749: 'Romance', 878: 'Sci-Fi', 53: 'Thriller',
  10752: 'War', 37: 'Western',
}

export default function RecommendationSection() {
  const [movies, setMovies] = useState([])
  const [loading, setLoading] = useState(true)
  const [topGenreNames, setTopGenreNames] = useState([])
  const [hasHistory, setHasHistory] = useState(false)

  useEffect(() => {
    const interactions = getInteractions()

    // Neu chua co tuong tac nao → khong hien thi section nay
    if (interactions.length === 0) {
      setLoading(false)
      return
    }

    setHasHistory(true)

    // Tinh chuoi diem genre va danh sach phim can loai tru
    const genreScores = buildGenreScoresParam()
    const excludeIds = buildExcludeIdsParam()

    if (!genreScores) {
      setLoading(false)
      return
    }

    // Lay ten cua top genre de hien thi tieu de
    const topIds = genreScores.split(',').slice(0, 3).map((s) => s.split(':')[0])
    setTopGenreNames(topIds.map((id) => GENRE_NAMES[id] || id).filter(Boolean))

    // Goi API backend
    getRecommendations(genreScores, excludeIds, 12)
      .then((r) => setMovies(r.data.results || []))
      .catch(() => setMovies([]))
      .finally(() => setLoading(false))
  }, [])

  // Chua co lich su tuong tac → khong hien thi gi ca
  if (!hasHistory) return null

  return (
    <section className="mb-10">
      {/* Tieu de section */}
      <div className="flex items-center gap-3 mb-5">
        <span className="material-symbols-outlined text-2xl text-red-400">favorite</span>
        <div>
          <h2 className="font-bold text-xl text-on-surface">Gợi ý cho bạn</h2>
          {topGenreNames.length > 0 && (
            <p className="text-xs text-on-surface-variant mt-0.5">
              Vì bạn thích: {topGenreNames.join(', ')}
            </p>
          )}
        </div>
      </div>

      {/* Hien thi skeleton loading hoac danh sach phim */}
      {loading ? (
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
      ) : movies.length > 0 ? (
        <div
          className="flex gap-4 overflow-x-auto pb-4"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          {movies.map((movie) => (
            <div key={movie.id} className="flex-shrink-0 w-40">
              <MovieCard movie={movie} size="sm" />
            </div>
          ))}
        </div>
      ) : null}
    </section>
  )
}
