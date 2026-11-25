import { useMemo } from 'react'
import { Tags } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { type ActProp } from '@/api/mutation'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Toggle } from '@/components/ui/toggle'
import { FormRow, PagedList, Section } from '@/components/domain'
import { Label } from '@/components/typography'
import { type EntityContext } from '../actions/context'
import { humanize } from '../actions/schema'
import { useLoreMutation } from '../api/mutations'
import { useActionCatalogue, useCatalogue } from '../api/queries'

type TagChange = {
  add_flags?: string[]
  remove_flags?: string[]
  add_traits?: string[]
  remove_traits?: string[]
  add_mechanics?: string[]
  remove_mechanics?: string[]
  law?: string
}

type TagBody = components['schemas']['PatchEntitiesEntityIdTagsBody']

function tagBody(change: TagChange): TagBody {
  return {
    add_flags: (change.add_flags ?? []) as TagBody['add_flags'],
    remove_flags: (change.remove_flags ?? []) as TagBody['remove_flags'],
    add_traits: (change.add_traits ?? []) as TagBody['add_traits'],
    remove_traits: (change.remove_traits ?? []) as TagBody['remove_traits'],
    add_mechanics: (change.add_mechanics ?? []) as TagBody['add_mechanics'],
    remove_mechanics: (change.remove_mechanics ??
      []) as TagBody['remove_mechanics'],
    ...(change.law !== undefined ? { law: change.law as TagBody['law'] } : {}),
  }
}

function enumOf(
  schema: Record<string, unknown> | undefined,
  name: string
): string[] {
  const defs = (schema?.$defs ?? {}) as Record<string, { enum?: string[] }>
  return defs[name]?.enum ?? []
}

function ToggleGrid({
  label,
  options,
  active,
  disabled,
  labelOf,
  onToggle,
  act,
}: {
  label: string
  options: string[]
  active: (key: string) => boolean
  disabled: boolean
  labelOf: (key: string) => string
  onToggle: (key: string, on: boolean) => void
  act?: ActProp
}) {
  if (options.length === 0) return null
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{label}</Label>
      <PagedList
        items={options}
        initial={12}
        noun={['entry', 'entries']}
        as='div'
        className='flex min-w-0 flex-wrap gap-1'
        itemKey={(key) => key}
      >
        {(key) => (
          <Toggle
            act={act}
            key={key}
            variant='outline'
            size='sm'
            pressed={active(key)}
            disabled={disabled}
            onPressedChange={(on) => onToggle(key, on)}
            aria-label={labelOf(key)}
          >
            {labelOf(key)}
          </Toggle>
        )}
      </PagedList>
    </div>
  )
}

export function TagEditor({
  ctx,
  readOnlyReason,
}: {
  ctx: EntityContext
  readOnlyReason: string | null
}) {
  const actions = useActionCatalogue()
  const catalogue = useCatalogue()
  const schema = actions.data?.find(
    (item) => item.id === 'entity:tags'
  )?.input_schema
  const flags = useMemo(() => enumOf(schema, 'EntityFlag'), [schema])
  const traits = useMemo(() => enumOf(schema, 'CreatureTrait'), [schema])
  const mechanics = useMemo(() => enumOf(schema, 'ResourceMechanic'), [schema])
  const laws = useMemo(() => enumOf(schema, 'NaturalLaw'), [schema])
  const change = useLoreMutation({
    writes: [{ lever: 'entity:tags' }],
    run: (body: TagChange) =>
      unwrap(
        api.PATCH('/api/entities/{entity_id}/tags', {
          params: { path: { entity_id: ctx.entity.id } },
          body: tagBody(body),
        })
      ),
  })
  const traitLabel = (key: string) =>
    catalogue.data?.creature_traits.find((item) => item.key === key)?.label ??
    humanize(key)
  const disabled = readOnlyReason !== null || change.isPending
  const currentLaw = ctx.detail.tags
    .find((tag) => tag.startsWith('law:'))
    ?.slice('law:'.length)
  const hasMechanic = (key: string) =>
    ctx.detail.tags.includes(`mechanic:${key}`) || ctx.detail.tags.includes(key)
  return (
    <Section id='section-tags' title='Marks and traits' level={3}>
      <Collapsible className='flex min-w-0 flex-col gap-4'>
        <CollapsibleTrigger asChild>
          <Button act={change} variant='outline' className='self-start'>
            <Tags />
            Change marks
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className='flex min-w-0 flex-col gap-4'>
          <ToggleGrid
            act={change}
            label='Marks'
            options={flags}
            active={(key) => ctx.flags.has(key)}
            disabled={disabled}
            labelOf={humanize}
            onToggle={(key, on) =>
              change.mutate(on ? { add_flags: [key] } : { remove_flags: [key] })
            }
          />
          {ctx.type === 'species' && (
            <ToggleGrid
              act={change}
              label='Species traits'
              options={traits}
              active={(key) => ctx.detail.traits.includes(key as never)}
              disabled={disabled}
              labelOf={traitLabel}
              onToggle={(key, on) =>
                change.mutate(
                  on ? { add_traits: [key] } : { remove_traits: [key] }
                )
              }
            />
          )}
          {ctx.type === 'resource' && (
            <ToggleGrid
              act={change}
              label='How the resource behaves'
              options={mechanics}
              active={hasMechanic}
              disabled={disabled}
              labelOf={humanize}
              onToggle={(key, on) =>
                change.mutate(
                  on ? { add_mechanics: [key] } : { remove_mechanics: [key] }
                )
              }
            />
          )}
          {ctx.type === 'natural_law' && laws.length > 0 && (
            <FormRow label='How the law works'>
              {(id) => (
                <Select
                  act={change}
                  value={currentLaw}
                  disabled={disabled}
                  onValueChange={(value) => change.mutate({ law: value })}
                >
                  <SelectTrigger id={id} className='w-full'>
                    <SelectValue placeholder='Choose a law' />
                  </SelectTrigger>
                  <SelectContent>
                    {laws.map((law) => (
                      <SelectItem key={law} value={law}>
                        {humanize(law)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </FormRow>
          )}
        </CollapsibleContent>
      </Collapsible>
    </Section>
  )
}
