import { useMemo, useState } from 'react'
import { BookMarked, Feather, Lock, LockOpen } from 'lucide-react'
import { type EditValues, postAction } from '@/api/actions'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState, EntityLink, Paged, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { KeeperName } from '@/features/chronicle/KeeperByline'
import { ThingPicker } from '@/features/gatherings/parts'
import { useNames } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { fateKeys, type RecordKeeper } from './api'

const KEEPER = 'keeper_entity_id'

const KIND_LABEL: Record<RecordKeeper['kind'], string> = {
  chronicler: 'Chronicler of the cosmos',
  historian: 'Historian of a people',
}

function useNodeNames() {
  const names = useNames()
  return useMemo(() => {
    const table = new Map<number, string>()
    for (const entry of names.data ?? []) table.set(entry.id, entry.name)
    return table
  }, [names.data])
}

function KeeperRow({
  keeper,
  names,
}: {
  keeper: RecordKeeper
  names: Map<number, string>
}) {
  const { reason } = useGodGate()
  const [picked, setPicked] = useState<number | null>(null)
  const edit = useGodAction<{ values: EditValues; release: string[] }>({
    writes: [{ lever: 'record_row:edit' }],
    run: ({ values, release }) =>
      postAction('record_row:edit', {
        table: 'record_keepers',
        key: { id: keeper.id },
        values,
        hold: Object.keys(values).length > 0,
        release,
      }),
    invalidate: [fateKeys.controls],
    success: 'The keeper of the record is set',
  })
  const held = keeper.locked.includes(KEEPER)
  const blocked = reason({})
  const scope = names.get(keeper.scope_node_id) ?? 'this people'
  const choose = () =>
    edit.mutate(
      { values: { [KEEPER]: picked }, release: [] },
      { onSuccess: () => setPicked(null) }
    )
  const release = () => edit.mutate({ values: {}, release: [KEEPER] })
  return (
    <li
      data-record-keeper={keeper.id}
      className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2'>
        <div className='flex min-w-0 flex-1 basis-60 flex-col gap-0.5'>
          <Text weight='medium' truncate={2}>
            {keeper.kind === 'historian' ? (
              <EntityLink kind='entity' id={String(keeper.scope_node_id)}>
                {scope}
              </EntityLink>
            ) : (
              KIND_LABEL.chronicler
            )}
          </Text>
          <Muted
            as='p'
            variant='caption'
            className='flex min-w-0 flex-wrap items-center gap-x-1'
          >
            <Feather aria-hidden='true' className='size-icon-xs shrink-0' />
            <span>
              {keeper.keeper_entity_id === null
                ? 'No living mortal keeps it'
                : 'Kept by'}
            </span>
            {keeper.keeper_entity_id !== null && (
              <KeeperName
                id={keeper.keeper_entity_id}
                name={names.get(keeper.keeper_entity_id)}
                fallback='a mortal'
              />
            )}
            {keeper.keeper_entity_id !== null && (
              <span>{`since epoch ${formatInteger(keeper.since_epoch)}`}</span>
            )}
          </Muted>
        </div>
        <Badge variant={held ? 'default' : 'outline'}>
          {held ? <Lock /> : <LockOpen />}
          {held ? 'Held by you' : 'Chosen by the world'}
        </Badge>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='min-w-0 flex-1 basis-64'>
          <ThingPicker
            label={
              keeper.kind === 'historian'
                ? 'Choose its historian'
                : 'Choose the chronicler'
            }
            value={picked}
            onChange={setPicked}
            blocked={blocked}
            types={['mortal']}
          />
        </div>
        <Button
          act={edit}
          size='sm'
          disabled={blocked !== null || picked === null || edit.isPending}
          disabledReason={
            blocked ??
            (picked === null ? 'Choose a living mortal first' : undefined)
          }
          onClick={choose}
        >
          <Lock />
          Set and hold
        </Button>
        <Button
          act={edit}
          variant='outline'
          size='sm'
          disabled={blocked !== null || !held || edit.isPending}
          disabledReason={
            blocked ??
            (held ? undefined : 'The world already chooses this keeper')
          }
          onClick={release}
        >
          <LockOpen />
          Let the world choose
        </Button>
      </div>
    </li>
  )
}

export function KeepersPanel({ keepers }: { keepers: RecordKeeper[] }) {
  const names = useNodeNames()
  return (
    <Section
      id='section-record-keepers'
      title='Keepers of the record'
      description='The living mortals who write the chronicle of every age and the history of each people. When one dies, the world chooses a successor from those who write, unless you hold your own choice.'
      surface='card'
      level={3}
      icon={BookMarked}
      tone='gold'
    >
      {keepers.length === 0 ? (
        <EmptyState
          size='compact'
          icon={BookMarked}
          title='No keepers yet'
          description='The world seats a chronicler and a historian for each people when its first epoch runs.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={keepers} as='li'>
            {(keeper) => (
              <KeeperRow key={keeper.id} keeper={keeper} names={names} />
            )}
          </Paged>
        </ul>
      )}
    </Section>
  )
}
