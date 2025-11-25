import React from 'react';
import Layout from './components/Layout';
import ChatInterface from './components/ChatInterface';
import RagUpload from './components/RagUpload';

function App() {
  return (
    <Layout>
      <div className="relative h-full">
        <RagUpload />
        <ChatInterface />
      </div>
    </Layout>
  );
}

export default App;
