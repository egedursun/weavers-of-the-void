import { useMemo, useState } from 'react'
import {
  Building2,
  CircleCheck,
  Crown,
  Layers,
  Lock,
  Plus,
  Ship,
  Sparkles,
  Trash2,
  Unlock,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Switch } from '@/components/ui/switch'
import { Medallion, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  AdjustBlock,
  ChoicePicker,
  LoreCard,
  RowEditor,
  RowEditors,
} from './LoreFields'
import { type LearningCard } from './api'
import { type LoreNamed, PERCENT, branchOf, busyOf, sentence } from './model'
import { useLoreAction } from './panels/controlParts'
import { BOOST_TRIGGERS, CAPABILITY_LOOK, CHOOSERS } from './researchLabels'

type Technique = LearningCard['techniques'][number]
type Institution = LearningCard['institutions'][number]
type Boost = LearningCard['boosts'][number]

const GRID = 'grid min-w-0 grid-cols-1 gap-2 @md/lore:grid-cols-2'
const BOOST_MAX = PERCENT - 1

function useTechniques(card: LearningCard) {
  return useMemo(
    () => new Map(card.techniques.map((row) => [row.technique, row])),
    [card.techniques]
  )
}

function techniqueTable(rows: Technique[]): Record<string, LoreNamed> {
  return Object.fromEntries(
    rows.map((row) => {
      const branch = branchOf(row.branch)
      return [
        row.technique,
        { label: row.label, icon: branch.icon, tone: branch.tone },
      ]
    })
  )
}

function useFocus(holderId: number) {
  return useLoreAction<{ technique: string | null; hold: boolean }>(
    '/api/actions/research:focus',
    (value) => ({
      holder_id: holderId,
      technique: value.technique,
      hold: value.hold,
    })
  )
}

function OptionTile({
  row,
  current,
  busy,
  onPick,
}: {
  row: Technique
  current: boolean
  busy: string | null
  onPick: () => void
}) {
  const branch = branchOf(row.branch)
  return (
    <li
      data-surface='ResearchOption'
      data-state={current ? 'chosen' : 'drawn'}
      className={cn(
        'flex h-full min-w-0 flex-col gap-2 rounded-lg border p-3 @md/lore:last:odd:col-span-2',
        current
          ? 'border-primary/50 bg-primary/8 shadow-md ring-1 shadow-primary/10 ring-primary/20'
          : 'border-info/40 bg-info/5'
      )}
    >
      <div className='flex min-w-0 items-start gap-2.5'>
        <Medallion
          icon={current ? CircleCheck : branch.icon}
          tone={current ? 'gold' : branch.tone}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold'>
            {row.label}
          </Text>
          <Muted variant='caption'>{row.effect}</Muted>
        </div>
        {row.institution && (
          <Badge size='sm' variant='outline'>
            <Building2 aria-hidden='true' />
            Institution
          </Badge>
        )}
      </div>
      <Progress
        value={row.progress}
        size='sm'
        aria-label={`${row.label} research progress`}
      />
      <div className='mt-auto flex min-w-0 flex-wrap items-center gap-2'>
        <Muted as='span' variant='caption' className='flex-1'>
          {`${row.progress}% researched · ${branch.label}`}
        </Muted>
        {current ? (
          <Badge variant='default'>
            <Sparkles aria-hidden='true' />
            Their focus
          </Badge>
        ) : (
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={onPick}
          >
            <Layers />
            Make it the focus
          </Button>
        )}
      </div>
    </li>
  )
}

