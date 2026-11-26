import {
  Archive,
  Bot,
  ChevronDown,
  Clock,
  Database,
  FileText,
  HardDrive,
  HeartPulse,
  ImageIcon,
  Layers,
  ShieldCheck,
  Tag,
  TriangleAlert,
  Waypoints,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { formatBytes, formatDuration, plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'
import { MiniStat, Paged, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useHealth } from '@/features/images/api'
import { useRoleModel } from '@/features/providers/api'
import { useHealthReport } from './api'

const MINUTE_SECONDS = 60
const HEALTH_STATUS: Record<components['schemas']['HealthStatus'], string> = {
  ok: 'All good',
  warning: 'Recent errors',
  bad: 'Database damaged',
  degraded: 'Database checks failing',
}
const RECENT_ERRORS = 5

export function HealthPanel() {
  const report = useHealthReport()
  const data = report.data?.report
  const good = data?.status === 'ok'
  const sound = data?.database.quick_check === 'ok'
  const errors = data?.recent_errors ?? []
  const health = useHealth()
  const live = health.data
  const writingModel = useRoleModel('writing')
  const imageModel = useRoleModel('images')
  return (
    <Section
      title='Health'
      description='The server, its database and its backups.'
      surface='card'
      level={3}
      icon={HeartPulse}
      tone={data && !good ? 'danger' : 'success'}
      actions={
        data && (
          <div className='flex flex-wrap gap-1.5'>
            <Badge variant={good ? 'success' : 'destructive'}>
              {HEALTH_STATUS[data.status]}
            </Badge>
            {data.read_only && <Badge variant='warning'>Read-only</Badge>}
          </div>
        )
      }
    >
      {report.isPending && <Skeleton className='h-48 w-full' />}
      {report.isError && <Text tone='destructive'>{report.error.message}</Text>}
      {live && (
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <MiniStat
            icon={Bot}
            label='Writing model'
            value={
              !live.llm_enabled ? 'Turned off' : writingModel || 'No model set'
            }
            tone={live.llm_enabled && writingModel ? 'success' : 'warning'}
            hint='Set under Team and workspace, Models'
          />
          <MiniStat
            icon={Database}
            label='Database right now'
            value={live.database_ok ? 'Answering' : 'Not answering'}
            tone={live.database_ok ? 'success' : 'danger'}
          />
          <MiniStat
            icon={ImageIcon}
            label='Image model'
            value={imageModel || 'No model set'}
            tone={imageModel ? 'success' : 'warning'}
            hint='Set under Team and workspace, Models'
          />
          <MiniStat
            icon={Waypoints}
            label='Gateway for API keys'
            value={live.gateway_ready ? 'Ready' : 'Not configured'}
            tone={live.gateway_ready ? 'success' : 'warning'}
            hint={
              live.gateway_ready
                ? 'API keys reach their providers through it'
                : 'Set AERONA_GATEWAY_URL; docker-compose starts it for you'
            }
          />
        </div>
      )}
      {data && (
        <>
          <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
            <MiniStat
              icon={Tag}
              label='Version'
              value={data.version}
              tone='muted'
            />
            <MiniStat
              icon={Clock}
              label='Uptime'
              value={formatDuration(data.uptime_seconds)}
              tone='info'
            />
            <MiniStat
              icon={Database}
              label='Database'
              value={formatBytes(data.database.size)}
              tone='gold'
              hint={`${data.database.file} with ${formatBytes(data.database.wal_size)} of journal`}
            />
            <MiniStat
              icon={ShieldCheck}
              label='Integrity'
              value={sound ? 'Sound' : data.database.quick_check}
              tone={sound ? 'success' : 'danger'}
            />
            <MiniStat
              icon={Archive}
              label='Backups'
              value={data.backup_count}
              tone={data.backup_count > 0 ? 'verdigris' : 'warning'}
            />
            <MiniStat
              icon={HardDrive}
              label='Last backup'
              value={
                data.latest_backup_age_minutes !== null
                  ? `${formatDuration(data.latest_backup_age_minutes * MINUTE_SECONDS)} ago`
                  : 'Never'
              }
              tone={
                data.latest_backup_age_minutes !== null
                  ? 'verdigris'
                  : 'warning'
              }
              hint={data.latest_backup ?? undefined}
            />
            <MiniStat
              icon={Layers}
              label='Running jobs'
              value={data.running_jobs}
              tone={data.running_jobs > 0 ? 'info' : 'muted'}
            />
            <MiniStat
              icon={TriangleAlert}
              label='Recent errors'
              value={errors.length}
              tone={errors.length > 0 ? 'danger' : 'success'}
            />
          </div>
          <div className='flex min-w-0 items-center gap-2'>
            <FileText
              aria-hidden='true'
              className='size-icon-sm shrink-0 text-muted-foreground'
            />
            <Muted variant='caption' truncate>
              {`Log file: ${data.log_file}`}
            </Muted>
          </div>
          {errors.length > 0 && (
            <Collapsible>
              <CollapsibleTrigger asChild>
                <Button variant='ghost' size='sm' className='w-fit'>
                  <ChevronDown />
                  {errors.length === 1
                    ? 'Show the recent error'
                    : `Show the last ${plural(Math.min(errors.length, RECENT_ERRORS), 'error', 'errors')}`}
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <ul className='flex min-w-0 flex-col gap-1.5 pt-2'>
                  <Paged items={errors.slice(-RECENT_ERRORS)} as='li'>
                    {(entry, index) => (
                      <li
                        key={`${entry.at}-${index}`}
                        className='flex min-w-0 flex-col gap-0.5 rounded-md border surface-sheen border-destructive/30 bg-destructive/5 p-2'
                      >
                        <Muted variant='caption'>{`${entry.at} · ${entry.level}`}</Muted>
                        <Text variant='caption'>{entry.text}</Text>
                      </li>
                    )}
                  </Paged>
                </ul>
              </CollapsibleContent>
            </Collapsible>
          )}
        </>
      )}
    </Section>
  )
}
