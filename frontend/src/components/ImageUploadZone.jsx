import { useState, useRef } from 'react';

/**
 * ImageUploadZone - Reusable drag-drop image upload component
 * 
 * Features:
 * - Drag and drop zone
 * - Click to browse
 * - Image preview
 * - File validation (only images)
 * - Max file size check
 */
export function ImageUploadZone({ onImageSelected, maxSizeMB = 5 }) {
  const [preview, setPreview] = useState(null);
  const [fileName, setFileName] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const maxBytes = maxSizeMB * 1024 * 1024;

  const validateFile = (file) => {
    // Check if it's an image
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file (JPG, PNG, etc.)');
      return false;
    }

    // Check file size
    if (file.size > maxBytes) {
      setError(`Image must be smaller than ${maxSizeMB}MB`);
      return false;
    }

    return true;
  };

  const handleFile = (file) => {
    setError(null);

    if (!validateFile(file)) {
      return;
    }

    setFileName(file.name);

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target.result);
      // Pass file to parent component
      onImageSelected(file);
    };
    reader.readAsDataURL(file);
  };

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
      handleFile(files[0]);
    }
  };

  const handleChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const clearImage = (e) => {
    e.stopPropagation();
    setPreview(null);
    setFileName(null);
    setError(null);
    onImageSelected(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="input-group">
      <label className="input-label">📷 Person Image</label>

      {preview ? (
        // Preview state
        <div
          style={{
            position: 'relative',
            borderRadius: 'var(--radius)',
            overflow: 'hidden',
            backgroundColor: 'var(--bg-subtle)',
            border: '2px solid var(--teal)',
          }}
        >
          <img
            src={preview}
            alt="Person preview"
            style={{
              display: 'block',
              width: '100%',
              maxHeight: '200px',
              objectFit: 'cover',
              backgroundColor: '#000',
            }}
          />
          <div
            style={{
              padding: 'var(--space-sm)',
              background: 'var(--bg)',
              borderTop: '1px solid var(--border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span
              style={{
                fontSize: '0.85rem',
                color: 'var(--text-muted)',
                wordBreak: 'break-all',
              }}
            >
              {fileName}
            </span>
            <button
              onClick={clearImage}
              type="button"
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--danger)',
                cursor: 'pointer',
                fontSize: '1.1rem',
                padding: '4px 8px',
              }}
              title="Remove image"
            >
              ✕
            </button>
          </div>
        </div>
      ) : (
        // Upload zone
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px ${dragActive ? 'solid' : 'dashed'} ${dragActive ? 'var(--teal)' : 'var(--border)'}`,
            borderRadius: 'var(--radius)',
            padding: 'var(--space-lg)',
            textAlign: 'center',
            cursor: 'pointer',
            background: dragActive ? 'var(--bg-subtle)' : 'transparent',
            transition: 'all 0.2s ease',
          }}
        >
          <div style={{ fontSize: '2.5rem', marginBottom: 'var(--space-sm)' }}>
            📷
          </div>
          <div
            style={{
              fontWeight: 600,
              color: 'var(--text)',
              marginBottom: '4px',
            }}
          >
            Drag photo here or click to upload
          </div>
          <div
            style={{
              fontSize: '0.85rem',
              color: 'var(--text-muted)',
            }}
          >
            JPG, PNG, WebP up to {maxSizeMB}MB
          </div>
        </div>
      )}

      {error && (
        <div
          style={{
            marginTop: 'var(--space-sm)',
            padding: 'var(--space-sm)',
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
        accept="image/*"
        onChange={handleChange}
        style={{ display: 'none' }}
      />
    </div>
  );
}
