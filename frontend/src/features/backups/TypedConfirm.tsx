import { type ReactNode, useId, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { ConfirmDialog } from '@/components/domain'

type TypedConfirmProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: ReactNode
  word: string
  confirmText: string
  loading: boolean
  onConfirm: (word: string) => void
}

export function TypedConfirm({
  open,
  onOpenChange,
  title,
  description,
  word,
  confirmText,
  loading,
  onConfirm,
}: TypedConfirmProps) {
  const [typed, setTyped] = useState('')
  const id = useId()
  const matches = typed.trim() === word
  return (
    <ConfirmDialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setTyped('')
        onOpenChange(next)
      }}
      title={title}
      desc={<div className='flex min-w-0 flex-col gap-2'>{description}</div>}
      confirmText={confirmText}
      destructive
      disabled={!matches}
      isLoading={loading}
      handleConfirm={() => onConfirm(typed.trim())}
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <FieldLabel htmlFor={id}>{`Type ${word} to confirm`}</FieldLabel>
        <Input
          id={id}
          autoComplete='off'
          value={typed}
          aria-invalid={typed !== '' && !matches}
          onChange={(event) => setTyped(event.target.value)}
        />
      </div>
    </ConfirmDialog>
  )
}
