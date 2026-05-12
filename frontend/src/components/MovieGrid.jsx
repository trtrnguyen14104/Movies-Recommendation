import MovieCard from './MovieCard'
import { Skeleton } from 'antd'

export default function MovieGrid({ movies, loading, columns = 5 }) {
  const gridCols = {
    3: 'grid-cols-2 sm:grid-cols-3',
    4: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4',
    5: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5',
    6: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6',
  }

  if (loading) {
    return (
      <div className={`grid ${gridCols[columns] || gridCols[5]} gap-4`}>
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="rounded-xl overflow-hidden bg-surface-container animate-pulse">
            <div className="aspect-[2/3] bg-surface-bright" />
            <div className="p-3 space-y-2">
              <div className="h-3 bg-surface-bright rounded w-3/4" />
              <div className="h-2 bg-surface-bright rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (!movies || movies.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-on-surface-variant">
        <span className="material-symbols-outlined text-5xl mb-4 opacity-30">movie_off</span>
        <p className="text-lg font-medium opacity-50">No movies found</p>
      </div>
    )
  }

  return (
    <div className={`grid ${gridCols[columns] || gridCols[5]} gap-4`}>
      {movies.map((movie) => (
        <MovieCard key={movie.id} movie={movie} />
      ))}
    </div>
  )
}
