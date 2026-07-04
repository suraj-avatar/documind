import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';

const SUGGESTIONS = [
  'Summarize the main topics covered in these documents',
  'What are the key requirements mentioned?',
  'List all the important definitions found',
  'What are the main conclusions or recommendations?',
];

export default function ChatWindow({ messages, onSuggestionClick }) {
  const bottomRef = useRef(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="messages-list">
        <div className="empty-state">
          <div className="empty-icon">✦</div>
          <h1 className="empty-title">DocuMind</h1>
          <p className="empty-sub">
            Upload your PDF documents using the sidebar, then ask any question
            about their contents. Answers are grounded in your documents — no hallucinations.
          </p>
          <div className="suggestion-chips">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                className="chip"
                onClick={() => onSuggestionClick(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="messages-list">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
