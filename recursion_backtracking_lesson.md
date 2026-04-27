# 🧑‍🏫 Topic 10: Recursion & Backtracking Patterns in C++

---

## 1. Recursion in C++ — The Mechanics You Forgot

### 1.1 Basic Recursive Function

```cpp
// Every recursive function has:
// 1. Base case — when to STOP
// 2. Recursive case — break problem down + call yourself

int factorial(int n) {
    if (n <= 1) return 1;       // base case
    return n * factorial(n - 1); // recursive case
}
```

**JS equivalent you already know:**
```javascript
const factorial = (n) => n <= 1 ? 1 : n * factorial(n - 1);
```

Identical logic. The only difference: C++ needs the **return type** declared (`int`).

---

### 1.2 What Happens Under the Hood — The Call Stack

Every function call in C++ pushes a **stack frame** onto the call stack. Each frame contains:
- Local variables
- Function arguments (copies or references)
- Return address

```
factorial(4)
  → factorial(3)    // new stack frame pushed
    → factorial(2)  // another frame
      → factorial(1) // another frame — base case hit
      ← returns 1    // frame popped
    ← returns 2
  ← returns 6
← returns 24
```

> ⚠️ **Stack overflow risk**: Default stack size is ~1-8 MB. Deep recursion (e.g., `n = 100000`) will crash. This is true in all languages, but C++ gives you NO safety net — no tail-call optimization guaranteed.

---

### 1.3 Passing Arguments in Recursion — This is Where It Gets Real

This is **THE** thing that trips up people coming from JS/Python. In those languages, you never think about this. In C++, it's everything.

#### Pass by VALUE (copy)

```cpp
void helper(int x) {   // x is a COPY
    x = 99;            // modifies the copy, not the original
}

int main() {
    int a = 5;
    helper(a);
    // a is still 5 here!
}
```

**When to use**: When you want each recursive call to have its own independent copy. Common for simple counters, indices.

#### Pass by REFERENCE (`&`)

```cpp
void helper(int& x) {  // x IS the original variable (alias)
    x = 99;            // modifies the ORIGINAL
}

int main() {
    int a = 5;
    helper(a);
    // a is now 99!
}
```

**When to use**: When you want recursive calls to **share and modify** the same data. This is the backbone of backtracking.

#### Pass by POINTER (`*`)

```cpp
void helper(int* x) {  // x is a pointer — holds the ADDRESS of the original
    *x = 99;           // dereference (*x) to modify what it points to
}

int main() {
    int a = 5;
    helper(&a);         // &a = "address of a"
    // a is now 99!
}
```

**When to use**: Mostly for tree/linked-list nodes (`TreeNode*`). Rarely used for plain variables in DSA.

### 📊 Side-by-side: How the 3 approaches compare

```
┌──────────────────────────┬──────────────┬──────────────────┬──────────────────┐
│                          │ By Value     │ By Reference (&) │ By Pointer (*)   │
├──────────────────────────┼──────────────┼──────────────────┼──────────────────┤
│ Declaration              │ void f(int x)│ void f(int& x)   │ void f(int* x)   │
│ Calling                  │ f(a)         │ f(a)             │ f(&a)            │
│ Modifies original?       │ ❌ No        │ ✅ Yes           │ ✅ Yes           │
│ Can be null?             │ N/A          │ ❌ No            │ ✅ Yes (nullptr) │
│ Syntax to read value     │ x            │ x                │ *x               │
│ JS/Python equivalent     │ primitives   │ objects/arrays   │ (no equivalent)  │
└──────────────────────────┴──────────────┴──────────────────┴──────────────────┘
```

### 1.4 The Arrow Operator (`->`) Refresher

The arrow `->` is used to access members of a struct/class **through a pointer**.

```cpp
struct TreeNode {
    int val;
    TreeNode* left;   // pointer to another TreeNode
    TreeNode* right;  // pointer to another TreeNode

    // Constructor — lets you create nodes easily
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

void printNode(TreeNode* node) {
    if (node == nullptr) return;  // null check — ALWAYS do this first

    // node is a POINTER, so use -> to access members
    cout << node->val << endl;    // same as (*node).val

    // Recurse on children (which are also pointers)
    printNode(node->left);
    printNode(node->right);
}
```

