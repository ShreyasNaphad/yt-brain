import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Trophy, CheckCircle, XCircle, Loader2, Star, Zap, Brain, Home } from 'lucide-react';
import { getQuestions, gradeAnswer } from '../api/client';

const GameView = ({ videoId, metadata, onBack, onGoHome }) => {
    const [questions, setQuestions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentQ, setCurrentQ] = useState(0);
    const [selectedAnswer, setSelectedAnswer] = useState(null);
    const [showResult, setShowResult] = useState(false);
    const [isCorrect, setIsCorrect] = useState(false);
    const [openAnswer, setOpenAnswer] = useState('');
    const [grading, setGrading] = useState(false);
    const [gradeFeedback, setGradeFeedback] = useState(null);
    const [score, setScore] = useState(0);
    const [xp, setXp] = useState(0);
    const [gameComplete, setGameComplete] = useState(false);

    useEffect(() => {
        const fetchQuestions = async () => {
            try {
                const data = await getQuestions(videoId);
                if (data?.questions && Array.isArray(data.questions)) {
                    setQuestions(data.questions);
                } else {
                    setError("Failed to load questions. Unexpected format.");
                }
            } catch (err) {
                console.error(err);
                setError("Failed to load quiz questions. Try again later.");
            } finally {
                setLoading(false);
            }
        };
        fetchQuestions();
    }, [videoId]);

    const currentQuestion = questions[currentQ];

    const handleMCQSelect = (option) => {
        if (showResult) return;
        setSelectedAnswer(option);
        // Extract the letter (e.g., "A" from "A. something")
        const letter = option.charAt(0).toUpperCase();
        const correct = currentQuestion.correct?.charAt(0)?.toUpperCase() === letter;
        setIsCorrect(correct);
        setShowResult(true);
        if (correct) {
            const points = currentQuestion.difficulty === 'easy' ? 10 : 20;
            setScore(prev => prev + 1);
            setXp(prev => prev + points);
        }
    };

    const handleOpenSubmit = async () => {
        if (!openAnswer.trim() || grading) return;
        setGrading(true);
        try {
            const result = await gradeAnswer(
                currentQuestion.question,
                currentQuestion.correct,
                openAnswer,
                currentQuestion.difficulty
            );
            setGradeFeedback(result);
            setShowResult(true);
            setXp(prev => prev + (result.xp_earned || 0));
            if (result.score >= 2) setScore(prev => prev + 1);
        } catch (err) {
            setGradeFeedback({ score: 0, feedback: "Error grading answer.", xp_earned: 0 });
            setShowResult(true);
        } finally {
            setGrading(false);
        }
    };

    const handleNext = () => {
        if (currentQ + 1 >= questions.length) {
            setGameComplete(true);
        } else {
            setCurrentQ(prev => prev + 1);
            setSelectedAnswer(null);
            setShowResult(false);
            setIsCorrect(false);
            setOpenAnswer('');
            setGradeFeedback(null);
        }
    };

    const getDifficultyColor = (diff) => {
        if (diff === 'easy') return 'text-green-400 bg-green-400/10 border-green-400/30';
        if (diff === 'medium') return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
        return 'text-red-400 bg-red-400/10 border-red-400/30';
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[500px] gap-4">
                <Loader2 className="animate-spin text-game-purple" size={40} />
                <p className="text-gray-400 text-lg">Generating quiz questions...</p>
                <p className="text-gray-600 text-sm">This may take a moment</p>
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

    if (gameComplete) {
        const percentage = Math.round((score / questions.length) * 100);
        const level = xp >= 300 ? 'Master' : xp >= 150 ? 'Analyst' : xp >= 50 ? 'Thinker' : 'Listener';
        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="w-full max-w-2xl mx-auto"
            >
                <div className="bg-game-card border border-game-border rounded-3xl p-10 text-center relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-game-purple/10 to-game-cyan/10 pointer-events-none" />
                    <div className="relative z-10">
                        <Trophy className="mx-auto text-yellow-400 mb-4" size={64} />
                        <h2 className="text-3xl font-bold text-white mb-2">Quiz Complete!</h2>
                        <p className="text-gray-400 mb-8">Here's how you did</p>

                        <div className="grid grid-cols-3 gap-6 mb-8">
                            <div className="bg-white/5 rounded-2xl p-5">
                                <p className="text-3xl font-bold text-game-cyan">{score}/{questions.length}</p>
                                <p className="text-gray-400 text-sm mt-1">Correct</p>
                            </div>
                            <div className="bg-white/5 rounded-2xl p-5">
                                <p className="text-3xl font-bold text-game-purple">{xp} XP</p>
                                <p className="text-gray-400 text-sm mt-1">Earned</p>
                            </div>
                            <div className="bg-white/5 rounded-2xl p-5">
                                <p className="text-3xl font-bold text-yellow-400">{percentage}%</p>
                                <p className="text-gray-400 text-sm mt-1">Score</p>
                            </div>
                        </div>

                        <div className="bg-gradient-to-r from-game-purple/20 to-game-cyan/20 rounded-xl p-4 mb-8 inline-block">
                            <p className="text-gray-400 text-sm">Your Level</p>
                            <p className="text-2xl font-bold text-white">{level}</p>
                        </div>

                        <div>
                            <button
                                onClick={onBack}
                                className="px-8 py-3 bg-gradient-to-r from-game-purple to-game-pink text-white font-bold rounded-xl hover:shadow-lg transition-all"
                            >
                                Back to Video
                            </button>
                        </div>
                    </div>
                </div>
            </motion.div>
        );
    }

    return (
        <div className="w-full max-w-3xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                    <button onClick={onBack} className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
                        <ArrowLeft size={20} /> Dashboard
                    </button>
                    <div className="w-px h-4 bg-white/20"></div>
                    <button onClick={onGoHome} className="flex items-center gap-2 text-gray-400 hover:text-game-pink transition-colors">
                        <Home size={20} /> New Video
                    </button>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1 text-yellow-400">
                        <Zap size={18} /> <span className="font-bold">{xp} XP</span>
                    </div>
                    <div className="flex items-center gap-1 text-game-cyan">
                        <Star size={18} /> <span className="font-bold">{score} correct</span>
                    </div>
                </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-white/5 rounded-full h-2 mb-8">
                <motion.div
                    className="bg-gradient-to-r from-game-purple to-game-cyan h-2 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${((currentQ + 1) / questions.length) * 100}%` }}
                    transition={{ duration: 0.3 }}
                />
            </div>

            {/* Question Card */}
            <AnimatePresence mode="wait">
                <motion.div
                    key={currentQ}
                    initial={{ opacity: 0, x: 30 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -30 }}
                    className="bg-game-card border border-game-border rounded-3xl p-8 relative overflow-hidden"
                >
                    <div className="flex items-center justify-between mb-6">
                        <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getDifficultyColor(currentQuestion.difficulty)}`}>
                            {currentQuestion.difficulty?.toUpperCase()}
                        </span>
                        <span className="text-gray-500 text-sm font-mono">
                            {currentQ + 1} / {questions.length}
                        </span>
                    </div>

                    <h3 className="text-xl font-bold text-white mb-8 leading-relaxed">
                        {currentQuestion.question}
                    </h3>

                    {/* MCQ Options */}
                    {currentQuestion.type === 'mcq' && currentQuestion.options && currentQuestion.options.length > 0 ? (
                        <div className="space-y-3">
                            {currentQuestion.options.map((opt, idx) => {
                                const letter = opt.charAt(0).toUpperCase();
                                const correctLetter = currentQuestion.correct?.charAt(0)?.toUpperCase();
                                let optClass = 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-game-purple/50';
                                if (showResult) {
                                    if (letter === correctLetter) {
                                        optClass = 'bg-green-500/20 border-green-500/50 text-green-300';
                                    } else if (selectedAnswer === opt) {
                                        optClass = 'bg-red-500/20 border-red-500/50 text-red-300';
                                    } else {
                                        optClass = 'bg-white/5 border-white/5 opacity-50';
                                    }
                                }
                                return (
                                    <button
                                        key={idx}
                                        onClick={() => handleMCQSelect(opt)}
                                        disabled={showResult}
                                        className={`w-full text-left p-4 rounded-xl border transition-all ${optClass} ${!showResult ? 'cursor-pointer' : 'cursor-default'}`}
                                    >
                                        <span className="text-gray-200 font-medium">{opt}</span>
                                    </button>
                                );
                            })}
                        </div>
                    ) : (
                        /* Open-ended */
                        <div>
                            <textarea
                                value={openAnswer}
                                onChange={(e) => setOpenAnswer(e.target.value)}
                                disabled={showResult}
                                placeholder="Type your answer here..."
                                className="w-full bg-game-darker border border-game-border rounded-xl p-4 text-white placeholder-gray-500 focus:outline-none focus:border-game-purple min-h-[120px] resize-none transition-colors"
                            />
                            {!showResult && (
                                <button
                                    onClick={handleOpenSubmit}
                                    disabled={!openAnswer.trim() || grading}
                                    className="mt-4 px-6 py-3 bg-game-purple text-white font-bold rounded-xl hover:bg-game-pink transition-colors disabled:opacity-50 flex items-center gap-2"
                                >
                                    {grading ? <><Loader2 size={18} className="animate-spin" /> Grading...</> : <><Brain size={18} /> Submit Answer</>}
                                </button>
                            )}
                        </div>
                    )}

                    {/* Result Feedback */}
                    {showResult && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="mt-6"
                        >
                            {currentQuestion.type === 'mcq' ? (
                                <div className={`p-4 rounded-xl flex items-start gap-3 ${isCorrect ? 'bg-green-500/10 border border-green-500/30' : 'bg-red-500/10 border border-red-500/30'}`}>
                                    {isCorrect ? <CheckCircle className="text-green-400 shrink-0 mt-0.5" size={20} /> : <XCircle className="text-red-400 shrink-0 mt-0.5" size={20} />}
                                    <div>
                                        <p className={`font-bold ${isCorrect ? 'text-green-400' : 'text-red-400'}`}>
                                            {isCorrect ? 'Correct!' : 'Incorrect'}
                                        </p>
                                        {currentQuestion.explanation && (
                                            <p className="text-gray-400 text-sm mt-1">{currentQuestion.explanation}</p>
                                        )}
                                    </div>
                                </div>
                            ) : gradeFeedback && (
                                <div className={`p-4 rounded-xl border ${gradeFeedback.score >= 2 ? 'bg-green-500/10 border-green-500/30' : 'bg-yellow-500/10 border-yellow-500/30'}`}>
                                    <p className="font-bold text-white">Score: {gradeFeedback.score}/3 — +{gradeFeedback.xp_earned} XP</p>
                                    <p className="text-gray-400 text-sm mt-1">{gradeFeedback.feedback}</p>
                                </div>
                            )}

                            <button
                                onClick={handleNext}
                                className="mt-4 w-full py-3 bg-gradient-to-r from-game-purple to-game-cyan text-white font-bold rounded-xl hover:shadow-lg transition-all"
                            >
                                {currentQ + 1 >= questions.length ? 'See Results' : 'Next Question →'}
                            </button>
                        </motion.div>
                    )}
                </motion.div>
            </AnimatePresence>
        </div>
    );
};

export default GameView;
