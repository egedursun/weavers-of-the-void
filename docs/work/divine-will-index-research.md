# Divine Will index: research report (2026-11-27)

## Problem

After every epoch the Divine Will index re-embeds most of the world. On the live world after epoch 8 the job read 267,099 passages, about 35 minutes at the container's rate (~230 passages/s).

## 1. Production per epoch grows

Records written per epoch on the live world:

| Epoch | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Incidents | 1,476 | 2,122 | 3,507 | 5,821 | 8,103 | 11,483 | 14,988 | 18,244 |
| Entities born | 282 | 297 | 407 | 769 | 1,106 | 1,549 | 1,938 | 2,202 |
| State changes (thousand) | 42 | 76 | 153 | 276 | 454 | 775 | 1,130 | 1,496 |
| Long entity descriptions (>300 chars) | 158 | 154 | 268 | 504 | 696 | 927 | 971 | 1,061 |

Incidents per epoch grow by about 3,300 each epoch. If that trend holds (an assumption), by epoch 50:
- each epoch writes about 160,000 incidents, and the world holds about 3.8 million;
- embedding only the new records would mean about 270,000 passages per epoch, 20 minutes at the container's rate;
- the vectors would reach about 6.5 million passages and about 5 GB of RAM.

Any method that embeds every record ahead of time grows without bound, even when it embeds only new records. Model-written prose also grows: long entity descriptions went from 158 to 1,061 per epoch.

## 2. Why the index re-reads so much today

Epoch 7 to epoch 8 (backups `aerona-epoch7` and `aerona-epoch8`, then epoch 8 itself) produced 243,161 new passages, 41.5 million tokens:

| Source | New passages |
|---|---|
| Typed sections (Beliefs, Rumours, Then and now, Account stances…) | 178,522 |
| Incidents | 49,561 |
| Chronicle | 17,285 |
| Other | about 3,000 |

The causes:
- A typed section is one passage cut into 256-token windows. Values drift every epoch and rows are inserted, so every window after a change moves.
- An incident carries its rumour list, whose fidelity drops and whose hearers grow every epoch.
- Every chronicle line of epoch 8 (17,273 of 17,273) belongs to an incident. Each line is embedded twice: alone, and inside its incident.

Stabilising the chunking does not fix it. Masking numbers and cutting at content-defined boundaries brings 41.5M tokens per epoch down only to 24.6M.

## 3. Defect: the word half of today's search finds nothing for sentences

`match_expression` makes every word required (implicit AND). A natural question such as "When was Zeotla initiated into the faith of Ombrath?" matches nothing. Today's hybrid search is therefore dense search alone.

## 4. Retrieval quality on 30 questions

The corpus is the live index: 234,767 passages. Each cell counts questions whose target record is in the top 10.

| Method | Named, EN sentence | Named, EN keywords | Named, TR sentence | Unnamed, EN sentence | Unnamed, TR sentence |
|---|---|---|---|---|---|
| Words, today (AND) | 0/21 | 7/21 | 0/21 | 0/9 | 0/9 |
| Words, BM25 OR | 12/21 | 13/21 | 6/21 | 6/9 | 0/9 |
| Meaning only | 14/21 | 12/21 | 11/21 | 4/9 | 0/9 |
| BM25 OR + meaning (RRF) | 17/21 | 16/21 | 8/21 | 5/9 | 0/9 |
| BM25 OR top 200, reranked by meaning at query time | 15/21 | 14/21 | 9/21 | 4/9 | 0/9 |

Caveat: one author wrote these 30 questions. They show a direction, not a measurement.

## 5. Scale measurements

| What | Measured |
|---|---|
| FTS5 on disk, insert | 234,767 rows in about 1.5 s (about 150,000 per second) |
| FTS5 at 2.35M rows | 1.3 GB. Queries take 8–50 ms after `optimize`; one query took 1.27 s before it. |
| Exact cosine over 2M float16 vectors | 0.21 s, 1.54 GB |
| Embedding 200 passages at query time (4 threads, laptop) | 1.14 s |

## 6. Literature (sources in the session; summary)

- **Agentic lexical search.** Claude Code and Sourcegraph Cody dropped embeddings for agentic search; neither published numbers. "Is Grep All You Need?" (arXiv 2605.15184), on conversational memory: with tool results inline, grep beat vector search in 10 of 10 harness–model pairs; with file delivery, vector search won 5 of 10. Cursor reports semantic search plus grep beating grep alone by about 12.5% on average (vendor data).
- **BM25 on entities.** BM25 is strongest on entity-centric questions: EntityQuestions top-20 accuracy, BM25 72% against DPR 50–57%.
- **Cross-lingual.** Untranslated BM25 collapses across languages; multilingual dense models bridge the gap. No study measures directly whether an LLM's query translation closes it.
- **Reranking.** BM25 with reranking at query time beats BM25 on 16 of 18 BEIR datasets. It cannot recover a record BM25 never retrieved.
- **Summary indexes (RAPTOR, GraphRAG, Zep).** They bound what is embedded, but their ingestion costs model work that grows with input. LazyGraphRAG defers that work to query time.
- **FTS5 above 10M rows.** No controlled benchmark exists.

