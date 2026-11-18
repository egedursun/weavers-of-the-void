import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Anchor,
  CloudRain,
  CloudSun,
  Droplets,
  Hammer,
  Landmark,
  Save,
  Sparkles,
  Trash2,
  Waypoints,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components, weatherKindValues } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { KpiTile, Paged, FieldTile } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import {
  AdjustPanel,
  Card,
  Held,
  Name,
  NumberField,
  SwitchField,
} from '@/features/entity/wilds/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { WEATHER, named } from './labels'

type RegionEnvironment = components['schemas']['RegionEnvironmentView']
type Works = components['schemas']['RegionWorksView']
type SettlementWorks = components['schemas']['SettlementWorks']
type LeyWork = components['schemas']['LeyWorkView']
type LeyLine = components['schemas']['LeyLineView']
type Forced = components['schemas']['ForcedWeatherView']

const WORKING = 'Working on it.'
const WORKS_MAX = 5
const PERCENT = 100
const TIES: { key: 'attuned' | 'on_ley_line' | 'at_nexus'; label: string }[] = [
  { key: 'attuned', label: 'Channels the ley' },
  { key: 'on_ley_line', label: 'Stands on a line' },
  { key: 'at_nexus', label: 'Stands at a nexus' },
]
const WORK_LABELS: Record<string, string> = {
  bridges: 'Bridges',
  irrigation: 'Irrigation works',
  attuned: 'Channels the ley',
  on_ley_line: 'On a line',
  at_nexus: 'At a nexus',
}

function label(key: string) {
  return WORK_LABELS[key] ?? key.replaceAll('_', ' ')
}

function whole(text: string): number | null {
  const value = Number(text)
  return text.trim() !== '' && Number.isInteger(value) ? value : null
}

function SettlementRow({
  item,
  blocked,
}: {
  item: SettlementWorks
  blocked: string | null
}) {
  const [bridges, setBridges] = useState(String(item.bridges))
  const [irrigation, setIrrigation] = useState(String(item.irrigation))
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/settlement:edit', {
          body: {
            settlement_id: item.settlement_id,
            values: {
              bridges: whole(bridges) ?? item.bridges,
              irrigation: whole(irrigation) ?? item.irrigation,
            },
            release: [],
          },
        })
      ),
    success: 'The works are set and held',
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/settlement:edit', {
          body: {
            settlement_id: item.settlement_id,
            values: {},
            release: item.locked,
          },
        })
      ),
    success: 'The settlement builds as it sees fit again',
  })
  const busy = blocked ?? (save.isPending || release.isPending ? WORKING : null)
  const values = [whole(bridges), whole(irrigation)]
  const reason =
    busy ??
    (values.some((value) => value === null || value < 0 || value > WORKS_MAX)
      ? `Works run from 0 to ${WORKS_MAX}.`
      : null) ??
    (values[0] === item.bridges && values[1] === item.irrigation
      ? 'Nothing has changed.'
      : null)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Name item={{ id: item.settlement_id, name: item.name }} />
        {item.harbour && (
          <Badge size='sm' variant='info'>
            Harbour
          </Badge>
        )}
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NumberField
          label='Bridges'
          value={bridges}
          min={0}
          max={WORKS_MAX}
          onChange={setBridges}
        />
        <NumberField
          label='Irrigation works'
          value={irrigation}
          min={0}
          max={WORKS_MAX}
          onChange={setIrrigation}
        />
        <Button
          variant='outline'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => save.mutate()}
        >
          <Save />
          Set and hold
        </Button>
      </div>
      <Held
        keys={item.locked}
        label={label}
        busy={busy}
        onRelease={() => release.mutate()}
      />
    </li>
  )
}

