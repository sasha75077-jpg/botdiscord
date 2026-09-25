import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  title?: string;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50 dark:bg-dark-900">
          <div className="card max-w-md w-full text-center">
            <div className="text-5xl mb-4">⚠️</div>
            <h2 className="text-2xl font-bold mb-2">{this.props.title || 'Что-то сломалось'}</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 break-words">
              {this.state.error.message}
            </p>
            <div className="flex gap-2 justify-center">
              <button
                onClick={() => this.setState({ error: null })}
                className="btn btn-secondary text-sm"
              >
                Попробовать снова
              </button>
              <button
                onClick={() => window.location.reload()}
                className="btn btn-primary text-sm"
              >
                Перезагрузить
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
