import { useState } from 'react'
import {
  Ban,
  BookUser,
  Eraser,
  ListChecks,
  Save,
  Shapes,
  Unlock,
} from 'lucide-react'
import { type ActionBody } from '@/api/actions'
import {
  damageTypeValues,
  magicSchoolValues,
  summonFormValues,
  techniqueValues,
} from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Paged, PagedList, FieldTile } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { AdjustBlock, ChoicePicker, NamedChip, Who } from '../LoreFields'
import { type LoreCard as LoreCardData } from '../api'
import { KindForge } from '../forge/KindForge'
import { CALENDAR_SLOTS } from '../forge/forgeModel'
import { EFFECTS, type LoreNamed, busyOf, lookup } from '../model'
import { PickAndRun, useLoreAction } from './controlParts'

type Rite = NonNullable<LoreCardData['rite']>
type Effect = Rite['effects'][number]
type Needs = Record<string, string | number | boolean>
const HOLDERS = ['mortal', 'settlement', 'people', 'cult', 'faction'] as const
const AUTHORITIES = ['polity', 'cult', 'settlement', 'people'] as const
const NONE = ''

function named(values: readonly string[]): Record<string, LoreNamed> {
  return Object.fromEntries(values.map((value) => [value, lookup({}, value)]))
}

const DAMAGE = named(damageTypeValues)
const SUMMONS = named(summonFormValues)
const TECHNIQUES = named(techniqueValues)
const PLACES = named(['settlement', 'place', 'structure', 'region'])

function EffectShape({
  id,
  effect,
  blocked,
}: {
  id: number
  effect: Effect
  blocked: string | null
}) {
  const [damage, setDamage] = useState(effect.damage_type ?? NONE)
  const [form, setForm] = useState(effect.summon_form ?? NONE)
  const save = useLoreAction('rite:effect', (_: void) => ({
    rite_id: id,
    effect: effect.effect,
    magnitude: effect.magnitude,
    detail: effect.detail ?? null,
    damage_type: (damage || null) as ActionBody<'rite:effect'>['damage_type'],
    summon_form: (form || null) as ActionBody<'rite:effect'>['summon_form'],
    custom_kind_id: effect.custom_kind_id ?? null,
  }))
  const busy = busyOf(blocked, save.isPending)
  return (
    <li className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-4'>
      <NamedChip
        spec={lookup(EFFECTS, effect.effect)}
      >{`${lookup(EFFECTS, effect.effect).label} ${effect.magnitude}`}</NamedChip>
      <ChoicePicker
        label='Wound it deals'
        value={damage}
        table={DAMAGE}
        blocked={busy}
        placeholder='As the school'
        onPick={setDamage}
      />
      <ChoicePicker
        label='What it calls'
        value={form}
        table={SUMMONS}
        blocked={busy}
        placeholder='A spirit'
        onPick={setForm}
      />
      <Button
        act={save}
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => save.mutate()}
      >
        <Save />
        Shape it
      </Button>
    </li>
  )
}

function Requirements({
  id,
  card,
  blocked,
}: {
  id: number
  card: Rite
  blocked: string | null
}) {
  const [needs, setNeeds] = useState<Needs>({ ...(card.requirements as Needs) })
  const save = useLoreAction('rite:requirements', (_: void) => ({
    rite_id: id,
    requirements: needs,
  }))
  const busy = busyOf(blocked, save.isPending)
  const put = (key: string, value: string | number | boolean | null) =>
    setNeeds((before) => {
      const next = { ...before }
      if (value === null || value === '' || value === false) delete next[key]
      else next[key] = value
      return next
    })
  return (
    <AdjustBlock title='What it asks of its caster' icon={ListChecks}>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <ChoicePicker
          label='Technique'
          value={String(needs.technique ?? NONE)}
          table={TECHNIQUES}
          blocked={busy}
          placeholder='None'
          onPick={(value) => put('technique', value)}
        />
        <ChoicePicker
          label='Worked in'
          value={String(needs.place ?? NONE)}
          table={PLACES}
          blocked={busy}
          placeholder='Anywhere'
          onPick={(value) => put('place', value)}
        />
        <ChoicePicker
          label='Season'
          value={String(needs.slot ?? NONE)}
          table={CALENDAR_SLOTS}
          blocked={busy}
          placeholder='Any season'
          onPick={(value) => put('slot', value)}
        />
        <FieldTile label='Spellcraft needed'>
          <Input
            type='number'
            min={0}
            max={100}
            aria-label='Spellcraft needed'
            value={String(needs.skill ?? '')}
            onChange={(event) =>
              put(
                'skill',
                event.target.value === ''
                  ? null
                  : Math.round(Number(event.target.value))
              )
            }
          />
        </FieldTile>
        <FieldTile label='Hands needed'>
          <Input
            type='number'
            min={0}
            aria-label='Hands needed'
            value={String(needs.participants ?? '')}
            onChange={(event) =>
              put(
                'participants',
                event.target.value === ''
                  ? null
                  : Math.round(Number(event.target.value))
              )
            }
          />
        </FieldTile>
        <label className='flex min-w-0 items-center gap-2'>
          <Switch
            checked={Boolean(needs.ley)}
            aria-label='On a ley line'
            onCheckedChange={(next) => put('ley', next)}
          />
          <Text as='span'>Only on a ley line</Text>
        </label>
        <label className='flex min-w-0 items-center gap-2'>
          <Switch
            checked={Boolean(needs.war)}
            aria-label='Only in a time of war'
            onCheckedChange={(next) => put('war', next)}
          />
          <Text as='span'>Only in a time of war</Text>
        </label>
      </div>
      <Button
        act={save}
        size='sm'
        className='self-start'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => save.mutate()}
      >
        <Save />
        Set what it asks
      </Button>
    </AdjustBlock>
  )
}

