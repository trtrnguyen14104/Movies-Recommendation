import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Pagination } from 'antd'
import MovieGrid from '../components/MovieGrid'
import { getMoviesByGenre, getGenres } from '../services/api'

export default function GenreDetailPage() {
  const { genreId } = useParams()
  const navigate = useNavigate()
  const [movies, setMovies] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [genreName, setGenreName] = useState('')

  useEffect(() => {
    getGenres().then((r) => {
      const genre = r.data.genres?.find((g) => g.id === parseInt(genreId))
      if (genre) setGenreName(genre.name)
    })
  }, [genreId])

  useEffect(() => {
    setLoading(true)
    getMoviesByGenre(genreId, page)
      .then((r) => {
        setMovies(r.data.results || [])
        setTotal(r.data.total_results || 0)
      })
      .finally(() => setLoading(false))
  }, [genreId, page])

  return (
    <div className="min-h-screen pt-20 px-6 md:px-12 max-w-[1440px] mx-auto pb-12">
      <div className="mb-8">
        <button
          onClick={() => navigate('/genres')}
          className="flex items-center gap-1 text-on-surface-variant hover:text-on-surface transition-colors mb-4 text-sm"
        >
          <span className="material-symbols-outlined text-base">arrow_back</span>
          All Genres
        </button>
        <h1 className="text-4xl font-black text-on-surface mb-1">{genreName || 'Genre'}</h1>
        {total > 0 && (
          <p className="text-on-surface-variant">{total.toLocaleString()} movies</p>
        )}
      </div>

      <MovieGrid movies={movies} loading={loading} columns={5} />

      {total > 20 && (
        <div className="flex justify-center mt-8">
          <Pagination
            current={page}
            total={Math.min(total, 10000)}
            pageSize={20}
            onChange={setPage}
            showSizeChanger={false}
          />
        </div>
      )}
    </div>
  )
}