function LeyWorkRow({
  item,
  blocked,
}: {
  item: LeyWork
  blocked: string | null
}) {
  const tie = useGodAction<{ key: string; value: boolean }>({
    run: ({ key, value }) =>
      unwrap(
        api.POST('/api/actions/ley:work', {
          body: {
            structure_id: item.structure_id,
            values: { [key]: value },
            release: [],
          },
        })
      ),
    success: 'The work is tied to the ley anew',
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/ley:work', {
          body: {
            structure_id: item.structure_id,
            values: {},
            release: item.locked,
          },
        })
      ),
    success: 'The land decides the work’s ties again',
  })
  const busy = blocked ?? (tie.isPending || release.isPending ? WORKING : null)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Name item={{ id: item.structure_id, name: item.name }} />
        {item.function !== null && item.function !== undefined && (
          <Badge
            size='sm'
            variant='secondary'
          >{`Function ${item.function}`}</Badge>
        )}
        {item.attuned && item.on_ley_line && (
          <Badge size='sm' variant='success'>
            Drawing power
          </Badge>
        )}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/works:grid-cols-3'>
        {TIES.map((entry) => (
          <SwitchField
            key={entry.key}
            label={entry.label}
            checked={item[entry.key]}
            disabled={busy !== null}
            onChange={(value) => tie.mutate({ key: entry.key, value })}
          />
        ))}
      </div>
      <Held
        keys={item.locked}
        label={label}
        busy={busy}
        onRelease={() => release.mutate()}
      />
    </li>
  )
}

function LeyLineRow({
  line,
  blocked,
}: {
  line: LeyLine
  blocked: string | null
}) {
  const [strength, setStrength] = useState(String(line.strength))
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/ley:strength', {
          body: {
            line_id: line.id,
            strength: whole(strength) ?? line.strength,
          },
        })
      ),
    success: 'The line flows at a new strength, held',
  })
  const dissolve = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/ley:dissolve', { body: { line_id: line.id } })
      ),
    success: 'The ley line is unmade',
  })
  const busy =
    blocked ?? (save.isPending || dissolve.isPending ? WORKING : null)
  const parsed = whole(strength)
  const reason =
    busy ??
    (parsed === null || parsed < 0 || parsed > PERCENT
      ? 'Strength runs from 0 to 100.'
      : null) ??
    (parsed === line.strength ? 'This is the present strength.' : null)
  return (
    <li className='flex min-w-0 flex-wrap items-end gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <Text weight='medium' className='flex-1 basis-32' truncate>
        {`To ${line.other_region_name}`}
      </Text>
      {line.forged && (
        <Badge size='sm' variant='default'>
          Held
        </Badge>
      )}
      <NumberField
        label='Strength'
        value={strength}
        min={0}
        max={PERCENT}
        onChange={setStrength}
      />
      <Button
        variant='outline'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => save.mutate()}
      >
        <Save />
        Set and hold
      </Button>
      <Button
        variant='ghost'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => dissolve.mutate()}
      >
        <Trash2 />
        Unmake
      </Button>
    </li>
  )
}

function ForcedRow({
  item,
  blocked,
}: {
  item: Forced
  blocked: string | null
}) {
  const [kind, setKind] = useState<string>(item.kind)
  const [until, setUntil] = useState(String(item.until_epoch))
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/weather:edit', {
          body: {
            forced_id: item.id,
            kind: kind as Forced['kind'],
            until_epoch: whole(until) ?? item.until_epoch,
            every_season: false,
          },
        })
      ),
    success: 'The held weather was changed',
  })
  const parsed = whole(until)
  const reason =
    blocked ??
    (parsed === null || parsed < item.from_epoch
      ? `It cannot end before epoch ${item.from_epoch}.`
      : null) ??
    (kind === item.kind && parsed === item.until_epoch
      ? 'Nothing has changed.'
      : null) ??
    (save.isPending ? WORKING : null)
  return (
    <li className='flex min-w-0 flex-wrap items-end gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <FieldTile label='Weather'>
        <Select value={kind} onValueChange={setKind}>
          <SelectTrigger aria-label='Held weather'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {weatherKindValues.map((value) => (
              <SelectItem key={value} value={value}>
                {named(WEATHER, value).label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FieldTile>
      <NumberField
        label='Until epoch'
        value={until}
        min={item.from_epoch}
        onChange={setUntil}
      />
      <Button
        variant='outline'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => save.mutate()}
      >
        <Save />
        Change
      </Button>
    </li>
  )
}

function Summary({ works }: { works: Works }) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @md/works:grid-cols-2 @2xl/works:grid-cols-4'>
      <KpiTile
        label='Bridges'
        value={String(works.bridges)}
        icon={Landmark}
        tone='gold'
        hint='Each eases the river crossing for traders and armies'
      />
      <KpiTile
        label='Irrigation'
        value={`+${works.irrigation_pct}%`}
        icon={Droplets}
        tone='success'
        hint={`${plural(works.irrigation, 'level', 'levels')} of works carry the river to the fields`}
      />
      <KpiTile
        label='Harbours'
        value={String(works.harbours)}
        icon={Anchor}
        tone='info'
        hint='Harbour districts make the water a road'
      />
      <KpiTile
        label='Rain lost to clearing'
        value={`−${works.rain_lost_to_clearing}`}
        icon={CloudRain}
        tone={works.rain_lost_to_clearing > 0 ? 'warning' : 'muted'}
        hint={`${works.cleared}% of the forest is cleared; rainfall stands at ${works.rainfall}`}
      />
    </div>
  )
}