export function RiteControls({
  id,
  card,
  blocked,
}: {
  id: number
  card: Rite
  blocked: string | null
}) {
  const teach = useLoreAction(
    'rite:teach',
    (value: { holder: number; taught: boolean }) => ({
      rite_id: id,
      holder_id: value.holder,
      taught: value.taught,
    })
  )
  const forbid = useLoreAction(
    'rite:forbid',
    (value: { authority: number; forbidden: boolean }) => ({
      rite_id: id,
      authority_id: value.authority,
      forbidden: value.forbidden,
    })
  )
  const dispel = useLoreAction('rite:dispel', (_: void) => ({
    rite_id: id,
  }))
  const busy = busyOf(blocked, dispel.isPending, forbid.isPending)
  return (
    <div data-surface='RiteDesigner' className='flex min-w-0 flex-col gap-3'>
      <Requirements id={id} card={card} blocked={blocked} />
      <AdjustBlock title='Shape its workings' icon={Shapes}>
        <ul className='flex min-w-0 flex-col gap-3'>
          <Paged items={card.effects} as='li'>
            {(effect) => (
              <EffectShape
                key={effect.effect}
                id={id}
                effect={effect}
                blocked={blocked}
              />
            )}
          </Paged>
        </ul>
        {card.effects.length === 0 && (
          <Muted variant='caption'>Give it a working first.</Muted>
        )}
      </AdjustBlock>
      <AdjustBlock title='Teach it' icon={BookUser}>
        <PickAndRun
          act={teach}
          types={HOLDERS}
          placeholder='Choose a pupil…'
          label='Teach the rite'
          icon={BookUser}
          blocked={blocked}
          pending={teach.isPending}
          onRun={(holder) => teach.mutate({ holder, taught: true })}
        />
      </AdjustBlock>
      <AdjustBlock title='Forbid it' icon={Ban}>
        {card.forbidden_by.length > 0 && (
          <PagedList
            items={card.forbidden_by}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap gap-2'
            itemKey={(item) => item.id}
          >
            {(item) => (
              <Badge key={item.id} variant='destructive'>
                <Ban aria-hidden='true' />
                <Who item={item} />
                <Button
                  act={forbid}
                  size='icon'
                  variant='ghost'
                  aria-label={`Lift the ban of ${item.name}`}
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() =>
                    forbid.mutate({ authority: item.id, forbidden: false })
                  }
                >
                  <Unlock />
                </Button>
              </Badge>
            )}
          </PagedList>
        )}
        <PickAndRun
          act={forbid}
          types={AUTHORITIES}
          placeholder='Choose a realm, cult or people…'
          label='Forbid it there'
          icon={Ban}
          blocked={blocked}
          pending={forbid.isPending}
          variant='destructive'
          onRun={(authority) => forbid.mutate({ authority, forbidden: true })}
        />
      </AdjustBlock>
      <AdjustBlock title='Undo its last working' icon={Eraser}>
        <Muted variant='caption'>{`Lifts the weather it called, the ward it raised or the curse it laid (${wordOf(magicSchoolValues, card.school)}).`}</Muted>
        <Button
          act={dispel}
          size='sm'
          variant='outline'
          className='self-start'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => dispel.mutate()}
        >
          <Eraser />
          Dispel it
        </Button>
      </AdjustBlock>
      <KindForge catalog='rite_effect' />
    </div>
  )
}
