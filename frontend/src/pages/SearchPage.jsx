import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Input, Pagination } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import MovieGrid from '../components/MovieGrid'
import { searchMovies } from '../services/api'

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [results, setResults] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const query = searchParams.get('q') || ''

  useEffect(() => {
    if (!query) return
    setLoading(true)
    searchMovies(query, page)
      .then((r) => {
        setResults(r.data.results || [])
        setTotal(r.data.total_results || 0)
      })
      .finally(() => setLoading(false))
  }, [query, page])

  const handleSearch = (val) => {
    if (val.trim()) {
      setSearchParams({ q: val.trim() })
      setPage(1)
    }
  }

  return (
    <div className="min-h-screen pt-20 px-6 md:px-12 max-w-[1440px] mx-auto">
      {/* Search bar */}
      <div className="mb-8">
        <h1 className="text-3xl font-black text-on-surface mb-4">Tìm Kiếm Phim</h1>
        <Input
          size="large"
          placeholder="Tìm kiếm phim..."
          defaultValue={query}
          prefix={<SearchOutlined className="text-on-surface-variant" />}
          onPressEnter={(e) => handleSearch(e.target.value)}
          className="max-w-xl"
          style={{
            background: 'rgba(30,32,32,0.9)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '12px',
            color: '#e2e2e2',
          }}
          allowClear
        />
      </div>

      {query && (
        <div className="mb-6">
          <p className="text-on-surface-variant">
            {loading ? 'Đang tìm kiếm...' : `${total.toLocaleString()} kết quả cho "${query}"`}
          </p>
        </div>
      )}

      <MovieGrid movies={results} loading={loading} columns={5} />

      {total > 20 && (
        <div className="flex justify-center mt-8 mb-12">
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
