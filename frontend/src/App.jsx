import { useEffect, useState } from 'react'
import './App.css'
import { API_BASE_URL, IS_STATIC_MODE } from './api'
import ListingsView from './ListingsView'

function App() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    if (IS_STATIC_MODE) return
    fetch(`${API_BASE_URL}/health`)
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data) => setStatus(data.status === 'ok' ? 'ok' : 'error'))
      .catch(() => setStatus('error'))
  }, [])

  return (
    <div>
      {!IS_STATIC_MODE && (
        <div className="health-check">
          <span className={`dot ${status}`} />
          <span>
            Backend:{' '}
            {status === 'checking' ? 'checking...' : status === 'ok' ? 'healthy' : 'unreachable'}
          </span>
        </div>
      )}
      <ListingsView />
    </div>
  )
}

export default App
