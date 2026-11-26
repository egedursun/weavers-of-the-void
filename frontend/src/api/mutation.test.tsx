import { useQuery, useQueryClient } from '@tanstack/react-query'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { Button } from '@/components/ui/button'
import { useMutation } from './mutation'

const FLAG_KEY = ['world', 'flag'] as const

type Gate = { promise: Promise<boolean>; open: (value: boolean) => void }

function gate(): Gate {
  let open: (value: boolean) => void = () => undefined
  const promise = new Promise<boolean>((resolve) => {
    open = resolve
  })
  return { promise, open }
}

function FlagToggle({ fetches }: { fetches: Gate[] }) {
  const queryClient = useQueryClient()
  const flag = useQuery({
    queryKey: FLAG_KEY,
    queryFn: () => {
      const next = gate()
      fetches.push(next)
      return next.promise
    },
  })
  const toggle = useMutation({
    mutationFn: async (next: boolean) => next,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: FLAG_KEY })
    },
  })
  const shown = toggle.isPending ? toggle.variables : flag.data
  return (
    <Button act={toggle} onClick={() => toggle.mutate(!shown)}>
      {shown ? 'Flag on' : 'Flag off'}
    </Button>
  )
}

describe('a gated mutation', () => {
  it('keeps showing the chosen value until the refetch its success started lands', async () => {
    const fetches: Gate[] = []
    const { screen } = await renderScreen(<FlagToggle fetches={fetches} />)
    await expect.poll(() => fetches.length).toBe(1)
    fetches[0].open(false)
    await expect
      .element(screen.getByRole('button', { name: 'Flag off' }))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Flag off' }).click()
    await expect.poll(() => fetches.length).toBe(2)
    await new Promise((resolve) => setTimeout(resolve, 50))
    await expect
      .element(screen.getByRole('button', { name: 'Flag on' }))
      .toBeVisible()
    fetches[1].open(true)
    await expect
      .element(screen.getByRole('button', { name: 'Flag on' }))
      .toBeVisible()
  })
})
