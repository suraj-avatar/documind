import { useEffect, useState } from 'react';
import { Plus, Upload, FileText, Database, MessageSquare } from 'lucide-react';
import { getHealth } from '../api/client';

export default function Sidebar({ docs, onNewChat, onUploadClick, sessionCount }) {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [docs]); // re-check after uploads

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">✦</div>
          <div>
            <div className="logo-text">DocuMind</div>
            <div className="logo-sub">RAG Intelligence</div>
          </div>
        </div>

        <button id="new-chat-btn" className="btn-new-chat" onClick={onNewChat}>
          <Plus size={15} />
          New Chat
        </button>
      </div>

      {/* Documents section */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">📂 Documents</div>

        <button
          id="upload-docs-btn"
          className="btn-upload-sidebar"
          onClick={onUploadClick}
        >
          <Upload size={14} />
          Upload PDFs
        </button>

        {docs.length === 0 ? (
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '12px' }}>
            No documents yet.<br />Upload a PDF to get started.
          </p>
        ) : (
          docs.map((name, i) => (
            <div key={i} className="doc-item">
              <div className="doc-icon"><FileText size={13} /></div>
              <span className="doc-name" title={name}>{name}</span>
              <span className="doc-badge">✓</span>
            </div>
          ))
        )}
      </div>

      {/* Stats */}
      {health && (
        <div style={{ padding: '0 20px 12px' }}>
          <div className="sidebar-section-title">📊 Stats</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
              <Database size={12} style={{ color: 'var(--accent-cyan)' }} />
              {health.vectorstore_chunks?.toLocaleString() ?? '—'} chunks indexed
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
              <MessageSquare size={12} style={{ color: 'var(--accent-violet-l)' }} />
              {sessionCount} message{sessionCount !== 1 ? 's' : ''} this session
            </div>
          </div>
        </div>
      )}

      {/* Health footer */}
      <div className="sidebar-footer">
        <div className="health-indicator">
          <div className={`health-dot ${health ? '' : 'offline'}`} />
          {health ? `API online · ${health.llm_model ?? 'Llama 3.1'}` : 'API offline'}
        </div>
      </div>
    </aside>
  );
}
