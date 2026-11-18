import { useState } from 'react'
import { Crown, Gem, PawPrint, Sparkles, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { EmptyState, KpiTile, PagedList, FieldTile } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { Facts, ForgeCard, RecordRow } from '@/features/cosmography/parts'
import { SCHOOLS } from '@/features/divine/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import {
  type MagicSchool,
  type MagicSiteKind,
  type MagicSiteView,
  type PlaceDominionView,
  type RuleView,
  type ThroneView,
  useDominionAction,
} from './api'
import { SITE_KINDS, THRONE_ICON, table } from './labels'
import { GOD_KINDS, PLACE_TYPES, why } from './model'
import {
  ClaimCard,
  CreatureCard,
  NodePicker,
  SiteCard,
  ThroneCard,
} from './parts'

export function RuleCard({ rule }: { rule: RuleView }) {
  return (
    <RecordRow
      icon={THRONE_ICON}
      tone='gold'
      title={<Ref node={rule.god} empty='no god' />}
      caption={`Rules ${rule.region?.name ?? 'this land'} · weighed in epoch ${rule.epoch}`}
    >
      <Facts
        items={[
          [
            'Region',
            <Ref key='region' node={rule.region} empty='a lost region' />,
          ],
          ['Share of all divine hold', `${rule.share}%`],
          ['Rival gods here', String(rule.rivals)],
        ]}
      />
    </RecordRow>
  )
}

export function ThroneForm({
  placeId,
  thrones,
  blocked,
}: {
  placeId: number | null
  thrones: ThroneView[]
  blocked: string | null
}) {
  const [place, setPlace] = useState<number | null>(null)
  const [power, setPower] = useState('60')
  const [holder, setHolder] = useState<number | null>(null)
  const target = placeId ?? place
  const create = useDominionAction(
    'throne:create',
    (_: void) => ({
      place_id: target ?? 0,
      power: Number(power),
      holder_id: holder,
    }),
    'A throne of power rises'
  )
  const busy = why(blocked, create.isPending)
  const taken = thrones.some((row) => row.place?.id === target)
  const missing =
    target === null
      ? 'Choose a place first'
      : taken
        ? 'A throne already stands there'
        : power === '' || Number.isNaN(Number(power))
          ? 'Type its power'
          : null
  return (
    <ForgeCard
      icon={Crown}
      tone='gold'
      title='Raise a throne of power'
      note='A throne gives the god who holds it essence, awe and spreading dominion, and counts toward ascension.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => {
            create.mutate()
            setPlace(null)
            setHolder(null)
          }}
        >
          <Crown />
          Raise
        </Button>
      }
    >
      <NodePicker
        label='Place'
        value={target}
        onChange={setPlace}
        blocked={busy ?? (placeId !== null ? 'The throne rises here' : null)}
        types={PLACE_TYPES}
      />
      <NumberField
        label='Power'
        value={power}
        min={0}
        max={100}
        disabled={busy !== null}
        onChange={setPower}
      />
      <NodePicker
        label='Seat a god at once'
        value={holder}
        onChange={setHolder}
        blocked={busy}
        kinds={GOD_KINDS}
      />
    </ForgeCard>
  )
}

export function SiteForm({
  placeId,
  blocked,
}: {
  placeId: number | null
  blocked: string | null
}) {
  const [place, setPlace] = useState<number | null>(null)
  const [kind, setKind] = useState<MagicSiteKind | ''>('')
  const [school, setSchool] = useState<MagicSchool | ''>('')
  const [strength, setStrength] = useState('50')
  const [now, setNow] = useState(false)
  const target = placeId ?? place
  const create = useDominionAction(
    'magic_site:create',
    (_: void) => ({
      place_id: target ?? 0,
      kind: kind as MagicSiteKind,
      school: school as MagicSchool,
      strength: Number(strength),
      found_now: now,
    }),
    now
      ? 'A magic site is laid and found'
      : 'A magic site is hidden in the land'
  )
  const busy = why(blocked, create.isPending)
  const missing =
    target === null
      ? 'Choose a place first'
      : kind === ''
        ? 'Choose the kind of site'
        : school === ''
          ? 'Choose its school'
          : null
  return (
    <ForgeCard
      icon={Sparkles}
      tone='verdigris'
      title='Lay a magic site'
      note='A source yields reagents, a school seat strengthens its school, a ward shields rites and a gateway opens toward another world.'
      columns={4}
      action={
        <div className='flex min-w-0 flex-wrap items-center justify-end gap-3'>
          <div className='flex items-center gap-2'>
            <FieldTile
              id={`site-now-${placeId ?? 'any'}`}
              label='Found at once'
            >
              <Switch
                id={`site-now-${placeId ?? 'any'}`}
                checked={now}
                disabled={busy !== null}
                onCheckedChange={setNow}
              />
            </FieldTile>
          </div>
          <Button
            size='sm'
            disabled={busy !== null || missing !== null}
            disabledReason={busy ?? missing ?? undefined}
            onClick={() => {
              create.mutate()
              setPlace(null)
            }}
          >
            <Gem />
            Lay it
          </Button>
        </div>
      }
    >
      <NodePicker
        label='Place'
        value={target}
        onChange={setPlace}
        blocked={busy ?? (placeId !== null ? 'The site lies here' : null)}
        types={PLACE_TYPES}
      />
      <MindPicker
        label='Kind of site'
        value={kind}
        table={table(SITE_KINDS)}
        blocked={busy}
        onPick={(value) => setKind(value as MagicSiteKind)}
      />
      <MindPicker
        label='School'
        value={school}
        table={SCHOOLS}
        blocked={busy}
        onPick={(value) => setSchool(value as MagicSchool)}
      />
      <NumberField
        label='Strength'
        value={strength}
        min={0}
        max={100}
        disabled={busy !== null}
        onChange={setStrength}
      />
    </ForgeCard>
  )
}

