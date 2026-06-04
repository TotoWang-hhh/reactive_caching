"""Caching module for class properties, with auto invalidation."""
from __future__ import annotations as _

import typing as _typing

import warnings as _warnings


class CachedClass():
    """Caching ability of a class.

    Must set `self._cache_initialized` to `True` after `__init__()`
    """

    def __init_subclass__(cls) -> None:
        """Inherit or create empty caching rule for classes."""
        inherit: bool = True
        if hasattr(cls, "_inherit_cache_rule"):
            if isinstance(cls._inherit_cache_rule, bool):   # type: ignore
                inherit = cls._inherit_cache_rule           # type: ignore
        if cls is CachedClass:
            inherit = False
        cls._cached_list: dict[str, list | _typing.Literal["-all-"] | _typing.Literal["-exposed-"]]
        if inherit:
            inherited_rules = {}
            for parent_cls in reversed(cls.__mro__[1:]):
                # Override rules, the first parent class is the most prior, and last overrided
                if issubclass(parent_cls, CachedClass):
                    inherited_rules.update(parent_cls._cached_list)
            cls._cached_list = inherited_rules
        else:
            cls._cached_list = {}

    def __init__(self) -> None:
        """Initialize a cache class."""
        self._cache_dirty_state: dict[str, bool] = {}
        self._cache_data: dict[str, _typing.Any] = {}
        self._cache_alive: bool = False

        for prop in type(self)._cached_list:
            self._cache_dirty_state[prop] = True
            self._cache_data[prop] = None

        self._cache_alive = True

    @classmethod
    def _cached_property(
        cls, 
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
            cls._cached_list[func.__name__] = watched_attrs

            @property
            def wrapper(self: CachedClass) -> PropType:
                if not self._cache_alive:
                    _warnings.warn(
                        "Trying to get a cached property from a destroyed cached class. This "
                        "operation is not suggested and caching system will be bypassed."
                        )
                    return func(self)
                if self._cache_dirty_state[func.__name__]:
                    # If cache in dirty state, re-calculate it
                    self._cache_data[func.__name__] = func(self)
                    self._cache_dirty_state[func.__name__] = False
                return self._cache_data[func.__name__]

            return wrapper

        return decorator

    def _on_cache_dirty(self, prop_name: str) -> None:
        """Customizable operations to carry out when a cache is flagged dirty. To be overrided.

        To implement running a specific routine on a cache is flagged dirty, override this function 
        when subclassing `CachedClass` with such routine.
        """
        return None

    def __setattr__(self, name: str, value: _typing.Any) -> None:
        """Set attr and update cache dirty state."""
        if not self._cache_alive:
            super().__setattr__(name, value)
            return
        super().__setattr__(name, value)
        if name in [ # Ignore names used by caching system
            "_cache_initialized", 
            "_cached_list", 
            "_cached_data", 
            "_cache_dirty_state", 
            "_cache_alive"
            ]:
            return
        for prop in self._cached_list.keys():
            if self._cache_dirty_state[prop]:
                continue # If is already dirty, then can skip
                # Because no need to flag a prop cache that is already dirty as dirty again
            match self._cached_list[prop]:
                case "-all-":
                    self._cache_dirty_state[prop] = True
                    self._on_cache_dirty(prop)
                case "-exposed-":
                    if not name.startswith("_"):
                        self._cache_dirty_state[prop] = True
                        self._on_cache_dirty(prop)
                case list() | tuple():
                    if name in self._cached_list[prop]:
                        self._cache_dirty_state[prop] = True
                        self._on_cache_dirty(prop)
                case _:
                    _warnings.warn(
                        f"Cache rule {self._cached_list[prop]} neither a valid list nor valid "
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