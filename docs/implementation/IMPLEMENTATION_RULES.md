# Implementation Rules for TelePlay

## Context

- **Mode**: Ponytail full, Caveman full
- **Project**: `D:\filmchi_tel\TelePlay-main`
- **Python**: `D:\Program Files (x86)\Microsoft Visual Studio\Shared\Android\AndroidNDK\android-ndk-r23c\toolchains\llvm\prebuilt\windows-x86_64\python3`
- **Monitor**: `https://teleplay-main-production.up.railway.app/auth?token=...`

---

## Agent Rules

| Rule | Details |
|------|---------|
| Max concurrent agents | 2 |
| Max tasks per agent batch | 5 |
| Periodic review | Every 5 tasks |
| Commit after | Every batch (5 tasks) |
| Pause depth | Max 30 levels |

---

## Documented Work

See `DOCUMENTED_WORK.md` for execution log and work graph.

---

## Workflow

1. Read file first
2. Edit only if needed
3. No concurrent mid-edit
4. Commit after batch
5. Review after 5 tasks
