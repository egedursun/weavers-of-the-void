import { useState } from 'react'
import { Blocks, FileText, ToggleRight, X } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { CodeBlock, EmptyState, FormRow, Section } from '@/components/domain'
import { ChoiceTiles, SwitchRow } from '@/components/domain/SettingsKit'
import { Muted, Text } from '@/components/typography'
import { NamePicker } from '@/features/pantheon/NamePicker'
import {
  type BlockQuery,
  type ContextBlockInfo,
  type ContextBlockKind,
  type SummarySection,
  useContextBlock,
  useContextBlockList,
} from './api'
import { BLOCK_OPTIONS, SUMMARY_SECTIONS, sectionLabel } from './promptModel'

const WHOLE_SUMMARY = 'whole'

type Picks = {
  sonId: number | null
  worldId: number | null
  entityId: number | null
  section: SummarySection | null
  short: boolean
  full: boolean
}

const NO_PICKS: Picks = {
  sonId: null,
  worldId: null,
  entityId: null,
  section: null,
  short: false,
  full: false,
}

function missingPick(info: ContextBlockInfo, picks: Picks): string | null {
  if (info.needs_son && picks.sonId === null)
    return 'This block is written for one son. Pick one.'
  if (info.needs_entity && picks.entityId === null)
    return 'This block describes one record. Pick it.'
  return null
}

function asId(value: string | null): number | null {
  return value === null ? null : Number(value)
}

function OptionSwitch({
  label,
  description,
  checked,
  onChange,
}: {
  label: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <SwitchRow
      icon={ToggleRight}
      tone='info'
      label={label}
      description={description}
      checked={checked}
      onChange={onChange}
    />
  )
}

function ClearPick({
  shown,
  onClear,
}: {
  shown: boolean
  onClear: () => void
}) {
  if (!shown) return null
  return (
    <Button variant='ghost' size='sm' onClick={onClear}>
      <X />
      Clear
    </Button>
  )
}

