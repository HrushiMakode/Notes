# 🐍 Topic 2: Mutability & References

## Variables Are Name Tags, NOT Boxes

In Python, variables are **labels (references)** that point to objects — not containers that hold values.

```python
a = [1, 2, 3]
b = a         # b is another label on the SAME object
b.append(4)
# a is [1, 2, 3, 4] — same object, both names see it
```

```
  a ──┐
      ├──→ [1, 2, 3]   (one object, two names)
  b ──┘
```

**WHY?** Performance. Assignment is always O(1) — just copies a pointer, never the data.

---

## Mutable vs Immutable

| Mutable (change in-place) | Immutable (cannot change) |
|---|---|
| `list`, `dict`, `set`, `bytearray` | `tuple`, `frozenset`, `str`, `bytes` |
| Custom objects (by default) | `int`, `float`, `bool`, `None` |
|  | `namedtuple`, `frozen dataclass` |

### "Changing" an immutable creates a NEW object:

```python
>>> s = "hello"
>>> id(s)
140234866534384
>>> s = s + " world"
>>> id(s)
140234866534192  # ← DIFFERENT object
```

### ⚠️ Immutable containers can hold mutable objects:

```python
>>> t = ([1, 2], [3, 4])
>>> t[0].append(99)      # Works! List inside is mutable.
>>> t
([1, 2, 99], [3, 4])
```

The tuple stores **references** — those references are frozen, but the objects they point to can still mutate.

> This is why `([1,2], [3,4])` is **unhashable** — mutable contents could change the hash.

---

## `is` vs `==`

| Operator | Checks | Under the hood |
|---|---|---|
| `==` | **Value equality** (same content?) | Calls `__eq__()` |
| `is` | **Identity** (same object in memory?) | Compares `id()` |

```python
>>> a = [1, 2, 3]
>>> b = [1, 2, 3]
>>> a == b    # True  — same content
>>> a is b    # False — different objects
```

### When to use `is`: **Only for singletons**

```python
# ✅ Correct
if x is None:

# ❌ Wrong
if x == None:   # __eq__ could be overridden
```

### ⚠️ Small Integer Cache (CPython):

CPython caches integers **-5 to 256**:

```python
>>> a = 256; b = 256; a is b  → True   # cached
>>> a = 257; b = 257; a is b  → False  # outside cache
```

**Never rely on `is` for ints or strings** — this is a CPython implementation detail.

### String Interning:

CPython interns some strings (identifiers, short strings without spaces):

```python
>>> "hello" is "hello"          → True   # interned
>>> "hello world!" is "hello world!"  → False  # not interned
```

Force with `sys.intern()`, but never write code that depends on it.

---

## Shallow Copy vs Deep Copy

### No Copy (aliasing):

```python
b = a  # b IS a — same object
```

### Shallow Copy — new container, shared elements:

```python
import copy

a = [1, [2, 3], 4]

b = a.copy()        # Method 1
b = list(a)          # Method 2
b = a[:]             # Method 3
b = copy.copy(a)     # Method 4
```

```
a ──→ [ ref_0,  ref_1,  ref_2 ]
         │        │        │
         ▼        ▼        ▼
         1    [2, 3]       4

b ──→ [ ref_0,  ref_1,  ref_2 ]   ← NEW outer list
         │        │        │
         ▼        ▼        ▼
         1    [2, 3]       4       ← SHARED inner list!
```

```python
>>> b[1].append(99)
>>> a
[1, [2, 3, 99], 4]   # Inner list is shared — a sees mutation!

>>> b.append(5)
>>> a
[1, [2, 3, 99], 4]   # Outer list is independent
```

### For dicts:

```python
original = {"key": [1, 2, 3]}
shallow = original.copy()
shallow["key"].append(4)       # original["key"] → [1, 2, 3, 4] — shared!
shallow["new_key"] = "hello"   # original has no "new_key" — independent
```

### Deep Copy — new everything, recursively:

```python
import copy

a = [1, [2, 3], 4]
b = copy.deepcopy(a)
b[1].append(99)
# a is [1, [2, 3], 4] — completely independent
```

- Handles **circular references** (tracks already-copied objects)
- Customize via `__copy__()` and `__deepcopy__(memo)` on custom classes

---

