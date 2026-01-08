/**
 * Skeleton Loading Component
 * Provides visual feedback during async operations
 * Based on UI/UX Pro Max guideline: "Show feedback during async operations"
 */

import React from 'react';
import './Skeleton.css';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'rectangular',
  width,
  height,
  animation = 'pulse',
}) => {
  const style: React.CSSProperties = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  };

  return (
    <div
      className={`skeleton skeleton-${variant} skeleton-${animation} ${className}`}
      style={style}
      aria-busy="true"
      aria-live="polite"
    />
  );
};

// Preset skeleton components for common use cases
export const SkeletonText: React.FC<{ lines?: number; className?: string }> = ({
  lines = 3,
  className = '',
}) => {
  return (
    <div className={`skeleton-text-container ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          variant="text"
          height={16}
          width={index === lines - 1 ? '80%' : '100%'}
          className="skeleton-text-line"
        />
      ))}
    </div>
  );
};

export const SkeletonCard: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div className={`skeleton-card ${className}`}>
      <Skeleton variant="rectangular" height={200} className="skeleton-card-image" />
      <div className="skeleton-card-content">
        <Skeleton variant="text" height={24} width="60%" className="skeleton-card-title" />
        <SkeletonText lines={2} className="skeleton-card-description" />
        <div className="skeleton-card-footer">
          <Skeleton variant="rounded" height={36} width={100} />
          <Skeleton variant="circular" width={36} height={36} />
        </div>
      </div>
    </div>
  );
};

export const SkeletonAvatar: React.FC<{ size?: number; className?: string }> = ({
  size = 40,
  className = '',
}) => {
  return <Skeleton variant="circular" width={size} height={size} className={className} />;
};

export const SkeletonButton: React.FC<{ width?: number; className?: string }> = ({
  width = 120,
  className = '',
}) => {
  return <Skeleton variant="rounded" height={44} width={width} className={className} />;
};

// Storyboard skeleton for video generation
export const SkeletonStoryboard: React.FC = () => {
  return (
    <div className="skeleton-storyboard">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="skeleton-storyboard-item">
          <Skeleton variant="rectangular" height={160} className="skeleton-storyboard-image" />
          <div className="skeleton-storyboard-content">
            <Skeleton variant="text" height={16} width="80%" />
            <Skeleton variant="text" height={14} width="60%" />
          </div>
        </div>
      ))}
    </div>
  );
};

// Video library skeleton
export const SkeletonVideoGrid: React.FC<{ count?: number }> = ({ count = 6 }) => {
  return (
    <div className="skeleton-video-grid">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="skeleton-video-item">
          <Skeleton variant="rectangular" height={180} className="skeleton-video-thumbnail" />
          <div className="skeleton-video-info">
            <Skeleton variant="text" height={18} width="90%" />
            <Skeleton variant="text" height={14} width="60%" />
            <div className="skeleton-video-meta">
              <Skeleton variant="text" height={12} width={80} />
              <Skeleton variant="text" height={12} width={60} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// Table skeleton
export const SkeletonTable: React.FC<{ rows?: number; columns?: number }> = ({
  rows = 5,
  columns = 4,
}) => {
  return (
    <div className="skeleton-table">
      <div className="skeleton-table-header">
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={index} variant="text" height={20} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="skeleton-table-row">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} variant="text" height={16} />
          ))}
        </div>
      ))}
    </div>
  );
};

export default Skeleton;