## 7. Status

Certain:
- Embedding every record ahead of time does not scale.
- An FTS5 index on disk, fed only new rows, scales to millions of rows (measured up to 2.35M).
- The AND query is a defect.
- The agent reads sources in full through structured tools.

Open: the form of the meaning layer. Section 8 settles it with a larger evaluation and with costs.

## 8. Evaluation with 198 questions

### Setup

- **Targets.** 204 records sampled by source from the live index: 60 incidents, 30 chronicle lines, 45 typed sections, 45 entities, 8 messages, 8 epochs, and a few words, sons and councils.
- **Questions.** Haiku wrote the questions from the records; 198 were kept. Each record got a named question in Turkish and in English, and a question with no names in Turkish and in English.
- **Agent queries.** Haiku also played the Divine Will. Given the Turkish question, it wrote 1–3 search queries in the lore language, as the Ask Lore prompt instructs. This is how `search_lore` is really called, because only the agent calls it.
- **Scoring.** A question counts as found when its record is in the top 10 of any of its queries.

### Results

| Method | Named TR | Named EN | Unnamed TR | Unnamed EN | Agent, named | Agent, unnamed |
|---|---|---|---|---|---|---|
| Words, AND (today's word half) | 0 | 1 | 0 | 0 | 37 | 0 |
| BM25 OR | 104 | 178 | 8 | 85 | 183 | 82 |
| Meaning, everything embedded (close to today) | 151 | 190 | 12 | 86 | 189 | 83 |
| BM25 + meaning, everything embedded | 160 | 192 | 20 | 103 | 190 | 104 |
| BM25 + bounded layer | 108 | 152 | 29 | 72 | 174 | 86 |
| BM25 top 300 reranked at query time | 156 | 190 | 14 | 91 | 190 | 101 |
| **BM25 + bounded layer + top 300 rerank** | 144 | 187 | 28 | 97 | **192** | **105** |
| BM25 + bounded layer + top 1000 rerank | 150 | 191 | 35 | 97 | 192 | 107 |

The bounded layer is the passages of nodes (entities, sons, foreign gods, worlds, stars, the Creator), epochs, words, councils and writings: 7,117 of the 234,767 passages.

### What the results show

- With the queries the agent forms itself, "BM25 + bounded layer + top 300 rerank" matches embedding everything: 192 against 190 for named questions, 105 against 104 for unnamed ones. No record of the world is embedded ahead of time.
- Raw Turkish questions do worse without eager vectors (144 against 160). The Divine Will never sends a raw player question to `search_lore`; it searches in the lore language.
- Typed sections must stay in the word index. With them left out, finding at least the owning node for typed targets drops from 43/44 to 37/44 for named questions and from 25/44 to 7/44 for unnamed ones.

## 9. Costs (epoch 8 of the live world)

| Stage | Today | Measured for the design |
|---|---|---|
| Engine epoch (reference) | 398 s | 398 s |
| Gathering | 148 s (`BookBuilder.load_common`) | Typed rows: 22 µs a row (full `TypedIndex.load`: 1.12M rows in 24.5 s). Incidents, chronicle and entities: 2.2 s for the whole world. |
| Rows changed in the epoch | — | 679,769 distinct rows: 365,345 inserted or deleted, 124,555 with changed words, 189,869 with numbers only |
| Word index | rebuilt in memory every refresh | FTS5 on disk, about 150,000 rows/s, queries 8–50 ms at 2.35M rows after `optimize` |
| Embedding | 243,161 passages, about 1,060 s at 230/s | Bounded layer: about 3,000 new passages, about 13 s |
| Query time | about 1 ms | Rerank of 300 candidates of about 71 tokens: 1.04 s on 4 threads, 1.98 s on 2. Cached by digest, so a candidate is embedded once. |

- `load_common` spends most of its time in `Ledger.load_changes`. That turns the world's whole change history into text (1.5M new rows each epoch), and the index never reads it.
- Updating from the change feed costs about 490,000 rows × 22 µs ≈ 11 s of rendering plus about 4 s of FTS writes. That is about 4% of the engine epoch. The cost grows with the engine's own writes, at a fixed small fraction of them.

## 11. Target: one minute or less after an epoch, at epoch 100

The design of sections 8–9 still needs about 500 s after an epoch at epoch 100: about 340 s to render and index, and about 155 s of embedding. It still does work that grows with production after the epoch ends. Getting under a minute needs two changes.

### 1. The index follows the epoch while it runs

Every engine step runs in its own transaction: 504 steps in epoch 8, the longest 38 s. A separate indexer process can therefore follow `state_changes` as each step commits:
- render the changed rows (22 µs a row);
- write them to the search index;
- embed new node passages for the bounded layer.

The index lives in its own files, so the indexer never takes a write lock on the world's database. After the epoch only the tail is left: the last steps and the writes after the tick.

Measured tail in epoch 8: the last 11 engine steps plus the writes outside engine steps hold about 18,500 changes, 1.2% of the epoch's 1,495,508.

Indexing inside SQLite by triggers was rejected. Measured, it adds 10–11 µs to each inserted row and 65 µs to each row whose words change, inside the engine. Triggers also cannot resolve names.

### 2. Tantivy instead of FTS5

The two engines on the same documents (copies of the live index), 803 agent queries, BM25 top 300:

| | FTS5 | Tantivy 0.27 (block-max WAND) |
|---|---|---|
| Index 23.5M documents | about 10 min (contentless_delete) | 84 s on 8 threads, 2.6 GB |
| Query at 23.5M, no pruning | median 2,954 ms, p90 9,150 ms, max 15,043 ms | median 23 ms, p90 84 ms, max 188 ms |
| Query at 235k | median about 1 ms | median 1 ms, max 2 ms |
| BM25 quality, agent queries (198) | named 183, unnamed 82 | named 182, unnamed 90 |

FTS5 scores every match before taking the top k, so frequent terms cost more as the world grows. Pruning frequent terms fixes the time but breaks quality. With the full design, pruning terms found in more than 1% of rows drops it from 192/105 to 172/87; at 0.2%, to 129/72. Tantivy computes only the top k and needs no pruning.

### Projection at epoch 100 (linear trend; measured unit costs)

Inputs:
- About 16.4M rows change per epoch, about 11.8M of them with changed words.
- About 26,500 entities are born per epoch.
- The engine epoch takes about 8,400 s.

| | Today | Sections 8–9 | Follower + Tantivy |
|---|---|---|---|
| Work during the epoch | — | — | Rendering about 260 s, indexing about 42 s, bounded embedding about 155 s, on spare cores |
| **Wait after the epoch** | about 76,000 s | about 500 s | **about 10 s**: a tail of about 200,000 rows (1.2%) plus the passages of nodes born in the tail |
| Query | about 1 ms of vector search, but about 84 GB of vectors in memory | rerank 1–2 s | tens to hundreds of ms of BM25, plus a 1–2 s rerank |

### Still to prove before building

- Tantivy beyond 23.5M documents. The projection reaches hundreds of millions of rows by epoch 100, because typed rows are the world's state. At that size the world's own database also grows to hundreds of GB.
- The follower process inside the container: free cores and WAL readers while the engine writes.
- Tantivy is a new dependency. It is MIT licensed, ships Rust wheels for linux arm64 and x86_64, and needs an entry in THIRD_PARTY_NOTICES.

## 12. Tantivy experiment (before any integration)

### Setup

- **Documents.** Copies of the live index's 234,767 passages, each copy marked with a token of its own (`copyN`).
- **Queries.** The agent queries of the 198-question set, BM25 top 300, with no pruning.
- **Machines.**
  - macOS: Python 3.13, tantivy-py 0.27.
  - Linux: a throwaway container from `aerona-backend:local` (aarch64, 15 CPUs), tantivy installed with pip into `/tmp`.

### Scale

| Documents | Machine | Index build | Size | Query median | Query p90 | Query max |
|---|---|---|---|---|---|---|
| 234,767 | macOS | 1 s | — | 1 ms | 1 ms | 2 ms |
| 23,476,700 | macOS | 84 s | 2.6 GB | 23 ms | 84 ms | 188 ms |
| 23,476,700 | Linux container | 158 s | 2.6 GB | 37 ms | 147 ms | 312 ms |
| 93,906,800 | macOS | 283 s | 10.4 GB | 96 ms | 360 ms | 826 ms |

- Opening the index cold takes about 0 s. The first 50 queries after a cold open take 8.3 s in total at 94M docs, and 3.0 s at 23.5M docs in the container.
- Query time grows roughly in proportion to the index: 4× the documents gives about 4× the median.

### One epoch lived on the index

Each epoch replaces documents in many small commits: delete by key, then add. 60% of the keys already exist; 40% are new.

| | macOS, 94M docs, epoch-100 scale | Linux container, 23.5M docs |
|---|---|---|
| Updates | 11,800,000 in 500 commits | 2,950,000 in 125 commits |
| Time | 136 s (86,557 a second) | 48 s (61,225 a second) |
| Commit time (median / max) | 123 ms / 803 ms | 81 ms / 222 ms |
| Queries during writing (median / p90 / max) | 111 / 436 / 917 ms | 42 / 165 / 293 ms |
| Tail committed and searchable | 200,000 in 1.4 s | 50,000 in 1.0 s |
| Background merges after the epoch | settled in 1 s | settled in 0 s |
| Size after | 10.4 GB → 11.8 GB (105.9M docs) | 2.6 GB → 3.0 GB |
| Peak RSS (includes mapped index pages) | 5.8 GB | 1.3 GB |
| Queries after the epoch (median / p90 / max) | 94 / 376 / 765 ms | 40 / 180 / 388 ms |

### Against the epoch-100 target

- **Wait after the epoch.** The tail is about 200,000 rows. Rendering takes about 4.4 s at 22 µs a row; committing and making them searchable takes 1.4–4 s. The bounded-layer embeddings of the tail come on top. That is well under 60 s.
- **Keeping up during the epoch.** About 11.8M updates take 136–195 s of writing, plus about 260 s of rendering, spread over an engine epoch of about 8,400 s.
- **Queries.** About 0.1 s median and under 1 s worst case at 94–106M docs. If the projection reaches about 400M docs, the median reaches about 0.4–0.6 s and the worst case a few seconds (extrapolated from the linear growth above).

### Caveats

- Copies repeat the same vocabulary, so frequent-term posting lists are longer than a real world of the same size would have. This leans toward the pessimistic side.
- The binding's `delete_documents` is deprecated. Integration must use `delete_documents_by_term` (rule 8).
- Tantivy is MIT licensed and needs an entry in THIRD_PARTY_NOTICES.

## 10. Conclusion

**The word index covers the whole world.**
- It is FTS5 in a sidecar file per universe. It is a rebuildable cache, outside the ledger and the backups.
- It holds one document per typed row, incident, chronicle line not owned by an incident, and node passage.
- After each epoch it is updated from `state_changes` beyond the last mark, plus new incidents by id range and incidents whose rumours or steps changed.
- Queries are BM25 with OR terms.
- It is optimised periodically.

**The meaning layer has two parts.**
- Vectors kept ahead of time only for the bounded layer.
- A query-time rerank of the BM25 top 300, with vectors cached by digest.

**Retired.**
- Embedding every record.
- Gathering the whole world through `load_common`.
- The AND query.

**Risks still open.**
- Haiku wrote the questions from the records themselves, which may favour words.
- The agent was simulated, not the real Divine Will loop.
- FTS5 beyond 2.35M rows is unmeasured.
- The bounded layer grows with births: 2,202 entities born in epoch 8.

## 13. Integrated and measured (2026-11-27)

The design of sections 10–12 is integrated in `services/divine_will/` (`store.py`, `vectors.py`, `follow.py`, `passages.py`, `index.py`) and `db/record_edits.py`. The old `divine_will_chunks` table is dropped by migration `e7d2a9c4b6f1`.

### Measured on copies of the live world

| | Before | After |
|---|---|---|
| Full build, epoch-8 world | 148 s gathering plus about 1,060 s embedding | 87 s on 4 processes, the 9,483 bounded-layer vectors included |
| Refresh when nothing changed | — | 0.01 s |
| Search, query embedding and rerank of 300 candidates included | about 1 ms of vector search, with all vectors in memory | 0.5–0.9 s |
| Engine epoch 10 without the index / with the index following | — | 708 s / 662 s |
| Wait after epoch 9 ended / after epoch 10 ended | about 35 min | 0.0 s / 0.3 s |

- The two epoch-10 times differ by load from other work on the machine; the engine did not slow down.
- After epoch 10, the followed index was compared with an index built from scratch on the same database: 2,153,794 documents, none missing and none different. The 38 extra documents were spy agents that SQLite deleted by `ON DELETE CASCADE`. Such deletes reach neither the ORM nor the change record.

### Classes the equivalence guard found and closed

| Class | Closed by |
|---|---|
| Bookkeeping tables (`name_registry`, `bond_reviews`) never reach the change record | Uncaptured tables are not indexed |
| A node's own passage kept its old name | Every node passage records its own name; any change of a `nodes` row renders the node's own passages |
| Incident participants recast in place by the roles backfill | `db/record_edits.py` reports every in-place edit of a record table at commit |
| Rows deleted by a database cascade | Every reference is recorded even without a label; a deleted row or node renders every passage that names it, transitively |

### Found outside the index

`state_changes` does not record rows that SQLite deletes or sets to null by `ON DELETE CASCADE` / `SET NULL`. In epoch 10, 38 spy agents were deleted with their networks and left no record. Closed in the following commit: the capture now records every row a delete takes with it and every column it empties (spec 16 F58.5, `tests/engine/core/test_every_cascade_recorded.py`).
