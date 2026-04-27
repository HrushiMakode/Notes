# ⚡ Python — Speed Revision Sheet

> **Purpose:** Night-before-the-interview rapid revision. You've already learned the concepts — this is pure recall.
> **Time:** ~20 minutes to scan everything.

---

## 🗺️ Full Curriculum Map

```mermaid
flowchart LR
    subgraph P1["🔴 Phase 1: Foundation"]
        M1["M1: Object Model"]
        M2["M2: Variables"]
        M3["M3: Data Structures"]
        M4["M4: Strings"]
        M5["M5: Functions"]
    end
    subgraph P2["🟠 Phase 2: Mechanics"]
        M6["M6: Iterators"]
        M7["M7: Decorators"]
        M8["M8: OOP"]
        M9["M9: Errors"]
        M10["M10: Comprehensions"]
    end
    subgraph P3["🔵 Phase 3: Internals"]
        M11["M11: Bytecode"]
        M12["M12: Memory"]
        M13["M13: GIL"]
    end
    subgraph P4["🟢 Phase 4: Concurrency"]
        M14["M14: Threading"]
        M15["M15: Multiprocessing"]
        M16["M16: Asyncio"]
    end
    subgraph P5["🟣 Phase 5: Production"]
        M17["M17: Imports"]
        M18["M18: Types"]
        M19["M19: Testing"]
        M20["M20: Profiling"]
    end
    subgraph P6["🔷 Phase 6: Design"]
        M21["M21: Patterns"]
        M22["M22: System Design"]
    end

    P1 --> P2 --> P3 --> P4 --> P5 --> P6

    style P1 fill:#d00000,color:#fff
    style P2 fill:#e76f51,color:#fff
    style P3 fill:#264653,color:#fff
    style P4 fill:#2a9d8f,color:#fff
    style P5 fill:#6a0572,color:#fff
    style P6 fill:#1a535c,color:#fff
```

---

## Phase 1 — Foundation (M1–M5)

### 🖼️ Object Model — Everything Is an Object

```mermaid
flowchart TD
    OBJ["Every Python Object"] --> ID["🆔 Identity\nid() — never changes"]
    OBJ --> TYPE["📦 Type\ntype() — never changes"]
    OBJ --> VAL["💎 Value\nmay or may not change"]

    VAL --> MUT["🔓 Mutable\nlist, dict, set"]
    VAL --> IMMUT["🔒 Immutable\nint, str, tuple, frozenset"]

    MUT -->|"❌ unhashable"| NOKEY["Can't be dict key\nCan't be in set"]
    IMMUT -->|"✅ hashable"| KEY["Can be dict key\nCan be in set"]

    style MUT fill:#d00000,color:#fff
    style IMMUT fill:#2d6a4f,color:#fff
    style NOKEY fill:#800f19,color:#fff
    style KEY fill:#1b4332,color:#fff
```

- `is` = identity (same `id()`) | `==` = equality (`__eq__`)
- **Only `is` for:** `None`, `True`, `False`
- Integer cache: `[-5, 256]` — CPython-specific, never rely on it

### 🖼️ Variables & Memory — Labels, Not Boxes

```mermaid
flowchart LR
    subgraph ASSIGN["a = [1,2,3]; b = a"]
        A["a"] -->|label| OBJ["[1, 2, 3]"]
        B["b"] -->|label| OBJ
    end
    subgraph REBIND["a = [4,5,6]"]
        A2["a"] --> NEW["[4, 5, 6]"]
        B2["b"] --> OLD["[1, 2, 3]"]
    end

    ASSIGN -->|"a = [4,5,6]\n(rebind a)"| REBIND

    style OBJ fill:#2a9d8f,color:#fff
    style NEW fill:#e76f51,color:#fff
    style OLD fill:#2a9d8f,color:#fff
```

- `=` never copies — just moves a label
- **Ref counting:** refcount 0 → immediately freed
- `del` deletes the **name**, not the object
- **Pass-by-object-reference:** mutate → visible. Rebind → invisible.

### 🖼️ Copy Model

