import React from "react";

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
        <div
          className="rounded-2xl p-4 text-sm"
          style={{
            background: "var(--emo-error-bg)",
            border: "1px solid var(--emo-error-border)",
            color: "var(--emo-error-text)",
          }}
        >
          <p className="font-medium mb-1">{this.props.label || "Erreur d'affichage"}</p>
          <p className="text-xs opacity-80 mb-3">{error.message || "Composant indisponible."}</p>
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            className="text-xs px-3 py-1.5 rounded-xl font-medium"
            style={{ background: "var(--emo-accent)", color: "var(--emo-on-accent)" }}
          >
            Réessayer
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
