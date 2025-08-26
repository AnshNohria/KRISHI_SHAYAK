import { useState, useRef } from 'react';
// import { backend_url } from '..constant/constant'
import { Mic, MicOff, Volume2 } from 'lucide-react';
import AnimatedWaveform from './AnimateWaveform';
import SpeakingAnimation from './SpeakingAnimation';

const VoiceAssistant = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [conversation, setConversation] = useState([]);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordStartTime = useRef(null);

  // ... keep existing code (getSupportedMimeType, startRecording, stopRecording, playBase64Audio, handleStop functions)

  return (
    <div className="min-h-screen bg-white p-4">
      <div className="w-full max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-5xl font-bold text-gray-900 mb-4">
            Voice Assistant
          </h1>
          <p className="text-lg md:text-xl text-gray-600">
            Press and hold to speak, get AI-powered responses
          </p>
        </div>

        <div className="flex flex-col lg:grid lg:grid-cols-2 gap-6 lg:gap-8 items-start">
          {/* Conversation Panel */}
          <div className="w-full bg-gray-50 border border-gray-200 p-4 md:p-6 h-[400px] md:h-[500px] overflow-hidden order-2 lg:order-1">
            <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-4">Conversation</h2>
            <div className="h-[320px] md:h-[400px] overflow-y-auto space-y-4 pr-2">
              {conversation.length === 0 && (
                <div className="text-center text-gray-500 py-12 md:py-16">
                  <Mic className="mx-auto h-12 w-12 md:h-16 md:w-16 mb-4 opacity-50" />
                  <p className="text-sm md:text-base">Start a conversation by speaking...</p>
                </div>
              )}
              
              {conversation.map((turn, idx) => (
                <div key={idx} className="space-y-3">
                  <div className="flex justify-end">
                    <div className="bg-blue-500 text-white rounded-2xl px-4 py-3 max-w-[85%] md:max-w-[80%]">
                      <p className="text-xs font-medium mb-1 opacity-90">You</p>
                      <p className="text-sm md:text-base">{turn.user}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="bg-gray-200 text-gray-900 rounded-2xl px-4 py-3 max-w-[85%] md:max-w-[80%]">
                      <p className="text-xs font-medium mb-1 text-gray-600">Assistant</p>
                      <p className="text-sm md:text-base">{turn.assistant}</p>
                    </div>
                    <button
                      size="sm"
                      variant="ghost"
                      className="text-gray-600 hover:bg-gray-100 p-2 flex-shrink-0"
                      onClick={() => playBase64Audio(turn.audio_base64)}
                    >
                      <Volume2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
              
              {loading && (
                <div className="flex justify-center py-4">
                  <div className="flex items-center gap-2 text-gray-500">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-gray-600"></div>
                    <span className="text-sm">Processing...</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Voice Control Panel */}
          <div className="flex flex-col items-center justify-center space-y-6 md:space-y-8 order-1 lg:order-2 py-8">
            <div className="relative">
              {/* Main Voice Button */}
              <div className="relative">
                {isRecording && <AnimatedWaveform />}
                {isSpeaking && <SpeakingAnimation />}
                
                <button
                  className={`
                    w-32 h-32 md:w-48 md:h-48 rounded-full text-white text-base md:text-lg font-semibold
                    transition-all duration-300 relative z-10 shadow-xl
                    ${isRecording 
                      ? 'bg-red-500 hover:bg-red-600' 
                      : isSpeaking
                      ? 'bg-green-500 hover:bg-green-600'
                      : 'bg-blue-600 hover:bg-blue-700'
                    }
                    ${loading ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105 active:scale-95'}
                  `}
                  onMouseDown={startRecording}
                  onMouseUp={stopRecording}
                  onTouchStart={startRecording}
                  onTouchEnd={stopRecording}
                  disabled={loading || isSpeaking}
                >
                  <div className="flex flex-col items-center gap-2">
                    {isRecording ? (
                      <>
                        <MicOff className="h-6 w-6 md:h-8 md:w-8" />
                        <span className="text-sm md:text-base">Listening...</span>
                      </>
                    ) : isSpeaking ? (
                      <>
                        <Volume2 className="h-6 w-6 md:h-8 md:w-8" />
                        <span className="text-sm md:text-base">Speaking...</span>
                      </>
                    ) : (
                      <>
                        <Mic className="h-6 w-6 md:h-8 md:w-8" />
                        <span className="text-sm md:text-base">Hold to Talk</span>
                      </>
                    )}
                  </div>
                </button>
              </div>
            </div>

            {/* Status Text */}
            <div className="text-center space-y-2 px-4">
              {isRecording && (
                <p className="text-red-600 font-medium text-sm md:text-base">
                  🔴 Recording - Speak now...
                </p>
              )}
              {loading && (
                <p className="text-blue-600 text-sm md:text-base">
                  🤖 AI is thinking...
                </p>
              )}
              {isSpeaking && (
                <p className="text-green-600 font-medium text-sm md:text-base">
                  🔊 AI is speaking...
                </p>
              )}
              {!isRecording && !loading && !isSpeaking && (
                <p className="text-gray-500 text-sm md:text-base">
                  Press and hold the button to start
                </p>
              )}
            </div>
          </div>
        </div>

        <footer className="text-center mt-8 md:mt-12 text-gray-400 text-xs md:text-sm">
          © {new Date().getFullYear()} Voice Assistant Powered by AI
        </footer>
      </div>
    </div>
  );
};

export default VoiceAssistant;