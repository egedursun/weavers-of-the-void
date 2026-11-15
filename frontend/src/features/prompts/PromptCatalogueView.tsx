import { useMemo, useState } from 'react'
import { BookText, Crown, Search, Users } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  CodeBlock,
  EmptyState,
  KeyValueList,
  Section,
  ToolList,
  type ToolCardData,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  type PromptArea,
  type PromptEntry,
  type PromptId,
  type ToolEntry,
  usePromptCatalogue,
  usePromptDetail,
} from './api'
import { AREA_LABEL, matchesPrompt, schemaText } from './promptModel'

const ALL_AREAS = 'all'

function toolCard(tool: ToolEntry): ToolCardData {
  const properties = (tool.input_schema.properties ?? {}) as Record<
    string,
    { type?: string; title?: string }
  >
  const required = new Set(
    Array.isArray(tool.input_schema.required)
      ? (tool.input_schema.required as string[])
      : []
  )
  return {
    id: `${tool.agent}:${tool.tool_id}`,
    name: tool.tool_id,
    description: tool.description,
    fields: Object.fromEntries(
      Object.entries(properties).map(([field, spec]) => [
        field,
        `${spec.type ?? 'value'}${required.has(field) ? '' : ', optional'}`,
      ])
    ),
    actionCost: tool.action_cost,
    essenceCost: tool.essence_cost,
    readOnly: tool.read_only,
    longJob: tool.long_job,
    minimumRarity: tool.minimum_rarity,
  }
}

function PromptList({
  prompts,
  selected,
  onSelect,
}: {
  prompts: PromptEntry[]
  selected: PromptId | null
  onSelect: (promptId: PromptId) => void
}) {
  return (
    <ul className='flex min-w-0 flex-col'>
      {prompts.map((entry) => (
        <li
          key={entry.prompt_id}
          data-prompt={entry.prompt_id}
          className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 border-b py-2 last:border-b-0'
        >
          <Button
            variant={entry.prompt_id === selected ? 'secondary' : 'ghost'}
            size='sm'
            className='font-mono'
            aria-pressed={entry.prompt_id === selected}
            onClick={() => onSelect(entry.prompt_id)}
          >
            {entry.prompt_id}
          </Button>
          <Muted as='span' variant='caption' truncate className='flex-1'>
            {`${AREA_LABEL[entry.area]} · ${formatInteger(entry.variables.length)} variable${entry.variables.length === 1 ? '' : 's'}${entry.output ? ` · ${entry.output}` : ''}`}
          </Muted>
        </li>
      ))}
    </ul>
  )
}

function PromptDetailPanel({ promptId }: { promptId: PromptId | null }) {
  const detail = usePromptDetail(promptId)
  if (promptId === null)
    return (
      <EmptyState
        size='compact'
        icon={BookText}
        title='Pick a prompt'
        description='Its template, variables and output model appear here.'
      />
    )
  if (detail.isPending) return <Skeleton className='h-textarea w-full' />
  if (detail.isError)
    return <Text tone='destructive'>{detail.error.message}</Text>
  const data = detail.data
  const schema = schemaText(data.output_schema)
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <KeyValueList
        items={[
          { label: 'Prompt', value: data.prompt_id },
          { label: 'Area', value: AREA_LABEL[data.area] },
          { label: 'Template', value: data.template_path },
          { label: 'Context', value: data.context },
          { label: 'Output model', value: data.output ?? 'Free text' },
          {
            label: 'Constraints',
            value: data.has_constraints ? 'Validated after the answer' : 'None',
          },
        ]}
      />
      {data.variables.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Variable</TableHead>
              <TableHead>Type</TableHead>
              <TableHead className='text-end'>Required</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.variables.map((variable) => (
              <TableRow key={variable.name}>
                <TableCell>{variable.name}</TableCell>
                <TableCell>{variable.type}</TableCell>
                <TableCell className='text-end'>
                  {variable.required ? 'Yes' : 'No'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      <CodeBlock label='Template source' text={data.template_source} />
      {schema !== '' && <CodeBlock label='Output schema' text={schema} />}
    </div>
  )
}

function ToolGrid({ tools }: { tools: ToolEntry[] }) {
  if (tools.length === 0)
    return <Muted variant='caption'>No tools in this catalogue.</Muted>
  return <ToolList tools={tools.map(toolCard)} columns={2} initial={8} />
}

export function PromptCatalogueView() {
  const [area, setArea] = useState<PromptArea | null>(null)
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<PromptId | null>(null)
  const catalogue = usePromptCatalogue(area)
  const shown = useMemo(
    () =>
      (catalogue.data?.prompts ?? []).filter((entry) =>
        matchesPrompt(entry, query)
      ),
    [catalogue.data, query]
  )
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Select
          value={area ?? ALL_AREAS}
          onValueChange={(value) =>
            setArea(value === ALL_AREAS ? null : (value as PromptArea))
          }
        >
          <SelectTrigger aria-label='Prompt area' className='w-48'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_AREAS}>Every area</SelectItem>
            {(Object.keys(AREA_LABEL) as PromptArea[]).map((key) => (
              <SelectItem key={key} value={key}>
                {AREA_LABEL[key]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className='min-w-0 flex-1 basis-60'>
          <Input
            type='search'
            leadingIcon={Search}
            aria-label='Search prompts'
            placeholder='Search prompts, templates and variables'
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
      </div>
      {catalogue.isPending && <Skeleton className='h-textarea w-full' />}
      {catalogue.isError && (
        <Text tone='destructive'>{catalogue.error.message}</Text>
      )}
      {catalogue.data && (
        <div className='grid min-w-0 grid-cols-1 items-start gap-6 xl:grid-cols-2'>
          <Section
            title='Prompts'
            description={`${formatInteger(shown.length)} of ${plural(catalogue.data.prompts.length, 'prompt', 'prompts')}. Every prompt text lives in one catalogue.`}
            surface='card'
            level={3}
            icon={BookText}
          >
            {shown.length === 0 ? (
              <EmptyState
                size='compact'
                icon={Search}
                title='No prompt matches'
                description='Try another word or another area.'
              />
            ) : (
              <PromptList
                prompts={shown}
                selected={selected}
                onSelect={setSelected}
              />
            )}
          </Section>
          <Section
            title={selected ?? 'Prompt'}
            surface='card'
            level={3}
            actions={
              selected && (
                <Badge size='sm' variant='outline'>
                  Read only
                </Badge>
              )
            }
          >
            <PromptDetailPanel promptId={selected} />
          </Section>
        </div>
      )}
      {catalogue.data && (
        <>
          <Section
            title='Son tools'
            description='The tools a son may call, with their costs and inputs.'
            surface='card'
            level={3}
            icon={Crown}
            tone='verdigris'
          >
            <ToolGrid tools={catalogue.data.son_tools} />
          </Section>
          <Section
            title='Mortal tools'
            description='The tools a mortal agent may call.'
            surface='card'
            level={3}
            icon={Users}
            tone='info'
          >
            <ToolGrid tools={catalogue.data.mortal_tools} />
          </Section>
        </>
      )}
    </div>
  )
}
