import { useState } from 'react'
import { Globe, Languages, Orbit, Plus, Route, Users } from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { VALUE_ICONS } from '@/features/entity/mind/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type ClimesNodeView, useClimesAction } from './api'
import {
  COMMUNITY_TYPES,
  LANGUAGE_TYPES,
  SPAN,
  SYNODIC_MAX,
  WORLD_KINDS,
  epochsToWindow,
  useClimesRow,
  useClimesStep,
} from './model'

type View = ClimesNodeView
type Window = View['windows'][number]
type Culture = View['cultures'][number]
type Member = Culture['members'][number]

const NO_ROAD = 'none'

function WindowCard({
  row,
  epoch,
  blocked,
}: {
  row: Window
  epoch: number
  blocked: string | null
}) {
  const action = useClimesRow(
    'launch_window:edit',
    'launch_window:delete',
    { from_world_id: row.from_world.id, to_world_id: row.to_world.id },
    blocked
  )
  const wait = epochsToWindow(row.synodic, row.offset, epoch)
  return (
    <Held
      icon={Orbit}
      tone={row.open ? 'success' : 'muted'}
      title={`${row.from_world.name} and ${row.to_world.name}`}
      caption={`Opens every ${plural(row.synodic, 'epoch', 'epochs')} · ${row.open ? 'open now' : wait === 0 ? 'opens this epoch' : `opens in ${plural(wait, 'epoch', 'epochs')}`}`}
      removeLabel='Forget the window'
      editTitle='Set the window'
      note='Physical ways between these worlds (sails, slingshots, void arks and cosmic mounts) open when the worlds come round to each other. A journey that leaves outside the window takes longer; gates, bridges and other divine ways ignore it.'
      fields={[
        {
          key: 'synodic',
          label: 'Epochs between windows',
          kind: 'number',
          min: 1,
          max: SYNODIC_MAX,
        },
        {
          key: 'offset',
          label: 'Offset of the cycle',
          kind: 'number',
          min: 0,
          max: SYNODIC_MAX,
        },
        { key: 'open', label: 'Open now', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <Badge size='sm' variant={row.open ? 'success' : 'secondary'}>
          {row.open ? 'Window open' : 'Window shut'}
        </Badge>
      }
    >
      <Facts
        items={[
          ['From', <Ref key='from' node={row.from_world} empty='no world' />],
          ['To', <Ref key='to' node={row.to_world} empty='no world' />],
        ]}
      />
      <Meter
        label={`Through the cycle (${row.synodic - wait} of ${row.synodic})`}
        value={row.synodic - wait}
        max={Math.max(1, row.synodic)}
        tone={row.open ? 'success' : 'info'}
        icon={Orbit}
      />
    </Held>
  )
}

function MemberCard({
  row,
  cultureId,
  blocked,
}: {
  row: Member
  cultureId: number
  blocked: string | null
}) {
  const action = useClimesRow(
    'cosmopolitan_member:edit',
    'cosmopolitan_member:delete',
    { culture_id: cultureId, community_id: row.community.id },
    blocked
  )
  return (
    <Held
      icon={Users}
      tone='verdigris'
      title={row.community.name}
      caption={`${row.share}% of its ways · joined in epoch ${row.joined_epoch}`}
      removeLabel='Take it out'
      editTitle='Set its share'
      note='The share grows while the road stays busy. It pulls the values of the member people toward the culture, and from the common-tongue mark the member speaks the tongue of the road.'
      fields={[
        {
          key: 'share',
          label: 'Share of its ways (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Share (${row.share} of ${SPAN})`}
        value={row.share}
        tone='info'
        icon={Users}
      />
    </Held>
  )
}

function CultureCard({
  row,
  blocked,
}: {
  row: Culture
  blocked: string | null
}) {
  const action = useClimesRow(
    'cosmopolitan_culture:edit',
    'cosmopolitan_culture:delete',
    { record_id: row.id },
    blocked
  )
  const [axis, setAxis] = useState('tradition')
  const [value, setValue] = useState('0')
  const valuing = useClimesAction(
    'cosmopolitan_culture:value',
    (_: void) => ({
      culture_id: row.id,
      axis: axis as Culture['values'][number]['axis'],
      value: Math.max(-SPAN, Math.min(SPAN, Number(value) || 0)),
    }),
    'The value is set'
  )
  const valueBusy = why(blocked, valuing.isPending)
  return (
    <Held
      icon={Route}
      tone='verdigris'
      title={row.name}
      caption={`${row.route ? row.route.name : 'No road'} · strength ${row.strength} · ${plural(row.members.length, 'member', 'members')} · formed in epoch ${row.formed_epoch}`}
      removeLabel='Let the culture fade'
      editTitle='Set the culture'
      note='The travellers of a busy road between worlds grow a culture of their own. Its values pull its member peoples toward them, and its common tongue spreads among its members.'
      fields={[
        { key: 'name', label: 'Name of the culture', kind: 'text' },
        {
          key: 'lingua_franca_entity_id',
          label: 'Common tongue',
          kind: 'node',
          types: LANGUAGE_TYPES,
        },
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          [
            'Common tongue',
            <Ref key='tongue' node={row.lingua_franca} empty='none yet' />,
          ],
          ['Road', row.route?.name ?? 'No road'],
        ]}
      />
      <Meter
        label={`Strength (${row.strength} of ${SPAN})`}
        value={row.strength}
        tone='success'
        icon={Route}
      />
      <Listed
        title='Values'
        items={[...row.values].sort(
          (left, right) => Math.abs(right.value) - Math.abs(left.value)
        )}
        empty='The culture holds no values of its own yet.'
        noun={['value', 'values']}
        itemKey={(item) => item.axis}
      >
        {(item) => {
          const named = VALUE_ICONS[item.axis]
          return (
            <Meter
              label={`${named?.label ?? item.axis} (${item.value > 0 ? '+' : ''}${item.value})`}
              value={Math.abs(item.value)}
              tone={item.value < 0 ? 'warning' : 'success'}
              icon={named?.icon}
            />
          )
        }}
      </Listed>
      <Listed
        title='Members'
        items={row.members}
        empty='No community belongs to it yet.'
        noun={['member', 'members']}
        itemKey={(item) => item.community.id}
      >
        {(item) => (
          <MemberCard row={item} cultureId={row.id} blocked={blocked} />
        )}
      </Listed>
      <ForgeCard
        icon={Languages}
        tone='info'
        title='Set one of its values'
        note='From -100 to 100; a value you set stays as you set it.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={valueBusy !== null}
            disabledReason={valueBusy ?? undefined}
            onClick={() => valuing.mutate()}
          >
            <Plus />
            Set the value
          </Button>
        }
      >
        <MindPicker
          label='Value'
          value={axis}
          table={table(VALUE_ICONS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setAxis}
        />
        <NumberField
          label='Weight (-100 to 100)'
          value={value}
          min={-SPAN}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setValue}
        />
      </ForgeCard>
    </Held>
  )
}

export function CrossingsPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: View
  blocked: string | null
}) {
  const worldId = data.world?.id ?? null
  const community = (COMMUNITY_TYPES as readonly string[]).includes(kind ?? '')
  const [other, setOther] = useState<number | null>(null)
  const [route, setRoute] = useState(
    data.routes[0] ? String(data.routes[0].id) : NO_ROAD
  )
  const [name, setName] = useState('')
  const [tongue, setTongue] = useState<number | null>(null)
  const [culture, setCulture] = useState(
    data.cultures[0] ? String(data.cultures[0].id) : ''
  )
  const [member, setMember] = useState<number | null>(community ? nodeId : null)
  const opening = useClimesAction(
    'launch_window:set',
    (_: void) => ({ from_world_id: worldId ?? 0, to_world_id: other ?? 0 }),
    'The window is set'
  )
  const founding = useClimesAction(
    'cosmopolitan_culture:create',
    (_: void) => ({
      route_id: route === NO_ROAD ? null : Number(route),
      name: name.trim(),
      lingua_franca_entity_id: tongue,
    }),
    'A culture of the road is founded'
  )
  const joining = useClimesAction(
    'cosmopolitan_member:set',
    (_: void) => ({ culture_id: Number(culture), community_id: member ?? 0 }),
    'It joins the culture'
  )
  const reading = useClimesStep(
    'crossings:run',
    blocked,
    'The crossings are read'
  )
  const noWorld =
    worldId === null ? 'Only a thing on a world has crossings' : null
  const windowBusy = why(
    blocked ??
      noWorld ??
      (other === null
        ? 'Choose the other world'
        : other === worldId
          ? 'A window opens between two different worlds'
          : data.windows.some(
                (row) =>
                  row.from_world.id === other || row.to_world.id === other
              )
            ? 'That window is set already; adjust it above'
            : null),
    opening.isPending
  )
  const foundBusy = why(
    blocked ?? (!name.trim() ? 'Name the culture' : null),
    founding.isPending
  )
  const joinBusy = why(
    blocked ??
      (!culture
        ? 'No culture of a road touches this yet; found one first'
        : member === null
          ? 'Choose the community'
          : data.cultures
                .find((row) => String(row.id) === culture)
                ?.members.some((row) => row.community.id === member)
            ? 'It belongs to that culture already; adjust it above'
            : null),
    joining.isPending
  )
  const routeTable = Object.fromEntries([
    [NO_ROAD, 'No road'],
    ...data.routes.map((row) => [String(row.id), row.name]),
  ])
  const cultureTable = Object.fromEntries(
    data.cultures.map((row) => [String(row.id), row.name])
  )
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <div
        data-surface='CrossingsPanel'
        className='flex min-w-0 flex-col gap-4'
      >
        <Bars
          chart='chart-windows'
          title='Windows between worlds'
          legend={[
            { text: 'Open', variant: 'success' },
            { text: 'Through the cycle', variant: 'secondary' },
          ]}
          rows={data.windows.map((row) => {
            const wait = epochsToWindow(row.synodic, row.offset, data.epoch)
            return {
              key: `${row.from_world.id}-${row.to_world.id}`,
              caption: `${row.from_world.name} and ${row.to_world.name}: ${row.open ? 'open' : `opens in ${plural(wait, 'epoch', 'epochs')}`}`,
              segments: [
                {
                  value: row.synodic - wait,
                  fill: row.open ? 'fill-success' : 'fill-info',
                },
              ],
            }
          })}
          max={Math.max(1, ...data.windows.map((row) => row.synodic))}
          noun={['window', 'windows']}
          empty='No physical way joins this world to another.'
        />
        <Listed
          title='Launch windows'
          items={data.windows}
          empty='No physical way joins this world to another.'
          noun={['window', 'windows']}
          itemKey={(item) => `${item.from_world.id}-${item.to_world.id}`}
        >
          {(item) => (
            <WindowCard row={item} epoch={data.epoch} blocked={blocked} />
          )}
        </Listed>
        <ForgeCard
          icon={Globe}
          tone='info'
          title='Set a window to another world'
          note='How often the window between this world and another opens for physical ways of travel.'
          columns={2}
          action={
            <div className='flex min-w-0 flex-wrap gap-2'>
              <StepButton
                icon={Orbit}
                label='Read the crossings now'
                busy={reading.busy}
                onClick={reading.run}
              />
              <Button
                size='sm'
                disabled={windowBusy !== null}
                disabledReason={windowBusy ?? undefined}
                onClick={() => opening.mutate()}
              >
                <Plus />
                Set the window
              </Button>
            </div>
          }
        >
          <NodePicker
            label='Other world'
            value={other}
            onChange={setOther}
            blocked={blocked}
            kinds={WORLD_KINDS}
          />
        </ForgeCard>
      </div>
      <div
        data-surface='RoadCulturesPanel'
        className='flex min-w-0 flex-col gap-4'
      >
        <Bars
          chart='chart-road-cultures'
          title='Cultures of the roads and their members'
          legend={[{ text: 'Share of members', variant: 'success' }]}
          rows={data.cultures.map((row) => ({
            key: String(row.id),
            caption: `${row.name}: ${plural(row.members.length, 'member', 'members')}, strength ${row.strength}`,
            segments: row.members.map((item) => ({
              value: item.share,
              fill: 'fill-success',
            })),
          }))}
          noun={['culture', 'cultures']}
          empty='No culture of a road touches this.'
        />
        <Listed
          title='Cultures of the roads'
          items={data.cultures}
          empty='No culture of a road touches this.'
          noun={['culture', 'cultures']}
          itemKey={(item) => item.id}
        >
          {(item) => <CultureCard row={item} blocked={blocked} />}
        </Listed>
        <ForgeCard
          icon={Route}
          tone='verdigris'
          title='Found a culture of a road'
          note='A culture shared by the travellers and towns of a road between worlds.'
          columns={3}
          action={
            <Button
              size='sm'
              disabled={foundBusy !== null}
              disabledReason={foundBusy ?? undefined}
              onClick={() => founding.mutate()}
            >
              <Plus />
              Found it
            </Button>
          }
        >
          <TextField
            label='Name of the culture'
            value={name}
            blocked={blocked}
            onChange={setName}
          />
          <MindPicker
            label='Road'
            value={route}
            table={routeTable}
            placeholder='Choose'
            blocked={blocked}
            onPick={setRoute}
          />
          <NodePicker
            label='Common tongue'
            value={tongue}
            onChange={setTongue}
            blocked={blocked}
            types={LANGUAGE_TYPES}
          />
        </ForgeCard>
        <ForgeCard
          icon={Users}
          tone='success'
          title='Bring a community into a culture'
          note='A town, people, guild or cult takes up a share of the ways of a culture of a road.'
          columns={2}
          action={
            <Button
              size='sm'
              disabled={joinBusy !== null}
              disabledReason={joinBusy ?? undefined}
              onClick={() => joining.mutate()}
            >
              <Plus />
              Bring it in
            </Button>
          }
        >
          <MindPicker
            label='Culture of a road'
            value={culture}
            table={cultureTable}
            placeholder='Choose'
            blocked={blocked}
            onPick={setCulture}
          />
          <NodePicker
            label='Community'
            value={member}
            onChange={setMember}
            blocked={blocked}
            types={COMMUNITY_TYPES}
          />
        </ForgeCard>
      </div>
    </div>
  )
}
