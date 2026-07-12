/* Lappa IDE client */
const API = "";
let demos = [];
let activePkg = null;
let openFile = null;
let editor = null;
let hotOn = true;
let simRunning = false;
let trail = [];
let keys = {};
let selectedMeshId = null;
let ros2Versions = [];

function log(msg) {
  const el = document.getElementById("console");
  el.textContent += msg + "\n";
  el.scrollTop = el.scrollHeight;
}

async function api(path, opts = {}) {
  const r = await fetch(API + path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || r.statusText);
  }
  const ct = r.headers.get("content-type") || "";
  if (ct.includes("application/json")) return r.json();
  return r.text();
}

function setPill(text, cls) {
  const p = document.getElementById("status-pill");
  p.textContent = text;
  p.className = "pill " + (cls || "idle");
}

function renderTree(files) {
  const root = document.getElementById("file-tree");
  root.innerHTML = "";
  (files || []).forEach((f) => {
    const d = document.createElement("div");
    d.className = "item" + (openFile === f ? " on" : "");
    d.textContent = f;
    d.title = f;
    d.onclick = () => openPath(f);
    root.appendChild(d);
  });
}

function renderDemos() {
  const root = document.getElementById("demo-list");
  root.innerHTML = "";
  demos.forEach((d) => {
    const card = document.createElement("div");
    card.className = "demo-card";
    card.innerHTML = `<h4>${d.name}</h4><p>${d.description || "ROS2 package"}</p>`;
    card.onclick = () => loadDemo(d.name);
    root.appendChild(card);
  });
}

async function loadDemo(name) {
  log("open demo " + name);
  activePkg = await api("/api/workspace/open", {
    method: "POST",
    body: JSON.stringify({ demo: name }),
  });
  document.getElementById("pkg-label").textContent = activePkg.name;
  renderTree(activePkg.files);
  const prefer = activePkg.files.find((f) => f.endsWith("teleop.py"))
    || activePkg.files.find((f) => f === "package.xml")
    || activePkg.files[0];
  if (prefer) await openPath(prefer);
  await api("/api/sim/start", {
    method: "POST",
    body: JSON.stringify({ demo: name }),
  });
  simRunning = true;
  setPill("running", "run");
  trail = [];
  log("sim started: " + name + " (native)");
}

async function openPath(rel) {
  const data = await api("/api/files?path=" + encodeURIComponent(rel));
  openFile = rel;
  document.getElementById("tabs").innerHTML =
    `<div class="tab on">${rel}</div>`;
  renderTree(activePkg?.files || []);
  if (editor) {
    const lang = rel.endsWith(".py")
      ? "python"
      : rel.endsWith(".xml") || rel.endsWith(".urdf")
        ? "xml"
        : rel.endsWith(".yaml") || rel.endsWith(".yml")
          ? "yaml"
          : "plaintext";
    monaco.editor.setModelLanguage(editor.getModel(), lang);
    editor.setValue(data.content);
  }
}

async function saveCurrent() {
  if (!openFile || !editor) return;
  await api("/api/files", {
    method: "PUT",
    body: JSON.stringify({ path: openFile, content: editor.getValue() }),
  });
  log("saved " + openFile + " (hot-reload notified)");
}

function setupMonaco() {
  return new Promise((resolve) => {
    require.config({
      paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.49.0/min/vs" },
    });
    require(["vs/editor/editor.main"], () => {
      editor = monaco.editor.create(document.getElementById("editor"), {
        value: "# Open a demo package to start\n",
        language: "python",
        theme: "vs-dark",
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 13,
        minimap: { enabled: true },
        automaticLayout: true,
        scrollBeyondLastLine: false,
      });
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        saveCurrent().catch((e) => log("save error: " + e.message));
      });
      resolve();
    });
  });
}

