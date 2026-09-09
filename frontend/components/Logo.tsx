import React from 'react'

interface LogoProps {
  size?: number
  showText?: boolean
  className?: string
  textClassName?: string
}

export function Logo({
  size = 32,
  showText = true,
  className = '',
  textClassName = '',
}: LogoProps) {
  const gradientId = React.useId()

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <div
        className="relative flex items-center justify-center shrink-0"
        style={{ width: size, height: size }}
      >
        <svg
          width={size}
          height={size}
          viewBox="0 0 40 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="drop-shadow-[0_0_12px_rgba(59,130,246,0.5)]"
        >
          <defs>
            <linearGradient
              id={gradientId}
              x1="0%"
              y1="0%"
              x2="100%"
              y2="100%"
            >
              <stop offset="0%" stopColor="#3B82F6" />
              <stop offset="50%" stopColor="#6366F1" />
              <stop offset="100%" stopColor="#8B5CF6" />
            </linearGradient>
            <linearGradient
              id={`${gradientId}-accent`}
              x1="0%"
              y1="100%"
              x2="100%"
              y2="0%"
            >
              <stop offset="0%" stopColor="#60A5FA" />
              <stop offset="100%" stopColor="#A78BFA" />
            </linearGradient>
          </defs>

          {/* Outer Rounded Hexagon / Shield Node */}
          <path
            d="M20 3L35 11.66V28.34L20 37L5 28.34V11.66L20 3Z"
            fill={`url(#${gradientId})`}
            fillOpacity="0.15"
            stroke={`url(#${gradientId})`}
            strokeWidth="2.5"
            strokeLinejoin="round"
          />

          {/* Stylized Inner 'F' & Node Spark */}
          <path
            d="M13 13H27M13 13V27M13 20H23"
            stroke={`url(#${gradientId}-accent)`}
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Glowing Center Core Pulse */}
          <circle
            cx="24"
            cy="24"
            r="3.5"
            fill="#60A5FA"
            className="animate-pulse"
          />
        </svg>
      </div>

      {showText && (
        <div className="flex flex-col">
          <div className="flex items-center gap-1.5">
            <span
              className={`font-mono font-bold tracking-tight text-white text-base ${textClassName}`}
            >
              FleetMind
            </span>
            <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-fleet-accent/20 text-fleet-accent border border-fleet-accent/30">
              AI
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export default Logo
