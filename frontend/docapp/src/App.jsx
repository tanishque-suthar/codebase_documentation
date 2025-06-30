import { useState, useRef } from 'react'
import './App.css'
import CodeInput from './components/CodeInput'
import FileUpload from './components/FileUpload'
import GitHubInput from './components/GitHubInput'
import DocumentationDisplay from './components/DocumentationDisplay'
import { generateDocumentation, uploadFileForDocumentation, downloadDocumentationUniversal, generateGitHubDocumentation } from './services/api'

function App() {
  const [documentation, setDocumentation] = useState('');
  const [activeTab, setActiveTab] = useState('code'); // 'code', 'file', or 'github'
  const [error, setError] = useState('');
  const [currentCode, setCurrentCode] = useState(null);
  const [currentGitHubData, setCurrentGitHubData] = useState(null);
  const outputSectionRef = useRef(null);

  // Function to scroll to documentation section
  const scrollToDocumentation = () => {
    if (outputSectionRef.current) {
      outputSectionRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  };

  const handleCodeSubmit = async (code) => {
    try {
      setError('');
      const response = await generateDocumentation(code);
      setDocumentation(response.markdown);
      setCurrentCode(code);
      // Scroll to documentation after a short delay to ensure content is rendered
      setTimeout(() => scrollToDocumentation(), 100);
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
      // Scroll to documentation after a short delay to ensure content is rendered
      setTimeout(() => scrollToDocumentation(), 100);
      return response;
    } catch (err) {
      const message = err.message || 'Failed to process file. Please try again.';
      setError(message);
      console.error('Error processing file:', err);
      throw err;
    }
  };

  const handleGitHubSubmit = async (githubUrl, maxFiles) => {
    try {
      setError('');
      const response = await generateGitHubDocumentation(githubUrl, maxFiles);
      setDocumentation(response.markdown);
      setCurrentGitHubData({ githubUrl, maxFiles });
      setCurrentCode(null); // Clear code data when using GitHub
      // Scroll to documentation after a short delay to ensure content is rendered
      setTimeout(() => scrollToDocumentation(), 100);
      return response;
    } catch (err) {
      const message = err.message || 'Failed to generate GitHub documentation. Please try again.';
      setError(message);
      console.error('Error generating GitHub documentation:', err);
      throw err;
    }
  };

  const handleDownload = async () => {
    try {
      setError('');

      // Check if we have documentation to download
      if (!documentation || !documentation.trim()) {
        throw new Error('No documentation to download. Please generate documentation first.');
      }

      // Determine source type and filename based on current state
      let sourceType = 'code';
      let filenamePrefix = 'documentation';

      if (currentGitHubData) {
        sourceType = 'github';
        // Extract repo name for filename
        const repoMatch = currentGitHubData.githubUrl.match(/github\.com\/([^/]+)\/([^/]+)/);
        const repoName = repoMatch ? `${repoMatch[1]}_${repoMatch[2]}` : 'github_repo';
        filenamePrefix = `github_docs_${repoName}`;
      } else if (currentCode instanceof File) {
        sourceType = 'file';
        filenamePrefix = `file_docs_${currentCode.name.replace(/\.[^/.]+$/, '')}`; // Remove file extension
      } else if (currentCode) {
        sourceType = 'code';
        filenamePrefix = 'code_documentation';
      }

      // Use the universal download function with stored documentation
      await downloadDocumentationUniversal(documentation, filenamePrefix, sourceType);

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
    setCurrentGitHubData(null); // Reset GitHub data
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
        <button
          className={`tab-button ${activeTab === 'github' ? 'active' : ''}`}
          onClick={() => handleTabChange('github')}
        >
          GitHub Repository
        </button>
      </div>

      <main className="app-content">
        <div className="input-section">
          {activeTab === 'code' ? (
            <CodeInput onSubmit={handleCodeSubmit} />
          ) : activeTab === 'file' ? (
            <FileUpload onSubmit={handleFileSubmit} />
          ) : (
            <GitHubInput onSubmit={handleGitHubSubmit} />
          )}

          {error && <div className="error-message">{error}</div>}
        </div>

        <div className="output-section" ref={outputSectionRef}>
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