function drawRobot(ctx, state, w, h) {
  ctx.clearRect(0, 0, w, h);
  // grid
  ctx.strokeStyle = "#1c2533";
  ctx.lineWidth = 1;
  const step = 40;
  for (let x = 0; x < w; x += step) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 0; y < h; y += step) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }
  // origin
  const cx = w / 2;
  const cy = h / 2;
  const scale = 80;
  const rx = cx + (state.x || 0) * scale;
  const ry = cy - (state.y || 0) * scale;

  trail.push({ x: rx, y: ry });
  if (trail.length > 200) trail.shift();
  ctx.strokeStyle = "#388bfd66";
  ctx.lineWidth = 2;
  ctx.beginPath();
  trail.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
  ctx.stroke();

  // lidar
  if (state.lidar && state.lidar.length) {
    ctx.strokeStyle = "#3fb95033";
    const th0 = state.theta || 0;
    state.lidar.forEach((r, i) => {
      const a = th0 + (i / state.lidar.length) * Math.PI * 2;
      const lx = rx + Math.cos(a) * r * 12;
      const ly = ry - Math.sin(a) * r * 12;
      ctx.beginPath();
      ctx.moveTo(rx, ry);
      ctx.lineTo(lx, ly);
      ctx.stroke();
    });
  }

  const kind = state.kind || "diff_drive_2w";
  ctx.save();
  ctx.translate(rx, ry);
  ctx.rotate(-(state.theta || 0));

  if (kind === "simple_arm") {
    const j = state.joints || [0.4, -0.6];
    ctx.strokeStyle = "#a371f7";
    ctx.lineWidth = 6;
    ctx.lineCap = "round";
    let x = 0, y = 0;
    const l1 = 50, l2 = 40;
    const x1 = Math.cos(j[0]) * l1;
    const y1 = Math.sin(j[0]) * l1;
    const x2 = x1 + Math.cos(j[0] + j[1]) * l2;
    const y2 = y1 + Math.sin(j[0] + j[1]) * l2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(x1, -y1);
    ctx.lineTo(x2, -y2);
    ctx.stroke();
    ctx.fillStyle = "#58a6ff";
    [[0, 0], [x1, -y1], [x2, -y2]].forEach(([px, py]) => {
      ctx.beginPath();
      ctx.arc(px, py, 5, 0, Math.PI * 2);
      ctx.fill();
    });
  } else if (kind === "omni_3w") {
    ctx.fillStyle = "#1f6feb";
    ctx.beginPath();
    ctx.arc(0, 0, 18, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#79c0ff";
    for (let i = 0; i < 3; i++) {
      const a = (i * 2 * Math.PI) / 3;
      ctx.beginPath();
      ctx.arc(Math.cos(a) * 16, Math.sin(a) * 16, 5, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.strokeStyle = "#fff";
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(24, 0);
    ctx.stroke();
  } else if (kind === "ackermann_4w") {
    ctx.fillStyle = "#d29922";
    ctx.fillRect(-22, -12, 44, 24);
    ctx.fillStyle = "#222";
    [[-14, -14], [-14, 10], [14, -14], [14, 10]].forEach(([wx, wy]) => {
      ctx.fillRect(wx - 4, wy, 8, 4);
    });
    ctx.strokeStyle = "#fff";
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(28, 0);
    ctx.stroke();
  } else if (kind === "tricycle_3w") {
    ctx.fillStyle = "#a371f7";
    ctx.beginPath();
    ctx.moveTo(20, 0);
    ctx.lineTo(-14, 14);
    ctx.lineTo(-14, -14);
    ctx.closePath();
    ctx.fill();
  } else {
    // diff 2w
    ctx.fillStyle = "#3fb950";
    ctx.fillRect(-16, -12, 32, 24);
    ctx.fillStyle = "#111";
    ctx.fillRect(-14, -16, 10, 6);
    ctx.fillRect(-14, 10, 10, 6);
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(22, 0);
    ctx.stroke();
  }
  ctx.restore();

  // HUD
  ctx.fillStyle = "#8b949e";
  ctx.font = "11px JetBrains Mono, monospace";
  ctx.fillText(
    `${kind}  t=${(state.t || 0).toFixed(1)}s  pose=(${(state.x || 0).toFixed(2)}, ${(state.y || 0).toFixed(2)}, ${(state.theta || 0).toFixed(2)})`,
    12,
    18
  );
}

async function tickLoop() {
  const canvas = document.getElementById("viewport");
  const ctx = canvas.getContext("2d");
  // apply keys
  if (simRunning) {
    let lx = parseFloat(document.getElementById("lx").value);
    let ly = parseFloat(document.getElementById("ly").value);
    let az = parseFloat(document.getElementById("az").value);
    if (keys["w"]) lx = 0.6;
    if (keys["s"]) lx = -0.6;
    if (keys["a"]) az = 0.8;
    if (keys["d"]) az = -0.8;
    if (keys["q"]) ly = 0.5;
    if (keys["e"]) ly = -0.5;
    try {
      await api("/api/sim/cmd", {
        method: "POST",
        body: JSON.stringify({ linear_x: lx, linear_y: ly, angular_z: az }),
      });
      const st = await api("/api/sim/state");
      drawRobot(ctx, st, canvas.width, canvas.height);
      document.getElementById("t-cmd").textContent =
        `lx=${lx.toFixed(2)} ly=${ly.toFixed(2)} az=${az.toFixed(2)}`;
      document.getElementById("t-odom").textContent =
        `x=${(st.x || 0).toFixed(2)} y=${(st.y || 0).toFixed(2)} θ=${(st.theta || 0).toFixed(2)}`;
      document.getElementById("t-scan").textContent =
        st.lidar ? `${st.lidar.length} rays` : "—";
      document.getElementById("sim-meta").textContent =
        (st.mode || "native") + (st.message ? " · " + st.message : "");
      const status = await api("/api/sim/status");
      document.getElementById("reload-badge").textContent =
        "reloads: " + (status.reload_count || 0);
      if (status.logs && status.logs.length) {
        // append only new-ish
      }
    } catch (e) {
      /* ignore tick errors when stopped */
    }
  } else {
    drawRobot(ctx, { x: 0, y: 0, theta: 0, kind: "diff_drive_2w", lidar: [] }, canvas.width, canvas.height);
  }
  requestAnimationFrame(() => setTimeout(tickLoop, 50));
}

async function loadRos2Versions() {
  const data = await api("/api/ros2/versions");
  ros2Versions = data.versions || [];
  const sel = document.getElementById("ros2-version");
  sel.innerHTML = "";
  const current = data.selected?.id || "humble";
  ros2Versions.forEach((v) => {
    const o = document.createElement("option");
    o.value = v.id;
    o.textContent = `${v.id} — ${v.name} (${v.status})`;
    if (v.id === current) o.selected = true;
    sel.appendChild(o);
  });
}

async function refreshBundleUi() {
  const pkgs = await api("/api/packages");
  const list = document.getElementById("bundle-pkg-list");
  list.innerHTML = "";
  pkgs.forEach((p) => {
    const lab = document.createElement("label");
    lab.innerHTML = `<input type="checkbox" value="${p.name}" checked /> <span><b>${p.name}</b><br/><span class="muted">${p.files} files</span></span>`;
    list.appendChild(lab);
  });
  const bundles = await api("/api/packages/bundles");
  const bl = document.getElementById("bundle-list");
  bl.innerHTML = "";
  bundles.slice(0, 12).forEach((b) => {
    const d = document.createElement("div");
    d.className = "item";
    d.textContent = `${b.filename} (${Math.round(b.size_bytes / 1024)} KB)`;
    d.title = "Download " + b.filename;
    d.onclick = () => {
      window.open("/api/packages/bundles/" + encodeURIComponent(b.filename), "_blank");
    };
    bl.appendChild(d);
  });
}

async function refreshMeshUi() {
  const presets = await api("/api/models/presets");
  const ps = document.getElementById("mesh-preset");
  if (!ps.options.length) {
    presets.forEach((p) => {
      const o = document.createElement("option");
      o.value = p.id;
      o.textContent = `${p.id} — ${p.description}`;
      ps.appendChild(o);
    });
  }
  const models = await api("/api/models");
  const ml = document.getElementById("mesh-list");
  ml.innerHTML = "";
  models.forEach((m) => {
    const d = document.createElement("div");
    d.className = "item" + (selectedMeshId === m.id ? " on" : "");
    d.textContent = m.id + (m.meta?.preset ? ` (${m.meta.preset})` : "");
    d.onclick = () => {
      selectedMeshId = m.id;
      refreshMeshUi();
    };
    ml.appendChild(d);
  });
}

function wireUi() {
  document.querySelectorAll(".act").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll(".act").forEach((b) => b.classList.remove("on"));
      btn.classList.add("on");
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("on"));
      document.getElementById("panel-" + btn.dataset.panel).classList.add("on");
      if (btn.dataset.panel === "package") refreshBundleUi().catch((e) => log(e.message));
      if (btn.dataset.panel === "models") refreshMeshUi().catch((e) => log(e.message));
    };
  });

  document.getElementById("ros2-version").onchange = async (e) => {
    const distro = e.target.value;
    try {
      const r = await api("/api/ros2/version", {
        method: "POST",
        body: JSON.stringify({ distro }),
      });
      log("ROS2 target → " + r.selected.id + " (" + r.selected.docker_image + ")");
    } catch (err) {
      log("ros2 version error: " + err.message);
    }
  };

  document.getElementById("btn-bundle").onclick = async () => {
    const boxes = [...document.querySelectorAll("#bundle-pkg-list input:checked")];
    const packages = boxes.map((b) => b.value);
    const distro = document.getElementById("ros2-version").value;
    log("bundling " + packages.join(", ") + " for " + distro + "…");
    try {
      const r = await api("/api/packages/bundle", {
        method: "POST",
        body: JSON.stringify({ packages, distro }),
      });
      log("bundle ok: " + r.filename + " (" + r.size_bytes + " bytes)");
      await refreshBundleUi();
    } catch (e) {
      log("bundle error: " + e.message);
    }
  };

  document.getElementById("btn-mesh-create").onclick = async () => {
    const preset = document.getElementById("mesh-preset").value;
    const name = document.getElementById("mesh-name").value || null;
    try {
      const r = await api("/api/models", {
        method: "POST",
        body: JSON.stringify({ preset, name }),
      });
      selectedMeshId = r.id;
      log("mesh created: " + r.id + " (" + r.bytes + " bytes OBJ)");
      await refreshMeshUi();
    } catch (e) {
      log("mesh error: " + e.message);
    }
  };

  document.getElementById("btn-mesh-attach").onclick = async () => {
    if (!selectedMeshId) {
      log("select a mesh in library first");
      return;
    }
    const packageName = activePkg?.name;
    if (!packageName) {
      log("open a demo package first");
      return;
    }
    try {
      const r = await api("/api/models/attach", {
        method: "POST",
        body: JSON.stringify({ package: packageName, model_id: selectedMeshId }),
      });
      log("attached " + selectedMeshId + " → " + packageName + " urdf");
      // refresh file tree
      activePkg = await api("/api/workspace");
      renderTree(activePkg.files);
      if (r.urdf) {
        const rel = "urdf/robot.urdf";
        try {
          await openPath(rel);
        } catch (_) {}
      }
    } catch (e) {
      log("attach error: " + e.message);
    }
  };

  document.getElementById("btn-run").onclick = async () => {
    const demo = activePkg?.name || demos[0]?.name || "diff_drive_2w";
    await api("/api/sim/start", {
      method: "POST",
      body: JSON.stringify({ demo }),
    });
    simRunning = true;
    trail = [];
    setPill("running", "run");
    log("▶ sim " + demo);
  };
  document.getElementById("btn-stop").onclick = async () => {
    await api("/api/sim/stop", { method: "POST" });
    simRunning = false;
    setPill("idle", "idle");
    log("■ stopped");
  };
  document.getElementById("btn-hot").onclick = async () => {
    hotOn = !hotOn;
    document.getElementById("btn-hot").classList.toggle("on", hotOn);
    await api("/api/hot-reload", {
      method: "POST",
      body: JSON.stringify({ enabled: hotOn }),
    });
    log("hot-reload " + (hotOn ? "on" : "off"));
  };
  document.getElementById("btn-zero").onclick = () => {
    document.getElementById("lx").value = 0;
    document.getElementById("ly").value = 0;
    document.getElementById("az").value = 0;
  };
  const refreshDocker = async () => {
    const st = await api("/api/docker/show");
    document.getElementById("docker-info").textContent = JSON.stringify(st, null, 2);
  };
  document.getElementById("btn-docker").onclick = refreshDocker;
  document.getElementById("btn-docker-refresh").onclick = refreshDocker;
  document.getElementById("btn-docker-start").onclick = async () => {
    log("starting docker runtime…");
    try {
      const r = await api("/api/docker/start", { method: "POST" });
      log(JSON.stringify(r).slice(0, 400));
      setPill(r.ok ? "docker" : "idle", r.ok ? "docker" : "idle");
      await refreshDocker();
    } catch (e) {
      log("docker start: " + e.message);
    }
  };

  const canvas = document.getElementById("viewport");
  canvas.addEventListener("keydown", (e) => {
    keys[e.key.toLowerCase()] = true;
  });
  canvas.addEventListener("keyup", (e) => {
    keys[e.key.toLowerCase()] = false;
  });
  window.addEventListener("blur", () => {
    keys = {};
  });
}

async function boot() {
  wireUi();
  await setupMonaco();
  await loadRos2Versions();
  demos = await api("/api/demos");
  renderDemos();
  log("Lappa IDE ready — " + demos.length + " demos");
  log("Ctrl+S saves file and triggers hot-reload");
  log("Pick ROS2 version in title bar · Package panel bundles · Models panel for OBJ");
  if (demos[0]) await loadDemo(demos[0].name);
  tickLoop();
  try {
    const d = await api("/api/docker/status");
    log("docker available=" + d.available + " daemon=" + d.daemon + " ros2=" + (d.ros2_distro || "?"));
  } catch (_) {}
}

boot().catch((e) => {
  console.error(e);
  log("boot error: " + e.message);
});
