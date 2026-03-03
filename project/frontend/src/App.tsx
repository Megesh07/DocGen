import { Component, type ReactNode } from 'react';
import './index.css';
import { WorkflowPage } from './components/WorkflowPage';

interface EBState { error: Error | null }
class ErrorBoundary extends Component<{ children: ReactNode }, EBState> {
  state: EBState = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          height: '100vh', flexDirection: 'column', gap: 16,
          background: '#fef2f2', fontFamily: 'Inter, sans-serif',
        }}>
          <div style={{ fontSize: 32 }}>⚠️</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#dc2626' }}>Something went wrong</div>
          <pre style={{
            fontSize: 12, color: '#991b1b', background: '#fff',
            border: '1px solid #fca5a5', borderRadius: 8,
            padding: '12px 20px', maxWidth: 600, overflowX: 'auto',
            whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          }}>{this.state.error.message}</pre>
          <button
            onClick={() => { this.setState({ error: null }); window.location.reload(); }}
            style={{
              padding: '10px 24px', borderRadius: 8, border: 'none',
              background: '#dc2626', color: '#fff', fontWeight: 700,
              fontSize: 14, cursor: 'pointer',
            }}
          >
            Reload App
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return <ErrorBoundary><WorkflowPage /></ErrorBoundary>;
}

export default App;
