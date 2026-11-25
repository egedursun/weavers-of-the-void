import { useId, useState } from 'react'
import {
  Database,
  Download,
  Eye,
  Images,
  Merge,
  PackageOpen,
  Replace,
  Share2,
  Upload,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Medallion, Section } from '@/components/domain'
import { FilePicker } from '@/components/domain/FilePicker'
import { type Choice, ChoiceTiles } from '@/components/domain/SettingsKit'
import { Muted, Text } from '@/components/typography'
import { MergeExplanation, MergeSummaryView } from './MergeSummaryView'
import { TypedConfirm } from './TypedConfirm'
import {
  type ImportMode,
  type ImportResult,
  MERGE_WORD,
  REPLACE_WORD,
  exportUrl,
  useImportWorld,
} from './api'

const PACKAGE_ACCEPT = '.aerona,application/gzip,application/octet-stream'

const MODES: readonly Choice<ImportMode>[] = [
  {
    value: 'discovery',
    label: 'Discovery',
    hint: 'Browse it read-only beside your world',
    icon: Eye,
  },
  {
    value: 'merge',
    label: 'Merge',
    hint: 'Add its entities and places to your world',
    icon: Merge,
  },
  {
    value: 'replace',
    label: 'Replace',
    hint: 'It takes the place of your world',
    icon: Replace,
  },
]

type ShareWorldProps = {
  hasWorld: boolean
  readOnly: boolean
}

export function ShareWorld({ hasWorld, readOnly }: ShareWorldProps) {
  const importer = useImportWorld()
  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState<ImportMode>('discovery')
  const [confirming, setConfirming] = useState(false)
  const [merged, setMerged] = useState<ImportResult | null>(null)
  const pickerId = useId()

  const run = (confirm: string | null) => {
    if (!file) return
    importer.mutate(
      { file, mode, confirm },
      {
        onSuccess: (result) => {
          setConfirming(false)
          setMerged(result.merge ? result : null)
          toast.success(
            result.mode === 'discovery'
              ? `${result.world.name} opened read-only`
              : result.mode === 'merge'
                ? `${result.world.name} merged`
                : `${result.world.name} imported`
          )
          setFile(null)
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }

  const action =
    mode === 'replace'
      ? { icon: Replace, label: 'Import and replace' }
      : mode === 'merge'
        ? { icon: Merge, label: 'Merge into my world' }
        : { icon: Eye, label: 'Open read-only' }
  return (
    <Section
      title='Share the world'
      description="The whole world becomes one package with its database and images. Open someone else's world read-only beside yours, merge it into yours, or let it replace yours."
      surface='card'
      level={3}
      icon={Share2}
      tone='info'
    >
      <div className='grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-3'>
        <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={PackageOpen} tone='gold' size='sm' />
            <div className='flex min-w-0 flex-col'>
              <Text as='span' weight='semibold'>
                Export
              </Text>
              <Muted as='span' variant='caption'>
                One .aerona file to keep or send.
              </Muted>
            </div>
          </div>
          <Button
            className='self-start'
            variant='outline'
            size='tile'
            disabled={!hasWorld}
            disabledReason='There is no world to export yet'
            asChild={hasWorld}
          >
            {hasWorld ? (
              <a href={exportUrl(true)} download>
                <Medallion icon={Images} tone='gold' size='sm' />
                <span className='flex min-w-0 flex-1 flex-col'>
                  <Text as='span' weight='semibold'>
                    With images
                  </Text>
                  <Muted as='span' variant='caption'>
                    Everything, ready to share
                  </Muted>
                </span>
                <Download aria-hidden='true' className='size-icon-sm' />
              </a>
            ) : (
              <>
                <Medallion icon={Images} tone='muted' size='sm' />
                <Text as='span' weight='semibold'>
                  With images
                </Text>
              </>
            )}
          </Button>
          <Button
            className='self-start'
            variant='outline'
            size='tile'
            disabled={!hasWorld}
            disabledReason='There is no world to export yet'
            asChild={hasWorld}
          >
            {hasWorld ? (
              <a href={exportUrl(false)} download>
                <Medallion icon={Database} tone='verdigris' size='sm' />
                <span className='flex min-w-0 flex-1 flex-col'>
                  <Text as='span' weight='semibold'>
                    Without images
                  </Text>
                  <Muted as='span' variant='caption'>
                    The lore only, much smaller
                  </Muted>
                </span>
                <Download aria-hidden='true' className='size-icon-sm' />
              </a>
            ) : (
              <>
                <Medallion icon={Database} tone='muted' size='sm' />
                <Text as='span' weight='semibold'>
                  Without images
                </Text>
              </>
            )}
          </Button>
        </div>
        <form
          className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4 xl:col-span-2'
          onSubmit={(event) => {
            event.preventDefault()
            if (!file) return
            if (mode !== 'discovery') setConfirming(true)
            else run(null)
          }}
        >
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={Upload} tone='info' size='sm' />
            <div className='flex min-w-0 flex-col'>
              <Text as='span' weight='semibold'>
                Import
              </Text>
              <Muted as='span' variant='caption'>
                Open a package someone shared with you.
              </Muted>
            </div>
          </div>
          <FilePicker
            id={pickerId}
            file={file}
            onChange={setFile}
            accept={PACKAGE_ACCEPT}
            label='Drop a .aerona package here'
            hint='Exported from Weavers of the Void with or without its images.'
            disabledReason={importer.isPending ? 'Importing' : null}
          />
          <ChoiceTiles
            label='How it opens'
            value={mode}
            options={MODES}
            onChange={setMode}
          />
          {mode !== 'discovery' && (
            <Text variant='caption' tone='warning'>
              {`A safety backup of the current world is taken before it is ${mode === 'merge' ? 'merged' : 'replaced'}.`}
            </Text>
          )}
          {mode === 'merge' && <MergeExplanation />}
          <Button
            act={importer}
            type='submit'
            className='self-start'
            variant={mode === 'discovery' ? 'default' : 'destructive'}
            disabled={
              !file || importer.isPending || (readOnly && mode !== 'discovery')
            }
            disabledReason={
              !file
                ? 'Choose a .aerona file first'
                : readOnly
                  ? 'Return to your own world before changing it'
                  : 'Importing'
            }
          >
            <action.icon />
            {action.label}
          </Button>
        </form>
      </div>
      <TypedConfirm
        act={importer}
        open={confirming}
        onOpenChange={setConfirming}
        title={
          mode === 'merge' ? 'Merge into your world?' : 'Replace your world?'
        }
        description={
          mode === 'merge'
            ? `${file?.name ?? 'The package'} is added to your world. Its sons, creator, ledger and jobs stay behind. A safety backup is taken first.`
            : `${file?.name ?? 'The package'} takes the place of your world. A safety backup is taken first.`
        }
        word={mode === 'merge' ? MERGE_WORD : REPLACE_WORD}
        confirmText={
          mode === 'merge' ? 'Merge into my world' : 'Replace my world'
        }
        loading={importer.isPending}
        onConfirm={run}
      />
      {merged?.merge && <MergeSummaryView summary={merged.merge} />}
    </Section>
  )
}
