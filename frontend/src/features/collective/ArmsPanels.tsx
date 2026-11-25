import { useState } from 'react'
import { Copy, Dices, Quote, Shield } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Label, Muted, Text } from '@/components/typography'
import { Chip, Facts, ForgeCard } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { useKinds } from '@/features/kinds/api'
import { ArmsShield } from './ArmsShield'
import {
  type ArmsDesign,
  type ArmsView,
  rollArms,
  useArmsPreview,
  useCollectiveAction,
} from './api'
import {
  ARRANGEMENTS,
  BEARERS,
  CHARGES,
  DIVISIONS,
  LINES,
  POSES,
  RIMS,
  SHAPES,
  TINCTURES,
} from './labels'
import { useRow } from './model'
import { Held, type Field } from './parts'

type Tincture = keyof typeof TINCTURES
const AUTOMATIC = 'none'
const TINCTURE_PICK: Record<string, string> = {
  [AUTOMATIC]: 'Automatic contrast',
  ...TINCTURES,
}
const BEARER_TYPES: Record<string, keyof typeof BEARERS> = {
  house: 'house',
  polity: 'polity',
  title: 'title',
  army: 'army',
  faction: 'guild',
}
const ROLLS = 1_000_000

const GROUPS: {
  title: string
  fields: {
    key: keyof ArmsDesign
    label: string
    table: Record<string, string>
  }[]
}[] = [
  {
    title: 'The field',
    fields: [
      { key: 'shape', label: 'Shield shape', table: SHAPES },
      { key: 'field', label: 'Field tincture', table: TINCTURES },
      { key: 'division', label: 'Division', table: DIVISIONS },
      { key: 'line', label: 'Line of the division', table: LINES },
      { key: 'second', label: 'Second tincture', table: TINCTURE_PICK },
    ],
  },
  {
    title: 'The charges',
    fields: [
      { key: 'charge', label: 'First charge', table: CHARGES },
      {
        key: 'charge_tincture',
        label: 'First charge tincture',
        table: TINCTURE_PICK,
      },
      { key: 'charge_two', label: 'Second charge', table: CHARGES },
      {
        key: 'charge_two_tincture',
        label: 'Second charge tincture',
        table: TINCTURE_PICK,
      },
      { key: 'charge_three', label: 'Third charge', table: CHARGES },
      {
        key: 'charge_three_tincture',
        label: 'Third charge tincture',
        table: TINCTURE_PICK,
      },
      { key: 'arrangement', label: 'Arrangement', table: ARRANGEMENTS },
    ],
  },
  {
    title: 'Around the shield',
    fields: [
      { key: 'rim', label: 'Rim', table: RIMS },
      { key: 'rim_line', label: 'Edge of the shield', table: LINES },
      { key: 'rim_tincture', label: 'Rim tincture', table: TINCTURE_PICK },
      { key: 'supporter', label: 'Supporters', table: CHARGES },
      { key: 'supporter_pose', label: 'Supporters’ pose', table: POSES },
      {
        key: 'supporter_tincture',
        label: 'Supporters’ tincture',
        table: TINCTURE_PICK,
      },
      { key: 'crest', label: 'Crest', table: CHARGES },
      { key: 'crest_tincture', label: 'Crest tincture', table: TINCTURE_PICK },
    ],
  },
]

const STARTING: ArmsDesign = {
  shape: 'heater',
  field: 'blue',
  division: 'plain',
  line: 'straight',
  second: null,
  charge: 'star',
  charge_tincture: 'gold',
  charge_two: 'none',
  charge_two_tincture: null,
  charge_three: 'none',
  charge_three_tincture: null,
  arrangement: 'two_and_one',
  rim: 'line',
  rim_line: 'straight',
  rim_tincture: null,
  supporter: 'none',
  supporter_pose: 'crossed',
  supporter_tincture: null,
  crest: 'none',
  crest_tincture: null,
}

function tinctureText(value: Tincture | null) {
  return value ? TINCTURES[value] : 'automatic contrast'
}

function chargeText(charge: keyof typeof CHARGES, tincture: Tincture | null) {
  return charge === 'none'
    ? 'none'
    : `${CHARGES[charge]}, ${tinctureText(tincture)}`
}

function designOf(row: ArmsDesign): ArmsDesign {
  return {
    shape: row.shape,
    field: row.field,
    division: row.division,
    line: row.line,
    second: row.second,
    charge: row.charge,
    charge_tincture: row.charge_tincture,
    charge_two: row.charge_two,
    charge_two_tincture: row.charge_two_tincture,
    charge_three: row.charge_three,
    charge_three_tincture: row.charge_three_tincture,
    arrangement: row.arrangement,
    rim: row.rim,
    rim_line: row.rim_line,
    rim_tincture: row.rim_tincture,
    supporter: row.supporter,
    supporter_pose: row.supporter_pose,
    supporter_tincture: row.supporter_tincture,
    crest: row.crest,
    crest_tincture: row.crest_tincture,
  }
}