```mermaid
flowchart TD
    subgraph SHALLOW["Shallow Copy"]
        SO["original"] --> OUTER1["{ }"]
        SC["copy"] --> OUTER2["{ }"]
        OUTER1 --> INNER["[shared inner]"]
        OUTER2 --> INNER
    end
    subgraph DEEP["Deep Copy"]
        DO["original"] --> DOUTER["{ }"]
        DC["copy"] --> DCOUTER["{ }"]
        DOUTER --> DI1["[inner A]"]
        DCOUTER --> DI2["[inner A']"]
    end

    style INNER fill:#d00000,color:#fff
    style DI1 fill:#2d6a4f,color:#fff
    style DI2 fill:#2d6a4f,color:#fff
```

| Method | Copies | Use for |
|--------|--------|---------|
| `=` | Nothing (new label) | Shared state |
| `.copy()` / `copy.copy()` | Top-level only | Flat structures |
| `copy.deepcopy()` | Everything recursively | Nested structures |

### 🖼️ Data Structures — Internals at a Glance

```mermaid
flowchart TD
    subgraph LIST["list — Dynamic Array"]
        LP["ptr0 | ptr1 | ptr2 | ... | empty | empty"]
    end
    subgraph DICT["dict — Compact Hash Table"]
        DI["indices (sparse)"] --> DE["entries (dense, insertion-order)"]
    end
    subgraph SET["set — Hash Table (keys only)"]
        SK["key | key | key | ..."]
    end
    subgraph TUPLE["tuple — Fixed Array"]
        TP["ptr0 | ptr1 | ptr2"]
    end

    style LIST fill:#264653,color:#fff
    style DICT fill:#2a9d8f,color:#fff
    style SET fill:#e76f51,color:#fff
    style TUPLE fill:#6a0572,color:#fff
```

| Structure | `append` | `insert(0)` | `x in` | Ordered? | Mutable? |
|-----------|----------|-------------|--------|----------|----------|
| `list` | O(1) | **O(n)** | O(n) | ✅ | ✅ |
| `dict` | O(1) | — | **O(1)** | ✅ 3.7+ | ✅ |
| `set` | O(1) | — | **O(1)** | ❌ | ✅ |
| `tuple` | — | — | O(n) | ✅ | ❌ |

### Strings & Unicode
- `str` = code points | `bytes` = raw bytes
- **`"".join(list)` = O(n). `+=` in loop = O(n²).**
- UTF-8: ASCII=1B, CJK=3B, emoji=4B
- One emoji → entire string upgrades to 4 bytes/char (PEP 393)

### 🖼️ LEGB Scope Chain

```mermaid
flowchart TD
    subgraph B["Built-in (len, print)"]
        subgraph G["Global (module level)"]
            subgraph E["Enclosing (outer function)"]
                L["Local (current function)\n← search starts HERE"]
            end
        end
    end

    style L fill:#d00000,color:#fff
    style E fill:#c44b2c,color:#fff
    style G fill:#e76f51,color:#fff
    style B fill:#f4a261,color:#000
```

- Assignment anywhere in body → local for **entire** function → `UnboundLocalError`
- **Closures capture VARIABLES, not values** → fix: `lambda i=i: i`
- Defaults evaluated **once at definition** → `None` sentinel

---

## Phase 2 — Mechanics (M6–M10)

### 🖼️ Generator Lifecycle

```mermaid
stateDiagram-v2
    [*] --> CREATED: gen = func()
    CREATED --> RUNNING: next(gen)
    RUNNING --> SUSPENDED: yield value
    SUSPENDED --> RUNNING: next(gen)
    RUNNING --> CLOSED: StopIteration
    SUSPENDED --> CLOSED: gen.close()
    CLOSED --> [*]
```

- Generator expression `(...)` → **O(1) memory, single-use**
- Generators are **permanently dead** after exhaustion

### 🖼️ Decorator Mental Model

```mermaid
flowchart LR
    ORIG["original func"] -->|"C wraps"| C["C(func)"]
    C -->|"B wraps"| B["B(C(func))"]
    B -->|"A wraps"| A["A(B(C(func)))"]

    CALL["call()"] --> A -->|"A's logic"| B -->|"B's logic"| C -->|"C's logic"| ORIG

    style ORIG fill:#2d6a4f,color:#fff
    style A fill:#d00000,color:#fff
    style B fill:#e76f51,color:#fff
    style C fill:#f4a261,color:#000
```

