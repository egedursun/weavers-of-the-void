import * as React from 'react'
import { type ActProp, refusalOf } from '@/api/mutation'
import { cn } from '@/lib/utils'
import { controlText } from './control-size'
import { fieldSurface } from './input'

function Textarea({
  className,
  act,
  readOnly,
  ...props
}: React.ComponentProps<'textarea'> & { act?: ActProp }) {
  const refusal = refusalOf(act)
  return (
    <textarea
      readOnly={readOnly || refusal !== null}
      aria-description={refusal ?? undefined}
      title={refusal ?? props.title}
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
