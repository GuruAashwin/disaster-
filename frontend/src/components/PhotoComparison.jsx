import { useState } from 'react';
import { getPersonPhotoUrl } from '../api';

/**
 * PhotoComparison - Side-by-side photo comparison for match verification
 * Shows found person photos vs missing person photos during police review
 */
export function PhotoComparison({ foundPhotos = [], missingPhotos = [], photoConfidence = 0 }) {
  const [selectedFoundIdx, setSelectedFoundIdx] = useState(0);
  const [selectedMissingIdx, setSelectedMissingIdx] = useState(0);
  const [fullscreenPhoto, setFullscreenPhoto] = useState(null);

  const foundPhoto = foundPhotos?.[selectedFoundIdx];
  const missingPhoto = missingPhotos?.[selectedMissingIdx];

  const getConfidenceColor = (conf) => {
    if (conf >= 80) return '#10b981'; // green
    if (conf >= 60) return '#f59e0b'; // amber
    if (conf >= 40) return '#ef4444'; // red
    return '#6b7280'; // gray
  };

  const getConfidenceLabel = (conf) => {
    if (conf >= 80) return 'High';
    if (conf >= 60) return 'Medium';
    if (conf >= 40) return 'Low';
    return 'Very Low';
  };

  if (!foundPhotos?.length && !missingPhotos?.length) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
        <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>📸</div>
        <div>No photos available for comparison</div>
      </div>
    );
  }

  return (
    <div>
      {/* Confidence Indicator */}
      {photoConfidence > 0 && (
        <div
          style={{
            marginBottom: '1.5rem',
            padding: '1rem',
            background: `${getConfidenceColor(photoConfidence)}18`,
            border: `2px solid ${getConfidenceColor(photoConfidence)}`,
            borderRadius: 'var(--radius)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div
              style={{
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                background: getConfidenceColor(photoConfidence),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 700,
                fontSize: '1.5rem',
              }}
            >
              {Math.round(photoConfidence)}%
            </div>
            <div>
              <div style={{ fontWeight: 700, color: getConfidenceColor(photoConfidence) }}>
                Photo Match Confidence: {getConfidenceLabel(photoConfidence)}
              </div>
              <div style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '4px' }}>
                Based on visual similarity analysis of available photos
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Comparison Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'auto 1fr',
          gap: '1.5rem',
          marginBottom: '1.5rem',
        }}
      >
        {/* Found Person Photos */}
        <div>
          <div style={{ fontWeight: 700, marginBottom: '1rem', color: '#1e3a5f' }}>
            🦺 Found Person Photos ({foundPhotos?.length || 0})
          </div>
          {foundPhotos && foundPhotos.length > 0 ? (
            <div>
              <div
                onClick={() => setFullscreenPhoto(foundPhoto)}
                style={{
                  width: '250px',
                  height: '250px',
                  borderRadius: 'var(--radius)',
                  overflow: 'hidden',
                  border: '2px solid var(--teal)',
                  cursor: 'pointer',
                  background: '#000',
                  marginBottom: '1rem',
                }}
              >
                <img
                  src={getPersonPhotoUrl(foundPhoto)}
                  alt="Found person"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              </div>
              <div
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  flexWrap: 'wrap',
                }}
              >
                {foundPhotos.map((photo, idx) => (
                  <div
                    key={idx}
                    onClick={() => setSelectedFoundIdx(idx)}
                    style={{
                      width: '60px',
                      height: '60px',
                      borderRadius: '6px',
                      overflow: 'hidden',
                      border: selectedFoundIdx === idx ? '2px solid var(--teal)' : '1px solid var(--border)',
                      cursor: 'pointer',
                      background: '#000',
                    }}
                  >
                    <img
                      src={getPersonPhotoUrl(photo)}
                      alt={`Found ${idx}`}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ color: '#94a3b8', fontSize: '0.9rem', padding: '1rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius)' }}>
              No photos uploaded
            </div>
          )}
        </div>

        {/* Missing Person Photos */}
        <div>
          <div style={{ fontWeight: 700, marginBottom: '1rem', color: '#1e3a5f' }}>
            👨‍👩‍👦 Missing Person Photos ({missingPhotos?.length || 0})
          </div>
          {missingPhotos && missingPhotos.length > 0 ? (
            <div>
              <div
                onClick={() => setFullscreenPhoto(missingPhoto)}
                style={{
                  width: '250px',
                  height: '250px',
                  borderRadius: 'var(--radius)',
                  overflow: 'hidden',
                  border: '2px solid var(--orange)',
                  cursor: 'pointer',
                  background: '#000',
                  marginBottom: '1rem',
                }}
              >
                <img
                  src={getPersonPhotoUrl(missingPhoto)}
                  alt="Missing person"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              </div>
              <div
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  flexWrap: 'wrap',
                }}
              >
                {missingPhotos.map((photo, idx) => (
                  <div
                    key={idx}
                    onClick={() => setSelectedMissingIdx(idx)}
                    style={{
                      width: '60px',
                      height: '60px',
                      borderRadius: '6px',
                      overflow: 'hidden',
                      border: selectedMissingIdx === idx ? '2px solid var(--orange)' : '1px solid var(--border)',
                      cursor: 'pointer',
                      background: '#000',
                    }}
                  >
                    <img
                      src={getPersonPhotoUrl(photo)}
                      alt={`Missing ${idx}`}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ color: '#94a3b8', fontSize: '0.9rem', padding: '1rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius)' }}>
              No photos on file
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen Modal */}
      {fullscreenPhoto && (
        <div
          onClick={() => setFullscreenPhoto(null)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.95)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            cursor: 'pointer',
          }}
        >
          <img
            src={getPersonPhotoUrl(fullscreenPhoto)}
            alt="Full view"
            style={{
              maxWidth: '90vw',
              maxHeight: '90vh',
              objectFit: 'contain',
            }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
