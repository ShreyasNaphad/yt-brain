import React, { createContext, useContext, useState, useCallback } from 'react';

const VideoContext = createContext();

export const useVideo = () => {
    const context = useContext(VideoContext);
    if (!context) {
        throw new Error('useVideo must be used within a VideoProvider');
    }
    return context;
};

export const VideoProvider = ({ children }) => {
    const [view, setView] = useState('home'); // 'home', 'processing', 'video', 'chat', 'summary', 'game'
    const [videoData, setVideoData] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

    // Additional state for "Chat About Weak Spots" or other specific navigations
    const [initialChatMessage, setInitialChatMessage] = useState('');

    const navigate = useCallback((newView, payload = {}) => {
        // Handle specific transitions/payloads
        if (newView === 'home') {
            setVideoData(null);
            setError(null);
        }

        if (payload.initialMessage) {
            setInitialChatMessage(payload.initialMessage);
        } else if (newView !== 'chat') {
            // Reset if leaving chat flow? Or keep history?
            // For now, reset initial message when navigating away from chat intention
            setInitialChatMessage('');
        }

        setView(newView);
    }, []);

    const value = {
        view,
        setView,
        videoData,
        setVideoData,
        error,
        setError,
        loading,
        setLoading,
        navigate,
        initialChatMessage
    };

    return (
        <VideoContext.Provider value={value}>
            {children}
        </VideoContext.Provider>
    );
};
