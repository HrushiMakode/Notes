# ⚡ Python — Speed Revision Sheet

> **Purpose:** Night-before-the-interview rapid revision. You've already learned the concepts — this is pure recall.
> **Time:** ~20 minutes to scan everything.

---

## Phase 1 — Foundation (M1–M5)

### Object Model
- Everything is an object — `id()` (identity), `type()` (type), value
- `is` = identity (same object) | `==` = equality (same value via `__eq__`)
- **Only use `is` for:** `None`, `True`, `False`
- Integer cache: `[-5, 256]` — CPython-specific, never rely on it
- Mutable: `list, dict, set` | Immutable: `int, str, tuple, frozenset, bytes`
- Mutable → unhashable → can't be dict key / set member
- Tuple with mutable inside = still unhashable: `{(1, [2])}` → `TypeError`

### Variables & Memory
- Variables = labels (name bindings), NOT boxes. `=` never copies.
- **Reference counting:** refcount 0 → immediately freed (deterministic)
- `sys.getrefcount()` returns count **+1** (temp arg reference)
- **Shallow copy:** new container, shared inner objects
- **Deep copy:** everything new, recursively. Handles cycles.
- `del` deletes the **name**, not the object
- **Pass-by-object-reference:** mutate → caller sees it. Rebind → caller doesn't.
- `+=` on list → in-place (`__iadd__`). `+=` on tuple → new object.
- **Tuple `+=` puzzle:** `t=([1],); t[0]+=[2]` → `TypeError` BUT list IS mutated (step 1 succeeds, step 2 fails)

### Data Structures

| Structure | Internal | Key Operations |
|-----------|----------|---------------|
| `list` | Dynamic array of pointers | `append` O(1), `insert(0)` **O(n)**, `pop(0)` **O(n)** |
| `dict` | Hash table (compact) | O(1) avg lookup, insertion-ordered since **3.7** |
| `set` | Hash table (keys only) | O(1) membership, `\|` `&` `-` `^` operations |
| `tuple` | Fixed-size array | 27% smaller than list, hashable if contents are |

- Need a queue? → `collections.deque` (O(1) both ends)
- `defaultdict` inserts on read — silent side effect
- Never mutate dict/set during iteration → `RuntimeError`
- `__eq__` without `__hash__` → class becomes unhashable

### Strings & Unicode
- `str` = Unicode code points | `bytes` = raw bytes
- **Decode at I/O boundary, work with `str` inside, encode at boundary**
- UTF-8: 1–4 bytes/char. ASCII=1, CJK=3, emoji=4
- `len(str)` = characters. `len(bytes)` = bytes. Different for non-ASCII.
- **`"".join(list)` = O(n). `+=` in loop = O(n²).** ← interview classic
- One emoji → entire string upgrades to 4 bytes/char (PEP 393)
- f-string debug: `f"{var=}"` (3.8+)

### Functions & Scoping
- Functions are **first-class objects** — assigned, passed, returned, stored
- **LEGB:** Local → Enclosing → Global → Built-in
- Assignment anywhere in function body → **local for entire function** → `UnboundLocalError`
- `global` for module-level. `nonlocal` for enclosing scope.
- **Closures capture VARIABLES, not values** → late binding trap
- Fix: `lambda i=i: i` (default arg captures value at definition)
- Defaults evaluated **once at definition** → `None` sentinel for mutables
- `*` in signature → everything after is keyword-only

---

## Phase 2 — Mechanics (M6–M10)

### Iterators & Generators
- Iterable = has `__iter__()` | Iterator = has `__iter__()` + `__next__()`
- `for` loop → `iter()` → repeated `next()` → catches `StopIteration`
- Generator = function with `yield` — pauses and resumes
- Generator expression `(x for x in ...)` → **O(1) memory, single-use**
- `yield from` delegates to sub-generator (proxies send/throw/close)
- **Generators are single-use** — second `list(gen)` = `[]`

### Decorators
- `@dec` = `func = dec(func)` — just a function call
- **Always `@functools.wraps(func)`** — preserves `__name__`, `__doc__`
- Decorator with args = **decorator factory** (3 nesting levels)
- Stack: `@A @B @C def f` → `A(B(C(f)))`. A's wrapper executes first.

### OOP
- `__new__` creates. `__init__` initializes.
- **MRO = C3 linearization.** `super()` follows MRO, NOT parent.
- `D(B,C)` where both inherit `A` → MRO: `D → B → C → A → object`
- `__slots__` → ~40% less memory, no `__dict__`, no dynamic attrs
- **Attribute lookup:** data descriptor → instance dict → non-data descriptor → `__getattr__`
- `__repr__` = developer/debug. `__str__` = user-facing. Always implement `__repr__`.
- `print([obj])` calls `__repr__` on elements, NOT `__str__` ⚠️
- **`__eq__`/`__hash__` contract:** `a == b` → `hash(a) == hash(b)` MUST hold
- Return `NotImplemented` from `__eq__`, never `False`, for unknown types
- **Truthiness chain:** `__bool__()` → `__len__()` → always `True`
- `@dataclass(frozen=True)` → auto `__eq__` + `__hash__`, immutable

