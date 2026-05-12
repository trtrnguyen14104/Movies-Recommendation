import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Input } from 'antd'
import { SearchOutlined, MenuOutlined, CloseOutlined } from '@ant-design/icons'

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`)
      setSearchOpen(false)
      setQuery('')
    }
  }

  const navLinks = [
    { label: 'Phim', path: '/' },
    { label: 'Thể Loại', path: '/genres' },
    { label: 'Đánh Giá Cao', path: '/top-rated' },
    { label: 'Đang Chiếu', path: '/now-playing' },
  ]

  const isActive = (path) => location.pathname === path

  return (
    <>
      <nav
        className={`fixed top-0 w-full z-50 transition-all duration-300 ${
          scrolled
            ? 'bg-surface-container-lowest/95 backdrop-blur-xl border-b border-white/10 shadow-2xl'
            : 'bg-transparent'
        }`}
      >
        <div className="flex justify-between items-center px-6 md:px-12 py-4 max-w-[1440px] mx-auto">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-container flex items-center justify-center">
              <span className="material-symbols-outlined text-white text-sm">movie</span>
            </div>
            <span className="font-black text-xl tracking-tighter text-primary-container">
              CINEVIEW
            </span>
          </Link>

          {/* Desktop Nav Links */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                  isActive(link.path)
                    ? 'text-primary-container bg-primary-container/10'
                    : 'text-on-surface/60 hover:text-on-surface hover:bg-white/5'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {searchOpen ? (
              <form onSubmit={handleSearch} className="flex items-center gap-2 animate-fade-in">
                <Input
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Tìm kiếm phim..."
                  prefix={<SearchOutlined className="text-on-surface-variant" />}
                  className="w-48 md:w-64 bg-surface-container border-white/20 text-on-surface rounded-lg"
                  style={{ background: 'rgba(30,32,32,0.9)', border: '1px solid rgba(255,255,255,0.15)' }}
                />
                <button
                  type="button"
                  onClick={() => setSearchOpen(false)}
                  className="p-2 rounded-full hover:bg-white/10 text-on-surface-variant transition-colors"
                >
                  <CloseOutlined />
                </button>
              </form>
            ) : (
              <button
                onClick={() => setSearchOpen(true)}
                className="p-2 rounded-full hover:bg-white/10 text-primary-container transition-all duration-200 active:scale-90"
              >
                <span className="material-symbols-outlined">search</span>
              </button>
            )}
            <button
              className="md:hidden p-2 rounded-full hover:bg-white/10 text-primary-container transition-colors"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              {menuOpen ? <CloseOutlined /> : <MenuOutlined />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {menuOpen && (
          <div className="md:hidden bg-surface-container-lowest/98 backdrop-blur-xl border-t border-white/10 px-6 py-4 flex flex-col gap-2 animate-slide-up">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMenuOpen(false)}
                className={`px-4 py-3 rounded-lg text-sm font-semibold transition-colors ${
                  isActive(link.path)
                    ? 'text-primary-container bg-primary-container/10'
                    : 'text-on-surface/70 hover:bg-white/5'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>
        )}
      </nav>
    </>
  )
}
