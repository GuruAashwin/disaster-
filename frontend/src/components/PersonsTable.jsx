import { useState, useEffect, useCallback } from 'react';
import { listPersons, getPersonImageUrl, deletePerson, getRole } from '../api';
import { PhotoGallery } from './PhotoGallery';

const GENDER_ICON = { Male: '♂', Female: '♀', Unknown: '·' };

function timeAgo(isoStr) {
  if (!isoStr) return '—';
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function PersonsTable({ type, title, accentColor = '#4f6ef7', refreshTrigger = 0, showPhotoUpload = false }) {
  const [persons, setPersons]   = useState([]);
  const [loading, setLoading]   = useState(false);
  const [selected, setSelected] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const userRole = getRole();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listPersons({ type, limit: 100 });
      setPersons(data);
    } catch { /* secondary UI */ }
    finally { setLoading(false); }
  }, [type]);

  useEffect(() => { load(); }, [load, refreshTrigger]);

  const expandRows = (p) => {
    const age = p.age_min != null
      ? (p.age_min === p.age_max ? String(p.age_min) : `${p.age_min}–${p.age_max}`)
      : '—';
    const rows = [
      ['Age',    age],
      ['Gender', p.gender || '—'],
    ];
    if (type === 'found') {
      rows.push(['Condition', p.raw_fields?.condition   || '—']);
      rows.push(['Location',  p.raw_fields?.location    || '—']);
    } else {
      rows.push(['Description', p.raw_fields?.descriptors || '—']);
      rows.push(['Last Seen',   p.raw_fields?.location    || '—']);
    }
    rows.push(['ID', (p.id?.slice(0, 13) ?? '') + '…']);
    return rows;
  };

  const handlePhotosAdded = () => {
    // Refresh person data to show new photos
    load();
  };

  const handleDeletePerson = async (personId) => {
    if (!window.confirm('Are you sure you want to delete this record? This action cannot be undone.')) {
      return;
    }
    
    setDeleting(personId);
    try {
      await deletePerson(personId);
      // Remove from list
      setPersons(persons.filter(p => p.id !== personId));
      setSelected(null);
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="panel" style={{ minHeight: '480px', maxHeight: '82vh' }}>
      {/* Header */}
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: accentColor, flexShrink: 0 }} />
          <h3 style={{ fontSize: '0.87rem', margin: 0, color: '#1e3a5f' }}>{title}</h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ background: `${accentColor}18`, border: `1px solid ${accentColor}40`, borderRadius: '9999px', padding: '1px 9px', fontSize: '0.7rem', color: accentColor, fontWeight: 700 }}>
            {persons.length}
          </span>
          <button className="btn btn-ghost" onClick={load} disabled={loading} style={{ padding: '3px 10px', fontSize: '0.7rem' }}>
            {loading ? '…' : '↻'}
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="panel-body">
        {!loading && persons.length === 0 && (
          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#94a3b8' }}>
            <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>📂</div>
            <div style={{ fontSize: '0.8rem' }}>No records yet</div>
          </div>
        )}

        {persons.map((p) => {
          const name   = p.raw_fields?.name || '(unknown)';
          const sub    = p.raw_fields?.location || '—';
          const gender = p.gender || 'Unknown';
          const isOpen = selected === p.id;

          return (
            <div
              key={p.id}
              className={`panel-row${isOpen ? ' active' : ''}`}
              onClick={() => setSelected(isOpen ? null : p.id)}
            >
              {/* Summary row */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                  <div style={{ width: '28px', height: '28px', borderRadius: '7px', background: `${accentColor}15`, border: `1px solid ${accentColor}30`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', color: accentColor, fontWeight: 700, flexShrink: 0 }}>
                    {GENDER_ICON[gender] ?? '·'}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.82rem', color: '#0f172a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{name}</div>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{sub}</div>
                  </div>
                </div>
                <div style={{ flexShrink: 0, textAlign: 'right' }}>
                  <span className="badge badge-success" style={{ fontSize: '0.62rem', padding: '1px 7px', display: 'block', marginBottom: '2px' }}>{p.status || 'active'}</span>
                  <span style={{ fontSize: '0.62rem', color: '#94a3b8' }}>{timeAgo(p.created_at)}</span>
                </div>
              </div>

              {/* Expanded */}
              {isOpen && (
                <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #f1f5f9' }}>
                  {/* Image display */}
                  {p.image_filename && (
                    <div style={{ marginBottom: '12px' }}>
                      <img
                        src={getPersonImageUrl(p.id)}
                        alt="Person"
                        style={{ maxWidth: '100%', height: 'auto', borderRadius: '6px', maxHeight: '150px', objectFit: 'contain' }}
                      />
                    </div>
                  )}

                  {/* Photo Gallery (rescuer only) */}
                  {showPhotoUpload && (
                    <div style={{ marginBottom: '12px', padding: '10px', background: '#f8fafc', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                      <PhotoGallery
                        personId={p.id}
                        photos={p.photo_filenames || []}
                        onPhotosAdded={handlePhotosAdded}
                      />
                    </div>
                  )}
                  
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
                    <tbody>
                      {expandRows(p).map(([k, v]) => (
                        <tr key={k}>
                          <td style={{ padding: '2px 10px 2px 0', color: '#94a3b8', fontWeight: 600, whiteSpace: 'nowrap', verticalAlign: 'top', width: '80px' }}>{k}</td>
                          <td style={{ padding: '2px 0', color: '#334155', wordBreak: 'break-word' }}>{v}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {/* Admin delete button */}
                  {userRole === 'admin' && (
                    <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #f1f5f9', display: 'flex', gap: '8px' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeletePerson(p.id);
                        }}
                        disabled={deleting === p.id}
                        style={{
                          padding: '6px 12px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          background: deleting === p.id ? '#dc2626' : '#ef4444',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: deleting === p.id ? 'not-allowed' : 'pointer',
                          opacity: deleting === p.id ? 0.6 : 1,
                        }}
                      >
                        {deleting === p.id ? '⏳ Deleting…' : '🗑 Delete'}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
