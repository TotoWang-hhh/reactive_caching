"""Caching module for class properties, with automatic invalidation based on attribute changes."""

# Copyright 2026 rgzz666
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations as _

import typing as _typing

import warnings as _warnings


__version__ = "0.2.1"


type CacheRule= \
    list[str] | \
    _typing.Literal["-all-"] | \
    _typing.Literal["-exposed-"]


@_typing.runtime_checkable
class _BoundFunc(_typing.Protocol):
    """Type representing any function bound to a caching rule."""

    calc: _typing.Callable
    _cache_rule: CacheRule
    # _lazy: bool = True

    def __call__(self, *args, **kwargs) -> _typing.Any: ...


class CachedClass:
    """Caching ability of a class.

    Must set `self._cache_initialized` to `True` after `__init__()`
    """

    _cache_rules: dict[_typing.Callable, CacheRule] = {}

    def __init_subclass__(cls) -> None:
        """Inherit or create empty, then configure caching rules for classes."""
        ## Inherit or create
        inherit: bool = True
        if hasattr(cls, "_inherit_cache_rule"):
            if isinstance(cls._inherit_cache_rule, bool):   # type: ignore
                inherit = cls._inherit_cache_rule           # type: ignore
        cls._cache_rules: dict[_typing.Callable, CacheRule]
        if inherit:
            inherited_rules = {}
            for parent_cls in reversed(cls.__mro__[1:]):
                # Override rules, the first parent class is the most prior, and last overrided
                if issubclass(parent_cls, CachedClass):
                    inherited_rules.update(parent_cls._cache_rules)
            cls._cache_rules = inherited_rules
        else:
            cls._cache_rules = {}
        ## Add config of current class
        for _, obj in cls.__dict__.items():
            if isinstance(obj, property):
                fget = obj.fget
                if _typing.TYPE_CHECKING:
                    fget = _typing.cast(function, fget)
                if isinstance(fget, _BoundFunc):
                    func = fget.calc
                    cls._cache_rules[func] = fget._cache_rule # type: ignore

    def __init__(self) -> None:
        """Initialize a cache class."""
        self._cache_alive: bool = False
        self._cache_dirty_state: dict[_typing.Callable, bool] = {}
        self._cache_data: dict[_typing.Callable, _typing.Any] = {}

        for prop in type(self)._cache_rules.keys():
            self._cache_dirty_state[prop] = True
            self._cache_data[prop] = None

        self._cache_alive = True

    def _on_cache_dirty(self, prop_name: str) -> None:
        """Customizable operations to carry out when a cache is flagged dirty. To be overrided.

        To implement running a specific routine on a cache is flagged dirty, override this function 
        when subclassing `CachedClass` with such routine.
        """
        return None

    def __setattr__(self, name: str, value: _typing.Any) -> None:
        """Set attr and update cache dirty state."""
        super().__setattr__(name, value)
        if not hasattr(self, "_cache_alive"):
            return
        if not self._cache_alive:
            return
        if name in [ # Ignore names used by caching system
            "_cached_rules", 
            "_cache_data", 
            "_cache_dirty_state", 
            "_cache_alive"
            ]:
            return
        for prop in self._cache_rules.keys():
            if self._cache_dirty_state[prop]:
                continue # If is already dirty, then can skip
                # Because no need to flag a prop cache that is already dirty as dirty again
            match self._cache_rules[prop]:
                case "-all-":
                    self._cache_dirty_state[prop] = True
                    self._on_cache_dirty(prop.__name__)
                case "-exposed-":
                    if not name.startswith("_"):
                        self._cache_dirty_state[prop] = True
                        self._on_cache_dirty(prop.__name__)
                case list() | tuple():
                    if name in self._cache_rules[prop]:
                        self._cache_dirty_state[prop] = True
                        self._on_cache_dirty(prop.__name__)
                case _:
                    _warnings.warn(
                        f"Cache rule {self._cache_rules[prop]} neither a valid list nor valid "
                        "keyword, check spelling! The cache will be regarded as dirty anyway."
                        )
                    self._cache_dirty_state[prop] = True
                    self._on_cache_dirty(prop.__name__)
                    return

    def destroy_cache(self):
        """Destroy cache."""
        if not self._cache_alive:
            return
        self._cache_alive = False
        self._cache_data.clear()
        self._cache_dirty_state.clear()


def cached_property(
    watched_attrs: list[str] | _typing.Literal["-all-"] | _typing.Literal["-exposed-"]
    ) -> _typing.Callable[[_typing.Callable], property]:
    """Generate a decorator for cached properties.

    Caching Rules
    -------------
    Caching rules can be set to either a list of property names, or one of the keywords. Effect 
    of each configuration will be introduced below: 
    - **List of property names:** All attributes with name included in that list will be 
        watched. When any of their values is changed, the cache will be flagged dirty.
    - **Keyword `-all-`:** All attributes will be watched and if any of them is changed, the 
        cache will be flagged dirty.
    - **Keyword `-exposed-`:** All exposed attributes (those with name that does not starts 
        with `_`) will be watched. When any of their values is changed, the cache will be flagged 
        dirty.

    :param watched_attrs: List of attributes to watch or a keyword, in other words, caching rule
    """

    PropType = _typing.TypeVar("PropType")

    def decorator(func: _typing.Callable[[CachedClass], PropType]) -> property:

        # func_name = func.__name__

        def wrapper(self: CachedClass) -> PropType:
            if not self._cache_alive:
                _warnings.warn(
                    "Trying to get a cached property from a destroyed / booting cached obj. This "
                    "operation is not suggested and caching system will be bypassed."
                    )
                return func(self)
            if func not in self._cache_data:
                return func(self)
            if self._cache_dirty_state[func]:
                # If cache in dirty state, re-calculate it
                self._cache_data[func] = func(self)
                self._cache_dirty_state[func] = False
            return self._cache_data[func]

        wrapper = _typing.cast(_BoundFunc, wrapper)
        wrapper._cache_rule = watched_attrs
        wrapper.calc = func
        return property(wrapper)

    return decorator


_SourceCallableType = _typing.TypeVar("_SourceCallableType", bound = _typing.Callable)

def on_attr_change(
    watched_attrs: list[str] | _typing.Literal["-all-"] | _typing.Literal["-exposed-"]
    ) -> _typing.Callable[[_SourceCallableType], _SourceCallableType]:
    """Carry out specific task when specific attributes changes.

    :param watched_attrs: List of attributes to watch or a keyword, in other words, caching rule
    """

    def decorator(func: _SourceCallableType) -> _SourceCallableType:
        func.calc = func
        func._cache_rule = watched_attrs
        return func

    return decorator