import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import '../styles/floodmap.css'

const BASEMAP = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxzoom: 19,
    },
  },
  layers: [{ id: 'osm-tiles', type: 'raster', source: 'osm' }],
}

const VELACHERY_CENTER = [80.223, 12.975]
const VELACHERY_ZOOM = 14

export function FloodMap({ isOpen, onClose }) {
  const mapContainer = useRef(null)
  const mapRef = useRef(null)
  const [rainfall, setRainfall] = useState(100)
  const [loading, setLoading] = useState(false)

  // Initialize map
  useEffect(() => {
    if (!isOpen || mapRef.current) return

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: BASEMAP,
      center: VELACHERY_CENTER,
      zoom: VELACHERY_ZOOM,
    })

    map.addControl(new maplibregl.NavigationControl(), 'top-right')
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right')
    
    mapRef.current = map

    return () => {
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="floodmap-modal">
      <div className="floodmap-container">
        {/* Header */}
        <div className="floodmap-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.5rem' }}>🌧️</span>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#001a4d' }}>
                FloodSafe Chennai - Velachery Flood Risk Map
              </h2>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: '#64748b' }}>
                Real-time road-level flood risk assessment
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '1.5rem',
              cursor: 'pointer',
              color: '#64748b',
            }}
          >
            ✕
          </button>
        </div>

        {/* Controls */}
        <div className="floodmap-controls">
          <div className="rainfall-control">
            <label style={{ fontSize: '0.85rem', fontWeight: 600, color: '#1a2a4d' }}>
              💧 Rainfall Level: {rainfall}mm
            </label>
            <input
              type="range"
              min="0"
              max="500"
              value={rainfall}
              onChange={e => setRainfall(Number(e.target.value))}
              style={{
                width: '100%',
                cursor: 'pointer',
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#64748b' }}>
              <span>0mm</span>
              <span>500mm</span>
            </div>
          </div>
        </div>

        {/* Map */}
        <div className="floodmap-canvas" ref={mapContainer} />

        {/* Legend */}
        <div className="floodmap-legend">
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#001a4d', marginBottom: '8px' }}>
            📊 Risk Levels
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', background: '#34a853', borderRadius: '2px' }} />
              <span>Low Risk (0-33)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', background: '#fbbc04', borderRadius: '2px' }} />
              <span>Medium Risk (34-66)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', background: '#ea4335', borderRadius: '2px' }} />
              <span>High Risk (67+)</span>
            </div>
          </div>
        </div>

        {/* Info */}
        <div className="floodmap-info">
          <p style={{ fontSize: '0.75rem', color: '#64748b', margin: 0 }}>
            ℹ️ Adjust rainfall to see how flood risk changes. Roads are color-coded by risk level.
          </p>
        </div>
      </div>
    </div>
  )
}