`@A @B @C def f` → `A(B(C(f)))`. **Always `@functools.wraps(func)`.**

### 🖼️ MRO — Diamond Inheritance

```mermaid
flowchart TD
    D["D"] --> B["B"] --> A["A"] --> OBJ["object"]
    D --> C["C"] --> A
    MRO["MRO: D → B → C → A → object\nsuper() in B calls C, NOT A!"]

    style D fill:#d00000,color:#fff
    style MRO fill:#2d6a4f,color:#fff
```

### 🖼️ `__eq__` / `__hash__` Contract

```mermaid
flowchart TD
    EQ{"a == b?"} -->|"True"| HASH{"hash(a) == hash(b)?"}
    HASH -->|"MUST be True"| OK["✅ Contract holds"]
    HASH -->|"False"| CORRUPT["💀 Silent corruption\nGhost entries in dict/set"]

    EQ -->|"False"| ANY["hash can be anything\n(collisions are OK)"]

    style OK fill:#2d6a4f,color:#fff
    style CORRUPT fill:#d00000,color:#fff
```

- Return `NotImplemented`, not `False`, for unknown types
- **Truthiness:** `__bool__()` → `__len__()` → `True`
- `@dataclass(frozen=True)` → auto correct `__eq__` + `__hash__`

### 🖼️ Exception Hierarchy

```mermaid
flowchart TD
    BE["BaseException ☠️"] --> SE["SystemExit"]
    BE --> KI["KeyboardInterrupt"]
    BE --> GE["GeneratorExit"]
    BE --> EX["Exception ✅ CATCH THIS"]
    EX --> VE["ValueError"]
    EX --> TE["TypeError"]
    EX --> KE["KeyError"]
    EX --> RE["RuntimeError"]
    EX --> OE["OSError"]

    style BE fill:#800f19,color:#fff
    style EX fill:#2d6a4f,color:#fff
```

**Never bare `except:`** — catches `KeyboardInterrupt` → unkillable process.

---

## Phase 3 — CPython Internals (M11–M13)

### 🖼️ Compilation Pipeline

```mermaid
flowchart LR
    SRC["Source (.py)"] --> TOK["Tokenizer"] --> AST["AST"] --> COMP["Compiler"] --> BC["Bytecode (.pyc)"] --> PVM["PVM Execution"]

    style SRC fill:#6a0572,color:#fff
    style BC fill:#2a9d8f,color:#fff
    style PVM fill:#d00000,color:#fff
```

### 🖼️ Memory Management — Two Mechanisms

```mermaid
flowchart TD
    subgraph PRIMARY["Reference Counting (Primary)"]
        RC["Every object has ob_refcnt\nrefcount 0 → IMMEDIATE free\n(deterministic)"]
    end
    subgraph SECONDARY["Generational GC (Cycles)"]
        G0["Gen 0\nNew objects\nThreshold: 700"] --> G1["Gen 1\nEvery 10 gen-0"]
        G1 --> G2["Gen 2\nEvery 10 gen-1"]
    end

    PRIMARY -->|"Can't handle cycles"| SECONDARY

    style PRIMARY fill:#2d6a4f,color:#fff
    style SECONDARY fill:#264653,color:#fff
    style G0 fill:#d00000,color:#fff
    style G1 fill:#e76f51,color:#fff
    style G2 fill:#264653,color:#fff
```

### 🖼️ GIL — One Microphone Room

```mermaid
gantt
    title GIL Thread Switching (5ms intervals)
    dateFormat X
    axisFormat %s

    section Thread 1
    Execute    :a1, 0, 5
    Wait       :a2, 5, 10
    Execute    :a3, 10, 15

    section Thread 2
    Wait       :b1, 0, 5
    Execute    :b2, 5, 10
    Wait       :b3, 10, 15
```

