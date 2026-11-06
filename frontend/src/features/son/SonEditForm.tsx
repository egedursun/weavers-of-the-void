import { useState } from 'react'
import { PenLine } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { RARITIES, RARITY_LABEL } from '@/constants/rarity'
import { Button } from '@/components/ui/button'
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
import { FormRow, Section } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { type Rarity, type SonPublic } from '@/features/pantheon/api'
import { STAT_SCALE } from '@/features/pantheon/constants'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { SON_PASSIONS, STATS } from '@/features/pantheon/labels'

type Body = components['schemas']['PatchSonsSonIdBody']
type Personality = components['schemas']['Personality']

const PERSONALITY: { key: keyof Personality; label: string }[] = [
  { key: 'appearance', label: 'Appearance' },
  { key: 'temperament', label: 'Temperament' },
  { key: 'obsession', label: 'Obsession' },
  { key: 'fear', label: 'Fear' },
  { key: 'speech_style', label: 'Speech' },
  { key: 'secret', label: 'Secret' },
]

const RESOURCES = [
  { key: 'stars', label: 'Stars' },
  { key: 'essence', label: 'Essence' },
  { key: 'hp', label: 'Life' },
  { key: 'existence', label: 'Existence' },
  { key: 'fame', label: 'Fame' },
  { key: 'level', label: 'Level' },
  { key: 'faith', label: 'Faith' },
] as const

type ResourceKey = (typeof RESOURCES)[number]['key']

const NAME_MAX = 60
const TITLE_MAX = 120
const PLAN_MAX = 1200

function NumberField({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string
  value: number
  min?: number
  max?: number
  onChange: (value: number) => void
}) {
  return (
    <FormRow label={label}>
      {(id) => (
        <Input
          id={id}
          type='number'
          min={min}
          max={max}
          value={value}
          className='w-32'
          onChange={(event) => onChange(Number(event.target.value))}
        />
      )}
    </FormRow>
  )
}

export function SonEditForm({ view }: { view: SonPublic }) {
  const son = view.son
  const [name, setName] = useState(son.name)
  const [title, setTitle] = useState(son.title)
  const [plan, setPlan] = useState(son.plan ?? '')
  const [personality, setPersonality] = useState<Personality>(son.personality)
  const [passions, setPassions] = useState<Record<string, number>>(
    Object.fromEntries(
      SON_PASSIONS.map((passion) => [passion.key, son[passion.key]])
    )
  )
  const [stats, setStats] = useState<Record<string, number>>(
    Object.fromEntries(STATS.map((stat) => [stat.key, son[stat.key]]))
  )
  const [rarity, setRarity] = useState<Rarity>(son.rarity)
  const [resources, setResources] = useState<Record<ResourceKey, number>>({
    stars: son.stars,
    essence: son.essence,
    hp: son.hp,
    existence: son.existence,
    fame: son.fame,
    level: son.level,
    faith: son.faith,
  })
  const { reason } = useGodGate()
  const save = useGodAction({
    run: (body: Body) =>
      unwrap(
        api.PATCH('/api/sons/{son_id}', {
          params: { path: { son_id: son.id } },
          body,
        })
      ),
    success: `${son.name} was edited`,
  })
  const submit = () => {
    const changedStats = Object.fromEntries(
      Object.entries(stats).filter(
        ([key, value]) => son[key as keyof typeof son] !== value
      )
    )
    const changedPassions = Object.fromEntries(
      Object.entries(passions).filter(
        ([key, value]) => son[key as keyof typeof son] !== value
      )
    )
    const changedResources = Object.fromEntries(
      Object.entries(resources).filter(
        ([key, value]) => son[key as keyof typeof son] !== value
      )
    )
    save.mutate({
      name: name.trim() !== son.name ? name.trim() : undefined,
      title: title.trim() !== son.title ? title.trim() : undefined,
      plan: plan !== (son.plan ?? '') ? plan : undefined,
      personality,
      passions: changedPassions,
      stats: changedStats,
      rarity: rarity !== son.rarity ? rarity : undefined,
      resources:
        Object.keys(changedResources).length > 0 ? changedResources : undefined,
    })
  }
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3'>
      <CollapsibleTrigger asChild>
        <Button variant='outline' className='self-start'>
          <PenLine />
          Edit name, plan, personality, stats and resources
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <Section title={`Edit ${son.name}`} surface='card' level={3}>
          <FormRow label='Name'>
            {(id) => (
              <Input
                id={id}
                value={name}
                maxLength={NAME_MAX}
                onChange={(event) => setName(event.target.value)}
              />
            )}
          </FormRow>
          <FormRow label='Title'>
            {(id) => (
              <Input
                id={id}
                value={title}
                maxLength={TITLE_MAX}
                onChange={(event) => setTitle(event.target.value)}
              />
            )}
          </FormRow>
          <FormRow label='Plan'>
            {(id) => (
              <Textarea
                id={id}
                value={plan}
                maxLength={PLAN_MAX}
                onChange={(event) => setPlan(event.target.value)}
              />
            )}
          </FormRow>
          {PERSONALITY.map((field) => (
            <FormRow key={field.key} label={field.label}>
              {(id) => (
                <Textarea
                  id={id}
                  value={personality[field.key]}
                  onChange={(event) =>
                    setPersonality({
                      ...personality,
                      [field.key]: event.target.value,
                    })
                  }
                />
              )}
            </FormRow>
          ))}
          <Label variant='overline'>Passions</Label>
          <div className='grid min-w-0 grid-cols-2 gap-3'>
            {SON_PASSIONS.map((passion) => (
              <NumberField
                key={passion.key}
                label={passion.label}
                min={0}
                max={STAT_SCALE}
                value={passions[passion.key]}
                onChange={(value) =>
                  setPassions({ ...passions, [passion.key]: value })
                }
              />
            ))}
          </div>
          <Label variant='overline'>Stats</Label>
          <div className='grid min-w-0 grid-cols-2 gap-3'>
            {STATS.map((stat) => (
              <NumberField
                key={stat.key}
                label={stat.label}
                min={1}
                max={STAT_SCALE}
                value={stats[stat.key]}
                onChange={(value) => setStats({ ...stats, [stat.key]: value })}
              />
            ))}
          </div>
          <Muted variant='caption'>
            Life and essence clamp to the new caps; every edit can be undone
            from the ledger.
          </Muted>
          <Label variant='overline'>Class and resources</Label>
          <FormRow
            label='Class'
            description='Changing class by hand is free and goes into the chronicle.'
          >
            {(id) => (
              <Select
                value={rarity}
                onValueChange={(value) => setRarity(value as Rarity)}
              >
                <SelectTrigger id={id} className='w-48'>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {RARITIES.map((item) => (
                    <SelectItem key={item} value={item}>
                      {RARITY_LABEL[item]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </FormRow>
          <div className='grid min-w-0 grid-cols-2 gap-3'>
            {RESOURCES.map((resource) => (
              <NumberField
                key={resource.key}
                label={resource.label}
                min={0}
                value={resources[resource.key]}
                onChange={(value) =>
                  setResources({ ...resources, [resource.key]: value })
                }
              />
            ))}
          </div>
          <Muted variant='caption'>
            Changes are canon; they know themselves this way on their next turn.
          </Muted>
          <div>
            <ActionButton
              label='Save'
              variant='default'
              blocked={reason() ?? (name.trim() ? null : 'A name is needed.')}
              pending={save.isPending}
              onRun={submit}
            />
          </div>
        </Section>
      </CollapsibleContent>
    </Collapsible>
  )
}
