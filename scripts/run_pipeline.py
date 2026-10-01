import subprocess
import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent
dbt_dir = project_dir / "olist_warehouse"
dbt_executable = Path(sys.executable).parent / "dbt"

def main():
    print("Step 1/2: Load data from MinIO into raw tables", flush=True)

    subprocess.run(
        [sys.executable, str(project_dir / "scripts" / "load_raw.py")],
        cwd=project_dir,
        check=True,
    )

    print("Step 2/2: Build dbt models and run tests", flush=True)

    subprocess.run(
        [
            str(dbt_executable),
            "build",
            "--select",
            "+fct_orders",
            "+dim_customers",
        ],
        cwd=dbt_dir,
        check=True,
    )

    print(
        "Pipeline completed. Review the dbt output above for warnings.",
        flush=True
    )

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(
            f"Pipeline stopped because a step failed "
            f"(exit code {error.returncode}).",
            file=sys.stderr,
        )
        sys.exit(error.returncode)