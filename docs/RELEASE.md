# Lappa release builds

Produce standalone binaries:

| Artifact | Platform |
| --- | --- |
| `lappa-windows-x64.exe` | Windows 10/11 x64 |
| `lappa-linux-x64` | Linux x64 |

Stack: **PyInstaller onefile** + FastAPI/uvicorn IDE server. Double-click / run with no args opens the browser on `http://127.0.0.1:8840`.

## Local build

### Windows

```powershell
cd D:\ThanhTrucSolutions\Lappa
pwsh scripts\build_release.ps1
# → dist\release\lappa-windows-x64.exe
```

### Linux

```bash
bash scripts/build_release.sh
# → dist/release/lappa-linux-x64
```

### Manual PyInstaller

```bash
cd packages/server
pip install -e ".[release]"
pyinstaller --noconfirm --clean lappa.spec
```

## GitHub Actions

Workflow: [`.github/workflows/release.yml`](../.github/workflows/release.yml)

| Trigger | Result |
| --- | --- |
| Tag `v*` (e.g. `v0.2.1`) | Build Win+Linux, create GitHub Release with assets + SHA256SUMS |
| `workflow_dispatch` | Build both platforms, upload artifacts (no release unless tag) |

```bash
git tag v0.2.1
git push origin v0.2.1
```

## Runtime layout (frozen)

Beside the executable:

```text
lappa-windows-x64.exe
lappa_data/
  demos/          # copied once from bundle
  docker/
  workspaces/     # bundles, meshes library, ros2_version.json
```

Override with env `LAPPA_HOME=/path/to/data`.

## CLI (same binary)

```text
lappa.exe                 # desktop: serve + browser
lappa.exe desktop
lappa.exe serve --port 8840
lappa.exe demo
lappa.exe ros2 list
lappa.exe package bundle -p diff_drive_2w
lappa.exe version
```
