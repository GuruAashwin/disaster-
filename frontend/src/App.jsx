import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { isLoggedIn, getRole, getUsername, clearSession } from './api';
import { Login } from './components/Login';
import { AddFoundPerson } from './components/AddFoundPerson';
import { MissingPersonForm } from './components/MissingPersonForm';
import { MatchReview } from './components/MatchReview';
import { VideoClothingSearch } from './components/VideoClothingSearch';
import { FloodMap } from './components/FloodMap';

function RequireAuth({ children, allowedRoles }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  const role = getRole();
  if (allowedRoles && !allowedRoles.includes(role)) return <Navigate to="/" replace />;
  return children;
}

const ROLE_LABEL = { rescuer: 'Rescuer', police: 'Police Admin', admin: 'Admin', public: 'Family' };
const ROLE_COLOR = { rescuer: 'badge-primary', police: 'badge-navy', admin: 'badge-navy', public: 'badge-warning' };

function NavBar({ onLogout, onFloodMapOpen }) {
  const role     = getRole();
  const username = getUsername();
  const isPolice = role === 'police' || role === 'admin';

  const linkStyle = ({ isActive }) => ({
    textDecoration: 'none',
    fontWeight: 700,
    fontSize: '0.95rem',
    padding: '8px 16px',
    borderRadius: '4px',
    color: isActive ? '#001a4d' : 'rgba(255,255,255,0.85)',
    background: isActive ? '#ffffff' : 'transparent',
    border: isActive ? '1px solid #001a4d' : '1px solid transparent',
    transition: 'all 0.2s ease',
    whiteSpace: 'nowrap',
  });

  const floodMapButtonStyle = {
    textDecoration: 'none',
    fontWeight: 700,
    fontSize: '0.95rem',
    padding: '8px 16px',
    borderRadius: '4px',
    color: 'rgba(255,255,255,0.85)',
    background: 'transparent',
    border: '1px solid transparent',
    transition: 'all 0.2s ease',
    whiteSpace: 'nowrap',
    cursor: 'pointer',
    display: 'inline-block',
    appearance: 'none',
  };

  return (
    <header style={{
      background: '#001a4d',
      borderBottom: '3px solid #000d26',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      width: '100%',
      overflowX: 'hidden',
    }}>
      <div style={{ 
        padding: '0.75rem 1rem',
        display: 'grid',
        gridTemplateColumns: 'auto 1fr auto',
        alignItems: 'center',
        gap: '1.5rem',
        minHeight: '70px',
        maxWidth: '100%',
      }}>
        {/* Official Emblem & Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0 }}>
          {/* Emblem Circle */}
          <div style={{ 
            width: '46px', 
            height: '46px', 
            background: 'linear-gradient(135deg, #ffffff, #e6ecf5)', 
            borderRadius: '50%', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            fontSize: '1.6rem',
            flexShrink: 0,
            border: '2px solid #ffffff',
            boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
            fontWeight: 'bold',
          }}>
            🛡️
          </div>
          {/* Text & Subtitle */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ 
              fontWeight: 800, 
              fontSize: '1.05rem', 
              color: 'white', 
              lineHeight: 1.2,
              fontFamily: "'Lora', serif",
            }}>
              DISASTER RESPONSE
            </div>
            <div style={{ 
              fontSize: '0.7rem', 
              color: 'rgba(255,255,255,0.85)', 
              letterSpacing: '0.08em', 
              textTransform: 'uppercase', 
              fontWeight: 700,
              fontFamily: "'Roboto', sans-serif",
            }}>
              Family Reunification System
            </div>
          </div>
        </div>

        {/* Nav links - centered and expanded */}
        <nav style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'wrap', alignItems: 'center' }}>
          <NavLink to="/found" style={linkStyle}>Found Persons</NavLink>
          <NavLink to="/missing" style={linkStyle}>Missing Persons</NavLink>
          {isPolice && <NavLink to="/matches" style={linkStyle}>Verification</NavLink>}
          {isPolice && <NavLink to="/video-search" style={linkStyle}>Video Search</NavLink>}
          {/* Separator */}
          <div style={{ width: '1px', height: '24px', background: 'rgba(255,255,255,0.2)' }} />
          {/* Flood Map button - accessible to all users */}
          <button 
            type="button"
            onClick={onFloodMapOpen}
            style={{
              ...floodMapButtonStyle,
              background: 'rgba(255,255,255,0.15)',
              border: '1px solid rgba(255,255,255,0.3)',
            }}
            onMouseEnter={(e) => {
              e.target.style.color = '#ffffff';
              e.target.style.background = 'rgba(255,255,255,0.25)';
            }}
            onMouseLeave={(e) => {
              e.target.style.color = 'rgba(255,255,255,0.85)';
              e.target.style.background = 'rgba(255,255,255,0.15)';
            }}
          >
            🌧️ Flood Map
          </button>
          <a href="/floodsafe/" style={{...floodMapButtonStyle, background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)'}} onMouseEnter={(e) => {
            e.target.style.color = '#ffffff';
            e.target.style.background = 'rgba(255,255,255,0.25)';
          }} onMouseLeave={(e) => {
            e.target.style.color = 'rgba(255,255,255,0.85)';
            e.target.style.background = 'rgba(255,255,255,0.15)';
          }}>
            🌊 FloodSafe
          </a>
        </nav>

        {/* User - right aligned */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0, justifyContent: 'flex-end' }}>
          <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'white', lineHeight: 1, fontFamily: "'Roboto', sans-serif" }}>
              {username.length > 15 ? username.substring(0, 13) + '…' : username}
            </div>
            <span className={`badge ${ROLE_COLOR[role] || 'badge-neutral'}`} style={{ fontSize: '0.65rem', width: 'fit-content' }}>
              {ROLE_LABEL[role] || role}
            </span>
          </div>
          <button className="btn btn-ghost" onClick={onLogout} style={{ 
            flexShrink: 0, 
            padding: '6px 12px',
            fontSize: '0.8rem',
            minHeight: 'auto',
            color: 'rgba(255,255,255,0.9)',
            fontWeight: 700,
            whiteSpace: 'nowrap',
          }}>
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}

