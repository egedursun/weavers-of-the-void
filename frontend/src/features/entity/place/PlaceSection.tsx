import { useState } from 'react'
import { Eye, Footprints, Lock, Sparkles, Swords, Unlock } from 'lucide-react'
import { placeKindValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { EmptyState, KpiTile, Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { busyOf, PERCENT } from '../lore/model'
import { MindPicker } from '../mind/parts'
import { AdjustPanel, NumberField, SwitchField } from '../wilds/parts'
import { PlaceSecrets } from './PlaceSecrets'
import { type PlaceProfile, usePlaceAction, usePlaceProfile } from './api'
import { PLACE_ICON, SACRED, choices, fieldOf, kindOf } from './labels'

const HOLDABLE = ['kind', 'sacredness', 'mystery'] as const

export function PlaceHolds({
  placeId,
  held,
  only,
}: {
  placeId: number
  held: readonly string[]
  only?: readonly string[]
}) {
  const { reason } = useGodGate()
  const release = usePlaceAction('place:release')
  const busy = busyOf(reason(), release.isPending)
  const shown = held.filter((key) => !only || only.includes(key))
  if (shown.length === 0) return null
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2'>
      <Lock aria-hidden='true' className='size-icon-xs shrink-0 text-primary' />
      {shown.map((key) => (
        <Button
          act={release}
          key={key}
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() =>
            release.mutate({
              place_id: placeId,
              field: key as 'kind',
            })
          }
        >
          <Unlock />
          {`Release ${fieldOf(key).toLowerCase()}`}
        </Button>
      ))}
    </div>
  )
}

function Summary({ profile }: { profile: PlaceProfile }) {
  const kind = kindOf(profile.kind)
  const sacred = SACRED[profile.sacred_class] ?? SACRED.profane
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @md/place:grid-cols-2 @3xl/place:grid-cols-4'>
      <KpiTile
        label='Kind'
        value={kind.label}
        icon={kind.icon}
        tone={kind.tone ?? 'gold'}
        hint={kind.hint}
      />
      <KpiTile
        label='Sacredness'
        value={profile.sacredness}
        icon={Sparkles}
        tone={profile.holy_site ? 'gold' : 'muted'}
        hint={`${sacred.label} kind; drifting toward ${profile.sacred_target}${profile.holy_site ? '; a holy site' : ''}`}
        meter={{ value: profile.sacredness, max: PERCENT, label: 'Sacredness' }}
      />
      <KpiTile
        label='Pilgrims each age'
        value={profile.pilgrims}
        icon={Footprints}
        tone={profile.pilgrims > 0 ? 'verdigris' : 'muted'}
        hint={
          profile.pilgrimage_site
            ? 'A declared pilgrimage site'
            : 'Sacred places draw their region'
        }
      />
      <KpiTile
        label='Mystery'
        value={profile.mystery}
        icon={Eye}
        tone='info'
        hint='Searchers and seers find secrets faster here'
        meter={{ value: profile.mystery, max: PERCENT, label: 'Mystery' }}
      />
      {profile.battles > 0 && (
        <KpiTile
          label='Battles fought here'
          value={profile.battles}
          icon={Swords}
          tone='danger'
          hint='Valleys and crossroads become battlefields'
        />
      )}
    </div>
  )
}

function ShapePlace({ profile }: { profile: PlaceProfile }) {
  const { reason } = useGodGate()
  const edit = usePlaceAction('place:edit')
  const declare = usePlaceAction('pilgrimage:declare')
  const clear = usePlaceAction('pilgrimage:clear')
  const [kind, setKind] = useState(profile.kind)
  const [sacredness, setSacredness] = useState(String(profile.sacredness))
  const [mystery, setMystery] = useState(String(profile.mystery))
  const [hold, setHold] = useState(true)
  const busy = busyOf(
    reason(),
    edit.isPending,
    declare.isPending,
    clear.isPending
  )
  const held = profile.locked.filter((key) =>
    (HOLDABLE as readonly string[]).includes(key)
  )
  const save = () =>
    edit.mutate({
      place_id: profile.place_id,
      kind: kind === profile.kind ? null : kind,
      sacredness:
        Number(sacredness) === profile.sacredness ? null : Number(sacredness),
      mystery: Number(mystery) === profile.mystery ? null : Number(mystery),
      hold,
    })
  return (
    <AdjustPanel
      acts={[edit, clear, declare]}
      title='Shape this place'
      note='Set its kind, sacredness and mystery; held values stay as you set them until you release them. Every change goes into the ledger.'
      head={
        <div className='flex min-w-0 flex-col gap-2'>
          <PlaceHolds
            placeId={profile.place_id}
            held={[...held, ...(profile.mystery_held ? ['mystery'] : [])]}
          />
        </div>
      }
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/place:grid-cols-2 @3xl/place:grid-cols-4'>
        <MindPicker
          label='Kind'
          value={kind}
          table={choices(placeKindValues, (key) => kindOf(key).label)}
          blocked={busy}
          onPick={(value) => setKind(value as typeof kind)}
        />
        <NumberField
          label='Sacredness'
          value={sacredness}
          min={0}
          max={PERCENT}
          disabled={busy !== null}
          onChange={setSacredness}
        />
        <NumberField
          label='Mystery'
          value={mystery}
          min={0}
          max={PERCENT}
          disabled={busy !== null}
          onChange={setMystery}
        />
        <SwitchField
          permission='lock_canon'
          label='Hold what I set'
          checked={hold}
          disabled={busy !== null}
          onChange={setHold}
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          act={edit}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={save}
        >
          Save
        </Button>
        {profile.pilgrimage_site ? (
          <Button
            act={clear}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => clear.mutate({ entity_id: profile.place_id })}
          >
            Take it off the pilgrims' roads
          </Button>
        ) : (
          <Button
            act={declare}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => declare.mutate({ entity_id: profile.place_id })}
          >
            Declare a pilgrimage site
          </Button>
        )}
      </div>
    </AdjustPanel>
  )
}

export function PlaceSection({ placeId }: { placeId: number }) {
  const view = usePlaceProfile(placeId)
  const profile = view.data
  return (
    <Section
      id='section-place'
      title='Place'
      description='What kind of place this is, how holy it is, who comes to it, and what it hides.'
      icon={PLACE_ICON}
    >
      {!profile ? (
        <EmptyState
          icon={PLACE_ICON}
          title='Not surveyed yet'
          description='The next epoch gives this place its kind.'
        />
      ) : (
        <div className='@container/place flex min-w-0 flex-col gap-4'>
          <Summary profile={profile} />
          <PlaceSecrets profile={profile} />
          <ShapePlace
            key={`${profile.kind}-${profile.sacredness}-${profile.mystery}`}
            profile={profile}
          />
          <Muted variant='caption'>
            {profile.deep
              ? 'Deep enough for miners to strike what lies below.'
              : 'Too shallow for miners to reach its secrets.'}
          </Muted>
        </div>
      )}
    </Section>
  )
}
