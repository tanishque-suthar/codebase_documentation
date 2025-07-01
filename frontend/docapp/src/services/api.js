const API_BASE_URL = 'https://codebase-documentation.onrender.com';

/**
 * Generate documentation from code text input
 */
export async function generateDocumentation(code) {
    try {
        const response = await fetch(`${API_BASE_URL}/docs/gen`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code,
                isBase64: false,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(
                errorData?.detail || `Server error: ${response.status} ${response.statusText}`
            );
        }

        return response.json();
    } catch (error) {
        console.error('API error in generateDocumentation:', error);
        throw error;
    }
}

/**
 * Upload a file for documentation generation
 */
export async function uploadFileForDocumentation(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE_URL}/docs/from-upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(
                errorData?.detail || `Server error: ${response.status} ${response.statusText}`
            );
        }

        return response.json();
    } catch (error) {
        console.error('API error in uploadFileForDocumentation:', error);
        throw error;
    }
}

/**
 * Universal download function - accepts pre-generated markdown content
 */
export async function downloadDocumentationUniversal(markdownContent, filenamePrefix = 'documentation', sourceType = 'code') {
    try {
        const response = await fetch(`${API_BASE_URL}/docs/download`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                markdown_content: markdownContent,
                filename_prefix: filenamePrefix,
                source_type: sourceType,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(
                errorData?.detail || `Server error: ${response.status} ${response.statusText}`
            );
        }

        // Get the blob from the response
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);

        // Extract filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('content-disposition');
        let filename = `${filenamePrefix}_${new Date().toISOString().replace(/[-:.]/g, '').substring(0, 14)}.md`;

        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="(.+)"/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }

        // Create a temporary anchor to trigger download
        const a = document.createElement('a');
        a.download = filename;
        a.href = url;
        document.body.appendChild(a);
        a.click();

        // Clean up
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        return true;
    } catch (error) {
        console.error('API error in downloadDocumentationUniversal:', error);
        throw error;
    }
}

/**
 * Generate documentation from GitHub repository
 */
export async function generateGitHubDocumentation(githubUrl, maxFiles = 10) {
    try {
        const response = await fetch(`${API_BASE_URL}/docs/from-github`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                github_url: githubUrl,
                max_files: maxFiles,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(
                errorData?.detail || `Server error: ${response.status} ${response.statusText}`
            );
        }

        return response.json();
    } catch (error) {
        console.error('API error in generateGitHubDocumentation:', error);
        throw error;
    }
}

/**
 * Legacy download functions - kept for backward compatibility
 * These are now wrappers around the universal download function
 */
export async function downloadDocumentation(markdownContent, sourceType = 'code') {
    return downloadDocumentationUniversal(markdownContent, 'code_documentation', sourceType);
}

export async function downloadGitHubDocumentation(markdownContent, githubUrl) {
    // Extract repo name for filename
    const repoMatch = githubUrl.match(/github\.com\/([^/]+)\/([^/]+)/);
    const repoName = repoMatch ? `${repoMatch[1]}_${repoMatch[2]}` : 'github_repo';

    return downloadDocumentationUniversal(markdownContent, `github_docs_${repoName}`, 'github');
}
