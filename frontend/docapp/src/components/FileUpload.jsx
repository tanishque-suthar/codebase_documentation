import { useState, useRef } from 'react';

function FileUpload({ onSubmit }) {
    const [file, setFile] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const fileInputRef = useRef(null);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!file) return;

        setIsProcessing(true);

        onSubmit(file)
            .finally(() => {
                setIsProcessing(false);
                // Reset file input
                setFile(null);
                if (fileInputRef.current) {
                    fileInputRef.current.value = '';
                }
            });
    };

    return (
        <div className="file-upload-container">
            <h2>Upload Code File</h2>
            <form onSubmit={handleSubmit}>
                <div className="file-input-wrapper">
                    <input
                        type="file"
                        onChange={handleFileChange}
                        ref={fileInputRef}
                        accept=".js,.jsx,.ts,.tsx,.py,.java,.c,.cpp,.cs,.go,.rb,.php,.html,.css"
                    />
                    <p className="file-name">{file ? file.name : 'No file selected'}</p>
                </div>
                <button
                    type="submit"
                    className="submit-button"
                    disabled={isProcessing || !file}
                >
                    {isProcessing ? 'Uploading...' : 'Upload & Generate'}
                </button>
            </form>
        </div>
    );
}

export default FileUpload;
