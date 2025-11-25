import React, { useState, useRef } from 'react';
import { Upload, File, CheckCircle, AlertCircle, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const RagUpload = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, uploading, success, error
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === 'application/pdf') {
      setFile(droppedFile);
      setStatus('idle');
    }
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setStatus('idle');
    }
  };

  const uploadFile = async () => {
    if (!file) return;

    setStatus('uploading');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Upload failed');

      setStatus('success');
      setTimeout(() => {
        setFile(null);
        setStatus('idle');
      }, 3000);
    } catch (error) {
      console.error('Upload error:', error);
      setStatus('error');
    }
  };

  return (
    <div className="absolute top-6 right-6 z-10">
      <AnimatePresence>
        {!file ? (
          <motion.button
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            onClick={() => fileInputRef.current?.click()}
            className="glass p-3 rounded-full hover:bg-white/10 transition-colors group relative"
            title="Upload Document"
          >
            <Upload size={20} className="text-cyan-400 group-hover:text-white transition-colors" />
            <span className="absolute right-full mr-3 top-1/2 -translate-y-1/2 px-2 py-1 bg-black/80 text-xs rounded text-white opacity-0 group-hover:opacity-100 whitespace-nowrap transition-opacity pointer-events-none">
              Upload PDF
            </span>
          </motion.button>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="glass p-4 rounded-xl w-72 shadow-2xl backdrop-blur-xl border border-cyan-500/30"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2 overflow-hidden">
                <div className="p-2 bg-cyan-500/20 rounded-lg">
                  <File size={18} className="text-cyan-400" />
                </div>
                <span className="text-sm font-medium truncate text-gray-200">{file.name}</span>
              </div>
              <button 
                onClick={() => setFile(null)} 
                className="text-gray-500 hover:text-white transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            {status === 'idle' && (
              <button
                onClick={uploadFile}
                className="w-full py-2 bg-gradient-to-r from-cyan-600 to-blue-600 rounded-lg text-sm font-semibold text-white hover:shadow-[0_0_15px_rgba(0,240,255,0.4)] transition-all"
              >
                Ingest Document
              </button>
            )}

            {status === 'uploading' && (
              <div className="space-y-2">
                <div className="h-1 w-full bg-gray-700 rounded-full overflow-hidden">
                  <motion.div 
                    className="h-full bg-cyan-400"
                    initial={{ width: "0%" }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 1.5, ease: "easeInOut" }}
                  />
                </div>
                <p className="text-xs text-center text-cyan-400 animate-pulse">Processing vector embeddings...</p>
              </div>
            )}

            {status === 'success' && (
              <div className="flex items-center justify-center gap-2 text-green-400 py-1">
                <CheckCircle size={18} />
                <span className="text-sm font-medium">Ingestion Complete</span>
              </div>
            )}

            {status === 'error' && (
              <div className="flex items-center justify-center gap-2 text-red-400 py-1">
                <AlertCircle size={18} />
                <span className="text-sm font-medium">Upload Failed</span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept=".pdf"
        className="hidden"
      />
    </div>
  );
};

export default RagUpload;