**Mental model:**
- `node` = a pointer (holds a memory address)
- `*node` = the actual TreeNode struct at that address
- `node->val` = shorthand for `(*node).val` = "follow the pointer, then access .val"

**Python equivalent:**
```python
# In Python, everything is a reference. You just write:
print(node.val)
node.left  # no -> needed, Python handles it
```

---

## 2. Backtracking — The Master Template

Backtracking = **recursion + undo**. You explore a choice, recurse, then **undo the choice** to try another path.

### 2.1 The Universal Backtracking Template

```cpp
void backtrack(
    vector<vector<int>>& result,    // accumulates ALL valid solutions (by ref!)
    vector<int>& current,           // the current partial solution (by ref — shared!)
    /* other params: candidates, start index, target, etc. */
) {
    // 1. BASE CASE: Is current solution complete/valid?
    if (/* goal condition */) {
        result.push_back(current);  // save a COPY of current solution
        return;
    }

    // 2. EXPLORE: Try each possible next choice
    for (int i = start; i < candidates.size(); i++) {

        // 3. CHOOSE: Make a choice
        current.push_back(candidates[i]);

        // 4. RECURSE: Explore further with this choice
        backtrack(result, current, /* updated params */);

        // 5. UN-CHOOSE (BACKTRACK): Undo the choice
        current.pop_back();   // ← THIS is the backtracking step
    }
}
```

### Why pass `result` and `current` by reference (`&`)?

- **`result`** → by reference because we want ALL recursive calls to add to the **same** result vector. If by value, each call would have its own copy and results would be lost.
- **`current`** → by reference because we want to **modify it in-place** (push/pop). This avoids copying the entire vector at every recursive call → huge performance win.

> 🔑 **Critical gotcha**: When you do `result.push_back(current)`, it stores a **copy** of `current`. This is correct because `current` will keep changing as we backtrack. If you stored a reference, all entries in `result` would point to the same (final, empty) vector.

### Python comparison:

```python
def backtrack(result, current, ...):
    if goal_condition:
        result.append(current[:])  # current[:] = make a COPY (same idea!)
        return

    for choice in candidates:
        current.append(choice)       # choose
        backtrack(result, current, ...)
        current.pop()                # un-choose
```

The C++ and Python templates are **structurally identical**. The difference is that in C++, you must explicitly declare `&` for pass-by-reference.

---

## 3. Pattern 1: Subsets (Power Set)

**LeetCode 78 — Subsets**

Given `nums = [1, 2, 3]`, return all subsets: `[[], [1], [2], [3], [1,2], [1,3], [2,3], [1,2,3]]`

```cpp
class Solution {
public:
    vector<vector<int>> subsets(vector<int>& nums) {
        vector<vector<int>> result;  // stores all subsets
        vector<int> current;         // current subset being built

        backtrack(result, current, nums, 0);
        return result;
    }

private:
    void backtrack(
        vector<vector<int>>& result,  // & = same result across all calls
        vector<int>& current,         // & = modify in place, then undo
        vector<int>& nums,            // & = avoid copying the input (read-only)
        int start                     // by value — each call gets its own copy
    ) {
        // Every partial solution is a valid subset — add it
        result.push_back(current);  // pushes a COPY of current

        for (int i = start; i < nums.size(); i++) {
            current.push_back(nums[i]);             // CHOOSE
            backtrack(result, current, nums, i + 1); // EXPLORE (i+1, not i — no reuse)
            current.pop_back();                      // UN-CHOOSE
        }
    }
};
```

**Recursion tree for `[1,2,3]`:**
```
                      []
                /      |      \
             [1]      [2]     [3]
            /   \      |
         [1,2] [1,3] [2,3]
          |
       [1,2,3]
```

---

## 4. Pattern 2: Subsets with Duplicates

**LeetCode 90 — Subsets II**

Input may have duplicates: `[1, 2, 2]`. Skip duplicate branches.

