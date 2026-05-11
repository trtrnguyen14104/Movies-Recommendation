import { useState, useEffect } from 'react'
import { hasInteraction, recordInteraction, removeInteraction } from '../services/interactions'

/**
 * Nut Yeu thich hien thi tren trang chi tiet phim.
 * Bam lan 1: them vao danh sach thich (+3 diem cho genre)
 * Bam lan 2: xoa khoi danh sach thich (-3 diem cho genre)
 *
 * @param {Object} movie - Du lieu phim tu TMDB
 */
export default function LikeButton({ movie }) {
  // Trang thai: user da thich phim nay chua?
  const [liked, setLiked] = useState(false)

  // Khi component load, kiem tra localStorage xem da thich phim nay chua
  useEffect(() => {
    if (movie?.id) {
      setLiked(hasInteraction(movie.id, 'like'))
    }
  }, [movie?.id])

  const handleClick = () => {
    if (liked) {
      // Da thich roi → bo thich → xoa khoi localStorage
      removeInteraction(movie.id, 'like')
      setLiked(false)
    } else {
      // Chua thich → them vao localStorage voi weight=3
      recordInteraction(movie, 'like')
      setLiked(true)
    }
  }

  return (
    <button
      onClick={handleClick}
      className={`flex items-center gap-2 px-5 py-3 rounded-xl border font-semibold
        transition-all duration-200 active:scale-95 ${
        liked
          ? 'bg-red-500/20 border-red-500/50 text-red-400'
          : 'glass-panel border-white/10 text-on-surface-variant hover:border-red-500/40 hover:text-red-400'
      }`}
    >
      <span className="material-symbols-outlined text-base">
        {liked ? 'favorite' : 'favorite_border'}
      </span>
      {liked ? 'Đã thích' : 'Yêu thích'}
    </button>
  )
}
