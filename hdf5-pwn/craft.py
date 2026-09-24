import h5py
import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create an HDF5 file with one dataset backed by an external file."
    )
    parser.add_argument("h5file", help="Path of the HDF5 file to create")
    parser.add_argument("external", help="External file the dataset reads from")
    parser.add_argument(
        "--dataset", default="data", help="dataset name inside the hdf5 file"
    )
    parser.add_argument(
        "--size",
        type=int,
        default=512,
        help="Bytes to map from the external file (default: whole file)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    with h5py.File("pwn.h5", "w") as f:
        f.create_dataset(
            args.dataset,
            shape=("<n_bytes_to_read>",),
            dtype="uint8",
            external=[("<local_path>", 0, h5py.h5f.UNLIMITED)]
        )

    print(
        f"Created {args.h5file}: dataset '{args.dataset}' -> {args.external}"
    )


if __name__ == "__main__":
    main()