export function SiteList({
  sites,
  blocked,
}: {
  sites: MagicSiteView[]
  blocked: string | null
}) {
  if (sites.length === 0)
    return <Muted variant='caption'>No magic site lies here.</Muted>
  return (
    <PagedList
      items={sites}
      initial={3}
      noun={['site', 'sites']}
      className='flex min-w-0 flex-col gap-2'
      itemKey={(row) => row.id}
    >
      {(row) => <SiteCard site={row} blocked={blocked} />}
    </PagedList>
  )
}

export function ThroneList({
  thrones,
  blocked,
}: {
  thrones: ThroneView[]
  blocked: string | null
}) {
  if (thrones.length === 0)
    return <Muted variant='caption'>No throne of power stands here.</Muted>
  return (
    <PagedList
      items={thrones}
      initial={3}
      noun={['throne', 'thrones']}
      className='flex min-w-0 flex-col gap-2'
      itemKey={(row) => row.id}
    >
      {(row) => <ThroneCard throne={row} blocked={blocked} />}
    </PagedList>
  )
}

export function PlaceDominionPanel({
  data,
  blocked,
  laysSites,
}: {
  data: PlaceDominionView
  blocked: string | null
  laysSites: boolean
}) {
  const found = data.sites.filter((site) => site.found_epoch !== null).length
  const placeId = data.place.id
  return (
    <div
      data-surface='PlaceDominionPanel'
      className='flex min-w-0 flex-col gap-3'
    >
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <KpiTile
          label='Gods contending'
          value={data.claims.length}
          icon={Users}
          tone='info'
        />
        <KpiTile
          label='Thrones'
          value={data.thrones.length}
          icon={Crown}
          tone='gold'
        />
        <KpiTile
          label='Magic sites found'
          value={`${found} of ${data.sites.length}`}
          icon={Gem}
          tone='verdigris'
        />
        <KpiTile
          label='Divine creatures'
          value={data.creatures.length}
          icon={PawPrint}
          tone='warning'
        />
      </div>
      <Label variant='overline'>The god who rules this land</Label>
      {data.rule ? (
        <RuleCard rule={data.rule} />
      ) : (
        <EmptyState
          icon={Crown}
          size='inline'
          title='No god rules this land'
          description='A god whose dominion holds a large enough share of a region rules it and leans it by its scales.'
        />
      )}
      {data.claims.length > 0 && (
        <>
          <Label variant='overline'>Gods with dominion here</Label>
          <PagedList
            items={data.claims}
            initial={4}
            noun={['god', 'gods']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(claim) => claim.god?.id ?? 0}
          >
            {(claim) => (
              <ClaimCard claim={claim} focus='region' blocked={blocked} />
            )}
          </PagedList>
        </>
      )}
      <Label variant='overline'>Thrones of power</Label>
      <ThroneList thrones={data.thrones} blocked={blocked} />
      <ThroneForm
        placeId={laysSites ? placeId : null}
        thrones={data.thrones}
        blocked={blocked}
      />
      <Label variant='overline'>Magic sites</Label>
      <SiteList sites={data.sites} blocked={blocked} />
      <SiteForm placeId={laysSites ? placeId : null} blocked={blocked} />
      <Label variant='overline'>Divine creatures</Label>
      {data.creatures.length === 0 ? (
        <Muted variant='caption'>No divine creature dwells here.</Muted>
      ) : (
        <PagedList
          items={data.creatures}
          initial={2}
          noun={['creature', 'creatures']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.creature?.id ?? 0}
        >
          {(row) => <CreatureCard creature={row} blocked={blocked} />}
        </PagedList>
      )}
    </div>
  )
}