## Default Mutable Arguments — The Classic Trap

```python
def add_item(item, items=[]):   # ← LIST CREATED ONCE at definition
    items.append(item)
    return items

>>> add_item("a")  → ['a']
>>> add_item("b")  → ['a', 'b']   # Accumulates!
>>> add_item("c")  → ['a', 'b', 'c']
```

### WHY?

Default values are evaluated **once at function definition time**, not at each call. The list is stored on `add_item.__defaults__` and shared across calls.

### The Fix (memorize this pattern):

```python
def add_item(item, items=None):
    if items is None:
        items = []        # Fresh list per call
    items.append(item)
    return items
```

---

## Pass by Object Reference

Python is neither "pass by value" nor "pass by reference" — it's **pass by object reference**:

> The function receives a reference to the **same object**. Not a copy, not a reference to the variable.

### Mutation vs Rebinding:

```python
def modify(lst):
    lst.append(4)        # MUTATION — modifies original, caller sees it

def rebind(lst):
    lst = [10, 20, 30]   # REBINDING — new local name, caller doesn't see it

x = [1, 2, 3]
modify(x)   # x → [1, 2, 3, 4]
rebind(x)   # x → [1, 2, 3, 4] — unchanged!
```

### With immutables:

```python
def try_modify(n):
    n = n + 1   # Creates NEW int, rebinds local name
    return n

x = 10
try_modify(x)
# x is still 10
```

**Rule:**
- **Mutating** (`.append()`, `[0]=...`, `.update()`) → caller sees it
- **Rebinding** (`=`) → caller doesn't see it

---

## `+=` Behaves Differently on Mutables vs Immutables

### Mutable (`list`) — mutates in place via `__iadd__`:

```python
a = [1, 2]
b = a
a += [3]       # a.__iadd__([3]) → mutates in place
>>> b → [1, 2, 3]   # Same object — b sees it
```

### Immutable (`tuple`) — creates new object:

```python
a = (1, 2)
b = a
a += (3,)      # No __iadd__ → creates NEW tuple
>>> b → (1, 2)      # b still points to old tuple
>>> a is b → False
```

### ⚠️ The Tuple-in-Tuple `+=` Puzzle (Famous Interview Question!):

```python
>>> t = ([1, 2],)
>>> t[0] += [3, 4]
```

**Result:** `TypeError: 'tuple' object does not support item assignment`
**BUT:** `t` is now `([1, 2, 3, 4],)` — the list WAS modified!

**Why?** `t[0] += [3, 4]` expands to:

```python
temp = t[0].__iadd__([3, 4])   # Step 1: mutates list ✅
t[0] = temp                     # Step 2: assigns back to tuple ❌ TypeError
```

Step 1 succeeds, Step 2 raises. You get **both a side effect AND an exception**.

---

## 📌 Interview Cheat Sheet

| Concept | Key Point |
|---|---|
| **Variables** | Name tags pointing to objects, NOT boxes |
| **`is` vs `==`** | `is` = identity (`id`), `==` = value equality. Use `is` only for `None`/`True`/`False` |
| **Small int cache** | `-5` to `256` cached in CPython. Never rely on `is` for ints/strings |
| **Mutable defaults** | Evaluated ONCE at definition. Fix: `None` sentinel + create inside function |
| **Shallow copy** | New container, shared inner references |
| **Deep copy** | New everything, recursively. Handles circular refs |
| **Immutable ≠ deeply immutable** | Tuple of lists — tuple is immutable, lists inside are not |
| **Pass by object reference** | Mutation → caller sees. Rebinding → caller doesn't |
| **`+=`** | Mutates in place for mutables (`__iadd__`), creates new for immutables |
| **Tuple `+=` trap** | List IS mutated, then assignment to tuple raises TypeError. Both happen. |

### 🎯 What SDE2 Interviewers Look For:

1. You explain the **name tag / reference model** clearly
2. You know the **mutable default argument trap** cold and can fix it
3. You can trace through **shallow vs deep copy** on nested structures
4. You understand **pass by object reference** — mutation vs rebinding
5. You know when `is` is appropriate vs `==`
6. You can explain the `+=` tuple trap (shows deep understanding)
7. You know **immutable ≠ deeply immutable** (tuple of lists)
