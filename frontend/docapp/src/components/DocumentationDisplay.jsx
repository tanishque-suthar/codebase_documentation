import { useState } from 'react';
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';

// Configure marked to use highlight.js for code syntax highlighting
marked.setOptions({
    highlight: function (code, lang) {
        const language = hljs.getLanguage(lang) ? lang : 'plaintext';
        return hljs.highlight(code, { language }).value;
    },
    langPrefix: 'hljs language-', // highlight.js css classes
    breaks: true, // Convert line breaks to <br>
    gfm: true, // GitHub Flavored Markdown
    xhtml: false, // Close HTML tags
    headerIds: false // Don't add IDs to headers (prevents horizontal overflow from long IDs)
});

function DocumentationDisplay({ markdown, onDownload }) {
    const [isDownloading, setIsDownloading] = useState(false);

    const handleDownload = () => {
        if (!markdown) return;

        setIsDownloading(true);

        onDownload()
            .finally(() => {
                setIsDownloading(false);
            });
    };

    // Convert markdown to HTML using marked
    const htmlContent = markdown ? marked(markdown) : '';

    return (
        <div className="documentation-display">
            <div className="documentation-header">
                <h2>Generated Documentation</h2>
                {markdown && (
                    <button
                        onClick={handleDownload}
                        className="download-button"
                        disabled={isDownloading}
                    >
                        {isDownloading ? 'Downloading...' : 'Download as MD'}
                    </button>
                )}
            </div>

            <div className="documentation-content">
                {markdown ? (
                    <div className="markdown-preview" dangerouslySetInnerHTML={{ __html: htmlContent }} />
                ) : (
                    <div className="empty-state">
                        <p>No documentation generated yet.</p>
                        <p>Paste code or upload a file to generate documentation.</p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default DocumentationDisplay;
