const SpeakingAnimation = () => {
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      {/* Ripple effect for speaking */}
      <div className="absolute w-40 h-40 md:w-64 md:h-64 rounded-full border-4 border-green-400/20 animate-pulse"></div>
      <div className="absolute w-36 h-36 md:w-56 md:h-56 rounded-full border-4 border-green-400/40 animate-pulse animation-delay-300"></div>
      <div className="absolute w-32 h-32 md:w-52 md:h-52 rounded-full border-4 border-green-400/60 animate-pulse animation-delay-600"></div>
      
      {/* Equalizer bars */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="flex items-center gap-1">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="w-2 bg-green-400 rounded-full animate-pulse"
              style={{
                height: `${Math.sin(Date.now() * 0.01 + i) * 15 + 25}px`,
                animationDelay: `${i * 0.2}s`,
                animationDuration: '1s',
              }}
            />
          ))}
        </div>
      </div>
      
      {/* Breathing glow effect */}
      <div className="absolute w-32 h-32 md:w-48 md:h-48 rounded-full bg-green-400/10 animate-ping animation-delay-100"></div>
    </div>
  );
};

export default SpeakingAnimation;
