# Debian + QEMU sandbox for LLM-agent swarm (research only, nothing was installed or run)

Legend: [V] = verified from a fetched source or read-only local check; [U] = uncertain / from general knowledge or weak source; [E] = my estimate.

## TL;DR
- **Pick: Debian 13 (trixie) `genericcloud` amd64 qcow2** (325 MB on cloud.debian.org [V]) as the guest, driven by a NoCloud cloud-init seed, run as a throwaway qcow2 overlay on a read-only base. Use `nocloud` only if you want a passwordless root prompt without cloud-init.
- **KVM in WSL2: very likely works on this host.** Read-only check here: `/dev/kvm` exists and `/proc/cpuinfo` shows `vmx` [V, local]. Nested virt is a `.wslconfig` `nestedVirtualization` setting on the Windows side [V, search results; default conflicting]. I did not test that KVM actually boots a guest.
- **TCG (no KVM) is roughly 10x slower** for x86 guests (range ~5-50x; sources are old or vendor blogs) [U]. Fine for tiny shell tasks, painful for a 24-VM swarm.
- **Tracing recommendation (two layers):** (1) in-guest, low overhead, KVM-compatible: auditd `execve` rules plus a bpftrace/Tetragon exec+connect+openat feed, shipped out via virtio-serial; (2) host-side QEMU TCG plugin `execlog`/`insn`/`bb` or PANDA record/replay only on a *sampled/replayed* subset, since they require TCG and are heavy.
- **Best fingerprint signals:** the ordered sequence of (execve path+argv, file open/write paths, connect destinations), plus a hash of the final filesystem diff of the overlay. Avoid hashing raw instruction traces (non-deterministic: timers, ASLR, interrupts).
- **Containment:** `-netdev user,restrict=on` (or `-nic none`) plus `-snapshot`/overlays; talk to the agent harness over virtio-serial/unix socket, not the network.
- **Footprint [E]:** ~512 MB-1 GB RAM, 1 vCPU, overlay of tens of MB per VM; 24 parallel VMs is about 12-24 GB RAM, which fits in 47 GB but competes with vLLM host RAM.
- **Firecracker/gVisor/Docker:** Firecracker needs working KVM (same fragility as QEMU+KVM, little gain). gVisor systrap needs no KVM but gives syscall-level isolation of a container, not a full OS. Docker is the fallback if KVM breaks.

## 1. Distro options

| Option | Size / boot | cloud-init | Packages | Snapshot suitability | Verdict |
|---|---|---|---|---|---|
| Debian 13 `genericcloud` qcow2 | 325 MB [V] | yes (cloud-init) [V] | full Debian apt | excellent: qcow2, read-only base + overlays | **Pick** |
| Debian 13 `generic` qcow2 | 419 MB [V] | yes; more hardware drivers | full | same | use if genericcloud fails to boot on a given machine type [V: Debian says to use generic if genericcloud does not work] |
| Debian 13 `nocloud` qcow2 | 389 MB [V] | no cloud-init; boots to root prompt, aimed at local QEMU [V] | full | same | simplest, but you must inject config another way (serial or 9p) |
| Debian netinst / minimal install | ~hundreds MB ISO [U] | no (preseed instead) | full | needs an install step per base | worse: install time, no benefit |
| DietPi | small SBC-oriented images [U] | no (its own dietpi.txt first-boot) | Debian-based, curated | OK | more SBC-focused, x86 VM images exist [U]; extra layer, not needed |
| antiX | Debian-based, live-ISO oriented, systemd-free [U] | no | Debian stable repos | awkward (live ISO) | no |
| Devuan | Debian fork without systemd [U] | not first-class [U] | Debian-like | OK | only if you need no-systemd; fewer images |
| Ubuntu minimal / cloud images | cloud images ~600 MB class [U, not fetched] | yes (native) | apt, larger | excellent | viable alternative; Debian is smaller and the user asked for Debian-based |
| Alpine | ~tens of MB [U] | tiny-cloud / limited | musl, different tooling | excellent | not Debian; skip unless footprint dominates |

