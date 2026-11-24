import { useState } from 'react'
import { worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it, vi } from 'vitest'
import { userEvent } from 'vitest/browser'
import { FilePicker } from './FilePicker'
import { LineChart } from './LineChart'
import { MentionText } from './MentionText'
import { MultiSelect } from './MultiSelect'
import { RecordNavLink } from './RecordNavLink'
import { readThemeColors } from './useThemeColors'

const SERIES = [
  {
    key: 'population',
    label: 'Population',
    color: 'var(--chart-1)',
    points: [1, 2, 3, 4].map((x) => ({ x, y: x * 40 })),
  },
  {
    key: 'followers',
    label: 'Disciples',
    color: 'var(--chart-2)',
    points: [1, 2, 3, 4].map((x) => ({ x, y: x * 10 })),
  },
]

function Picker({ onPick }: { onPick: (file: File | null) => void }) {
  const [file, setFile] = useState<File | null>(null)
  return (
    <FilePicker
      file={file}
      accept='.aerona'
      label='Drop a package'
      onChange={(next) => {
        setFile(next)
        onPick(next)
      }}
    />
  )
}

function Choice({ onChange }: { onChange: (next: string[]) => void }) {
  const [value, setValue] = useState<string[]>([])
  return (
    <MultiSelect
      label='Kinds'
      min={2}
      options={[
        { value: 'war', label: 'War' },
        { value: 'birth', label: 'Birth' },
        { value: 'death', label: 'Death' },
      ]}
      value={value}
      onChange={(next) => {
        setValue(next)
        onChange(next)
      }}
    />
  )
}

describe('LineChart', () => {
  it('draws one line per series with end dots, a legend and a hover tooltip', async () => {
    const { screen } = await renderScreen(
      <LineChart title='Records and knowledge' series={SERIES} />
    )
    await expect
      .element(screen.getByRole('img', { name: 'Records and knowledge' }))
      .toBeVisible()
    expect(document.querySelectorAll('polyline[data-series]')).toHaveLength(2)
    expect(document.querySelectorAll('svg[role="img"] circle')).toHaveLength(2)
    expect(document.querySelector('[data-direct-label]')).toBeNull()
    const legend = screen.getByRole('list', {
      name: 'Records and knowledge legend',
    })
    await expect.element(legend).toBeVisible()
    expect(
      legend
        .getByRole('listitem')
        .elements()
        .map((item) => item.textContent)
    ).toEqual(['Population', 'Disciples'])
    expect(
      [...document.querySelectorAll('svg text')].map((node) => node.textContent)
    ).toContain('200')
    const hit = document.querySelector('[data-chart-hit]') as SVGRectElement
    const box = hit.getBoundingClientRect()
    hit.dispatchEvent(
      new PointerEvent('pointermove', {
        bubbles: true,
        clientX: box.right - 1,
        clientY: box.top + 5,
      })
    )
    await expect
      .element(screen.getByRole('tooltip'))
      .toHaveTextContent(/Epoch 4.*Population.*160.*Disciples.*40/)
    expect(document.querySelector('[data-chart-guide]')).not.toBeNull()
  })

  it('shows the last value for a single series and a fixed ceiling', async () => {
    const { screen } = await renderScreen(
      <LineChart title='Existence' series={[SERIES[1]]} max={100} />
    )
    await expect
      .element(screen.getByText('40', { exact: true }).first())
      .toBeVisible()
    expect(
      [...document.querySelectorAll('svg text')].map((node) => node.textContent)
    ).toEqual(expect.arrayContaining(['0', '50', '100', 'E1', 'E4']))
    expect(document.querySelector('[data-direct-label]')).toBeNull()
  })
})

