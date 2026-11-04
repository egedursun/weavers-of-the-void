import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Brain,
  GraduationCap,
  Hammer,
  Plus,
  Sparkles,
  Trash2,
  type LucideIcon,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState, Medallion, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { CONDITIONS } from '@/features/entity/body/labels'
import { SKILL_ICONS, TRAIT_ICONS } from '@/features/entity/mind/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

export type Variant = components['schemas']['VariantView']
type Family = components['schemas']['KindFamily']

const VARIANTS_KEY = ['variants'] as const
const WORKING = 'Working on it.'
const STRENGTH_MAX = 400
const FAMILIES: Record<
  Family,
  { label: string; icon: LucideIcon; bases: Record<string, { label: string }> }
> = {
  trait: { label: 'Trait', icon: Brain, bases: TRAIT_ICONS },
  skill: { label: 'Skill', icon: GraduationCap, bases: SKILL_ICONS },
  condition: { label: 'Condition', icon: Sparkles, bases: CONDITIONS },
}

export function useVariants() {
  return useQuery({
    queryKey: VARIANTS_KEY,
    queryFn: () => unwrap(api.GET('/api/variants')),
  })
}

export function variantChoices(
  variants: Variant[] | undefined,
  family: Family,
  base: string
): Record<string, string> {
  return Object.fromEntries(
    (variants ?? [])
      .filter((item) => item.family === family && item.base === base)
      .map((item) => [String(item.id), item.name])
  )
}

function table(source: Record<string, { label: string }>) {
  return Object.fromEntries(
    Object.entries(source).map(([key, value]) => [key, value.label])
  )
}

function percent(value: string): number {
  return Math.max(0, Math.min(STRENGTH_MAX, Math.round(Number(value) || 0)))
}

function VariantRow({
  variant,
  blocked,
}: {
  variant: Variant
  blocked: string | null
}) {
  const [strength, setStrength] = useState(String(variant.strength_pct))
  const [learning, setLearning] = useState(String(variant.learning_pct))
  const spec = FAMILIES[variant.family]
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/variant:edit', {
          body: {
            variant_id: variant.id,
            strength_pct: percent(strength),
            learning_pct: percent(learning),
            hold: true,
          },
        })
      ),
    invalidate: [VARIANTS_KEY],
  })
  const unmake = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/variant:delete', {
          body: { variant_id: variant.id },
        })
      ),
    invalidate: [VARIANTS_KEY],
  })
  const reason =
    blocked ?? (save.isPending || unmake.isPending ? WORKING : null)
  return (
    <li className='flex min-w-0 flex-wrap items-end gap-2 rounded-md border bg-background p-2'>
      <Medallion icon={spec.icon} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col'>
        <Text weight='semibold' truncate>
          {variant.name}
        </Text>
        <Muted variant='caption'>{`A kind of ${(spec.bases[variant.base]?.label ?? variant.base).toLowerCase()}`}</Muted>
      </div>
      <div className='flex flex-col gap-1'>
        <Label as='label' htmlFor={`variant-strength-${variant.id}`}>
          Strength %
        </Label>
        <Input
          id={`variant-strength-${variant.id}`}
          type='number'
          min={0}
          max={STRENGTH_MAX}
          value={strength}
          disabled={reason !== null}
          onChange={(event) => setStrength(event.target.value)}
        />
      </div>
      {variant.family === 'skill' && (
        <div className='flex flex-col gap-1'>
          <Label as='label' htmlFor={`variant-learning-${variant.id}`}>
            Learning %
          </Label>
          <Input
            id={`variant-learning-${variant.id}`}
            type='number'
            min={0}
            max={STRENGTH_MAX}
            value={learning}
            disabled={reason !== null}
            onChange={(event) => setLearning(event.target.value)}
          />
        </div>
      )}
      {variant.held.length > 0 && (
        <Badge size='sm' variant='outline'>
          Held
        </Badge>
      )}
      <Button
        size='sm'
        variant='outline'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => save.mutate(undefined)}
      >
        Keep
      </Button>
      <Button
        size='icon'
        variant='ghost'
        aria-label={`Unmake ${variant.name}`}
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => unmake.mutate(undefined)}
      >
        <Trash2 />
      </Button>
    </li>
  )
}

export function VariantForge() {
  const { reason } = useGodGate()
  const variants = useVariants()
  const [family, setFamily] = useState<Family>('trait')
  const [base, setBase] = useState('')
  const [name, setName] = useState('')
  const [strength, setStrength] = useState('120')
  const create = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/variant:create', {
          body: {
            family,
            base,
            name: name.trim(),
            strength_pct: percent(strength),
            learning_pct: 100,
          },
        })
      ),
    invalidate: [VARIANTS_KEY],
    onDone: () => setName(''),
  })
  const blocked = reason()
  const busy = blocked ?? (create.isPending ? WORKING : null)
  const missing =
    base === ''
      ? 'Choose what it is a kind of.'
      : name.trim() === ''
        ? 'Give it a name.'
        : null
  return (
    <div
      data-surface='VariantForge'
      className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={Hammer} tone='verdigris' size='sm' />
        <div className='flex min-w-0 flex-col'>
          <Label variant='overline'>Kinds of this world</Label>
          <Muted variant='caption'>
            Forge new traits, skills and conditions on a known kind. The engine
            treats them as their base, scaled by their strength.
          </Muted>
        </div>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-4'>
        <MindPicker
          label='Family'
          value={family}
          table={Object.fromEntries(
            Object.entries(FAMILIES).map(([key, value]) => [key, value.label])
          )}
          blocked={busy}
          onPick={(value) => {
            setFamily(value as Family)
            setBase('')
          }}
        />
        <MindPicker
          label='A kind of'
          value={base}
          table={table(FAMILIES[family].bases)}
          blocked={busy}
          placeholder='Choose a base'
          onPick={setBase}
        />
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor='variant-name'>
            Name
          </Label>
          <Input
            id='variant-name'
            value={name}
            disabled={busy !== null}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor='variant-strength'>
            Strength %
          </Label>
          <Input
            id='variant-strength'
            type='number'
            min={0}
            max={STRENGTH_MAX}
            value={strength}
            disabled={busy !== null}
            onChange={(event) => setStrength(event.target.value)}
          />
        </div>
      </div>
      <div className='flex justify-end'>
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => create.mutate(undefined)}
        >
          <Plus />
          Forge it
        </Button>
      </div>
      {(variants.data ?? []).length === 0 ? (
        <EmptyState
          icon={Hammer}
          title='No world-made kinds yet'
          description='What you forge here appears for every mortal.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={variants.data ?? []} as='li'>
            {(variant) => (
              <VariantRow
                key={variant.id}
                variant={variant}
                blocked={blocked}
              />
            )}
          </Paged>
        </ul>
      )}
    </div>
  )
}
