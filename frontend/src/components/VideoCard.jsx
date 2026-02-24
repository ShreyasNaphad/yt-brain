import React from 'react';
import { motion } from 'framer-motion';
import { Play, MessageSquare, FileText, Gamepad2, Clock, User } from 'lucide-react';

const VideoCard = ({ metadata, onStartChat, onStartSummary, onStartGame }) => {
    const [imgError, setImgError] = React.useState(false);
    if (!metadata) return null;

    const { title, channel, thumbnail_url, duration_seconds } = metadata;

    const formatDuration = (seconds) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: "spring", stiffness: 100, damping: 20 }}
            className="max-w-4xl mx-auto w-full bg-game-card/50 backdrop-blur-xl border border-game-border rounded-3xl p-6 md:p-8 shadow-2xl relative overflow-hidden group"
        >
            {/* Glow Effect */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-game-purple/20 blur-[100px] pointer-events-none group-hover:bg-game-purple/30 transition duration-500" />

            <div className="flex flex-col md:flex-row gap-8 items-start">
                {/* Thumbnail */}
                <div className="relative shrink-0 w-full md:w-80 aspect-video rounded-xl overflow-hidden border border-game-purple/30 shadow-[0_0_20px_rgba(124,58,237,0.3)] group-hover:shadow-[0_0_30px_rgba(124,58,237,0.5)] transition duration-300 bg-black/50">
                    {imgError ? (
                        <div className="w-full h-full flex flex-col items-center justify-center text-gray-500 bg-game-darker">
                            <Play size={48} className="nav-link-icon mb-2 opacity-50" />
                            <span className="text-xs">No Thumbnail</span>
                        </div>
                    ) : (
                        <img
                            src={thumbnail_url}
                            alt={title}
                            onError={() => setImgError(true)}
                            className="w-full h-full object-cover transform group-hover:scale-105 transition duration-500"
                        />
                    )}
                    <div className="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-1 rounded flex items-center gap-1 backdrop-blur-sm z-10">
                        <Clock size={12} />
                        {formatDuration(duration_seconds)}
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 space-y-6 w-full">
                    <div>
                        <h2 className="text-2xl md:text-3xl font-bold leading-tight mb-2 text-white group-hover:text-game-purple transition-colors duration-300">
                            {title}
                        </h2>
                        <div className="flex items-center gap-2 text-gray-400">
                            <User size={16} />
                            <span className="font-medium">{channel}</span>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <button
                            onClick={onStartChat}
                            className="group/btn relative p-5 rounded-xl bg-game-card border border-game-cyan/30 hover:border-game-cyan hover:bg-game-cyan/10 transition-all duration-300 flex flex-col items-center text-center"
                        >
                            <div className="p-3 mb-3 rounded-xl bg-game-cyan/20 text-game-cyan group-hover/btn:bg-game-cyan group-hover/btn:text-black transition-colors shrink-0 shadow-lg">
                                <MessageSquare size={24} />
                            </div>
                            <span className="font-bold text-lg text-white mb-1">Chat</span>
                            <p className="text-xs text-gray-400 group-hover/btn:text-gray-300">Ask questions, get answers.</p>
                        </button>

                        <button
                            onClick={onStartSummary}
                            className="group/btn relative p-5 rounded-xl bg-game-card border border-game-purple/30 hover:border-game-purple hover:bg-game-purple/10 transition-all duration-300 flex flex-col items-center text-center"
                        >
                            <div className="p-3 mb-3 rounded-xl bg-game-purple/20 text-game-purple group-hover/btn:bg-game-purple group-hover/btn:text-white transition-colors shrink-0 shadow-lg">
                                <FileText size={24} />
                            </div>
                            <span className="font-bold text-lg text-white mb-1">Summary</span>
                            <p className="text-xs text-gray-400 group-hover/btn:text-gray-300">Key concepts & takeaways.</p>
                        </button>

                        <button
                            onClick={onStartGame}
                            className="group/btn relative p-5 rounded-xl bg-gradient-to-br from-game-gold/10 to-game-pink/10 border border-game-gold/30 hover:border-game-gold hover:from-game-gold/20 hover:to-game-pink/20 transition-all duration-300 flex flex-col items-center text-center animate-pulse-slow"
                        >
                            <div className="absolute inset-0 bg-gradient-to-r from-game-gold/20 to-game-pink/20 blur-xl opacity-0 group-hover/btn:opacity-50 transition duration-500" />
                            <div className="relative p-3 mb-3 rounded-xl bg-gradient-to-br from-game-gold to-game-pink text-white shadow-lg shrink-0">
                                <Gamepad2 size={24} />
                            </div>
                            <span className="relative font-bold text-lg text-transparent bg-clip-text bg-gradient-to-r from-game-gold to-game-pink mb-1">
                                Game Mode
                            </span>
                            <p className="text-xs text-gray-400 group-hover/btn:text-gray-300 relative">Test your knowledge & level up!</p>
                        </button>
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

export default VideoCard;
