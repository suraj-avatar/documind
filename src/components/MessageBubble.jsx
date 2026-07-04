import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import SourceCards from './SourceCards';

const AI_AVATAR = '✦';
const USER_AVATAR = '👤';

function TypingIndicator() {
  return (
    <div className="typing-indicator">
      <div className="typing-dot" />
      <div className="typing-dot" />
      <div className="typing-dot" />
    </div>
  );
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const isLoading = message.loading;

  return (
    <div className={`message-row ${isUser ? 'user' : 'ai'}`}>
      {/* Avatar */}
      <div className={`avatar ${isUser ? 'user' : 'ai'}`}>
        {isUser ? USER_AVATAR : AI_AVATAR}
      </div>

      {/* Bubble */}
      <div className="bubble">
        {isUser ? (
          <div className="bubble-user">{message.content}</div>
        ) : (
          <div className="bubble-ai">
            {isLoading ? (
              <TypingIndicator />
            ) : (
              <>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
                {message.sources && message.sources.length > 0 && (
                  <SourceCards sources={message.sources} />
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
