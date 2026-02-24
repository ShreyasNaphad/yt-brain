import React from 'react';
import { motion } from 'framer-motion';
import { Zap } from 'lucide-react';

const Layout = ({ children }) => {
    // Generate random particles
    const particles = Array.from({ length: 20 }).map((_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        duration: 10 + Math.random() * 20,
        delay: Math.random() * 5,
    }));

    return (
        <div className="min-h-screen bg-game-dark text-white relative overflow-hidden font-sans selection:bg-game-purple selection:text-white">
            {/* Animated Particle Background */}
            {particles.map((p) => (
                <motion.div
                    key={p.id}
                    className="absolute rounded-full bg-game-purple/20 blur-sm"
                    style={{
                        width: Math.random() * 6 + 2 + 'px',
                        height: Math.random() * 6 + 2 + 'px',
                        left: `${p.x}%`,
                        top: `${p.y}%`,
                    }}
                    animate={{
                        y: [0, -100, 0],
                        x: [0, 50, -50, 0],
                        opacity: [0.2, 0.5, 0.2],
                    }}
                    transition={{
                        duration: p.duration,
                        repeat: Infinity,
                        ease: "linear",
                        delay: p.delay,
                    }}
                />
            ))}

            {/* Navbar */}
            <nav className="relative z-10 flex items-center justify-between px-6 py-4 border-b border-white/5 backdrop-blur-md">
                <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-gradient-to-br from-game-purple to-game-pink">
                        <Zap size={24} className="text-white fill-white" />
                    </div>
                    <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-game-purple via-game-pink to-game-gold">
                        YTBrain
                    </span>
                </div>
                <div className="text-sm font-medium text-gray-400">
                    Learn Smarter. Play Harder.
                </div>
            </nav>

            {/* Main Content */}
            <main className="relative z-10 container mx-auto px-4 py-8">
                {children}
            </main>

            {/* Corner Gradients */}
            <div className="absolute top-0 left-0 w-96 h-96 bg-game-purple/10 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
            <div className="absolute bottom-0 right-0 w-96 h-96 bg-game-cyan/10 rounded-full blur-3xl translate-x-1/2 translate-y-1/2 pointer-events-none" />
        </div>
    );
};

export default Layout;
