import React, { useState } from 'react';
import Layout from './components/Layout';
import ChatInterface from './components/ChatInterface';
import DocumentWorkspace from './components/DocumentWorkspace';

function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocuments, setSelectedDocuments] = useState([]);

  return (
    <Layout>
      <DocumentWorkspace
        documents={documents}
        onDocumentsChange={setDocuments}
        selectedDocuments={selectedDocuments}
        onSelectionChange={setSelectedDocuments}
      />
      <ChatInterface
        selectedDocuments={selectedDocuments}
        documents={documents}
      />
    </Layout>
  );
}

export default App;
