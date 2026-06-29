import { useEffect, useState } from 'react'
import './App.css'
import { API_BASE_URL } from './api'
import ListingsView from './ListingsView'

function App() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data) => setStatus(data.status === 'ok' ? 'ok' : 'error'))
      .catch(() => setStatus('error'))
  }, [])

  return (
    <div>
      <div className="health-check">
        <span className={`dot ${status}`} />
        <span>
          Backend:{' '}
          {status === 'checking' ? 'checking...' : status === 'ok' ? 'healthy' : 'unreachable'}
        </span>
      </div>
      <ListingsView />
    </div>
  )
}

export default App
