from fastapi.middleware.cors import CORSMiddleware

def setup_cors_middleware(app):
    """
    Configure CORS middleware for the FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """
    origins = [
        "http://localhost:5173",     # Default Vite dev server
        "http://localhost:3000",     # Alternative port
        "http://127.0.0.1:5173",     # Using IP instead of localhost
        "http://127.0.0.1:3000",     # Alternative port with IP
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app
