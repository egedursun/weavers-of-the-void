import { Skeleton } from '@/components/ui/skeleton'

const GHOST_ROWS = ['w-full', 'w-5/6', 'w-2/3']

export function LoadingBlock({ label }: { label: string }) {
  return (
    <div
      role='status'
      aria-busy='true'
      aria-label={label}
      data-domain='loading-block'
      className='flex min-w-0 flex-col gap-2'
    >
      {GHOST_ROWS.map((width) => (
        <Skeleton key={width} className={`h-control-sm ${width}`} />
      ))}
      <span className='sr-only'>{label}</span>
    </div>
  )
}
