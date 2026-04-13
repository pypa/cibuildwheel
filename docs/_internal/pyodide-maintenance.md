# Maintaining Pyodide support

This page describes how to update cibuildwheel's Pyodide platform code when either:

- a new Pyodide alpha release arrives with support for a new [PyEmscripten Platform](https://pyodide.org/en/latest/development/abi.html) (which is tied to updates in Emscripten and CPython versions, compiler/linker flags, and so on), or
- when that alpha release graduates to a stable one.

## Background

Pyodide has two types of releases that matter to cibuildheel:

- **Stable** – the most recent full Pyodide release (e.g., `0.29.x` / cp313). This is enabled by default with no special `CIBW_ENABLE` flag needed.
- **Prerelease** – an alpha/beta/rc Pyodide release that uses the _next_ CPython version (e.g., `314.0.0a1` / cp314). Users must opt in with `CIBW_ENABLE: pyodide-prerelease` to build against this version. This may or may not be available at any given time, depending on the Pyodide release cycle.

The guards in `cibuildwheel/selector.py` enforce this distinction. The constraints files under `cibuildwheel/resources/` pin the exact tool versions that go with each build.

---

## When a new Pyodide prerelease becomes available

For example, consider a scenario when Pyodide ships a new `315.0.0a1` with cp315 support.

### 1. Add the new Python configuration

In `cibuildwheel/resources/build-platforms.toml`, add an entry under `[pyodide]`:

```toml
{ identifier = "cp315-pyodide_wasm32", version = "3.15", default_pyodide_version = "315.0.0a1", node_version = "v24" },
```

`version` is the CPython version string, `default_pyodide_version` is the Pyodide release to use when the user does not pin one explicitly (use the latest available alpha/beta for a prerelease entry), and `node_version` is the minimum Node.js major required by that Pyodide release — check the [pyodide-build FAQ](https://pyodide-build.readthedocs.io/en/latest/faq.html#what-node-js-version-do-i-need) for a rudimentary idea of what the correct value is.

### 2. Update the prerelease guards in the selector

In `cibuildwheel/selector.py`, update the patterns in the `PyodidePrerelease` guards to match the new identifier:

```python
if EnableGroup.PyodidePrerelease not in self.enable and fnmatch(
    build_id, "cp315-pyodide_*"
):
    return False
```

### 3. Generate and pin a constraints file

Run the `update_constraints` `nox` session, which reads `build-platforms.toml` and regenerates all Pyodide constraints files automatically:

```bash
nox -s update_constraints
```

Alternatively, run the generator script directly:

```bash
python bin/generate_pyodide_constraints.py 315.0.0a1 \
    | uv pip compile - --python-version=3.15 \
        -o cibuildwheel/resources/constraints-pyodide315.txt
```

### 4. Update tests and update CI configuration

- Update the unit tests so the new identifier is accepted by the selector with `PyodidePrerelease` enabled and rejected without it. Pyodide-specific integration tests may also need their hardcoded expected-wheel lists extended.

- Run the full test suite with `CIBW_PLATFORM=pyodide` and `CIBW_ENABLE=pyodide-prerelease` environment variables to make sure the new configuration is exercised in CI.

## When a Pyodide prerelease becomes stable

Pyodide uses a versioning scheme where the stable release for a given CPython version is named `[PythonMajorMinor].0.0`, so the first stable release shipping cp314 will be **`314.0.0`**. See [pyodide/pyodide#6084](https://github.com/pyodide/pyodide/issues/6084) for a rationale of this versioning scheme.

### 1. Update the stable entries, and remove (or replace) the prerelease entry

In `build-platforms.toml`, update the former prerelease entry's `default_pyodide_version` to the new stable release (e.g. `314.0.0`) and remove the prerelease marker from the identifier if present. Remove previous prerelease entries if they are now obsolete, or update them to the next prerelease if one is available. Based on your discretion, you may choose to keep the old stable entry for a while if it is still supported by Pyodide, or remove it immediately if it is already retired.

### 2. Disable or update the prerelease guards

In `selector.py`:

- **If a new prerelease is available**: update the `fnmatch` pattern to the next identifier (e.g. `cp315-pyodide_*`) as described above.
- **If there is no new prerelease**: comment out the `PyodidePrerelease` logic.

### 3. Update the constraints file

Run `nox -s update_constraints` to regenerate the constraints file for the newly stable version. If the entry was already in `build-platforms.toml` as a prerelease, its constraints file already exists, and this step just refreshes it against the stable Pyodide release and updates the dependencies' versions.

### 4. Update tests and CI configuration

Update the unit tests so the newly stable identifier is accepted by the selector without needing `PyodidePrerelease` in the enable set. Pyodide-specific integration tests may also need their hardcoded expected-wheel lists extended.

- Run the full test suite with `CIBW_PLATFORM=pyodide` and `CIBW_ENABLE=pyodide-prerelease` environment variables to make sure the new configuration is exercised in CI.

## When an old Pyodide version is to be retired

### 1. Remove the python configuration

Delete the entry from `build-platforms.toml`.

### 2. Delete the constraints file

Remove `cibuildwheel/resources/constraints-pyodideXYZ.txt`.

### 3. Update tests and CI configuration

Remove references to the old identifier from the unit tests, integration tests, and drop any expected-wheel entries for it from the test helper. Also, ensure that no CI job is still trying to build it.
