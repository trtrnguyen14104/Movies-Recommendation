import { useState, useEffect } from 'react'
import { Pagination } from 'antd'
import MovieGrid from '../components/MovieGrid'
import { getTopRatedMovies } from '../services/api'

export default function TopRatedPage() {
  const [movies, setMovies] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    setLoading(true)
    getTopRatedMovies(page)
      .then((r) => {
        setMovies(r.data.results || [])
        setTotal(r.data.total_results || 0)
      })
      .finally(() => setLoading(false))
  }, [page])

  return (
    <div className="min-h-screen pt-20 px-6 md:px-12 max-w-[1440px] mx-auto pb-12">
      <div className="mb-8 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-yellow-500/20 flex items-center justify-center">
          <span className="material-symbols-outlined text-yellow-400">star</span>
        </div>
        <div>
          <h1 className="text-4xl font-black text-on-surface">Đánh Giá Cao</h1>
          <p className="text-on-surface-variant text-sm">The highest rated movies of all time</p>
        </div>
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
