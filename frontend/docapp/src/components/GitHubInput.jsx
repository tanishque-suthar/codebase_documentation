import { useState } from 'react';

function GitHubInput({ onSubmit }) {
    const [githubUrl, setGithubUrl] = useState('');
    const [maxFiles, setMaxFiles] = useState(10);
    const [isLoading, setIsLoading] = useState(false);
    const [loadingStep, setLoadingStep] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!githubUrl.trim()) {
            alert('Please enter a GitHub repository URL');
            return;
        }

        // Basic GitHub URL validation
        if (!githubUrl.match(/github\.com\/[^/]+\/[^/]+/)) {
            alert('Please enter a valid GitHub repository URL');
            return;
        }

        setIsLoading(true);

        try {
            // Show loading steps
            setLoadingStep('Exploring repository structure...');
            await new Promise(resolve => setTimeout(resolve, 2000));

            setLoadingStep('Analyzing files...');
            await new Promise(resolve => setTimeout(resolve, 2500));

            setLoadingStep('Generating comprehensive documentation...');

            await onSubmit(githubUrl.trim(), maxFiles);

            setLoadingStep('✅ Documentation generated successfully!');
            await new Promise(resolve => setTimeout(resolve, 1000));

        } catch (error) {
            setLoadingStep('❌ Failed to generate documentation');
            console.error('GitHub documentation generation failed:', error);
            // Error handling is done in the parent component
        } finally {
            setIsLoading(false);
            setLoadingStep('');
        }
    };

    const handleUrlChange = (e) => {
        setGithubUrl(e.target.value);
    };

    const handleMaxFilesChange = (e) => {
        const value = parseInt(e.target.value);
        if (value >= 1 && value <= 50) {
            setMaxFiles(value);
        }
    };

    return (
        <div className="github-input-container">
            <h3>Generate Documentation from GitHub Repository</h3>
            <form onSubmit={handleSubmit} className="github-form">
                <div className="input-group">
                    <label htmlFor="github-url">Repository URL:</label>
                    <input
                        id="github-url"
                        type="url"
                        value={githubUrl}
                        onChange={handleUrlChange}
                        placeholder="https://github.com/username/repository"
                        className="github-url-input"
                        disabled={isLoading}
                    />
                </div>

                <div className="input-group">
                    <label htmlFor="max-files">Max Files to Process:</label>
                    <input
                        id="max-files"
                        type="number"
                        value={maxFiles}
                        onChange={handleMaxFilesChange}
                        min="1"
                        max="50"
                        className="max-files-input"
                        disabled={isLoading}
                    />
                    <small className="input-hint">Limit: 1-50 files (recommended: 10-20 for best results)</small>
                </div>

                <button
                    type="submit"
                    className={`generate-button ${githubUrl.trim() ? 'active' : ''}`}
                    disabled={isLoading || !githubUrl.trim()}
                >
                    {isLoading ? 'Analyzing Repository...' : 'Generate Documentation'}
                </button>

                {isLoading && loadingStep && (
                    <div className="loading-status">
                        <div className="loading-text">{loadingStep}</div>
                        <div className="loading-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                )}
            </form>
        </div>
    );
}

export default GitHubInput;
