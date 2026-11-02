import { useRouterState } from '@tanstack/react-router'
import { Progress } from '@/components/ui/progress'

export function NavigationProgress() {
  const pending = useRouterState({
    select: (state) => state.status === 'pending',
  })
  if (!pending) return null
  return (
    <div
      data-layout='navigation-progress'
      className='fixed inset-x-0 top-0 z-50'
    >
      <Progress
        indeterminate
        size='sm'
        aria-label='Loading'
        className='rounded-none bg-transparent'
      />
    </div>
  )
}
