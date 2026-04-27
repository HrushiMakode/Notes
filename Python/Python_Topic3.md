# 🐍 Topic 3: Iterators & Generators

## Why Do Iterators Exist?

Iterators enable **lazy evaluation** — producing values one at a time on demand, instead of storing entire sequences in memory. Process a 10GB file line-by-line with constant memory usage.

> **Core idea:** Iterators separate the concept of a sequence from how/when values are produced.

---

## The Iteration Protocol — Two Distinct Concepts

### Iterable — "I CAN be iterated"

- Implements `__iter__()` → returns an **iterator**
- Can be iterated **multiple times** (creates a new iterator each time)
- Examples: `list`, `tuple`, `dict`, `str`, `set`, `range`, `file`

### Iterator — "I AM iterating"

- Implements `__iter__()` (returns `self`) + `__next__()` (returns next value)
- **Single-use**, one direction only
- Raises `StopIteration` when exhausted

```
Iterable                    Iterator
────────                    ────────
Has __iter__()         Has __iter__() (returns self)
Returns an Iterator    Has __next__()

  list ──__iter__()──→  list_iterator
  dict ──__iter__()──→  dict_keyiterator
  str  ──__iter__()──→  str_ascii_iterator
```

> **Analogy:** Iterable = a **book** (read it many times). Iterator = a **bookmark** (tracks position, goes forward only).

---

## What `for` Does Under the Hood

```python
for item in [1, 2, 3]:
    print(item)

# Translates to:
_iter = iter([1, 2, 3])       # Step 1: Call __iter__() → get iterator
while True:
    try:
        item = next(_iter)     # Step 2: Call __next__() → get value
    except StopIteration:      # Step 3: StopIteration = loop ends
        break
    print(item)
```

---

## Custom Iterator — Two-Class Pattern

### Problem: Single-class iterators are single-use

```python
class CountDown:
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        return self

    def __next__(self):
        if self.n <= 0:
            raise StopIteration
        value = self.n
        self.n -= 1
        return value

>>> c = CountDown(3)
>>> list(c)  → [3, 2, 1]
>>> list(c)  → []           # Exhausted! Can't restart.
```

### Fix: Separate Iterable from Iterator

```python
class CountDown:
    """Iterable — can create multiple iterators."""
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        return CountDownIterator(self.n)   # Fresh iterator each time


class CountDownIterator:
    """Iterator — tracks position, single-use."""
    def __init__(self, n):
        self.current = n

    def __iter__(self):
        return self

    def __next__(self):
        if self.current <= 0:
            raise StopIteration
        value = self.current
        self.current -= 1
        return value

>>> c = CountDown(3)
>>> list(c)  → [3, 2, 1]
>>> list(c)  → [3, 2, 1]   # ✅ Works again!
```

> This is exactly how `list` works — each `for` loop creates a fresh `list_iterator`.

---

## Generators — Iterators Made Easy

A function with `yield` is a **generator function**. Calling it returns a **generator object** (which is an iterator).

```python
def countdown(n: int):
    while n > 0:
        yield n
        n -= 1
```

```python
>>> gen = countdown(3)
>>> type(gen)         → <class 'generator'>
>>> next(gen)         → 3
>>> next(gen)         → 2
>>> next(gen)         → 1
>>> next(gen)         → StopIteration
```

### How `yield` Works:

- **`yield` suspends** the function, saving its entire local state (variables, instruction pointer)
- **`next()` resumes** from exactly where it left off
- Calling the generator function **doesn't execute the body** — it just creates the generator object

```python
def my_gen():
    print("Start")
    yield 1
    print("After first yield")
    yield 2
    print("End")

>>> g = my_gen()     # Nothing prints!
>>> next(g)          # Prints "Start", returns 1
>>> next(g)          # Prints "After first yield", returns 2
>>> next(g)          # Prints "End", raises StopIteration
```

### Exhausted generators are permanently dead:

```python
>>> next(g)          → StopIteration  # Every time, forever.
>>> next(g, None)    → None           # Safe alternative with default
```

> You cannot restart a generator. You must create a **new generator object**.

---

## Generator Expressions — One-Liner Generators

```python
# List comprehension — full list in memory
squares_list = [x**2 for x in range(1_000_000)]   # ~8MB

# Generator expression — lazy, almost no memory
squares_gen = (x**2 for x in range(1_000_000))     # ~200 bytes
```

### When to use which:

| Use | When |
|---|---|
| **List comp** `[...]` | Need multiple passes, indexing, `len()`, or small data |
| **Gen expr** `(...)` | Single-pass, large/infinite data, feeding into `sum()`, `max()`, `any()` |

