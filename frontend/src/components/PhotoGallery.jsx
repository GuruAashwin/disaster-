import { useState, useRef } from 'react';
import { uploadPersonPhotos, getPersonPhotoUrl } from '../api';

/**
 * PhotoGallery - Display and upload photos for a person
 * Modes:
 * 1. showLocalPreview=true: For selecting files before form submission (rescuer form)
 * 2. showLocalPreview=false: For uploading to backend after person creation (from log)
 */
export function PhotoGallery({ 
  personId, 
  photos = [], 
  onPhotosAdded, 
  onPhotosSelected,
  isDisabled = false,
  showLocalPreview = false 
}) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFiles(Array.from(files));
    }
  };

  const handleChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFiles(Array.from(files));
    }
  };

  const handleFiles = async (files) => {
    setError(null);

    // For local preview mode (before form submission)
    if (showLocalPreview && onPhotosSelected) {
      // Validate files
      for (const file of files) {
        if (!file.type.startsWith('image/')) {
          setError(`${file.name} is not an image file`);
          return;
        }
        if (file.size > 5 * 1024 * 1024) {
          setError(`${file.name} is larger than 5MB`);
          return;
        }
      }
      onPhotosSelected(files);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      return;
    }

    // For backend upload mode (after person creation)
    if (!personId) {
      setError('Person ID is required for upload');
      return;
    }

    setUploading(true);

    try {
      // Validate files
      for (const file of files) {
        if (!file.type.startsWith('image/')) {
          throw new Error(`${file.name} is not an image file`);
        }
        if (file.size > 5 * 1024 * 1024) {
          throw new Error(`${file.name} is larger than 5MB`);
        }
      }

      // Upload
      const result = await uploadPersonPhotos(personId, files);
      if (result && onPhotosAdded) {
        onPhotosAdded(result);
      }
      
      // Clear input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      {/* Photo Gallery Display (only in backend upload mode) */}
      {!showLocalPreview && photos && photos.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))',
            gap: '0.75rem',
            marginBottom: '1rem',
          }}
        >
          {photos.map((photoFilename, idx) => (
            <div
              key={idx}
              onClick={() => setSelectedPhoto(photoFilename)}
              style={{
                position: 'relative',
                cursor: 'pointer',
                borderRadius: 'var(--radius)',
                overflow: 'hidden',
                border: selectedPhoto === photoFilename ? '2px solid var(--teal)' : '1px solid var(--border)',
                aspectRatio: '1',
                background: '#f3f4f6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <img
                src={getPersonPhotoUrl(photoFilename)}
                alt={`Photo ${idx + 1}`}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                }}
                onError={(e) => {
                  // Show error placeholder if image fails to load
                  e.target.parentElement.style.background = '#fee2e2';
                  e.target.style.display = 'none';
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  top: '4px',
                  right: '4px',
                  background: 'rgba(0,0,0,0.7)',
                  color: 'white',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  fontSize: '0.65rem',
                  fontWeight: 700,
                }}
              >
                {idx + 1}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Full-screen preview */}
      {selectedPhoto && (
        <div
          onClick={() => setSelectedPhoto(null)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.9)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            cursor: 'pointer',
          }}
        >
          <img
            src={getPersonPhotoUrl(selectedPhoto)}
            alt="Full preview"
            style={{
              maxWidth: '90vw',
              maxHeight: '90vh',
              objectFit: 'contain',
            }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* Upload Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !isDisabled && fileInputRef.current?.click()}
        style={{
          border: `2px ${dragActive ? 'solid' : 'dashed'} ${dragActive ? 'var(--teal)' : 'var(--border)'}`,
          borderRadius: 'var(--radius)',
          padding: 'var(--space-lg)',
          textAlign: 'center',
          cursor: isDisabled ? 'not-allowed' : 'pointer',
          background: dragActive ? 'var(--bg-subtle)' : 'transparent',
          transition: 'all 0.2s ease',
          opacity: isDisabled ? 0.5 : 1,
        }}
      >
        <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📸</div>
        <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: '4px' }}>
          {uploading ? 'Uploading...' : 'Drag photos or click to upload'}
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Multiple JPG, PNG, WebP up to 5MB each
        </div>
      </div>

      {error && (
        <div
          style={{
            marginTop: '0.75rem',
            padding: '0.75rem',
            background: 'var(--danger-soft)',
            border: '1px solid var(--danger)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--danger)',
            fontSize: '0.85rem',
          }}
        >
          ⚠️ {error}
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/*"
        onChange={handleChange}
        disabled={isDisabled || uploading}
        style={{ display: 'none' }}
      />
    </div>
  );
}
