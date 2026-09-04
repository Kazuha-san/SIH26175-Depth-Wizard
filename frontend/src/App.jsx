/**
 * Root component. Owns which of the 3 main views is active:
 * Upload -> Processing -> Results. Keep this as simple state-based
 * view switching -- no router needed for a local single-session app.
 */
import { useState } from 'react'
import UploadView from './views/UploadView.jsx'
import ProcessingView from './views/ProcessingView.jsx'
import ResultsView from './views/ResultsView.jsx'

export default function App() {
  const [view, setView] = useState('upload') // 'upload' | 'processing' | 'results'

  // TODO: lift pipeline result state up here once views are wired together

  return (
    <div className="app">
      {view === 'upload' && <UploadView onStart={() => setView('processing')} />}
      {view === 'processing' && <ProcessingView onDone={() => setView('results')} />}
      {view === 'results' && <ResultsView onReset={() => setView('upload')} />}
    </div>
  )
}
