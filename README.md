# 🧠 YTBrain - YouTube Master Agent

YTBrain is an AI-powered tool that turns YouTube videos into interactive learning experiences. It extracts transcripts, analyzes content using Llama 3 (via Groq), and provides summaries, chat, and educational games.

## 🌟 Features
- **Video Summarization**: Get concise summaries of any YouTube video.
- **Interactive Chat**: Ask questions about the video content.
- **Gamified Learning**: "Chat About Weak Spots" mode to test your knowledge.
- **RAG Powered**: Uses Qdrant vector database for accurate context retrieval.

## 🛠 Prerequisites
- **Docker**: For running Redis and Qdrant.
- **Python 3.11+**: For the backend API.
- **Node.js 18+**: For the frontend.
- **Groq API Key**: You need a valid API key from [Groq Console](https://console.groq.com/).

## 🚀 Quick Start

1.  **Clone the repository**
    ```bash
    git clone <repository-url>
    cd Youtube-brain
    ```

2.  **Environment Setup**
    Create a `.env` file in the root directory (or `backend/` depending on structure, current setup reads from root normally or backend/.env):
    ```env
    GROQ_API_KEY=your_groq_api_key_here
    ```

3.  **Start Everything**
    Run the startup script:
    ```bash
    ./start.sh
    ```
    This script will:
    - Start Docker containers (Redis, Qdrant)
    - Install Python dependencies and start the FastAPI backend
    - Install Node dependencies and start the React frontend

4.  **Access the App**
    - Frontend: [http://localhost:5173](http://localhost:5173)
    - Backend Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🏗 Architecture
- **Frontend**: React, Tailwind CSS, Framer Motion
- **Backend**: FastAPI, LangChain
- **AI/LLM**: Llama 3 (via Groq)
- **Database**: Qdrant (Vector Store), Redis (Caching)

## 📄 License
MIT
