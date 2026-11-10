import { describe, expect, it } from 'vitest'
import { type TechGraph } from './api'
import { boostText, gateText } from './learningModel'

const GRAPH = {
  branches: [],
  capabilities: [],
  techniques: [
    {
      technique: 'siegecraft',
      branch: 'engineering',
      level: 2,
      label: 'Siegecraft',
      effect: '',
      all_of: [{ branch: 'engineering', level: 2 }],
      any_of: [
        { branch: 'metallurgy', level: 1 },
        { branch: 'military', level: 2 },
      ],
      institution: false,
    },
  ],
  triggers: [
    { trigger: 'war_won', label: 'A war won', techniques: ['siegecraft'] },
  ],
} as unknown as TechGraph

describe('the gates of the technique tree', () => {
  it('names the levels a technique needs and what hastens it', () => {
    expect(gateText(GRAPH, 'siegecraft')).toMatch(
      /^Needs .+ 2 and one of .+ 1, .+ 2$/
    )
    expect(boostText(GRAPH, 'siegecraft')).toBe('Hastened by a war won')
    expect(gateText(GRAPH, 'horse_archery')).toBeNull()
    expect(boostText(GRAPH, 'horse_archery')).toBeNull()
  })
})
