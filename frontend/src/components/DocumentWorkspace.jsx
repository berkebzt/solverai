import React, { useEffect, useState } from 'react';
import { Upload, FileText, RefreshCw, Trash2, RotateCcw, CheckCircle2, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || '';

const DocumentWorkspace = ({
  documents = [],
  onDocumentsChange = () => {},
  selectedDocuments = [],
  onSelectionChange = () => {},
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/documents`);
      if (!res.ok) throw new Error('Failed to fetch documents');
      const data = await res.json();
      onDocumentsChange(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const formatSize = (bytes) => {
    if (!bytes) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  const handleFile = async (file) => {
    if (!file) return;
    setUploading(true);
    setError('');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Upload failed');
      await fetchDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await fetch(`${API_BASE}/documents/${docId}`, { method: 'DELETE' });
      onSelectionChange(selectedDocuments.filter((id) => id !== docId));
      await fetchDocuments();
    } catch (err) {
      setError('Failed to delete');
    }
  };

  const toggleSelection = (docId) => {
    if (selectedDocuments.includes(docId)) {
      onSelectionChange(selectedDocuments.filter((id) => id !== docId));
    } else {
      onSelectionChange([...selectedDocuments, docId]);
    }
  };

  return (
    <div className="doc-workspace">
      <div className="doc-header" onClick={() => setIsOpen(!isOpen)}>
        <div className="doc-title">
          <FileText size={16} />
          <h2>Documents</h2>
          {selectedDocuments.length > 0 && (
            <span className="doc-badge">{selectedDocuments.length} selected</span>
          )}
        </div>
        <div className="doc-actions">
          <button onClick={(e) => { e.stopPropagation(); fetchDocuments(); }}>
            <RefreshCw size={14} />
          </button>
          <span className="doc-toggle">
            {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </span>
        </div>
      </div>

      {isOpen && (
        <div className="doc-body">
          <div
            className={`doc-upload-zone ${dragActive ? 'active' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => { e.preventDefault(); setDragActive(false); handleFile(e.dataTransfer.files[0]); }}
          >
            <input
              id="doc-upload"
              type="file"
              accept=".pdf,.txt"
              style={{ display: 'none' }}
              onChange={(e) => handleFile(e.target.files[0])}
            />
            <label htmlFor="doc-upload" style={{ cursor: 'pointer', display: 'block' }}>
              <Upload size={18} />
              <span>{uploading ? 'Uploading...' : 'Drop PDF/TXT or click'}</span>
            </label>
          </div>

          {error && <div className="doc-error">{error}</div>}

          <div className="doc-list">
            {documents.length === 0 ? (
              <div className="doc-empty">No documents yet</div>
            ) : (
              documents.map((doc) => (
                <div key={doc.id} className={`doc-item ${selectedDocuments.includes(doc.id) ? 'selected' : ''}`}>
                  <div className="doc-item-header">
                    <div className="doc-item-info">
                      <h3>{doc.original_filename}</h3>
                      <span className="doc-item-meta">{doc.chunk_count} chunks · {formatSize(doc.size_bytes)}</span>
                    </div>
                    <div className={`doc-item-status ${doc.status}`}>
                      {doc.status === 'ready' ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                      <span>{doc.status}</span>
                    </div>
                  </div>
                  <div className="doc-item-actions">
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        className={`select-btn ${selectedDocuments.includes(doc.id) ? 'selected' : ''}`}
                        onClick={() => toggleSelection(doc.id)}
                      >
                        {selectedDocuments.includes(doc.id) ? 'Selected' : 'Select'}
                      </button>
                      <button className="delete-btn" onClick={() => handleDelete(doc.id)}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentWorkspace;
