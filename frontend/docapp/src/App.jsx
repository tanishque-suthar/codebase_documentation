import { useState } from 'react'
import './App.css'
import CodeInput from './components/CodeInput'
import FileUpload from './components/FileUpload'
import DocumentationDisplay from './components/DocumentationDisplay'
import { generateDocumentation, uploadFileForDocumentation, downloadDocumentation } from './services/api'

function App() {
  const [documentation, setDocumentation] = useState('');
  const [activeTab, setActiveTab] = useState('code'); // 'code' or 'file'
  const [error, setError] = useState('');
  const [currentCode, setCurrentCode] = useState(null);

  const handleCodeSubmit = async (code) => {
    try {
      setError('');
      const response = await generateDocumentation(code);
      setDocumentation(response.markdown);
      setCurrentCode(code);
      return response;
    } catch (err) {
      const message = err.message || 'Failed to generate documentation. Please try again.';
      setError(message);
      console.error('Error generating documentation:', err);
      throw err;
    }
  };

  const handleFileSubmit = async (file) => {
    try {
      setError('');
      const response = await uploadFileForDocumentation(file);
      setDocumentation(response.markdown);
      setCurrentCode(file);
      return response;
    } catch (err) {
      const message = err.message || 'Failed to process file. Please try again.';
      setError(message);
      console.error('Error processing file:', err);
      throw err;
    }
  };

  const handleDownload = async () => {
    try {
      setError('');
      await downloadDocumentation(currentCode);
      return true;
    } catch (err) {
      const message = err.message || 'Failed to download documentation. Please try again.';
      setError(message);
      console.error('Error downloading documentation:', err);
      throw err;
    }
  };

  // Clear error and documentation when switching tabs
  const handleTabChange = (tab) => {
    setError('');
    setDocumentation(''); // Clear documentation output
    setCurrentCode(null); // Reset current code/file
    setActiveTab(tab);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Code Documentation Generator</h1>
        <p>Generate comprehensive documentation for your code</p>
      </header>

      <div className="tab-navigation">
        <button
          className={`tab-button ${activeTab === 'code' ? 'active' : ''}`}
          onClick={() => handleTabChange('code')}
        >
          Paste Code
        </button>
        <button
          className={`tab-button ${activeTab === 'file' ? 'active' : ''}`}
          onClick={() => handleTabChange('file')}
        >
          Upload File
        </button>
      </div>

      <main className="app-content">
        <div className="input-section">
          {activeTab === 'code' ? (
            <CodeInput onSubmit={handleCodeSubmit} />
          ) : (
            <FileUpload onSubmit={handleFileSubmit} />
          )}

          {error && <div className="error-message">{error}</div>}
        </div>

        <div className="output-section">
          <DocumentationDisplay
            markdown={documentation}
            onDownload={handleDownload}
          />
        </div>
      </main>

      <footer className="app-footer">
        <p>Made by Team Daffodils</p>
      </footer>
    </div>
  )
}

export default App
