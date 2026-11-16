import { useState } from 'react'
import {
  Archive,
  ArchiveRestore,
  Database,
  Download,
  HardDrive,
  Hourglass,
  Package,
  ShieldCheck,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatBytes } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  Medallion,
  MiniStat,
  Paged,
  Section,
} from '@/components/domain'
import { Label, Text } from '@/components/typography'
import { VerifyBackupButton } from '@/features/maintenance/VerifyBackupButton'
import { useRuleValue } from '@/features/world-rules/api'
import { SecondaryTargetForm } from './SecondaryTargetForm'
import { TypedConfirm } from './TypedConfirm'
import {
  type BackupInfo,
  RESTORE_WORD,
  databaseUrl,
  packageUrl,
  useBackups,
  useRestoreBackup,
  useTakeBackup,
} from './api'

const KEEP_RULE = 'backup.recent_epoch_backups'
const MILESTONE_RULE = 'backup.milestone_epoch_multiple'

const dateTime = new Intl.DateTimeFormat('en-US', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

type BackupsPanelProps = {
  readOnly: boolean
}

const SAFETY = /safety/i
const EPOCH = /epoch/i

function backupLook(backup: BackupInfo) {
  const text = `${backup.label} ${backup.file}`
  if (SAFETY.test(text)) return { icon: ShieldCheck, tone: 'warning' as const }
  if (EPOCH.test(text)) return { icon: Hourglass, tone: 'verdigris' as const }
  return { icon: Archive, tone: 'gold' as const }
}

function BackupRow({
  backup,
  readOnly,
  onRestore,
}: {
  backup: BackupInfo
  readOnly: boolean
  onRestore: (backup: BackupInfo) => void
}) {
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <Medallion
        icon={backupLook(backup).icon}
        tone={backupLook(backup).tone}
        size='sm'
      />
      <div className='flex min-w-0 flex-1 basis-60 flex-col gap-0.5'>
        <Text weight='medium' truncate>
          {backup.label || backup.file}
        </Text>
        <Label truncate>
          {`${backup.file} · ${formatBytes(backup.size)} · ${dateTime.format(new Date(backup.modified))}`}
        </Label>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <VerifyBackupButton file={backup.file} />
        <Button variant='outline' size='sm' asChild>
          <a href={databaseUrl(backup.file)} download title='The database only'>
            <Database />
            Database
          </a>
        </Button>
        <Button variant='outline' size='sm' asChild>
          <a
            href={packageUrl(backup.file)}
            download
            title='A shareable package with its images'
          >
            <Package />
            Package
          </a>
        </Button>
        <Button
          variant='destructive'
          size='sm'
          disabled={readOnly}
          disabledReason='A guest world is read-only'
          onClick={() => onRestore(backup)}
        >
          <ArchiveRestore />
          Restore
        </Button>
      </div>
    </li>
  )
}

export function BackupsPanel({ readOnly }: BackupsPanelProps) {
  const backups = useBackups()
  const take = useTakeBackup()
  const restore = useRestoreBackup()
  const keep = useRuleValue(KEEP_RULE)
  const milestone = useRuleValue(MILESTONE_RULE)
  const [target, setTarget] = useState<BackupInfo | null>(null)
  return (
    <Section
      title='Backups'
      description={`A full copy of the world is taken before every epoch${keep !== null ? `; the last ${keep} are kept` : ''}${milestone !== null ? `, and every ${milestone}th epoch's copy is always kept` : ''}. Restoring first takes a safety backup, so a restore can be undone too.`}
      surface='card'
      level={3}
      icon={Archive}
      tone='verdigris'
      actions={
        <Button
          variant='outline'
          size='sm'
          disabled={take.isPending || readOnly}
          disabledReason={
            readOnly ? 'A guest world is read-only' : 'Taking a backup'
          }
          onClick={() =>
            take.mutate(undefined, {
              onSuccess: (backup) =>
                toast.success(`Backup taken: ${backup.file}`),
              onError: (error) => toast.error(error.message),
            })
          }
        >
          <Archive />
          Take a backup now
        </Button>
      }
    >
      {backups.isPending && <Skeleton className='h-24 w-full' />}
      {backups.isError && (
        <Text tone='destructive'>{backups.error.message}</Text>
      )}
      {backups.data && backups.data.length === 0 && (
        <EmptyState
          size='compact'
          icon={Download}
          title='No backups yet'
          description='The first backup is written before the first epoch runs.'
        />
      )}
      {backups.data && backups.data.length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
          <MiniStat
            icon={Archive}
            label='Kept copies'
            value={backups.data.length}
            tone='verdigris'
          />
          <MiniStat
            icon={HardDrive}
            label='Space used'
            value={formatBytes(
              backups.data.reduce((sum, item) => sum + item.size, 0)
            )}
            tone='info'
          />
          <MiniStat
            icon={Hourglass}
            label='Newest'
            value={dateTime.format(new Date(backups.data[0].modified))}
            tone='gold'
          />
        </div>
      )}
      {backups.data && backups.data.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={backups.data} as='li'>
            {(backup) => (
              <BackupRow
                key={backup.file}
                backup={backup}
                readOnly={readOnly}
                onRestore={setTarget}
              />
            )}
          </Paged>
        </ul>
      )}
      <SecondaryTargetForm readOnly={readOnly} />
      <TypedConfirm
        open={target !== null}
        onOpenChange={(open) => !open && setTarget(null)}
        title='Restore this backup?'
        description={`The world returns to the moment of ${target?.file ?? ''}. A safety backup of the current world is taken first.`}
        word={RESTORE_WORD}
        confirmText='Restore'
        loading={restore.isPending}
        onConfirm={(word) => {
          if (!target) return
          restore.mutate(
            { file: target.file, confirm: word },
            {
              onSuccess: (result) => {
                setTarget(null)
                toast.success(
                  `The world returned to the backup. Safety copy: ${result.safety_backup}`
                )
              },
              onError: (error) => toast.error(error.message),
            }
          )
        }}
      />
    </Section>
  )
}
