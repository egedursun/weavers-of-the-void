import { useState } from 'react'
import { Gavel, Plus, Save, Scale, Trash2, TriangleAlert } from 'lucide-react'
import { type ActionBody, type EditValues } from '@/api/actions'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  LoadingBlock,
  Medallion,
  Paged,
  Section,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { busyOf } from '@/features/entity/lore/model'
import {
  Group,
  Held,
  NumberField,
  SwitchField,
} from '@/features/entity/wilds/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { VetoButton } from './CouncilOrderPanel'
import { type RulingView, useDivineAction, useRulings } from './api'
import {
  MOTIONS,
  PENANCE_DEEDS,
  PUNISHMENTS,
  SCHOOLS,
  VOTING_RULES,
  heldLabel,
} from './labels'
import { useGodTable } from './model'
import { NodeName, PickRow } from './parts'

const GOD_TARGETS = new Set([
  'war_on_foreign_god',
  'punish_son',
  'holy_world',
  'reassign_world',
  'outlaw_power',
  'admit_member',
  'expel_member',
  'recognise_god',
])
const HERO_TARGETS = new Set(['bless_hero'])
const WORLD_TARGETS = new Set(['holy_world', 'reassign_world', 'outlaw_source'])
const RULE_NAMES = Object.fromEntries(
  Object.entries(VOTING_RULES).map(([key, value]) => [key, value.label])
)

function RulingRow({ row, busy }: { row: RulingView; busy: string | null }) {
  const edit = useDivineAction(
    'ruling:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      ruling_id: row.id,
      ...vars,
    })
  )
  const revoke = useDivineAction('ruling:revoke', (_: void) => ({
    ruling_id: row.id,
  }))
  const [until, setUntil] = useState('')
  const spec = MOTIONS[row.motion]
  const pending = busyOf(busy, edit.isPending, revoke.isPending)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion
          icon={spec.icon}
          tone={row.active ? spec.tone : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text weight='semibold'>{spec.label}</Text>
          <div className='flex min-w-0 flex-wrap items-center gap-1'>
            <Badge size='sm' variant={row.active ? 'success' : 'secondary'}>
              {row.active ? 'In force' : 'Lapsed'}
            </Badge>
            <Badge size='sm' variant='outline'>
              {row.enacted ? 'Carried out' : 'Not yet carried out'}
            </Badge>
            {row.target && <NodeName item={row.target} />}
            {row.world && <NodeName item={row.world} />}
            {row.school && (
              <Badge
                size='sm'
                variant='outline'
              >{`${SCHOOLS[row.school]} rites`}</Badge>
            )}
            {row.voting_rule && (
              <Badge size='sm' variant='outline'>
                {VOTING_RULES[row.voting_rule].label}
              </Badge>
            )}
            {row.punishment && row.motion === 'punish_son' && (
              <Badge size='sm' variant='outline'>
                {PUNISHMENTS[row.punishment]}
              </Badge>
            )}
            {row.penance_deed && row.punishment === 'penance' && (
              <Badge size='sm' variant='outline'>
                {`Penance: ${PENANCE_DEEDS[row.penance_deed]}`}
              </Badge>
            )}
          </div>
          <Muted variant='caption'>{`Laid down in epoch ${row.epoch}${row.until_epoch ? `, holds until epoch ${row.until_epoch}` : ''}${row.note ? ` — ${row.note}` : ''}`}</Muted>
        </div>
        <VetoButton ruling={row} busy={pending} />
        <Button
          act={revoke}
          size='sm'
          variant='ghost'
          disabled={pending !== null}
          disabledReason={pending ?? undefined}
          onClick={() => revoke.mutate()}
        >
          <Trash2 />
          Strike out
        </Button>
      </div>
      <Held
        act={edit}
        keys={row.locked}
        label={heldLabel}
        busy={pending}
        onRelease={() => edit.mutate({ values: {}, release: row.locked })}
      />
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
        <SwitchField
          act={edit}
          label='In force'
          checked={row.active}
          disabled={pending !== null}
          onChange={(active) =>
            edit.mutate({ values: { active }, release: [] })
          }
        />
        <NumberField
          label='Holds until epoch'
          value={until}
          min={0}
          disabled={pending !== null}
          onChange={setUntil}
        />
        <div className='flex min-w-0 items-end'>
          <Button
            act={edit}
            size='sm'
            disabled={pending !== null || until === ''}
            disabledReason={
              pending ?? (until === '' ? 'Set an epoch first' : undefined)
            }
            onClick={() => {
              edit.mutate({
                values: { until_epoch: Number(until) },
                release: [],
              })
              setUntil('')
            }}
          >
            <Save />
            Hold its end
          </Button>
        </div>
      </div>
    </li>
  )
}

