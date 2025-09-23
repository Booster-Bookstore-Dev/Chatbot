import pathlib

def build_index():
    data_dir = pathlib.Path("/data")
    data_dir.mkdir(parents=True, exist_ok=True)

    index_file = data_dir / "index.txt"
    with index_file.open("w") as f:
        f.write("This is a dummy FAISS index.\n")
        f.write("Built at runtime inside Docker.\n")

    print(f"Index built: {index_file}")

if __name__ == "__main__":
    build_index()