export function RegionWorksPanel({
  regionId,
  ground,
}: {
  regionId: number
  ground: RegionEnvironment
}) {
  const { reason } = useGodGate()
  const blocked = reason()
  const query = useQuery({
    queryKey: ['region', regionId, 'works'],
    queryFn: () =>
      unwrap(
        api.GET('/api/regions/{region_id}/works', {
          params: { path: { region_id: regionId } },
        })
      ),
    retry: false,
  })
  const works = query.data
  if (!works) return null
  return (
    <div
      data-surface='RegionWorksPanel'
      className='@container/works flex min-w-0 flex-col gap-3'
    >
      <Card
        title='Works on the land'
        icon={Hammer}
        tone='gold'
        hint='Bridges, irrigation and harbours are built by settlements and change what the land gives'
      >
        <Summary works={works} />
      </Card>
      <div className='grid min-w-0 grid-cols-1 gap-3 @2xl/works:grid-cols-2'>
        <Card title='Settlements and their works' icon={Landmark}>
          {works.settlements.length === 0 ? (
            <Muted>No settlement stands in this land.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-col gap-2'>
              <Paged items={works.settlements} as='li'>
                {(item) => (
                  <SettlementRow
                    key={`${item.settlement_id}-${item.bridges}-${item.irrigation}`}
                    item={item}
                    blocked={blocked}
                  />
                )}
              </Paged>
            </ul>
          )}
        </Card>
        <Card title='Works and the ley' icon={Sparkles} tone='verdigris'>
          {works.ley_works.length === 0 ? (
            <Muted>No structure stands in this land.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-col gap-2'>
              <Paged items={works.ley_works} as='li'>
                {(item) => (
                  <LeyWorkRow
                    key={item.structure_id}
                    item={item}
                    blocked={blocked}
                  />
                )}
              </Paged>
            </ul>
          )}
        </Card>
      </div>
      <AdjustPanel
        title='Reshape ley lines and held weather'
        note='Set a ley line’s strength (it is then held), unmake any line, or change the kind and end of weather held over this land. Every change can be undone from the ledger.'
        label='Lines and weather'
      >
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Ley lines</Label>
          {ground.ley_lines.length === 0 ? (
            <Muted>No ley line runs through this land.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-col gap-2'>
              <Paged items={ground.ley_lines} as='li'>
                {(line) => (
                  <LeyLineRow
                    key={`${line.id}-${line.strength}`}
                    line={line}
                    blocked={blocked}
                  />
                )}
              </Paged>
            </ul>
          )}
        </div>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Held weather</Label>
          {ground.forced_weather.length === 0 ? (
            <Muted>No weather is held over this land.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-col gap-2'>
              <Paged items={ground.forced_weather} as='li'>
                {(item) => (
                  <ForcedRow
                    key={`${item.id}-${item.kind}-${item.until_epoch}`}
                    item={item}
                    blocked={blocked}
                  />
                )}
              </Paged>
            </ul>
          )}
        </div>
      </AdjustPanel>
      <div className='flex min-w-0 items-center gap-2'>
        <CloudSun aria-hidden='true' className='size-icon-xs shrink-0' />
        <Waypoints aria-hidden='true' className='size-icon-xs shrink-0' />
        <Muted variant='caption'>
          Wind spreads the fires of a settlement; wet years put them out and
          weaken fire rites.
        </Muted>
      </div>
    </div>
  )
}
