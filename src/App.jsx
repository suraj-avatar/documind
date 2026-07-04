import { useState, useRef, useCallback, useEffect } from 'react';
import { Send } from 'lucide-react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import FileUpload from './components/FileUpload';
import { askQuestion } from './api/client';

let msgIdCounter = 0;
const newId = () => ++msgIdCounter;

function generateSessionId() {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [docs, setDocs] = useState([]);
  const [toast, setToast] = useState(null);
  const [sessionId] = useState(generateSessionId);
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    }
  }, [input]);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const addMessage = (role, content, extras = {}) => {
    const id = newId();
    setMessages((prev) => [...prev, { id, role, content, ...extras }]);
    return id;
  };

  const updateMessage = (id, updates) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...updates } : m))
    );
  };

  const handleSend = useCallback(async (questionOverride) => {
    const question = (questionOverride ?? input).trim();
    if (!question || loading) return;

    setInput('');
    addMessage('user', question);

    const aiId = newId();
    setMessages((prev) => [...prev, { id: aiId, role: 'assistant', content: '', loading: true }]);
    setLoading(true);

    try {
      const data = await askQuestion(question, sessionId);
      updateMessage(aiId, {
        content: data.answer,
        sources: data.sources,
        loading: false,
      });
    } catch (err) {
      updateMessage(aiId, {
        content: `⚠️ Error: ${err.message}`,
        loading: false,
      });
    } finally {
      setLoading(false);
    }
  }, [input, loading, sessionId]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setInput('');
  };

  const handleUploadSuccess = (result, filenames, errorMsg) => {
    if (!result) {
      showToast(`Upload failed: ${errorMsg}`, 'error');
      return;
    }
    setDocs((prev) => [...new Set([...prev, ...filenames])]);
    showToast(
      `✓ Ingested ${result.files_ingested} file(s) · ${result.chunks_added} chunks added`,
      'success'
    );
  };

  const totalMessages = messages.filter((m) => m.role === 'user').length;

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <Sidebar
        docs={docs}
        onNewChat={handleNewChat}
        onUploadClick={() => setShowUpload(true)}
        sessionCount={totalMessages}
      />

      {/* Main chat */}
      <div className="chat-area">
        {/* Header */}
        <div className="chat-header">
          <div>
            <div className="chat-header-title">AI Document Assistant</div>
            <div className="chat-header-sub">
              {docs.length > 0
                ? `${docs.length} document${docs.length !== 1 ? 's' : ''} loaded`
                : 'Upload documents to get started'}
            </div>
          </div>
        </div>

        {/* Messages */}
        <ChatWindow
          messages={messages}
          onSuggestionClick={(s) => handleSend(s)}
        />

        {/* Input area */}
        <div className="input-area">
          <div className="input-wrapper">
            <textarea
              id="chat-input"
              ref={textareaRef}
              className="input-textarea"
              placeholder={
                docs.length > 0
                  ? 'Ask anything about your documents…'
                  : 'Upload a PDF first, then ask your question…'
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button
              id="send-btn"
              className="btn-send"
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              title="Send (Enter)"
            >
              <Send size={15} />
            </button>
          </div>
          <p className="input-hint">
            Press <strong>Enter</strong> to send · <strong>Shift+Enter</strong> for new line
          </p>
        </div>
      </div>

      {/* Upload modal */}
      {showUpload && (
        <FileUpload
          onClose={() => setShowUpload(false)}
          onUploadSuccess={handleUploadSuccess}
        />
      )}

      {/* Toast */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.msg}
        </div>
      )}
    </div>
  );
}
