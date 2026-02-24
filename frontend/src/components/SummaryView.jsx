import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Brain, Microscope, Lightbulb, Clock, Check, Copy, CheckCheck, Home } from 'lucide-react';
import { getSummary } from '../api/client';

const SummaryView = ({ videoId, metadata, onBack, onGoHome }) => {
    const [activeTab, setActiveTab] = useState('overview');
    const [summaryData, setSummaryData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                const data = await getSummary(videoId);
                // Ensure data has required fields with defaults
                const safeSummary = {
                    overview: data?.overview || "No overview available.",
                    deep_concepts: Array.isArray(data?.deep_concepts) ? data.deep_concepts : [],
                    actionable_takeaways: Array.isArray(data?.actionable_takeaways) ? data.actionable_takeaways : []
                };
                setSummaryData(safeSummary);
            } catch (err) {
                console.error(err);
                setError("Failed to load summary. The video might not be fully processed yet.");
            } finally {
                setLoading(false);
            }
        };
        fetchSummary();
    }, [videoId]);

    const handleCopyTakeaways = () => {
        if (!summaryData) return;
        const text = summaryData.actionable_takeaways.map(t => `• ${t}`).join('\n');
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const formatTime = (seconds) => {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    const TabButton = ({ id, label, icon: Icon }) => (
        <button
            onClick={() => setActiveTab(id)}
            className={`relative flex items-center gap-2 px-6 py-3 rounded-xl transition-all duration-300 ${activeTab === id
                ? 'text-white bg-white/10'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
        >
            <Icon size={18} />
            <span className="font-medium">{label}</span>
            {activeTab === id && (
                <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-game-purple to-game-pink rounded-full"
                />
            )}
        </button>
    );

    if (loading) {
        return (
            <div className="w-full max-w-6xl mx-auto min-h-[600px] p-8">
                <div className="animate-pulse space-y-8">
                    <div className="h-8 w-1/3 bg-white/10 rounded-lg"></div>
                    <div className="flex gap-4">
                        <div className="h-12 w-32 bg-white/10 rounded-xl"></div>
                        <div className="h-12 w-32 bg-white/10 rounded-xl"></div>
                        <div className="h-12 w-32 bg-white/10 rounded-xl"></div>
                    </div>
                    <div className="h-64 w-full bg-white/10 rounded-2xl"></div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
                <div className="text-red-400 mb-4 text-xl">⚠️ {error}</div>
                <button onClick={onBack} className="text-game-cyan hover:underline">Go Back</button>
            </div>
        );
    }

    return (
        <div className="w-full max-w-6xl mx-auto pb-12">
            {/* Header */}
            <div className="mb-8 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onBack}
                        className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
                        title="Back to Dashboard"
                    >
                        <ArrowLeft size={24} />
                    </button>
                    <button
                        onClick={onGoHome}
                        className="p-2 rounded-lg hover:bg-game-pink/20 text-gray-400 hover:text-game-pink transition-colors"
                        title="New Video"
                    >
                        <Home size={24} />
                    </button>
                    <div>
                        <h1 className="text-2xl font-bold text-white leading-tight">{metadata.title}</h1>
                        <p className="text-gray-400 text-sm">AI Generated Summary</p>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex flex-wrap gap-2 mb-8 border-b border-white/5 pb-1">
                <TabButton id="overview" label="Overview" icon={Brain} />
                <TabButton id="concepts" label="Deep Concepts" icon={Microscope} />
                <TabButton id="takeaways" label="Takeaways" icon={Lightbulb} />
            </div>

            {/* Content Area */}
            <AnimatePresence mode="wait">

                {/* OVERVIEW TAB */}
                {activeTab === 'overview' && (
                    <motion.div
                        key="overview"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.3 }}
                        className="bg-game-card border border-game-border rounded-3xl p-8 shadow-2xl relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 w-64 h-64 bg-game-purple/10 blur-[80px] pointer-events-none" />
                        <div className="relative z-10 border-l-4 border-game-purple pl-6 py-2">
                            <h3 className="text-lg font-bold text-game-purple mb-4 uppercase tracking-wider">Executive Summary</h3>
                            <p className="text-lg md:text-xl leading-relaxed text-gray-200">
                                {summaryData.overview}
                            </p>
                        </div>
                    </motion.div>
                )}

                {/* DEEP CONCEPTS TAB */}
                {activeTab === 'concepts' && (
                    <motion.div
                        key="concepts"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.98 }}
                        className="grid grid-cols-1 md:grid-cols-2 gap-6"
                    >
                        {summaryData.deep_concepts.map((concept, idx) => (
                            <motion.div
                                key={idx}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.1 }}
                                className="group relative bg-game-card/50 border border-white/5 rounded-2xl p-6 hover:border-game-purple/50 hover:bg-game-card hover:shadow-[0_0_20px_rgba(124,58,237,0.1)] transition-all duration-300"
                            >
                                <div className="flex justify-between items-start mb-3">
                                    <h3 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400 group-hover:from-game-cyan group-hover:to-game-purple transition-all duration-300">
                                        {concept.name}
                                    </h3>
                                    <a
                                        href={`https://youtu.be/${videoId}?t=${Math.floor(concept.start_time)}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="px-2 py-1 rounded bg-white/5 hover:bg-game-purple text-xs text-game-purple hover:text-white font-mono transition-colors flex items-center gap-1"
                                    >
                                        <Clock size={12} /> {formatTime(concept.start_time)}
                                    </a>
                                </div>
                                <p className="text-gray-400 leading-relaxed group-hover:text-gray-300 transition-colors">
                                    {concept.explanation}
                                </p>
                            </motion.div>
                        ))}
                    </motion.div>
                )}

                {/* TAKEAWAYS TAB */}
                {activeTab === 'takeaways' && (
                    <motion.div
                        key="takeaways"
                        initial={{ opacity: 0, x: 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -10 }}
                        className="bg-game-card border border-game-border rounded-3xl p-8 relative"
                    >
                        <div className="space-y-4">
                            {summaryData.actionable_takeaways.map((item, idx) => (
                                <motion.div
                                    key={idx}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: idx * 0.1 }}
                                    className="flex items-start gap-4 p-4 rounded-xl bg-white/5 hover:bg-white/10 transition-colors"
                                >
                                    <div className="mt-1 p-1 rounded-full bg-game-green/20 text-game-green">
                                        <Check size={16} strokeWidth={3} />
                                    </div>
                                    <p className="text-lg text-gray-200 font-medium">{item}</p>
                                </motion.div>
                            ))}
                        </div>

                        <div className="mt-8 flex justify-end">
                            <button
                                onClick={handleCopyTakeaways}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-game-purple text-white hover:bg-game-pink transition-colors font-medium"
                            >
                                {copied ? <CheckCheck size={18} /> : <Copy size={18} />}
                                {copied ? "Copied!" : "Copy Takeaways"}
                            </button>
                        </div>
                    </motion.div>
                )}

            </AnimatePresence>
        </div>
    );
};

export default SummaryView;
