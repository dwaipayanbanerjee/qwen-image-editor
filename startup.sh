#!/bin/bash

echo "=== RunPod Workspace Setup ==="

# Create workspace directories
mkdir -p /workspace/.ssh
mkdir -p /workspace/.npm-global
mkdir -p /workspace/.claude
mkdir -p /workspace/repos

# Symlink SSH (for git/gh operations)
if [ ! -L ~/.ssh ]; then
    rm -rf ~/.ssh
    ln -sf /workspace/.ssh ~/.ssh
    chmod 700 ~/.ssh
fi

# Symlink Claude CLI config
if [ ! -L ~/.claude ]; then
    rm -rf ~/.claude
    ln -sf /workspace/.claude ~/.claude
fi

# Configure npm global path
npm config set prefix '/workspace/.npm-global'
export PATH="/workspace/.npm-global/bin:$PATH"
echo 'export PATH="/workspace/.npm-global/bin:$PATH"' >> ~/.bashrc

# Symlink git config if it exists
if [ -f /workspace/.gitconfig ]; then
    ln -sf /workspace/.gitconfig ~/.gitconfig
fi

# Source RunPod environment variables (fixes SSH session env var bug)
if [ -f /etc/rp_environment ]; then
    source /etc/rp_environment
    # Also add to bashrc so it's available in future sessions
    echo 'source /etc/rp_environment' >> ~/.bashrc
fi

# Set git SSH command to use workspace key
export GIT_SSH_COMMAND="ssh -i /workspace/.ssh/github_ed25519 -o StrictHostKeyChecking=no"
echo 'export GIT_SSH_COMMAND="ssh -i /workspace/.ssh/github_ed25519 -o StrictHostKeyChecking=no"' >> ~/.bashrc

echo "=== Workspace setup complete ==="
echo "SSH config: ~/.ssh -> /workspace/.ssh"
echo "npm global: /workspace/.npm-global"
echo "Claude config: ~/.claude -> /workspace/.claude"
echo "Git config: ~/.gitconfig -> /workspace/.gitconfig"