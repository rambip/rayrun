export function render({ model, el }) {
  // Get current state
  let status = model.get("status");
  let podId = model.get("pod_id");
  let ipAddress = model.get("ip_address");
  let rayUrl = model.get("ray_url");
  let dashboardUrl = model.get("dashboard_url");
  let elapsedSeconds = model.get("elapsed_seconds");
  let errorMessage = model.get("error_message");
  let selectedGpu = model.get("selected_gpu");
  let idleTimeout = model.get("idle_timeout_minutes");

  // Create container
  const container = document.createElement("div");
  container.className = "rayrun-widget";

  // Status header
  const header = document.createElement("div");
  header.className = "rayrun-header";
  
  const title = document.createElement("h3");
  title.textContent = "RayRun Compute";
  header.appendChild(title);
  
  const statusBadge = document.createElement("span");
  statusBadge.className = `rayrun-status rayrun-status-${status}`;
  statusBadge.textContent = status.toUpperCase();
  header.appendChild(statusBadge);
  
  container.appendChild(header);

  // Controls section
  const controls = document.createElement("div");
  controls.className = "rayrun-controls";

  // GPU selection
  if (status === "stopped" || status === "error") {
    const gpuLabel = document.createElement("label");
    gpuLabel.textContent = "Instance Type:";
    controls.appendChild(gpuLabel);

    const gpuSelect = document.createElement("select");
    gpuSelect.className = "rayrun-select";
    
    const gpuOptions = [
      { value: "gpu.a100", label: "NVIDIA A100 80GB" },
      { value: "gpu.h100", label: "NVIDIA H100 80GB" },
      { value: "gpu.rtx4090", label: "NVIDIA RTX 4090" },
      { value: "gpu.a6000", label: "NVIDIA RTX A6000" },
    ];
    
    gpuOptions.forEach(opt => {
      const option = document.createElement("option");
      option.value = opt.value;
      option.textContent = opt.label;
      option.selected = opt.value === selectedGpu;
      gpuSelect.appendChild(option);
    });
    
    gpuSelect.addEventListener("change", (e) => {
      model.set("selected_gpu", e.target.value);
      model.save_changes();
    });
    
    controls.appendChild(gpuSelect);

    // Idle timeout
    const timeoutLabel = document.createElement("label");
    timeoutLabel.textContent = "Idle Timeout (min):";
    controls.appendChild(timeoutLabel);

    const timeoutInput = document.createElement("input");
    timeoutInput.type = "number";
    timeoutInput.className = "rayrun-input";
    timeoutInput.value = idleTimeout;
    timeoutInput.min = 5;
    timeoutInput.max = 120;
    timeoutInput.addEventListener("change", (e) => {
      model.set("idle_timeout_minutes", parseInt(e.target.value));
      model.save_changes();
    });
    controls.appendChild(timeoutInput);
  }

  // Start/Stop button
  const actionButton = document.createElement("button");
  actionButton.className = "rayrun-button";
  
  if (status === "stopped" || status === "error") {
    actionButton.textContent = "Start Compute";
    actionButton.className += " rayrun-button-start";
    actionButton.onclick = () => {
      model.send({ action: "start" });
    };
  } else if (status === "starting") {
    actionButton.textContent = "Starting...";
    actionButton.disabled = true;
  } else if (status === "stopping") {
    actionButton.textContent = "Stopping...";
    actionButton.disabled = true;
  } else {
    actionButton.textContent = "Stop Compute";
    actionButton.className += " rayrun-button-stop";
    actionButton.onclick = () => {
      model.send({ action: "stop" });
    };
  }
  
  controls.appendChild(actionButton);
  container.appendChild(controls);

  // Info section
  if (status === "running") {
    const infoSection = document.createElement("div");
    infoSection.className = "rayrun-info";

    // Elapsed time
    const timeDiv = document.createElement("div");
    timeDiv.className = "rayrun-info-row";
    const hours = Math.floor(elapsedSeconds / 3600);
    const minutes = Math.floor((elapsedSeconds % 3600) / 60);
    const seconds = Math.floor(elapsedSeconds % 60);
    timeDiv.innerHTML = `<span class="rayrun-label">Elapsed:</span> ${hours}h ${minutes}m ${seconds}s`;
    infoSection.appendChild(timeDiv);

    // Pod ID
    if (podId) {
      const podDiv = document.createElement("div");
      podDiv.className = "rayrun-info-row";
      podDiv.innerHTML = `<span class="rayrun-label">Pod ID:</span> ${podId}`;
      infoSection.appendChild(podDiv);
    }

    // IP Address
    if (ipAddress) {
      const ipDiv = document.createElement("div");
      ipDiv.className = "rayrun-info-row";
      ipDiv.innerHTML = `<span class="rayrun-label">IP:</span> ${ipAddress}`;
      infoSection.appendChild(ipDiv);
    }

    // Ray URL
    if (rayUrl) {
      const rayDiv = document.createElement("div");
      rayDiv.className = "rayrun-info-row";
      rayDiv.innerHTML = `<span class="rayrun-label">Ray Client:</span> <code>${rayUrl}</code>`;
      infoSection.appendChild(rayDiv);
    }

    // Dashboard URL
    if (dashboardUrl) {
      const dashDiv = document.createElement("div");
      dashDiv.className = "rayrun-info-row";
      const dashLink = document.createElement("a");
      dashLink.href = dashboardUrl;
      dashLink.target = "_blank";
      dashLink.textContent = "Open Ray Dashboard";
      dashDiv.innerHTML = `<span class="rayrun-label">Dashboard:</span> `;
      dashDiv.appendChild(dashLink);
      infoSection.appendChild(dashDiv);
    }

    container.appendChild(infoSection);
  }

  // Error message
  if (errorMessage) {
    const errorDiv = document.createElement("div");
    errorDiv.className = "rayrun-error";
    errorDiv.textContent = errorMessage;
    container.appendChild(errorDiv);
  }

  // Update elapsed time
  if (status === "running") {
    const updateElapsed = () => {
      elapsedSeconds = model.get("elapsed_seconds");
      const timeDiv = container.querySelector(".rayrun-info-row");
      if (timeDiv && timeDiv.innerHTML.includes("Elapsed")) {
        const hours = Math.floor(elapsedSeconds / 3600);
        const minutes = Math.floor((elapsedSeconds % 3600) / 60);
        const seconds = Math.floor(elapsedSeconds % 60);
        timeDiv.innerHTML = `<span class="rayrun-label">Elapsed:</span> ${hours}h ${minutes}m ${seconds}s`;
      }
      if (model.get("status") === "running") {
        requestAnimationFrame(updateElapsed);
      }
    };
    updateElapsed();
  }

  el.appendChild(container);

  // Listen for model changes
  model.on("change:status", () => {
    render({ model, el });
  });
  model.on("change:elapsed_seconds", () => {
    // Handled in updateElapsed
  });
}
