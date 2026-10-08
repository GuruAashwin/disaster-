import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { isLoggedIn, getRole, getUsername, clearSession } from './api';
import { Login } from './components/Login';
import { AddFoundPerson } from './components/AddFoundPerson';
import { MissingPersonForm } from './components/MissingPersonForm';
import { MatchReview } from './components/MatchReview';
import { VideoClothingSearch } from './components/VideoClothingSearch';

function RequireAuth({ children, allowedRoles }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  const role = getRole();
  if (allowedRoles && !allowedRoles.includes(role)) return <Navigate to="/" replace />;
  return children;
}

const ROLE_LABEL = { rescuer: 'Rescuer', police: 'Police Admin', admin: 'Admin', public: 'Family' };
const ROLE_COLOR = { rescuer: 'badge-primary', police: 'badge-navy', admin: 'badge-navy', public: 'badge-warning' };

function NavBar({ onLogout }) {
  const role     = getRole();
  const username = getUsername();
  const isPolice = role === 'police' || role === 'admin';
  const isPublic = role === 'public';

  const linkStyle = ({ isActive }) => ({
    textDecoration: 'none',
    fontWeight: 700,
    fontSize: '0.95rem',
    padding: '8px 14px',
    borderRadius: '4px',
    color: isActive ? '#003d99' : 'rgba(255,255,255,0.85)',
    background: isActive ? '#ffffff' : 'transparent',
    border: isActive ? '1px solid #b3d9ff' : '1px solid transparent',
    transition: 'all 0.2s ease',
    whiteSpace: 'nowrap',
  });

  return (
    <header style={{
      background: '#003d99',
      borderBottom: '2px solid #002966',
      boxShadow: 'var(--shadow-md)',
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
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            background: 'linear-gradient(135deg, #0066ff, #3385ff)', 
            borderRadius: '6px', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            fontSize: '1.3rem',
            flexShrink: 0,
          }}>
            🚨
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontWeight: 800, fontSize: '1rem', color: 'white', lineHeight: 1.2 }}>
              DFR System
            </div>
            <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.9)', letterSpacing: '0.05em', textTransform: 'uppercase', fontWeight: 600 }}>
              Reunification
            </div>
          </div>
        </div>

        {/* Nav links - centered and expanded */}
        <nav style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'nowrap' }}>
          {(role === 'rescuer' || isPolice) && <NavLink to="/found"   style={linkStyle}>Found</NavLink>}
          {(isPublic         || isPolice) && <NavLink to="/missing" style={linkStyle}>Missing</NavLink>}
          {isPolice                        && <NavLink to="/matches" style={linkStyle}>Matches</NavLink>}
          {isPolice                        && <NavLink to="/video-search" style={linkStyle}>Video Search</NavLink>}
        </nav>

        {/* User - right aligned */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0, justifyContent: 'flex-end' }}>
          <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'white', lineHeight: 1 }}>
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
            Out
          </button>
        </div>
      </div>
    </header>
  );
}

function Shell({ onLogout, children }) {
  return (
    <>
      <NavBar onLogout={onLogout} />
      <main style={{ maxWidth: '100%', width: '100%', margin: '0', padding: 'clamp(1rem, 2vw, 2rem)' }}>
        {children}
      </main>
    </>
  );
}

function AppRoutes() {
  const [authed, setAuthed] = useState(isLoggedIn());
  const navigate = useNavigate();

  const handleLogin = (data) => {
    setAuthed(true);
    const r = data.role;
    if (r === 'police' || r === 'admin') navigate('/matches');
    else if (r === 'public') navigate('/missing');
    else navigate('/found');
  };

  const handleLogout = () => { clearSession(); setAuthed(false); navigate('/login'); };

  useEffect(() => { if (!authed) navigate('/login'); }, [authed, navigate]);

  return (
    <Routes>
      <Route path="/login" element={authed ? <Navigate to="/found" replace /> : <Login onLogin={handleLogin} />} />

      <Route path="/found" element={
        <RequireAuth allowedRoles={['rescuer', 'police', 'admin']}>
          <Shell onLogout={handleLogout}><AddFoundPerson /></Shell>
        </RequireAuth>
      } />

      <Route path="/missing" element={
        <RequireAuth allowedRoles={['public', 'police', 'admin']}>
          <Shell onLogout={handleLogout}><MissingPersonForm /></Shell>
        </RequireAuth>
      } />

      <Route path="/matches" element={
        <RequireAuth allowedRoles={['police', 'admin']}>
          <Shell onLogout={handleLogout}><MatchReview /></Shell>
        </RequireAuth>
      } />

      <Route path="/video-search" element={
        <RequireAuth allowedRoles={['police', 'admin']}>
          <Shell onLogout={handleLogout}><VideoClothingSearch /></Shell>
        </RequireAuth>
      } />

      <Route path="*" element={
        !authed ? <Navigate to="/login" replace /> :
        <Navigate to={getRole() === 'public' ? '/missing' : getRole() === 'police' || getRole() === 'admin' ? '/matches' : '/found'} replace />
      } />
    </Routes>
  );
}

export default function App() {
  return <BrowserRouter><AppRoutes /></BrowserRouter>;
}