```python
# Perfect for genexpr — sum() only needs one pass
total = sum(x**2 for x in range(1_000_000))  # No intermediate list!
```

---

## `yield from` — Delegating to Sub-Generators

```python
# Without yield from
def flatten(nested):
    for sublist in nested:
        for item in sublist:
            yield item

# With yield from
def flatten(nested):
    for sublist in nested:
        yield from sublist
```

### Recursive flattening:

```python
def flatten_deep(data):
    for item in data:
        if isinstance(item, list):
            yield from flatten_deep(item)
        else:
            yield item

>>> list(flatten_deep([1, [2, [3, [4]], 5], 6]))
[1, 2, 3, 4, 5, 6]
```

### Beyond sugar — `yield from` also proxies:

- `.send()` → forwarded to the sub-generator
- `.throw()` → forwarded to the sub-generator
- `.close()` → forwarded to the sub-generator

Without `yield from`, you'd manually handle all this forwarding.

---

## Generator Methods: `.send()`, `.throw()`, `.close()`

### `.send(value)` — Push data INTO a generator

```python
def accumulator():
    total = 0
    while True:
        value = yield total
        total += value

>>> acc = accumulator()
>>> next(acc)          → 0     # Must prime first!
>>> acc.send(10)       → 10
>>> acc.send(20)       → 30
```

> ⚠️ Must call `next()` first (or `.send(None)`) to advance to the first `yield`.

### `.throw(exception)` — Inject an exception

```python
def careful_gen():
    try:
        yield 1
        yield 2
    except ValueError:
        yield "caught!"

>>> g = careful_gen()
>>> next(g)              → 1
>>> g.throw(ValueError)  → 'caught!'
```

### `.close()` — Graceful shutdown

```python
def gen():
    try:
        while True:
            yield "running"
    finally:
        print("Cleanup!")

>>> g = gen()
>>> next(g)    → 'running'
>>> g.close()  → prints "Cleanup!"
```

Throws `GeneratorExit` at the yield point. Generator can clean up in `finally`.

---

## Common Patterns

### 1. Large File Processing

```python
def read_in_chunks(path, chunk_size=8192):
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk
```

### 2. Pipeline Pattern (Unix-pipe style)

```python
def read_lines(path):
    with open(path) as f:
        yield from f

def strip_lines(lines):
    for line in lines:
        yield line.strip()

def filter_errors(lines):
    for line in lines:
        if "ERROR" in line:
            yield line

# Fully streaming — no intermediate lists
pipeline = filter_errors(strip_lines(read_lines("app.log")))
```

### 3. Infinite Sequences

```python
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

from itertools import islice
list(islice(fibonacci(), 10))
# [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

---

## When to Use Which

| Use a Generator | Use a Custom Iterator Class |
|---|---|
| Simple iteration logic | Complex state management |
| One-shot or streaming data | Need to serialize/pickle |
| 95% of the time | Need multiple public methods beyond iteration |

---

## 📌 Interview Cheat Sheet

| Concept | Key Point |
|---|---|
| **Iterable** | Has `__iter__()`, returns an iterator. Can be iterated multiple times. |
| **Iterator** | Has `__iter__()` (returns self) + `__next__()`. Single-use, one direction. |
| **`for` loop** | `iter()` → repeated `next()` → catches `StopIteration` |
| **Generator function** | Contains `yield`. Calling it returns a generator object (not executed immediately). |
| **`yield`** | Suspends function, saves all local state. `next()` resumes. |
| **Exhausted generator** | Raises `StopIteration` forever. Cannot restart. Must create new object. |
| **Generator expression** | `(x for x in ...)` — lazy, O(1) memory. |
| **`yield from`** | Delegates to sub-iterable. Proxies `.send()`/`.throw()`/`.close()`. |
| **`.send()`** | Push values INTO a generator. Must prime with `next()` first. |
| **Memory** | Generators = O(1). List comprehensions = O(n). |
| **`next(gen, default)`** | Returns default instead of raising `StopIteration`. |

### 🎯 What SDE2 Interviewers Look For:

1. You can explain **iterable vs iterator** precisely
2. You know what `for` translates to under the hood
3. You understand `yield` **suspends and resumes** — not restarts
4. You know when to use **generator expression vs list comprehension**
5. You can use `yield from` and explain what it does beyond simple delegation
6. You can write practical generators (file processing, pipelines, infinite sequences)
7. You understand generators are **single-use** and what happens when exhausted (`StopIteration` — not silence)