function Shell({ onLogout, onFloodMapOpen, children }) {
  return (
    <>
      <NavBar onLogout={onLogout} onFloodMapOpen={onFloodMapOpen} />
      <main style={{ maxWidth: '100%', width: '100%', margin: '0', padding: 'clamp(1rem, 2vw, 2rem)' }}>
        {children}
      </main>
    </>
  );
}

function AppRoutes() {
  const [authed, setAuthed] = useState(isLoggedIn());
  const [floodMapOpen, setFloodMapOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogin = (data) => {
    setAuthed(true);
    const r = data.role;
    if (r === 'police' || r === 'admin') navigate('/matches');
    else if (r === 'public') navigate('/missing');
    else navigate('/found');
  };

  const handleLogout = () => { clearSession(); setAuthed(false); navigate('/login'); };

  useEffect(() => { 
    if (!authed) navigate('/login'); 
  }, [authed, navigate]);

  return (
    <>
      <FloodMap isOpen={floodMapOpen} onClose={() => setFloodMapOpen(false)} />
      <Routes>
        <Route path="/login" element={authed ? <Navigate to="/found" replace /> : <Login onLogin={handleLogin} />} />

        <Route path="/found" element={
          <RequireAuth allowedRoles={['rescuer', 'police', 'admin', 'public']}>
            <Shell onLogout={handleLogout} onFloodMapOpen={() => setFloodMapOpen(true)}><AddFoundPerson /></Shell>
          </RequireAuth>
        } />

        <Route path="/missing" element={
          <RequireAuth allowedRoles={['public', 'police', 'admin', 'rescuer']}>
            <Shell onLogout={handleLogout} onFloodMapOpen={() => setFloodMapOpen(true)}><MissingPersonForm /></Shell>
          </RequireAuth>
        } />

        <Route path="/matches" element={
          <RequireAuth allowedRoles={['police', 'admin']}>
            <Shell onLogout={handleLogout} onFloodMapOpen={() => setFloodMapOpen(true)}><MatchReview /></Shell>
          </RequireAuth>
        } />

        <Route path="/video-search" element={
          <RequireAuth allowedRoles={['police', 'admin']}>
            <Shell onLogout={handleLogout} onFloodMapOpen={() => setFloodMapOpen(true)}><VideoClothingSearch /></Shell>
          </RequireAuth>
        } />

        <Route path="*" element={
          !authed ? <Navigate to="/login" replace /> :
          <Navigate to={getRole() === 'public' ? '/missing' : getRole() === 'police' || getRole() === 'admin' ? '/matches' : '/found'} replace />
        } />
      </Routes>
    </>
  );
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('React ErrorBoundary caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#1e293b',
          color: 'white',
          padding: '1rem',
          textAlign: 'center',
          fontFamily: 'system-ui, sans-serif',
        }}>
          <div style={{ maxWidth: '500px' }}>
            <h1 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>⚠️ Application Error</h1>
            <p style={{ marginBottom: '1rem', fontSize: '1rem', lineHeight: '1.5' }}>
              {this.state.error?.message || 'An unexpected rendering error occurred'}
            </p>
            <pre style={{
              background: '#0f172a',
              color: '#e2e8f0',
              padding: '1rem',
              borderRadius: '6px',
              fontSize: '0.75rem',
              overflow: 'auto',
              maxHeight: '200px',
              marginBottom: '1rem',
              textAlign: 'left',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}>
              {this.state.error?.stack || JSON.stringify(this.state.error, null, 2)}
            </pre>
            <button 
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              style={{
                marginTop: '1rem',
                padding: '0.75rem 1.5rem',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: 'bold',
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ErrorBoundary>
  );
}
