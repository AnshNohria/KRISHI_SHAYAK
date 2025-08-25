// Utility to check if running in Docker
const isDocker = () => {
  return window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
}

export const backend_url = isDocker() ? "http://backend:8000" : "http://localhost:8000";

// export const backend_url = "http://localhost:8000";  // Default backend URL

// for local development
// For Docker deployment, App.jsx will override this to http://backend:8000 if needed