```cpp
class Solution {
public:
    vector<vector<int>> subsetsWithDup(vector<int>& nums) {
        sort(nums.begin(), nums.end());  // MUST sort to group duplicates
        vector<vector<int>> result;
        vector<int> current;

        backtrack(result, current, nums, 0);
        return result;
    }

private:
    void backtrack(
        vector<vector<int>>& result,
        vector<int>& current,
        vector<int>& nums,
        int start
    ) {
        result.push_back(current);

        for (int i = start; i < nums.size(); i++) {
            // SKIP DUPLICATES: if this element == previous element
            // AND we're not at the start of this level
            if (i > start && nums[i] == nums[i - 1]) continue;

            current.push_back(nums[i]);
            backtrack(result, current, nums, i + 1);
            current.pop_back();
        }
    }
};
```

> 🔑 **The duplicate-skip pattern**: `if (i > start && nums[i] == nums[i-1]) continue;`
> This is the single most important line for handling duplicates in backtracking. Memorize it.

---

## 5. Pattern 3: Permutations

**LeetCode 46 — Permutations**

```cpp
class Solution {
public:
    vector<vector<int>> permute(vector<int>& nums) {
        vector<vector<int>> result;
        vector<int> current;
        vector<bool> used(nums.size(), false);  // track which elements are used

        backtrack(result, current, nums, used);
        return result;
    }

private:
    void backtrack(
        vector<vector<int>>& result,
        vector<int>& current,
        vector<int>& nums,
        vector<bool>& used   // & = shared "used" state across recursion
    ) {
        // Base case: permutation is complete when size matches
        if (current.size() == nums.size()) {
            result.push_back(current);
            return;
        }

        for (int i = 0; i < nums.size(); i++) {
            if (used[i]) continue;  // skip already-used elements

            used[i] = true;                          // CHOOSE
            current.push_back(nums[i]);
            backtrack(result, current, nums, used);   // EXPLORE
            current.pop_back();                       // UN-CHOOSE
            used[i] = false;                         // UN-CHOOSE (undo the used flag too!)
        }
    }
};
```

**Key difference from Subsets:**
- Subsets: use `start` index to avoid going backwards → combinations
- Permutations: always start from `i = 0`, use `used[]` array to skip used elements → orderings matter

---

## 6. Pattern 4: Combination Sum

**LeetCode 39 — Combination Sum** (elements can be reused)

```cpp
class Solution {
public:
    vector<vector<int>> combinationSum(vector<int>& candidates, int target) {
        vector<vector<int>> result;
        vector<int> current;

        backtrack(result, current, candidates, target, 0);
        return result;
    }

private:
    void backtrack(
        vector<vector<int>>& result,
        vector<int>& current,
        vector<int>& candidates,
        int remaining,    // by VALUE — each call tracks its own remaining
        int start
    ) {
        if (remaining < 0) return;         // pruning — overshot
        if (remaining == 0) {
            result.push_back(current);     // found valid combination
            return;
        }

        for (int i = start; i < candidates.size(); i++) {
            current.push_back(candidates[i]);
            // pass `i` (not i+1) — same element can be reused!
            backtrack(result, current, candidates, remaining - candidates[i], i);
            current.pop_back();
        }
    }
};
```

**Variation — LeetCode 40 (each element used once):** Change `i` → `i + 1`, sort input, add duplicate skip.

---

## 7. Pattern 5: N-Queens (Grid Backtracking)

**LeetCode 51 — N-Queens**

```cpp
class Solution {
public:
    vector<vector<string>> solveNQueens(int n) {
        vector<vector<string>> result;
        // Initialize empty board: n rows, each row is n dots
        vector<string> board(n, string(n, '.'));

        backtrack(result, board, 0, n);
        return result;
    }

private:
    void backtrack(
        vector<vector<string>>& result,
        vector<string>& board,  // & = modify board in-place, then undo
        int row,
        int n
    ) {
        if (row == n) {
            result.push_back(board);  // all queens placed — save board copy
            return;
        }

        for (int col = 0; col < n; col++) {
            if (!isValid(board, row, col, n)) continue;

            board[row][col] = 'Q';              // CHOOSE: place queen
            backtrack(result, board, row + 1, n); // EXPLORE: next row
            board[row][col] = '.';              // UN-CHOOSE: remove queen
        }
    }

    bool isValid(vector<string>& board, int row, int col, int n) {
        // Check column above
        for (int i = 0; i < row; i++) {
            if (board[i][col] == 'Q') return false;
        }
        // Check upper-left diagonal
        for (int i = row - 1, j = col - 1; i >= 0 && j >= 0; i--, j--) {
            if (board[i][j] == 'Q') return false;
        }
        // Check upper-right diagonal
        for (int i = row - 1, j = col + 1; i >= 0 && j < n; i--, j++) {
            if (board[i][j] == 'Q') return false;
        }
        return true;
    }
};
```

