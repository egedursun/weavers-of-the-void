import { describe, expect, it } from 'vitest'
import { buildPayload, fieldsOf, initialValues, routeFor } from './schemaForm'

const SCHEMA = {
  $defs: { Miracle: { enum: ['healing', 'peace'], type: 'string' } },
  properties: {
    entity_id: { title: 'Entity Id', type: 'integer' },
    miracle: {
      anyOf: [{ $ref: '#/$defs/Miracle' }, { type: 'null' }],
      default: null,
    },
    ids: { type: 'array', items: { type: 'integer' } },
    loud: { type: 'boolean', default: false },
  },
  required: ['entity_id'],
}

describe('action schema form', () => {
  it('reads fields, kinds and options from a JSON schema', () => {
    const fields = fieldsOf(SCHEMA)
    expect(
      fields.map((field) => [field.name, field.kind, field.required])
    ).toEqual([
      ['entity_id', 'integer', true],
      ['miracle', 'enum', false],
      ['ids', 'integer-list', false],
      ['loud', 'boolean', false],
    ])
    expect(fields[1].options).toEqual(['healing', 'peace'])
  })

  it('builds a typed payload and reports missing values', () => {
    const fields = fieldsOf(SCHEMA)
    const values = {
      ...initialValues(fields),
      entity_id: '42',
      ids: '1, 2',
      miracle: 'peace',
    }
    expect(buildPayload(fields, values)).toEqual({
      payload: { entity_id: 42, miracle: 'peace', ids: [1, 2] },
    })
    expect(buildPayload(fields, initialValues(fields))).toEqual({
      error: 'Entity Id is required.',
    })
  })

  it('moves path parameters out of the body', () => {
    expect(
      routeFor('/api/sons/{son_id}/bless', { son_id: 7, amount: 3 })
    ).toEqual({
      url: '/api/sons/7/bless',
      body: { amount: 3 },
    })
    expect(routeFor('/api/sons/{son_id}/bless', {})).toEqual({
      error: 'Son id is required.',
    })
  })
})
