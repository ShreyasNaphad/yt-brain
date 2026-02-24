import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Layout from './components/Layout';
import URLInput from './components/URLInput';
import VideoCard from './components/VideoCard';
import ChatInterface from './components/ChatInterface';
import SummaryView from './components/SummaryView';
import GameView from './components/GameView';
import { ChevronLeft } from 'lucide-react';
import { VideoProvider, useVideo } from './context/VideoContext';
import { ToastProvider } from './components/Toast';
import ErrorBoundary from './components/ErrorBoundary';

function AppContent() {
  const { view, setView, videoData, navigate, initialChatMessage } = useVideo();

  const handleMetadataLoaded = (data) => {
    // navigate sets videoData internally if we want, but our context logic might need adjustment
    // Actually, in context we have setVideoData.
    // Let's rely on component calling setVideoData, or helper in context.
    // For now, URLInput calls onMetadataLoaded, which we handle here.
    // Better: URLInput updates context directly? 
    // Let's keep URLInput emitting events for now to minimize refactor there, 
    // or update here to call context setters.
  };

  // URLInput is likely calling onMetadataLoaded with data.
  // We need to pass a handler that updates context.

  return (
    <Layout>
      <AnimatePresence mode="wait">

        {/* HOME / PROCESSING VIEW */}
        {(view === 'home' || view === 'processing') && (
          <motion.div
            key="home"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="w-full"
          >
            <URLInput
              onMetadataLoaded={(data) => {
                // We need access to setVideoData from context, which we have.
                // But we can't call it if we destructured navigate only? 
                // We destructured everything needed.
                // We need to update context state.
                // Actually URLInput prop names: onMetadataLoaded, onProcessingStart
              }}
            // We'll wrap URLInput logic inside a wrapper or just pass context methods if we modify URLInput.
            // To avoid modifying URLInput too much, let's just handle it here.
            />
            {/* 
               Wait, URLInput needs to update videoData in context. 
               We should pass a handler that does that.
            */}
          </motion.div>
        )}
        {/* ... */}
      </AnimatePresence>
    </Layout>
  );
}

// Re-writing App component completely to avoid confusion with partial replacement
function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <VideoProvider>
          <MainContent />
        </VideoProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}

function MainContent() {
  const {
    view,
    videoData,
    setVideoData,
    setView,
    navigate,
    initialChatMessage
  } = useVideo();

  const handleMetadataLoaded = (data) => {
    setVideoData(data);
    navigate('video');
  };

  const handleProcessingStart = () => {
    setView('processing');
  };

  return (
    <Layout>
      <AnimatePresence mode="wait">

        {/* HOME / PROCESSING VIEW */}
        {(view === 'home' || view === 'processing') && (
          <motion.div
            key="home"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="w-full"
          >
            <URLInput
              onMetadataLoaded={handleMetadataLoaded}
              onProcessingStart={handleProcessingStart}
            />
          </motion.div>
        )}

        {/* VIDEO DASHBOARD VIEW */}
        {view === 'video' && videoData && (
          <motion.div
            key="video"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="w-full space-y-8"
          >
            <button
              onClick={() => navigate('home')}
              className="flex items-center gap-2 text-gray-400 hover:text-game-cyan transition-colors"
            >
              <ChevronLeft size={20} /> Back to Search
            </button>

            <VideoCard
              metadata={videoData}
              onStartChat={() => navigate('chat')}
              onStartSummary={() => navigate('summary')}
              onStartGame={() => navigate('game')}
            />
          </motion.div>
        )}

        {/* CHAT VIEW */}
        {view === 'chat' && videoData && (
          <motion.div
            key="chat"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full"
          >
            <ChatInterface
              videoId={videoData.video_id}
              metadata={videoData}
              onBack={() => navigate('video')}
              onGoHome={() => navigate('home')}
              initialMessage={initialChatMessage}
            />
          </motion.div>
        )}

        {/* SUMMARY VIEW */}
        {view === 'summary' && videoData && (
          <motion.div
            key="summary"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full"
          >
            <SummaryView
              videoId={videoData.video_id}
              metadata={videoData}
              onBack={() => navigate('video')}
              onGoHome={() => navigate('home')}
            />
          </motion.div>
        )}

        {/* GAME VIEW */}
        {view === 'game' && videoData && (
          <motion.div
            key="game"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full"
          >
            <GameView
              videoId={videoData.video_id}
              metadata={videoData}
              onBack={() => navigate('video')}
              onGoHome={() => navigate('home')}
            />
          </motion.div>
        )}

      </AnimatePresence>
    </Layout>
  );
}

export default App;
