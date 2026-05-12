/**
 * Quan ly lich su tuong tac cua user voi cac phim.
 * Du lieu luu trong localStorage cua trinh duyet.
 *
 * He thong diem:
 *   like    = +3 diem (user bam nut Yeu thich)
 *   trailer = +2 diem (user bam xem trailer)
 *   view    = +1 diem (user bam vao trang chi tiet phim)
 */

const STORAGE_KEY = 'cineview_interactions'

// Trong so tuong ung voi tung hanh dong
const WEIGHTS = {
  like: 3,
  trailer: 2,
  view: 1,
}

/**
 * Doc toan bo danh sach tuong tac tu localStorage.
 * Tra ve mang rong neu chua co du lieu hoac bi loi.
 */
export function getInteractions() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

/**
 * Luu mot tuong tac moi vao localStorage.
 *
 * @param {Object} movie  - Doi tuong phim tu TMDB (can co id, title, genres, genre_ids)
 * @param {string} action - Hanh dong: 'like' | 'trailer' | 'view'
 *
 * Quy tac:
 *   - Moi cap (movie_id + action) chi luu 1 lan
 *   - Vi du: bam xem trailer 5 lan chi tinh 1 lan +2 diem
 */
export function recordInteraction(movie, action) {
  const weight = WEIGHTS[action]
  if (!weight) return // Bo qua action khong hop le

  const interactions = getInteractions()

  // Kiem tra xem cap (movie_id + action) nay da ton tai chua
  const alreadyExists = interactions.some(
    (i) => i.movie_id === movie.id && i.action === action
  )
  if (alreadyExists) return // Da ghi nhan roi, bo qua

  // Lay danh sach genre_ids cua phim
  // TMDB tra ve 2 dang:
  //   - Trang danh sach: genre_ids = [28, 12, 53]
  //   - Trang chi tiet : genres = [{id:28, name:"Action"}, ...]
  // Nen lay ca hai truong hop
  const genreIds =
    movie.genre_ids ||
    (movie.genres || []).map((g) => g.id) ||
    []

  // Them tuong tac moi vao dau mang (moi nhat len truoc)
  interactions.unshift({
    movie_id: movie.id,
    title: movie.title,
    genre_ids: genreIds,
    action: action,   // 'like' | 'trailer' | 'view'
    weight: weight,   // 3 | 2 | 1
  })

  // Giu toi da 100 tuong tac gan nhat, tranh day localStorage
  const trimmed = interactions.slice(0, 100)

  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed))
}

/**
 * Xoa mot tuong tac khi user bo thich.
 *
 * @param {number} movieId - ID cua phim can xoa
 * @param {string} action  - Hanh dong can xoa ('like' | 'trailer' | 'view')
 */
export function removeInteraction(movieId, action) {
  const interactions = getInteractions().filter(
    (i) => !(i.movie_id === movieId && i.action === action)
  )
  localStorage.setItem(STORAGE_KEY, JSON.stringify(interactions))
}

/**
 * Kiem tra xem user da thuc hien hanh dong nao do voi phim chua.
 *
 * @param {number} movieId - ID cua phim
 * @param {string} action  - Hanh dong can kiem tra
 * @returns {boolean}
 */
export function hasInteraction(movieId, action) {
  return getInteractions().some(
    (i) => i.movie_id === movieId && i.action === action
  )
}

/**
 * Tinh diem tung genre dua tren lich su tuong tac.
 *
 * Cach tinh:
 *   Moi tuong tac, lay tung genre_id cua phim do
 *   va cong them "weight" diem vao genre do.
 *
 * Vi du:
 *   Batman  liked   (28,12)  weight=3 → 28:+3, 12:+3
 *   Avengers trailer (28,878) weight=2 → 28:+2, 878:+2
 *   Ket qua: { "28": 5, "12": 3, "878": 2 }
 *
 * @returns {Object} - { "28": 5, "12": 3, "878": 2, ... }
 */
export function calcGenreScores() {
  const interactions = getInteractions()
  const scores = {}

  for (const interaction of interactions) {
    for (const genreId of interaction.genre_ids) {
      const key = String(genreId)
      scores[key] = (scores[key] || 0) + interaction.weight
    }
  }

  return scores
}

/**
 * Chuyen dict diem genre thanh chuoi de gui len API.
 *
 * @returns {string} - "28:5,12:3,878:2" hoac "" neu chua co du lieu
 *
 * Vi du:
 *   Input:  { "28": 5, "12": 3, "878": 2 }
 *   Output: "28:5,12:3,878:2"
 */
export function buildGenreScoresParam() {
  const scores = calcGenreScores()
  return Object.entries(scores)
    .filter(([, score]) => score > 0)
    .sort(([, a], [, b]) => b - a) // Sap xep giam dan
    .map(([id, score]) => `${id}:${score}`)
    .join(',')
}

/**
 * Lay danh sach movie_id ma user da tuong tac (de loai tru khoi goi y).
 *
 * @returns {string} - "272,1726,76338" hoac ""
 */
export function buildExcludeIdsParam() {
  const interactions = getInteractions()
  const ids = [...new Set(interactions.map((i) => i.movie_id))]
  return ids.join(',')
}

/**
 * Xoa toan bo lich su tuong tac.
 */
export function clearInteractions() {
  localStorage.removeItem(STORAGE_KEY)
}