**Note on `string(n, '.')`:** Creates a string of `n` dots. This is a C++ string constructor — `string(count, char)`.

---

## 8. Pattern 6: Word Search (2D Grid DFS + Backtracking)

**LeetCode 79 — Word Search**

```cpp
class Solution {
public:
    bool exist(vector<vector<char>>& board, string word) {
        int rows = board.size();
        int cols = board[0].size();

        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (dfs(board, word, r, c, 0)) return true;
            }
        }
        return false;
    }

private:
    bool dfs(
        vector<vector<char>>& board,  // & = modify in-place for visited marking
        const string& word,           // const& = don't copy, don't modify
        int r, int c,                 // by value — each call has its own position
        int idx                       // by value — index into word
    ) {
        // Base case: matched all characters
        if (idx == word.size()) return true;

        // Bounds check + character match
        if (r < 0 || r >= board.size() ||
            c < 0 || c >= board[0].size() ||
            board[r][c] != word[idx]) {
            return false;
        }

        char temp = board[r][c];   // save original character
        board[r][c] = '#';         // CHOOSE: mark as visited

        // EXPLORE: try all 4 directions
        bool found = dfs(board, word, r + 1, c, idx + 1) ||
                     dfs(board, word, r - 1, c, idx + 1) ||
                     dfs(board, word, r, c + 1, idx + 1) ||
                     dfs(board, word, r, c - 1, idx + 1);

        board[r][c] = temp;        // UN-CHOOSE: restore original (backtrack!)

        return found;
    }
};
```

**Key patterns here:**
- `const string& word` — pass by const reference: no copy, no modification. Use this for read-only data.
- Marking visited by modifying the grid in-place (`'#'`), then restoring — classic backtracking on grids.

---

## 9. Pattern 7: Palindrome Partitioning

**LeetCode 131 — Palindrome Partitioning**

```cpp
class Solution {
public:
    vector<vector<string>> partition(string s) {
        vector<vector<string>> result;
        vector<string> current;

        backtrack(result, current, s, 0);
        return result;
    }

private:
    void backtrack(
        vector<vector<string>>& result,
        vector<string>& current,
        const string& s,    // const& — read-only, no copy
        int start
    ) {
        if (start == s.size()) {
            result.push_back(current);
            return;
        }

        for (int end = start; end < s.size(); end++) {
            if (!isPalindrome(s, start, end)) continue; // pruning

            // s.substr(start, length) — extract substring
            current.push_back(s.substr(start, end - start + 1));  // CHOOSE
            backtrack(result, current, s, end + 1);                // EXPLORE
            current.pop_back();                                    // UN-CHOOSE
        }
    }

    bool isPalindrome(const string& s, int left, int right) {
        while (left < right) {
            if (s[left] != s[right]) return false;
            left++;
            right--;
        }
        return true;
    }
};
```

**`s.substr(pos, len)`** — returns a new string starting at `pos` with length `len`. Python equivalent: `s[start:end+1]`.

---

## 10. Recursion with Trees — Pointer Heavy

This is where `*` and `->` dominate.

### Tree DFS Template

