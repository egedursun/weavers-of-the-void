import '@/styles/index.css'
import { describe, expect, it, vi } from 'vitest'
import { render } from 'vitest-browser-react'
import { ServerLineList } from './ServerLineList'
import { ToolCard } from './ToolCard'

describe('ServerLineList', () => {
  it('renders server text and tool links', async () => {
    const onTool = vi.fn()
    const screen = await render(
      <ServerLineList
        lines={[
          {
            key: 'a',
            text: 'Rival siblings stir.',
            tension: true,
            tools: ['challenge'],
          },
        ]}
        emptyText='Nothing.'
        onTool={onTool}
      />
    )
    await expect
      .element(screen.getByText('Rival siblings stir.'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'challenge' }).click()
    expect(onTool).toHaveBeenCalledWith('challenge')
  })

  it('shows the empty text', async () => {
    const screen = await render(
      <ServerLineList lines={[]} emptyText='Nothing stands out.' />
    )
    await expect
      .element(screen.getByText('Nothing stands out.'))
      .toBeInTheDocument()
  })
})

describe('ToolCard', () => {
  it('shows costs and description', async () => {
    const screen = await render(
      <ToolCard
        tool={{
          name: 'send_dream',
          description: 'Send a dream.',
          actionCost: 1,
          essenceCost: 10,
          readOnly: false,
          longJob: false,
          minimumRarity: 'Rare',
        }}
      />
    )
    await expect.element(screen.getByText('send_dream')).toBeInTheDocument()
    await expect.element(screen.getByText('Send a dream.')).toBeInTheDocument()
    await expect.element(screen.getByText('from Rare')).toBeInTheDocument()
  })
})
