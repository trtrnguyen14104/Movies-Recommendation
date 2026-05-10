import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Tag, Rate, Spin, message as antMessage } from 'antd'
import { getMovieDetail, recordInteraction } from '../services/api'
import AIReviewSummary from '../components/AIReviewSummary'
import ReviewsList from '../components/ReviewsList'
import MovieCard from '../components/MovieCard'

const PLACEHOLDER_BACK = 'https://via.placeholder.com/1280x720/1e2020/5e3f3b?text=No+Image'

function TrailerModal({ videoKey, onClose }) {
  if (!videoKey) return null
  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl mx-4 aspect-video rounded-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <iframe
          src={`https://www.youtube.com/embed/${videoKey}?autoplay=1`}
          className="w-full h-full"
          allow="autoplay; fullscreen"
          allowFullScreen
          title="Trailer"
        />
        <button
          onClick={onClose}
          className="absolute top-3 right-3 w-9 h-9 rounded-full bg-black/70 flex items-center justify-center hover:bg-black transition-colors"
        >
          <span className="material-symbols-outlined text-white text-lg">close</span>
        </button>
      </div>
    </div>
  )
}

export default function MoviePage() {
  const { id } = useParams()
  const [movie, setMovie] = useState(null)
  const [loading, setLoading] = useState(true)
  const [trailerKey, setTrailerKey] = useState(null)
  const [showTrailer, setShowTrailer] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const [likeStatus, setLikeStatus] = useState(null) // 'like' | 'dislike' | null

  useEffect(() => {
    setLoading(true)
    setMovie(null)
    setLikeStatus(null)
    window.scrollTo(0, 0)
    getMovieDetail(id)
      .then((r) => {
        setMovie(r.data)
        const videos = r.data.videos?.results || []
        const trailer = videos.find(
          (v) => v.type === 'Trailer' && v.site === 'YouTube'
        ) || videos.find((v) => v.site === 'YouTube')
        if (trailer) setTrailerKey(trailer.key)
        // Auto-record view interaction for AI personalization
        recordInteraction(parseInt(id), 'view').catch(() => {})
      })
      .finally(() => setLoading(false))
  }, [id])

  const handleLike = async (action) => {
    if (likeStatus === action) {
      setLikeStatus(null)
      return
    }
    setLikeStatus(action)
    try {
      await recordInteraction(parseInt(id), action)
      antMessage.success(
        action === 'like'
          ? '❤️ Đã thêm vào danh sách yêu thích!'
          : '👎 Đã ghi nhận phản hồi của bạn'
      )
    } catch (e) {
      // silent fail
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen pt-16">
        <div className="text-center">
          <Spin size="large" />
          <p className="text-on-surface-variant mt-4">Đang tải phim...</p>
        </div>
      </div>
    )
  }

  if (!movie) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-16 text-on-surface-variant">
        <span className="material-symbols-outlined text-5xl mb-4 opacity-30">movie_off</span>
        <p className="text-lg">Không tìm thấy phim</p>
        <Link to="/" className="mt-4 text-primary-container hover:underline">Về trang chủ</Link>
      </div>
    )
  }

  const runtime = movie.runtime
    ? `${Math.floor(movie.runtime / 60)}g ${movie.runtime % 60}p`
    : null
  const rating = movie.vote_average?.toFixed(1)
  const year = movie.release_date?.substring(0, 4)
  const cast = movie.credits?.cast?.slice(0, 8) || []
  const director = movie.credits?.crew?.find((c) => c.job === 'Director')
  const similar = movie.similar?.results?.slice(0, 6) || []

  const tabs = [
    { key: 'overview', label: 'Tổng Quan', icon: 'info' },
    { key: 'ai-review', label: 'AI Phân Tích', icon: 'auto_awesome' },
    { key: 'reviews', label: 'Đánh Giá', icon: 'rate_review' },
    { key: 'cast', label: 'Diễn Viên', icon: 'group' },
  ]

  return (
    <>
      {showTrailer && trailerKey && (
        <TrailerModal videoKey={trailerKey} onClose={() => setShowTrailer(false)} />
      )}

      <div className="min-h-screen pt-16 animate-fade-in">
        {/* Backdrop */}
        <div className="relative h-[60vh] min-h-[400px]">
          <img
            src={movie.backdrop_url || PLACEHOLDER_BACK}
            alt={movie.title}
            className="absolute inset-0 w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-surface via-surface/70 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-t from-surface to-transparent" />

          {trailerKey && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <button
                onClick={() => setShowTrailer(true)}
                className="pointer-events-auto w-16 h-16 rounded-full bg-primary-container/90 flex items-center justify-center hover:scale-110 transition-transform shadow-2xl"
              >
                <span className="material-symbols-outlined text-white text-3xl">play_arrow</span>
              </button>
            </div>
          )}
        </div>

        {/* Movie Info */}
        <div className="px-6 md:px-12 max-w-[1440px] mx-auto -mt-32 relative z-10">
          <div className="flex flex-col md:flex-row gap-8 mb-8">
            {/* Poster */}
            <div className="flex-shrink-0">
              <div className="w-40 md:w-56 rounded-2xl overflow-hidden shadow-2xl border border-white/10">
                <img
                  src={movie.poster_url || 'https://via.placeholder.com/300x450/1e2020/5e3f3b?text=No+Poster'}
                  alt={movie.title}
                  className="w-full aspect-[2/3] object-cover"
                />
              </div>
            </div>

            {/* Details */}
            <div className="flex-1 pt-2">
              <div className="flex flex-wrap gap-2 mb-3">
                {movie.genres?.map((g) => (
                  <Link key={g.id} to={`/genres/${g.id}`}>
                    <Tag className="text-xs px-3 py-1 rounded-full cursor-pointer hover:border-primary-container/50 transition-colors">
                      {g.name}
                    </Tag>
                  </Link>
                ))}
              </div>

              <h1 className="text-3xl md:text-5xl font-black tracking-tight text-white mb-2">
                {movie.title}
              </h1>

              {movie.tagline && (
                <p className="text-on-surface-variant italic text-lg mb-4">"{movie.tagline}"</p>
              )}

              <div className="flex flex-wrap items-center gap-4 mb-6">
                <div className="flex items-center gap-1.5">
                  <div className="w-8 h-8 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                    <span className="material-symbols-outlined text-yellow-400 text-sm">star</span>
                  </div>
                  <span className="font-black text-2xl text-yellow-400">{rating}</span>
                  <span className="text-on-surface-variant text-sm">/10</span>
                </div>
                <div className="flex items-center gap-1 text-on-surface-variant text-sm">
                  <span className="material-symbols-outlined text-xs">how_to_vote</span>
                  {movie.vote_count?.toLocaleString()} lượt
                </div>
                {year && (
                  <div className="flex items-center gap-1 text-on-surface-variant text-sm">
                    <span className="material-symbols-outlined text-xs">calendar_today</span>
                    {year}
                  </div>
                )}
                {runtime && (
                  <div className="flex items-center gap-1 text-on-surface-variant text-sm">
                    <span className="material-symbols-outlined text-xs">schedule</span>
                    {runtime}
                  </div>
                )}
              </div>

              {/* Action buttons */}
              <div className="flex gap-3 flex-wrap">
                {trailerKey && (
                  <button
                    onClick={() => setShowTrailer(true)}
                    className="flex items-center gap-2 px-6 py-3 bg-primary-container text-white font-bold rounded-xl hover:bg-red-700 transition-all duration-200 active:scale-95"
                  >
                    <span className="material-symbols-outlined text-lg">play_arrow</span>
                    Xem Trailer
                  </button>
                )}
                <button
                  onClick={() => setActiveTab('ai-review')}
                  className="flex items-center gap-2 px-6 py-3 glass-panel text-primary font-semibold rounded-xl hover:bg-white/10 transition-all duration-200 active:scale-95 border border-primary/20"
                >
                  <span className="material-symbols-outlined text-lg">auto_awesome</span>
                  AI Phân Tích
                </button>

                {/* Like/Dislike for personalization */}
                <div className="flex items-center gap-2 ml-1">
                  <button
                    onClick={() => handleLike('like')}
                    className={`flex items-center gap-1.5 px-4 py-3 rounded-xl border transition-all duration-200 active:scale-95 text-sm font-semibold ${
                      likeStatus === 'like'
                        ? 'bg-green-500/20 border-green-500/50 text-green-400'
                        : 'glass-panel border-white/10 text-on-surface-variant hover:border-green-500/40 hover:text-green-400'
                    }`}
                  >
                    <span className="material-symbols-outlined text-base">
                      {likeStatus === 'like' ? 'favorite' : 'favorite_border'}
                    </span>
                    Yêu thích
                  </button>
                  <button
                    onClick={() => handleLike('dislike')}
                    className={`flex items-center gap-1.5 px-4 py-3 rounded-xl border transition-all duration-200 active:scale-95 text-sm font-semibold ${
                      likeStatus === 'dislike'
                        ? 'bg-red-500/10 border-red-500/30 text-red-400'
                        : 'glass-panel border-white/10 text-on-surface-variant hover:border-red-500/30 hover:text-red-400'
                    }`}
                  >
                    <span className="material-symbols-outlined text-base">thumb_down</span>
                  </button>
                </div>
              </div>

              {/* Personalization hint */}
              <p className="text-xs text-on-surface-variant/50 mt-3 flex items-center gap-1">
                <span className="material-symbols-outlined" style={{ fontSize: 12 }}>psychology</span>
                AI đang ghi nhận sở thích của bạn để cải thiện gợi ý
              </p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mb-8 border-b border-white/10 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold whitespace-nowrap transition-all duration-200 border-b-2 -mb-px ${
                  activeTab === tab.key
                    ? 'text-primary-container border-primary-container'
                    : 'text-on-surface/50 border-transparent hover:text-on-surface hover:bg-white/5'
                }`}
              >
                <span className="material-symbols-outlined text-base">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="mb-12 animate-fade-in" key={activeTab}>
            {activeTab === 'overview' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                  <div>
                    <h3 className="font-bold text-on-surface mb-3 uppercase tracking-widest text-xs text-on-surface-variant">
                      Nội Dung
                    </h3>
                    <p className="text-on-surface/80 leading-relaxed text-base">
                      {movie.overview || 'Chưa có mô tả.'}
                    </p>
                  </div>
                  {director && (
                    <div>
                      <h3 className="font-bold text-on-surface mb-2 uppercase tracking-widest text-xs text-on-surface-variant">
                        Đạo Diễn
                      </h3>
                      <p className="text-on-surface font-semibold">{director.name}</p>
                    </div>
                  )}
                </div>
                <div className="space-y-4">
                  {[
                    { label: 'Ngày Phát Hành', value: movie.release_date, icon: 'calendar_today' },
                    { label: 'Thời Lượng', value: runtime, icon: 'schedule' },
                    { label: 'Trạng Thái', value: movie.status, icon: 'info' },
                    { label: 'Lượt Bình Chọn', value: movie.vote_count?.toLocaleString(), icon: 'how_to_vote' },
                  ].filter((i) => i.value).map((item) => (
                    <div key={item.label} className="flex items-center gap-3 p-3 rounded-lg bg-surface-container-low">
                      <span className="material-symbols-outlined text-on-surface-variant text-base">{item.icon}</span>
                      <div>
                        <div className="text-xs text-on-surface-variant uppercase tracking-wider">{item.label}</div>
                        <div className="text-sm font-semibold text-on-surface">{item.value}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'ai-review' && (
              <div className="max-w-3xl">
                <div className="mb-6">
                  <h2 className="text-2xl font-black text-on-surface mb-2">Phân Tích AI</h2>
                  <p className="text-on-surface-variant">
                    AI phân tích đánh giá từ người dùng TMDB bằng RAG (Retrieval-Augmented Generation)
                    với Gemini để giúp bạn quyết định xem có nên xem phim này không.
                  </p>
                </div>
                <AIReviewSummary movieId={parseInt(id)} movieTitle={movie.title} />
              </div>
            )}

            {activeTab === 'reviews' && (
              <div className="max-w-3xl">
                <ReviewsList movieId={id} />
              </div>
            )}

            {activeTab === 'cast' && (
              <div>
                <h3 className="font-bold text-on-surface mb-5 text-lg">Diễn Viên</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-8">
                  {cast.map((person) => (
                    <div key={person.cast_id || person.id} className="text-center">
                      <div className="w-full aspect-square rounded-xl overflow-hidden bg-surface-container mb-2 border border-white/5">
                        {person.profile_url ? (
                          <img
                            src={person.profile_url}
                            alt={person.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <span className="material-symbols-outlined text-3xl text-on-surface-variant/30">person</span>
                          </div>
                        )}
                      </div>
                      <p className="text-xs font-semibold text-on-surface truncate">{person.name}</p>
                      <p className="text-xs text-on-surface-variant truncate">{person.character}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Similar Movies */}
          {similar.length > 0 && (
            <section className="mb-12">
              <h3 className="font-bold text-xl text-on-surface mb-5 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary-container">recommend</span>
                Phim Tương Tự
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
                {similar.map((m) => (
                  <MovieCard key={m.id} movie={m} size="sm" />
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </>
  )
}


