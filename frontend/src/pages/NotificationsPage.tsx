import { useState } from 'react'
import { useMarkNotificationRead, useNotifications } from '../api/queries'
import { EmptyState, ErrorState, LoadingState } from '../components/AsyncState'

export function NotificationsPage() {
  const [unreadOnly, setUnreadOnly] = useState(false)
  const notifications = useNotifications(unreadOnly)
  const markRead = useMarkNotificationRead()

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Notifications</h1>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={(event) => setUnreadOnly(event.target.checked)}
          />
          Unread only
        </label>
      </div>

      <div className="mt-4 divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
        {notifications.isLoading && <LoadingState />}
        {notifications.isError && <ErrorState message="Failed to load notifications." />}
        {notifications.data?.items.length === 0 && <EmptyState message="No notifications." />}
        {notifications.data?.items.map((notification) => (
          <div
            key={notification.id}
            className={`flex items-start justify-between gap-4 px-4 py-3 ${
              notification.is_read ? '' : 'bg-brand-blue/5'
            }`}
          >
            <div>
              <p className="text-sm font-medium text-gray-900">{notification.title}</p>
              <p className="text-sm text-gray-600">{notification.body}</p>
              <p className="mt-1 text-xs text-gray-400">
                {new Date(notification.created_at).toLocaleString()}
              </p>
            </div>
            {!notification.is_read && (
              <button
                type="button"
                onClick={() => markRead.mutate(notification.id)}
                className="whitespace-nowrap rounded-md border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
              >
                Mark read
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
