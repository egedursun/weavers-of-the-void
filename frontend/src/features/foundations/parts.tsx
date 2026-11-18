import { useId } from 'react'
import { type QueryKey } from '@tanstack/react-query'
import { Lock, LockOpen } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { FieldTile } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useSons } from '@/features/pantheon/api'
import { useGodAction } from '@/features/pantheon/godAction'
import { type HoldKind, holdFoundation } from './api'

export const NO_SON = 'none'

export function HoldToggle({
  kind,
  nodeId,
  held,
  blocked,
  what,
  invalidate,
}: {
  kind: HoldKind
  nodeId: number
  held: boolean
  blocked: string | null
  what: string
  invalidate?: QueryKey[]
}) {
  const toggle = useGodAction<boolean>({
    run: (next) => holdFoundation(kind, nodeId, next),
    invalidate,
  })
  const Icon = held ? Lock : LockOpen
  const busy = blocked ?? (toggle.isPending ? 'Working…' : null)
  return (
    <label
      data-surface='FoundationHold'
      className={cn(
        'flex min-w-0 cursor-pointer items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2.5',
        held ? 'border-primary/40 bg-primary/5' : 'bg-card'
      )}
    >
      <Icon
        aria-hidden='true'
        className={cn(
          'size-icon-sm shrink-0',
          held ? 'text-primary' : 'text-muted-foreground'
        )}
      />
      <span className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' weight='medium' truncate>
          {held ? `Held: ${what}` : `Free: ${what}`}
        </Text>
        <Muted as='span' variant='caption' truncate>
          {held
            ? 'The world keeps it as you set it. Release it to let the engine move it again.'
            : 'The engine may change it. Hold it to keep it as it is.'}
        </Muted>
      </span>
      <Switch
        checked={held}
        disabled={busy !== null}
        aria-label={held ? `Release ${what}` : `Hold ${what}`}
        onCheckedChange={(next) => toggle.mutate(next)}
      />
    </label>
  )
}

export function SonSelect({
  label,
  value,
  onChange,
  allowNone = false,
  disabled = false,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  allowNone?: boolean
  disabled?: boolean
}) {
  const id = useId()
  const sons = useSons()
  const living = (sons.data ?? []).filter((item) => item.son.status !== 'dead')
  return (
    <FieldTile id={id} label={label}>
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger id={id} aria-label={label} className='w-full'>
          <SelectValue placeholder='Choose a god' />
        </SelectTrigger>
        <SelectContent>
          {allowNone && <SelectItem value={NO_SON}>No god</SelectItem>}
          {living.map((item) => (
            <SelectItem key={item.son.id} value={String(item.son.id)}>
              {item.son.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FieldTile>
  )
}
