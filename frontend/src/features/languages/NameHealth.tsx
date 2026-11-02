import { Copy, Hash, ShieldAlert, Sparkle, TriangleAlert } from 'lucide-react'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, KpiTile, Medallion } from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { useNameReport } from './api'

const PERCENT = 100
const WARN_PCT = 10
const BAD_PCT = 25

export function NameHealth() {
  const report = useNameReport()
  if (report.isPending) return <Skeleton className='h-textarea w-full' />
  if (report.isError)
    return <Text tone='destructive'>{report.error.message}</Text>
  const data = report.data
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Muted>
        How well record names follow the sounds of their world's dialect. Fate
        rejects misfits as they are born; a data repair renames pending ones.
      </Muted>
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4'>
        <KpiTile
          label='Dialect misfits'
          icon={TriangleAlert}
          tone={data.misfits > 0 ? 'warning' : 'success'}
          value={data.misfits}
          hint='Names using sounds their dialect does not have'
        />
        <KpiTile
          label='Weak names'
          icon={Sparkle}
          tone={data.weak_names > 0 ? 'warning' : 'success'}
          value={data.weak_names}
          hint='Too short or built on a tired motif word'
        />
        <KpiTile
          label='Numbered borrowings'
          icon={Hash}
          tone={data.numbered_borrowed_names > 0 ? 'warning' : 'success'}
          value={data.numbered_borrowed_names}
          hint='Numbered names taken from another kind of record'
        />
        <KpiTile
          label='God lookalikes'
          icon={Copy}
          tone={data.god_lookalikes > 0 ? 'danger' : 'success'}
          value={data.god_lookalikes}
          hint='Names too close to a god of the pantheon'
        />
      </div>
      {data.worlds.length === 0 ? (
        <EmptyState
          icon={ShieldAlert}
          size='compact'
          title='No named records yet'
          description='The report fills as worlds name their records.'
        />
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
          {data.worlds.map((world) => {
            const tone =
              world.misfit_pct >= BAD_PCT
                ? 'danger'
                : world.misfit_pct >= WARN_PCT
                  ? 'warning'
                  : 'success'
            return (
              <li
                key={world.world_id}
                className='flex min-w-0 items-center gap-3 rounded-xl border bg-background p-3'
              >
                <Medallion icon={TriangleAlert} tone={tone} size='sm' />
                <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
                  <div className='flex min-w-0 items-center justify-between gap-2'>
                    <Text as='span' weight='medium' truncate>
                      {world.world_name}
                    </Text>
                    <Stat
                      value={`${world.misfit_pct}%`}
                      tone={
                        tone === 'danger'
                          ? 'destructive'
                          : tone === 'warning'
                            ? 'warning'
                            : 'success'
                      }
                    />
                  </div>
                  <Progress
                    size='sm'
                    tone={
                      tone === 'danger'
                        ? 'destructive'
                        : tone === 'warning'
                          ? 'warning'
                          : 'success'
                    }
                    value={Math.min(PERCENT, world.misfit_pct)}
                    aria-label={`Misfit share in ${world.world_name}`}
                  />
                  <Label>{`${world.misfits} of ${world.named} names misfit`}</Label>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
