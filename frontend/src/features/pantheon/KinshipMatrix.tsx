import { useState } from 'react'
import { Users } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { EmptyState, EntityLink, Section, FieldTile } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { ActionButton } from './ActionButton'
import {
  type SonPublic,
  type WorldState,
  useSonRelations,
  useSons,
} from './api'
import { RELATION_SCALE } from './constants'
import { useGodGate, useRuleLookup } from './gate'
import { useGodAction } from './godAction'
import { relationLabel, signed } from './relations'

const COVENANT_MARK = '\u26ad'

function toneOf(
  value: number,
  rule: (path: string) => number | undefined
): string {
  const close = rule('core_rules.relation_close_friend')
  const friend = rule('core_rules.relation_friend')
  const enemy = rule('core_rules.relation_enemy')
  const cold = rule('core_rules.relation_cold')
  if (close !== undefined && value >= close)
    return 'border-success/70 bg-success/40 text-foreground'
  if (friend !== undefined && value >= friend)
    return 'border-success/40 bg-success/20 text-foreground'
  if (enemy !== undefined && value <= -enemy)
    return 'border-destructive/70 bg-destructive/40 text-foreground'
  if (cold !== undefined && value <= -cold)
    return 'border-destructive/40 bg-destructive/20 text-foreground'
  return ''
}

function Cell({
  first,
  second,
  value,
  covenant,
}: {
  first: SonPublic
  second: SonPublic
  value: number
  covenant: boolean
}) {
  const rule = useRuleLookup()
  const { reason } = useGodGate()
  const [draft, setDraft] = useState(String(value))
  const set = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/son:relation', {
          body: {
            first_id: first.son.id,
            second_id: second.son.id,
            value: Number(draft),
          },
        })
      ),
    success: 'The relation was set',
  })
  const title = `${first.son.name} and ${second.son.name}: ${relationLabel(value, rule)} (${signed(value)})${covenant ? ' · covenant' : ''}`
  return (
    <Popover onOpenChange={(open) => open && setDraft(String(value))}>
      <PopoverTrigger asChild>
        <Button
          variant='ghost'
          size='sm'
          className={cn('w-full tabular-nums', toneOf(value, rule))}
          aria-label={title}
          title={title}
        >
          {`${signed(value)}${covenant ? ` ${COVENANT_MARK}` : ''}`}
        </Button>
      </PopoverTrigger>
      <PopoverContent className='flex flex-col gap-2'>
        <div className='flex min-w-0 items-end gap-2'>
          <FieldTile label={title} className='flex-1'>
            <Input
              aria-label='New relation'
              type='number'
              min={-RELATION_SCALE}
              max={RELATION_SCALE}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
            />
          </FieldTile>
          <ActionButton
            label='Set'
            blocked={reason() ?? (draft === '' ? 'Enter a value.' : null)}
            pending={set.isPending}
            onRun={() => set.mutate()}
          />
        </div>
        <Muted variant='caption'>
          Shared domains, councils and deeds keep moving it.
        </Muted>
      </PopoverContent>
    </Popover>
  )
}

export function KinshipMatrix({ state }: { state: WorldState }) {
  const sons = useSons()
  const relations = useSonRelations()
  const alive = (sons.data ?? state.sons).filter(
    (view) => view.son.status !== 'dead'
  )
  const pairs = relations.data ?? state.relations
  const valueOf = (first: number, second: number) => {
    const low = Math.min(first, second)
    const high = Math.max(first, second)
    return (
      pairs.find((item) => item.son_a_id === low && item.son_b_id === high)
        ?.value ?? 0
    )
  }
  const covenantOf = (first: number, second: number) =>
    state.covenants.some(
      (item) =>
        (item.son_a_id === first && item.son_b_id === second) ||
        (item.son_a_id === second && item.son_b_id === first)
    )
  return (
    <Section
      title='Kinship'
      description='How the sons stand with one another. Pick a cell to set it yourself.'
    >
      {alive.length < 2 ? (
        <EmptyState
          icon={Users}
          size='compact'
          title='Kinship needs at least two sons'
          description='Summon another son to see how they stand.'
        />
      ) : (
        <div className='min-w-0 overflow-x-auto'>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  <span className='sr-only'>Son</span>
                </TableHead>
                {alive.map((view) => (
                  <TableHead key={view.son.id}>
                    <Label truncate className='max-w-24'>
                      {view.son.name}
                    </Label>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {alive.map((row) => (
                <TableRow key={row.son.id}>
                  <TableHead scope='row'>
                    <EntityLink
                      kind='son'
                      id={String(row.son.id)}
                      rarity={row.son.rarity}
                      className='max-w-32'
                    >
                      {row.son.name}
                    </EntityLink>
                  </TableHead>
                  {alive.map((column) => (
                    <TableCell key={column.son.id}>
                      {row.son.id === column.son.id ? null : (
                        <Cell
                          first={row}
                          second={column}
                          value={valueOf(row.son.id, column.son.id)}
                          covenant={covenantOf(row.son.id, column.son.id)}
                        />
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Section>
  )
}
