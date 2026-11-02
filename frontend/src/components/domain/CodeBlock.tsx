import { Label, Muted, Text } from '@/components/typography'
import { CopyButton } from './CopyButton'

type CodeBlockProps = {
  label: string
  text: string
  meta?: string
  empty?: string
}

export function CodeBlock({
  label,
  text,
  meta,
  empty = 'Nothing to show.',
}: CodeBlockProps) {
  return (
    <div data-domain='code-block' className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Label truncate className='flex-1'>
          {label}
        </Label>
        {meta && (
          <Muted as='span' variant='caption' truncate>
            {meta}
          </Muted>
        )}
        <CopyButton text={text} label={`Copy ${label.toLowerCase()}`} />
      </div>
      <Text
        as='div'
        variant='caption'
        tone={text ? 'default' : 'muted'}
        tabIndex={0}
        role='region'
        aria-label={label}
        className='max-h-96 min-w-0 overflow-auto rounded-md border bg-muted p-3 font-mono whitespace-pre-wrap'
      >
        {text || empty}
      </Text>
    </div>
  )
}
