import { useState } from 'react'
import {
  Award,
  BookMarked,
  CircleCheck,
  FileText,
  Hourglass,
  Microscope,
  Plus,
  Skull,
  Sparkles,
  Trash2,
  TriangleAlert,
  Users,
} from 'lucide-react'
import { type ActionBody } from '@/api/actions'
import { greatFieldValues } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Medallion, Paged, PagedList, FieldTile } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import {
  AdjustBlock,
  ChoicePicker,
  LoreCard,
  RefChip,
  RowEditor,
  RowEditors,
  Who,
} from './LoreFields'
import { type LearningCard } from './api'
import { BLUEPRINT_LOOK, GREAT_FIELDS, INCIDENT_KINDS } from './discoveryLabels'
import { type LoreNamed, PERCENT, busyOf } from './model'
import { useLoreAction } from './panels/controlParts'

type Key = Record<string, string | number>
const GRID = 'grid min-w-0 grid-cols-1 gap-2 @md/lore:grid-cols-2'
const TILE =
  'flex h-full min-w-0 flex-col gap-2 rounded-md border p-3 @md/lore:last:odd:col-span-2 border-gild/70 bg-card surface-framed'

function useRowEdit() {
  return useLoreAction(
    'record_row:edit',
    (value: {
      table: string
      key: Key
      values: Record<string, number | string | boolean>
      hold: boolean
    }) => value
  )
}

function useRowCreate() {
  return useLoreAction(
    'record_row:create',
    (value: {
      table: string
      values: Record<string, number | string | boolean | number[]>
    }) => value
  )
}

function useRowRemove() {
  return useLoreAction(
    'record_row:delete',
    (value: { table: string; key: Key }) => value
  )
}

function Remove({
  label,
  busy,
  onRemove,
}: {
  label: string
  busy: string | null
  onRemove: () => void
}) {
  return (
    <Button
      size='sm'
      variant='ghost'
      className='ml-auto'
      disabled={busy !== null}
      disabledReason={busy ?? undefined}
      onClick={onRemove}
    >
      <Trash2 />
      {label}
    </Button>
  )
}

function FieldMeter({
  card,
  field,
  look,
  blocked,
}: {
  card: LearningCard
  field: string
  look: LoreNamed
  blocked: string | null
}) {
  const row = card.great_points.find((item) => item.field === field)
  const edit = useRowEdit()
  const create = useRowCreate()
  const busy = busyOf(blocked, edit.isPending, create.isPending)
  const points = row?.points ?? 0
  const threshold = row?.threshold ?? card.great_points[0]?.threshold ?? 0
  const share =
    threshold > 0 ? Math.min(PERCENT, (points / threshold) * PERCENT) : 0
  return (
    <li
      className={cn(
        TILE,
        share >= PERCENT ? 'border-primary/50' : 'bg-muted/20'
      )}
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={look.icon} tone={look.tone} size='sm' />
        <Text as='span' weight='semibold' className='min-w-0 flex-1' truncate>
          {look.label}
        </Text>
        {row && row.locked.length > 0 && (
          <Badge size='sm' variant='secondary'>
            Held
          </Badge>
        )}
      </div>
      <Progress value={share} size='sm' aria-label={`${look.label} points`} />
      <Muted variant='caption'>
        {threshold > 0
          ? `${points} of ${plural(threshold, 'point', 'points')} toward the next one`
          : `${plural(points, 'point', 'points')} gathered`}
      </Muted>
      <RowEditor
        label='Points'
        value={points}
        blocked={busy}
        onSave={(next) =>
          row
            ? edit.mutate({
                table: 'great_person_points',
                key: { holder_entity_id: card.holder_id, field },
                values: { points: next },
                hold: true,
              })
            : create.mutate({
                table: 'great_person_points',
                values: {
                  holder_entity_id: card.holder_id,
                  field,
                  points: next,
                  updated_epoch: 0,
                },
              })
        }
      />
    </li>
  )
}

