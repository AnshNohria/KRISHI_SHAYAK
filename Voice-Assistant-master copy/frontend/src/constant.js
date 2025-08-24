const isLocal = () => {
  return (
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
  );
};

export const backend_url = isLocal()
  ? "http://localhost:8000" // when running locally
  : "https://krishi-shayak.onrender.com"; // when deployed on Render