```cpp
struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

// Example: find all root-to-leaf paths
class Solution {
public:
    vector<vector<int>> allPaths(TreeNode* root) {
        vector<vector<int>> result;
        vector<int> path;
        dfs(root, path, result);
        return result;
    }

private:
    void dfs(
        TreeNode* node,              // pointer to current node (can be null!)
        vector<int>& path,           // & = modify in-place
        vector<vector<int>>& result  // & = accumulate results
    ) {
        if (node == nullptr) return;  // ALWAYS check for null first

        path.push_back(node->val);    // CHOOSE: add node value to path

        if (node->left == nullptr && node->right == nullptr) {
            // Leaf node — save this path
            result.push_back(path);   // saves a copy
        } else {
            dfs(node->left, path, result);   // EXPLORE left
            dfs(node->right, path, result);  // EXPLORE right
        }

        path.pop_back();  // UN-CHOOSE: backtrack
    }
};
```

**Why `TreeNode*` (pointer) and not `TreeNode&` (reference)?**
- A pointer can be `nullptr`. A reference cannot.
- Tree children can be null (leaf nodes), so they must be pointers.
- This is a universal C++ convention for trees and linked lists.

---

## 11. 🚨 Common Gotchas & Pitfalls

### Gotcha 1: Forgetting to pass by reference

```cpp
// ❌ BUG: result is passed by VALUE — modifications lost!
void backtrack(vector<vector<int>> result, vector<int>& current, ...) {
    result.push_back(current);  // this adds to a LOCAL copy only
}

// ✅ CORRECT: pass by reference
void backtrack(vector<vector<int>>& result, vector<int>& current, ...) {
    result.push_back(current);  // adds to the ACTUAL result
}
```

### Gotcha 2: Storing reference instead of copy in result

```cpp
// ❌ BUG in Python-thinking:
// result.push_back(current) already stores a COPY in C++, so this is actually fine.
// But in Python, you must do result.append(current[:])
// In C++, push_back automatically copies. So this is correct.

// ⚠️ BUT if you tried to store a reference/pointer for "optimization":
// result.push_back(&current) — DO NOT do this. current will change/be destroyed.
```

### Gotcha 3: `size()` returns `size_t` (unsigned)

```cpp
// ❌ Potential bug with unsigned arithmetic:
for (int i = 0; i < nums.size() - 1; i++) {
    // If nums is EMPTY, nums.size() is 0 (unsigned).
    // 0 - 1 wraps around to 18446744073709551615 (huge number!)
    // Loop runs forever or accesses garbage memory.
}

// ✅ Fix: cast to int, or handle empty case
for (int i = 0; i + 1 < (int)nums.size(); i++) { ... }
```

### Gotcha 4: Stack overflow on deep recursion

```cpp
// C++ default stack size: ~1MB (MSVC) to ~8MB (Linux)
// Recursion depth > ~10,000 may crash
// For very deep recursion, consider iterative approach with explicit stack
```

### Gotcha 5: Modifying a collection while iterating

```cpp
// ❌ Dangerous: don't push_back to the vector you're iterating
for (int i = 0; i < vec.size(); i++) {
    vec.push_back(something);  // can invalidate iterators, cause UB
}
```

---

## 12. `const` Reference — When and Why

```cpp
// Use const& for parameters you READ but don't MODIFY
// Avoids copying + prevents accidental modification

bool isPalindrome(const string& s, int left, int right);
//                ^^^^^^^^^^^^^^
//                "I promise not to modify s"
//                + no copy of the string is made

void backtrack(..., const vector<int>& nums, ...);
//                  ^^^^^^^^^^^^^^^^^^^^^^^
//                  read-only access to input, no copy
```

**Rule of thumb:**
| What you're doing | Parameter type |
|---|---|
| Reading input data (nums, target) | `const vector<int>&` or `const string&` |
| Building result (accumulator) | `vector<...>&` |
| Building current path/state | `vector<...>&` |
| Simple index/counter | `int` (by value) |
| Tree/list nodes | `TreeNode*` (pointer) |

---

## 13. Bonus: Direction Arrays for Grid Problems

```cpp
// Instead of writing 4 separate recursive calls:
dfs(r+1, c); dfs(r-1, c); dfs(r, c+1); dfs(r, c-1);

// Use a direction array (cleaner, extensible):
int dx[] = {0, 0, 1, -1};  // row deltas
int dy[] = {1, -1, 0, 0};  // col deltas

for (int d = 0; d < 4; d++) {
    int nr = r + dx[d];     // new row
    int nc = c + dy[d];     // new col
    dfs(board, word, nr, nc, idx + 1);
}

// For 8-directional (including diagonals):
int dx[] = {-1, -1, -1, 0, 0, 1, 1, 1};
int dy[] = {-1, 0, 1, -1, 1, -1, 0, 1};
```

