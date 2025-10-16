export default function LogoIcon({ size = 48 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <g stroke="#ec1c24" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="60" cy="60" r="52" />
        <path d="M36 84 L60 34" />
        <path d="M60 82 L88 82" />
        <path d="M72 86 V36" />
      </g>
    </svg>
  )
}
