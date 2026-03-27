interface DevModeBannerProps {
  show: boolean
}

export function DevModeBanner({ show }: DevModeBannerProps) {
  if (!show) return null
  return (
    <div
      role="alert"
      className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-center text-xs text-amber-800"
    >
      ⚠ Dev mode active (<code>LINGO_DEV_MODE=true</code>) — authentication is disabled. Not for production use.
    </div>
  )
}
