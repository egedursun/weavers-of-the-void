import { useState } from 'react'
import { PenLine } from 'lucide-react'
import {
  domainValues,
  existenceModeValues,
  foreignGodPowerEffectValues,
  foreignGodStatusValues,
} from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { FormRow, Section, FieldTile } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { type Domain } from '@/features/pantheon/api'
import { RELATION_SCALE, STAT_SCALE } from '@/features/pantheon/constants'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  FOREIGN_STATUS_LABEL,
  STATS,
  useLabels,
} from '@/features/pantheon/labels'
import {
  FOREIGN_EFFECT_LABEL,
  type ForeignEditBody,
  type ForeignGodDetail,
  type ForeignPowerEffect,
  editForeignGod,
} from './api'

const NONE = 'none'

type PowerRow = {
  name: string
  effect: ForeignPowerEffect | ''
  description: string
}

const PERSONALITY_FIELDS = [
  ['appearance', 'Appearance'],
  ['temperament', 'Temperament'],
  ['obsession', 'Obsession'],
  ['fear', 'Fear'],
  ['speech_style', 'Speech'],
  ['secret', 'Secret'],
] as const

const DEPTH_TEXTS = [
  ['history', 'History'],
  ['desire', 'Wish'],
  ['view_of_pantheon', 'View of the pantheon'],
  ['worship', 'Worship'],
  ['hidden_truth', 'Hidden truth'],
] as const

const DEPTH_LISTS = [
  ['secrets', 'Secrets'],
  ['fears', 'Fears'],
  ['taboos', 'Prohibitions'],
  ['gifts', 'Gifts'],
  ['rumours', 'Rumours'],
] as const

