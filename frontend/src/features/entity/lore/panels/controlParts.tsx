import { useState } from 'react'
import { type LucideIcon } from 'lucide-react'
import { type ActionBody, type ActionName, postAction } from '@/api/actions'
import { type ActProp } from '@/api/mutation'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodAction } from '@/features/pantheon/godAction'
import { busyOf } from '../model'

export function useLoreAction<Name extends ActionName, T>(
  name: Name,
  body: (value: T) => ActionBody<Name>
) {
  return useGodAction<T>({
    writes: [{ lever: name }],
    run: (value) => postAction(name, body(value)),
  })
}

export function PickAndRun({
  types,
  placeholder,
  label,
  icon: Icon,
  blocked,
  pending,
  note,
  onRun,
  variant = 'outline',
  act,
}: {
  types: readonly string[]
  placeholder: string
  label: string
  icon: LucideIcon
  blocked: string | null
  pending: boolean
  note?: string
  onRun: (id: number) => void
  variant?: 'outline' | 'default' | 'destructive'
  act?: ActProp
}) {
  const [picked, setPicked] = useState<number | null>(null)
  const busy = busyOf(blocked, pending)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      {note && <Muted variant='caption'>{note}</Muted>}
      <EntityPicker
        types={[...types]}
        value={picked}
        onChange={setPicked}
        placeholder={placeholder}
      />
      <Button
        act={act}
        size='sm'
        variant={variant}
        className='self-start'
        disabled={busy !== null || picked === null}
        disabledReason={busy ?? (picked === null ? 'Choose first' : undefined)}
        onClick={() => picked !== null && onRun(picked)}
      >
        <Icon />
        {label}
      </Button>
    </div>
  )
}
