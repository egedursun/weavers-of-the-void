import { formatInteger } from '@/lib/format'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { EntityLink, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useCosmicChronicle } from './api'

const LAST_EPOCHS = 8
const HEADLINES_SHOWN = 2

export function CosmicChronicleGrid({ enabled }: { enabled: boolean }) {
  const cosmic = useCosmicChronicle(LAST_EPOCHS, enabled)
  if (!enabled) return null
  const rows = cosmic.data ?? []
  const worlds = new Map<number, string>()
  for (const row of rows)
    for (const world of row.worlds) worlds.set(world.world_id, world.name)
  return (
    <Section
      id='chronicle-cosmic'
      title='The cosmic chronicle'
      description='What each world lived through, epoch by epoch.'
      level={3}
    >
      {cosmic.isPending && <Skeleton className='h-textarea w-full' />}
      {cosmic.isError && <Text tone='destructive'>{cosmic.error.message}</Text>}
      {rows.length > 0 && (
        <div className='min-w-0 overflow-x-auto'>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Epoch</TableHead>
                {[...worlds.entries()].map(([id, name]) => (
                  <TableHead key={id}>
                    <EntityLink kind='world-guide' id={String(id)}>
                      {name}
                    </EntityLink>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.epoch}>
                  <TableCell className='align-top'>
                    <div className='flex min-w-0 flex-col'>
                      <Text
                        as='span'
                        weight='medium'
                      >{`Epoch ${formatInteger(row.epoch)}`}</Text>
                      {row.name && (
                        <Muted as='span' variant='caption'>
                          {row.name}
                        </Muted>
                      )}
                    </div>
                  </TableCell>
                  {[...worlds.keys()].map((id) => {
                    const cell = row.worlds.find(
                      (world) => world.world_id === id
                    )
                    return (
                      <TableCell
                        key={id}
                        className='max-w-64 min-w-40 align-top whitespace-normal'
                      >
                        {!cell || cell.event_count === 0 ? (
                          <Muted as='span' variant='caption' italic>
                            quiet
                          </Muted>
                        ) : (
                          <div className='flex min-w-0 flex-col gap-1'>
                            <Label>{`${formatInteger(cell.event_count)} events`}</Label>
                            {cell.headlines
                              .slice(0, HEADLINES_SHOWN)
                              .map((headline, index) => (
                                <Text
                                  key={index}
                                  as='span'
                                  variant='caption'
                                  truncate={2}
                                >
                                  {headline}
                                </Text>
                              ))}
                          </div>
                        )}
                      </TableCell>
                    )
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Section>
  )
}
