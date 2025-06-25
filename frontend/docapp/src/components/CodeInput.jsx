import { useState } from 'react';

function CodeInput({ onSubmit }) {
    const [code, setCode] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!code.trim()) return;

        setIsProcessing(true);

        onSubmit(code)
            .finally(() => {
                setIsProcessing(false);
            });
    };

    return (
        <div className="code-input-container">
            <h2>Paste Your Code</h2>
            <form onSubmit={handleSubmit}>
                <textarea
                    className="code-textarea"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="Paste your code here..."
                    rows={10}
                />
                <button
                    type="submit"
                    className="submit-button"
                    disabled={isProcessing || !code.trim()}
                >
                    {isProcessing ? 'Generating...' : 'Generate Documentation'}
                </button>
            </form>
        </div>
    );
}

export default CodeInput;
