# Python — Phase 2: The Mechanics

> **Modules 6–10** | Iterators & Generators → Decorators → OOP → Error Handling → Comprehensions
> **Goal:** Master the core language features that separate juniors from seniors.

```mermaid
flowchart LR
    M6["M6: Iterators & Generators"] --> M7["M7: Decorators"]
    M7 --> M8["M8: OOP"]
    M8 --> M9["M9: Error Handling & Context Managers"]
    M9 --> M10["M10: Comprehensions & Functional Tools"]

    style M6 fill:#e76f51,color:#fff
    style M7 fill:#d65d3e,color:#fff
    style M8 fill:#c44b2c,color:#fff
    style M9 fill:#b3391a,color:#fff
    style M10 fill:#a12708,color:#fff
```

---

## Module 6: Iterators & Generators

> `[ ]` — Notes will be filled in as we cover this

### 🔑 Core Idea

*(pending — `__iter__`/`__next__`, generator functions, `yield`, `yield from`, lazy evaluation)*

### 💡 Key Concepts

*(pending — iterator protocol, generator state machine, `StopIteration`)*

### 🧠 Mental Model

*(pending — generator lifecycle diagram: CREATED → RUNNING → SUSPENDED → CLOSED)*

### ⚠️ Don't Forget

*(pending — generator exhaustion, `send()`, generator-based coroutines vs async)*

### 🎯 Must-Know for Interview

*(pending)*

### 📎 Quick Code Snippet

*(pending)*

---

## Module 7: Decorators

> `[ ]` — Notes will be filled in as we cover this

### 🔑 Core Idea

*(pending — function decorators, class decorators, `@wraps`, decorator factories, stacking order)*

### 💡 Key Concepts

*(pending — closures as decorators, `functools.wraps`, parametrized decorators)*

### 🧠 Mental Model

*(pending — decorator unwrapping/stacking order diagram)*

### ⚠️ Don't Forget

*(pending — losing `__name__`/`__doc__` without `@wraps`, decorator vs decorator factory)*

### 🎯 Must-Know for Interview

*(pending)*

### 📎 Quick Code Snippet

*(pending)*

---

## Module 8: OOP in Python

> `[ ]` — Notes will be filled in as we cover this

### 🔑 Core Idea

*(pending — classes, MRO (C3 linearization), `__init__` vs `__new__`, slots, descriptors, metaclasses)*

### 💡 Key Concepts

*(pending — attribute lookup chain, data descriptors vs non-data, `__mro__`, `type()` vs `isinstance()`)*

### 🧠 Mental Model

*(pending — MRO resolution diagram, attribute lookup flowchart)*

### ⚠️ Don't Forget

*(pending — diamond problem, `super()` with MRO, `__slots__` saves memory but breaks `__dict__`)*

### 🎯 Must-Know for Interview

*(pending)*

### 📎 Quick Code Snippet

*(pending)*

---

## Module 9: Error Handling & Context Managers

> `[ ]` — Notes will be filled in as we cover this

### 🔑 Core Idea

*(pending — exception hierarchy, custom exceptions, `with` protocol, `__enter__`/`__exit__`)*

### 💡 Key Concepts

*(pending — `contextlib.contextmanager`, exception chaining, bare `except` dangers)*

### 🧠 Mental Model

*(pending — exception hierarchy tree, context manager lifecycle diagram)*

### ⚠️ Don't Forget

*(pending — `except Exception` vs `except BaseException`, `__exit__` return True suppresses)*

### 🎯 Must-Know for Interview

*(pending)*

### 📎 Quick Code Snippet

*(pending)*

---

## Module 10: Comprehensions & Functional Tools

> `[ ]` — Notes will be filled in as we cover this

### 🔑 Core Idea

*(pending — list/dict/set/generator comprehensions, `map`, `filter`, `reduce`, `functools`)*

### 💡 Key Concepts

*(pending — comprehension scope rules, `functools.lru_cache`, `functools.partial`, `operator` module)*

### 🧠 Mental Model

*(pending — comprehension translation to loop equivalents)*

### ⚠️ Don't Forget

*(pending — nested comprehension readability, generator comprehension vs list, variable leak (Python 2 vs 3))*

### 🎯 Must-Know for Interview

*(pending)*

### 📎 Quick Code Snippet

*(pending)*

---

## Phase 2 — Interview Quick-Fire

*(Will be compiled after all 5 modules are covered)*

---

## Phase 2 — Key Gotchas Rapid Fire

*(Will be compiled after all 5 modules are covered)*
