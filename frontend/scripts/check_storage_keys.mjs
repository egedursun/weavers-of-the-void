import { readFileSync, readdirSync, statSync } from 'node:fs'
import path from 'node:path'

const ROOT = path.resolve(import.meta.dirname, '..', 'src')
const STORAGE_MODULES = new Set([
  'lib/universeStorage.ts',
  'api/universeStore.ts',
  'api/workspaceStore.ts',
])
const RAW_STORAGE = /\b(?:localStorage|sessionStorage)\b/
const JSON_STORAGE = /\bcreateJSONStorage\s*\(/
const TEST_FILE = /\.test\.tsx?$|ixtures\.tsx?$|\/test-utils\//

function sources(folder) {
  return readdirSync(folder).flatMap((name) => {
    const full = path.join(folder, name)
    if (statSync(full).isDirectory())
      return name === 'generated' ? [] : sources(full)
    return /\.tsx?$/.test(name) ? [full] : []
  })
}

export function storageProblems(files) {
  const problems = []
  for (const file of files) {
    const relative = path.relative(ROOT, file).split(path.sep).join('/')
    if (STORAGE_MODULES.has(relative) || TEST_FILE.test(`/${relative}`)) continue
    const lines = readFileSync(file, 'utf8').split('\n')
    lines.forEach((line, index) => {
      if (RAW_STORAGE.test(line))
        problems.push(
          `${relative}:${index + 1}: reads or writes browser storage directly; go through storedItem/storeItem with universeKey or viewerKey, or universePersisted/viewerPersisted, so every key carries the account`
        )
      if (JSON_STORAGE.test(line))
        problems.push(
          `${relative}:${index + 1}: builds its own persisted storage; use universePersisted or viewerPersisted from lib/universeStorage so the key carries the account`
        )
    })
  }
  return problems
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const problems = storageProblems(sources(ROOT))
  for (const problem of problems) console.log(problem)
  console.log(`storage keys: ${problems.length}`)
  process.exit(problems.length === 0 ? 0 : 1)
}