export function ArmsFacts({ row }: { row: ArmsDesign }) {
  const groups: [string, [string, string][]][] = [
    [
      'The field',
      [
        ['Shield shape', SHAPES[row.shape]],
        ['Field tincture', TINCTURES[row.field]],
        ['Division', DIVISIONS[row.division]],
        ['Line of the division', LINES[row.line]],
        [
          'Second tincture',
          row.division === 'plain' ? 'a plain field' : tinctureText(row.second),
        ],
      ],
    ],
    [
      'The charges',
      [
        ['First charge', chargeText(row.charge, row.charge_tincture)],
        ['Second charge', chargeText(row.charge_two, row.charge_two_tincture)],
        [
          'Third charge',
          chargeText(row.charge_three, row.charge_three_tincture),
        ],
        ['Arrangement', ARRANGEMENTS[row.arrangement]],
      ],
    ],
    [
      'Around the shield',
      [
        [
          'Rim',
          row.rim === 'line'
            ? RIMS[row.rim]
            : `${RIMS[row.rim]}, ${tinctureText(row.rim_tincture)}`,
        ],
        ['Edge of the shield', LINES[row.rim_line]],
        ['Supporters', chargeText(row.supporter, row.supporter_tincture)],
        [
          'Supporters’ pose',
          row.supporter === 'none'
            ? 'no supporters'
            : POSES[row.supporter_pose],
        ],
        ['Crest', chargeText(row.crest, row.crest_tincture)],
      ],
    ],
  ]
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {groups.map(([title, items]) => (
        <div key={title} className='flex min-w-0 flex-col gap-1'>
          <Label variant='overline'>{title}</Label>
          <Facts items={items} />
        </div>
      ))}
    </div>
  )
}

export function Motto({ motto }: { motto: string | null }) {
  return motto ? (
    <div className='flex min-w-0 items-center gap-2'>
      <Quote
        className='size-icon-sm shrink-0 text-muted-foreground'
        aria-hidden='true'
      />
      <Text>{motto}</Text>
    </div>
  ) : (
    <Muted variant='caption'>These arms carry no words.</Muted>
  )
}

const EDITOR_FIELDS: Field[] = [
  ...GROUPS.flatMap((group) =>
    group.fields.map((field): Field => ({
      key: field.key,
      label: field.label,
      kind: 'pick',
      table: field.table,
    }))
  ),
  { key: 'motto', label: 'Motto', kind: 'text' },
]

function useEmblemSystems() {
  const systems = useKinds('emblem_system', null)
  return {
    none: 'No system of emblems',
    ...Object.fromEntries(
      (systems.data ?? []).map((system) => [String(system.id), system.name])
    ),
  }
}

function useRoll(holderId: number) {
  const [rolling, setRolling] = useState(false)
  const roll = async (apply: (design: ArmsDesign) => void) => {
    setRolling(true)
    try {
      apply(
        designOf(
          await rollArms(holderId, 1 + Math.floor(Math.random() * ROLLS))
        )
      )
    } catch {
      toast.error('The dice could not be cast')
    } finally {
      setRolling(false)
    }
  }
  return { rolling, roll }
}

export function ArmsCard({
  holderId,
  row,
  label,
  blocked,
}: {
  holderId: number
  row: ArmsView
  label: string
  blocked: string | null
}) {
  const action = useRow(
    'arms:edit',
    'arms:delete',
    { holder_id: holderId },
    blocked
  )
  const [other, setOther] = useState<number | null>(null)
  const quartering = useCollectiveAction(
    'arms:quarter',
    (_: void) => ({ holder_id: holderId, other_id: other ?? 0 }),
    'The arms are quartered'
  )
  const dice = useRoll(holderId)
  const systems = useEmblemSystems()
  const busy = why(action.busy, quartering.isPending, dice.rolling)
  const bearer = BEARERS[row.holder_kind]
  return (
    <Held
      icon={Shield}
      tone='gold'
      title={`Arms of ${label}`}
      caption={`${bearer.label} has borne these arms since epoch ${row.since_epoch}`}
      removeLabel='Grant them anew'
      editTitle='Set the arms'
      note='Every part of the arms can be set here. A tincture left on automatic contrast is chosen to stand out from what lies beneath it.'
      fields={[
        ...EDITOR_FIELDS,
        {
          key: 'emblem_system_id',
          label: 'System of emblems',
          kind: 'pick',
          table: systems,
        },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Chip icon={bearer.icon}>{bearer.label}</Chip>}
    >
      <div className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start'>
        <ArmsShield
          drawing={row.drawing}
          label={`Arms of ${label}`}
          size='xl'
        />
        <div className='flex min-w-0 flex-1 flex-col gap-3'>
          <Text weight='semibold'>{row.blazon}</Text>
          <Motto motto={row.motto} />
          <ArmsFacts row={row} />
          <Facts
            items={[
              [
                'Differenced from',
                <Ref key='parent' node={row.parent} empty='no parent' />,
              ],
              [
                'Quartered with',
                <Ref key='quartered' node={row.quartered} empty='no one' />,
              ],
            ]}
          />
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() =>
            void dice.roll((design) =>
              action.onEdit({ values: design, release: [] })
            )
          }
        >
          <Dices />
          Reforge at random
        </Button>
        <NodePicker
          label='Quarter with'
          value={other}
          onChange={setOther}
          blocked={busy}
          types={['house', 'polity']}
        />
        <Button
          act={quartering}
          size='sm'
          variant='outline'
          disabled={
            (other === null ? 'Choose whose arms to quarter with' : busy) !==
            null
          }
          disabledReason={
            other === null
              ? 'Choose whose arms to quarter with'
              : (busy ?? undefined)
          }
          onClick={() => quartering.mutate()}
        >
          <Copy />
          Quarter them
        </Button>
      </div>
    </Held>
  )
}

