import './Skeleton.css';

/**
 * Generic shimmer block. Use for any loading placeholder.
 * Props: width (px or '%'), height (px), radius (px), className.
 */
export function Skeleton({ width = '100%', height = 16, radius = 6, className = '', style }) {
  return (
    <span
      className={`skeleton ${className}`.trim()}
      style={{
        width,
        height,
        borderRadius: radius,
        ...style,
      }}
      aria-hidden="true"
    />
  );
}

/**
 * Card-shaped placeholder mimicking a room/court tile.
 * Use as a drop-in for the rooms grid while loading.
 */
export function ResourceCardSkeleton() {
  return (
    <div className="skeleton-card" aria-hidden="true">
      <div className="skeleton-card-row">
        <Skeleton width="55%" height={18} />
        <Skeleton width={70} height={20} radius={999} />
      </div>
      <Skeleton width="35%" height={13} />
      <div className="skeleton-card-tags">
        <Skeleton width={60} height={20} radius={999} />
        <Skeleton width={80} height={20} radius={999} />
        <Skeleton width={50} height={20} radius={999} />
      </div>
      <Skeleton width="100%" height={36} radius={8} />
    </div>
  );
}

/** Render N ResourceCardSkeleton in a grid container — caller supplies the wrapping grid. */
export function ResourceGridSkeleton({ count = 4 }) {
  return Array.from({ length: count }, (_, i) => <ResourceCardSkeleton key={i} />);
}
