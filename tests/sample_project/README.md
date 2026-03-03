# docstring-hellhole

**This project is intentionally messy.**

It exists to stress-test automated Python docstring generators.

Every construct that makes automated documentation hard is represented here:

- Closures, nested functions, and lambdas stored in variables
- Async generators, async context managers
- Abstract base classes, deep inheritance chains, mixins
- Decorators that change return types
- Mutable default arguments
- Positional-only and keyword-only parameters
- TypedDict, Generics, forward references
- Dynamic attributes added at runtime
- Monkey patching
- Conditional imports
- Dead code alongside live code
- Deliberately misleading variable names
- `*args` / `**kwargs` with no type information
- Functions that implicitly return `None`
- Functions raising different exceptions depending on runtime conditions
- Properties with side effects

Run with Python 3.10+.

```
pip install -r requirements.txt   # none required, stdlib only
python -m pytest tests/ -q        # basic smoke tests
```
