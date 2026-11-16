import { useState } from 'react'
import {
  Factory,
  Flag,
  Gauge,
  Scale,
  Target,
  TriangleAlert,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  Medallion,
  Paged,
  StatBar,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import { EntityPicker, Held, RecordButtons } from './controls'
import { type RecordRow, useRecords } from './depth'
import {
  CASUS_BELLI,
  PERCENT,
  WAR_GOODS,
  busyOf,
  cardGrid,
  named,
} from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  NumberField,
  Panel,
  Plain,
  Tag,
  ToggleField,
} from './parts'
import {
  type Values,
  numbersOf,
  useRecordActions,
  useRecordCreate,
} from './recordHooks'

const WARRING = ['people', 'settlement', 'faction', 'cult', 'polity']
const CAUSE_NUMBERS = ['justification', 'expires_epoch'] as const
const LINE_NUMBERS = ['efficiency'] as const
const USED = { label: 'Pressed in a war', icon: Flag, tone: 'muted' as const }
const CONVERTED = {
  label: 'Turned to war production',
  icon: Factory,
  tone: 'warning' as const,
}

function nameOf(
  names: { id: number; name: string }[] | undefined,
  id: unknown
) {
  return names?.find((entry) => entry.id === Number(id))?.name ?? 'Someone'
}

function CauseCard({
  row,
  holderId,
  blocked,
}: {
  row: RecordRow
  holderId: number
  blocked: string | null
}) {
  const actions = useRecordActions('casus_belli', row.id, holderId)
  const names = useNames()
  const [draft, setDraft] = useState<Values>({})
  const value = (key: string) => (key in draft ? draft[key] : row.values[key])
  const kind = named(CASUS_BELLI, String(row.values.kind))
  const used =
    row.values.used_war_id !== null && row.values.used_war_id !== undefined
  const justification = Number(row.values.justification ?? 0)
  return (
    <li
      data-surface='CasusBelliCard'
      className='@container/mil flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion
          icon={kind.icon}
          tone={used ? 'muted' : (kind.tone ?? 'gold')}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text as='span' weight='semibold' truncate>
            {kind.label}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {'Against '}
            <EntityLink kind='entity' id={String(row.values.target_entity_id)}>
              {nameOf(names.data, row.values.target_entity_id)}
            </EntityLink>
            {` · since epoch ${String(row.values.since_epoch)}`}
          </Muted>
        </div>
        <Held locked={row.locked} />
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Tag item={kind} />
        {used && <Tag item={USED} />}
        {row.values.expires_epoch !== null &&
          row.values.expires_epoch !== undefined &&
          !used && (
            <Plain
              icon={TriangleAlert}
            >{`Lapses after epoch ${String(row.values.expires_epoch)}`}</Plain>
          )}
      </div>
      <StatBar
        label='Justification'
        icon={Scale}
        value={justification}
        max={PERCENT}
        tone={justification >= 50 ? 'success' : 'warning'}
      />
      <Adjust
        title='Reshape the grievance'
        note='Its kind, target, how just it has grown and when it lapses; held values stay as set.'
      >
        <FieldGrid>
          <ChoiceField
            label='Kind'
            icon={Flag}
            value={String(value('kind') ?? 'claim')}
            table={CASUS_BELLI}
            blocked={blocked}
            onPick={(next) => setDraft({ ...draft, kind: next })}
          />
          <EntityPicker
            label='Against'
            icon={Target}
            types={WARRING}
            value={Number(value('target_entity_id')) || null}
            onChange={(next) => setDraft({ ...draft, target_entity_id: next })}
            blocked={blocked}
          />
          <NumberField
            label='Justification'
            icon={Scale}
            value={String(value('justification') ?? 0)}
            max={PERCENT}
            onChange={(next) => setDraft({ ...draft, justification: next })}
          />
          <NumberField
            label='Lapses after epoch'
            icon={TriangleAlert}
            value={String(value('expires_epoch') ?? '')}
            onChange={(next) => setDraft({ ...draft, expires_epoch: next })}
          />
        </FieldGrid>
        <RecordButtons
          actions={actions}
          values={numbersOf(draft, CAUSE_NUMBERS)}
          locked={row.locked}
          blocked={blocked}
          removeLabel='Drop the grievance'
        />
      </Adjust>
    </li>
  )
}

function NewCause({
  holderId,
  blocked,
}: {
  holderId: number
  blocked: string | null
}) {
  const create = useRecordCreate('casus_belli', holderId)
  const [target, setTarget] = useState<number | null>(null)
  const [kind, setKind] = useState('claim')
  const busy = busyOf(blocked, create.isPending)
  const why =
    busy ??
    (target === null
      ? 'Choose whom it is held against'
      : target === holderId
        ? 'A grievance needs another side'
        : undefined)
  return (
    <Adjust
      title='Grant a grievance'
      note='A casus belli this side holds against another; it grows more just each epoch until it is pressed in a war or lapses.'
      label='Grant a casus belli'
    >
      <FieldGrid>
        <EntityPicker
          label='Against'
          icon={Target}
          types={WARRING}
          value={target}
          onChange={setTarget}
          blocked={blocked}
        />
        <ChoiceField
          label='Kind'
          icon={Flag}
          value={kind}
          table={CASUS_BELLI}
          blocked={blocked}
          onPick={setKind}
        />
      </FieldGrid>
      <Button
        size='sm'
        className='self-start'
        disabled={why !== undefined}
        disabledReason={why}
        onClick={() =>
          create.mutate({
            holder_entity_id: holderId,
            target_entity_id: target,
            kind,
          })
        }
      >
        <Flag />
        Grant
      </Button>
    </Adjust>
  )
}

