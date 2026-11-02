import * as React from 'react'
import { cn } from '@/lib/utils'
import { controlText } from './control-size'
import { fieldSurface } from './input'

function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      data-slot='textarea'
      className={cn(
        'flex field-sizing-content min-h-textarea w-full px-3 py-2',
        fieldSurface,
        controlText,
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
