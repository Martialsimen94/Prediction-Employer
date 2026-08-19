import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="py-16 text-center">
      <p className="text-lg font-semibold text-gray-900">Page not found</p>
      <Link to="/" className="mt-2 inline-block text-sm text-brand-blue hover:underline">
        Go back home
      </Link>
    </div>
  )
}
