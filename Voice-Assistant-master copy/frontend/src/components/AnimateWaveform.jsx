const AnimatedWaveform = () => {
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      {/* Outer pulse rings */}
      <div className="absolute w-40 h-40 md:w-64 md:h-64 rounded-full border-4 border-red-400/30 animate-ping"></div>
      <div className="absolute w-36 h-36 md:w-56 md:h-56 rounded-full border-4 border-red-400/50 animate-ping animation-delay-200"></div>
      <div className="absolute w-32 h-32 md:w-52 md:h-52 rounded-full border-4 border-red-400/70 animate-ping animation-delay-400"></div>
      
      {/* Waveform bars */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="flex items-end gap-1 h-12 md:h-16">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="w-1 bg-red-400 rounded-full animate-bounce"
              style={{
                height: `${Math.random() * 60 + 20}%`,
                animationDelay: `${i * 0.1}s`,
                animationDuration: `${0.5 + Math.random() * 0.5}s`,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default AnimatedWaveform;