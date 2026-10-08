import { useState } from 'react';
import { searchVideoByClothing, processVideos } from '../api';

// Get API base URL for image serving
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// 14 supported colors from STEP 7, with friendly labels
const SUPPORTED_COLORS = [
  { value: 'red', label: 'Red' },
  { value: 'blue', label: 'Blue' },
  { value: 'black', label: 'Black' },
  { value: 'white', label: 'White' },
  { value: 'gray', label: 'Gray' },
  { value: 'green', label: 'Green' },
  { value: 'yellow', label: 'Yellow' },
  { value: 'brown', label: 'Brown' },
  { value: 'orange', label: 'Orange' },
  { value: 'purple', label: 'Purple' },
  { value: 'pink', label: 'Pink' },
  { value: 'navy', label: 'Navy' },
  { value: 'beige', label: 'Beige' },
  { value: 'maroon', label: 'Maroon' },
];

/**
 * Convert seconds to HH:MM:SS format
 * @param {number} seconds - Total seconds
 * @returns {string} - Formatted time string
 */
function formatTimestamp(seconds) {
  if (seconds === null || seconds === undefined) {
    return 'Timestamp unavailable';
  }
  
  const totalSeconds = Math.floor(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;
  
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * ResultCard - Display a single clothing match candidate
 * 
 * Shows:
 * - Frame image preview with viewer modal
 * - Camera, video, frame details
 * - Detected clothing colors and match status
 * - Clothing match score (0-100)
 * - Verification warning (not identity verification)
 */
function ResultCard({ candidate }) {
  const [showImage, setShowImage] = useState(false);
  const shirtMatched = candidate.upper_body?.detected_color !== null;
  const pantsMatched = candidate.lower_body?.detected_color !== null;
  
  // Build frame image URL with full API base
  const frameImageUrl = `${API_BASE}/videos/frame/${candidate.camera_id}/${candidate.video_id}/${candidate.frame}`;
  
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: 'var(--space-lg)',
      marginBottom: 'var(--space-lg)',
      boxShadow: 'var(--shadow-sm)',
      transition: 'all 0.2s ease',
    }}>
      {/* Header with warning icon */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-md)',
        marginBottom: 'var(--space-lg)',
        paddingBottom: 'var(--space-md)',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div style={{
          fontSize: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          ⚠️
        </div>
        <div>
          <div style={{
            fontSize: '1rem',
            fontWeight: 600,
            color: 'var(--text)',
          }}>
            Possible Sighting
          </div>
          <div style={{
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
            marginTop: '2px',
          }}>
            Clothing match detected in authorized footage
          </div>
        </div>
      </div>

      {/* Frame Image - Clickable Preview */}
      <div style={{
        marginBottom: 'var(--space-lg)',
        display: 'flex',
        justifyContent: 'center',
      }}>
        <button
          onClick={() => setShowImage(true)}
          style={{
            background: 'var(--bg-subtle)',
            border: '2px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            cursor: 'pointer',
            padding: 0,
            overflow: 'hidden',
            transition: 'all 0.2s ease',
            maxWidth: '100%',
            height: 'auto',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--teal)';
            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border)';
            e.currentTarget.style.boxShadow = 'none';
          }}
          aria-label="View frame image in full size"
        >
          <img
            src={frameImageUrl}
            alt="Clothing match frame"
            style={{
              display: 'block',
              maxWidth: '100%',
              height: 'auto',
              maxHeight: '300px',
              width: '100%',
              objectFit: 'contain',
              background: 'var(--bg)',
            }}
            onError={(e) => {
              e.target.style.display = 'none';
              e.target.parentElement.innerHTML = '<div style="padding: var(--space-lg); text-align: center; color: var(--text-muted);">Unable to load frame image</div>';
            }}
          />
        </button>
      </div>

      {/* Image Modal - Full Screen Viewer */}
      {showImage && (
        <div
          onClick={() => setShowImage(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.9)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            cursor: 'pointer',
            padding: 'var(--space-xl)',
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              position: 'relative',
              maxWidth: '90vw',
              maxHeight: '90vh',
            }}
          >
            {/* Close button */}
            <button
              onClick={() => setShowImage(false)}
              style={{
                position: 'absolute',
                top: '-40px',
                right: 0,
                background: 'none',
                border: 'none',
                color: 'white',
                fontSize: '2rem',
                cursor: 'pointer',
                padding: '0',
                width: '40px',
                height: '40px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'scale(1.2)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
              }}
              aria-label="Close image viewer"
            >
              ✕
            </button>
            
            {/* Image */}
            <img
              src={frameImageUrl}
              alt="Clothing match frame - full view"
              style={{
                maxWidth: '90vw',
                maxHeight: '90vh',
                width: 'auto',
                height: 'auto',
                display: 'block',
                borderRadius: 'var(--radius-lg)',
              }}
            />
            
            {/* Info overlay */}
            <div
              style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                background: 'rgba(0, 0, 0, 0.7)',
                color: 'white',
                padding: 'var(--space-md)',
                borderBottomLeftRadius: 'var(--radius-lg)',
                borderBottomRightRadius: 'var(--radius-lg)',
                fontSize: '0.9rem',
              }}
            >
              <div>{candidate.camera_id} • {candidate.video_id} • {candidate.frame}</div>
              <div style={{ marginTop: '4px', fontSize: '0.85rem', opacity: 0.8 }}>
                Time: {formatTimestamp(candidate.timestamp_seconds)} • Score: {candidate.match_score}/100
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Metadata */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: 'var(--space-md)',
        marginBottom: 'var(--space-lg)',
      }}>
        <div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
            Camera
          </div>
          <div style={{ fontSize: '0.95rem', color: 'var(--text)', fontWeight: 500 }}>
            {candidate.camera_id}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
            Video
          </div>
          <div style={{ fontSize: '0.95rem', color: 'var(--text)', fontWeight: 500 }}>
            {candidate.video_id}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
            Frame
          </div>
          <div style={{ fontSize: '0.95rem', color: 'var(--text)', fontWeight: 500, wordBreak: 'break-all' }}>
            {candidate.frame}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
            Time
          </div>
          <div style={{ fontSize: '0.95rem', color: 'var(--text)', fontWeight: 500 }}>
            {formatTimestamp(candidate.timestamp_seconds)}
          </div>
        </div>
      </div>

      {/* Clothing Detection */}
      <div style={{
        background: 'var(--bg-subtle)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius)',
        padding: 'var(--space-md)',
        marginBottom: 'var(--space-lg)',
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
          gap: 'var(--space-md)',
        }}>
          {/* Shirt */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-md)',
          }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, marginBottom: '4px' }}>
                Shirt
              </div>
              <div style={{ 
                fontSize: '0.95rem', 
                color: 'var(--text)',
                fontWeight: 500,
              }}>
                {candidate.upper_body?.detected_color ? 
                  (candidate.upper_body.detected_color.charAt(0).toUpperCase() + candidate.upper_body.detected_color.slice(1))
                  : 'Not detected'
                }
              </div>
            </div>
            {shirtMatched && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '24px',
                height: '24px',
                background: 'var(--success)',
                color: 'white',
                borderRadius: '50%',
                fontSize: '0.9rem',
                flexShrink: 0,
              }}>
                ✓
              </div>
            )}
          </div>

          {/* Pants */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-md)',
          }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, marginBottom: '4px' }}>
                Pants
              </div>
              <div style={{ 
                fontSize: '0.95rem', 
                color: 'var(--text)',
                fontWeight: 500,
              }}>
                {candidate.lower_body?.detected_color ? 
                  (candidate.lower_body.detected_color.charAt(0).toUpperCase() + candidate.lower_body.detected_color.slice(1))
                  : 'Not detected'
                }
              </div>
            </div>
            {pantsMatched && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '24px',
                height: '24px',
                background: 'var(--success)',
                color: 'white',
                borderRadius: '50%',
                fontSize: '0.9rem',
                flexShrink: 0,
              }}>
                ✓
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Match Score */}
      <div style={{
        marginBottom: 'var(--space-lg)',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--space-sm)',
        }}>
          <div style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text)' }}>
            Clothing Match Score
          </div>
          <div style={{
            fontSize: '1rem',
            fontWeight: 600,
            color: 'var(--navy)',
          }}>
            {candidate.match_score}/100
          </div>
        </div>
        {/* Score bar - NOT styled like probability */}
        <div style={{
          width: '100%',
          height: '24px',
          background: 'var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          overflow: 'hidden',
          border: '1px solid var(--border)',
        }}>
          <div style={{
            height: '100%',
            width: `${candidate.match_score}%`,
            background: `linear-gradient(90deg, var(--teal), var(--teal-light))`,
            transition: 'width 0.3s ease',
          }} />
        </div>
        <div style={{
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          marginTop: '4px',
          fontStyle: 'italic',
        }}>
          Indicates clothing similarity only
        </div>
      </div>

      {/* Verification Warning */}
      <div style={{
        background: 'var(--warning-soft)',
        border: `1px solid var(--warning)`,
        borderRadius: 'var(--radius)',
        padding: 'var(--space-md)',
        display: 'flex',
        gap: 'var(--space-md)',
        alignItems: 'flex-start',
      }}>
        <div style={{
          fontSize: '1.2rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          ⚠️
        </div>
        <div>
          <div style={{
            fontWeight: 600,
            color: 'var(--text)',
            marginBottom: '4px',
          }}>
            Verification Required
          </div>
          <div style={{
            fontSize: '0.9rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
          }}>
            Clothing similarity does not confirm identity. Please verify the person manually using additional information such as distinctive features, belongings, or family identification.
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * VideoClothingSearch - Main component
 * 
 * Allows users to search authorized disaster video footage
 * for possible clothing matches. Results require human verification
 * and are NOT identity confirmation.
 */
export function VideoClothingSearch() {
  const [upperColor, setUpperColor] = useState('');
  const [lowerColor, setLowerColor] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processingError, setProcessingError] = useState(null);

  const canSearch = upperColor || lowerColor;

  const handleProcessVideos = async () => {
    setProcessing(true);
    setProcessingError(null);

    try {
      const response = await processVideos();
      alert(`Successfully processed ${response.videos_processed} video(s)`);
      setProcessing(false);
    } catch (err) {
      setProcessingError(err.message);
      setProcessing(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!canSearch) return;

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await searchVideoByClothing({
        upper_body_color: upperColor || null,
        lower_body_color: lowerColor || null,
      });

      setResults(response);
      setSearched(true);
    } catch (err) {
      setError(err.message);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setUpperColor('');
    setLowerColor('');
    setResults(null);
    setError(null);
    setSearched(false);
  };

  return (
    <div style={{
      maxWidth: '900px',
      margin: '0 auto',
      padding: 'var(--space-xl)',
    }}>
      {/* Processing Section */}
      {processingError && (
        <div style={{
          background: 'var(--danger-soft)',
          border: `1px solid var(--danger)`,
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-lg)',
          marginBottom: 'var(--space-xl)',
          display: 'flex',
          gap: 'var(--space-md)',
          alignItems: 'flex-start',
        }}>
          <div style={{ fontSize: '1.5rem', flexShrink: 0 }}>❌</div>
          <div>
            <div style={{
              fontWeight: 600,
              color: 'var(--text)',
              marginBottom: '4px',
            }}>
              Unable to process videos
            </div>
            <div style={{
              fontSize: '0.95rem',
              color: 'var(--text-secondary)',
            }}>
              {processingError}
            </div>
          </div>
        </div>
      )}

      {/* Process Videos Card */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-lg)',
        marginBottom: 'var(--space-xl)',
        boxShadow: 'var(--shadow-sm)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 'var(--space-lg)',
        }}>
          <div style={{
            fontSize: '2rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            🎬
          </div>
          <div style={{ flex: 1 }}>
            <h2 style={{
              fontSize: '1.1rem',
              fontWeight: 600,
              color: 'var(--text)',
              marginBottom: 'var(--space-sm)',
            }}>
              Process Videos
            </h2>
            <p style={{
              fontSize: '0.95rem',
              color: 'var(--text-secondary)',
              marginBottom: 'var(--space-md)',
              lineHeight: 1.6,
            }}>
              Videos must be processed into frames before searching. This extracts frames from your video files and prepares them for clothing analysis.
            </p>
            <button
              onClick={handleProcessVideos}
              disabled={processing}
              style={{
                padding: '10px 20px',
                fontSize: '0.95rem',
                fontWeight: 600,
                background: processing ? 'var(--border)' : 'var(--navy)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--radius)',
                cursor: processing ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s ease',
                opacity: processing ? 0.6 : 1,
              }}
            >
              {processing ? '⏳ Processing...' : '🎬 Process Videos Now'}
            </button>
          </div>
        </div>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-lg)',
        marginBottom: 'var(--space-xl)',
        boxShadow: 'var(--shadow-sm)',
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--space-lg)',
          marginBottom: 'var(--space-lg)',
        }}>
          {/* Shirt Color */}
          <div>
            <label style={{
              display: 'block',
              fontSize: '0.95rem',
              fontWeight: 700,
              color: 'var(--text)',
              marginBottom: 'var(--space-sm)',
            }}>
              Shirt Color
            </label>
            <select
              value={upperColor}
              onChange={(e) => setUpperColor(e.target.value)}
              disabled={loading}
              style={{
                width: '100%',
                padding: 'var(--space-md)',
                fontSize: 'inherit',
                border: `2px solid ${upperColor ? 'var(--border-focus)' : 'var(--border)'}`,
                borderRadius: 'var(--radius)',
                background: 'var(--bg)',
                color: 'var(--text)',
                cursor: 'pointer',
                transition: 'border-color 0.2s ease',
                fontWeight: 600,
              }}
              aria-label="Select shirt color"
            >
              <option value="">Select clothing color</option>
              {SUPPORTED_COLORS.map(color => (
                <option key={color.value} value={color.value}>
                  {color.label}
                </option>
              ))}
            </select>
          </div>

          {/* Pants Color */}
          <div>
            <label style={{
              display: 'block',
              fontSize: '0.95rem',
              fontWeight: 700,
              color: 'var(--text)',
              marginBottom: 'var(--space-sm)',
            }}>
              Pants Color
            </label>
            <select
              value={lowerColor}
              onChange={(e) => setLowerColor(e.target.value)}
              disabled={loading}
              style={{
                width: '100%',
                padding: 'var(--space-md)',
                fontSize: 'inherit',
                border: `2px solid ${lowerColor ? 'var(--border-focus)' : 'var(--border)'}`,
                borderRadius: 'var(--radius)',
                background: 'var(--bg)',
                color: 'var(--text)',
                cursor: 'pointer',
                transition: 'border-color 0.2s ease',
                fontWeight: 600,
              }}
              aria-label="Select pants color"
            >
              <option value="">Select clothing color</option>
              {SUPPORTED_COLORS.map(color => (
                <option key={color.value} value={color.value}>
                  {color.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Buttons */}
        <div style={{
          display: 'flex',
          gap: 'var(--space-md)',
          flexWrap: 'wrap',
        }}>
          <button
            type="submit"
            disabled={!canSearch || loading}
            style={{
              padding: '10px 20px',
              fontSize: '0.95rem',
              fontWeight: 600,
              background: canSearch && !loading ? 'var(--teal)' : 'var(--border)',
              color: 'white',
              border: 'none',
              borderRadius: 'var(--radius)',
              cursor: canSearch && !loading ? 'pointer' : 'not-allowed',
              transition: 'all 0.2s ease',
              opacity: canSearch && !loading ? 1 : 0.6,
              minHeight: '48px',
              minWidth: '150px',
            }}
            aria-busy={loading}
            aria-label={loading ? 'Searching...' : 'Search video footage'}
          >
            {loading ? (
              <span>🔍 Searching...</span>
            ) : (
              <span>🔍 Search Video Footage</span>
            )}
          </button>
          {searched && (
            <button
              type="button"
              onClick={handleReset}
              disabled={loading}
              style={{
                padding: '10px 20px',
                fontSize: '0.95rem',
                fontWeight: 600,
                background: 'var(--bg-subtle)',
                color: 'var(--text)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                minHeight: '48px',
                minWidth: '120px',
              }}
              aria-label="Reset search form"
            >
              Reset
            </button>
          )}
        </div>
      </form>

      {/* Loading State */}
      {loading && (
        <div style={{
          textAlign: 'center',
          padding: 'var(--space-2xl)',
          background: 'var(--bg-subtle)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
        }}>
          <div style={{ fontSize: '2rem', marginBottom: 'var(--space-md)' }}>
            🔍
          </div>
          <div style={{
            fontSize: '1rem',
            color: 'var(--text)',
            fontWeight: 500,
            marginBottom: 'var(--space-sm)',
          }}>
            Searching disaster footage...
          </div>
          <div style={{
            fontSize: '0.9rem',
            color: 'var(--text-secondary)',
          }}>
            This may take a few moments.
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div style={{
          background: 'var(--danger-soft)',
          border: `1px solid var(--danger)`,
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-lg)',
          marginBottom: 'var(--space-xl)',
          display: 'flex',
          gap: 'var(--space-md)',
          alignItems: 'flex-start',
        }}>
          <div style={{ fontSize: '1.5rem', flexShrink: 0 }}>❌</div>
          <div>
            <div style={{
              fontWeight: 600,
              color: 'var(--text)',
              marginBottom: '4px',
            }}>
              Unable to search video footage right now.
            </div>
            <div style={{
              fontSize: '0.95rem',
              color: 'var(--text-secondary)',
              marginBottom: 'var(--space-md)',
            }}>
              Please check your connection and try again.
            </div>
            <button
              onClick={handleReset}
              style={{
                padding: '8px 16px',
                fontSize: '0.9rem',
                fontWeight: 600,
                background: 'var(--danger)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--radius)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* No Results State */}
      {searched && !loading && !error && results && results.total_candidates === 0 && (
        <div style={{
          background: 'var(--info-soft)',
          border: `1px solid var(--info)`,
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-lg)',
          marginBottom: 'var(--space-xl)',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 'var(--space-md)' }}>
            🔎
          </div>
          <div style={{
            fontWeight: 600,
            color: 'var(--text)',
            marginBottom: 'var(--space-sm)',
            fontSize: '1rem',
          }}>
            No matching clothing candidate found in analyzed footage
          </div>
          <div style={{
            color: 'var(--text-secondary)',
            fontSize: '0.95rem',
            lineHeight: 1.6,
            marginBottom: 'var(--space-md)',
          }}>
            This does not mean the person is not present. The search only covers available authorized footage.
          </div>
          <div style={{
            color: 'var(--text-muted)',
            fontSize: '0.85rem',
            fontStyle: 'italic',
          }}>
            Try adjusting the clothing colors or searching additional footage.
          </div>
        </div>
      )}

      {/* Results */}
      {searched && !loading && !error && results && results.total_candidates > 0 && (
        <div>
          <div style={{
            marginBottom: 'var(--space-lg)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-md)',
          }}>
            <h2 style={{
              fontSize: '1.3rem',
              fontWeight: 600,
              color: 'var(--navy)',
            }}>
              Possible Sightings
            </h2>
            <span style={{
              background: 'var(--teal)',
              color: 'white',
              borderRadius: '50%',
              width: '32px',
              height: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 600,
              fontSize: '0.9rem',
            }}>
              {results.total_candidates}
            </span>
          </div>

          {/* Summary by video */}
          {(() => {
            const videoGroups = {};
            results.candidates.forEach(c => {
              const key = c.video_id;
              if (!videoGroups[key]) videoGroups[key] = [];
              videoGroups[key].push(c);
            });
            return (
              <div style={{
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-lg)',
                marginBottom: 'var(--space-lg)',
              }}>
                <h3 style={{
                  fontSize: '1rem',
                  fontWeight: 600,
                  color: 'var(--text)',
                  marginBottom: 'var(--space-md)',
                }}>
                  📊 Summary by Video
                </h3>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: 'var(--space-md)',
                }}>
                  {Object.entries(videoGroups).map(([videoId, candidates]) => (
                    <div key={videoId} style={{
                      background: 'var(--bg)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius)',
                      padding: 'var(--space-md)',
                    }}>
                      <div style={{
                        fontWeight: 600,
                        color: 'var(--teal)',
                        fontSize: '0.95rem',
                        marginBottom: '4px',
                      }}>
                        {videoId}
                      </div>
                      <div style={{
                        fontSize: '1.2rem',
                        fontWeight: 700,
                        color: 'var(--navy)',
                      }}>
                        {candidates.length} match{candidates.length !== 1 ? 'es' : ''}
                      </div>
                      <div style={{
                        fontSize: '0.8rem',
                        color: 'var(--text-muted)',
                        marginTop: '4px',
                      }}>
                        Avg score: {Math.round(candidates.reduce((a, c) => a + c.match_score, 0) / candidates.length)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          <div style={{
            display: 'flex',
            flexDirection: 'column',
          }}>
            {results.candidates.map((candidate, idx) => (
              <ResultCard key={idx} candidate={candidate} />
            ))}
          </div>

          {results.total_candidates > 0 && (
            <div style={{
              textAlign: 'center',
              padding: 'var(--space-lg)',
              color: 'var(--text-muted)',
              fontSize: '0.9rem',
            }}>
              Showing {results.total_candidates} result{results.total_candidates !== 1 ? 's' : ''}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
