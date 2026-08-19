export function Pagination({
  total,
  limit,
  offset,
  onOffsetChange,
}: {
  total: number
  limit: number
  offset: number
  onOffsetChange: (offset: number) => void
}) {
  if (total <= limit) return null

  const page = Math.floor(offset / limit) + 1
  const pageCount = Math.max(1, Math.ceil(total / limit))

  return (
    <div className="flex items-center justify-between border-t border-gray-200 px-1 py-3 text-sm text-gray-600">
      <span>
        Page {page} of {pageCount} &middot; {total} total
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
          disabled={offset === 0}
          onClick={() => onOffsetChange(Math.max(0, offset - limit))}
        >
          Previous
        </button>
        <button
          type="button"
          className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
          disabled={offset + limit >= total}
          onClick={() => onOffsetChange(offset + limit)}
        >
          Next
        </button>
      </div>
    </div>
  )
}
