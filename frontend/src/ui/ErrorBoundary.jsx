import { Component } from "react";

// If a page crashes while drawing, React throws everything away and you get a black
// screen. This catches it and says so instead, the rest of the site keeps working.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidUpdate(prev) {
    // switching page clears it, so one broken page doesn't stick around
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="bg-pw-panel rounded-xl p-4 my-4">
        <p className="font-semibold">Something on this page broke. Try another tab or reload.</p>
        <p className="text-xs text-pw-muted mt-1">{String(this.state.error?.message || this.state.error)}</p>
      </div>
    );
  }
}
