import { GitCompareArrows, ShieldCheck, Swords } from 'lucide-react'
import { type ConflictChange, usePendingConflict } from '@/api/conflicts'
import { formatSince } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Medallion, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { spokenField } from './teamLook'

const NOTHING = 'nothing'

function shown(value: unknown): string {
  if (value === null || value === undefined || value === '') return NOTHING
  if (typeof value === 'number') return value.toLocaleString('en-US')
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}

function ValueCell({
  caption,
  value,
  strong,
}: {
  caption: string
  value: string
  strong?: boolean
}) {
  return (
    <div className='flex min-w-0 flex-col gap-0.5 rounded-md surface-well p-2'>
      <Muted as='span' variant='caption'>
        {caption}
      </Muted>
      <Text
        as='span'
        weight={strong ? 'semibold' : 'normal'}
        truncate={2}
        tone={value === NOTHING ? 'muted' : 'default'}
      >
        {value}
      </Text>
    </div>
  )
}

function ChangeRow({
  change,
  mine,
}: {
  change: ConflictChange
  mine: Record<string, unknown>
}) {
  const field = change.field ?? change.table
  const yours = change.field !== null && change.field in mine
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg surface-sheen p-3'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Text as='span' weight='semibold'>
          {spokenField(field)}
        </Text>
        <Badge variant='outline' size='sm'>
          {change.by ?? 'Someone else'}
          {change.at ? ` · ${formatSince(change.at)}` : ''}
        </Badge>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
        <ValueCell caption='When you opened it' value={shown(change.before)} />
        <ValueCell caption='Theirs now' value={shown(change.after)} strong />
        <ValueCell
          caption='Yours'
          value={yours ? shown(mine[change.field ?? '']) : 'Unchanged by you'}
          strong={yours}
        />
      </div>
    </li>
  )
}

export function ConflictDialog() {
  const conflict = usePendingConflict()
  const people = [
    ...new Set((conflict?.changes ?? []).map((item) => item.by ?? 'Someone')),
  ]
  return (
    <Dialog
      open={conflict !== null}
      onOpenChange={(open) => {
        if (!open) conflict?.decide('theirs')
      }}
    >
      <DialogContent className='sm:max-w-2xl'>
        <DialogHeader>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={GitCompareArrows} tone='warning' />
            <DialogTitle>Someone changed this while you worked</DialogTitle>
          </div>
          <DialogDescription>
            {`${people.join(' and ')} changed what you are saving since you opened it. Choose whose values stand; nothing is lost either way, and every change stays in the ledger.`}
          </DialogDescription>
        </DialogHeader>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='gilded'>What they changed</Label>
          <ul
            aria-label='Changes made by others'
            className='flex min-w-0 flex-col gap-2'
          >
            <Paged items={conflict?.changes ?? []} as='li'>
              {(change, position) => (
                <ChangeRow
                  key={`${change.table}-${change.field ?? ''}-${position}`}
                  change={change}
                  mine={conflict?.mine ?? {}}
                />
              )}
            </Paged>
          </ul>
        </div>
        <DialogFooter>
          <Button
            type='button'
            variant='outline'
            onClick={() => conflict?.decide('theirs')}
          >
            <ShieldCheck />
            Keep theirs
          </Button>
          <Button type='button' onClick={() => conflict?.decide('mine')}>
            <Swords />
            Apply mine over theirs
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
