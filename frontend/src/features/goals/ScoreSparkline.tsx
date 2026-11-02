import { LineChart } from '@/components/domain/LineChart'

export function ScoreSparkline({ history }: { history: number[][] }) {
  if (history.length < 2) return null
  return (
    <LineChart
      label='Score over the epochs'
      bare
      xLabel={(epoch) => `E${epoch}`}
      tooltipLabel={(epoch) => `Epoch ${epoch}`}
      series={[
        {
          key: 'score',
          label: 'Score',
          color: 'var(--primary)',
          points: history.map(([epoch, total]) => ({ x: epoch, y: total })),
        },
      ]}
    />
  )
}
