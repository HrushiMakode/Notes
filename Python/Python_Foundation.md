# Python — Phase 1: The Foundation

> **Modules 1–5** | Object Model → Variables & Memory → Data Structures → Strings & Unicode → Functions & Scoping
> **Goal:** Build an unshakable mental model of how Python actually works under the hood.

```mermaid
flowchart LR
    M1["M1: Object Model"] --> M2["M2: Variables & Memory"]
    M2 --> M3["M3: Data Structures"]
    M3 --> M4["M4: Strings & Unicode"]
    M4 --> M5["M5: Functions & Scoping"]

    style M1 fill:#d00000,color:#fff
    style M2 fill:#c9190b,color:#fff
    style M3 fill:#a4161a,color:#fff
    style M4 fill:#800f19,color:#fff
    style M5 fill:#660a13,color:#fff
```

---

## Module 1: Python Object Model

> `[ ]` — Notes will be filled in as we cover this

### 🔑 Core Idea

*(pending — everything is an object, `id()`, `type()`, `is` vs `==`, mutability)*

### 💡 Key Concepts

*(pending)*

### 🧠 Mental Model

*(pending — diagram showing objects on the heap, names as labels)*

### ⚠️ Don't Forget

*(pending — gotchas, traps)*

### 🎯 Must-Know for Interview

*(pending — what an SDE2 interviewer expects)*

### 📎 Quick Code Snippet

*(pending)*

---

## Module 2: Variables & Memory

> `[ ]` — Notes will be filled in as we cover this

### 🔑 Core Idea

*(pending — names vs objects, reference semantics, `sys.getrefcount()`, interning & caching)*

### 💡 Key Concepts

*(pending)*

### 🧠 Mental Model

*(pending — reference diagram, interning pool)*

### ⚠️ Don't Forget

*(pending)*

### 🎯 Must-Know for Interview

*(pending)*

### 📎 Quick Code Snippet

*(pending)*

---

## Module 3: Data Structures Deep Dive

> `[ ]` — Notes will be filled in as we cover this

### 🔑 Core Idea

*(pending — `list`, `tuple`, `dict`, `set` — internals, time complexities, when to use what)*

### 💡 Key Concepts

*(pending — hash tables, dynamic arrays, open addressing)*

### 🧠 Mental Model

*(pending — internal layout diagrams for dict, list resizing)*

### ⚠️ Don't Forget

*(pending — dict ordering guarantee, mutable default args, unhashable keys)*

### 🎯 Must-Know for Interview

*(pending — time complexity table, dict vs OrderedDict)*

### 📎 Quick Code Snippet

*(pending)*

---

## Module 4: Strings & Unicode

> `[ ]` — Notes will be filled in as we cover this

### 🔑 Core Idea

*(pending — encoding, `str` vs `bytes`, `encode()`/`decode()`, f-strings internals)*

### 💡 Key Concepts

*(pending — UTF-8 vs UTF-16, PEP 393 compact strings, string interning)*

### 🧠 Mental Model

*(pending — encoding/decoding pipeline diagram)*

### ⚠️ Don't Forget

*(pending — UnicodeDecodeError, mojibake, `b''` vs `''`)*

### 🎯 Must-Know for Interview

*(pending)*

### 📎 Quick Code Snippet

*(pending)*

---

## Module 5: Functions & Scoping

> `[ ]` — Notes will be filled in as we cover this

### 🔑 Core Idea

*(pending — first-class functions, closures, LEGB rule, `*args`/`**kwargs`, early vs late binding)*

### 💡 Key Concepts

*(pending — function objects, `__code__`, `__closure__`, default argument evaluation)*

### 🧠 Mental Model

*(pending — LEGB scope chain diagram)*

### ⚠️ Don't Forget

*(pending — mutable default argument trap, late binding closures in loops)*

### 🎯 Must-Know for Interview

*(pending)*

### 📎 Quick Code Snippet

*(pending)*

---

## Phase 1 — Interview Quick-Fire

*(Will be compiled after all 5 modules are covered)*

---

## Phase 1 — Key Gotchas Rapid Fire

*(Will be compiled after all 5 modules are covered)*
