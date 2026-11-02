import { cn } from '@/lib/utils'
import { buttonVariants } from '@/components/ui/button'

export function SkipToMain() {
  return (
    <a
      href='#content'
      className={cn(
        buttonVariants(),
        'fixed start-4 top-2 z-50 -translate-y-24 focus:translate-y-0'
      )}
    >
      Skip to content
    </a>
  )
}