describe('MultiSelect', () => {
  it('filters, keeps ticked items visible and counts against the minimum', async () => {
    const onChange = vi.fn()
    const { screen } = await renderScreen(<Choice onChange={onChange} />)
    await screen
      .getByRole('button', { name: 'Kinds · 0 selected · at least 2' })
      .click()
    await screen.getByRole('checkbox', { name: 'War' }).click()
    expect(onChange).toHaveBeenLastCalledWith(['war'])
    await screen.getByRole('searchbox', { name: 'Filter kinds' }).fill('bir')
    await expect
      .element(screen.getByRole('checkbox', { name: 'War' }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('checkbox', { name: 'Death' }))
      .not.toBeInTheDocument()
    await screen.getByRole('checkbox', { name: 'Birth' }).click()
    expect(onChange).toHaveBeenLastCalledWith(['war', 'birth'])
    await screen.getByRole('button', { name: 'Clear' }).click()
    expect(onChange).toHaveBeenLastCalledWith([])
  })

  it('keeps a long list inside its popover and scrolls it', async () => {
    const options = Array.from({ length: 60 }, (_, index) => ({
      value: `kind-${index}`,
      label: `Kind ${index}`,
    }))
    const { screen } = await renderScreen(
      <MultiSelect
        label='Kinds'
        options={options}
        value={[]}
        onChange={() => undefined}
      />
    )
    await screen.getByRole('button', { name: /Kinds/ }).click()
    const viewport = document.querySelector(
      '[data-slot="popover-content"] [data-slot="scroll-area-viewport"]'
    ) as HTMLElement
    const popover = document.querySelector(
      '[data-slot="popover-content"]'
    ) as HTMLElement
    expect(viewport.scrollHeight).toBeGreaterThan(viewport.clientHeight)
    expect(viewport.getBoundingClientRect().bottom).toBeLessThanOrEqual(
      popover.getBoundingClientRect().bottom
    )
  })
})

describe('FilePicker', () => {
  it('takes a dropped or chosen file, shows its size and removes it', async () => {
    const onPick = vi.fn()
    const { screen } = await renderScreen(<Picker onPick={onPick} />)
    await expect.element(screen.getByText('Drop a package')).toBeVisible()
    const zone = document.querySelector(
      '[data-domain="file-picker"]'
    ) as HTMLElement
    const transfer = new DataTransfer()
    transfer.items.add(new File(['x'.repeat(2048)], 'ember.aerona'))
    zone.dispatchEvent(
      new DragEvent('drop', {
        bubbles: true,
        cancelable: true,
        dataTransfer: transfer,
      })
    )
    await expect.element(screen.getByText('ember.aerona')).toBeVisible()
    await expect.element(screen.getByText(/2(\.0)? KB/)).toBeVisible()
    await screen.getByRole('button', { name: 'Remove' }).click()
    expect(onPick).toHaveBeenLastCalledWith(null)
    await userEvent.upload(
      screen.getByLabelText('Drop a package'),
      new File(['x'], 'cover.png', { type: 'image/png' })
    )
    await expect
      .element(screen.getByText('cover.png is not a file this accepts.'))
      .toBeVisible()
    expect(onPick).toHaveBeenCalledTimes(2)
  })
})

describe('MentionText', () => {
  it('resolves id tokens into record links that open the drawer', async () => {
    const { screen, router } = await renderScreen(
      <MentionText text='son#7 Ithren met #12 by thread#5.' />,
      {
        'GET /api/names': [
          { kind: 'son', id: 7, name: 'Ithren', type: 'son' },
          { kind: 'entity', id: 12, name: 'Velmora', type: 'settlement' },
        ],
        'GET /api/state': worldState({
          threads: [
            {
              id: 5,
              epoch: 1,
              text: 'The bell beneath the salt sea',
              status: 'open',
              closing_text: null,
              closed_epoch: null,
              progress: 0,
            },
          ],
        }),
      }
    )
    await expect
      .element(screen.getByRole('link', { name: 'Ithren' }))
      .toBeVisible()
    await expect
      .element(screen.getByText('"The bell beneath the salt sea"'))
      .toHaveAttribute('title', 'The bell beneath the salt sea')
    await screen.getByRole('link', { name: 'Velmora' }).click()
    await expect
      .poll(() => router.state.location.search)
      .toMatchObject({ entry: 'entity:12' })
  })

  it('links names of records returned with the text without asking for names', async () => {
    const { screen, server, router } = await renderScreen(
      <MentionText
        text='The Marsh Folk crossed the Glass Fen.'
        targets={[{ id: 40, name: 'Marsh Folk', kind: 'entity' }]}
      />
    )
    await screen.getByRole('link', { name: 'Marsh Folk' }).click()
    await expect
      .poll(() => router.state.location.search)
      .toMatchObject({ entry: 'entity:40' })
    expect(server.calls).toHaveLength(0)
  })

  it('renders plain text without asking for names', async () => {
    const { screen, server } = await renderScreen(
      <MentionText text='A quiet line.' />
    )
    await expect.element(screen.getByText('A quiet line.')).toBeVisible()
    expect(server.calls).toHaveLength(0)
  })
})

describe('RecordNavLink', () => {
  it('builds the cross-view links with their search params', async () => {
    const { screen } = await renderScreen(
      <div>
        <RecordNavLink to={{ view: 'map', world: 3, focus: 12 }} />
        <RecordNavLink to={{ view: 'network', focus: 12 }} />
        <RecordNavLink to={{ view: 'climate', world: 3 }} />
        <RecordNavLink to={{ view: 'atlas', type: 'people' }}>
          Peoples
        </RecordNavLink>
        <RecordNavLink to={{ view: 'chronicle', epoch: 4 }} />
      </div>
    )
    await expect
      .element(screen.getByRole('link', { name: 'Show on map' }))
      .toHaveAttribute('href', '/map?world=3&focus=12')
    await expect
      .element(screen.getByRole('link', { name: 'Show in network' }))
      .toHaveAttribute('href', '/network?focus=12')
    const climate = screen.getByRole('link', { name: 'Climate' })
    await expect.element(climate).toBeVisible()
    expect(
      decodeURIComponent(climate.element().getAttribute('href') ?? '')
    ).toContain('entry=world:3')
    await expect
      .element(screen.getByRole('link', { name: 'Peoples' }))
      .toHaveAttribute('href', '/atlas?type=people')
    await expect
      .element(screen.getByRole('link', { name: 'In the chronicle' }))
      .toHaveAttribute('href', '/chronicle?epoch=4')
  })
})

describe('useThemeColors', () => {
  it('reads resolved theme tokens and follows the theme class', () => {
    const root = document.documentElement
    root.classList.add('dark')
    const dark = readThemeColors()
    root.classList.remove('dark')
    const light = readThemeColors()
    expect(dark.dark).toBe(true)
    expect(light.dark).toBe(false)
    expect(dark.background).not.toBe('')
    expect(dark.primary).not.toBe('gray')
  })
})
