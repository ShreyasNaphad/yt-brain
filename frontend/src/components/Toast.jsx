import React, { createContext, useContext, useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

const ToastContext = createContext();

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};

export const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((message, type = 'info', duration = 3000) => {
        const id = Date.now().toString();
        const toast = { id, message, type };

        setToasts(prev => [...prev, toast]);

        if (duration > 0) {
            setTimeout(() => {
                removeToast(id);
            }, duration);
        }
    }, []);

    const removeToast = useCallback((id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    return (
        <ToastContext.Provider value={{ addToast, removeToast }}>
            {children}
            <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-full max-w-sm pointer-events-none">
                <AnimatePresence>
                    {toasts.map(toast => (
                        <Toast key={toast.id} {...toast} onClose={() => removeToast(toast.id)} />
                    ))}
                </AnimatePresence>
            </div>
        </ToastContext.Provider>
    );
};

const Toast = ({ message, type, onClose }) => {
    const styles = {
        success: { bg: 'bg-green-500/20', border: 'border-green-500/50', icon: <CheckCircle className="text-green-500" size={20} /> },
        error: { bg: 'bg-red-500/20', border: 'border-red-500/50', icon: <AlertCircle className="text-red-500" size={20} /> },
        info: { bg: 'bg-blue-500/20', border: 'border-blue-500/50', icon: <Info className="text-blue-500" size={20} /> },
    };

    const style = styles[type] || styles.info;

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: -20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
            className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl border backdrop-blur-md shadow-lg ${style.bg} ${style.border} text-white`}
        >
            <div className="mt-0.5 shrink-0">{style.icon}</div>
            <p className="text-sm font-medium flex-1">{message}</p>
            <button onClick={onClose} className="opacity-70 hover:opacity-100 transition-opacity">
                <X size={16} />
            </button>
        </motion.div >
    );
};
