# Changelog

## 0.2.0 (Beta)

### Changed

- Add check of cache system alive state when `__setattr__` to prevent errors.

## 0.2.0 (Beta)

### Added

- Functionality test script.

### Changed

- Changed `reactive_caching.CachedClass.cached_property()` decorator factory to `reactive_caching.cached_property()` to make things work.
- Changed rules specifying routine, from adding record to class directly to adding the record to the function, then detect them on class initialization. This is because the class cannot be accessed when using the decorator factory.

## 0.1.1 (Beta, Recalled)

### Added

- setuptools config to include the package file when build. (oh my bad memory)

### Changed

- Description in docstring and on PyPI, and the introduction in README.
- Dynamic versioning according to version number in code.

## 0.1.0 (Beta)

Very first version.
