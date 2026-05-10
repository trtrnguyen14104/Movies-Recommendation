import { useState, useEffect } from 'react'
import { Pagination } from 'antd'
import HeroBanner from '../components/HeroBanner'
import MovieSection from '../components/MovieSection'
import MovieGrid from '../components/MovieGrid'
import PersonalizedSection from '../components/PersonalizedSection'
import { getTrendingMovies, getPopularMovies, getTopRatedMovies, getNowPlaying } from '../services/api'

export default function HomePage() {
  const [trending, setTrending] = useState([])
  const [popular, setPopular] = useState([])
  const [topRated, setTopRated] = useState([])
  const [nowPlaying, setNowPlaying] = useState([])
  const [loadingTrending, setLoadingTrending] = useState(true)
  const [loadingPopular, setLoadingPopular] = useState(true)
  const [loadingTopRated, setLoadingTopRated] = useState(true)
  const [loadingNowPlaying, setLoadingNowPlaying] = useState(true)
  const [popularPage, setPopularPage] = useState(1)
  const [popularTotal, setPopularTotal] = useState(0)

  useEffect(() => {
    getTrendingMovies('week')
      .then((r) => setTrending(r.data.results || []))
      .finally(() => setLoadingTrending(false))

    getTopRatedMovies()
      .then((r) => setTopRated(r.data.results || []))
      .finally(() => setLoadingTopRated(false))

    getNowPlaying()
      .then((r) => setNowPlaying(r.data.results || []))
      .finally(() => setLoadingNowPlaying(false))
  }, [])

  useEffect(() => {
    setLoadingPopular(true)
    getPopularMovies(popularPage)
      .then((r) => {
        setPopular(r.data.results || [])
        setPopularTotal(r.data.total_results || 0)
      })
      .finally(() => setLoadingPopular(false))
  }, [popularPage])

  return (
    <div className="min-h-screen pt-16">
      {/* Hero */}
      <div className="px-6 md:px-12 pt-6 pb-10 max-w-[1440px] mx-auto">
        <HeroBanner movies={trending} />
      </div>

      {/* Sections */}
      <div className="px-6 md:px-12 max-w-[1440px] mx-auto">

        {/* AI Personalized Recommendations */}
        <PersonalizedSection />

        <MovieSection
          title="Đang Chiếu"
          icon="theaters"
          movies={nowPlaying}
          loading={loadingNowPlaying}
        />

        <MovieSection
          title="Xu Hướng Tuần Này"
          icon="trending_up"
          movies={trending}
          loading={loadingTrending}
        />

        <MovieSection
          title="Được Đánh Giá Cao"
          icon="star"
          movies={topRated}
          loading={loadingTopRated}
        />

        {/* Popular movies with pagination */}
        <section className="mb-10">
          <div className="flex items-center gap-2 mb-5">
            <span className="material-symbols-outlined text-primary-container">local_fire_department</span>
            <h2 className="font-bold text-xl text-on-surface">Phim Phổ Biến</h2>
          </div>
          <MovieGrid movies={popular} loading={loadingPopular} columns={5} />
          {popularTotal > 0 && (
            <div className="flex justify-center mt-8">
              <Pagination
                current={popularPage}
                total={Math.min(popularTotal, 10000)}
                pageSize={20}
                onChange={setPopularPage}
                showSizeChanger={false}
              />
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
