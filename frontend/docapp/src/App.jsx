import { Routes, Route, Navigate } from 'react-router-dom'
import './App.css'
import Homepage from './components/Homepage'
import DocumentationApp from './components/DocumentationApp'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Homepage />} />
      <Route path="/generate-docs" element={<DocumentationApp />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
