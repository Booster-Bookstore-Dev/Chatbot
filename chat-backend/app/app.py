import pkg_resources
import pathlib

def list_installed_packages():
    return sorted([str(d) for d in pkg_resources.working_set])

def print_data():
    data_dir = pathlib.Path("./data")
    if not data_dir.exists():
        print("No data directory found.")
        return
    for file in data_dir.glob("*"):
        print(f"Found file: {file.name}")
        try:
            print(file.read_text())
        except Exception as e:
            print(f"  (Could not read {file.name}: {e})")

if __name__ == "__main__":
    print("=== Installed requirements ===")
    for pkg in list_installed_packages():
        print(pkg)

    print("\n=== Data contents ===")
    print_data()
