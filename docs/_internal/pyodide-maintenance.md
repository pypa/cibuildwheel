# Maintaining Pyodide support

Last updated: May 2026

This page describes how to update cibuildwheel's Pyodide platform code when either:

- a new Pyodide alpha release arrives with support for a new [PyEmscripten Platform](https://pyodide.org/en/latest/development/abi.html) (which is tied to updates in Emscripten and CPython versions, compiler/linker flags, and so on), or
- when that alpha release graduates to a stable one.

## Background

Pyodide has three types of releases that matter to cibuildwheel:

- **Stable** – the most recent full Pyodide release (e.g., `0.29.x` / cp313). This is enabled by default with no special `CIBW_ENABLE` flag needed.
- **Prerelease** – an alpha/beta/rc Pyodide release that uses the _next_ CPython version (e.g., `314.0.0a1` / cp314). Users must opt in with `CIBW_ENABLE: pyodide-prerelease` to build against this version. This may or may not be available at any given time, depending on the Pyodide release cycle.
- **End-of-life (EoL)** – older Pyodide stable releases that are no longer the current stable. These are kept available behind `CIBW_ENABLE: pyodide-eol` so that users who still need to build for older Pyodide versions can do so.

The guards in `cibuildwheel/selector.py` enforce this distinction. The constraints files under `cibuildwheel/resources/` pin the exact tool versions that go with each build.

---

## When a new Pyodide prerelease becomes available

For example, consider a scenario when Pyodide ships a new `315.0.0a1` with cp315 support.

### 1. Add the new Python configuration

In `cibuildwheel/resources/build-platforms.toml`, add an entry under `[pyodide]`:

```toml
{ identifier = "cp315-pyodide_wasm32", version = "3.15", default_pyodide_version = "315.0.0a1", node_version = "v24", sha256 = "SHA256" },
```

`version` is the CPython version string, `default_pyodide_version` is the Pyodide release to use when the user does not pin one explicitly (use the latest available alpha/beta for a prerelease entry), and `node_version` is the minimum Node.js major required by that Pyodide release — check the [pyodide-build FAQ](https://pyodide-build.readthedocs.io/en/latest/faq.html#what-node-js-version-do-i-need) for a rudimentary idea of what the correct value is. `sha256` is the checksum of the Pyodide xbuildenv tarball.

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

### 4. Update tests

Update the unit tests so the new identifier is accepted by the selector with `PyodidePrerelease` enabled and rejected without it. Pyodide-specific integration tests may also need their hardcoded expected-wheel lists extended.

## When a Pyodide prerelease becomes stable

Pyodide uses a versioning scheme where the stable release for a given CPython version is named `[PythonMajorMinor].0.0`, so the first stable release shipping cp314 will be **`314.0.0`**. See [pyodide/pyodide#6084](https://github.com/pyodide/pyodide/issues/6084) for a rationale of this versioning scheme.

### 1. Update the stable entries, and remove (or replace) the prerelease entry

In `build-platforms.toml`, update the former prerelease entry's `default_pyodide_version` to the new stable release (e.g. `314.0.0`) and remove the prerelease marker from the identifier if present. Remove previous prerelease entries if they are now obsolete, or update them to the next prerelease if one is available. Move the previous stable version behind `pyodide-eol` rather than dropping it outright (see below).

### 2. Disable or update the prerelease guards

In `selector.py`:

- **If a new prerelease is available**: update the `fnmatch` pattern to the next identifier (e.g. `cp315-pyodide_*`) as described above.
- **If there is no new prerelease**: comment out the `PyodidePrerelease` logic.

### 3. Update the constraints file

Run `nox -s update_constraints` to regenerate the constraints file for the newly stable version. If the entry was already in `build-platforms.toml` as a prerelease, its constraints file already exists, and this step just refreshes it against the stable Pyodide release and updates the dependencies' versions.

### 4. Update tests

Update the unit tests so the newly stable identifier is accepted by the selector without needing `PyodidePrerelease` in the enable set. Pyodide-specific integration tests may also need their hardcoded expected-wheel lists extended.

## When an old Pyodide version is to be moved to end-of-life

When a Pyodide version is superseded by a new stable release, move it behind the `pyodide-eol` enable flag. We want to allow users who still build for older Pyodide ABIs time to upgrade.

### 1. Add the `pyodide-eol` guard in the selector

In `cibuildwheel/selector.py`, add (or update) the `PyodideEoL` guard to include the old identifier:

```python
if EnableGroup.PyodideEoL not in self.enable and fnmatch(build_id, "cp312-pyodide_*"):
    return False
```

### 2. Update tests

Update the unit tests so the EoL identifier requires `PyodideEoL` to be included in the enable set. The default (no `CIBW_ENABLE`) should exclude it.

## When an old Pyodide version is to be fully retired

Retirement is not expected to happen on a routine basis. It is only warranted when the Pyodide ecosystem itself has evolved to the point where an older ABI version is considered obsolete – for example, if the surrounding toolchain, packaging standards, or runtime infrastructure have moved on so substantially that building for the older version no longer makes practical sense. Any retirement is to be discussed and agreed upon by Pyodide maintainers before proceeding.

### 1. Remove the Python configuration

Delete the entry from `build-platforms.toml` and remove the `PyodideEoL` guard for that identifier in `selector.py`.

### 2. Delete the constraints file

Remove `cibuildwheel/resources/constraints-pyodideXYZ.txt`.

### 3. Update tests

Remove references to the old identifier from the unit tests, integration tests, and drop any expected-wheel entries for it from the test helper.
