export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return <p className="py-8 text-center text-sm text-gray-500">{label}</p>
}

export function ErrorState({ message }: { message: string }) {
  return (
    <p className="rounded-md bg-status-critical/10 px-4 py-3 text-sm text-status-critical">
      {message}
    </p>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <p className="py-8 text-center text-sm text-gray-500">{message}</p>
}