function BlockControls({
  info,
  picks,
  onChange,
}: {
  info: ContextBlockInfo
  picks: Picks
  onChange: (next: Partial<Picks>) => void
}) {
  const option = BLOCK_OPTIONS[info.kind]
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3'>
        <FormRow
          label={info.needs_son ? 'Son' : 'Seen by a son'}
          description={
            info.needs_son
              ? 'Required: the block is their own.'
              : 'Optional: render it as this son would see it.'
          }
        >
          {(id) => (
            <>
              <div className='min-w-0 flex-1 basis-60'>
                <NamePicker
                  id={id}
                  value={picks.sonId === null ? null : String(picks.sonId)}
                  kinds={['son']}
                  placeholder={
                    info.needs_son ? 'Pick a son' : 'No son, the plain view'
                  }
                  onChange={(value) => onChange({ sonId: asId(value) })}
                />
              </div>
              <ClearPick
                shown={picks.sonId !== null}
                onClear={() => onChange({ sonId: null })}
              />
            </>
          )}
        </FormRow>
        {info.needs_entity && (
          <FormRow
            label='Record'
            description='Required: the record to describe.'
          >
            {(id) => (
              <div className='min-w-0 flex-1 basis-60'>
                <NamePicker
                  id={id}
                  value={
                    picks.entityId === null ? null : String(picks.entityId)
                  }
                  kinds={['entity']}
                  placeholder='Pick a record'
                  onChange={(value) => onChange({ entityId: asId(value) })}
                />
              </div>
            )}
          </FormRow>
        )}
        <FormRow
          label='World'
          description='Optional: otherwise the son’s world, the record’s world or the first world.'
        >
          {(id) => (
            <>
              <div className='min-w-0 flex-1 basis-60'>
                <NamePicker
                  id={id}
                  value={picks.worldId === null ? null : String(picks.worldId)}
                  kinds={['world']}
                  placeholder='The default world'
                  onChange={(value) => onChange({ worldId: asId(value) })}
                />
              </div>
              <ClearPick
                shown={picks.worldId !== null}
                onClear={() => onChange({ worldId: null })}
              />
            </>
          )}
        </FormRow>
        {option === 'section' && (
          <FormRow
            label='Section'
            description='Show one part of the summary only.'
          >
            {(id) => (
              <Select
                value={picks.section ?? WHOLE_SUMMARY}
                onValueChange={(value) =>
                  onChange({
                    section:
                      value === WHOLE_SUMMARY
                        ? null
                        : (value as SummarySection),
                  })
                }
              >
                <SelectTrigger id={id} className='w-48'>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={WHOLE_SUMMARY}>
                    The whole summary
                  </SelectItem>
                  {SUMMARY_SECTIONS.map((section) => (
                    <SelectItem key={section} value={section}>
                      {sectionLabel(section)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </FormRow>
        )}
      </div>
      {option === 'short' && (
        <OptionSwitch
          label='Short form'
          description='The one-line header used where space is tight.'
          checked={picks.short}
          onChange={(short) => onChange({ short })}
        />
      )}
      {option === 'full' && (
        <OptionSwitch
          label='Full memory'
          description='Every remembered line, without the usual cap.'
          checked={picks.full}
          onChange={(full) => onChange({ full })}
        />
      )}
    </div>
  )
}

function RenderedBlock({
  query,
  info,
}: {
  query: BlockQuery
  info: ContextBlockInfo
}) {
  const blocked = missingPick(info, query)
  const block = useContextBlock(query, blocked === null)
  if (blocked) return <Muted>{blocked}</Muted>
  if (block.isPending) return <Skeleton className='h-textarea w-full' />
  if (block.isError)
    return <Text tone='destructive'>{block.error.message}</Text>
  return (
    <CodeBlock
      label='Rendered block'
      meta={`${formatInteger(block.data.characters)} characters, about ${formatInteger(block.data.token_estimate)} tokens`}
      text={block.data.text}
      empty='This block is empty for the current world.'
    />
  )
}

export function ContextBlocksView() {
  const list = useContextBlockList()
  const [kind, setKind] = useState<ContextBlockKind | null>(null)
  const [picks, setPicks] = useState<Picks>(NO_PICKS)
  const blocks = list.data ?? []
  const info = blocks.find((item) => item.kind === kind) ?? blocks[0]
  if (list.isPending) return <Skeleton className='h-textarea w-full' />
  if (list.isError) return <Text tone='destructive'>{list.error.message}</Text>
  if (!info)
    return (
      <EmptyState
        icon={Blocks}
        title='No context blocks'
        description='The server offers no block to preview.'
      />
    )
  const query: BlockQuery = { kind: info.kind, ...picks }
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <Section
        title='Context block'
        description='Every prompt is assembled from these blocks. Render one exactly as an agent reads it.'
        surface='card'
        level={3}
        icon={Blocks}
        tone='info'
      >
        <ChoiceTiles
          label='Block'
          value={info.kind}
          options={blocks.map((item) => ({
            value: item.kind,
            label: sectionLabel(item.kind),
            hint: `Read by ${item.audience}${item.needs_son ? ' · needs a son' : ''}${item.needs_entity ? ' · needs a record' : ''}`,
            icon: Blocks,
          }))}
          onChange={(value) => {
            setKind(value)
            setPicks((current) => ({
              ...current,
              section: null,
              short: false,
              full: false,
            }))
          }}
          columns={4}
        />
        <BlockControls
          info={info}
          picks={picks}
          onChange={(next) => setPicks((current) => ({ ...current, ...next }))}
        />
      </Section>
      <Section
        title={sectionLabel(info.kind)}
        surface='card'
        level={3}
        icon={FileText}
      >
        <RenderedBlock query={query} info={info} />
      </Section>
    </div>
  )
}