### Error Handling
- Catch `Exception`, **never bare `except:`** (catches `KeyboardInterrupt` → unkillable)
- `try / except / else / finally` — `else` = no exception, `finally` = always
- `raise X from Y` → exception chaining, preserves cause
- `__exit__` returning `True` suppresses exception — dangerous
- `@contextmanager` → generator-based context manager

### Comprehensions & Functional Tools
- Four types: `[list]` `{dict}` `{set}` `(generator)`
- `lru_cache` → args must be **hashable**. `list` arg → `TypeError`.
- `groupby` → input must be **pre-sorted**
- `itertools`: `chain`, `islice`, `groupby`, `product`, `combinations`

---

## Phase 3 — CPython Internals (M11–M13)

### Compilation & Bytecode
- Source → Tokens → AST → **Bytecode (.pyc)** → PVM execution
- Python is **compiled to bytecode**, not purely interpreted
- `.pyc` in `__pycache__/`, version-specific, invalidated on source change
- Constant folding: `24*60*60` → `86400` at compile time
- `dis.dis(func)` to inspect bytecode

### Memory Management
- **Reference counting** (primary, deterministic) + **generational GC** (cycles)
- pymalloc: objects ≤512 bytes. OS malloc: larger objects.
- **3 generations:** Gen 0 (threshold 700) → Gen 1 (every 10) → Gen 2 (every 10)
- `gc.disable()` disables cyclic GC only — refcounting still works
- `__del__` timing is unpredictable → use context managers for cleanup
- `weakref.ref()` → references that don't prevent GC

### The GIL
- **Mutex:** only one thread executes Python bytecode at a time
- Exists because refcounting is not thread-safe
- **Switches every 5ms** (`sys.getswitchinterval()`)
- GIL protects **CPython internals**, NOT your data structures
- **`counter += 1` is NOT thread-safe** — 3 bytecode ops, needs `Lock`
- **Released during I/O** → threading works for I/O-bound tasks
- CPU-bound → `multiprocessing` (separate GIL per process)

---

## Phase 4 — Concurrency (M14–M16)

### Decision Framework

```
I/O-bound, < 100 tasks    → ThreadPoolExecutor
I/O-bound, 100–10,000+    → asyncio
CPU-bound                  → ProcessPoolExecutor
Mixed                      → asyncio + run_in_executor
```

### Threading
- Works for **I/O-bound** (GIL released during I/O)
- `Lock` for mutual exclusion, `Semaphore(n)` for rate limiting
- Thread stack ~8 MB. 1000 threads = 8 GB.
- Daemon threads killed on main exit — no cleanup

### Multiprocessing
- **True CPU parallelism** — each process has own GIL
- `fork` vs `spawn`: fork is fast but unsafe with threads. Spawn is safe.
- **`if __name__ == '__main__'` guard is mandatory** (Windows/macOS)
- Everything must be **picklable** — no lambdas, no local functions
- Process overhead ~30 MB each

### Asyncio
- **Cooperative concurrency** on single thread via event loop
- Coroutine overhead ~**1 KB** vs ~8 MB per thread
- `await` = suspension point, yields control to event loop
- **Blocking calls freeze entire event loop** — use `asyncio.to_thread()`
- `asyncio.gather()` preserves input order, not completion order

---

## Phase 5 — Production (M17–M20)

### Imports
- `import` checks `sys.modules` cache → finders → loaders → cache
- Module code runs **top-to-bottom on first import** — side effects are real
- Circular import fix: function-level import, `TYPE_CHECKING` guard, restructure
- `__all__` controls `from module import *`

### Type Hints
- **ZERO runtime effect** — only `mypy` and IDEs use them
- `Optional[X]` = `X | None` (not "argument is optional")
- `Protocol` = structural typing (duck typing with type safety)
- `TYPE_CHECKING` guard breaks circular imports

### Testing
- **Arrange-Act-Assert** pattern
- **Mock where it's imported, not where it's defined**
- Fixture scopes: `function → class → module → session`
- `conftest.py` shares fixtures — auto-discovered, no import needed
- `@pytest.mark.parametrize` for data-driven tests

### Performance
- **Measure first, optimize second** — `cProfile` → `line_profiler` → `tracemalloc`
- `str += str` loop → O(n²). `"".join()` → O(n).
- `if x in list` → O(n). `if x in set` → O(1).
- Local variable lookup ~20% faster than global in hot loops
- `__slots__` for memory optimization of millions of instances

---

## Phase 6 — Design & Architecture (M21–M22)

### Design Patterns (Pythonic)
- **Strategy** → just pass a function (no interface class needed)
- **Singleton** → module-level instance (modules ARE singletons)
- **Iterator** → generator function
- **Registry** → `__init_subclass__` auto-registration
- **Resource mgmt** → context manager (`with`)
- `@dataclass` replaces Builder/DTO patterns

### System Design
- **WSGI** (sync: Django/Flask + Gunicorn) vs **ASGI** (async: FastAPI + Uvicorn)
- Gunicorn workers = **processes** (own GIL). Formula: `(2 × CPU) + 1`
- **Celery** for background tasks — tasks must be **idempotent** + JSON-serializable
- Connection pooling is mandatory (SQLAlchemy `pool_size`)
- Python strength = ecosystem + dev speed. Weakness = raw perf + GIL.

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
