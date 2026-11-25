import { readFileSync } from 'node:fs'
import path from 'node:path'

export const APP_VERSION = readFileSync(
  path.resolve(import.meta.dirname, '../../VERSION'),
  'utf8'
).trim()
