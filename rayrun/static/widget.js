import { render as uRender, html } from "https://esm.run/uhtml";

function formatElapsed(secs) {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  return `${h}h ${m}m ${s}s`;
}

function view(model) {
  const status = model.get("status");
  const podId = model.get("pod_id");
  const ipAddress = model.get("ip_address");
  const rayUrl = model.get("ray_url");
  const dashboardUrl = model.get("dashboard_url");
  const elapsedSeconds = model.get("elapsed_seconds");
  const errorMessage = model.get("error_message");
  const selectedTier = model.get("selected_tier");
  const idleTimeout = model.get("idle_timeout_minutes");

  const onStart = () => {
    model.set("status", "starting");
    model.save_changes();
    model.send({ action: "start" });
  };
  const onStop = () => {
    model.set("status", "stopping");
    model.save_changes();
    model.send({ action: "stop" });
  };

  const onTierChange = (e) => {
    model.set("selected_tier", e.target.value);
    model.save_changes();
  };
  const onTimeoutChange = (e) => {
    const v = parseInt(e.target.value, 10);
    model.set("idle_timeout_minutes", isNaN(v) ? idleTimeout : v);
    model.save_changes();
  };

  const tierOptions = [
    { value: "cheap", label: "Cheap (RTX 3070-5090, V100, T4, A30)" },
    { value: "medium", label: "Medium (RTX A5000/A6000, L40, A40)" },
    { value: "costly", label: "Costly (A100, H100, H200, B200, MI300X)" },
  ];

  return html`
    <div class="rayrun-widget">
      <div class="rayrun-header">
        <h3>RayRun Compute</h3>
        <span class=${`rayrun-status rayrun-status-${status}`}
          >${status.toUpperCase()}</span
        >
      </div>

      <div class="rayrun-controls">
        ${status === "stopped" || status === "error"
          ? html`
              <label>GPU Tier:</label>
              <select class="rayrun-select" onchange=${onTierChange}>
                ${tierOptions.map(
                  (opt) =>
                    html`<option
                      value=${opt.value}
                      .selected=${opt.value === selectedTier}
                    >
                      ${opt.label}
                    </option>`,
                )}
              </select>

              <label>Idle Timeout (min):</label>
              <input
                type="number"
                class="rayrun-input"
                value=${idleTimeout}
                min=${5}
                max=${120}
                onchange=${onTimeoutChange}
              />
            `
          : null}
        ${status === "fetching"
          ? html`<div class="rayrun-info-row"><span class="rayrun-label">Status:</span> Checking for existing pods...</div>`
          : null}
        ${status === "fetching"
          ? html`<button class="rayrun-button" disabled>Fetching pods...</button>`
          : status === "stopped" || status === "error"
            ? html`<button
                class="rayrun-button rayrun-button-start"
                onclick=${onStart}
              >
                Start Compute
              </button>`
            : status === "starting"
              ? html`<button class="rayrun-button" disabled>Starting...</button>`
              : status === "stopping"
                ? html`<button class="rayrun-button" disabled>
                    Stopping...
                  </button>`
                : html`<button
                    class="rayrun-button rayrun-button-stop"
                    onclick=${onStop}
                  >
                    Stop Compute
                  </button>`}
      </div>

      ${status === "running"
        ? html`
            <div class="rayrun-info">
              <div class="rayrun-info-row">
                <span class="rayrun-label">Elapsed:</span> ${formatElapsed(
                  elapsedSeconds,
                )}
              </div>
              ${podId
                ? html`<div class="rayrun-info-row">
                    <span class="rayrun-label">Pod ID:</span> ${podId}
                  </div>`
                : null}
              ${ipAddress
                ? html`<div class="rayrun-info-row">
                    <span class="rayrun-label">IP:</span> ${ipAddress}
                  </div>`
                : null}
              ${rayUrl
                ? html`<div class="rayrun-info-row">
                    <span class="rayrun-label">Ray Client:</span>
                    <code>${rayUrl}</code>
                  </div>`
                : null}
              ${dashboardUrl
                ? html`<div class="rayrun-info-row">
                    <span class="rayrun-label">Dashboard:</span>
                    <a href=${dashboardUrl} target="_blank"
                      >Open Ray Dashboard</a
                    >
                  </div>`
                : null}
            </div>
          `
        : null}
      ${errorMessage
        ? html`<div class="rayrun-error">${errorMessage}</div>`
        : null}
    </div>
  `;
}

function render({ model, el }) {
  // Install listeners once to avoid duplication
  if (!el.__rayrunInit) {
    const onChange = () => uRender(el, view(model));
    el.__onChange = onChange;
    model.on("change:status", onChange);
    model.on("change:elapsed_seconds", onChange);
    model.on("change:error_message", onChange);
    model.on("change:selected_tier", onChange);
    el.__rayrunInit = true;
  }

  uRender(el, view(model));
}

export default { render };