function FocusCard({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  const techniques = useTechniques(card)
  const set = useFocus(card.holder_id)
  const [hold, setHold] = useState(true)
  const [pick, setPick] = useState('')
  const busy = busyOf(blocked, set.isPending)
  const focus = card.focus
  const current = focus ? techniques.get(focus.technique) : undefined
  const options = (focus?.options ?? [])
    .map((item) => techniques.get(item))
    .filter((row): row is Technique => row !== undefined && !row.known)
  const reachable = card.techniques.filter((row) => row.reachable && !row.known)
  const chooser = focus ? CHOOSERS[focus.chooser] : null
  const held = focus?.locked.includes('technique') ?? false
  return (
    <LoreCard
      title='Research focus'
      icon={Layers}
      tone='info'
      aside={
        <Badge variant='secondary'>{`${reachable.length} within reach`}</Badge>
      }
    >
      <div data-surface='ResearchFocus' className='flex min-w-0 flex-col gap-3'>
        {focus && current ? (
          <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-muted/30 p-3'>
            <Medallion icon={branchOf(current.branch).icon} tone='gold' />
            <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Text as='span' weight='semibold' className='min-w-0 flex-1'>
                  {current.label}
                </Text>
                {chooser && (
                  <Badge size='sm' variant='outline' title={chooser.hint}>
                    <chooser.icon aria-hidden='true' />
                    {chooser.label}
                  </Badge>
                )}
                {held && (
                  <Badge size='sm' variant='default'>
                    <Lock aria-hidden='true' />
                    Held
                  </Badge>
                )}
              </div>
              <Progress
                value={current.progress}
                aria-label={`${current.label} research progress`}
              />
              <Muted variant='caption'>
                {`${current.progress}% researched since epoch ${focus.epoch}. The focus advances at full pace; every other technique within reach moves slowly.`}
              </Muted>
            </div>
          </div>
        ) : (
          <Muted>
            No focus yet. Each epoch their scholars draw a few techniques within
            reach and the most skilled among them choose one.
          </Muted>
        )}
        {options.length > 0 && (
          <ul className={GRID}>
            <Paged items={options} as='li'>
              {(row) => (
                <OptionTile
                  key={row.technique}
                  row={row}
                  current={row.technique === focus?.technique}
                  busy={busy}
                  onPick={() => set.mutate({ technique: row.technique, hold })}
                />
              )}
            </Paged>
          </ul>
        )}
        <AdjustBlock title='Set their focus' icon={Crown}>
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <div className='min-w-0 flex-1 basis-48'>
              <ChoicePicker
                label='Technique within reach'
                value={pick}
                table={techniqueTable(reachable)}
                blocked={
                  reachable.length === 0 ? 'Nothing is within reach' : busy
                }
                placeholder={
                  reachable.length === 0 ? 'Nothing within reach' : 'Choose'
                }
                onPick={setPick}
              />
            </div>
            <label className='flex items-center gap-1.5'>
              <Switch
                checked={hold}
                aria-label='Hold it against their scholars'
                onCheckedChange={setHold}
              />
              <Muted as='span' variant='caption'>
                Hold it
              </Muted>
            </label>
            <Button
              size='sm'
              disabled={busy !== null || pick === ''}
              disabledReason={
                busy ?? (pick === '' ? 'Choose a technique' : undefined)
              }
              onClick={() => {
                set.mutate({ technique: pick, hold })
                setPick('')
              }}
            >
              <Layers />
              Set the focus
            </Button>
          </div>
          {focus && (
            <div className='flex min-w-0 flex-wrap gap-2'>
              {held && (
                <Button
                  size='sm'
                  variant='outline'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() =>
                    set.mutate({ technique: focus.technique, hold: false })
                  }
                >
                  <Unlock />
                  Let their scholars choose again
                </Button>
              )}
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => set.mutate({ technique: null, hold: false })}
              >
                <Trash2 />
                Clear the focus
              </Button>
            </div>
          )}
        </AdjustBlock>
      </div>
    </LoreCard>
  )
}

function useInstitution(holderId: number) {
  return useLoreAction<{
    technique: string
    present: boolean
    values: Record<string, number | boolean>
    release: string[]
  }>('/api/actions/research:institution', (value) => ({
    community_id: holderId,
    technique: value.technique,
    present: value.present,
    values: value.values,
    release: value.release,
  }))
}

function InstitutionTile({
  holderId,
  row,
  label,
  blocked,
}: {
  holderId: number
  row: Institution
  label: string
  blocked: string | null
}) {
  const set = useInstitution(holderId)
  const busy = busyOf(blocked, set.isPending)
  const save = (values: Record<string, number | boolean>) =>
    set.mutate({ technique: row.technique, present: true, values, release: [] })
  return (
    <li
      data-surface='InstitutionCard'
      data-state={row.embraced ? 'embraced' : 'refused'}
      className={cn(
        'flex h-full min-w-0 flex-col gap-3 rounded-lg border p-3 @md/lore:last:odd:col-span-2',
        row.embraced ? 'border-success/40 bg-success/5' : 'border-warning/40'
      )}
    >
      <div className='flex min-w-0 items-start gap-2.5'>
        <Medallion
          icon={Building2}
          tone={row.embraced ? 'success' : 'warning'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold'>
            {label}
          </Text>
          <Muted variant='caption'>
            {row.embraced
              ? `Embraced since epoch ${row.since_epoch}; it quickens their research.`
              : `Known since epoch ${row.since_epoch} but refused for ${row.refused_epochs} epochs; their research falls behind.`}
          </Muted>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {row.origin && (
          <Badge size='sm' variant='default'>
            <Crown aria-hidden='true' />
            Born here
          </Badge>
        )}
        {row.locked.length > 0 && (
          <Badge size='sm' variant='secondary'>
            <Lock aria-hidden='true' />
            Held
          </Badge>
        )}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <label className='flex items-center gap-1.5'>
          <Switch
            checked={row.embraced}
            disabled={busy !== null}
            aria-label='Embraced'
            onCheckedChange={(embraced) => save({ embraced })}
          />
          <Muted as='span' variant='caption'>
            Embraced
          </Muted>
        </label>
        <label className='flex items-center gap-1.5'>
          <Switch
            checked={row.origin}
            disabled={busy !== null}
            aria-label='Born here'
            onCheckedChange={(origin) => save({ origin })}
          />
          <Muted as='span' variant='caption'>
            Born here
          </Muted>
        </label>
      </div>
      <RowEditors>
        <RowEditor
          label='Epochs refused'
          value={row.refused_epochs}
          blocked={busy}
          onSave={(refused_epochs) => save({ refused_epochs })}
        />
        <RowEditor
          label='Since epoch'
          value={row.since_epoch}
          blocked={busy}
          onSave={(since_epoch) => save({ since_epoch })}
        />
      </RowEditors>
      <div className='mt-auto flex min-w-0 flex-wrap gap-2'>
        {row.locked.length > 0 && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() =>
              set.mutate({
                technique: row.technique,
                present: true,
                values: {},
                release: [...row.locked],
              })
            }
          >
            <Unlock />
            Let the world decide again
          </Button>
        )}
        <Button
          size='sm'
          variant='ghost'
          className='ml-auto'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() =>
            set.mutate({
              technique: row.technique,
              present: false,
              values: {},
              release: [],
            })
          }
        >
          <Trash2 />
          Tear it down
        </Button>
      </div>
    </li>
  )
}

