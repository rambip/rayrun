# RayRun

A Jupyter notebook widget for on-demand GPU/CPU compute using RunPod and Ray.

## Overview

RayRun provides a simple way to spin up cloud GPU/CPU instances directly from your Jupyter notebook, run distributed computations with Ray, and automatically shut down when idle to minimize costs.

### Features

- **One-click compute**: Start GPU/CPU instances from within your notebook
- **Pre-configured environment**: PyTorch, data science tools, and Ray pre-installed
- **Auto-shutdown**: Automatically stops when idle to save money
- **Ray integration**: Direct connection to Ray cluster for distributed computing
- **Cost-effective**: Uses RunPod's community cloud by default

## Installation

```bash
pip install rayrun
```

## Quick Start

### 1. Set up your RunPod API key

```bash
export RUNPOD_API_KEY="your-api-key-here"
```

Or create a `.env` file in your project directory:
```
RUNPOD_API_KEY=your-api-key-here
```

### 2. Use in Jupyter

```python
from rayrun import RayRun

# Create the widget
compute = RayRun(idle_timeout_minutes=30)
compute
```

### 3. Start compute

Click the **"Start Compute"** button in the widget. The widget will:
1. Create a RunPod instance with Ray pre-installed
2. Wait for the instance to be ready
3. Display connection information (IP, Ray URL, Dashboard URL)

### 4. Connect to Ray

```python
# Now you can use Ray!
import ray

ray.init("<url here>")

@ray.remote
def my_function(x):
    return x * x

# Run distributed computation
futures = [my_function.remote(i) for i in range(10)]
results = ray.get(futures)
print(results)
```

### 5. Stop compute

Click **"Stop Compute"** in the widget, or the instance will automatically shut down after the idle timeout (default: 30 minutes).

## Pre-installed Packages

The Docker image includes:

- **Ray**: Distributed computing framework
- **PyTorch**: torch, torchaudio, torchvision
- **Data Science**: polars, numpy, scipy, scikit-learn
- **Visualization**: matplotlib, altair
- **System**: ffmpeg


## Future Work

The following features are currently outside the scope of this project:

- **Custom Docker Images**: Support for user-specified Docker images with custom dependencies
- **TLS/SSL for Ray Connections**: Encrypted Ray client connections via TLS
- **Cost Tracking UI**: Real-time cost display and accumulated spend in the widget
- **Automatic Retry Logic**: Retry on transient failures during pod creation or Ray connection
- **Partial Failure Recovery**: Handling cases where VM is up but Ray fails to start
- **Pre-shutdown Warnings**: Notification before automatic idle shutdown occurs
- **VM Logs Display**: Expandable section in widget to view container logs
- **Resource Usage Monitoring**: Display CPU/GPU/memory utilization in widget
- **Estimated Cost Display**: Show projected hourly/daily costs in widget
- **Restart Button**: Quick restart functionality without full stop/start cycle
- **Multi-GPU Support**: Configuration for pods with multiple GPUs
- **Custom Data Center Selection**: Fine-grained control over pod location
- **Network Volume Management**: Create and attach persistent network volumes
- **Spot Instance Fallback**: Automatic fallback to on-demand if spot unavailable

## License

MIT License - see LICENSE file for details.
