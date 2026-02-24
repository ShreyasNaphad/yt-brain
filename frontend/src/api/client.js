import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
    timeout: 60000,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const processVideo = async (url) => {
    const response = await api.post('/video/process', { url });
    return response.data;
};

export const getStatus = async (videoId) => {
    const response = await api.get(`/video/${videoId}/status`);
    return response.data;
};

export const getMetadata = async (videoId) => {
    const response = await api.get(`/video/${videoId}/metadata`);
    return response.data;
};

export const getSummary = async (videoId) => {
    const response = await api.get(`/video/${videoId}/summary`);
    return response.data;
};

export const sendChat = async (videoId, message, history) => {
    const response = await api.post('/chat', { video_id: videoId, message, history });
    return response.data;
};

export const getQuestions = async (videoId) => {
    const response = await api.get(`/game/${videoId}/questions`);
    return response.data;
};

export const gradeAnswer = async (question, correct, userAnswer, difficulty) => {
    const response = await api.post('/game/grade', {
        question,
        correct_answer: correct,
        user_answer: userAnswer,
        difficulty
    });
    return response.data;
};

export const completeGame = async (videoId, results, totalXp) => {
    const response = await api.post('/game/complete', {
        video_id: videoId,
        results,
        total_xp: totalXp
    });
    return response.data;
};

export default api;