function GreatPeopleCard({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  const raise = useLoreAction(
    'discovery:raise_great',
    (value: { mortal: number; field: string }) => ({
      mortal_id: value.mortal,
      field: value.field as ActionBody<'discovery:raise_great'>['field'],
      deed: true,
    })
  )
  const remove = useRowRemove()
  const [mortal, setMortal] = useState<number | null>(null)
  const [field, setField] = useState('')
  const busy = busyOf(blocked, raise.isPending, remove.isPending)
  return (
    <LoreCard
      title='Great people'
      icon={Award}
      tone='gold'
      aside={<Badge variant='secondary'>{card.great_people.length}</Badge>}
    >
      <div data-surface='GreatPeople' className='flex min-w-0 flex-col gap-3'>
        <ul className={GRID}>
          {greatFieldValues.map((key) => (
            <FieldMeter
              key={key}
              card={card}
              field={key}
              look={GREAT_FIELDS[key]}
              blocked={blocked}
            />
          ))}
        </ul>
        {card.great_people.length === 0 ? (
          <Muted>
            No great person has risen here yet. Skill and working schools,
            temples, forts, markets and harbours gather points in each field.
          </Muted>
        ) : (
          <ul className={GRID}>
            <Paged items={card.great_people} as='li'>
              {(row) => {
                const look = GREAT_FIELDS[row.field]
                return (
                  <li
                    key={row.mortal.id}
                    className={cn(TILE, 'border-primary/40 bg-primary/5')}
                  >
                    <div className='flex min-w-0 items-start gap-2.5'>
                      <Medallion icon={look.icon} tone={look.tone} size='sm' />
                      <div className='flex min-w-0 flex-1 flex-col'>
                        <Who item={row.mortal} />
                        <Muted variant='caption'>{`${row.label}, risen in epoch ${row.promoted_epoch}`}</Muted>
                      </div>
                      <Badge
                        size='sm'
                        variant={row.deed_done ? 'default' : 'outline'}
                      >
                        {row.deed_done ? <CircleCheck /> : <Hourglass />}
                        {row.deed_done
                          ? row.deed_epoch !== null
                            ? `Deed done in epoch ${row.deed_epoch}`
                            : 'Deed done'
                          : 'Deed waits'}
                      </Badge>
                    </div>
                    <Muted variant='caption'>{`Their deed: ${row.deed}.`}</Muted>
                    <Remove
                      label='Strike from the roll'
                      busy={busy}
                      onRemove={() =>
                        remove.mutate({
                          table: 'great_people',
                          key: { mortal_entity_id: row.mortal.id },
                        })
                      }
                    />
                  </li>
                )
              }}
            </Paged>
          </ul>
        )}
        <AdjustBlock title='Raise a great person' icon={Sparkles}>
          <div className='grid min-w-0 grid-cols-1 gap-2 @md/lore:grid-cols-2'>
            <div className='flex min-w-0 flex-col gap-1'>
              <Label>Mortal</Label>
              <EntityPicker
                types={['mortal']}
                value={mortal}
                onChange={setMortal}
                placeholder='Choose a mortal'
              />
            </div>
            <ChoicePicker
              label='Field'
              value={field}
              table={GREAT_FIELDS}
              blocked={busy}
              placeholder='Choose'
              onPick={setField}
            />
          </div>
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== null || mortal === null || field === ''}
            disabledReason={
              busy ??
              (mortal === null
                ? 'Choose a mortal'
                : field === ''
                  ? 'Choose a field'
                  : undefined)
            }
            onClick={() => mortal !== null && raise.mutate({ mortal, field })}
          >
            <Award />
            Raise them
          </Button>
        </AdjustBlock>
      </div>
    </LoreCard>
  )
}

