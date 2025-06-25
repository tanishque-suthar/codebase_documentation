const API_BASE_URL = 'http://localhost:8000';

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
 * Download documentation as a markdown file
 */
export async function downloadDocumentation(code, isBase64 = false) {
    const formData = new FormData();

    if (code instanceof File) {
        formData.append('file', code);
    } else {
        formData.append('code', code);
        formData.append('isBase64', isBase64);
    }

    // Using XMLHttpRequest for direct download handling
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${API_BASE_URL}/docs/download`, true);
        xhr.responseType = 'blob';

        xhr.onload = function () {
            if (xhr.status === 200) {
                // Create a blob URL for the response
                const blob = new Blob([xhr.response], { type: 'text/markdown' });
                const url = window.URL.createObjectURL(blob);

                // Create a temporary anchor to trigger download
                const a = document.createElement('a');
                const timestamp = new Date().toISOString().replace(/[-:.]/g, '').substring(0, 14);
                a.download = `code_documentation_${timestamp}.md`;
                a.href = url;
                document.body.appendChild(a);
                a.click();

                // Clean up
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                resolve();
            } else {
                // Try to parse error response
                try {
                    const reader = new FileReader();
                    reader.onload = function () {
                        try {
                            const errorData = JSON.parse(reader.result);
                            reject(new Error(errorData.detail || `Server error: ${xhr.status}`));
                        } catch (e) {
                            reject(new Error(`Server error: ${xhr.status}`));
                        }
                    };
                    reader.onerror = function () {
                        reject(new Error(`Server error: ${xhr.status}`));
                    };
                    reader.readAsText(xhr.response);
                } catch (e) {
                    reject(new Error(`Server error: ${xhr.status}`));
                }
            }
        };

        xhr.onerror = function () {
            reject(new Error('Network error - Could not connect to the server'));
        };

        xhr.send(formData);
    });
}
