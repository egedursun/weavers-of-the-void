import { useState } from 'react'
import { Lock, Plus, ScrollText, Trash2, Unlock } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { EntityLink, FieldTile, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodAction } from '@/features/pantheon/godAction'
import { AddBar, ItemRow, MindCard, NodePicker } from '../mind/parts'

type Will = components['schemas']['WillView']
type Line = { heir_id: number; share: number }

const WHOLE = 100
const WORKING = 'Working on it.'

function lines(will: Will | null): Line[] {
  return (will?.heirs ?? []).map((row) => ({
    heir_id: row.heir.id,
    share: row.share,
  }))
}

function rebalance(current: Line[], heirId: number, share: number): Line[] {
  const kept = Math.max(1, Math.min(WHOLE, share))
  const others = current.filter((line) => line.heir_id !== heirId)
  if (others.length === 0) return [{ heir_id: heirId, share: WHOLE }]
  const rest = WHOLE - Math.min(kept, WHOLE - others.length)
  const weight = others.reduce((sum, line) => sum + line.share, 0) || 1
  const spread = others.map((line) => ({
    heir_id: line.heir_id,
    share: Math.max(1, Math.floor((line.share * rest) / weight)),
  }))
  const given = spread.reduce((sum, line) => sum + line.share, 0)
  const own = WHOLE - given
  return [...spread, { heir_id: heirId, share: own }]
}

