import { useState, useRef, useEffect } from 'react'
import { backend_url } from './constant'
import SpeakingAnimation from './components/SpeakingAnimation'
import AnimatedWaveform from './components/AnimateWaveform'
import botImage from './assets/bot.png' // Import bot image

function App() {
  const [isRecording, setIsRecording] = useState(false)
  const [audioUrl, setAudioUrl] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [blobSize, setBlobSize] = useState(0)
  const [audioMime, setAudioMime] = useState('audio/wav')
  const [conversation, setConversation] = useState([]) // Add conversation state
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [language, setLanguage] = useState('en-IN')
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const recordStartTime = useRef(null)
  const conversationEndRef = useRef(null)

  // Check supported mime types
  const getSupportedMimeType = () => {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
      return 'audio/webm;codecs=opus'
    } else if (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/wav')) {
      return 'audio/wav'
    } else if (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/mp3')) {
      return 'audio/mp3'
    } else {
      return 'audio/webm'
    }
  }

  // Start recording
  const startRecording = async () => {
    setError(null)
    setAudioUrl(null)
    setBlobSize(0)
    try {
      const mimeType = getSupportedMimeType()
      setAudioMime(mimeType)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new window.MediaRecorder(stream, { mimeType })
      audioChunksRef.current = []
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data)
      }
      mediaRecorder.onstop = handleStop
      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start() // No timeslice argument, records until stop()
      recordStartTime.current = Date.now()
      setIsRecording(true)
    } catch {
      setError('Microphone access denied or not available.')
    }
  }

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      const elapsed = Date.now() - recordStartTime.current
      if (elapsed < 300) {
        setTimeout(() => {
          mediaRecorderRef.current.stop()
          setIsRecording(false)
        }, 300 - elapsed)
      } else {
        mediaRecorderRef.current.stop()
        setIsRecording(false)
      }
    }
  }

  // Play audio from base64 string
  const playBase64Audio = (base64, mimeHint) => {
    // Detect mime if not provided
    let mime = mimeHint || 'audio/wav'
    try {
      const bytes = atob(base64).slice(0,4)
      if (bytes.startsWith('ID3') || bytes.charCodeAt(0) === 0xFF) mime = 'audio/mpeg'
      else if (bytes === 'OggS') mime = 'audio/ogg'
      else if (bytes === 'RIFF') mime = 'audio/wav'
    } catch {}
    const audio = new Audio(`data:${mime};base64,${base64}`)
    setIsSpeaking(true)
    audio.onended = () => setIsSpeaking(false)
    audio.play().catch(e => console.error('Audio play error', e))
  }

  // Handle stop event
  const handleStop = async () => {
    setLoading(true)
    setError(null)
    const audioBlob = new Blob(audioChunksRef.current, { type: audioMime })
    setBlobSize(audioBlob.size)
    if (audioBlob.size === 0) {
      setError('No audio captured. Please speak clearly and try again.')
      setLoading(false)
      return
    }
    try {
      // Always use backend_url from constant.js
      const url = backend_url
      // Prepare conversation history for multi-turn
      const history = conversation.map(turn => [
        { role: 'user', content: turn.user },
        { role: 'assistant', content: turn.assistant }
      ]).flat();
      const headers = {
        'Content-Type': audioMime.startsWith('audio/') ? audioMime : 'audio/wav',
        'X-Language-Code': language,
        'X-Session-ID': 'test-session-123',
      };
      // Remove X-Chat-History header to avoid non-ASCII error
      // If conversation history is needed, send it another way (e.g., backend change required)
      const response = await fetch(url + '/voice-chat', {
        method: 'POST',
        body: audioBlob,
        headers,
      })
      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || 'Server error')
      }
    const data = await response.json()
      // Add to conversation
      setConversation(prev => [
        ...prev,
        {
          user: data.transcription,
      assistant: data.response,
      audio_base64: data.audio_base64,
      audio_mime: data.audio_mime
        }
      ])
      // Play the assistant's audio
    playBase64Audio(data.audio_base64, data.audio_mime)
      setAudioUrl(null) // Don't show old audio player
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (conversationEndRef.current) {
      conversationEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [conversation, loading])

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-100 to-indigo-200 p-4 overflow-hidden">
      <div className="flex flex-col md:flex-row gap-8 w-full max-w-4xl">
        {/* Chat Window */}
        <div className="flex-1 bg-white rounded-xl shadow-lg p-6 md:p-8 mb-6 md:mb-0 max-h-[32rem] flex flex-col">
          <h2 className="text-2xl font-bold mb-4 text-indigo-700">Conversation</h2>
          {/* Face Card Animation with Bot Image */}
          <div className="flex justify-center mb-4">
            <div className="relative w-24 h-24 md:w-32 md:h-32 flex items-center justify-center">
              {/* Animated waveform behind the bot image when listening */}
              {isRecording && (
                <span className="absolute inset-0 flex items-center justify-center z-0 pointer-events-none">
                  <AnimatedWaveform />
                </span>
              )}
              {/* Bot Image as round icon */}
              <img
                src={botImage}
                alt="Bot"
                className="w-24 h-24 md:w-32 md:h-32 rounded-full border-4 border-indigo-200 shadow-lg object-cover z-10"
                style={{ position: 'relative', zIndex: 2 }}
              />
              {/* Animated ring when talking or listening */}
              {(isRecording || isSpeaking) && (
                <span className={`absolute inset-0 flex items-center justify-center z-0 pointer-events-none`}>
                  <span className={`absolute w-full h-full rounded-full border-4 ${isSpeaking ? 'border-green-400' : 'border-indigo-400'} animate-pulse`}></span>
                  <span className={`absolute w-full h-full rounded-full border-8 ${isSpeaking ? 'border-green-200/60' : 'border-indigo-200/60'} animate-ping`}></span>
                </span>
              )}
            </div>
          </div>
          <div className="w-full flex-1 mb-2 max-h-96 overflow-y-auto custom-scrollbar" id="conversation-scroll">
            {conversation.length === 0 && (
              <div className="text-gray-400 text-center">No conversation yet. Start talking!</div>
            )}
            {conversation.map((turn, idx) => (
              <div key={idx} className="mb-4">
                <div className="text-right">
                  <span className="inline-block bg-indigo-100 text-indigo-700 rounded-lg px-3 py-1 mb-1 animate-fade-in">
                    <b>You:</b> {turn.user}
                  </span>
                </div>
                <div className="text-left flex items-center gap-2">
                  <span className="inline-block bg-gray-100 text-gray-700 rounded-lg px-3 py-1 animate-fade-in">
                    <b>Assistant:</b> {turn.assistant}
                  </span>
                  <button
                    className="ml-2 text-indigo-500 underline text-xs"
                    onClick={() => playBase64Audio(turn.audio_base64)}
                    title="Replay audio"
                  >
                    ▶️
                  </button>
                  {/* Animated dots when loading and this is the last turn */}
                  {loading && idx === conversation.length - 1 && (
                    <span className="ml-2 animate-bounce text-indigo-400 text-lg">...</span>
                  )}
                </div>
              </div>
            ))}
            {/* Show animated dots if waiting for first output */}
            {loading && conversation.length === 0 && (
              <div className="flex justify-center items-center mt-4">
                <span className="animate-bounce text-indigo-400 text-2xl">...</span>
              </div>
            )}
            <div ref={conversationEndRef} />
          </div>
        </div>

        {/* Talking Window */}
        <div className="flex flex-col items-center justify-center flex-shrink-0 bg-white rounded-xl shadow-lg p-8 w-full max-w-md">
          <h1 className="text-3xl font-bold mb-4 text-indigo-700">Voice Assistant</h1>
          <p className="mb-2 text-gray-600 text-center">Press and hold the button, speak your query, and get an AI-powered voice response!</p>
          {/* Language Selector */}
          <div className="mb-4 w-full flex flex-col items-center">
            <label htmlFor="language-select" className="text-sm text-gray-700 mb-1">Select Language:</label>
            <select
              id="language-select"
              className="border rounded px-2 py-1 text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              value={language}
              onChange={e => setLanguage(e.target.value)}
              disabled={isRecording || loading}
            >
              <option value="en-IN">English</option>
              <option value="hi-IN">Hindi</option>
              <option value="bn-IN">Bengali</option>
              <option value="gu-IN">Gujarati</option>
              <option value="kn-IN">Kannada</option>
              <option value="ml-IN">Malayalam</option>
              <option value="mr-IN">Marathi</option>
              <option value="od-IN">Odia</option>
              <option value="pa-IN">Punjabi</option>
              <option value="ta-IN">Tamil</option>
              <option value="te-IN">Telugu</option>
            </select>
          </div>
          <button
            className={`w-32 h-32 rounded-full flex items-center justify-center text-white text-xl font-semibold shadow-lg transition-all duration-200 mb-6 relative ${isRecording ? 'bg-red-500 animate-pulse' : 'bg-indigo-600 hover:bg-indigo-700'}`}
            onClick={isRecording ? stopRecording : startRecording}
            disabled={loading}
          >
            {isRecording && (
              <span className="absolute inset-0 flex items-center justify-center z-0">
                <AnimatedWaveform />
              </span>
            )}
            <span className="z-10">
              {isRecording ? (
                <span className="flex flex-col items-center">
                  <span>Listening...</span>
                  <span className="mt-2 flex gap-1">
                    <span className="w-3 h-3 bg-white rounded-full animate-bounce" style={{ animationDelay: '0s' }}></span>
                    <span className="w-3 h-3 bg-white rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                    <span className="w-3 h-3 bg-white rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></span>
                  </span>
                </span>
              ) : 'Tap to Talk'}
            </span>
          </button>
          {/* Show SpeakingAnimation when assistant is speaking */}
          {isSpeaking && <SpeakingAnimation />}
          {loading && <div className="text-indigo-600 mb-2 flex items-center gap-2">Processing <span className="animate-spin inline-block w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full"></span></div>}
          {error && <div className="text-red-500 mb-2">{error}</div>}
          {blobSize > 0 && <div className="text-xs text-gray-400 mb-2">Audio size: {blobSize} bytes ({audioMime})</div>}
          {audioUrl && (
            <audio controls src={audioUrl} className="mt-4 w-full" />
          )}
        </div>
      </div>
      <footer className="mt-8 text-gray-400 text-xs">&copy; {new Date().getFullYear()} Voice Assistant Powered by Sarvam AI & Groq</footer>
      {/* Animations CSS */}
      <style>{`
        .animate-fade-in {
          animation: fadeIn 0.7s;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .overflow-hidden {
          overflow: hidden !important;
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #c7d2fe;
          border-radius: 4px;
        }
        .custom-scrollbar {
          scrollbar-width: thin;
          scrollbar-color: #c7d2fe #f1f5f9;
        }
      `}</style>
    </div>
  )
}

export default App