Boot time: no verified number for Debian genericcloud. A vendor blog claims 10-30 s for Alpine/Ubuntu under TCG and under a second for hardware-accelerated lightweight guests [U, Microsoft Quicksand]. Expect roughly 5-15 s to login under KVM on a full Debian cloud image [E, unmeasured]; trimming services (disable unattended-upgrades, apt timers, etc.) cuts this.

Snapshot/restore: any qcow2 works with backing-file overlays. Cloud-init re-runs per instance-id, so give each VM a distinct seed `instance-id` or set it to run once on the base.

Sources: https://cloud.debian.org/images/cloud/ (variant descriptions), https://cloud.debian.org/images/cloud/trixie/latest/ (sizes).

## 2. QEMU inside WSL2

**KVM availability**
- Local read-only check on this machine: `/dev/kvm` present; `vmx` found in `/proc/cpuinfo` (48 matching lines, i.e. vCPU threads) [V]. Kernel is 6.6.87.2-microsoft-standard-WSL2, which ships with KVM support.
- Enable (Windows side, `%USERPROFILE%\.wslconfig`): `[wsl2]` then `nestedVirtualization=true`, then `wsl --shutdown`. Sources disagree on whether it is on by default (one says default-on, one says off) [V as conflicting]; since `/dev/kvm` already exists here, it is on.
- Permissions: add your user to the `kvm` group or fix `/dev/kvm` ownership; one guide persists this via a `boot` command in `/etc/wsl.conf` [V, secondary source].
- Gotchas: reports that some Windows/CPU/WSL combos do not expose nested virt even with the flag [V, GitHub issue on Windows 10]; WSL2 is itself a Hyper-V VM so you are double-nested (L0 Windows, L1 WSL2, L2 your guest), which costs some performance and exposes you to nested-virt bugs [U]; custom-kernel `kvm-intel nested=1` route is only for old guides [V]. Also: the nested hypervisor path adds overhead for I/O-heavy guests and for VM exits [U].
- Sources: https://boxofcables.dev/accelerated-kvm-guests-on-wsl-2/ , https://github.com/microsoft/WSL/issues/11216 , the search result set for "WSL2 nested virtualization KVM".

**Performance, KVM vs TCG**
- QEMU maintainer (2018): TCG about 12x slower than KVM on integer workloads like OS install; Linaro: 8x slower for x86-64 Android boot [V, via search, dated]. Microsoft Quicksand claims 10-50x [U]. Use ~10x as a planning number.
- Practical consequence: with TCG, 24 parallel VMs on 24 cores will each run at a fraction of native; shell-command agents are mostly idle, so it can still be workable.

**Alternatives and when to prefer each**
- **Firecracker:** needs read/write KVM access; a source notes it is not well tested under nested virtualization [V, search]. No gain over QEMU+KVM here unless you need very fast microVM starts; prefer only if KVM is stable.
- **QEMU `-machine microvm`:** no PCI or ACPI, aimed at fast boot/small footprint for short-lived guests [V, QEMU commit docs via search]. Needs a microvm-capable guest kernel (virtio-mmio); Debian generic cloud kernels may not suit it [U]. Third-party "sub-300 ms" claims are anecdotal [U].
- **gVisor:** systrap platform (default since mid-2023) needs no KVM and is recommended inside VMs / without virtualization support; KVM platform is slower when nested [V]. It isolates a container's syscalls, so you lose "full OS in a VM" semantics. I did not confirm gVisor on WSL2 specifically [U].
- **Docker in WSL2:** easiest and lightest; weakest isolation (shared kernel). Prefer for a fast prototype or if KVM fails. Combine with gVisor (`runsc`) for stronger syscall isolation.
- **Decision rule:** QEMU+KVM if `/dev/kvm` works (strong isolation, qcow2 snapshots, full-system tracing hooks); gVisor/Docker if it does not; QEMU TCG if you need TCG plugin tracing.