export function WillCard({
  testatorId,
  will,
  blocked,
  hold,
}: {
  testatorId: number
  will: Will | null
  blocked: string | null
  hold: boolean
}) {
  const [heir, setHeir] = useState<number | null>(null)
  const [forged, setForged] = useState(will?.forged ?? false)
  const write = useGodAction({
    writes: [{ lever: 'will:set' }],
    run: ({ heirs, hand }: { heirs: Line[]; hand: boolean }) =>
      unwrap(
        api.POST('/api/actions/will:set', {
          body: {
            testator_id: testatorId,
            heirs,
            witnesses: will?.witnesses.map((ref) => ref.id) ?? [],
            forged: hand,
            hold,
          },
        })
      ),
  })
  const tear = useGodAction({
    writes: [{ lever: 'will:remove' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/will:remove', {
          body: { testator_id: testatorId },
        })
      ),
  })
  const busy = blocked ?? (write.isPending || tear.isPending ? WORKING : null)
  const current = lines(will)
  const named = heir !== null && current.some((line) => line.heir_id === heir)
  const addReason =
    busy ??
    (heir === null
      ? 'Choose an heir first.'
      : heir === testatorId
        ? 'No one is their own heir.'
        : named
          ? 'That heir is already named.'
          : null)
  return (
    <MindCard
      title='Will'
      icon={ScrollText}
      hint='Read when they die: what they own passes to the heirs by these shares. Kin left out may contest it, and a forged will is set aside when contested.'
    >
      {will ? (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant='secondary'>
            {`Made in epoch ${will.made_epoch}`}
          </Badge>
          {will.read_epoch !== null && (
            <Badge size='sm' variant='default'>
              {`Read in epoch ${will.read_epoch}`}
            </Badge>
          )}
          {will.contested && (
            <Badge size='sm' variant='destructive'>
              Contested
            </Badge>
          )}
          {will.set_aside && (
            <Badge size='sm' variant='destructive'>
              Set aside
            </Badge>
          )}
          {will.forged && (
            <Badge size='sm' variant='destructive'>
              Forged
            </Badge>
          )}
          {will.held && (
            <Badge size='sm' variant='default'>
              <Lock />
              Held
            </Badge>
          )}
        </div>
      ) : (
        <Muted variant='caption'>
          No will is written; custom decides the heirs.
        </Muted>
      )}
      {current.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={will?.heirs ?? []} as='li'>
            {(row) => (
              <li key={row.heir.id} className='min-w-0'>
                <ItemRow
                  icon={ScrollText}
                  tone='gold'
                  title={
                    <EntityLink kind='entity' id={String(row.heir.id)}>
                      {row.heir.name}
                    </EntityLink>
                  }
                  meta={`${row.share} of every hundred parts of what they own`}
                  actions={
                    <Button
                      act={write}
                      size='sm'
                      variant='ghost'
                      disabled={busy !== null || current.length < 2}
                      disabledReason={
                        busy ??
                        (current.length < 2
                          ? 'A will names at least one heir; tear it up instead.'
                          : undefined)
                      }
                      onClick={() =>
                        write.mutate({
                          heirs: rebalance(
                            current.filter(
                              (line) => line.heir_id !== row.heir.id
                            ),
                            current.find((line) => line.heir_id !== row.heir.id)
                              ?.heir_id ?? row.heir.id,
                            current.find((line) => line.heir_id !== row.heir.id)
                              ?.share ?? WHOLE
                          ),
                          hand: forged,
                        })
                      }
                    >
                      Strike out
                    </Button>
                  }
                  editLabel={`share of ${row.heir.name}`}
                  editor={
                    <AdjustStats
                      id={`will-${testatorId}-${row.heir.id}`}
                      inline
                      groups={[
                        {
                          title: 'Share',
                          fields: [
                            {
                              key: 'share',
                              label: 'Parts of a hundred',
                              value: row.share,
                              min: 1,
                              max: WHOLE,
                            },
                          ],
                        },
                      ]}
                      run={({ value }) =>
                        unwrap(
                          api.POST('/api/actions/will:set', {
                            body: {
                              testator_id: testatorId,
                              heirs: rebalance(current, row.heir.id, value),
                              witnesses:
                                will?.witnesses.map((ref) => ref.id) ?? [],
                              forged,
                              hold,
                            },
                          })
                        )
                      }
                    />
                  }
                />
              </li>
            )}
          </Paged>
        </ul>
      )}
      {will && will.witnesses.length > 0 && (
        <Text variant='caption'>
          {`Witnessed by ${will.witnesses.map((ref) => ref.name).join(', ')}`}
        </Text>
      )}
      <FieldTile
        id={`will-forged-${testatorId}`}
        label='Written in a forged hand'
        className='items-center'
      >
        <Switch
          act={write}
          id={`will-forged-${testatorId}`}
          checked={forged}
          disabled={busy !== null || current.length === 0}
          onCheckedChange={(hand) => {
            setForged(hand)
            write.mutate({ heirs: current, hand })
          }}
          aria-label='Written in a forged hand'
        />
      </FieldTile>
      <AddBar
        title='Name an heir'
        action={
          <Button
            act={write}
            size='sm'
            disabled={addReason !== null}
            disabledReason={addReason ?? undefined}
            onClick={() => {
              if (heir === null) return
              write.mutate({
                heirs:
                  current.length === 0
                    ? [{ heir_id: heir, share: WHOLE }]
                    : rebalance(
                        [
                          ...current,
                          {
                            heir_id: heir,
                            share: Math.floor(WHOLE / (current.length + 1)),
                          },
                        ],
                        heir,
                        Math.floor(WHOLE / (current.length + 1))
                      ),
                hand: forged,
              })
              setHeir(null)
            }}
          >
            {hold ? <Lock /> : <Unlock />}
            <Plus />
            {current.length === 0 ? 'Write the will' : 'Add to the will'}
          </Button>
        }
      >
        <NodePicker
          label='Heir'
          types={['mortal']}
          value={heir}
          onChange={setHeir}
          blocked={busy}
        />
      </AddBar>
      <Button
        act={tear}
        className='self-start'
        size='sm'
        variant='outline'
        disabled={busy !== null || !will}
        disabledReason={busy ?? (!will ? 'No will is written.' : undefined)}
        onClick={() => tear.mutate()}
      >
        <Trash2 />
        Tear up the will
      </Button>
    </MindCard>
  )
}
