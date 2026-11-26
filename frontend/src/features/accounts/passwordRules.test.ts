import { describe, expect, it } from 'vitest'
import { PASSWORD_MIN, passwordChecks, strengthOf } from './passwordRules'

describe('password strength', () => {
  it('calls only a password below the minimum too short', () => {
    expect(strengthOf('')).toBe(0)
    expect(strengthOf('a'.repeat(PASSWORD_MIN - 1))).toBe(1)
  })

  it('never calls a password that meets every rule too short', () => {
    const password = 'kizilgunes'
    const met = passwordChecks(password, password, ['ege']).every(
      (check) => check.met
    )
    expect(met).toBe(true)
    expect(strengthOf(password)).toBeGreaterThan(1)
  })

  it('rises with variety and length', () => {
    expect(strengthOf('kizilgunes')).toBe(2)
    expect(strengthOf('Kizilgunes7')).toBe(3)
    expect(strengthOf('Kizilgunes7donuyor')).toBe(4)
    expect(strengthOf('Kizilgunes7donuyor!')).toBe(5)
  })
})
