import { motion } from 'framer-motion';

export interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'spinner' | 'dots' | 'pulse';
  color?: 'primary' | 'white' | 'success';
}

export function Loading({
  size = 'md',
  variant = 'spinner',
  color = 'primary',
}: LoadingProps) {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  const colors = {
    primary: 'text-primary-500',
    white: 'text-white',
    success: 'text-success-500',
  };

  if (variant === 'dots') {
    return (
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className={`w-2 h-2 rounded-full ${colors[color]}`}
            animate={{ scale: [0.8, 1.2, 0.8] }}
            transition={{
              duration: 0.6,
              repeat: Infinity,
              delay: i * 0.15,
            }}
          />
        ))}
      </div>
    );
  }

  if (variant === 'pulse') {
    return (
      <motion.div
        className={`rounded-full ${colors[color]} ${sizes[size]}`}
        animate={{ scale: [0.8, 1.2, 0.8], opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 1.5, repeat: Infinity }}
      />
    );
  }

  return (
    <motion.div
      className={`${sizes[size]} ${colors[color]}`}
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
    >
      <svg viewBox="0 0 24 24" fill="none" className="w-full h-full">
        <circle
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray="31.4 31.4"
        />
      </svg>
    </motion.div>
  );
}

export function LoadingOverlay({ message = 'Carregando...' }: { message?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 bg-gray-900/80 backdrop-blur-sm flex flex-col items-center justify-center gap-4 z-50"
    >
      <Loading size="lg" variant="spinner" color="primary" />
      <p className="text-body-sm text-gray-400">{message}</p>
    </motion.div>
  );
}
