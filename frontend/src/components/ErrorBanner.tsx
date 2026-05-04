type ErrorBannerProps = {
  message: string | null
}

export default function ErrorBanner({ message }: ErrorBannerProps) {
  if (!message) {
    return null
  }

  return <div className="error-banner">{message}</div>
}
