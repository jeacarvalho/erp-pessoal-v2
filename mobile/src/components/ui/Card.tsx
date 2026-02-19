import { type ReactNode } from 'react';
import { motion } from 'framer-motion';

export interface CardProps {
  children: ReactNode;
  className?: string;
  variant?: 'default' | 'glass' | 'elevated';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  animate?: boolean;
}

export function Card({
  children,
  className = '',
  variant = 'default',
  padding = 'md',
  animate = false,
}: CardProps) {
  const variants = {
    default: 'bg-gray-800',
    glass: 'bg-white/10 backdrop-blur-lg border border-white/20',
    elevated: 'bg-gray-800 shadow-lg',
  };

  const paddings = {
    none: '',
    sm: 'p-3',
    md: 'p-5',
    lg: 'p-8',
  };

  const cardContent = (
    <div
      className={`
        rounded-2xl shadow-soft 
        ${variants[variant]} 
        ${paddings[padding]} 
        ${className}
      `}
    >
      {children}
    </div>
  );

  if (animate) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
      >
        {cardContent}
      </motion.div>
    );
  }

  return cardContent;
}
