import React from 'react';
import { useNavigate } from 'react-router-dom';

const Homepage = () => {
    const navigate = useNavigate();

    const handleGetStarted = () => {
        navigate('/generate-docs');
    };

    return (
        <div className="homepage-container">
            <div className="homepage-content">
                <div className="hero-section">
                    <h1 className="homepage-title">BloomDocs</h1>
                    <p className="homepage-subtitle">
                        Generate clear and comprehensive documentation for your code
                    </p>
                    <button
                        className="generate-docs-button"
                        onClick={handleGetStarted}
                    >
                        Generate Documentation
                    </button>
                </div>

                {/* Features section */}
                <div className="features-section">
                    <div className="feature-card">
                        <h3>Smart Code Analysis</h3>
                        <p>Automatically analyze your code structure and generate comprehensive documentation</p>
                    </div>
                    <div className="feature-card">
                        <h3>Multiple Input Methods</h3>
                        <p>Paste code directly, upload files, or connect GitHub repositories seamlessly</p>
                    </div>
                    <div className="feature-card">
                        <h3>Quick Markdown Export</h3>
                        <p>Get professional documentation in markdown format ready for immediate use</p>
                    </div>
                </div>

                {/* Decorative background elements */}
                <div className="background-circles">
                    <div className="circle circle-1"></div>
                    <div className="circle circle-2"></div>
                    <div className="circle circle-3"></div>
                    <div className="circle circle-4"></div>
                    <div className="circle circle-5"></div>
                    <div className="circle circle-6"></div>
                    <div className="circle circle-7"></div>
                    <div className="circle circle-8"></div>
                </div>
            </div>
        </div>
    );
};

export default Homepage;