export function ArmsForge({
  holderId,
  type,
  blocked,
}: {
  holderId: number
  type: string | null
  blocked: string | null
}) {
  const [design, setDesign] = useState<ArmsDesign>(STARTING)
  const [parent, setParent] = useState<number | null>(null)
  const preview = useArmsPreview(design)
  const dice = useRoll(holderId)
  const bearer = type ? BEARER_TYPES[type] : undefined
  const granting = useCollectiveAction(
    'arms:set',
    (_: void) => ({
      holder_id: holderId,
      holder_kind: bearer ?? 'house',
      ...design,
    }),
    'The arms are granted'
  )
  const differencing = useCollectiveAction(
    'arms:difference',
    (_: void) => ({
      holder_id: holderId,
      parent_id: parent ?? 0,
      border: design.second ?? 'silver',
      line: design.line,
    }),
    'The cadet arms are drawn'
  )
  const wrong =
    bearer === undefined
      ? 'Only houses, realms, titles, armies and associations bear arms'
      : null
  const busy = why(
    wrong ?? blocked,
    granting.isPending,
    differencing.isPending,
    dice.rolling
  )
  const pick = (key: keyof ArmsDesign) => (value: string) =>
    setDesign((current) => ({
      ...current,
      [key]: value === AUTOMATIC && key.endsWith('tincture') ? null : value,
    }))
  const shown = (key: keyof ArmsDesign) => {
    const value = design[key]
    return value === null ? AUTOMATIC : String(value)
  }
  return (
    <ForgeCard
      icon={Shield}
      tone='gold'
      title='Grant arms'
      note='Shape the shield, part its field, place up to three charges and dress it with a rim, supporters and a crest, or cast the dice for arms drawn from this holder’s values.'
      columns={3}
      meta={
        <div className='flex min-w-0 items-center gap-3'>
          {preview.data ? (
            <ArmsShield
              drawing={preview.data.drawing}
              label='The arms as drawn'
              size='xl'
            />
          ) : (
            <Muted variant='caption'>
              {preview.isError
                ? 'The arms could not be drawn'
                : 'Drawing the arms'}
            </Muted>
          )}
          {preview.data && <Text weight='semibold'>{preview.data.blazon}</Text>}
        </div>
      }
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            act={granting}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => granting.mutate()}
          >
            <Shield />
            Grant them
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => void dice.roll(setDesign)}
          >
            <Dices />
            Cast the dice
          </Button>
          <Button
            act={differencing}
            size='sm'
            variant='outline'
            disabled={
              (parent === null
                ? 'Choose the parent whose arms to bear'
                : busy) !== null
            }
            disabledReason={
              parent === null
                ? 'Choose the parent whose arms to bear'
                : (busy ?? undefined)
            }
            onClick={() => differencing.mutate()}
          >
            <Copy />
            Bear the parent’s within a border
          </Button>
        </div>
      }
    >
      {GROUPS.map((group) => [
        <div key={group.title} className='col-span-full'>
          <Label variant='overline'>{group.title}</Label>
        </div>,
        ...group.fields.map((field) => (
          <MindPicker
            key={field.key}
            label={field.label}
            value={shown(field.key)}
            table={field.table}
            blocked={busy}
            onPick={pick(field.key)}
          />
        )),
      ])}
      <NodePicker
        label='Parent'
        value={parent}
        onChange={setParent}
        blocked={busy}
        types={['house', 'polity']}
      />
    </ForgeCard>
  )
}
