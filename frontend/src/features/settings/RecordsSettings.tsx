import { type ReactNode } from 'react'
import { Link } from '@tanstack/react-router'
import {
  BookOpen,
  CircleCheck,
  FileDown,
  FilePlusCorner,
  FileText,
  Library,
  NotebookPen,
  RefreshCw,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatBytes } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { type KpiTone, Medallion, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { bookUrl, codexMarkdownUrl, codexUrl } from '@/features/chronicle/api'
import { ModelMetrics } from '@/features/metrics/ModelMetrics'
import { useWorldState } from '@/features/overview/api'
import { bookPdfUrl, useBookPdf, usePrintBook } from './bookApi'

const PERCENT = 100

function BookPdfCard() {
  const status = useBookPdf()
  const print = usePrintBook()
  const data = status.data
  const running = Boolean(data?.job_id) || print.isPending
  const progress = Math.round((data?.progress ?? 0) * PERCENT)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'>
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion
          icon={FileText}
          tone={data?.ready ? 'gold' : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text as='span' weight='medium'>
            Printed book (PDF)
          </Text>
          <Muted variant='caption'>
            The whole book typeset into pages, with a cover, contents, maps,
            running heads, page numbers and an index.
          </Muted>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            {data?.ready ? (
              <>
                <Badge size='sm' variant={data.stale ? 'warning' : 'success'}>
                  {data.stale ? <TriangleAlert /> : <CircleCheck />}
                  {data.stale
                    ? `Out of date: made at epoch ${data.epoch}${data.world_epoch !== null && data.world_epoch !== undefined ? `, world at epoch ${data.world_epoch}` : ''}`
                    : 'Up to date'}
                </Badge>
                {data.size !== null && (
                  <Badge size='sm' variant='outline'>
                    {formatBytes(data.size)}
                  </Badge>
                )}
              </>
            ) : (
              <Badge size='sm' variant='outline'>
                Not printed yet
              </Badge>
            )}
          </div>
        </div>
      </div>
      {running && (
        <div className='flex min-w-0 flex-col gap-1'>
          <Progress
            value={progress}
            indeterminate={progress <= 0}
            aria-label='Printing progress'
          />
          <Muted variant='caption'>
            {data?.stage ? `${data.stage}… ${progress}%` : 'Starting…'}
          </Muted>
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          variant={data?.ready && !data.stale ? 'outline' : 'default'}
          disabled={running || status.isPending}
          disabledReason={
            running
              ? 'The book is being typeset'
              : 'Reading whether a PDF exists'
          }
          onClick={() =>
            print.mutate(undefined, {
              onError: (error) => toast.error(error.message),
            })
          }
        >
          {data?.ready ? <RefreshCw /> : <FilePlusCorner />}
          {data?.ready ? 'Regenerate PDF' : 'Generate PDF'}
        </Button>
        {data?.ready ? (
          <Button variant={data.stale ? 'outline' : 'default'} asChild>
            <a href={bookPdfUrl()} download>
              <FileDown />
              Download PDF
            </a>
          </Button>
        ) : (
          <Button
            variant='outline'
            disabled
            disabledReason='Generate the PDF first; there is nothing to download yet'
          >
            <FileDown />
            Download PDF
          </Button>
        )}
      </div>
    </div>
  )
}

function LinkTile({
  icon,
  tone,
  title,
  hint,
  children,
}: {
  icon: LucideIcon
  tone: KpiTone
  title: string
  hint: string
  children: (inner: ReactNode) => ReactNode
}) {
  return children(
    <>
      <Medallion icon={icon} tone={tone} size='sm' />
      <span className='flex min-w-0 flex-1 flex-col'>
        <Text as='span' weight='semibold' truncate>
          {title}
        </Text>
        <Muted as='span' variant='caption' truncate={2}>
          {hint}
        </Muted>
      </span>
    </>
  )
}

function BookCodexLinks({ hasWorld }: { hasWorld: boolean }) {
  const noWorld = 'There is no world to write down yet'
  return (
    <Section
      title='Ledger, book and codex'
      description='Every change with its undo, the whole world as an illustrated book, and the same world as Markdown.'
      surface='card'
      level={3}
      icon={Library}
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4'>
        <LinkTile
          icon={NotebookPen}
          tone='gold'
          title='Action ledger'
          hint='Every change, each with its undo'
        >
          {(inner) => (
            <Button variant='outline' size='tile' asChild>
              <Link to='/ledger'>{inner}</Link>
            </Button>
          )}
        </LinkTile>
        <LinkTile
          icon={BookOpen}
          tone='verdigris'
          title='The book'
          hint='Read the illustrated encyclopedia'
        >
          {(inner) =>
            hasWorld ? (
              <Button variant='outline' size='tile' asChild>
                <a href={bookUrl()} target='_blank' rel='noreferrer'>
                  {inner}
                </a>
              </Button>
            ) : (
              <Button
                variant='outline'
                size='tile'
                disabled
                disabledReason={noWorld}
              >
                {inner}
              </Button>
            )
          }
        </LinkTile>
        <LinkTile
          icon={FileDown}
          tone='info'
          title='Codex with pictures'
          hint='Markdown packed with images and maps'
        >
          {(inner) =>
            hasWorld ? (
              <Button variant='outline' size='tile' asChild>
                <a href={codexUrl()} download>
                  {inner}
                </a>
              </Button>
            ) : (
              <Button
                variant='outline'
                size='tile'
                disabled
                disabledReason={noWorld}
              >
                {inner}
              </Button>
            )
          }
        </LinkTile>
        <LinkTile
          icon={FileText}
          tone='muted'
          title='Markdown only'
          hint='One file, pictures linked'
        >
          {(inner) =>
            hasWorld ? (
              <Button variant='outline' size='tile' asChild>
                <a href={codexMarkdownUrl()} download>
                  {inner}
                </a>
              </Button>
            ) : (
              <Button
                variant='outline'
                size='tile'
                disabled
                disabledReason={noWorld}
              >
                {inner}
              </Button>
            )
          }
        </LinkTile>
      </div>
      {hasWorld && <BookPdfCard />}
    </Section>
  )
}

export function RecordsSettings() {
  const state = useWorldState()
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <BookCodexLinks hasWorld={Boolean(state.data?.world)} />
      <ModelMetrics />
    </div>
  )
}
