import { useState, useEffect } from 'react'
import { Avatar, Pagination, Spin } from 'antd'
import { UserOutlined } from '@ant-design/icons'
import { getReviews } from '../services/api'

function ReviewCard({ review }) {
  const [expanded, setExpanded] = useState(false)
  const rating = review.author_details?.rating
  const content = review.content || ''
  const truncated = content.length > 400 && !expanded

  const getRatingBg = (r) => {
    if (!r) return ''
    if (r >= 7) return 'bg-green-500/20 text-green-400 border-green-500/30'
    if (r >= 5) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    return 'bg-red-500/20 text-red-400 border-red-500/30'
  }

  return (
    <div className="bg-surface-container-low rounded-xl p-5 border border-white/5 hover:border-white/10 transition-colors">
      <div className="flex items-start justify-between mb-3 gap-3">
        <div className="flex items-center gap-3">
          <Avatar
            src={review.author_details?.avatar_path
              ? `https://image.tmdb.org/t/p/w45${review.author_details.avatar_path}`
              : null}
            icon={<UserOutlined />}
            className="bg-surface-container-high border border-white/10 flex-shrink-0"
          />
          <div>
            <div className="font-semibold text-on-surface text-sm">{review.author}</div>
            <div className="text-xs text-on-surface-variant">
              {new Date(review.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </div>
          </div>
        </div>
        {rating && (
          <div className={`flex items-center gap-1 px-2.5 py-1 rounded-full border text-xs font-bold flex-shrink-0 ${getRatingBg(rating)}`}>
            <span className="material-symbols-outlined text-[12px]">star</span>
            {rating}/10
          </div>
        )}
      </div>

      <p className={`text-on-surface/80 text-sm leading-relaxed ${truncated ? 'line-clamp-3' : ''}`}>
        {content}
      </p>

      {content.length > 400 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2 text-xs text-primary hover:text-primary-container transition-colors font-medium"
        >
          {expanded ? 'Show less' : 'Read more'}
        </button>
      )}
    </div>
  )
}

export default function ReviewsList({ movieId }) {
  const [reviews, setReviews] = useState([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const res = await getReviews(movieId, page)
        setReviews(res.data.results || [])
        setTotal(res.data.total_results || 0)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [movieId, page])

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-bold text-headline-md text-on-surface">
          User Reviews
          {total > 0 && (
            <span className="ml-2 text-sm text-on-surface-variant font-normal">({total} total)</span>
          )}
        </h3>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Spin size="large" />
        </div>
      ) : reviews.length === 0 ? (
        <div className="text-center py-12 text-on-surface-variant">
          <span className="material-symbols-outlined text-4xl block mb-3 opacity-30">rate_review</span>
          <p>No reviews yet</p>
        </div>
      ) : (
        <>
          <div className="space-y-4 mb-6">
            {reviews.map((r) => (
              <ReviewCard key={r.id} review={r} />
            ))}
          </div>
          {total > 20 && (
            <div className="flex justify-center">
              <Pagination
                current={page}
                total={total}
                pageSize={20}
                onChange={setPage}
                showSizeChanger={false}
                className="cineview-pagination"
              />
            </div>
          )}
        </>
      )}
    </div>
  )
}
