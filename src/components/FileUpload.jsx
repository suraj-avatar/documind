import { useState, useRef } from 'react';
import { Upload, X, FileText, Loader2 } from 'lucide-react';
import { uploadFiles } from '../api/client';

export default function FileUpload({ onClose, onUploadSuccess }) {
  const [files, setFiles] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef(null);

  const addFiles = (newFiles) => {
    const pdfs = Array.from(newFiles).filter(
      (f) => f.type === 'application/pdf'
    );
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...pdfs.filter((f) => !existing.has(f.name))];
    });
  };

  const removeFile = (name) =>
    setFiles((prev) => prev.filter((f) => f.name !== name));

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(e.dataTransfer.files);
  };

  const handleSubmit = async () => {
    if (!files.length) return;
    setUploading(true);
    try {
      const result = await uploadFiles(files);
      onUploadSuccess(result, files.map((f) => f.name));
      onClose();
    } catch (err) {
      onUploadSuccess(null, [], err.message);
      onClose();
    } finally {
      setUploading(false);
    }
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        {/* Header */}
        <div className="modal-header">
          <span className="modal-title">📎 Upload Documents</span>
          <button id="close-upload-modal" className="btn-close" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        {/* Drop zone */}
        <div
          className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            multiple
            onChange={(e) => addFiles(e.target.files)}
            style={{ display: 'none' }}
          />
          <div className="drop-icon">
            <Upload size={24} />
          </div>
          <p className="drop-text">Drop PDF files here</p>
          <p className="drop-hint">or click to browse · PDF only · max 50 MB each</p>
        </div>

        {/* File list */}
        {files.length > 0 && (
          <div className="file-list">
            {files.map((file) => (
              <div key={file.name} className="file-item">
                <FileText size={16} className="file-item-icon" />
                <span className="file-item-name">{file.name}</span>
                <span className="file-item-size">{formatSize(file.size)}</span>
                <button
                  id={`remove-file-${file.name}`}
                  className="btn-remove-file"
                  onClick={() => removeFile(file.name)}
                  disabled={uploading}
                >
                  <X size={13} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Upload button */}
        <button
          id="submit-upload-btn"
          className="btn-upload-submit"
          onClick={handleSubmit}
          disabled={!files.length || uploading}
        >
          {uploading ? (
            <><Loader2 size={16} className="spin" /> Ingesting…</>
          ) : (
            <><Upload size={16} /> Ingest {files.length} File{files.length !== 1 ? 's' : ''}</>
          )}
        </button>

        {uploading && <div className="upload-progress"><div className="upload-progress-bar" /></div>}
      </div>
    </div>
  );
}
