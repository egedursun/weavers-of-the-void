import { useState } from 'react'
import { type LucideIcon } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodAction } from '@/features/pantheon/godAction'
import { busyOf } from '../model'

export function useLoreAction<T>(path: string, body: (value: T) => object) {
  return useGodAction<T>({
    run: (value) =>
      unwrap(
        api.POST(path as '/api/actions/lore:edit', {
          body: body(value) as never,
        })
      ),
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