function IncidentsCard({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  const strike = useLoreAction(
    'discovery:incident',
    (value: { kind: string }) => ({
      holder_id: card.holder_id,
      kind: value.kind as ActionBody<'discovery:incident'>['kind'],
    })
  )
  const remove = useRowRemove()
  const [kind, setKind] = useState('')
  const busy = busyOf(blocked, strike.isPending, remove.isPending)
  const dead = card.incidents.reduce((sum, row) => sum + row.dead, 0)
  return (
    <LoreCard
      title='Mishaps of research'
      icon={TriangleAlert}
      tone='danger'
      aside={
        <Badge variant={dead > 0 ? 'destructive' : 'secondary'}>
          <Skull aria-hidden='true' />
          {`${dead} dead`}
        </Badge>
      }
    >
      <div
        data-surface='ResearchIncidents'
        className='flex min-w-0 flex-col gap-3'
      >
        {card.incidents.length === 0 ? (
          <Muted>
            No mishap yet. Dangerous arts and risky work in magic, metals,
            building and medicine can bring fires, explosions, poisonings, loose
            beasts and sicknesses.
          </Muted>
        ) : (
          <ul className={GRID}>
            <Paged items={card.incidents} as='li'>
              {(row) => {
                const look = INCIDENT_KINDS[row.kind]
                return (
                  <li
                    key={row.id}
                    className={cn(TILE, 'border-destructive/30')}
                  >
                    <div className='flex min-w-0 items-start gap-2.5'>
                      <Medallion icon={look.icon} tone={look.tone} size='sm' />
                      <div className='flex min-w-0 flex-1 flex-col'>
                        <Text as='span' weight='semibold'>
                          {row.label}
                        </Text>
                        <Muted variant='caption'>{`Epoch ${row.epoch}${row.dead ? `, ${row.dead} dead` : ''}`}</Muted>
                      </div>
                    </div>
                    <Progress
                      value={row.severity}
                      size='sm'
                      aria-label='Severity'
                    />
                    <Remove
                      label='Strike from the record'
                      busy={busy}
                      onRemove={() =>
                        remove.mutate({
                          table: 'research_incidents',
                          key: { id: row.id },
                        })
                      }
                    />
                  </li>
                )
              }}
            </Paged>
          </ul>
        )}
        <AdjustBlock title='Strike with a mishap' icon={TriangleAlert}>
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <div className='min-w-0 flex-1 basis-48'>
              <ChoicePicker
                label='Mishap'
                value={kind}
                table={INCIDENT_KINDS}
                blocked={busy}
                placeholder='Choose'
                onPick={setKind}
              />
            </div>
            <Button
              size='sm'
              variant='destructive'
              disabled={busy !== null || kind === ''}
              disabledReason={
                busy ?? (kind === '' ? 'Choose a mishap' : undefined)
              }
              onClick={() => strike.mutate({ kind })}
            >
              <TriangleAlert />
              Strike
            </Button>
          </div>
        </AdjustBlock>
      </div>
    </LoreCard>
  )
}

function StudiesCard({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  const edit = useRowEdit()
  const remove = useRowRemove()
  const busy = busyOf(blocked, edit.isPending, remove.isPending)
  const label = (technique: string) =>
    card.techniques.find((row) => row.technique === technique)?.label ??
    technique
  return (
    <LoreCard
      title='Things taken apart'
      icon={Microscope}
      tone='info'
      aside={<Badge variant='secondary'>{card.studies.length}</Badge>}
    >
      <div
        data-surface='ArtifactStudies'
        className='flex min-w-0 flex-col gap-3'
      >
        {card.studies.length === 0 ? (
          <Muted>
            Their scholars study nothing yet. Made things they own whose secret
            they lack are taken apart until the technique is learned.
          </Muted>
        ) : (
          <ul className={GRID}>
            <Paged items={card.studies} as='li'>
              {(row) => (
                <li key={row.item.id} className={cn(TILE, 'bg-muted/20')}>
                  <div className='flex min-w-0 items-center gap-2'>
                    <RefChip icon={BookMarked} label='' item={row.item} />
                    <Badge size='sm' variant='outline'>
                      {label(row.technique)}
                    </Badge>
                  </div>
                  <Progress
                    value={row.progress}
                    size='sm'
                    aria-label='Study progress'
                  />
                  <RowEditors>
                    <RowEditor
                      label='Progress'
                      value={row.progress}
                      max={PERCENT}
                      blocked={busy}
                      onSave={(next) =>
                        edit.mutate({
                          table: 'artifact_studies',
                          key: {
                            holder_entity_id: card.holder_id,
                            item_entity_id: row.item.id,
                          },
                          values: { progress: next },
                          hold: true,
                        })
                      }
                    />
                  </RowEditors>
                  <Remove
                    label='Stop the study'
                    busy={busy}
                    onRemove={() =>
                      remove.mutate({
                        table: 'artifact_studies',
                        key: {
                          holder_entity_id: card.holder_id,
                          item_entity_id: row.item.id,
                        },
                      })
                    }
                  />
                </li>
              )}
            </Paged>
          </ul>
        )}
      </div>
    </LoreCard>
  )
}

function BlueprintsCard({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  const grant = useLoreAction(
    'discovery:design',
    (value: { kind: string; subject: string; quality: number }) => ({
      holder_id: card.holder_id,
      kind: value.kind as ActionBody<'discovery:design'>['kind'],
      subject: value.subject,
      quality: value.quality,
    })
  )
  const edit = useRowEdit()
  const remove = useRowRemove()
  const [kind, setKind] = useState('')
  const [subject, setSubject] = useState('')
  const [quality, setQuality] = useState('60')
  const busy = busyOf(
    blocked,
    grant.isPending,
    edit.isPending,
    remove.isPending
  )
  const level = Math.round(Number(quality))
  const problem =
    kind === ''
      ? 'Choose a kind of design'
      : subject.trim() === ''
        ? 'Name what it is a design of'
        : Number.isNaN(level) || level < 0 || level > PERCENT
          ? `Quality runs from 0 to ${PERCENT}`
          : null
  return (
    <LoreCard
      title='Designs'
      icon={FileText}
      tone='verdigris'
      aside={<Badge variant='secondary'>{card.designs.length}</Badge>}
    >
      <div data-surface='Blueprints' className='flex min-w-0 flex-col gap-3'>
        {card.designs.length === 0 ? (
          <Muted>
            They hold no designs. Finished buildings, ships, siege engines and
            fine crafted things leave a design behind; designs are sold,
            licensed by associations and stolen by spies.
          </Muted>
        ) : (
          <ul className={GRID}>
            <Paged items={card.designs} as='li'>
              {(row) => {
                const look = BLUEPRINT_LOOK[row.kind]
                return (
                  <li key={row.id} className={cn(TILE, 'bg-muted/20')}>
                    <div className='flex min-w-0 items-start gap-2.5'>
                      <Medallion icon={look.icon} tone={look.tone} size='sm' />
                      <div className='flex min-w-0 flex-1 flex-col'>
                        <Text as='span' weight='semibold'>
                          {row.name}
                        </Text>
                        <Muted variant='caption'>{`${row.source_label}, since epoch ${row.since_epoch}`}</Muted>
                      </div>
                    </div>
                    {row.licensed_to.length > 0 && (
                      <PagedList
                        items={row.licensed_to}
                        initial={12}
                        noun={['entry', 'entries']}
                        as='div'
                        className='flex min-w-0 flex-wrap gap-1.5'
                        itemKey={(item) => item.id}
                      >
                        {(item) => (
                          <RefChip
                            key={item.id}
                            icon={Users}
                            label='Licensed'
                            item={item}
                          />
                        )}
                      </PagedList>
                    )}
                    <RowEditor
                      label='Quality'
                      value={row.quality}
                      max={PERCENT}
                      blocked={busy}
                      onSave={(next) =>
                        edit.mutate({
                          table: 'blueprints',
                          key: { id: row.id },
                          values: { quality: next },
                          hold: true,
                        })
                      }
                    />
                    <Remove
                      label='Burn the design'
                      busy={busy}
                      onRemove={() =>
                        remove.mutate({
                          table: 'blueprints',
                          key: { id: row.id },
                        })
                      }
                    />
                  </li>
                )
              }}
            </Paged>
          </ul>
        )}
        <AdjustBlock title='Grant a design' icon={Plus}>
          <div className='grid min-w-0 grid-cols-1 gap-2 @md/lore:grid-cols-3'>
            <ChoicePicker
              label='Kind'
              value={kind}
              table={BLUEPRINT_LOOK}
              blocked={busy}
              placeholder='Choose'
              onPick={setKind}
            />
            <FieldTile label='Design of'>
              <Input
                aria-label='Design of'
                value={subject}
                placeholder='Its subject'
                onChange={(event) => setSubject(event.target.value)}
              />
            </FieldTile>
            <FieldTile label='Quality (0–100)'>
              <Input
                type='number'
                min={0}
                max={PERCENT}
                aria-label='Quality'
                value={quality}
                onChange={(event) => setQuality(event.target.value)}
              />
            </FieldTile>
          </div>
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== null || problem !== null}
            disabledReason={busy ?? problem ?? undefined}
            onClick={() => {
              grant.mutate({ kind, subject: subject.trim(), quality: level })
              setSubject('')
            }}
          >
            <FileText />
            Grant it
          </Button>
        </AdjustBlock>
      </div>
    </LoreCard>
  )
}

export function DiscoveryDesk({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  return (
    <div data-surface='DiscoveryDesk' className='flex min-w-0 flex-col gap-4'>
      <GreatPeopleCard card={card} blocked={blocked} />
      <IncidentsCard card={card} blocked={blocked} />
      <StudiesCard card={card} blocked={blocked} />
      <BlueprintsCard card={card} blocked={blocked} />
    </div>
  )
}
