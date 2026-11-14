import { useState } from 'react'
import { Gem, Link, Plus, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { SCHOOLS } from '@/features/entity/lore/model'
import { EMOTION_ICONS } from '@/features/entity/mind/feelingLabels'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type CraftsNodeView, useCraftsAction } from './api'
import { MODES, TOKENS } from './labels'
import { MANY, MORTAL_TYPES, SPAN, useCraftsRow, useCraftsStep } from './model'

type View = CraftsNodeView
type Affinity = View['affinities'][number]
type LinkRow = View['links'][number]
type Spirit = View['spirits'][number]

function AffinityCard({
  row,
  blocked,
}: {
  row: Affinity
  blocked: string | null
}) {
  const action = useCraftsRow(
    'material_affinity:edit',
    'material_affinity:delete',
    { material_id: row.material_id, school: row.school },
    blocked
  )
  const school = SCHOOLS[row.school]
  return (
    <Held
      icon={school.icon}
      tone={school.tone}
      title={`${row.material}: ${school.label}`}
      caption={`${MODES[row.mode].label} · power ${row.power}`}
      removeLabel='Strike the affinity'
      editTitle='Set the affinity'
      note='Rites of the school worked near the material grow stronger, and more so for the gifted when it is consumed; mining it is worth more.'
      fields={[
        {
          key: 'mode',
          label: 'Used by being',
          kind: 'pick',
          table: table(MODES),
        },
        { key: 'power', label: 'Power', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Power (${row.power} of ${SPAN})`}
        value={row.power}
        tone='warning'
        icon={Gem}
      />
    </Held>
  )
}

function LinkCard({ row, blocked }: { row: LinkRow; blocked: string | null }) {
  const action = useCraftsRow(
    'sympathetic_link:edit',
    'sympathetic_link:delete',
    { record_id: row.id },
    blocked
  )
  const token = TOKENS[row.token]
  return (
    <Held
      icon={token.icon}
      tone={token.tone}
      title={`${token.label} of ${row.target.name}`}
      caption={`Held by ${row.holder.name} · strength ${row.strength} · taken in epoch ${row.obtained_epoch}`}
      removeLabel='Break the link'
      editTitle='Set the link'
      note='A rite worked through a link grows stronger and reaches its target from afar; links fade, the cursed burn what could link to them, and a link held by the accused is evidence of magic.'
      fields={[
        { key: 'token', label: 'Token', kind: 'pick', table: table(TOKENS) },
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'obtained_epoch',
          label: 'Taken in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Holder', <Ref key='holder' node={row.holder} empty='no one' />],
          ['Target', <Ref key='target' node={row.target} empty='no one' />],
        ]}
      />
    </Held>
  )
}

function SpiritCard({ row, blocked }: { row: Spirit; blocked: string | null }) {
  const action = useCraftsRow(
    'emotion_spirit:edit',
    'emotion_spirit:delete',
    { record_id: row.id },
    blocked
  )
  const feeling = EMOTION_ICONS[row.emotion]
  return (
    <Held
      icon={feeling?.icon ?? Sparkles}
      tone={feeling?.tone ?? 'verdigris'}
      title={`A spirit of ${feeling?.label.toLowerCase() ?? row.emotion}`}
      caption={`Strength ${row.strength} · ${row.bound_by ? `bound by ${row.bound_by.name}` : `lasts ${row.lifetime} more`} · born in epoch ${row.born_epoch}`}
      removeLabel='Disperse the spirit'
      editTitle='Set the spirit'
      note='The spirit deepens its feeling in the folk of its land, feeds the gods they worship and is read as an omen; a binding rite holds it, and a bound spirit yields reagents to its binder.'
      fields={[
        {
          key: 'emotion',
          label: 'Feeling',
          kind: 'pick',
          table: table(EMOTION_ICONS),
        },
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'lifetime',
          label: 'Epochs left',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'bound_by_node_id',
          label: 'Bound by',
          kind: 'node',
          types: MORTAL_TYPES,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Land', <Ref key='land' node={row.region} empty='no land' />],
          ['Bound by', <Ref key='binder' node={row.bound_by} empty='no one' />],
        ]}
      />
    </Held>
  )
}

export function ArcanePanel({
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
  const mortal = kind === 'mortal'
  const land = kind === 'region' ? nodeId : (data.region?.id ?? null)
  const [material, setMaterial] = useState(
    data.materials[0] ? String(data.materials[0].id) : ''
  )
  const [school, setSchool] = useState('earth')
  const [mode, setMode] = useState('worn')
  const [target, setTarget] = useState<number | null>(null)
  const [token, setToken] = useState('hair')
  const [emotion, setEmotion] = useState('joy')
  const laying = useCraftsAction(
    'material_affinity:set',
    (_: void) => ({
      material_id: Number(material || '0'),
      school: school as Affinity['school'],
      mode: mode as Affinity['mode'],
    }),
    'The material carries the affinity'
  )
  const linking = useCraftsAction(
    'sympathetic_link:create',
    (_: void) => ({
      holder_node_id: nodeId,
      target_node_id: target ?? 0,
      token: token as LinkRow['token'],
    }),
    'The link is made'
  )
  const waking = useCraftsAction(
    'emotion_spirit:create',
    (_: void) => ({
      region_entity_id: land ?? 0,
      emotion: emotion as Spirit['emotion'],
    }),
    'The spirit takes shape'
  )
  const reading = useCraftsStep(
    'sympathies:run',
    {},
    blocked,
    'Affinities, links and spirits are read'
  )
  const affinityBusy = why(
    blocked ?? (!material ? 'Its world holds no materials of its own' : null),
    laying.isPending
  )
  const linkBusy = why(
    blocked ??
      (!mortal
        ? 'Only a mortal holds a link'
        : target === null
          ? 'Choose whom it links to'
          : target === nodeId
            ? 'It cannot link to itself'
            : null),
    linking.isPending
  )
  const spiritBusy = why(
    blocked ?? (land === null ? 'It lies in no land' : null),
    waking.isPending
  )
  return (
    <div data-surface='ArcanePanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-sympathy'
        title='Affinities and links'
        legend={[
          { text: 'Affinity power', variant: 'warning' },
          { text: 'Link strength', variant: 'destructive' },
        ]}
        rows={[
          ...data.affinities.map((row) => ({
            key: `a${row.material_id}-${row.school}`,
            caption: `${row.material}, ${SCHOOLS[row.school].label}: power ${row.power}`,
            segments: [
              { value: Math.min(SPAN, row.power), fill: 'fill-warning' },
            ],
          })),
          ...data.links.map((row) => ({
            key: `l${row.id}`,
            caption: `${TOKENS[row.token].label} of ${row.target.name}: strength ${row.strength}`,
            segments: [
              { value: Math.min(SPAN, row.strength), fill: 'fill-destructive' },
            ],
          })),
        ]}
        max={SPAN}
        noun={['bond of magic', 'bonds of magic']}
        empty='No affinity or link touches this.'
      />
      <Listed
        title='Magical affinities of materials'
        items={data.affinities}
        empty='No material here carries an affinity.'
        noun={['affinity', 'affinities']}
        itemKey={(item) => `${item.material_id}-${item.school}`}
      >
        {(item) => <AffinityCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Sympathetic links'
        items={data.links}
        empty='No link binds this.'
        noun={['link', 'links']}
        itemKey={(item) => item.id}
      >
        {(item) => <LinkCard row={item} blocked={blocked} />}
      </Listed>
      <Bars
        chart='chart-spirits'
        title='Spirits of feeling'
        legend={[{ text: 'Strength', variant: 'success' }]}
        rows={data.spirits.map((row) => ({
          key: String(row.id),
          caption: `${EMOTION_ICONS[row.emotion]?.label ?? row.emotion} in ${row.region.name}: strength ${row.strength}`,
          segments: [
            { value: Math.min(SPAN, row.strength), fill: 'fill-success' },
          ],
        }))}
        max={SPAN}
        noun={['spirit', 'spirits']}
        empty='No spirit of feeling haunts this land.'
      />
      <Listed
        title='Spirits of feeling'
        items={data.spirits}
        empty='No spirit of feeling haunts this land.'
        noun={['spirit', 'spirits']}
        itemKey={(item) => item.id}
      >
        {(item) => <SpiritCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Sparkles}
        tone='verdigris'
        title='Lay magic'
        note='Give a material of its world an affinity, let a mortal hold a link to another, or give a feeling of its land a spirit.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Sparkles}
              label='Read affinities, links and spirits now'
              busy={reading.busy}
              onClick={reading.run}
            />
            <Button
              size='sm'
              variant='outline'
              disabled={affinityBusy !== null}
              disabledReason={affinityBusy ?? undefined}
              onClick={() => laying.mutate()}
            >
              <Gem />
              Lay the affinity
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={linkBusy !== null}
              disabledReason={linkBusy ?? undefined}
              onClick={() => linking.mutate()}
            >
              <Link />
              Make the link
            </Button>
            <Button
              size='sm'
              disabled={spiritBusy !== null}
              disabledReason={spiritBusy ?? undefined}
              onClick={() => waking.mutate()}
            >
              <Plus />
              Wake the spirit
            </Button>
          </div>
        }
      >
        <MindPicker
          label='Material'
          value={material}
          table={Object.fromEntries(
            data.materials.map((row) => [String(row.id), row.name])
          )}
          placeholder={
            data.materials.length ? 'Choose' : 'No material of its own'
          }
          blocked={blocked}
          onPick={setMaterial}
        />
        <MindPicker
          label='School'
          value={school}
          table={table(SCHOOLS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setSchool}
        />
        <MindPicker
          label='Used by being'
          value={mode}
          table={table(MODES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setMode}
        />
        <NodePicker
          label='Linked to'
          value={target}
          onChange={setTarget}
          blocked={blocked}
          types={MORTAL_TYPES}
        />
        <MindPicker
          label='Token'
          value={token}
          table={table(TOKENS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setToken}
        />
        <MindPicker
          label='Feeling'
          value={emotion}
          table={table(EMOTION_ICONS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setEmotion}
        />
      </ForgeCard>
    </div>
  )
}