---

## 📌 CHEAT SHEET

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RECURSION & BACKTRACKING CHEAT SHEET                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PARAMETER PASSING:                                                         │
│    int x          → by value (each call gets own copy)                     │
│    int& x         → by reference (all calls share same variable)           │
│    const int& x   → by const reference (read-only, no copy)               │
│    int* x         → by pointer (for nullable things: TreeNode*)            │
│    node->val      → access member via pointer (same as (*node).val)        │
│                                                                             │
│  BACKTRACKING TEMPLATE:                                                     │
│    void backtrack(result&, current&, inputs, start/state) {                │
│      if (goal) { result.push_back(current); return; }                      │
│      for (choice : choices) {                                              │
│        current.push_back(choice);        // CHOOSE                         │
│        backtrack(result, current, ...);  // EXPLORE                        │
│        current.pop_back();               // UN-CHOOSE                      │
│      }                                                                     │
│    }                                                                       │
│                                                                             │
│  PATTERNS:                                                                  │
│    Subsets      → start index, add at every level, i+1 no reuse           │
│    Permutations → used[] array, always i=0, base = size match             │
│    Combinations → start index + remaining target, i or i+1                │
│    Grid DFS     → mark visited, 4-dir loop, restore on backtrack          │
│    Tree DFS     → nullptr check, left/right recurse, path tracking        │
│                                                                             │
│  DUPLICATE SKIP:                                                            │
│    sort(nums.begin(), nums.end());                                         │
│    if (i > start && nums[i] == nums[i-1]) continue;                       │
│                                                                             │
│  COMMON STL:                                                                │
│    v.push_back(x)             → add to end                                │
│    v.pop_back()               → remove from end                           │
│    s.substr(pos, len)         → extract substring                         │
│    string(n, '.')             → string of n dots                          │
│    sort(v.begin(), v.end())   → sort vector                               │
│    (int)v.size()              → safe cast to avoid unsigned bugs           │
│                                                                             │
│  GOTCHAS:                                                                   │
│    ❌ Forgetting & on result/current → modifications lost                  │
│    ❌ size() - 1 on empty container → unsigned wraparound                  │
│    ❌ No nullptr check on TreeNode* → segfault                             │
│    ❌ Infinite recursion → stack overflow (no safety net)                   │
│    ✅ push_back(current) stores a COPY (unlike Python list.append)         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔁 QUICK QUIZ

Answer these before looking ahead. I'll grade your responses.

---

### Q1 (Easy):
In the following function signature, which parameters can be modified by the function, and which cannot?

```cpp
void solve(vector<int>& result, const vector<int>& nums, int idx, TreeNode* node);
```

For each of the 4 parameters, state: **modifiable / not modifiable / it depends**, and briefly explain why.

---

### Q2 (Medium):
Here's a backtracking function with a bug. Find it and explain what goes wrong at runtime:

```cpp
void backtrack(vector<vector<int>> result, vector<int>& current, vector<int>& nums, int start) {
    result.push_back(current);
    for (int i = start; i < nums.size(); i++) {
        current.push_back(nums[i]);
        backtrack(result, current, nums, i + 1);
        current.pop_back();
    }
}

vector<vector<int>> subsets(vector<int>& nums) {
    vector<vector<int>> result;
    vector<int> current;
    backtrack(result, current, nums, 0);
    return result;
}
```

---

### Q3 (Hard):
You are solving **LeetCode 47 — Permutations II** (permutations with duplicate elements, e.g., `[1, 1, 2]`). You need to return all **unique** permutations.

Write the complete C++ solution using the backtracking template. Make sure to:
1. Handle duplicates correctly
2. Use proper pass-by-reference
3. Add inline comments explaining your duplicate-skip logic

---

**Take your time. Reply with your answers and I'll grade each one.** 🎯
