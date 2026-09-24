"use client";
import React from "react";

export class ErrorBoundary extends React.Component<{ children: React.ReactNode; fallback?: React.ReactNode }, { hasError: boolean; error: any }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }
  componentDidCatch(error: any, info: any) {
    console.error("ErrorBoundary:", error, info);
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div style={{ padding: 16, border: "1px solid #ef4444", borderRadius: 12, background: "rgba(239,68,68,.08)", color: "#991b1b" }}>
          <div style={{ fontWeight: 700 }}>Ein Fehler ist aufgetreten</div>
          <div className="mono" style={{ fontSize: 11, marginTop: 6, whiteSpace: "pre-wrap" }}>{String(this.state.error?.message || this.state.error)}</div>
          <button onClick={() => this.setState({ hasError: false, error: null })} className="btn" style={{ marginTop: 10, padding: "6px 10px", fontSize: 11 }}>Erneut versuchen</button>
        </div>
      );
    }
    return this.props.children;
  }
}
