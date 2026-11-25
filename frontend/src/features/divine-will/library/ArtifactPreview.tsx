import { useMemo } from 'react'
import { FileQuestion, ShieldCheck } from 'lucide-react'
import { EmptyState } from '@/components/domain'
import { Muted } from '@/components/typography'
import { WillMarkdown } from '../WillMarkdown'
import { type ArtifactFormat } from '../types'
import { type FountainElement, parseFountain } from './fountain'

const ELEMENT_CLASS: Record<
  Exclude<FountainElement['type'], 'break'>,
  string
> = {
  scene: 'fountain-scene',
  action: 'fountain-action',
  character: 'fountain-character',
  parenthetical: 'fountain-parenthetical',
  dialogue: 'fountain-dialogue',
  transition: 'fountain-transition',
  centered: 'fountain-centered',
  section: 'fountain-section',
  note: 'fountain-note',
}

export function FountainView({ source }: { source: string }) {
  const script = useMemo(() => parseFountain(source), [source])
  const name = script.title.find((entry) => entry.key.toLowerCase() === 'title')
  return (
    <div data-domain='fountain' className='fountain rounded-md surface-well'>
      {script.title.length > 0 && (
        <div className='fountain-title'>
          {name && <div className='fountain-title-name'>{name.value}</div>}
          {script.title
            .filter((entry) => entry !== name)
            .map((entry) => (
              <div key={entry.key} className='whitespace-pre-wrap'>
                {entry.value}
              </div>
            ))}
        </div>
      )}
      {script.elements.map((element, index) =>
        element.type === 'break' ? (
          <div key={index} aria-hidden='true' className='fountain-break' />
        ) : (
          <div
            key={index}
            data-fountain={element.type}
            className={ELEMENT_CLASS[element.type]}
          >
            {element.text}
          </div>
        )
      )}
    </div>
  )
}

export function HtmlFrame({
  source,
  title,
}: {
  source: string
  title: string
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <iframe
        title={title}
        sandbox=''
        referrerPolicy='no-referrer'
        srcDoc={source}
        className='will-html-frame'
      />
      <Muted variant='caption' className='flex items-center gap-1'>
        <ShieldCheck aria-hidden='true' className='size-icon-xs shrink-0' />
        Shown sealed: no script runs and nothing leaves the page.
      </Muted>
    </div>
  )
}

export function ArtifactPreview({
  format,
  body,
  title,
}: {
  format: ArtifactFormat
  body: string
  title: string
}) {
  if (!body.trim())
    return (
      <EmptyState
        size='compact'
        icon={FileQuestion}
        title='Nothing written yet'
        description='This version has no text.'
      />
    )
  if (format === 'fountain') return <FountainView source={body} />
  if (format === 'html') return <HtmlFrame source={body} title={title} />
  return <WillMarkdown text={body} size='prose' />
}

type DiffLine = {
  change: 'added' | 'removed' | 'same' | 'hunk'
  text: string
}

function diffLines(text: string): DiffLine[] {
  return text
    .replace(/\n$/, '')
    .split('\n')
    .filter((line) => !line.startsWith('+++') && !line.startsWith('---'))
    .map((line): DiffLine => {
      if (line.startsWith('@@')) return { change: 'hunk', text: line }
      if (line.startsWith('+')) return { change: 'added', text: line.slice(1) }
      if (line.startsWith('-'))
        return { change: 'removed', text: line.slice(1) }
      return { change: 'same', text: line.slice(1) }
    })
}

const DIFF_MARK: Record<DiffLine['change'], string> = {
  added: '+',
  removed: '−',
  same: ' ',
  hunk: '…',
}

const DIFF_SPOKEN: Record<DiffLine['change'], string> = {
  added: 'Added: ',
  removed: 'Removed: ',
  same: '',
  hunk: 'Further on: ',
}

export function DiffView({ text }: { text: string }) {
  const lines = diffLines(text)
  if (
    !lines.some((line) => line.change === 'added' || line.change === 'removed')
  )
    return <Muted variant='caption'>The two versions are the same.</Muted>
  return (
    <div
      data-domain='will-diff'
      className='will-diff rounded-md surface-well py-2'
    >
      {lines.map((line, index) => (
        <div key={index} data-change={line.change} className='will-diff-line'>
          <span aria-hidden='true'>{DIFF_MARK[line.change]}</span>
          <span>
            <span className='sr-only'>{DIFF_SPOKEN[line.change]}</span>
            {line.change === 'hunk' ? 'Lines further on' : line.text || ' '}
          </span>
        </div>
      ))}
    </div>
  )
}
