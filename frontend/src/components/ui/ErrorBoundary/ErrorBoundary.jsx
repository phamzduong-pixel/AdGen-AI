import React from "react";
import "./ErrorBoundary.css";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error("AdGen AI caught an unhandled render error:", error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="adgen-error-boundary" role="alert">
          <div className="adgen-error-boundary__card">
            <div className="adgen-error-boundary__icon">⚠️</div>
            <h2>Đã xảy ra sự cố hiển thị</h2>
            <p>
              Hệ thống vừa gặp phải một lỗi giao diện. Bạn có thể thử tải lại trang hoặc khôi phục phiên làm việc.
            </p>
            {this.state.error?.message && (
              <pre className="adgen-error-boundary__details">
                {this.state.error.message}
              </pre>
            )}
            <div className="adgen-error-boundary__actions">
              <button
                type="button"
                className="adgen-btn adgen-btn--secondary"
                onClick={this.handleReset}
              >
                Thử lại
              </button>
              <button
                type="button"
                className="adgen-btn adgen-btn--primary"
                onClick={this.handleReload}
              >
                Tải lại trang
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
