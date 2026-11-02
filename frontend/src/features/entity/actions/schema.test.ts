import { describe, expect, it } from 'vitest'
import {
  bodyOf,
  fieldsOf,
  humanize,
  initialValue,
  missingRequired,
} from './schema'

const SCHEMA = {
  $defs: {
    Miracle: { enum: ['healing', 'bounty'], type: 'string' },
    SocialClass: { enum: ['farmer', 'scribe'], type: 'string' },
  },
  properties: {
    entity_id: { type: 'integer' },
    miracle: {
      anyOf: [{ $ref: '#/$defs/Miracle' }, { type: 'null' }],
      default: null,
    },
    how: { type: 'string', default: '', maxLength: 300 },
    devour: { type: 'boolean', default: false },
    percent: {
      anyOf: [{ type: 'integer' }, { type: 'null' }],
      default: null,
      minimum: 1,
    },
    shares: {
      type: 'object',
      additionalProperties: { type: 'number' },
      propertyNames: { $ref: '#/$defs/SocialClass' },
    },
    member_ids: { type: 'array', items: { type: 'integer' } },
  },
  required: ['entity_id', 'shares'],
}

describe('action input schemas', () => {
  const fields = fieldsOf(SCHEMA)

  it('reads every field kind from the catalogue schema', () => {
    expect(fields.map((field) => [field.key, field.kind])).toEqual([
      ['entity_id', 'integer'],
      ['miracle', 'enum'],
      ['how', 'string'],
      ['devour', 'boolean'],
      ['percent', 'integer'],
      ['shares', 'map'],
      ['member_ids', 'unsupported'],
    ])
    expect(fields[1]).toMatchObject({
      options: ['healing', 'bounty'],
      required: false,
    })
    expect(fields[5]).toMatchObject({
      keys: ['farmer', 'scribe'],
      required: true,
    })
  })

  it('starts from the schema defaults', () => {
    expect(fields.map(initialValue)).toEqual([
      null,
      null,
      '',
      false,
      null,
      {},
      null,
    ])
  })

  it('reports the first missing required field, skipping the record itself', () => {
    const values = Object.fromEntries(
      fields.map((field) => [field.key, initialValue(field)])
    )
    expect(missingRequired(fields, values, new Set(['entity_id']))?.key).toBe(
      'shares'
    )
    expect(
      missingRequired(
        fields,
        { ...values, shares: { farmer: 0.5 } },
        new Set(['entity_id'])
      )
    ).toBeNull()
  })

  it('builds a body without empty optional values', () => {
    const values = {
      entity_id: 3,
      miracle: 'healing',
      how: '',
      devour: true,
      percent: null,
      shares: {},
      member_ids: null,
    }
    expect(bodyOf(fields, values, new Set(['entity_id']))).toEqual({
      miracle: 'healing',
      devour: true,
    })
  })

  it('turns keys into readable labels', () => {
    expect(humanize('son_id')).toBe('Son')
    expect(humanize('share_pct')).toBe('Share percent')
    expect(humanize('teach_knowledge')).toBe('Teach knowledge')
  })
})
