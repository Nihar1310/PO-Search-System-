import { forwardRef } from 'react'
import { Loader2 } from 'lucide-react'

const variantClassMap = {
  primary: 'glass-button--primary',
  neutral: 'glass-button--neutral',
  danger: 'glass-button--danger',
  ghost: 'glass-button--ghost',
}

const GlassButton = forwardRef(function GlassButton(
  {
    children,
    className = '',
    variant = 'primary',
    icon: Icon,
    iconPosition = 'left',
    loading = false,
    ...props
  },
  ref
) {
  const renderIcon = (position) => {
    if (loading) {
      return position === iconPosition ? (
        <Loader2 aria-hidden className="glass-button__icon glass-button__spinner" />
      ) : null
    }
    if (Icon && position === iconPosition) {
      return <Icon aria-hidden className="glass-button__icon" />
    }
    return null
  }

  const classes = ['glass-button', variantClassMap[variant] || '', className]
    .filter(Boolean)
    .join(' ')

  return (
    <button
      ref={ref}
      className={classes}
      aria-busy={loading || undefined}
      {...props}
    >
      {renderIcon('left')}
      <span className="glass-button__text">{children}</span>
      {renderIcon('right')}
      <span className="glass-button__shine" aria-hidden />
    </button>
  )
})

export default GlassButton
