import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  withCredentials: true,
})

// Movies
export const getPopularMovies = (page = 1) => api.get(`/movies/popular?page=${page}`)
export const getTrendingMovies = (window = 'week') => api.get(`/movies/trending?time_window=${window}`)
export const getTopRatedMovies = (page = 1) => api.get(`/movies/top-rated?page=${page}`)
export const getNowPlaying = (page = 1) => api.get(`/movies/now-playing?page=${page}`)
export const getUpcoming = (page = 1) => api.get(`/movies/upcoming?page=${page}`)
export const searchMovies = (q, page = 1) => api.get(`/movies/search?q=${encodeURIComponent(q)}&page=${page}`)
export const getMovieDetail = (id) => api.get(`/movies/${id}`)
export const getMovieVideos = (id) => api.get(`/movies/${id}/videos`)
export const getGenres = () => api.get('/movies/genres')
export const getMoviesByGenre = (genreId, page = 1) => api.get(`/movies/by-genre/${genreId}?page=${page}`)

// AI
export const getAISummary = (movieId) => api.get(`/ai/summary/${movieId}`)
export const getReviews = (movieId, page = 1) => api.get(`/ai/reviews/${movieId}?page=${page}`)
export const reindexMovie = (movieId) => api.post(`/ai/reindex/${movieId}`)

// Recommendations
// genre_scores: chuoi diem genre vd "28:6,12:3,878:2"
// exclude_ids : chuoi movie_id can loai tru vd "272,1726"
export const getRecommendations = (genreScores, excludeIds = '', limit = 12) =>
  api.get(`/recommendations/goi-y?genre_scores=${genreScores}&exclude_ids=${excludeIds}&limit=${limit}`)

export default api
