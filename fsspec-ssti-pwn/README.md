# fsspec-ssti-pwn

A proof of concept demonstrating remote code execution through Jinja2
Server-Side Template Injection (SSTI) in `fsspec`'s `ReferenceFileSystem`
when an application loads an untrusted references document without
sandboxing.

## Overview

fsspec's `ReferenceFileSystem` (the Kerchunk-style references format) has a
`gen` section whose `url`, `offset` and `length` fields are rendered through
an **un-sandboxed** `jinja2.Template(...).render(...)`. Because Jinja2's
default globals expose Python internals, an attacker-controlled field can
reach `os.popen` and execute arbitrary commands — and this happens at
*reference-load time*, before any real data is read.

- `fsspec_reference_ssti.ipynb`  Jupyter notebook that reproduces the
  vulnerability end to end: isolated root-cause demo, triggering it through
  `ReferenceFileSystem`, and two remediation approaches.

Loading any of the crafted references documents makes the library execute
the embedded payload, since fsspec renders the template fields during
filesystem construction.

## Vulnerability

**CVE-2026-104851** — Remote Code Execution in
`fsspec.implementations.reference.ReferenceFileSystem`.

Three factors combine:

1. **Untrusted input rendered as a template** — fields in a references
   document's `gen` section are passed directly into
   `jinja2.Template(...).render(...)`.
2. **Un-sandboxed Jinja2 environment** — the default `Environment` exposes
   globals like `cycler`, whose `__init__.__globals__` provides a path to
   the `os` module.
3. **Triggers at load time** — the `gen` section is expanded during
   `ReferenceFileSystem.__init__`, so the payload fires before any data
   fetch occurs.

Together these let an attacker embed a Jinja2 expression such as
`{{ cycler.__init__.__globals__.os.popen('id').read() }}` in the `url` field
of a references document and achieve arbitrary command execution on any
machine that opens it.

## Prerequisites

- Python 3.11 or newer (`.python-version` pins 3.14)
- [uv](https://docs.astral.sh/uv/) (optional; plain `pip` also works)
- Dependencies: `fsspec==2025.10.0` (the vulnerable version), `jinja2`
- JupyterLab or Jupyter Notebook to run the `.ipynb`

> **Important:** The exploit requires `fsspec<=2025.10.0`. Newer versions
> (2026+) patched the vulnerability by switching to `SandboxedEnvironment`.
> The pip command below pins the correct version.

## Setup

```sh
uv sync
# or, with pip:
python3 -m venv .venv
.venv/bin/pip install 'fsspec==2025.10.0' jinja2 jupyterlab
```

## Usage

Launch the notebook:

```sh
uv run jupyter lab fsspec_reference_ssti.ipynb
# or: .venv/bin/jupyter lab fsspec_reference_ssti.ipynb
```

Run the cells in order. The notebook is structured in three parts:

### Part 1 — Root cause in isolation

Demonstrates that `jinja2.Template(untrusted).render()` evaluates
attacker-controlled expressions. First proves template evaluation with
`{{ 7 * 7 }}` → `49`, then escalates to command execution via the
`cycler.__init__.__globals__.os.popen(...)` gadget chain.

### Part 2 — Triggering through `ReferenceFileSystem`

Builds a malicious Kerchunk-style references JSON with the SSTI payload in
the `gen` section's `url` field and passes it to
`fsspec.filesystem("reference", fo=...)`. The payload executes during
filesystem construction — no data is ever fetched.

### Expected output

```
expanded reference for 'data/0':
['<command output>\n', 0, 0]
```

The command output (e.g. the result of `id` or `ls`) appears as the resolved
URL in the expanded reference table, proving arbitrary code execution.

### Part 3 — Remediation

Two independent fixes are demonstrated. Either removes the RCE;
defence-in-depth uses both.

1. **Sandboxed Jinja2 environment** —
   `jinja2.sandbox.ImmutableSandboxedEnvironment` blocks attribute access to
   Python internals, so the `cycler.__init__.__globals__` gadget raises
   `SecurityError`.
2. **Input validation** — reject any template field containing attribute
   access, calls, dunder names, or unknown variables before rendering.

## How it works

`ReferenceFileSystem` reads a references document containing a `gen` section
with templated fields (e.g. `url: "s3://bucket/chunk_{{i}}"`). During
`__init__`, these fields are expanded by calling
`jinja2.Template(field).render(...)` for every generated reference. The
default Jinja2 environment provides globals such as `cycler`, `joiner`, and
`namespace`. From any of these, Python's introspection chain
(`__init__` → `__globals__` → `os`) reaches the `os` module, enabling
`os.popen(cmd).read()` inside a template expression. Because expansion
happens at construction time, the attack fires before any real I/O — even
"only reading metadata" is not a mitigation.

## Safety

Local-only, offline, no real services contacted. Every payload in this
notebook is benign (`id`, `ls`, `7*7`) — there are no destructive, network,
or data-exfiltration commands. For SC3010 classroom demonstration only.
