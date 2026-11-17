import { useState } from 'react'
import {
  Church,
  Crown,
  Gem,
  GitBranch,
  Lock,
  Plus,
  Save,
  Sparkles,
  Trash2,
  Unlock,
  UserMinus,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { clergyFunctionValues } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  IconStat,
  Medallion,
  RangeField,
  StatBar,
  Paged,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { goodBand, named } from '../realm/labels'
import {
  AdjustPanel,
  ChoiceGrid,
  NumberField,
  Panel,
  RecordField,
  RefLink,
  Tag,
} from '../realm/parts'
import { type Doctrine } from './api'
import { CLERGY, HOLDINGS } from './labels'

const PERCENT = 100
const WORKING = 'Working…'
const COMMUNITIES = ['people', 'settlement', 'tribe'] as const
const SANCTITY_WORDS: [string, string, string, string] = [
  'A curiosity',
  'Revered',
  'Holy',
  'Most holy',
]
const DISTANCE_WORDS: [string, string, string, string] = [
  'A quibble',
  'A sect',
  'A rival creed',
  'Another faith',
]

type Office = Doctrine['clergy'][number]['kind']
type Holding = Doctrine['holdings'][number]['kind']

function busyOf(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function OfficeRow({
  cultId,
  office,
  blocked,
}: {
  cultId: number
  office: Doctrine['clergy'][number]
  blocked: string | null
}) {
  const [holder, setHolder] = useState<number | null>(office.holder?.id ?? null)
  const act = useGodAction<Record<string, unknown>>({
    run: (change) =>
      unwrap(
        api.POST('/api/actions/cult:office', {
          body: {
            cult_id: cultId,
            kind: office.kind,
            holder_id: null,
            locked: null,
            vacate: false,
            remove: false,
            ...change,
          },
        })
      ),
  })
  const busy = busyOf(blocked, act.isPending)
  const spec = named(CLERGY, office.kind)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion
          icon={spec.icon}
          tone={office.holder ? spec.tone : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Label truncate>{spec.label}</Label>
          {office.holder ? (
            <RefLink node={office.holder} />
          ) : (
            <Muted as='span'>Vacant</Muted>
          )}
        </div>
        {office.locked && (
          <Tag spec={{ label: 'Held', icon: Lock, tone: 'info' }} />
        )}
        <Muted
          as='span'
          variant='caption'
        >{`since ${office.since_epoch}`}</Muted>
      </div>
      <AdjustPanel
        trigger='Appoint'
        title={`The office of ${spec.label.toLowerCase()}`}
        note='An appointment is held: the faith will not replace the holder until you let it.'
      >
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <div className='min-w-48 flex-1'>
            <RecordField
              label='Holder'
              types={['mortal']}
              value={holder}
              onChange={setHolder}
              blocked={busy}
              placeholder='Choose a mortal'
            />
          </div>
          <Button
            size='sm'
            disabled={busy !== null || holder === null}
            disabledReason={busy ?? 'Choose the holder first.'}
            onClick={() => act.mutate({ holder_id: holder })}
          >
            <Crown />
            Appoint and hold
          </Button>
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {office.locked ? (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => act.mutate({ locked: false })}
            >
              <Unlock />
              Let the faith choose again
            </Button>
          ) : (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => act.mutate({ locked: true })}
            >
              <Lock />
              Hold this holder
            </Button>
          )}
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || !office.holder}
            disabledReason={busy ?? 'The office is already vacant.'}
            onClick={() => act.mutate({ vacate: true })}
          >
            <UserMinus />
            Leave it vacant
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => act.mutate({ remove: true })}
          >
            <Trash2 />
            Strike the office
          </Button>
        </div>
      </AdjustPanel>
    </li>
  )
}

