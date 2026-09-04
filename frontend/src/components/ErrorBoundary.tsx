/** 错误边界：页面运行时出错时显示可读信息，避免白屏。 */

import { Component, type ErrorInfo, type ReactNode } from "react";

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[页面错误]", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="page">
          <div
            className="card"
            style={{ borderColor: "rgba(184,74,50,0.5)", color: "var(--danger)" }}
          >
            <h2>页面加载出错</h2>
            <p className="small">{this.state.error.message}</p>
            <pre className="code-block" style={{ maxHeight: 200, overflow: "auto", fontSize: 12 }}>
              {this.state.error.stack}
            </pre>
            <button className="btn btn-primary" onClick={() => window.location.reload()}>
              刷新重试
            </button>
            <button className="btn" onClick={() => this.setState({ error: null })}>
              尝试继续
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

