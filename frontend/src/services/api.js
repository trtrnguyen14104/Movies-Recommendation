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

// Personalized Recommendations
export const getPersonalizedRecommendations = (limit = 10) =>
  api.get(`/recommendations/for-you?limit=${limit}`)
export const recordInteraction = (movieId, action = 'view') =>
  api.post(`/recommendations/interact?movie_id=${movieId}&action=${action}`)
export const getSimilarMovies = (movieId, limit = 8) =>
  api.get(`/recommendations/similar/${movieId}?limit=${limit}`)
export const getUserHistory = () => api.get('/recommendations/history')
export const clearUserHistory = () => api.delete('/recommendations/history')

export default api