export function ClergyOffices({
  doctrine,
  blocked,
}: {
  doctrine: Doctrine
  blocked: string | null
}) {
  const id = doctrine.cult?.id ?? 0
  const missing = clergyFunctionValues.filter(
    (kind) => !doctrine.clergy.some((office) => office.kind === kind)
  )
  const [kind, setKind] = useState<string>(missing[0] ?? 'priest')
  const found = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:office', {
          body: {
            cult_id: id,
            kind: kind as Office,
            holder_id: null,
            locked: null,
            vacate: false,
            remove: false,
          },
        })
      ),
  })
  const busy = busyOf(blocked, found.isPending)
  const filled = doctrine.clergy.filter((office) => office.holder).length
  return (
    <Panel
      title='Clergy'
      icon={Church}
      tone='verdigris'
      hint={
        doctrine.god_king
          ? `The god-king ${doctrine.god_king.name} is high priest`
          : `${filled} of ${plural(doctrine.clergy.length, 'office', 'offices')} filled`
      }
    >
      <div data-surface='ClergyOffices' className='flex min-w-0 flex-col gap-2'>
        {doctrine.clergy.length === 0 && <Muted>No office is founded.</Muted>}
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={doctrine.clergy} as='li'>
            {(office) => (
              <OfficeRow
                key={`${office.kind}.${office.holder?.id ?? 0}.${office.locked}`}
                cultId={id}
                office={office}
                blocked={blocked}
              />
            )}
          </Paged>
        </ul>
        {missing.length > 0 && (
          <AdjustPanel
            trigger='Found an office'
            title='Found a new office'
            note='The faith fills a new office from its best-taught clergy.'
          >
            <ChoiceGrid
              label='Office'
              table={Object.fromEntries(
                missing.map((item) => [item, named(CLERGY, item)])
              )}
              value={kind}
              blocked={busy}
              onPick={setKind}
            />
            <div>
              <Button
                size='sm'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => found.mutate(undefined)}
              >
                <Plus />
                Found it
              </Button>
            </div>
          </AdjustPanel>
        )}
      </div>
    </Panel>
  )
}

export function HoldingLevers({
  doctrine,
  blocked,
}: {
  doctrine: Doctrine
  blocked: string | null
}) {
  const id = doctrine.cult?.id ?? 0
  const [target, setTarget] = useState<number | null>(null)
  const [kind, setKind] = useState<string>('land')
  const act = useGodAction<boolean>({
    run: (remove) =>
      unwrap(
        api.POST('/api/actions/cult:holding', {
          body: {
            cult_id: id,
            entity_id: target ?? 0,
            kind: kind as Holding,
            remove,
          },
        })
      ),
  })
  const busy = busyOf(blocked, act.isPending)
  return (
    <AdjustPanel
      trigger='Grant or take a holding'
      title='The faith’s holdings'
      note='Lands are the tithe base; temples, relics, holy places and monasteries carry their own works.'
    >
      <ChoiceGrid
        label='Held as'
        table={HOLDINGS}
        value={kind}
        blocked={busy}
        onPick={setKind}
      />
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='min-w-48 flex-1'>
          <RecordField
            label='What it holds'
            types={null}
            value={target}
            onChange={setTarget}
            blocked={busy}
            placeholder='Choose a land, temple or relic'
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null || target === null}
          disabledReason={busy ?? 'Choose the holding first.'}
          onClick={() => act.mutate(false)}
        >
          <Plus />
          Grant it
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || target === null}
          disabledReason={busy ?? 'Choose the holding first.'}
          onClick={() => act.mutate(true)}
        >
          <Trash2 />
          Take it away
        </Button>
      </div>
    </AdjustPanel>
  )
}