export function CouncilRulingsPanel() {
  const view = useRulings()
  const gods = useGodTable()
  const { reason } = useGodGate()
  const [motion, setMotion] = useState('')
  const [god, setGod] = useState('')
  const [hero, setHero] = useState<number | null>(null)
  const [world, setWorld] = useState<number | null>(null)
  const [school, setSchool] = useState('')
  const [punishment, setPunishment] = useState('chain')
  const [rule, setRule] = useState('majority')
  const [deed, setDeed] = useState('restore_world')
  const decree = useDivineAction('ruling:decree', (_: void) => ({
    motion: motion as ActionBody<'ruling:decree'>['motion'],
    target_id: HERO_TARGETS.has(motion)
      ? hero
      : god === ''
        ? null
        : Number(god),
    world_id: world,
    school:
      school === '' ? null : (school as ActionBody<'ruling:decree'>['school']),
    punishment:
      motion === 'punish_son'
        ? (punishment as ActionBody<'ruling:decree'>['punishment'])
        : null,
    voting_rule:
      motion === 'set_council_rules'
        ? (rule as ActionBody<'ruling:decree'>['voting_rule'])
        : null,
    penance_deed:
      motion === 'punish_son' && punishment === 'penance'
        ? (deed as ActionBody<'ruling:decree'>['penance_deed'])
        : null,
  }))
  const busy = busyOf(reason(), decree.isPending)
  const motions = Object.fromEntries(
    (view.data?.motions ?? []).map((item) => [item, MOTIONS[item].label])
  )
  const problem =
    motion === ''
      ? 'Choose a decision'
      : GOD_TARGETS.has(motion) && god === ''
        ? 'Choose the god it names'
        : HERO_TARGETS.has(motion) && hero === null
          ? 'Choose the hero'
          : WORLD_TARGETS.has(motion) && world === null
            ? 'Choose the world'
            : motion === 'outlaw_rite' && school === ''
              ? 'Choose the school of rites'
              : null
  return (
    <Section
      id='section-council-rulings'
      title='Rulings of the council'
      description='Typed decisions of the Council of the Gods that bind the engine for a number of epochs: truces, outlawed rites, powers and sources, punishments, holy worlds, the division and giving of worlds, wars on foreign gods, members admitted, put out or recognised, tithes, the rules of the council itself, regulations of made minds, powers and living craft, blessings and petitions.'
      icon={Scale}
      tone='gold'
    >
      {view.isPending && <LoadingBlock label='Reading the rulings' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The rulings could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='CouncilRulings'
          className='flex min-w-0 flex-col gap-3'
        >
          {view.data.rulings.length === 0 ? (
            <EmptyState
              icon={Gavel}
              title='No ruling yet'
              description='When the council passes a typed decision it binds the gods here; you can lay one down.'
            />
          ) : (
            <ul className='flex min-w-0 flex-col gap-2'>
              <Paged items={view.data.rulings} as='li'>
                {(row) => <RulingRow key={row.id} row={row} busy={busy} />}
              </Paged>
            </ul>
          )}
          <Group title='Lay down a ruling' icon={Plus}>
            <div className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
              <PickRow
                label='Decision'
                table={motions}
                value={motion}
                blocked={busy}
                onPick={setMotion}
              />
              <PickRow
                label='God it names'
                table={gods}
                value={god}
                blocked={
                  GOD_TARGETS.has(motion) ? busy : 'This decision names no god'
                }
                onPick={setGod}
              />
              <EntityPicker
                types={['mortal']}
                value={hero}
                onChange={setHero}
                placeholder='Hero to bless'
              />
              <EntityPicker
                types={['world']}
                value={world}
                onChange={setWorld}
                placeholder='World it names'
              />
              <PickRow
                label='School of rites'
                table={SCHOOLS}
                value={school}
                blocked={
                  motion === 'outlaw_rite'
                    ? busy
                    : 'Only an outlaw names a school'
                }
                onPick={setSchool}
              />
              <PickRow
                label='Punishment'
                table={PUNISHMENTS}
                value={punishment}
                blocked={
                  motion === 'punish_son' ? busy : 'Only a punishment names one'
                }
                onPick={setPunishment}
              />
              <PickRow
                label='Deed of penance'
                table={PENANCE_DEEDS}
                value={deed}
                blocked={
                  motion === 'punish_son' && punishment === 'penance'
                    ? busy
                    : 'Only a penance names a deed'
                }
                onPick={setDeed}
              />
              <PickRow
                label='How the council decides'
                table={RULE_NAMES}
                value={rule}
                blocked={
                  motion === 'set_council_rules'
                    ? busy
                    : 'Only a change of council rules names one'
                }
                onPick={setRule}
              />
            </div>
            <Button
              act={decree}
              disabled={busy !== null || problem !== null}
              disabledReason={busy ?? problem ?? undefined}
              onClick={() => decree.mutate()}
            >
              <Gavel />
              Lay it down
            </Button>
          </Group>
        </div>
      )}
    </Section>
  )
}
