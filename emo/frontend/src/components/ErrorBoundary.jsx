import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("[ErrorBoundary]", error, info);
  }

  render() {
    const { error } = this.state;
    if (error) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6" style={{ background: "var(--emo-bg)" }}>
          <div className="emo-error-boundary max-w-md w-full">
            <div
              className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4"
              style={{ background: "var(--emo-error-bg)", border: "1px solid var(--emo-error-border)" }}
            >
              <AlertTriangle size={22} />
            </div>
            <p className="font-heading font-semibold text-base mb-1">
              {this.props.label || "Erreur d'affichage"}
            </p>
            <p className="text-xs opacity-80 mb-5 leading-relaxed">
              {error.message || "Ce composant est temporairement indisponible."}
            </p>
            <button
              type="button"
              onClick={() => this.setState({ error: null })}
              className="emo-btn-primary inline-flex items-center gap-2 px-4 py-2 text-xs"
            >
              <RefreshCw size={13} />
              Réessayer
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
