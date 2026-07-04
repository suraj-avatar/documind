import { useState } from 'react';
import { ChevronDown, FileText, BookOpen } from 'lucide-react';

export default function SourceCards({ sources }) {
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  // Deduplicate by source+page combination
  const unique = sources.reduce((acc, src) => {
    const key = `${src.source}|${src.page}`;
    if (!acc.seen.has(key)) {
      acc.seen.add(key);
      acc.list.push(src);
    }
    return acc;
  }, { seen: new Set(), list: [] }).list;

  const getFilename = (path) => {
    if (!path) return 'Unknown';
    return path.split(/[\\/]/).pop() || path;
  };

  return (
    <div className="sources-section">
      <button
        className={`sources-toggle ${open ? 'open' : ''}`}
        onClick={() => setOpen(!open)}
        id="toggle-sources-btn"
      >
        <BookOpen size={12} />
        {unique.length} source{unique.length !== 1 ? 's' : ''} cited
        <ChevronDown size={12} />
      </button>

      {open && (
        <div className="sources-list">
          {unique.map((src, i) => (
            <div key={i} className="source-card" title={src.source}>
              <FileText size={11} />
              <span className="source-filename">{getFilename(src.source)}</span>
              {src.page !== undefined && src.page !== '' && (
                <span className="source-page">p.{src.page}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
