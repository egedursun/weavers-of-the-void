import { useState } from 'react'
import {
  Coins,
  Crown,
  Gauge,
  Hammer,
  Hourglass,
  MessageSquare,
  ScrollText,
  Settings2,
  Zap,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  CodeBlock,
  EmptyState,
  EntityLink,
  FormRow,
  MiniStat,
  PagedList,
  Section,
  StatBar,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { NamePicker } from '@/features/pantheon/NamePicker'
import { type SonPromptPreview, useSonPrompt } from './api'
import { budgetTone, sectionLabel } from './promptModel'

type SonPromptViewProps = {
  initialSon: number | null
}

function ToolList({ title, tools }: { title: string; tools: string[] }) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label>{`${title} (${formatInteger(tools.length)})`}</Label>
      {tools.length === 0 ? (
        <Muted variant='caption'>None this turn.</Muted>
      ) : (
        <PagedList
          items={tools}
          initial={12}
          noun={['entry', 'entries']}
          as='div'
          className='flex min-w-0 flex-wrap items-center gap-1.5'
          itemKey={(tool) => tool}
        >
          {(tool) => (
            <Badge key={tool} size='sm' variant='outline'>
              {tool}
            </Badge>
          )}
        </PagedList>
      )}
    </div>
  )
}

function Budget({ preview }: { preview: SonPromptPreview }) {
  return (
    <Section
      title='Budget'
      description='How much of the prompt allowance this turn uses. Over the limit, the oldest context is cut first.'
      surface='card'
      level={3}
      icon={Gauge}
      tone={preview.over_limit ? 'danger' : 'success'}
      actions={
        preview.over_limit ? (
          <Badge variant='destructive'>Over the limit</Badge>
        ) : (
          <Badge variant='success'>Within the limit</Badge>
        )
      }
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Crown aria-hidden='true' className='size-icon-sm text-primary' />
        <EntityLink kind='son' id={String(preview.son_id)}>
          {preview.son_name}
        </EntityLink>
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-5'>
        <MiniStat
          icon={Hourglass}
          label='Epoch'
          value={preview.epoch}
          tone='verdigris'
        />
        <MiniStat
          icon={Zap}
          label='Action points'
          value={preview.action_points}
          tone='gold'
        />
        <MiniStat
          icon={Coins}
          label='Tokens, about'
          value={formatInteger(preview.token_estimate)}
          tone='info'
        />
        <MiniStat
          icon={Settings2}
          label='System prompt chars'
          value={formatInteger(preview.system_characters)}
          tone='muted'
        />
        <MiniStat
          icon={MessageSquare}
          label='User prompt chars'
          value={formatInteger(preview.user_characters)}
          tone='muted'
        />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-4 md:grid-cols-3'>
        <StatBar
          label='Whole prompt'
          value={preview.total_characters}
          max={preview.prompt_limit}
          tone={budgetTone(preview.total_characters, preview.prompt_limit)}
        />
        <StatBar
          label='World summary'
          value={preview.summary_characters}
          max={preview.summary_limit}
          tone={budgetTone(preview.summary_characters, preview.summary_limit)}
        />
        <StatBar
          label='Memory'
          value={preview.memory_characters}
          max={preview.memory_limit}
          tone={budgetTone(preview.memory_characters, preview.memory_limit)}
        />
      </div>
      {preview.summary_sections.length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4'>
          {preview.summary_sections.map((section) =>
            section.limit !== null && section.limit !== undefined ? (
              <StatBar
                key={section.section}
                label={sectionLabel(section.section)}
                value={section.characters}
                max={section.limit}
                tone={budgetTone(section.characters, section.limit)}
              />
            ) : (
              <div
                key={section.section}
                className='flex min-w-0 flex-col gap-1.5'
              >
                <Label truncate>{sectionLabel(section.section)}</Label>
                <Text variant='caption'>
                  {`${formatInteger(section.characters)} characters, no cap`}
                </Text>
              </div>
            )
          )}
        </div>
      )}
    </Section>
  )
}

export function SonPromptView({ initialSon }: SonPromptViewProps) {
  const [sonId, setSonId] = useState<number | null>(initialSon)
  const preview = useSonPrompt(sonId)
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <FormRow
        label='Son'
        description='The exact prompt this son would receive if their turn began now.'
      >
        {(id) => (
          <div className='min-w-0 flex-1 basis-60'>
            <NamePicker
              id={id}
              value={sonId === null ? null : String(sonId)}
              kinds={['son']}
              placeholder='Pick a son'
              onChange={(value) =>
                setSonId(value === null ? null : Number(value))
              }
            />
          </div>
        )}
      </FormRow>
      {sonId === null && (
        <EmptyState
          icon={Crown}
          title='Pick a son'
          description='Their system prompt, turn prompt, tools and budget appear here.'
        />
      )}
      {sonId !== null && preview.isPending && (
        <Skeleton className='h-textarea w-full' />
      )}
      {preview.isError && (
        <Text tone='destructive'>{preview.error.message}</Text>
      )}
      {preview.data && (
        <>
          <Budget preview={preview.data} />
          <Section
            title='Tools'
            icon={Hammer}
            description='What they may call this turn. Paid tools spend action points or essence.'
            surface='card'
            level={3}
          >
            <div className='grid min-w-0 grid-cols-1 gap-4 md:grid-cols-2'>
              <ToolList title='Paid tools' tools={preview.data.paid_tools} />
              <ToolList title='Free tools' tools={preview.data.free_tools} />
            </div>
          </Section>
          <Section
            title='The prompt'
            surface='card'
            level={3}
            icon={ScrollText}
          >
            <CodeBlock
              label='System prompt'
              meta={`${formatInteger(preview.data.system_characters)} characters`}
              text={preview.data.system_prompt}
            />
            <CodeBlock
              label='User prompt'
              meta={`${formatInteger(preview.data.user_characters)} characters`}
              text={preview.data.user_prompt}
            />
          </Section>
        </>
      )}
    </div>
  )
}
