import React from 'react';

interface ProgressProps {
  value: number;
  className?: string;
}

const Progress: React.FC<ProgressProps> = ({ value, className = '' }) => {
  return (
    <div className={`h-2 rounded-full overflow-hidden ${className}`}>
      <div
        className="h-full bg-[#1DB954] rounded-full"
        style={{ width: `${value}%` }}
      ></div>
    </div>
  );
};

export default Progress;