- GIL protects **CPython internals**, NOT your data
- **`counter += 1` = 3 bytecode ops** → needs `Lock`
- **Released during I/O** → threading works for I/O-bound

---

## Phase 4 — Concurrency (M14–M16)

### 🖼️ Concurrency Decision Framework

```mermaid
flowchart TD
    Q{"Bottleneck?"} -->|"I/O-bound\n< 100 tasks"| THREADS["🟢 ThreadPoolExecutor\n~8 MB/thread"]
    Q -->|"I/O-bound\n100–10,000+"| ASYNC["🟣 asyncio\n~1 KB/coroutine"]
    Q -->|"CPU-bound"| MP["🔴 ProcessPoolExecutor\n~30 MB/process"]
    Q -->|"Both"| HY["🟠 asyncio +\nrun_in_executor"]

    style THREADS fill:#2a9d8f,color:#fff
    style ASYNC fill:#6a0572,color:#fff
    style MP fill:#d00000,color:#fff
    style HY fill:#e76f51,color:#fff
```

### 🖼️ Comparison

| | Threading | Multiprocessing | Asyncio |
|---|-----------|-----------------|---------|
| **Type** | Preemptive | True parallel | Cooperative |
| **GIL** | Blocked (CPU) | Own GIL ✅ | N/A (1 thread) |
| **Memory** | ~8 MB | ~30 MB | **~1 KB** |
| **Best for** | I/O, <100 | CPU-bound | I/O, 100–10K+ |
| **Switch** | OS | OS | `await` (you) |
| **Shared state** | Yes (need Lock) | No (need IPC) | Yes (no locks*) |

*single-threaded asyncio = no preemption between `await` points

---

## Phase 5 — Production (M17–M20)

### 🖼️ Import System

```mermaid
flowchart LR
    IMP["import foo"] --> CACHE{"sys.modules?"}
    CACHE -->|"Hit"| RET["Return cached"]
    CACHE -->|"Miss"| FIND["Search sys.path"]
    FIND --> LOAD["Execute module"]
    LOAD --> STORE["Cache in sys.modules"]
    STORE --> RET

    style CACHE fill:#ff9f1c,color:#000
    style RET fill:#2d6a4f,color:#fff
```

### 🖼️ Test Pyramid

```mermaid
flowchart TD
    E2E["🔺 E2E Tests\nFew, slow, expensive"]
    INT["🔶 Integration Tests\nSome, moderate"]
    UNIT["🟩 Unit Tests\nMany, fast, cheap"]

    E2E --- INT --- UNIT

    style E2E fill:#d00000,color:#fff
    style INT fill:#e76f51,color:#fff
    style UNIT fill:#2d6a4f,color:#fff
```

- **Mock where imported, not defined**
- Fixture scopes: `function → class → module → session`

### 🖼️ Optimization Hierarchy

```mermaid
flowchart LR
    A1["Algorithm\nO(n²)→O(n)"] --> A2["Data Structure\nlist→set"] --> A3["Python-level\njoin, slots"] --> A4["C Extension\nnumpy, Cython"]

    style A1 fill:#d00000,color:#fff
    style A2 fill:#e76f51,color:#fff
    style A3 fill:#2a9d8f,color:#fff
    style A4 fill:#264653,color:#fff
```

---

## Phase 6 — Design & Architecture (M21–M22)

### 🖼️ Java Pattern → Python Way

```mermaid
flowchart LR
    S1["Strategy Pattern\n(interface + classes)"] -->|"Python"| S2["Pass a function"]
    S3["Singleton\n(private constructor)"] -->|"Python"| S4["Module-level instance"]
    S5["Iterator\n(Iterator class)"] -->|"Python"| S6["Generator function"]
    S7["Observer\n(interface + register)"] -->|"Python"| S8["Callbacks / signals"]

    style S1 fill:#800f19,color:#fff
    style S2 fill:#2d6a4f,color:#fff
    style S3 fill:#800f19,color:#fff
    style S4 fill:#2d6a4f,color:#fff
    style S5 fill:#800f19,color:#fff
    style S6 fill:#2d6a4f,color:#fff
    style S7 fill:#800f19,color:#fff
    style S8 fill:#2d6a4f,color:#fff
```

