import { Info, TriangleAlert } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Section } from '@/components/domain'
import { Stat, Text } from '@/components/typography'
import { Specimen } from './Specimen'
import { LONG_NAME } from './fixtures'

const ROWS = [
  { name: 'Orvael', kind: 'World', population: 1284000 },
  { name: 'Dazbush', kind: 'World', population: 402300 },
  { name: LONG_NAME, kind: 'Region', population: 1200 },
]

export function SurfaceSpecimens() {
  return (
    <Section
      title='Surfaces'
      description='Cards, alerts, tables and loading states.'
      level={3}
    >
      <Specimen name='Card'>
        <Card>
          <CardHeader>
            <CardTitle>The Salt Crown</CardTitle>
            <CardDescription>
              A legendary relic of the first age.
            </CardDescription>
            <CardAction>
              <Button variant='outline' size='sm'>
                Open
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent>
            <Text>Forged from the tears of the drowned king.</Text>
          </CardContent>
          <CardFooter>
            <Button size='sm'>Bless</Button>
            <Button size='sm' variant='ghost'>
              Dismiss
            </Button>
          </CardFooter>
        </Card>
      </Specimen>
      <Specimen name='Alert'>
        <Alert>
          <Info />
          <AlertTitle>The doom clock advanced</AlertTitle>
          <AlertDescription>
            Three leaks opened in the last epoch.
          </AlertDescription>
        </Alert>
        <Alert variant='destructive'>
          <TriangleAlert />
          <AlertTitle>Fate could not weigh the epoch</AlertTitle>
          <AlertDescription>
            The judgement will be retried before the next epoch.
          </AlertDescription>
        </Alert>
      </Specimen>
      <Specimen name='Table'>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Kind</TableHead>
              <TableHead className='text-end'>Population</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ROWS.map((row) => (
              <TableRow key={row.name}>
                <TableCell className='max-w-48'>
                  <Text as='span' truncate>
                    {row.name}
                  </Text>
                </TableCell>
                <TableCell>{row.kind}</TableCell>
                <TableCell className='text-end'>
                  <Stat value={row.population} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Specimen>
      <Specimen name='Skeleton'>
        <div className='flex min-w-0 items-center gap-3'>
          <Skeleton className='size-portrait-md rounded-full' />
          <div className='flex min-w-0 flex-1 flex-col gap-2'>
            <Skeleton className='h-meter-md w-1/2' />
            <Skeleton className='h-meter-md w-1/3' />
          </div>
        </div>
      </Specimen>
    </Section>
  )
}
