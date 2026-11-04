import { Crown, Languages, TriangleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { EmptyState, EntityLink, Section, StatBar } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useTongues } from '@/features/entity/lore/api'

const PERCENT = 100
const SHADES = [
  'bg-muted/30',
  'bg-primary/10',
  'bg-primary/20',
  'bg-primary/35',
  'bg-primary/50',
  'bg-primary/70',
] as const

function shade(value: number): string {
  return SHADES[
    Math.min(
      SHADES.length - 1,
      Math.floor((value / PERCENT) * (SHADES.length - 1))
    )
  ]
}

export function TongueAtlas({ worldId }: { worldId: number | null }) {
  const view = useTongues(worldId)
  if (worldId === null)
    return <Muted>Choose a world to see how its tongues stand.</Muted>
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Section
        id='section-prestige'
        title='Prestige of tongues'
        description='Which tongue the powerful, the learned and the holy speak.'
        icon={Crown}
      >
        {view.isPending && <Muted>Weighing the tongues…</Muted>}
        {view.isError && (
          <EmptyState
            icon={TriangleAlert}
            title='The tongues could not be weighed'
            description={view.error.message}
          />
        )}
        {view.data && (
          <ol
            data-surface='PrestigeRanking'
            className='flex min-w-0 flex-col gap-2'
          >
            {view.data.ranking.map((row, index) => (
              <li
                key={row.language.id}
                className='flex min-w-0 flex-wrap items-center gap-2'
              >
                <Text as='span' weight='semibold'>{`${index + 1}.`}</Text>
                <EntityLink kind='entity' id={String(row.language.id)}>
                  {row.language.name}
                </EntityLink>
                <div className='min-w-0 flex-1'>
                  <StatBar
                    label={`${row.speakers} speak it`}
                    value={row.prestige}
                    max={PERCENT}
                  />
                </div>
                <span className='flex gap-1'>
                  {row.lingua_franca && (
                    <Badge variant='info'>lingua franca</Badge>
                  )}
                  {row.liturgical && (
                    <Badge variant='outline'>liturgical</Badge>
                  )}
                </span>
              </li>
            ))}
          </ol>
        )}
      </Section>
      <Section
        id='section-intelligibility'
        title='Who understands whom'
        description='How much each tongue makes of every other; darker is closer.'
        icon={Languages}
      >
        {view.data && view.data.ranking.length > 0 && (
          <div
            data-surface='IntelligibilityHeatmap'
            className='min-w-0 overflow-x-auto'
          >
            <table className='border-separate border-spacing-0.5'>
              <thead>
                <tr>
                  <th />
                  {view.data.ranking.map((row) => (
                    <th
                      key={row.language.id}
                      scope='col'
                      className='max-w-8 truncate px-1 text-left align-bottom'
                    >
                      <Muted as='span' variant='caption'>
                        {row.language.name}
                      </Muted>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {view.data.ranking.map((row, line) => (
                  <tr key={row.language.id}>
                    <th scope='row' className='pr-2 text-left'>
                      <Muted as='span' variant='caption'>
                        {row.language.name}
                      </Muted>
                    </th>
                    {(view.data.matrix[line] ?? []).map((value, column) => (
                      <td
                        key={view.data.ranking[column]?.language.id ?? column}
                        title={`${row.language.name} → ${view.data.ranking[column]?.language.name ?? ''}: ${value}%`}
                        className={`size-control-sm rounded-sm text-center ${shade(value)}`}
                      >
                        <Muted as='span' variant='caption'>
                          {value}
                        </Muted>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  )
}
