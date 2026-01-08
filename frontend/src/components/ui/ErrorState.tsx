/**
 * Error State Component with Recovery
 * Provides clear error messages with actionable recovery paths
 * Based on UI/UX Pro Max guideline: "Help users recover from errors"
 */

import React from 'react';
import './ErrorState.css';

interface ErrorStateProps {
  title?: string;
  message: string;
  error?: Error | string;
  onRetry?: () => void;
  onCancel?: () => void;
  retryText?: string;
  cancelText?: string;
  showDetails?: boolean;
  icon?: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message,
  error,
  onRetry,
  onCancel,
  retryText = 'Try Again',
  cancelText = 'Go Back',
  showDetails = false,
  icon,
  className = '',
  children,
}) => {
  const [showErrorDetails, setShowErrorDetails] = React.useState(false);

  const errorDetails = error instanceof Error ? error.message : error;

  return (
    <div className={`error-state ${className}`} role="alert" aria-live="assertive">
      <div className="error-state-content">
        {icon ? (
          <div className="error-state-icon">{icon}</div>
        ) : (
          <div className="error-state-icon error-state-icon-default">
            <svg
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
        )}

        <h3 className="error-state-title">{title}</h3>
        <p className="error-state-message">{message}</p>

        {children}

        {showDetails && errorDetails && (
          <div className="error-state-details-container">
            <button
              className="error-state-details-toggle"
              onClick={() => setShowErrorDetails(!showErrorDetails)}
              aria-expanded={showErrorDetails}
            >
              {showErrorDetails ? 'Hide' : 'Show'} technical details
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                style={{
                  transform: showErrorDetails ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s',
                }}
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>

            {showErrorDetails && (
              <div className="error-state-details">
                <code>{errorDetails}</code>
              </div>
            )}
          </div>
        )}

        <div className="error-state-actions">
          {onRetry && (
            <button
              className="btn btn-primary error-state-retry"
              onClick={onRetry}
              aria-label={retryText}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <polyline points="23 4 23 10 17 10" />
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
              </svg>
              {retryText}
            </button>
          )}

          {onCancel && (
            <button
              className="btn btn-secondary error-state-cancel"
              onClick={onCancel}
              aria-label={cancelText}
            >
              {cancelText}
            </button>
          )}
        </div>

        <div className="error-state-help">
          <p className="error-state-help-text">
            Need help?{' '}
            <a href="/docs/troubleshooting" className="error-state-help-link">
              View troubleshooting guide
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

// Specific error state variants
export const NetworkErrorState: React.FC<Omit<ErrorStateProps, 'title' | 'message' | 'icon'>> = (
  props
) => {
  return (
    <ErrorState
      title="Connection Error"
      message="Unable to connect to the server. Please check your internet connection and try again."
      icon={
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M1 1l22 22M16.72 11.06A10.94 10.94 0 0 1 19 12.55M5 12.55a10.94 10.94 0 0 1 5.17-2.39M10.71 5.05A16 16 0 0 1 22.58 9M1.42 9a15.91 15.91 0 0 1 4.7-2.88M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01" />
        </svg>
      }
      {...props}
    />
  );
};

export const NotFoundErrorState: React.FC<Omit<ErrorStateProps, 'title' | 'message' | 'icon'>> = (
  props
) => {
  return (
    <ErrorState
      title="Not Found"
      message="The content you're looking for doesn't exist or has been removed."
      icon={
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
          <line x1="11" y1="8" x2="11" y2="14" />
          <line x1="8" y1="11" x2="14" y2="11" />
        </svg>
      }
      {...props}
    />
  );
};

export const PermissionErrorState: React.FC<Omit<ErrorStateProps, 'title' | 'message' | 'icon'>> = (
  props
) => {
  return (
    <ErrorState
      title="Access Denied"
      message="You don't have permission to access this resource. Please contact your administrator."
      icon={
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      }
      {...props}
    />
  );
};

export const TimeoutErrorState: React.FC<Omit<ErrorStateProps, 'title' | 'message' | 'icon'>> = (
  props
) => {
  return (
    <ErrorState
      title="Request Timeout"
      message="The request took too long to complete. This might be due to a slow connection or server issues."
      icon={
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      }
      {...props}
    />
  );
};

export const ValidationErrorState: React.FC<
  Omit<ErrorStateProps, 'title' | 'message' | 'icon'> & { errors?: string[] }
> = ({ errors, ...props }) => {
  return (
    <ErrorState
      title="Validation Error"
      message="Please fix the following errors and try again:"
      icon={
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      }
      {...props}
    >
      {errors && errors.length > 0 && (
        <ul className="error-state-validation-list">
          {errors.map((error, index) => (
            <li key={index} className="error-state-validation-item">
              {error}
            </li>
          ))}
        </ul>
      )}
    </ErrorState>
  );
};

export default ErrorState;