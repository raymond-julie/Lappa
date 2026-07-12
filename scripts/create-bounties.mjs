import { execSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

const REPO = 'mergeos-bounties/Lappa';

function sh(cmd) {
  return execSync(cmd, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
}

function ensureLabel(name, color, description) {
  try {
    sh(`gh label create ${JSON.stringify(name)} --repo ${REPO} --color ${color} --description ${JSON.stringify(description)}`);
  } catch {
    try {
      sh(`gh label edit ${JSON.stringify(name)} --repo ${REPO} --color ${color} --description ${JSON.stringify(description)}`);
    } catch { /* ignore */ }
  }
}

function createIssue(title, body, labels) {
  const dir = mkdtempSync(join(tmpdir(), 'lappa-issue-'));
  const file = join(dir, 'body.md');
  try {
    writeFileSync(file, body, 'utf8');
    const labelFlags = labels.map((l) => `--label ${JSON.stringify(l)}`).join(' ');
    console.log(sh(`gh issue create --repo ${REPO} --title ${JSON.stringify(title)} --body-file ${JSON.stringify(file)} ${labelFlags}`));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

for (const row of [
  ['bounty', '5319E7', 'Eligible for MergeOS MRG bounty'],
  ['bounty: feature', 'A2EEEF', 'Feature bounty'],
  ['ide', '1D76DB', 'Lappa IDE UI'],
  ['sim', 'D93F0B', 'Simulation engine'],
  ['docker', '0E8A16', 'Docker show mode'],
  ['ros2', 'FBCA04', 'ROS2 package'],
  ['demo', 'C5DEF5', 'Robot demo package'],
  ['hot-reload', 'BFD4F2', 'Hot reload'],
  ['reward:25-mrg', 'FEF2C0', '25 MRG'],
  ['reward:50-mrg', 'FEF2C0', '50 MRG'],
  ['reward:100-mrg', 'FEF2C0', '100 MRG'],
  ['reward:200-mrg', 'FEF2C0', '200 MRG'],
  ['good first issue', '7057FF', 'Good first issue'],
  ['documentation', '0075CA', 'Docs'],
]) ensureLabel(...row);

const footer = `

## Claim

1. Star https://github.com/mergeos-bounties/Lappa and https://github.com/mergeos-bounties/mergeos  
2. Comment: \`I claim this bounty\`  
3. MergeOS [Claim #1](https://github.com/mergeos-bounties/mergeos/issues/1) with issue link  
4. PR to **Lappa** with \`Fixes #<n>\`

Policy: [docs/BOUNTY.md](../blob/master/docs/BOUNTY.md)
`;

const issues = [
  { title: '[25 MRG] Docs: Windows quickstart + Docker Desktop notes', labels: ['bounty', 'bounty: feature', 'documentation', 'reward:25-mrg', 'good first issue'],
    body: `## 25 MRG\n\nExpand docs for Windows users: Python, Docker optional, ports, screenshots.\n\n## Acceptance\n- [ ] docs/WINDOWS.md + README link\n${footer}` },
  { title: '[25 MRG] IDE: keyboard command palette (Ctrl+Shift+P)', labels: ['bounty', 'bounty: feature', 'ide', 'reward:25-mrg', 'good first issue'],
    body: `## 25 MRG\n\nCommand palette for Run Sim, Stop, Open Demo, Toggle Hot Reload.\n\n## Acceptance\n- [ ] Screenshots + works offline\n${footer}` },
  { title: '[50 MRG] Sim: obstacle map + lidar hits', labels: ['bounty', 'bounty: feature', 'sim', 'reward:50-mrg'],
    body: `## 50 MRG\n\nAdd static obstacles to native sim; lidar rays report hit distances.\n\n## Acceptance\n- [ ] Tests for ray-cast\n- [ ] Canvas shows walls\n${footer}` },
  { title: '[50 MRG] Sim: multi-robot session (2 bases)', labels: ['bounty', 'bounty: feature', 'sim', 'reward:50-mrg'],
    body: `## 50 MRG\n\nRun two diff-drive robots with separate cmd_vel.\n\n## Acceptance\n- [ ] API + canvas\n${footer}` },
  { title: '[100 MRG] Docker: live ros2 launch bridge from IDE', labels: ['bounty', 'bounty: feature', 'docker', 'ros2', 'reward:100-mrg'],
    body: `## 100 MRG\n\nStart/stop \`ros2 launch\` inside lappa-ros2 container; stream logs to console.\n\n## Acceptance\n- [ ] Works with Docker Desktop on Windows docs\n- [ ] Graceful fallback if no Docker\n${footer}` },
  { title: '[100 MRG] Hot-reload: colcon build incremental in container', labels: ['bounty', 'bounty: feature', 'docker', 'hot-reload', 'reward:100-mrg'],
    body: `## 100 MRG\n\nOn file save, trigger incremental build + node restart in Docker mode.\n\n## Acceptance\n- [ ] Documented flow + logs\n${footer}` },
  { title: '[50 MRG] Demo: mecanum 4-wheel package', labels: ['bounty', 'bounty: feature', 'demo', 'reward:50-mrg'],
    body: `## 50 MRG\n\nNew demo package + engine kind for mecanum kinematics.\n\n## Acceptance\n- [ ] package.xml + tests + canvas style\n${footer}` },
  { title: '[50 MRG] Demo: differential tracked robot', labels: ['bounty', 'bounty: feature', 'demo', 'reward:50-mrg'],
    body: `## 50 MRG\n\nTracked skid-steer demo package.\n\n## Acceptance\n- [ ] Tests + IDE icon/canvas\n${footer}` },
  { title: '[50 MRG] URDF: parse links and draw simple sticks', labels: ['bounty', 'bounty: feature', 'ide', 'ros2', 'reward:50-mrg'],
    body: `## 50 MRG\n\nParse demo URDF and overlay on canvas.\n\n## Acceptance\n- [ ] At least base + wheels\n${footer}` },
  { title: '[100 MRG] Foxglove / rosbridge web panel stub', labels: ['bounty', 'bounty: feature', 'ide', 'docker', 'reward:100-mrg'],
    body: `## 100 MRG\n\nOptional panel connecting to rosbridge when Docker runtime is up.\n\n## Acceptance\n- [ ] Offline message if bridge down\n${footer}` },
  { title: '[50 MRG] IDE: split terminal with ANSI log colors', labels: ['bounty', 'bounty: feature', 'ide', 'reward:50-mrg'],
    body: `## 50 MRG\n\nImprove bottom console for multi-stream logs.\n\n## Acceptance\n- [ ] Screenshots\n${footer}` },
  { title: '[25 MRG] CI: cache pip + demo package path check', labels: ['bounty', 'bounty: feature', 'documentation', 'reward:25-mrg', 'good first issue'],
    body: `## 25 MRG\n\nHarden .github/workflows/ci.yml.\n\n## Acceptance\n- [ ] CI green\n${footer}` },
  { title: '[50 MRG] Server: workspace multi-root (import folder)', labels: ['bounty', 'bounty: feature', 'ide', 'reward:50-mrg'],
    body: `## 50 MRG\n\nAPI to register external package path (read/write sandboxed).\n\n## Acceptance\n- [ ] Tests for path escape blocked\n${footer}` },
  { title: '[100 MRG] Electron/Tauri desktop shell', labels: ['bounty', 'bounty: feature', 'ide', 'reward:100-mrg'],
    body: `## 100 MRG\n\nPackage Lappa IDE as desktop app launching local server.\n\n## Acceptance\n- [ ] README build steps Windows\n${footer}` },
  { title: '[200 MRG] E2E video: edit teleop → hot-reload → sim moves', labels: ['bounty', 'bounty: feature', 'ide', 'sim', 'hot-reload', 'reward:200-mrg'],
    body: `## 200 MRG\n\nRecord reproducible E2E on Windows with evidence.\n\n## Acceptance\n- [ ] Video/screenshots + steps\n${footer}` },
  { title: '[25 MRG] Vietnamese UI strings for IDE chrome', labels: ['bounty', 'bounty: feature', 'ide', 'reward:25-mrg', 'good first issue'],
    body: `## 25 MRG\n\ni18n toggle EN/VI for titlebar and panels.\n\n## Acceptance\n- [ ] Screenshots\n${footer}` },
  { title: '[50 MRG] Topic graph panel (nodes/topics mock)', labels: ['bounty', 'bounty: feature', 'ide', 'ros2', 'reward:50-mrg'],
    body: `## 50 MRG\n\nShow mock graph from package launch file; live when docker.\n\n## Acceptance\n- [ ] UI + tests\n${footer}` },
  { title: '[50 MRG] Sim: export trajectory CSV', labels: ['bounty', 'bounty: feature', 'sim', 'reward:50-mrg'],
    body: `## 50 MRG\n\nDownload odom trail as CSV from IDE.\n\n## Acceptance\n- [ ] Endpoint + button\n${footer}` },
];

for (const issue of issues) {
  createIssue(issue.title, issue.body, issue.labels);
}
console.log(`Created ${issues.length} issues on ${REPO}`);
