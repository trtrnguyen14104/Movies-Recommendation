import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import Navbar from './components/Navbar'
import HomePage from './pages/HomePage'
import MoviePage from './pages/MoviePage'
import SearchPage from './pages/SearchPage'
import GenresPage from './pages/GenresPage'
import GenreDetailPage from './pages/GenreDetailPage'
import TopRatedPage from './pages/TopRatedPage'
import NowPlayingPage from './pages/NowPlayingPage'

const antdTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#e50914',
    colorBgBase: '#121414',
    colorBgContainer: '#1e2020',
    colorBgElevated: '#1e2020',
    colorBorder: 'rgba(255,255,255,0.1)',
    colorText: '#e2e2e2',
    colorTextSecondary: '#af8782',
    borderRadius: 8,
    fontFamily: 'Inter, system-ui, sans-serif',
  },
}

function Footer() {
  return (
    <footer className="border-t border-white/8 py-8 px-6 md:px-12 text-center">
      <div className="max-w-[1440px] mx-auto">
        <div className="font-black text-primary-container tracking-tighter text-lg mb-2">CINEVIEW</div>
        <p className="text-on-surface-variant text-sm">
          Được hỗ trợ bởi TMDB API · AI Phân Tích bởi Gemini · Vector DB bởi ChromaDB · Xây dựng với React &amp; FastAPI
        </p>
        <p className="text-on-surface-variant/50 text-xs mt-2">
          Sản phẩm này sử dụng TMDB API nhưng không được TMDB chứng nhận hoặc bảo trợ.
        </p>
      </div>
    </footer>
  )
}

export default function App() {
  return (
    <ConfigProvider theme={antdTheme}>
      <BrowserRouter>
        <div className="min-h-screen bg-surface text-on-surface flex flex-col">
          <Navbar />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/movie/:id" element={<MoviePage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/genres" element={<GenresPage />} />
              <Route path="/genres/:genreId" element={<GenreDetailPage />} />
              <Route path="/top-rated" element={<TopRatedPage />} />
              <Route path="/now-playing" element={<NowPlayingPage />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </BrowserRouter>
    </ConfigProvider>
  )
}