## 3. Observability: capturing what actually executes

**Host-side (outside the guest, tamper-resistant)**
- **TCG plugins** (`-plugin ./libX.so,arg=val -d plugin`): enabled by default in any QEMU build with TCG [V]. Examples [V]: `execlog` (executed instructions with memory accesses and optional register changes; needs Capstone for disassembly; options `ifilter`, `afilter`, `reg`, `rdisas`), `insn` (instruction counts per vCPU), `bb` (basic-block execution counts), `hotblocks`, `mem`, `howvec`, `stoptrigger`. `syscall` plugin is user-mode only [V], so it is no use for a full-system guest.
  - Plugins instrument translated code, so they only work under TCG, not under KVM (by design of TCG; not stated on the page I fetched [U]).
  - Output goes through the QEMU log, not stdout/stderr [V].
  - Caveats [V]: instruction callbacks fire before the instruction runs and it may fault; memory callbacks fire only after a successful access; translation does not imply execution.
  - Fidelity: highest (every instruction); overhead: TCG slowdown plus per-instruction callbacks (large; no number found). Output volume is huge and it sees *instructions*, not "the agent ran `rm -rf`", so you need guest-OS semantic reconstruction to be useful.
- **`-d in_asm,exec`** with `-D file`: `-d` logs items, `-D` sets the log file [V]. `in_asm`/`exec` item meanings were not in the page excerpt I got; `qemu-system-x86_64 -d help` lists them [V that this command is the documented way]. Same TCG-only, high-volume story; plugins are the more maintained way.
- **PANDA** (https://github.com/panda-re/panda): QEMU-based record and replay; recordings are compact (page cites a 9-billion-instruction FreeBSD boot in a few hundred MB), record/replay supported for x86, x86_64, ARM guests [V]. Recordings only replay between builds with the same address length [V]. It enables deterministic after-the-fact analysis of the same execution with arbitrary plugins, which is the best fit for "inspect later what really ran". Whether it needs TCG: page silent; PANDA is TCG-based [U]. Maintenance looks active (dev branch, CI) [V].
- **PyREBox:** Python scriptable QEMU-based RE sandbox; I did not research it in this pass, and I believe it is largely unmaintained [U]. Not recommended over PANDA.

**In-guest (works with KVM, much cheaper)**
- **auditd:** `execve`/`connect`/`openat` rules. Moderate overhead [U, no numbers found]; simple, produces records with full argv; root in the guest can disable it, so lock rules with `-e 2` [U, known auditd feature].
- **strace:** per-process, high overhead (ptrace), good for a single traced agent shell, easy to evade or break with nested tools [U].
- **eBPF:** bpftrace for ad-hoc scripts (`tracepoint:syscalls:sys_enter_execve`); **Tetragon** reports ~1.68% overhead tracing all process execs during a kernel compile (2.46% with JSON export) [V, vendor benchmark, worst-case framing]; **Falco** is rule/alert-oriented with a userspace engine, anecdotally ~2x Tetragon's CPU [U, single anecdote]. Need a guest kernel with BTF/eBPF; Debian 13 kernel should have it [U].
- Trade-off summary: in-guest tools are cheap and semantic (they see argv, paths) but live in the thing being watched (a root agent could tamper). Host-side TCG/PANDA is tamper-resistant but expensive and low-level.

**What to hash/fingerprint for "what the agent actually did"**
1. Ordered list of normalized `execve` events: (resolved binary path, argv with volatile tokens like PIDs/tmp names masked). Best single signal; directly comparable to the LLM's stated command.
2. Set/sequence of file-write and file-delete paths (from audit/eBPF), and a content hash of the overlay's changed files (diff of overlay vs base, e.g. via `qemu-img compare` or mounting the overlay read-only [U]).
3. Network attempts: (dest ip:port) from `connect`; under `restrict=on` these should all fail but the attempts are the signal.
4. Exit codes and stdout hash per command.
- Avoid: raw instruction traces, timestamps, PIDs, ASLR addresses (non-deterministic). From TCG, use coarse aggregates instead: `bb` or `hotblocks` top-N block hash, or `insn` count, as an anomaly feature rather than an identity hash. [E]
- For the swarm-median comparison: embed (execve sequence, file-write path set) into a bag-of-tokens / n-gram vector, then compute distance to the per-task median. [E]

## 4. Containment for agent populations

- **Network:** `-netdev user,id=n0,restrict=on` plus `-device virtio-net-pci,netdev=n0`: with restrict on, "the guest will be isolated, i.e. it will not be able to contact the host" (also blocks outside access) [V]. Or `-nic none`: "no network devices should be configured", overriding the default user-mode NIC [V]. Note the default with no net options is a user NIC [V], so always set one explicitly. Harness communication: use a virtio-serial chardev on a unix socket instead of a network [U on exact cmdline below].
- **Disk:** `-snapshot` writes to temp files and never writes back the image [V]; note it is incompatible with `-blockdev` (use `qemu-img` overlays or the `snapshot` property on `-drive`) [V]. Preferred: a per-VM qcow2 overlay with a shared read-only backing file (`qemu-img create -f qcow2 -b base.qcow2 -F qcow2 vmN.qcow2`) which you keep for forensic diffing, then delete.
- **savevm/loadvm:** monitor commands `savevm tag` / `loadvm tag` store VM state inside a qcow2; useful to checkpoint after boot for sub-second restore [U, not in fetched pages]. Not compatible with all device configs (e.g. some passthrough); needs a qcow2 disk [U].
- **Resource limits:** `-m`, `-smp` bound the guest; for host-side bounds run each QEMU under a systemd scope or cgroup (`systemd-run --scope -p MemoryMax=... -p CPUQuota=...`) [U, standard systemd]; `-cpu` choices for determinism under TCG; `-icount` enables a virtual instruction counter for deterministic time under TCG [V that the option exists].
- **Config hygiene:** `-no-user-config` stops QEMU loading user config files from sysconfdir [V]. Also `-nodefaults` and `-display none` [U, standard].
- **Swarm of N VMs:** memory per VM is mainly the `-m` value (pages are touched lazily; idle Debian ~150-250 MB resident [E]). Add ~50-100 MB QEMU overhead [E]. KSM can dedupe identical guest pages across VMs [U, needs host config; availability in WSL2 kernel unchecked]. Overlays start tiny (MB) and grow with writes; base image shared (one 325 MB compressed file; ~3 GB virtual [U]).

## 5. Concrete setup plan (documentation only; NOT run)

Windows side, `%USERPROFILE%\.wslconfig` (keep existing keys such as memory/processors):
```
[wsl2]
nestedVirtualization=true
```
then in PowerShell: `wsl --shutdown`.

Inside WSL2 (Debian/Ubuntu):
```bash
# 0. check
ls -l /dev/kvm; grep -m1 -o -E 'vmx|svm' /proc/cpuinfo
sudo usermod -aG kvm $USER     # re-login afterwards

# 1. packages
sudo apt update
sudo apt install -y qemu-system-x86 qemu-utils cloud-image-utils auditd bpftrace

# 2. base image (verify checksum from the SHA512SUMS in the same directory)
mkdir -p ~/sandbox && cd ~/sandbox
curl -LO https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2
chmod a-w debian-13-genericcloud-amd64.qcow2

# 3. cloud-init seed (user, ssh key or serial autologin, auditd rules, shut off updates)
cat > user-data <<'EOF'
#cloud-config
users:
  - name: agent
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL     # drop sudo if you do not want agent root
    lock_passwd: false
    plain_text_passwd: agent          # sandbox only
packages: [auditd, strace]
runcmd:
  - auditctl -a always,exit -F arch=b64 -S execve -k agent_exec
EOF
echo "instance-id: vm0" > meta-data
cloud-localds seed0.iso user-data meta-data

# 4. per-VM overlay
qemu-img create -f qcow2 -b debian-13-genericcloud-amd64.qcow2 -F qcow2 vm0.qcow2 8G

# 5. run one VM: KVM, no network, serial console on a unix socket for the harness
qemu-system-x86_64 -enable-kvm -cpu host -smp 1 -m 768 \
  -display none -nodefaults -no-user-config \
  -drive file=vm0.qcow2,if=virtio,format=qcow2 \
  -drive file=seed0.iso,if=virtio,format=raw,readonly=on \
  -nic none \
  -chardev socket,id=ser0,path=/tmp/vm0.serial,server=on,wait=off,logfile=vm0.serial.log \
  -serial chardev:ser0 \
  -monitor unix:/tmp/vm0.mon,server,nowait
# (Use '-netdev user,id=n0,restrict=on -device virtio-net-pci,netdev=n0' instead of -nic none
#  if the guest needs a NIC present but no outside access.)
# Confirm every flag with: qemu-system-x86_64 -help ; flag set above is from memory + the
# docs fetched for restrict/-nic none/-no-user-config/-snapshot; serial/monitor syntax [U].

# 6. throwaway variant: add -snapshot (and drop the overlay) for no-persistence runs.

# 7. checkpoint after boot (monitor): savevm booted ; restore: loadvm booted   [U]

# 8. TCG tracing run (slow; for sampled replay only): drop -enable-kvm / -cpu host
#    use '-accel tcg -cpu max' and add:
#    -plugin /usr/lib/x86_64-linux-gnu/qemu/... (path varies) or a self-built libexeclog.so,
#    e.g. -plugin ./contrib/plugins/libexeclog.so,ifilter=... -d plugin -D trace.log
#    Distro QEMU may not ship plugin .so files; building QEMU from source with plugins is
#    likely required [U]. Capstone is needed for execlog disassembly [V].
```

Parallel launcher sketch (N VMs): loop `i` in 0..N-1: create `vm$i.qcow2` overlay, a seed with `instance-id: vm$i`, a unique socket path, and start under `systemd-run --user --scope -p MemoryMax=1G` [U]. Delete overlays after diffing.

**Per-VM footprint estimate [E, unmeasured]**
- RAM: 768 MB guest cap; ~250-450 MB resident when idle/light, plus ~50-100 MB QEMU process.
- vCPU: 1 (idle load near zero; bursts during commands). With KVM, 24 VMs fit on 24 cores easily.
- Disk: overlay 20-200 MB depending on package installs and logs; shared base 325 MB.
- Totals for N=24: ~10-20 GB RAM, ~1-5 GB overlays. Leaves room beside vLLM only if WSL's 47 GB is not consumed by the model's host RAM; check.
- Under TCG expect ~10x CPU cost per task [U], so reduce N or sample.

## Open questions / not verified
- Whether a KVM guest actually boots on this specific WSL2 setup (only `/dev/kvm` and `vmx` were confirmed).
- Debian genericcloud boot time, per-VM RSS, savevm behaviour, KSM in the WSL2 kernel: all untested.
- PyREBox and DietPi/antiX/Devuan details came from general knowledge, not fetched pages.
- auditd and Falco overhead numbers: none verifiable; Tetragon numbers are vendor-published (https://isovalent.com/blog/post/tetragon-release-10).
- TCG plugin docs: https://www.qemu.org/docs/master/devel/tcg-plugins.html (API) and https://gitlab.com/qemu-project/qemu/-/raw/master/docs/about/emulation.rst (plugin list/options); invocation: https://www.qemu.org/docs/master/system/invocation.html ; gVisor platforms: https://gvisor.dev/docs/architecture_guide/platforms .