function lines(text: string): string[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

function useEdit(godId: number, name: string) {
  return useGodAction({
    run: (body: ForeignEditBody) => editForeignGod(godId, body),
    success: `${name} was edited`,
  })
}

function DomainSelect({
  id,
  value,
  onChange,
  optional,
}: {
  id: string
  value: string
  onChange: (value: string) => void
  optional?: boolean
}) {
  const { domain } = useLabels()
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className='w-48'>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {optional && <SelectItem value={NONE}>None</SelectItem>}
        {domainValues.map((item) => (
          <SelectItem key={item} value={item}>
            {domain(item)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export function ForeignGodEditForm({ detail }: { detail: ForeignGodDetail }) {
  const god = detail.god
  const { reason } = useGodGate()
  const save = useEdit(god.id, god.name)
  const [name, setName] = useState(god.name)
  const [title, setTitle] = useState(god.title ?? '')
  const [primary, setPrimary] = useState<string>(god.domain_primary)
  const [secondary, setSecondary] = useState<string>(
    god.domain_secondary ?? NONE
  )
  const [stance, setStance] = useState(String(god.stance))
  const [power, setPower] = useState(String(god.power))
  const [status, setStatus] = useState(god.status)
  const [contacted, setContacted] = useState(god.contacted)
  const [description, setDescription] = useState(god.description ?? '')
  const [prompt, setPrompt] = useState(god.image_prompt ?? '')
  const [stats, setStats] = useState<Record<string, number>>(
    Object.fromEntries(STATS.map((stat) => [stat.key, god[stat.key]]))
  )
  const [powers, setPowers] = useState<PowerRow[]>(
    detail.powers.map((item) => ({
      name: item.name,
      effect: item.effect as ForeignPowerEffect,
      description: item.description,
    }))
  )
  const [personality, setPersonality] = useState<Record<string, string>>(
    Object.fromEntries(
      PERSONALITY_FIELDS.map(([key]) => [key, god.personality?.[key] ?? ''])
    )
  )
  const [mode, setMode] = useState<string>(god.existence_profile?.mode ?? NONE)
  const [nature, setNature] = useState(god.existence_profile?.nature ?? '')
  const [manifestation, setManifestation] = useState(
    god.existence_profile?.manifestation ?? ''
  )
  const [trueName, setTrueName] = useState(
    god.existence_profile?.true_name ?? ''
  )
  const [depthTexts, setDepthTexts] = useState<Record<string, string>>(
    Object.fromEntries(
      DEPTH_TEXTS.map(([key]) => [key, god.depth?.[key] ?? ''])
    )
  )
  const [depthLists, setDepthLists] = useState<Record<string, string>>(
    Object.fromEntries(
      DEPTH_LISTS.map(([key]) => [key, (god.depth?.[key] ?? []).join('\n')])
    )
  )
  const rows: PowerRow[] = [
    ...powers,
    { name: '', effect: '', description: '' },
  ]
  const updateRow = (index: number, patch: Partial<PowerRow>) => {
    const next = [...rows]
    next[index] = { ...next[index], ...patch }
    const trailing = next[next.length - 1]
    setPowers(
      trailing.name || trailing.effect || trailing.description
        ? next
        : next.slice(0, -1)
    )
  }
  const saveMain = () =>
    save.mutate({
      name: name.trim(),
      title: title.trim(),
      domain_primary: primary as Domain,
      domain_secondary: secondary === NONE ? null : (secondary as Domain),
      stance: Number(stance),
      power: Number(power),
      status,
      contacted,
      description,
      image_prompt: prompt,
    })
  const saveTraits = () =>
    save.mutate({
      stats,
      powers: powers
        .filter((row) => row.name.trim() && row.effect)
        .map((row) => ({
          name: row.name.trim(),
          effect: row.effect as ForeignPowerEffect,
          description: row.description,
        })),
      personality,
      existence: {
        mode:
          mode === NONE ? null : (mode as (typeof existenceModeValues)[number]),
        nature,
        manifestation,
        true_name: trueName,
      },
      depth: god.depth
        ? {
            ...Object.fromEntries(
              DEPTH_TEXTS.map(([key]) => [key, depthTexts[key]])
            ),
            ...Object.fromEntries(
              DEPTH_LISTS.map(([key]) => [key, lines(depthLists[key])])
            ),
          }
        : undefined,
    })
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Collapsible className='flex min-w-0 flex-col gap-3'>
        <CollapsibleTrigger asChild>
          <Button variant='outline' className='self-start'>
            <PenLine />
            Edit name, title, attitude, power and status
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <Section title={`Edit ${god.name}`} surface='card' level={3}>
            <FormRow label='Name'>
              {(id) => (
                <Input
                  id={id}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              )}
            </FormRow>
            <FormRow label='Title'>
              {(id) => (
                <Input
                  id={id}
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                />
              )}
            </FormRow>
            <FormRow label='First domain'>
              {(id) => (
                <DomainSelect id={id} value={primary} onChange={setPrimary} />
              )}
            </FormRow>
            <FormRow label='Second domain'>
              {(id) => (
                <DomainSelect
                  id={id}
                  value={secondary}
                  onChange={setSecondary}
                  optional
                />
              )}
            </FormRow>
            <div className='grid min-w-0 grid-cols-2 gap-3'>
              <FormRow label='Attitude' description='From enemy to friend.'>
                {(id) => (
                  <Input
                    id={id}
                    type='number'
                    min={-RELATION_SCALE}
                    max={RELATION_SCALE}
                    value={stance}
                    className='w-32'
                    onChange={(event) => setStance(event.target.value)}
                  />
                )}
              </FormRow>
              <FormRow label='Power'>
                {(id) => (
                  <Input
                    id={id}
                    type='number'
                    min={0}
                    max={STAT_SCALE}
                    value={power}
                    className='w-32'
                    onChange={(event) => setPower(event.target.value)}
                  />
                )}
              </FormRow>
            </div>
            <FormRow label='Status'>
              {(id) => (
                <Select
                  value={status}
                  onValueChange={(value) => setStatus(value as typeof status)}
                >
                  <SelectTrigger id={id} className='w-48'>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {foreignGodStatusValues.map((item) => (
                      <SelectItem key={item} value={item}>
                        {FOREIGN_STATUS_LABEL[item]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </FormRow>
            <div className='flex min-w-0 items-center gap-2'>
              <FieldTile
                id={`fg-contact-${god.id}`}
                label='Contact made with the pantheon'
              >
                <Checkbox
                  id={`fg-contact-${god.id}`}
                  checked={contacted}
                  onCheckedChange={(value) => setContacted(value === true)}
                />
              </FieldTile>
            </div>
            <FormRow label='Description'>
              {(id) => (
                <Textarea
                  id={id}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                />
              )}
            </FormRow>
            <FormRow label='Image prompt'>
              {(id) => (
                <Textarea
                  id={id}
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                />
              )}
            </FormRow>
            <div>
              <ActionButton
                label='Save'
                variant='default'
                blocked={reason() ?? (name.trim() ? null : 'A name is needed.')}
                pending={save.isPending}
                onRun={saveMain}
              />
            </div>
          </Section>
        </CollapsibleContent>
      </Collapsible>
      <Collapsible className='flex min-w-0 flex-col gap-3'>
        <CollapsibleTrigger asChild>
          <Button variant='outline' className='self-start'>
            <PenLine />
            Edit stats, powers, personality, existence and depth
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <Section title={`Shape ${god.name}`} surface='card' level={3}>
            <FieldTile group label='Stats'>
              <div className='grid min-w-0 grid-cols-2 gap-3'>
                {STATS.map((stat) => (
                  <FormRow key={stat.key} label={stat.label}>
                    {(id) => (
                      <Input
                        id={id}
                        type='number'
                        min={1}
                        max={STAT_SCALE}
                        value={stats[stat.key]}
                        className='w-32'
                        onChange={(event) =>
                          setStats({
                            ...stats,
                            [stat.key]: Number(event.target.value),
                          })
                        }
                      />
                    )}
                  </FormRow>
                ))}
              </div>
              <Label variant='overline'>Powers</Label>
              <Muted variant='caption'>
                Clearing a name removes that power; the last empty row adds a
                new one.
              </Muted>
              {rows.map((row, index) => (
                <div
                  key={index}
                  className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'
                >
                  <Input
                    aria-label={`Power ${index + 1} name`}
                    value={row.name}
                    placeholder='Power name'
                    onChange={(event) =>
                      updateRow(index, { name: event.target.value })
                    }
                  />
                  <Select
                    value={row.effect || undefined}
                    onValueChange={(value) =>
                      updateRow(index, { effect: value as ForeignPowerEffect })
                    }
                  >
                    <SelectTrigger
                      aria-label={`Power ${index + 1} effect`}
                      className='w-full'
                    >
                      <SelectValue placeholder='Effect' />
                    </SelectTrigger>
                    <SelectContent>
                      {foreignGodPowerEffectValues.map((effect) => (
                        <SelectItem key={effect} value={effect}>
                          {FOREIGN_EFFECT_LABEL[effect]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    aria-label={`Power ${index + 1} description`}
                    value={row.description}
                    placeholder='What it does'
                    onChange={(event) =>
                      updateRow(index, { description: event.target.value })
                    }
                  />
                </div>
              ))}
              <Label variant='overline'>Personality</Label>
              {PERSONALITY_FIELDS.map(([key, label]) => (
                <FormRow key={key} label={label}>
                  {(id) => (
                    <Textarea
                      id={id}
                      value={personality[key]}
                      onChange={(event) =>
                        setPersonality({
                          ...personality,
                          [key]: event.target.value,
                        })
                      }
                    />
                  )}
                </FormRow>
              ))}
              <Label variant='overline'>Existence</Label>
              <FormRow label='State'>
                {(id) => (
                  <Select value={mode} onValueChange={setMode}>
                    <SelectTrigger id={id} className='w-48'>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NONE}>Not set</SelectItem>
                      {existenceModeValues.map((item) => (
                        <SelectItem key={item} value={item}>
                          {wordOf(existenceModeValues, item)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </FormRow>
              <FormRow label='Nature'>
                {(id) => (
                  <Input
                    id={id}
                    value={nature}
                    onChange={(event) => setNature(event.target.value)}
                  />
                )}
              </FormRow>
              <FormRow label='Manifestation'>
                {(id) => (
                  <Input
                    id={id}
                    value={manifestation}
                    onChange={(event) => setManifestation(event.target.value)}
                  />
                )}
              </FormRow>
              <FormRow label='True name'>
                {(id) => (
                  <Input
                    id={id}
                    value={trueName}
                    onChange={(event) => setTrueName(event.target.value)}
                  />
                )}
              </FormRow>
              {god.depth && (
                <>
                  <Label variant='overline'>Depth</Label>
                  {DEPTH_TEXTS.map(([key, label]) => (
                    <FormRow key={key} label={label}>
                      {(id) => (
                        <Textarea
                          id={id}
                          value={depthTexts[key]}
                          onChange={(event) =>
                            setDepthTexts({
                              ...depthTexts,
                              [key]: event.target.value,
                            })
                          }
                        />
                      )}
                    </FormRow>
                  ))}
                  {DEPTH_LISTS.map(([key, label]) => (
                    <FormRow
                      key={key}
                      label={label}
                      description='One per line.'
                    >
                      {(id) => (
                        <Textarea
                          id={id}
                          value={depthLists[key]}
                          onChange={(event) =>
                            setDepthLists({
                              ...depthLists,
                              [key]: event.target.value,
                            })
                          }
                        />
                      )}
                    </FormRow>
                  ))}
                </>
              )}
            </FieldTile>
            <div>
              <ActionButton
                label='Save'
                variant='default'
                blocked={reason()}
                pending={save.isPending}
                onRun={saveTraits}
              />
            </div>
          </Section>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}
