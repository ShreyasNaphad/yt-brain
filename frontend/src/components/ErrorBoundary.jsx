import React from 'react';
import { AlertTriangle, RefreshCcw } from 'lucide-react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error("ErrorBoundary caught an error:", error, errorInfo);
        this.setState({ errorInfo });
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
        window.location.reload();
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-game-dark flex items-center justify-center p-4">
                    <div className="bg-game-card/80 backdrop-blur-xl border border-red-500/30 rounded-2xl p-8 max-w-md w-full text-center shadow-2xl shadow-red-500/10">
                        <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                            <AlertTriangle className="w-8 h-8 text-red-500" />
                        </div>

                        <h2 className="text-2xl font-bold text-white mb-2">Something went wrong</h2>
                        <p className="text-gray-400 mb-6">
                            We encountered an unexpected error. The application has been stopped to prevent further issues.
                        </p>

                        <div className="bg-black/30 rounded-lg p-4 mb-6 text-left overflow-auto max-h-40">
                            <code className="text-xs text-red-400 font-mono">
                                {this.state.error && this.state.error.toString()}
                            </code>
                        </div>

                        <button
                            onClick={this.handleRetry}
                            className="w-full py-3 px-6 bg-red-600 hover:bg-red-700 text-white rounded-xl font-semibold transition-all flex items-center justify-center gap-2 group"
                        >
                            <RefreshCcw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500" />
                            Reload Application
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
