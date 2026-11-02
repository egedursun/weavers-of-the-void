import { type ReactNode, useId } from 'react'
import { Label as FieldLabel } from '@/components/ui/label'
import { Muted } from '@/components/typography'

type FormRowProps = {
  label: string
  description?: string
  children: (controlId: string) => ReactNode
}

export function FormRow({ label, description, children }: FormRowProps) {
  const controlId = useId()
  return (
    <div
      data-domain='form-row'
      className='flex h-full min-w-0 flex-col justify-between gap-2'
    >
      <div className='flex min-w-0 flex-col gap-0.5'>
        <FieldLabel htmlFor={controlId}>{label}</FieldLabel>
        {description && <Muted variant='caption'>{description}</Muted>}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {children(controlId)}
      </div>
    </div>
  )
}
