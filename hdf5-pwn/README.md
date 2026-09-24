# hdf5-pwn

A proof of concept demonstrating arbitrary local file disclosure
through HDF5 external-storage datasets when an application opens untrusted
HDF5 files without sandboxing.

## Overview

HDF5 lets a dataset's raw data live in an external file; the path is stored in
the HDF5 file and resolved by the library at read time, relative to the reading
process's working directory.

- `server.py` Flask "HDF5 Viewer" that accepts uploaded `.h5` files, opens
  them read-only with h5py, and renders the contents of every dataset.
- `craft.py` Builds a crafted HDF5 file whose dataset is backed by an
  arbitrary external file given on the command line.

Uploading any of these files makes the server read and display the target
file's contents, since h5py transparently follows the external reference.

## Prerequisites

- Python 3.11 or newer (`.python-version` pins 3.11)
- [uv](https://docs.astral.sh/uv/) (optional; plain `pip` also works)
- Dependencies from `pyproject.toml`: `flask >= 3.1.3`, `h5py >= 3.16.0`

## Setup

```sh
uv sync
# or, with pip:
python3.11 -m venv .venv
.venv/bin/pip install -e .
```

## Usage

Start the viewer server:

```sh
uv run python server.py        # or: .venv/bin/python server.py
```

Craft a malicious HDF5 file that references sensitive data:

```sh
python craft.py pwn_env.h5 /proc/self/environ --dataset data --size 512
```

Positional arguments: output HDF5 path and the external file to reference.
`--dataset` sets the dataset name (default `data`); `--size` sets how many
bytes the dataset maps (default 512).

The app listens on `http://127.0.0.1:5000`. Upload a crafted file through the
web form at `/`, or with `curl`:

```sh
curl -F "file=@pwn_env.h5" http://127.0.0.1:5000/upload
```

### Expected output

The response previews every dataset in the uploaded file. For `pwn_env.h5`,
dataset `/data` resolves to the external `/proc/self/environ` file and the page shows its
contents:

```html
<h1>Preview of pwn_env.h5</h1>
<h2>/data</h2>
<p>SECRET=MY_SECRET</p>
```

## How it works

`craft.py` calls `create_dataset` with `external=[(path, 0, h5py.h5f.UNLIMITED)]`,
recording the external file in the dataset's layout instead of allocating
storage. When `server.py` reads the dataset (`obj[()]`), the HDF5 library opens
the referenced file from the server's working directory and returns its bytes as
ordinary dataset data. Because the viewer renders every dataset of any uploaded
file, the crafted file causes it to disclose arbitrary local files. The server
performs no path validation or sandboxing around dataset reads.
