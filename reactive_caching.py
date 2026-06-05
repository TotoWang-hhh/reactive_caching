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


__version__ = "0.2.0"


class CachedClass():
    """Caching ability of a class.

    Must set `self._cache_initialized` to `True` after `__init__()`
    """

    _cached_rules: dict[str, list | _typing.Literal["-all-"] | _typing.Literal["-exposed-"]] = {}

    def __init_subclass__(cls) -> None:
        """Inherit or create empty, then configure caching rules for classes."""
        ## Inherit or create
        inherit: bool = True
        if hasattr(cls, "_inherit_cache_rule"):
            if isinstance(cls._inherit_cache_rule, bool):   # type: ignore
                inherit = cls._inherit_cache_rule           # type: ignore
        cls._cached_rules: dict[str, list | _typing.Literal["-all-"] | _typing.Literal["-exposed-"]]
        if inherit:
            inherited_rules = {}
            for parent_cls in reversed(cls.__mro__[1:]):
                # Override rules, the first parent class is the most prior, and last overrided
                if issubclass(parent_cls, CachedClass):
                    inherited_rules.update(parent_cls._cached_rules)
            cls._cached_rules = inherited_rules
        else:
            cls._cached_rules = {}
        ## Add config of current class
        for name, obj in cls.__dict__.items():
            if isinstance(obj, property):
                func = obj.fget
                if hasattr(func, "_cache_rule"):
                    cls._cached_rules[name] = func._cache_rule # type: ignore

    def __init__(self) -> None:
        """Initialize a cache class."""
        self._cache_alive: bool = False
        self._cache_dirty_state: dict[str, bool] = {}
        self._cache_data: dict[str, _typing.Any] = {}

        for prop in type(self)._cached_rules.keys():
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
        if name in [ # Ignore names used by caching system
            "_cache_initialized", 
            "_cached_rules", 
            "_cache_data", 
            "_cache_dirty_state", 
            "_cache_alive"
            ]:
            return
        for prop in self._cached_rules.keys():
            if self._cache_dirty_state[prop]:
                continue # If is already dirty, then can skip
                # Because no need to flag a prop cache that is already dirty as dirty again
            match self._cached_rules[prop]:
                case "-all-":
                    self._cache_dirty_state[prop] = True
                    self._on_cache_dirty(prop)
                case "-exposed-":
                    if not name.startswith("_"):
                        self._cache_dirty_state[prop] = True
                        self._on_cache_dirty(prop)
                case list() | tuple():
                    if name in self._cached_rules[prop]:
                        self._cache_dirty_state[prop] = True
                        self._on_cache_dirty(prop)
                case _:
                    _warnings.warn(
                        f"Cache rule {self._cached_rules[prop]} neither a valid list nor valid "
                        "keyword, check spelling! The cache will be regarded as dirty anyway."
                        )
                    self._cache_dirty_state[prop] = True
                    self._on_cache_dirty(prop)
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
    """

    PropType = _typing.TypeVar("PropType")

    def decorator(func: _typing.Callable[[CachedClass], PropType]) -> property:

        func_name = func.__name__

        def wrapper(self: CachedClass) -> PropType:
            if not self._cache_alive:
                _warnings.warn(
                    "Trying to get a cached property from a destroyed / booting cached obj. This "
                    "operation is not suggested and caching system will be bypassed."
                    )
                return func(self)
            if func_name not in self._cache_data:
                return func(self)
            if self._cache_dirty_state[func_name]:
                # If cache in dirty state, re-calculate it
                self._cache_data[func_name] = func(self)
                self._cache_dirty_state[func_name] = False
            return self._cache_data[func_name]

        wrapper._cache_rule = watched_attrs
        return property(wrapper)

    return decorator
