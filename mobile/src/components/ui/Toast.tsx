import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle,
  XCircle,
  Warning,
  Info,
  X,
} from '@phosphor-icons/react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastProps {
  type: ToastType;
  message: string;
  isVisible: boolean;
  onClose: () => void;
  duration?: number;
}

const icons = {
  success: CheckCircle,
  error: XCircle,
  warning: Warning,
  info: Info,
};

const colors = {
  success: {
    bg: 'bg-success-500/10 border-success-500/30',
    icon: 'text-success-500',
  },
  error: {
    bg: 'bg-error-500/10 border-error-500/30',
    icon: 'text-error-500',
  },
  warning: {
    bg: 'bg-yellow-500/10 border-yellow-500/30',
    icon: 'text-yellow-500',
  },
  info: {
    bg: 'bg-primary-500/10 border-primary-500/30',
    icon: 'text-primary-500',
  },
};

export function Toast({
  type,
  message,
  isVisible,
  onClose,
}: ToastProps) {
  const Icon = icons[type];
  const color = colors[type];

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          className={`
            fixed top-4 left-4 right-4 z-[100] max-w-md mx-auto
            flex items-center gap-3 px-4 py-3 rounded-xl border
            ${color.bg} backdrop-blur-lg shadow-lg
          `}
        >
          <Icon className={`w-6 h-6 flex-shrink-0 ${color.icon}`} weight="fill" />
          <p className="flex-1 text-body-sm text-white">{message}</p>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function StatusBadge({
  type,
  children,
}: {
  type: ToastType;
  children: React.ReactNode;
}) {
  const color = colors[type];

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-caption font-medium
        ${color.bg} ${color.icon}
      `}
    >
      {children}
    </span>
  );
}