function InstitutionsCard({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  const techniques = useTechniques(card)
  const set = useInstitution(card.holder_id)
  const [pick, setPick] = useState('')
  const busy = busyOf(blocked, set.isPending)
  const present = new Set(card.institutions.map((row) => row.technique))
  const open = card.techniques.filter(
    (row) => row.institution && !present.has(row.technique)
  )
  const embraced = card.institutions.filter((row) => row.embraced).length
  return (
    <LoreCard
      title='Institutions'
      icon={Building2}
      tone='success'
      aside={
        <Badge variant='secondary'>{`${embraced} of ${card.institutions.length} embraced`}</Badge>
      }
    >
      <div className='flex min-w-0 flex-col gap-3'>
        {card.institutions.length === 0 ? (
          <Muted>
            No institution stands here. One is born where a technique meets
            wealth, trade and scholars, then spreads to neighbours, who embrace
            it from their treasury or fall behind while they refuse it.
          </Muted>
        ) : (
          <ul className={GRID}>
            <Paged items={card.institutions} as='li'>
              {(row) => (
                <InstitutionTile
                  key={row.technique}
                  holderId={card.holder_id}
                  row={row}
                  label={techniques.get(row.technique)?.label ?? row.technique}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        )}
        <AdjustBlock title='Found an institution' icon={Plus}>
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <div className='min-w-0 flex-1 basis-48'>
              <ChoicePicker
                label='Institution'
                value={pick}
                table={techniqueTable(open)}
                blocked={
                  open.length === 0 ? 'Every institution stands here' : busy
                }
                placeholder={open.length === 0 ? 'None left' : 'Choose'}
                onPick={setPick}
              />
            </div>
            <Button
              size='sm'
              disabled={busy !== null || pick === ''}
              disabledReason={
                busy ?? (pick === '' ? 'Choose an institution' : undefined)
              }
              onClick={() => {
                set.mutate({
                  technique: pick,
                  present: true,
                  values: { embraced: true },
                  release: [],
                })
                setPick('')
              }}
            >
              <Building2 />
              Found it
            </Button>
          </div>
        </AdjustBlock>
      </div>
    </LoreCard>
  )
}

function BoostTile({
  row,
  label,
  blocked,
}: {
  row: Boost
  label: string
  blocked: string | null
}) {
  const edit = useLoreAction<Record<string, number>>(
    '/api/actions/research:boost_edit',
    (values) => ({ boost_id: row.id, values })
  )
  const remove = useLoreAction<null>(
    '/api/actions/research:boost_remove',
    () => ({ boost_id: row.id })
  )
  const busy = busyOf(blocked, edit.isPending, remove.isPending)
  const trigger = BOOST_TRIGGERS[row.trigger]
  return (
    <li
      data-surface='ResearchBoost'
      className='flex h-full min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3 @md/lore:last:odd:col-span-2'
    >
      <div className='flex min-w-0 items-start gap-2.5'>
        <Medallion icon={trigger.icon} tone={trigger.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold'>
            {`${label} +${row.progress}%`}
          </Text>
          <Muted variant='caption'>{`${trigger.label}, epoch ${row.epoch}`}</Muted>
        </div>
      </div>
      <RowEditor
        label='Boost'
        value={row.progress}
        min={1}
        max={BOOST_MAX}
        blocked={busy}
        onSave={(progress) => edit.mutate({ progress })}
      >
        <Button
          type='button'
          size='icon'
          variant='ghost'
          aria-label='Strike the boost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate(null)}
        >
          <Trash2 />
        </Button>
      </RowEditor>
    </li>
  )
}

function BoostsCard({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  const techniques = useTechniques(card)
  const grant = useLoreAction<{
    technique: string
    trigger: string
    progress: number
  }>('/api/actions/research:boost', (value) => ({
    holder_id: card.holder_id,
    ...value,
  }))
  const [technique, setTechnique] = useState('')
  const [trigger, setTrigger] = useState('')
  const busy = busyOf(blocked, grant.isPending)
  const unknown = card.techniques.filter((row) => !row.known)
  const missing =
    technique === ''
      ? 'Choose a technique'
      : trigger === ''
        ? 'Choose what earned it'
        : null
  return (
    <LoreCard
      title='Boosts'
      icon={Zap}
      tone='warning'
      aside={<Badge variant='secondary'>{card.boosts.length}</Badge>}
    >
      <div className='flex min-w-0 flex-col gap-3'>
        {card.boosts.length === 0 ? (
          <Muted>
            No deed has pushed their research yet. Great catches, sieges
            survived, plagues outlived, eclipses watched, great trials and great
            debts each push the techniques they teach.
          </Muted>
        ) : (
          <ul className={GRID}>
            <Paged items={card.boosts} as='li'>
              {(row) => (
                <BoostTile
                  key={row.id}
                  row={row}
                  label={techniques.get(row.technique)?.label ?? row.technique}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        )}
        <AdjustBlock title='Grant a boost' icon={Zap}>
          <div className='grid min-w-0 grid-cols-1 gap-2 @md/lore:grid-cols-2'>
            <ChoicePicker
              label='Technique'
              value={technique}
              table={techniqueTable(unknown)}
              blocked={
                unknown.length === 0 ? 'They know every technique' : busy
              }
              placeholder='Choose'
              onPick={setTechnique}
            />
            <ChoicePicker
              label='What earned it'
              value={trigger}
              table={BOOST_TRIGGERS}
              blocked={busy}
              placeholder='Choose'
              onPick={setTrigger}
            />
          </div>
          <RowEditor
            label='Push toward it'
            value={0}
            min={1}
            max={BOOST_MAX}
            blocked={busy ?? missing}
            onSave={(progress) => {
              grant.mutate({ technique, trigger, progress })
              setTechnique('')
            }}
          />
        </AdjustBlock>
      </div>
    </LoreCard>
  )
}

function CapabilitiesCard({ card }: { card: LearningCard }) {
  const held = card.capabilities.filter((row) => row.held).length
  return (
    <LoreCard
      title='What their knowledge allows'
      icon={Ship}
      tone='verdigris'
      aside={
        <Badge variant='secondary'>{`${held} of ${card.capabilities.length}`}</Badge>
      }
    >
      <ul data-surface='Capabilities' className={GRID}>
        <Paged items={card.capabilities} as='li'>
          {(row) => {
            const look = CAPABILITY_LOOK[row.capability]
            return (
              <li
                key={row.capability}
                data-state={row.held ? 'held' : 'locked'}
                className={cn(
                  'flex min-w-0 items-start gap-2.5 rounded-lg border p-3 @md/lore:last:odd:col-span-2',
                  row.held
                    ? 'border-primary/50 bg-primary/8'
                    : 'border-dashed bg-muted/20'
                )}
              >
                <Medallion
                  icon={row.held ? look.icon : Lock}
                  tone={row.held ? look.tone : 'muted'}
                  size='sm'
                />
                <div className='flex min-w-0 flex-1 flex-col'>
                  <Text
                    as='span'
                    weight='semibold'
                    tone={row.held ? 'default' : 'muted'}
                  >
                    {row.label}
                  </Text>
                  <Muted variant='caption'>
                    {row.held
                      ? `${sentence(row.effect)}.`
                      : `Not yet: once they know enough, ${row.effect}.`}
                  </Muted>
                </div>
              </li>
            )
          }}
        </Paged>
      </ul>
    </LoreCard>
  )
}

export function ResearchDesk({
  card,
  blocked,
}: {
  card: LearningCard
  blocked: string | null
}) {
  return (
    <div data-surface='ResearchDesk' className='flex min-w-0 flex-col gap-4'>
      <FocusCard card={card} blocked={blocked} />
      <InstitutionsCard card={card} blocked={blocked} />
      <BoostsCard card={card} blocked={blocked} />
      <CapabilitiesCard card={card} />
    </div>
  )
}