export function RelicShrine({
  relic,
  blocked,
}: {
  relic: Doctrine['relics'][number]
  blocked: string | null
}) {
  const itemId = relic.item?.id ?? 0
  const [sanctity, setSanctity] = useState(relic.sanctity)
  const [pilgrims, setPilgrims] = useState(String(relic.pilgrims))
  const [shrine, setShrine] = useState<number | null>(relic.shrine?.id ?? null)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/relic:edit', {
          body: {
            item_id: itemId,
            values: {
              sanctity: Math.max(0, Math.min(PERCENT, Math.round(sanctity))),
              pilgrims: Math.max(0, Math.round(Number(pilgrims) || 0)),
              shrine_entity_id: shrine,
            },
            release: [],
          },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/relic:edit', {
          body: { item_id: itemId, values: {}, release: relic.locked },
        })
      ),
  })
  const strip = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/relic:remove', { body: { item_id: itemId } })
      ),
  })
  const busy = busyOf(
    blocked,
    save.isPending,
    release.isPending,
    strip.isPending
  )
  return (
    <li
      data-surface='RelicShrine'
      className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={Sparkles} tone='gold' size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Label variant='overline'>Saint</Label>
          {relic.saint ? (
            <RefLink node={relic.saint} />
          ) : (
            <Muted>Nameless</Muted>
          )}
        </div>
        <IconStat
          icon={Users}
          label='Pilgrims'
          value={formatInteger(relic.pilgrims)}
          tone='info'
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Gem
          aria-hidden='true'
          className='size-icon-xs shrink-0 text-brand-verdigris'
        />
        {relic.item ? <RefLink node={relic.item} /> : <Muted>No relic</Muted>}
        {relic.shrine && (
          <>
            <Church
              aria-hidden='true'
              className='size-icon-xs shrink-0 text-muted-foreground'
            />
            <RefLink node={relic.shrine} />
          </>
        )}
        {relic.locked.length > 0 && (
          <Tag
            spec={{ label: 'Held', icon: Lock, tone: 'info' }}
            text={`Holding ${relic.locked.length}`}
          />
        )}
      </div>
      <StatBar
        label={`Sanctity, canonised in epoch ${relic.canonised_epoch}`}
        value={relic.sanctity}
        max={PERCENT}
        icon={Sparkles}
      />
      <AdjustPanel
        trigger='Tend the relic'
        title='Tend the relic'
        note='Set how holy it is, how many walk to it and where its shrine stands. What you set is held.'
      >
        <RangeField
          label='Sanctity'
          icon={Sparkles}
          level={goodBand(sanctity, SANCTITY_WORDS).label}
          value={sanctity}
          min={0}
          max={PERCENT}
          lowLabel='A curiosity'
          highLabel='Most holy'
          onChange={setSanctity}
        />
        <div className='grid min-w-0 grid-cols-1 gap-2 @md/faith:grid-cols-2'>
          <NumberField
            label='Pilgrims'
            icon={Users}
            min={0}
            value={pilgrims}
            blocked={busy}
            onChange={setPilgrims}
          />
          <RecordField
            label='Shrine'
            types={COMMUNITIES}
            value={shrine}
            onChange={setShrine}
            blocked={busy}
            placeholder='Where it is kept'
          />
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => save.mutate(undefined)}
          >
            <Save />
            Set and hold
          </Button>
          {relic.locked.length > 0 && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => release.mutate(undefined)}
            >
              <Unlock />
              Let pilgrims decide
            </Button>
          )}
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strip.mutate(undefined)}
          >
            <Trash2 />
            Strip its holiness
          </Button>
        </div>
      </AdjustPanel>
    </li>
  )
}

export function HeresyLevers({
  heresy,
  blocked,
}: {
  heresy: Doctrine['heresies'][number]
  blocked: string | null
}) {
  const heresyId = heresy.heresy?.id ?? 0
  const [distance, setDistance] = useState(heresy.distance)
  const [tolerated, setTolerated] = useState(heresy.tolerated)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:edit_heresy', {
          body: {
            heresy_id: heresyId,
            values: {
              distance: Math.max(0, Math.min(PERCENT, Math.round(distance))),
              tolerated,
            },
            release: [],
          },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:edit_heresy', {
          body: { heresy_id: heresyId, values: {}, release: heresy.locked },
        })
      ),
  })
  const forgive = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:undeclare_heresy', {
          body: { heresy_id: heresyId },
        })
      ),
  })
  const busy = busyOf(
    blocked,
    save.isPending,
    release.isPending,
    forgive.isPending
  )
  return (
    <AdjustPanel
      trigger='Shape the heresy'
      title='How far it strayed'
      note='Set its distance from the mother church and whether it is suffered. Forgiving it unnames it.'
    >
      <RangeField
        label='Distance from the mother church'
        icon={GitBranch}
        level={goodBand(distance, DISTANCE_WORDS).label}
        value={distance}
        min={0}
        max={PERCENT}
        lowLabel='A quibble'
        highLabel='Another faith'
        onChange={setDistance}
      />
      <label className='flex min-w-0 items-center gap-2'>
        <Switch
          checked={tolerated}
          disabled={busy !== null}
          aria-label='Suffer it openly'
          onCheckedChange={setTolerated}
        />
        <Text as='span'>Suffer it openly</Text>
      </label>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Set and hold
        </Button>
        {heresy.locked.length > 0 && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => release.mutate(undefined)}
          >
            <Unlock />
            Let it drift again
          </Button>
        )}
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => forgive.mutate(undefined)}
        >
          <Trash2 />
          Forgive and unname it
        </Button>
      </div>
    </AdjustPanel>
  )
}
