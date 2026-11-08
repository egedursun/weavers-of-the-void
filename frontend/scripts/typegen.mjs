import { execFileSync } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import openapiTS, { astToString } from 'openapi-typescript'
import prettier from 'prettier'

const BACKEND_DIR = path.resolve(import.meta.dirname, '../../backend')
const OUTPUT_DIR = path.resolve(import.meta.dirname, '../src/api/generated')
const EXPORT_SCRIPT = 'import json; from aerona.main import create_app; print(json.dumps(create_app().openapi()))'

const schemaJson = execFileSync('uv', ['run', 'python', '-c', EXPORT_SCRIPT], { cwd: BACKEND_DIR, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 })
const ast = await openapiTS(JSON.parse(schemaJson), { enumValues: true })
mkdirSync(OUTPUT_DIR, { recursive: true })
const withoutComments = astToString(ast)
  .replace(/\/\*\*[\s\S]*?\*\//g, '')
  .split('\n')
  .filter((line) => !line.trim().startsWith('//'))
  .filter((line) => line.trim() !== '')
  .join('\n')
const target = path.join(OUTPUT_DIR, 'schema.ts')
const options = (await prettier.resolveConfig(target)) ?? {}
writeFileSync(target, await prettier.format(`${withoutComments}\n`, { ...options, filepath: target }))
console.log('api types generated')
