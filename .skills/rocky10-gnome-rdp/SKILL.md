---
name: rocky10-gnome-rdp
description: >
  Enable GNOME native RDP on a Rocky Linux 10 KVM VM when you only have SSH
  access and the virt-manager console mouse is broken. Use this skill whenever
  the task involves setting up RDP on a Rocky 10 / RHEL 10 VM, fixing mouse
  pointer drift in virt-manager over RDP, or enabling gnome-remote-desktop
  headlessly. Triggers on: "set up RDP on Rocky", "mouse broken in virt-manager",
  "enable remote desktop on Rocky 10", "gnome-remote-desktop from SSH".
---

# Rocky 10 — GNOME RDP Setup via SSH

## Context

Rocky 10 uses GNOME's native RDP via `gnome-remote-desktop`. No xrdp needed.
Setup requires a live Wayland session. If the virt-manager console mouse is
broken, fix the display resolution first — that unblocks GUI access.

---

## Step 1 — Fix Mouse in virt-manager (if needed)

**Problem:** virt-manager console pointer drifts at boundaries due to resolution
mismatch between the VM framebuffer and the console window.

**Fix:** Write `monitors.xml` as the VM user over SSH, then restart the GNOME
session.

```bash
# SSH into the VM as the regular user (not root)
ssh user@<vm-ip>

cat > ~/.config/monitors.xml << 'EOF'
<monitors version="2">
  <configuration>
    <logicalmonitor>
      <x>0</x>
      <y>0</y>
      <scale>1</scale>
      <primary>yes</primary>
      <monitor>
        <monitorspec>
          <connector>Virtual-1</connector>
          <vendor>unknown</vendor>
          <product>unknown</product>
          <serial>unknown</serial>
        </monitorspec>
        <mode>
          <width>1280</width>
          <height>720</height>
          <rate>60.000</rate>
        </mode>
      </monitor>
    </logicalmonitor>
  </configuration>
</monitors>
EOF

pkill -u user gnome-session
```

GNOME restarts at 1280x720. Mouse now works in virt-manager.

---

## Step 2 — Enable GNOME Remote Desktop

With the mouse working, use the VM GUI:

**Settings → System → Remote Desktop → enable Remote Login**

GNOME auto-generates the TLS certificate on enable. Set a password in the same panel.

---

## Step 3 — Open Firewall (as root)

```bash
sudo firewall-cmd --add-port=3389/tcp --permanent
sudo firewall-cmd --reload
```

Port should already be open on a default Rocky 10 install — command is idempotent.

---

## Step 4 — Verify

```bash
ss -tulpn | grep 3389
```

Expected: a LISTEN entry on 0.0.0.0:3389.

---

## Connect

```
Protocol : RDP
Host     : <vm-ip>
Port     : 3389
User     : <vm-username>
```

---

## Dead Ends — Do Not Use

### gsettings keys that do not exist in Rocky 10

```bash
# BROKEN
gsettings set org.gnome.desktop.remote-desktop.rdp prompt-enabled false
gsettings set org.gnome.desktop.remote-desktop.rdp authentication-methods "['password']"
gsettings set org.gnome.desktop.remote-desktop.rdp password 'yourpassword'
```

### grdctl generate-certificate

```bash
# BROKEN — not a valid subcommand on this version
grdctl rdp generate-certificate
```

### systemctl --user without dbus env

Fails with `DBUS_SESSION_BUS_ADDRESS not defined` when run over SSH without a
live graphical session attached. The GUI toggle in Step 2 is more reliable.

If you must use CLI, export both vars first:

```bash
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
```
<!-- consolidation:see-also:start -->
## See Also
[[openspec-workflow]]  [[gist-retriever]]  [[stratified-quota-sampling]]
<!-- consolidation:see-also:end -->
