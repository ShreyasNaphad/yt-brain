import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Loader2, Link2, AlertCircle } from 'lucide-react';
import axios from 'axios';

const URLInput = ({ onMetadataLoaded, onProcessingStart }) => {
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [loadingText, setLoadingText] = useState("Extracting transcript...");

    const loadingMessages = [
        "🔍 Fetching video info...",
        "📝 Extracting transcript...",
        "🧠 Building knowledge base...",
        "✅ Almost ready..."
    ];

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!url.trim()) return;

        setLoading(true);
        setError(null);
        onProcessingStart();

        // Cycle loading messages locally to keep user engaged
        let msgIndex = 0;
        const interval = setInterval(() => {
            msgIndex = (msgIndex + 1) % loadingMessages.length;
            setLoadingText(loadingMessages[msgIndex]);
        }, 3000);

        try {
            // One big request - wait up to 60s
            // status is returned in the response
            const response = await axios.post(
                (import.meta.env.DEV ? 'http://localhost:8000' : '') + '/api/video/process',
                { url },
                { timeout: 300000 } // 5m timeout
            );

            clearInterval(interval);
            setLoadingText("✅ Ready to chat!");

            setTimeout(() => {
                onMetadataLoaded(response.data);
                setLoading(false);
            }, 500);

        } catch (err) {
            clearInterval(interval);
            console.error(err);
            let errorMessage = "Failed to process video.";
            if (err.code === 'ECONNABORTED') {
                errorMessage = "Request timed out. The video is too long or server is busy.";
            } else if (err.response) {
                errorMessage = err.response.data?.detail || `Server Error (${err.response.status})`;
            } else if (err.request) {
                errorMessage = "Network Error - Backend unreachable.";
            } else {
                errorMessage = err.message || "Unknown Error";
            }
            setError(errorMessage);
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="max-w-3xl w-full space-y-8"
            >
                {/* Helper Badge */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.2 }}
                    className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-game-cyan text-sm mb-4"
                >
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-game-cyan opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-game-cyan"></span>
                    </span>
                    AI-Powered Learning Engine
                </motion.div>

                {/* Hero Text */}
                <h1 className="text-5xl md:text-7xl font-bold tracking-tight">
                    Drop a YouTube Link. <br />
                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-game-purple via-game-pink to-game-gold animate-gradient">
                        Master It.
                    </span>
                </h1>

                <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                    Turn any video into an interactive learning experience with AI chat, smart summaries, and gamified quizzes.
                </p>

                {/* Input Form */}
                <form onSubmit={handleSubmit} className="relative max-w-xl mx-auto mt-12 group">
                    <div className="absolute inset-0 bg-gradient-to-r from-game-purple to-game-pink rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                    <div className="relative flex items-center bg-game-card border border-game-border rounded-2xl p-2 shadow-2xl focus-within:border-game-purple/50 transition duration-300">
                        <div className="pl-4 text-gray-500">
                            <Link2 size={24} />
                        </div>
                        <input
                            type="text"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="Paste YouTube URL here..."
                            className="flex-1 bg-transparent border-none outline-none text-white placeholder-gray-500 text-lg px-4 py-3 min-w-0"
                            disabled={loading}
                        />
                        <button
                            type="submit"
                            disabled={loading || !url.trim()}
                            className="bg-gradient-to-r from-game-purple to-game-pink text-white px-6 py-3 rounded-xl font-semibold flex items-center gap-2 hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? (
                                <Loader2 className="animate-spin" size={20} />
                            ) : (
                                <>
                                    Analyze <ArrowRight size={20} />
                                </>
                            )}
                        </button>
                    </div>
                </form>

                {/* Loading State */}
                <AnimatePresence>
                    {loading && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="mt-4"
                        >
                            <div className="flex items-center justify-center gap-2 text-game-cyan font-medium">
                                <Loader2 size={16} className="animate-spin" />
                                <motion.span
                                    key={loadingText}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                >
                                    {loadingText}
                                </motion.span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Error Message */}
                <AnimatePresence>
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 flex items-center justify-center gap-2"
                        >
                            <AlertCircle size={20} />
                            {error}
                        </motion.div>
                    )}
                </AnimatePresence>

            </motion.div>
        </div>
    );
};

export default URLInput;