### 🖼️ Python Web Stack

```mermaid
flowchart LR
    CLIENT["Client"] --> LB["Nginx / ALB"]
    LB --> APP["Gunicorn / Uvicorn\n(2×CPU+1 workers)"]
    APP --> CODE["Django / FastAPI"]
    CODE --> CACHE["Redis"]
    CODE --> DB["PostgreSQL"]
    CODE --> QUEUE["Celery Workers"]

    style LB fill:#264653,color:#fff
    style APP fill:#2a9d8f,color:#fff
    style CODE fill:#e76f51,color:#fff
    style QUEUE fill:#6a0572,color:#fff
```

- WSGI (sync) vs ASGI (async) — Gunicorn workers = **processes** (own GIL)
- Celery tasks: **idempotent** + JSON-serializable

---

## 🔢 Key Numbers

| Item | Value |
|------|-------|
| Integer cache | `[-5, 256]` |
| `getrefcount()` overhead | +1 |
| GC thresholds | `(700, 10, 10)` |
| GIL switch interval | 5 ms |
| pymalloc limit | ≤512 bytes |
| Thread stack | ~8 MB |
| Process overhead | ~30 MB |
| Coroutine overhead | ~1 KB |
| Dict resize load factor | ~2/3 |
| Gunicorn workers | `(2 × CPU) + 1` |
| `lru_cache` default max | 128 |
| Max recursion depth | ~1000 |

---

## 💀 Top 20 Gotchas

1. `is` for values → wrong. Only for `None`/`True`/`False`
2. Integer cache `[-5, 256]` → CPython-specific
3. Mutable default `def f(x=[])` → shared across calls
4. `+=` on list = in-place. `+=` on tuple = new object
5. `del` deletes name, not object
6. Pass-by-object-reference ≠ pass-by-reference
7. `list.pop(0)` → O(n). Use `deque`
8. `defaultdict` inserts on read
9. String `+=` in loop → O(n²)
10. `len(str)` ≠ `len(bytes)` for non-ASCII
11. Generators are single-use
12. Late binding closures → `lambda i=i: i`
13. `@functools.wraps` is non-negotiable
14. `super()` follows MRO, not parent
15. Bare `except:` catches `KeyboardInterrupt`
16. `lru_cache` needs hashable args
17. `counter += 1` is NOT thread-safe
18. GIL protects CPython, NOT your code
19. `fork` + threads = deadlocks
20. Mock where it's imported, not defined

---

## 🎯 Top 15 Interview One-Liners

1. **"Pass by reference?"** → No. Pass-by-object-reference. Mutate=visible, rebind=invisible.
2. **"`is` vs `==`?"** → `is` = identity. `==` = equality. Only `is None`.
3. **"Dicts ordered?"** → Yes, insertion-ordered since 3.7 (language guarantee).
4. **"What's a closure?"** → Function capturing enclosing variables. Late binding — captures variable, not value.
5. **"Iterator vs iterable?"** → Iterable has `__iter__`. Iterator adds `__next__`. All iterators are iterable.
6. **"What's the GIL?"** → Mutex. One thread executes bytecode. Released during I/O.
7. **"`x += 1` thread-safe?"** → No. 3 bytecode ops. Use `Lock`.
8. **"Threading vs multiprocessing?"** → Threading = I/O-bound. Multiprocessing = CPU-bound.
9. **"asyncio vs threading?"** → Asyncio for 100+ concurrent I/O. 1KB/coroutine vs 8MB/thread.
10. **"Type hints runtime?"** → Zero effect. Only mypy/IDE.
11. **"Singleton in Python?"** → Module-level instance. Modules are singletons.
12. **"Memory management?"** → Refcounting (primary) + generational GC (cycles).
13. **"String concat in loop?"** → O(n²). Use `"".join()` → O(n).
14. **"`__eq__`/`__hash__` contract?"** → `a==b` → `hash(a)==hash(b)`. Violation = silent dict/set corruption.
15. **"Mutable default arg?"** → Evaluated once at definition. Fix: `None` sentinel.