export function CasusBelli({
  holderId,
  blocked,
}: {
  holderId: number
  blocked: string | null
}) {
  const causes = useRecords('casus_belli', holderId)
  const rows = causes.data?.rows ?? []
  return (
    <Panel
      title='Casus belli'
      icon={Flag}
      tone='danger'
      count={rows.length}
      hint='Grievances it holds against others; a war on a ripe one counts as justified'
    >
      <div data-surface='CasusBelli' className='flex min-w-0 flex-col gap-3'>
        {causes.isPending ? (
          <Muted variant='caption'>Gathering its grievances…</Muted>
        ) : causes.isError ? (
          <EmptyState
            icon={TriangleAlert}
            title='The grievances could not be read'
            description='Try again in a moment.'
          />
        ) : rows.length === 0 ? (
          <EmptyState
            icon={Flag}
            title='No grievances'
            description='A war it starts now would be one of conquest, and unjustified.'
          />
        ) : (
          <ul className={cardGrid(rows.length)}>
            <Paged items={rows} as='li'>
              {(row) => (
                <CauseCard
                  key={row.id}
                  row={row}
                  holderId={holderId}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        )}
        <NewCause holderId={holderId} blocked={blocked} />
      </div>
    </Panel>
  )
}

function LineEditor({
  row,
  communityId,
  blocked,
}: {
  row: RecordRow
  communityId: number
  blocked: string | null
}) {
  const actions = useRecordActions('war_production', row.id, communityId)
  const [draft, setDraft] = useState<Values>({})
  const value = (key: string) => (key in draft ? draft[key] : row.values[key])
  const good = named(WAR_GOODS, String(row.values.commodity))
  const converted = Boolean(row.values.converted)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion
          icon={good.icon}
          tone={converted ? (good.tone ?? 'gold') : 'muted'}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text as='span' weight='semibold' truncate>
            {good.label}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {converted
              ? `Made for the war since epoch ${String(row.values.since_epoch)}`
              : 'Workshops back at peace work'}
          </Muted>
        </div>
        <Held locked={row.locked} />
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        {converted && <Tag item={CONVERTED} />}
      </div>
      <StatBar
        label='Efficiency'
        icon={Gauge}
        value={Number(row.values.efficiency ?? 0)}
        max={PERCENT}
        tone='info'
      />
      <Adjust
        title='Direct the workshops'
        note='What its workshops make for the war, how practised they are at it and whether civilian goods are given up for it.'
      >
        <FieldGrid>
          <ChoiceField
            label='War good'
            icon={Factory}
            value={String(value('commodity') ?? 'weapons')}
            table={WAR_GOODS}
            blocked={blocked}
            onPick={(next) => setDraft({ ...draft, commodity: next })}
          />
          <NumberField
            label='Efficiency'
            icon={Gauge}
            value={String(value('efficiency') ?? 0)}
            onChange={(next) => setDraft({ ...draft, efficiency: next })}
          />
          <ToggleField
            item={CONVERTED}
            checked={Boolean(value('converted'))}
            disabled={blocked !== null}
            onChange={(next) => setDraft({ ...draft, converted: next })}
          />
        </FieldGrid>
        <RecordButtons
          actions={actions}
          values={numbersOf(draft, LINE_NUMBERS)}
          locked={row.locked}
          blocked={blocked}
          removeLabel='Close the line'
        />
      </Adjust>
    </div>
  )
}

export function WarProduction({
  communityId,
  blocked,
}: {
  communityId: number
  blocked: string | null
}) {
  const lines = useRecords('war_production', communityId)
  const create = useRecordCreate('war_production', communityId)
  const [good, setGood] = useState('weapons')
  const row = lines.data?.rows[0]
  const busy = busyOf(blocked, create.isPending)
  return (
    <Panel
      title='War production'
      icon={Factory}
      tone='warning'
      hint='At war its workshops turn to their scarcest war good and grow more practised each epoch'
    >
      <div data-surface='WarProduction' className='flex min-w-0 flex-col gap-3'>
        {lines.isPending ? (
          <Muted variant='caption'>Reading the workshops…</Muted>
        ) : lines.isError ? (
          <EmptyState
            icon={TriangleAlert}
            title='The workshops could not be read'
            description='Try again in a moment.'
          />
        ) : row ? (
          <LineEditor row={row} communityId={communityId} blocked={blocked} />
        ) : (
          <>
            <EmptyState
              icon={Factory}
              title='No war production'
              description='Its workshops make what peace needs; at war they turn to arms on their own.'
            />
            <Adjust
              title='Turn the workshops to war'
              note='Choose the war good; civilian goods are made less while the line runs.'
              label='Open a war line'
            >
              <FieldGrid>
                <ChoiceField
                  label='War good'
                  icon={Factory}
                  value={good}
                  table={WAR_GOODS}
                  blocked={blocked}
                  onPick={setGood}
                />
              </FieldGrid>
              <Button
                size='sm'
                className='self-start'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() =>
                  create.mutate({
                    community_entity_id: communityId,
                    commodity: good,
                    converted: true,
                  })
                }
              >
                <Factory />
                Open the line
              </Button>
            </Adjust>
          </>
        )}
      </div>
    </Panel>
  )
}
