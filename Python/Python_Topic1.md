# 🐍 Topic 1: Python Data Model — Dunder Methods

## What IS the Python Data Model?

The Python Data Model is the **framework that defines how objects behave** in Python. It's the API that lets your custom objects play nicely with Python's built-in syntax and operations — things like `len()`, `print()`, `==`, `in`, `for` loops, etc.

When you write `len(my_obj)`, Python actually calls `my_obj.__len__()`.  
When you write `a == b`, Python calls `a.__eq__(b)`.

> **Key Insight:** The data model is what makes Python feel consistent. A `list`, a `dict`, a `str`, and YOUR custom class can all respond to `len()` — because they all implement `__len__`. This is Python's version of **operator overloading** and **protocol-based polymorphism** (duck typing).

### WHY Dunder Methods?

Python follows: **"special syntax should map to special methods."**

Instead of requiring inheritance from a specific interface (like Java's `Comparable`), Python uses **duck typing + protocols**:

> *"If it has `__len__`, you can call `len()` on it."*

- More flexible than inheritance-based dispatch
- Faster — CPython can shortcut via C-level slots for built-in types

---

## 1. `__repr__` vs `__str__`

| Aspect | `__repr__` | `__str__` |
|---|---|---|
| **Purpose** | Developer / debugging | End user / display |
| **Goal** | Unambiguous, ideally `eval()`-able | Pretty, readable |
| **Fallback** | Is the fallback for `__str__` | Does NOT fall back to anything |

```python
class Money:
    def __init__(self, amount: float, currency: str = "USD"):
        self.amount = amount
        self.currency = currency

    def __repr__(self) -> str:
        return f"Money({self.amount!r}, {self.currency!r})"

    def __str__(self) -> str:
        return f"${self.amount:.2f} {self.currency}"
```

```python
>>> m = Money(42.5, "USD")
>>> repr(m)        # "Money(42.5, 'USD')"
>>> str(m)         # "$42.50 USD"
>>> print(m)       # "$42.50 USD"       — calls __str__
>>> f"{m}"         # "$42.50 USD"       — calls __str__
>>> f"{m!r}"       # "Money(42.5, 'USD')" — !r forces __repr__
```

### When is each called?

| Context | Calls |
|---|---|
| `repr(obj)`, typing `obj` in REPL | `__repr__` |
| `str(obj)`, `print(obj)`, `f"{obj}"` | `__str__` → falls back to `__repr__` |
| Inside a container: `print([m])` | `__repr__` on each element ⚠️ |
| Logging, debugging | `__repr__` |

> ⚠️ **Gotcha:** `print([m])` prints `[Money(42.5, 'USD')]` — it calls `__repr__` on elements inside containers, NOT `__str__`.

### The Rule

> **Always implement `__repr__`.** It's your universal fallback. Only add `__str__` if you need a different user-facing representation.

---

## 2. `__eq__` — Equality

**By default, `==` checks identity (same as `is`).** That's almost never what you want for value objects.

```python
class Point:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return NotImplemented  # ← NOT False!
        return self.x == other.x and self.y == other.y
```

### Why `NotImplemented` instead of `False`?

`NotImplemented` is a **signal to Python's runtime**:

> *"I don't know how to compare myself with this type. Try asking the other object."*

Python will then try `other.__eq__(self)` (the **reflected operation**).

If you return `False`, you're saying "we are definitely not equal" — which might be wrong if the other type has its own comparison logic.

### Reflection Mechanism

When Python evaluates `a == b`:

1. Call `a.__eq__(b)`
2. If result is `NotImplemented` → call `b.__eq__(a)`
3. If still `NotImplemented` → fall back to identity check (`is`)

**Special case:** If `type(b)` is a **subclass** of `type(a)`, Python tries `b.__eq__(a)` **first** (to give the more specific type priority).

---

## 3. `__hash__` — The `__eq__` / `__hash__` Contract

### ⚡ THE CONTRACT (memorize this):

> **If `a == b` is `True`, then `hash(a) == hash(b)` MUST be `True`.**  
> (The reverse is NOT required — hash collisions are fine.)

### What Python does automatically:

| You define | Python does |
|---|---|
| Nothing | `__eq__` uses `is`, `__hash__` uses `id()` |
| `__eq__` only | **Sets `__hash__ = None`** → object becomes **unhashable** ⚠️ |
| `__eq__` + `__hash__` | Uses your implementations |

### WHY does Python nullify `__hash__` when you define `__eq__`?

Because if you define custom equality but keep the default identity-based hash, you **break the contract**:

```python
a = Point(1, 2)
b = Point(1, 2)
# a == b is True (custom __eq__), but hash(a) != hash(b) (different id()s)
# This CORRUPTS any dict or set containing these objects
```

### Correct implementation:

```python
def __hash__(self) -> int:
    return hash((self.x, self.y))  # Tuple hashing — clean and correct
```

### Rules for `__hash__`:

1. Hash must be based on the **same fields** used in `__eq__`
2. Those fields must be **immutable** — or you'll corrupt sets/dicts if you mutate after insertion
3. Use `hash(tuple_of_fields)` as the go-to pattern

---

## 4. Mutable Fields + Hash = Silent Corruption

```python
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.email == other.email

    def __hash__(self):
        return hash(self.email)

users = {User("Alice", "alice@x.com"), User("Bob", "bob@x.com")}
alice = User("Alice", "alice@x.com")
alice.email = "new@x.com"  # ← MUTATION
```

**After mutation:**

- `alice in users` → `False` (hash points to wrong bucket)
- `len(users)` → `2` (she's still physically there)
- `users.discard(alice)` → does nothing (can't find her)
- She's a **ghost entry** — unreachable, undeletable, consuming memory

> 💀 **No exception, no warning — silent data corruption.**

**Fix:** Make hashed fields immutable via `frozen=True` dataclass, private attributes, or `__slots__` + properties.

---

## 5. `__len__` and `__bool__` — Truthiness

```python
class Playlist:
    def __init__(self, songs: list[str]):
        self.songs = songs

    def __len__(self) -> int:
        return len(self.songs)
```

### Truthiness Fallback Chain:

```
if obj:  →  __bool__()
                ↓ (not defined)
         →  __len__()  →  truthy if != 0
                ↓ (not defined)
         →  always truthy
```

```python
>>> bool(Playlist([]))         # False — __len__ returns 0
>>> bool(Playlist(["Song A"])) # True  — __len__ returns 1
```

You can override with `__bool__` to decouple truthiness from length:

```python
def __bool__(self) -> bool:
    return True  # Playlist is always "valid" even if empty
```

---

## 6. Inheritance Trap: `__eq__` / `__hash__` Across Hierarchies

```python
class Animal:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, Animal):
            return NotImplemented
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name)
        self.breed = breed

    def __eq__(self, other):
        if not isinstance(other, Dog):
            return NotImplemented
        return self.name == other.name and self.breed == other.breed

    def __hash__(self):
        return hash((self.name, self.breed))
```

```python
>>> a = Animal("Rex")
>>> d = Dog("Rex", "Labrador")
>>> a == d   # True — Animal.__eq__ sees Dog as isinstance(Animal) ✅
>>> d == a   # True — Dog.__eq__ returns NotImplemented, reflects to Animal.__eq__
```

### 💀 The Hidden Bug:

```python
>>> hash(a) == hash(d)
False  # hash("Rex") != hash(("Rex", "Labrador"))
```

**Equal objects, different hashes — contract violated!**

### Fixes:

- Use `type(other) is Animal` instead of `isinstance` (strict type check)
- Or ensure both hash on the same common fields
- Or don't define separate `__eq__` in the subclass

---

## 7. Complete Example — Value Object Done Right

```python
class Card:
    SUITS = "♠ ♥ ♦ ♣".split()
    RANKS = "2 3 4 5 6 7 8 9 10 J Q K A".split()

    def __init__(self, rank: str, suit: str):
        if rank not in self.RANKS:
            raise ValueError(f"Invalid rank: {rank}")
        if suit not in self.SUITS:
            raise ValueError(f"Invalid suit: {suit}")
        self._rank = rank  # "private" — discourage mutation
        self._suit = suit

    @property
    def rank(self) -> str:
        return self._rank

    @property
    def suit(self) -> str:
        return self._suit

    def __repr__(self) -> str:
        return f"Card({self.rank!r}, {self.suit!r})"

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self) -> int:
        return hash((self.rank, self.suit))

    def __lt__(self, other: "Card") -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return (self.RANKS.index(self.rank), self.SUITS.index(self.suit)) < \
               (self.RANKS.index(other.rank), self.SUITS.index(other.suit))
```

```python
>>> hand = {Card("A", "♠"), Card("K", "♥"), Card("A", "♠")}
>>> len(hand)
2  # Deduplication works — __eq__ + __hash__ are consistent

>>> sorted([Card("K", "♥"), Card("A", "♠"), Card("2", "♦")])
[Card('2', '♦'), Card('K', '♥'), Card('A', '♠')]  # __lt__ enables sorting
```

---

## 8. `dataclasses` — Auto-Generated Dunders

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int
    # Auto-generates: __init__, __repr__, __eq__
    # Does NOT auto-generate __hash__ (because __eq__ is defined)

@dataclass(frozen=True)
class FrozenPoint:
    x: int
    y: int
    # Auto-generates: __init__, __repr__, __eq__, __hash__
    # Also makes instances immutable (AttributeError on assignment)
```

| `@dataclass` option | `__eq__` | `__hash__` | Mutable? |
|---|---|---|---|
| Default | ✅ | ❌ (set to `None`) | ✅ |
| `frozen=True` | ✅ | ✅ | ❌ |
| `unsafe_hash=True` | ✅ | ✅ | ✅ ⚠️ (your risk) |

---

## 📌 Interview Cheat Sheet

| Point | Details |
|---|---|
| **`__repr__` vs `__str__`** | `repr` = developer/debug, `str` = user-facing. Always implement `repr`. Containers use `repr` on elements. |
| **`__eq__` return** | Return `NotImplemented`, never `False`, for unknown types |
| **`__eq__` kills `__hash__`** | Defining `__eq__` auto-sets `__hash__ = None`. Must explicitly define `__hash__`. |
| **Hash contract** | `a == b` → `hash(a) == hash(b)`. Violation corrupts dicts/sets **silently**. |
| **Hash from mutable fields** | Never do it. Mutating after insertion = ghost entries, silent corruption. |
| **Truthiness chain** | `__bool__` → `__len__` → `True` |
| **`dataclasses`** | Auto-generates `__repr__`, `__eq__`. Generates `__hash__` only if `frozen=True` or `unsafe_hash=True`. |
| **`!r` in f-strings** | Forces `__repr__` — useful for debugging inside format strings |
| **Inheritance trap** | Subclass with different `__eq__`/`__hash__` can break the hash contract with parent. Use strict `type()` checks if needed. |
| **Reflection** | If `a.__eq__(b)` → `NotImplemented`, Python tries `b.__eq__(a)`. Subclass gets priority. |

### 🎯 What SDE2 Interviewers Look For:

1. You know the `__eq__`/`__hash__` contract **cold**
2. You return `NotImplemented`, not `False`
3. You understand **why** Python nullifies `__hash__` when you define `__eq__`
4. You can design a proper **value object** (immutable + correct eq/hash)
5. You understand the **truthiness fallback chain**
6. You know the **inheritance pitfall** with eq/hash across hierarchies
7. You can explain when to use `dataclass(frozen=True)` vs manual dunders
