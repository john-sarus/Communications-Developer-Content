# AvaTax Communications REST v2 Test Harness

A Windows desktop app (Python + tkinter) for generating, executing, and validating test cases against the AvaTax Communications REST v2 API.

## Prerequisites

- Python 3.10+ with tkinter (included in standard Windows Python installs)
- pip

## Install Dependencies

From the **repo root**:

```
pip install -r test_harness/requirements.txt
```

## Launching

### From a Terminal

Open a terminal, `cd` to the repo root, and run:

```
python -m test_harness
```

The repo root must be the working directory so the module can locate the SDK and JSON samples.

### From PyCharm

1. **Open the repo root** (`Communications-Developer-Content`) as a PyCharm project.
2. Go to **Run > Edit Configurations...** and click **+** to add a new **Python** configuration.
3. Set the fields:
   - **Name**: `Test Harness`
   - **Module name**: `test_harness` (click the dropdown next to "Script path" and switch to "Module name")
   - **Working directory**: the repo root (e.g. `C:\Users\johnr\Documents\Avalara\AvaTax\Communications-Developer-Content`)
   - **Python interpreter**: your project interpreter with the dependencies installed
4. Click **Apply**, then **Run**.

Alternatively, right-click `test_harness/__main__.py` in the project tree and select **Run '__main__'**. If PyCharm sets the working directory to `test_harness/` instead of the repo root, edit the run configuration and change **Working directory** back to the repo root.

## First Run

On first launch the app opens to the **Configuration** tab. Enter your UAT credentials (username, password, client ID), click **Save Credentials** (stored in Windows Credential Manager via keyring), then click **Test Connection**. A green status means you're connected and the Test Builder tab will populate with TS pairs automatically.
