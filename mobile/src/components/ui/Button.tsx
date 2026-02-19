import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { motion } from 'framer-motion';
import { Spinner } from '@phosphor-icons/react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles = `
      inline-flex items-center justify-center gap-2 
      font-semibold rounded-xl transition-all duration-200 
      active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed
      focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900
    `;

    const variants = {
      primary: 'bg-primary-500 text-white hover:bg-primary-600 focus:ring-primary-500 shadow-soft hover:shadow-glow',
      secondary: 'bg-gray-800 text-gray-300 hover:bg-gray-700 focus:ring-gray-500',
      success: 'bg-success-500 text-white hover:bg-success-600 focus:ring-success-500 shadow-soft hover:shadow-glow-success',
      ghost: 'bg-transparent text-gray-400 hover:text-white hover:bg-white/5',
    };

    const sizes = {
      sm: 'px-3 py-2 text-body-sm',
      md: 'px-4 py-3 text-body',
      lg: 'px-6 py-4 text-heading-3',
    };

    return (
      <motion.button
        ref={ref}
        whileTap={{ scale: 0.98 }}
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
        disabled={disabled || isLoading}
        {...(props as any)}
      >
        {isLoading ? (
          <Spinner className="w-5 h-5 animate-spin" />
        ) : (
          leftIcon
        )}
        {children}
        {!isLoading && rightIcon}
      </motion.button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
