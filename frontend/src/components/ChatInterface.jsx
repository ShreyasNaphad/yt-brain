import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, ArrowLeft, Bot, User, Clock, ExternalLink, Loader2, Home } from 'lucide-react';
import { sendChat } from '../api/client';

const ChatInterface = ({ videoId, metadata, onBack, onGoHome, initialMessage = '' }) => {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Hi! I\'ve analyzed this video. Ask me anything about it!' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [currentSources, setCurrentSources] = useState([]);
    const chatContainerRef = useRef(null);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        if (chatContainerRef.current) {
            chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        }
    };

    useEffect(() => {
        if (initialMessage) {
            setInput(initialMessage);
        }
    }, [initialMessage]);

    useEffect(() => {
        scrollToBottom();
    }, [messages, loading]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);
        setCurrentSources([]); // Reset sources for new answer

        try {
            // Send the current user message with recent history for context
            const history = messages.slice(-6).map(m => ({ role: m.role, content: m.content }));

            const response = await sendChat(videoId, input, history);

            const aiMsg = {
                role: 'assistant',
                content: response.answer,
                sources: response.sources
            };

            setMessages(prev => [...prev, aiMsg]);
            if (response.sources) {
                setCurrentSources(response.sources);
            }
        } catch (error) {
            console.error(error);
            setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error. Please try again." }]);
        } finally {
            setLoading(false);
        }
    };

    const formatTime = (seconds) => {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    return (
        <div className="flex h-[calc(100vh-theme(spacing.24))] max-h-[900px] w-full max-w-7xl mx-auto bg-game-card border border-game-border rounded-3xl overflow-hidden shadow-2xl">

            {/* LEFT PANEL: Metadata & Citation Sources */}
            <div className="w-[35%] border-r border-white/5 bg-game-darker/50 p-6 flex flex-col gap-6 hidden md:flex">
                <div>
                    <div className="flex gap-4 items-center mb-6 text-sm">
                        <button
                            onClick={onBack}
                            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors group"
                        >
                            <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                            Dashboard
                        </button>
                        <div className="w-px h-4 bg-white/20"></div>
                        <button
                            onClick={onGoHome}
                            className="flex items-center gap-2 text-gray-400 hover:text-game-pink transition-colors group"
                        >
                            <Home size={16} className="group-hover:-translate-y-0.5 transition-transform" />
                            New Video
                        </button>
                    </div>

                    <div className="relative aspect-video rounded-xl overflow-hidden border border-game-purple/30 shadow-lg mb-4">
                        <img src={metadata.thumbnail_url} alt={metadata.title} className="w-full h-full object-cover" />
                        <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                            <a
                                href={`https://www.youtube.com/watch?v=${videoId}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="bg-red-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 font-bold hover:bg-red-700 transition"
                            >
                                <ExternalLink size={16} /> Watch on YouTube
                            </a>
                        </div>
                    </div>

                    <h2 className="text-xl font-bold leading-tight text-white mb-2">{metadata.title}</h2>
                    <p className="text-sm text-gray-400">{metadata.channel}</p>
                </div>

                <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                    <h3 className="text-sm font-bold text-game-cyan uppercase tracking-wider mb-3 flex items-center gap-2">
                        <Clock size={14} /> Context Sources
                    </h3>

                    {currentSources.length > 0 ? (
                        <div className="space-y-3">
                            {currentSources.map((source, idx) => (
                                <div key={idx} className="p-3 rounded-lg bg-white/5 border border-white/5 hover:border-game-purple/50 transition-colors">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs font-mono text-game-purple bg-game-purple/10 px-2 py-0.5 rounded">
                                            Source #{idx + 1}
                                        </span>
                                        <a
                                            href={`https://youtu.be/${videoId}?t=${Math.floor(source.start_time || 0)}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex items-center gap-1 text-xs text-game-cyan hover:underline"
                                        >
                                            <Clock size={12} /> {formatTime(source.start_time || 0)}
                                        </a>
                                    </div>
                                    <p className="text-xs text-gray-300 line-clamp-3 italic">"{source.text}..."</p>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-10 text-gray-600 text-sm italic">
                            Ask a question to see semantically relevant video segments here.
                        </div>
                    )}
                </div>
            </div>

            {/* RIGHT PANEL: Chat */}
            <div className="flex-1 flex flex-col bg-game-dark">
                {/* Mobile Header */}
                <div className="md:hidden p-4 border-b border-white/5 flex items-center justify-between">
                    <button onClick={onBack} className="p-2 text-gray-400 hover:text-white">
                        <ArrowLeft size={20} />
                    </button>
                    <span className="font-bold truncate text-sm px-4 flex-1 text-center">{metadata.title}</span>
                    <button onClick={onGoHome} className="p-2 text-gray-400 hover:text-game-pink">
                        <Home size={20} />
                    </button>
                </div>

                {/* Messages */}
                <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 custom-scrollbar">
                    {messages.map((msg, i) => (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`flex items-start gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                        >
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'assistant' ? 'bg-game-cyan/20 text-game-cyan' : 'bg-game-purple/20 text-game-purple'
                                }`}>
                                {msg.role === 'assistant' ? <Bot size={18} /> : <User size={18} />}
                            </div>

                            <div className={`max-w-[80%] rounded-2xl p-4 ${msg.role === 'user'
                                ? 'bg-gradient-to-br from-game-purple to-game-pink text-white rounded-tr-none'
                                : 'bg-game-card border-l-4 border-game-cyan text-gray-200 rounded-tl-none'
                                }`}>
                                <p className="whitespace-pre-wrap leading-relaxed text-sm md:text-base">{msg.content}</p>
                            </div>
                        </motion.div>
                    ))}

                    {loading && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex items-start gap-4"
                        >
                            <div className="w-8 h-8 rounded-full bg-game-cyan/20 text-game-cyan flex items-center justify-center shrink-0">
                                <Bot size={18} />
                            </div>
                            <div className="bg-game-card border-l-4 border-game-cyan p-4 rounded-2xl rounded-tl-none">
                                <div className="flex gap-1.5">
                                    <span className="w-2 h-2 rounded-full bg-game-cyan animate-bounce"></span>
                                    <span className="w-2 h-2 rounded-full bg-game-cyan animate-bounce delay-100"></span>
                                    <span className="w-2 h-2 rounded-full bg-game-cyan animate-bounce delay-200"></span>
                                </div>
                            </div>
                        </motion.div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 md:p-6 bg-game-card/30 border-t border-white/5">
                    <form onSubmit={handleSend} className="relative">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask about specific topics, quotes, or details..."
                            disabled={loading}
                            className="w-full bg-game-darker border border-game-border rounded-xl px-4 py-4 pr-14 text-white placeholder-gray-500 focus:outline-none focus:border-game-purple transition-colors disabled:opacity-50"
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || loading}
                            className="absolute right-2 top-2 p-2 bg-game-purple hover:bg-game-pink text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <Send size={20} />
                        </button>
                    </form>
                    <div className="text-center mt-2">
                        <p className="text-[10px] text-gray-600 uppercase tracking-widest">AI generated responses can be inaccurate.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatInterface;
