"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Error caught by boundary:", error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });

    // Log to external error tracking service (e.g., Sentry)
    if (typeof window !== "undefined" && (window as any).Sentry) {
      (window as any).Sentry.captureException(error, {
        contexts: {
          react: {
            componentStack: errorInfo.componentStack,
          },
        },
      });
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          className="flex min-h-screen items-center justify-center p-8"
          style={{ background: "#0D1117" }}
        >
          <div
            className="max-w-2xl rounded border p-8 text-center"
            style={{
              background: "#161B22",
              borderColor: "rgba(255, 255, 255, 0.07)",
            }}
          >
            <AlertTriangle
              size={64}
              className="mx-auto mb-4"
              style={{ color: "#F85149" }}
            />
            
            <h1
              className="mb-2 text-2xl font-semibold"
              style={{ color: "#E6EDF3" }}
            >
              Something went wrong
            </h1>
            
            <p className="mb-6 text-[14px]" style={{ color: "#8B949E" }}>
              An unexpected error occurred. Please try refreshing the page or contact support if the problem persists.
            </p>

            {process.env.NODE_ENV === "development" && this.state.error && (
              <details className="mb-6 text-left">
                <summary
                  className="cursor-pointer text-[13px] font-medium"
                  style={{ color: "#F0883E" }}
                >
                  Error Details (Development Only)
                </summary>
                <pre
                  className="mt-4 overflow-auto rounded border p-4 text-left text-[11px]"
                  style={{
                    background: "#0D1117",
                    borderColor: "rgba(255, 255, 255, 0.07)",
                    color: "#E6EDF3",
                    fontFamily: "IBM Plex Mono, monospace",
                  }}
                >
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}

            <div className="flex items-center justify-center gap-3">
              <button
                onClick={this.handleReset}
                className="inline-flex items-center gap-2 rounded border px-4 py-2 text-[13px] font-medium transition-all duration-150"
                style={{
                  borderColor: "rgba(255, 255, 255, 0.07)",
                  background: "#0D1117",
                  color: "#8B949E",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "#161B22";
                  e.currentTarget.style.color = "#E6EDF3";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "#0D1117";
                  e.currentTarget.style.color = "#8B949E";
                }}
              >
                <RefreshCw size={16} />
                Try Again
              </button>

              <button
                onClick={() => window.location.reload()}
                className="inline-flex items-center gap-2 rounded border px-4 py-2 text-[13px] font-medium transition-all duration-150"
                style={{
                  borderColor: "#00C9A7",
                  background: "#00C9A7",
                  color: "#FFFFFF",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "#00B396";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "#00C9A7";
                }}
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
