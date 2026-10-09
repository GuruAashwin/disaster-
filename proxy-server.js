/**
 * Reverse Proxy Server for Disaster-Affected Family Reunification + FloodSafe Chennai
 * 
 * Routes:
 *   / → http://localhost:5173 (Reunification Frontend)
 *   /floodsafe/* → http://localhost:8001 (FloodSafe Frontend, path preserved)
 *   /api/* → http://localhost:8000 (Reunification Backend, path preserved)
 *   /floodsafe-api/* → http://localhost:8090/path (FloodSafe Backend, path rewritten)
 */

import express from 'express'
import http from 'http'

const app = express()
const PORT = 3001

// Logging middleware
app.use((req, res, next) => {
  const timestamp = new Date().toISOString()
  console.log(`[${timestamp}] ${req.method} ${req.path}`)
  next()
})

// ─────────────────────────────────────────────────────────────────────────────
// Route 1: FloodSafe API — rewrite /floodsafe-api/* to /path on backend:8090
// ─────────────────────────────────────────────────────────────────────────────
app.use('/floodsafe-api/', (req, res, next) => {
  // Remove /floodsafe-api prefix and forward the path to backend on port 8090
  const targetPath = req.path.replace(/^\/floodsafe-api/, '') || '/'
  const targetUrl = `http://localhost:8090${targetPath}`
  
  const options = {
    hostname: 'localhost',
    port: 8090,
    path: targetPath,
    method: req.method,
    headers: {
      ...req.headers,
      // Remove host header to let the backend see the correct one
      host: 'localhost:8090',
    },
  }

  // Forward query string
  if (req.url.includes('?')) {
    options.path += '?' + req.url.split('?')[1]
  }

  const proxyReq = http.request(options, (proxyRes) => {
    // Copy status and headers
    res.writeHead(proxyRes.statusCode, proxyRes.headers)
    // Pipe response
    proxyRes.pipe(res)
  })

  proxyReq.on('error', (err) => {
    console.error(`[FloodSafe API Error] ${err.message}`)
    res.status(503).json({ error: 'FloodSafe backend unavailable', detail: err.message })
  })

  // Forward request body
  req.pipe(proxyReq)
})

// ─────────────────────────────────────────────────────────────────────────────
// Route 2: Reunification API — forward /api/* as-is to backend:8000
// ─────────────────────────────────────────────────────────────────────────────
app.use('/api/', (req, res, next) => {
  const targetPath = req.path
  const options = {
    hostname: 'localhost',
    port: 8000,
    path: targetPath,
    method: req.method,
    headers: {
      ...req.headers,
      host: 'localhost:8000',
    },
  }

  // Forward query string
  if (req.url.includes('?')) {
    options.path += '?' + req.url.split('?')[1]
  }

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers)
    proxyRes.pipe(res)
  })

  proxyReq.on('error', (err) => {
    console.error(`[Reunification API Error] ${err.message}`)
    res.status(503).json({ error: 'Reunification backend unavailable', detail: err.message })
  })

  req.pipe(proxyReq)
})

// ─────────────────────────────────────────────────────────────────────────────
// Route 3: FloodSafe Frontend — proxy /floodsafe/* to frontend:8001
// Special handling for SPA routing and WebSocket upgrades
// ─────────────────────────────────────────────────────────────────────────────
app.use('/floodsafe', (req, res, next) => {
  // For SPA: rewrite all requests under /floodsafe/ to / for the frontend
  const targetPath = req.path.replace(/^\/floodsafe/, '') || '/'
  
  const options = {
    hostname: 'localhost',
    port: 8001,
    path: targetPath,
    method: req.method,
    headers: {
      ...req.headers,
      host: 'localhost:8001',
      // Preserve original URL for SPA routing awareness
      'X-Forwarded-For': req.ip,
      'X-Forwarded-Proto': req.protocol,
      'X-Forwarded-Host': req.hostname,
    },
  }

  // Forward query string
  if (req.url.includes('?')) {
    options.path += '?' + req.url.split('?')[1]
  }

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers)
    proxyRes.pipe(res)
  })

  proxyReq.on('error', (err) => {
    console.error(`[FloodSafe Frontend Error] ${err.message}`)
    res.status(503).send(`<h1>FloodSafe Frontend Unavailable</h1><p>${err.message}</p>`)
  })

  req.pipe(proxyReq)
})

// ─────────────────────────────────────────────────────────────────────────────
// Route 4: Reunification Frontend (Default) — proxy / to frontend:5173
// ─────────────────────────────────────────────────────────────────────────────
app.use('/', (req, res) => {
  const targetPath = req.path
  
  const options = {
    hostname: 'localhost',
    port: 5173,
    path: targetPath,
    method: req.method,
    headers: {
      ...req.headers,
      host: 'localhost:5173',
      'X-Forwarded-For': req.ip,
      'X-Forwarded-Proto': req.protocol,
      'X-Forwarded-Host': req.hostname,
    },
  }

  // Forward query string
  if (req.url.includes('?')) {
    options.path += '?' + req.url.split('?')[1]
  }

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers)
    proxyRes.pipe(res)
  })

  proxyReq.on('error', (err) => {
    console.error(`[Reunification Frontend Error] ${err.message}`)
    res.status(503).send(`<h1>Reunification Frontend Unavailable</h1><p>${err.message}</p>`)
  })

  req.pipe(proxyReq)
})

// ─────────────────────────────────────────────────────────────────────────────
// Health check endpoint (on proxy itself, not proxied)
// ─────────────────────────────────────────────────────────────────────────────
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    message: 'Reverse proxy is running',
    timestamp: new Date().toISOString(),
    routing: {
      '/': 'http://localhost:5173 (Reunification Frontend)',
      '/api/': 'http://localhost:8000 (Reunification Backend)',
      '/floodsafe/': 'http://localhost:8001 (FloodSafe Frontend)',
      '/floodsafe-api/': 'http://localhost:8090 (FloodSafe Backend)',
    },
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// Start server
// ─────────────────────────────────────────────────────────────────────────────
app.listen(PORT, '0.0.0.0', () => {
  console.log('\n============================================================')
  console.log('    Unified Reverse Proxy - READY')
  console.log('============================================================')
  console.log(`  Public Entry Point: http://localhost:${PORT}/`)
  console.log('')
  console.log('  Routes:')
  console.log(`    ├─ GET  /                     -> Reunification (port 5173)`)
  console.log(`    ├─ GET  /floodsafe/*          -> FloodSafe (port 8001)`)
  console.log(`    ├─ POST /api/*                -> Reunification API (8000)`)
  console.log(`    └─ POST /floodsafe-api/*      -> FloodSafe API (8090)`)
  console.log('')
  console.log('  Open http://localhost:3001 in your browser')
  console.log('============================================================\n')
})

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('\n[SIGTERM] Shutting down gracefully...')
  process.exit(0)
})

process.on('SIGINT', () => {
  console.log('\n[SIGINT] Shutting down gracefully...')
  process.exit(0)
})
