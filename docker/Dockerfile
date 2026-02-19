FROM rayproject/ray:2.54.0-py313-gpu

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    torch \
    torchaudio \
    torchvision \
    polars \
    numpy \
    scipy \
    scikit-learn \
    matplotlib \
    altair \
    requests

# Copy shutdown monitor and startup script
COPY shutdown_monitor.py /app/shutdown_monitor.py
COPY start.sh /app/start.sh
RUN chmod +x /app/shutdown_monitor.py /app/start.sh

# Expose ports
EXPOSE 10001 8265 6379

# Set working directory
WORKDIR /workspace

# Entry point
ENTRYPOINT ["/app/start.sh"]
