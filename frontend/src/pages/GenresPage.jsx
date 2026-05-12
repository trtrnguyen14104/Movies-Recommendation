import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getGenres } from '../services/api'

const GENRE_ICONS = {
  Action: 'sports_martial_arts',
  Adventure: 'hiking',
  Animation: 'animation',
  Comedy: 'sentiment_very_satisfied',
  Crime: 'gavel',
  Documentary: 'camera_reel',
  Drama: 'theater_comedy',
  Family: 'family_restroom',
  Fantasy: 'auto_fix_high',
  History: 'history_edu',
  Horror: 'skull',
  Music: 'music_note',
  Mystery: 'search',
  Romance: 'favorite',
  'Science Fiction': 'rocket_launch',
  'TV Movie': 'tv',
  Thriller: 'mystery',
  War: 'military_tech',
  Western: 'landscape',
}

const GENRE_COLORS = [
  'from-red-900/40 to-red-800/10 border-red-800/30 hover:border-red-600/50',
  'from-blue-900/40 to-blue-800/10 border-blue-800/30 hover:border-blue-600/50',
  'from-purple-900/40 to-purple-800/10 border-purple-800/30 hover:border-purple-600/50',
  'from-green-900/40 to-green-800/10 border-green-800/30 hover:border-green-600/50',
  'from-yellow-900/40 to-yellow-800/10 border-yellow-800/30 hover:border-yellow-600/50',
  'from-pink-900/40 to-pink-800/10 border-pink-800/30 hover:border-pink-600/50',
  'from-orange-900/40 to-orange-800/10 border-orange-800/30 hover:border-orange-600/50',
  'from-teal-900/40 to-teal-800/10 border-teal-800/30 hover:border-teal-600/50',
]

export default function GenresPage() {
  const [genres, SetGenres] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getGenres()
      .then((r) => SetGenres(r.data.genres || []))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen pt-20 px-6 md:px-12 max-w-[1440px] mx-auto pb-12">
      <div className="mb-8">
        <h1 className="text-4xl font-black text-on-surface mb-2">Duyệt theo Thể Loại</h1>
        <p className="text-on-surface-variant">Explore movies across all categories</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="h-28 rounded-2xl bg-surface-container animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {genres.map((genre, i) => (
            <Link
              key={genre.id}
              to={`/genres/${genre.id}`}
              className={`group relative p-5 rounded-2xl bg-gradient-to-br border transition-all duration-300 hover:scale-105 hover:shadow-2xl ${
                GENRE_COLORS[i % GENRE_COLORS.length]
              }`}
            >
              <span className="material-symbols-outlined text-3xl text-white/70 group-hover:text-white transition-colors mb-2 block">
                {GENRE_ICONS[genre.name] || 'movie'}
              </span>
              <div className="font-bold text-on-surface group-hover:text-white transition-colors">
                {genre.name}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
