import { useMemo, useState } from 'react'
import {
  Anchor,
  Church,
  Flame,
  Link2Off,
  Lock,
  Save,
  Swords,
  TriangleAlert,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Section,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { Adjust, Panel } from '@/features/wars/military/parts'
import { type Anchorage, useAnchorage } from './api'
import { battles } from './labels'
import { HoldToggle } from './parts'

function endingText(war: Anchorage['incited'][number]): string {
  if (war.ending === null || war.ending === undefined)
    return `Still burning · ${battles(war.battles)}`
  return `Ended in age ${war.ended_epoch} · ${war.ending.replaceAll('_', ' ')} · ${battles(war.battles)}`
}

function AnchorControls({
  view,
  name,
  blocked,
}: {
  view: Anchorage
  name: string
  blocked: string | null
}) {
  const options = useMemo(
    () => [
      ...view.shrines.map((item) => ({
        value: String(item.id),
        label: item.name,
        hint: 'Dedicated to them',
      })),
      ...view.creations.map((item) => ({
        value: String(item.id),
        label: item.name,
        hint: 'Their own creation',
      })),
    ],
    [view]
  )
  const [choice, setChoice] = useState<string | null>(
    view.anchor ? String(view.anchor.id) : null
  )
  const [hold, setHold] = useState(true)
  const anchor = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/son:anchor', {
          body: { son_id: view.son_id, entity_id: Number(choice), hold },
        })
      ),
  })
  const clear = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/son:clear_anchor', {
          body: { son_id: view.son_id },
        })
      ),
  })
  const busy =
    blocked ?? (anchor.isPending || clear.isPending ? 'Working…' : null)
  return (
    <Adjust
      label='Move the anchor'
      title={`${name}'s anchor`}
      note='An anchor can be one of their own creations or a structure mortals dedicated to them. Held, the god cannot move it themselves.'
    >
      <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-3'>
        <div className='min-w-0 sm:col-span-2'>
          <RecordCombobox
            options={options}
            value={choice}
            onChange={(value) => setChoice(value)}
            placeholder='Choose a creation or shrine'
            aria-label='Anchor'
            disabled={busy !== null}
          />
        </div>
        <label className='flex min-w-0 items-center gap-2 rounded-lg border bg-background p-2.5'>
          <Switch
            checked={hold}
            onCheckedChange={setHold}
            aria-label='Hold the anchor'
          />
          <Text as='span'>Hold it</Text>
        </label>
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          disabled={busy !== null || choice === null}
          disabledReason={busy ?? (choice === null ? 'Choose one' : undefined)}
          onClick={() => anchor.mutate(undefined)}
        >
          <Save />
          Anchor here
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || view.anchor === null}
          disabledReason={busy ?? (view.anchor ? undefined : 'No anchor')}
          onClick={() => clear.mutate(undefined)}
        >
          <Link2Off />
          Cut the anchor
        </Button>
      </div>
      <HoldToggle
        kind='anchor_entity_id'
        nodeId={view.son_id}
        held={view.anchor_held}
        blocked={blocked}
        what='the anchor'
      />
    </Adjust>
  )
}

export function AnchorageSection({
  sonId,
  name,
}: {
  sonId: number
  name: string
}) {
  const view = useAnchorage(sonId)
  const { reason } = useGodGate()
  const blocked = reason()
  const data = view.data
  return (
    <Section
      id='section-anchorage'
      title='Anchor, shrines and wars'
      description='What holds this god in being, the works raised in their name and the wars they set off.'
      icon={Anchor}
    >
      {view.isPending && <Muted>Reading the anchor…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The anchor could not be read'
          description={view.error.message}
        />
      )}
      {data && (
        <div
          data-surface='SonAnchorage'
          className='flex min-w-0 flex-col gap-4'
        >
          <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
            <KpiTile
              label='Anchor'
              value={data.anchor ? data.anchor.name : 'None'}
              icon={Anchor}
              tone={
                data.anchor === null
                  ? 'muted'
                  : data.anchor_alive
                    ? 'success'
                    : 'danger'
              }
              hint={
                data.anchor === null
                  ? 'Nothing holds them in being'
                  : data.anchor_alive
                    ? 'While it stands, their existence stays firm'
                    : 'It has perished: they are fading'
              }
            />
            <KpiTile
              label='Shrines'
              value={data.shrines.length}
              icon={Church}
              tone='gold'
              hint='Each brings fame and existence every age'
            />
            <KpiTile
              label='Wars incited'
              value={data.incited.length}
              icon={Flame}
              tone={data.incited.length > 0 ? 'danger' : 'muted'}
              hint='Fame from their battles, hatred from their losers'
            />
          </div>
          {data.anchor_held && (
            <Badge size='sm' variant='outline' className='self-start'>
              <Lock aria-hidden='true' />
              The anchor is held
            </Badge>
          )}
          {data.shrines.length > 0 && (
            <Panel
              title='Dedicated to them'
              icon={Church}
              count={data.shrines.length}
              hint='Any of these can anchor them'
            >
              <ul className='flex min-w-0 flex-wrap gap-2'>
                {data.shrines.map((item) => (
                  <li key={item.id}>
                    <Badge size='default' variant='secondary'>
                      <Church aria-hidden='true' />
                      <EntityLink kind='entity' id={String(item.id)}>
                        {item.name}
                      </EntityLink>
                    </Badge>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
          {data.incited.length > 0 && (
            <Panel
              title='Wars they set off'
              icon={Swords}
              tone='danger'
              count={data.incited.length}
            >
              <ul className='flex min-w-0 flex-col gap-2'>
                {data.incited.map((war) => (
                  <li
                    key={war.war_id}
                    className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-2.5'
                  >
                    <Medallion
                      icon={war.ending ? Swords : Flame}
                      tone={war.ending ? 'muted' : 'danger'}
                      size='sm'
                    />
                    <div className='flex min-w-0 flex-1 flex-col'>
                      {war.event ? (
                        <EntityLink kind='entity' id={String(war.event.id)}>
                          {war.event.name}
                        </EntityLink>
                      ) : (
                        <Text>War #{war.war_id}</Text>
                      )}
                      <Muted variant='caption' truncate>
                        {`Begun in age ${war.started_epoch} · ${endingText(war)}`}
                      </Muted>
                    </div>
                    {war.held && (
                      <Badge size='sm' variant='outline'>
                        <Lock aria-hidden='true' />
                        Held
                      </Badge>
                    )}
                  </li>
                ))}
              </ul>
            </Panel>
          )}
          <AnchorControls view={data} name={name} blocked={blocked} />
        </div>
      )}
    </Section>
  )
}
