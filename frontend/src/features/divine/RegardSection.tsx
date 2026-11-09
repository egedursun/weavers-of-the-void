import { useState } from 'react'
import { HandHeart, Plus, Save, TriangleAlert } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { Button } from '@/components/ui/button'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { busyOf } from '@/features/entity/lore/model'
import { Group, NumberField } from '@/features/entity/wilds/parts'
import { useWorldState } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { useDivineAction, useRegard } from './api'
import { AXIS_LABELS, STANDING_AXES } from './labels'
import { useGodTable } from './model'
import { PickRow, StandingList } from './parts'

export function RegardSection({
  communityId,
  readOnlyReason,
}: {
  communityId: number
  readOnlyReason?: string | null
}) {
  const view = useRegard(communityId)
  const state = useWorldState()
  const creator = state.data?.creator
    ? { id: state.data.creator.id, name: state.data.creator.name }
    : null
  const gods = useGodTable(creator)
  const { reason } = useGodGate()
  const save = useDivineAction(
    'divine_standing:set',
    (vars: { god: number; values: EditValues; release: string[] }) => ({
      community_id: communityId,
      god_id: vars.god,
      values: vars.values,
      release: vars.release,
    })
  )
  const clear = useDivineAction('divine_standing:clear', (god: number) => ({
    community_id: communityId,
    god_id: god,
  }))
  const [god, setGod] = useState('')
  const [draft, setDraft] = useState<Record<string, string>>({})
  const busy = busyOf(
    readOnlyReason ?? reason(),
    save.isPending,
    clear.isPending
  )
  const values = Object.fromEntries(
    Object.entries(draft)
      .filter(([, text]) => text !== '')
      .map(([key, text]) => [key, Number(text)])
  )
  const problem =
    god === ''
      ? 'Choose a god'
      : Object.keys(values).length === 0
        ? 'Set at least one value'
        : null
  return (
    <Section
      id='section-regard'
      title='Regard of the gods'
      description='How this community regards each god, the Creator among them: awe, love, fear and neglect. Communities hold this regard; individual mortals, places without people and worlds do not.'
      icon={HandHeart}
      tone='verdigris'
    >
      {view.isPending && (
        <LoadingBlock label='Reading their regard of the gods' />
      )}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Their regard could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='CommunityRegard'
          className='flex min-w-0 flex-col gap-3'
        >
          {view.data.standing.length === 0 && (
            <EmptyState
              icon={HandHeart}
              title='No regard yet'
              description='A community forms a regard of the gods it worships and of the Creator after the next epoch; you can set one now.'
            />
          )}
          <StandingList
            rows={view.data.standing}
            focus='community'
            busy={busy}
            onSave={(row, next, release) =>
              save.mutate({ god: row.god.id, values: next, release })
            }
            onClear={(row) => clear.mutate(row.god.id)}
          />
          <Group title='Set their regard of a god' icon={Plus}>
            <PickRow
              label='God'
              table={gods}
              value={god}
              blocked={busy}
              onPick={setGod}
            />
            <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'>
              {STANDING_AXES.map((axis) => (
                <NumberField
                  key={axis}
                  label={AXIS_LABELS[axis].label}
                  value={draft[axis] ?? ''}
                  min={0}
                  max={100}
                  disabled={busy !== null}
                  onChange={(text) =>
                    setDraft((old) => ({ ...old, [axis]: text }))
                  }
                />
              ))}
            </div>
            <Button
              disabled={busy !== null || problem !== null}
              disabledReason={busy ?? problem ?? undefined}
              onClick={() => {
                save.mutate({ god: Number(god), values, release: [] })
                setDraft({})
              }}
            >
              <Save />
              Hold this regard
            </Button>
          </Group>
        </div>
      )}
    </Section>
  )
}
