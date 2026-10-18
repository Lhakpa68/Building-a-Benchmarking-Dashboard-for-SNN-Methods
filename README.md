# Building a Benchmarking Dashboard for SNN Methods

Project archive for the Master of ICT Research thesis *"Building a Benchmarking Dashboard for SNN Methods"* by **Lhakpa Tshering**, Melbourne Institute of Technology (October 2026).
Supervisors: Dr Belal Chowdhury (Principal), Dr Bahram Farhadinia (Associate).

[![Open the dashboard](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://snn-benchmark-dashboard.streamlit.app)

**Open the dashboard in your browser:** https://snn-benchmark-dashboard.streamlit.app (no installation needed).

The repository contains the benchmark suite, the results database, the analysis and reproduction scripts and the interactive dashboard used in the thesis (release **v1.0.0**).

## Overview

The study compares five spiking neural network (SNN) simulators across nine execution backends on one CPU-based platform, under a common protocol:

| Simulator | Backends |
|---|---|
| Brian2 | NumPy, Cython, C++ standalone |
| NEST | 1, 2 and 4 threads |
| Nengo | default |
| snnTorch | default (PyTorch) |
| SpikingJelly | default (PyTorch) |

Two plain-NumPy validation controls are included. The workload is a feedforward leaky integrate-and-fire (LIF) network with fixed fan-in, measured at five network sizes.

Experiments:

1. Inference cost (runtime, memory, processor-time energy proxy, processor use)
2. Native-learning cost and exploratory accuracy at a fixed training budget
3. Scalability across network sizes (fitted log-log exponents)
4. Energy-proxy consistency against an analytic operation-count reference

The dashboard brings these measurements together and recommends a measured backend for a chosen network size and set of priorities (runtime, memory growth, scalability and optional exploratory accuracy), using a weighted-sum method with a softmax activation that expresses scores as relative priority shares. It also reports rank stability, sensitivity and the runtime consequences of reusing a choice at another network size.

## Repository structure

```
snnbench/                 Benchmark suite (adapters, runner, profiler)
  adapters/base.py        Common adapter interface for every simulator
  runner.py               Measurement driver (warm-up and measured runs)
  profiler.py             Processor-time energy proxy
dashboard/                Flask dashboard + Streamlit alternative
  dashboard_data.py       Shared data layer (queries, fits, Kendall's tau-b)
  optimization.py         Preference-aware selection and activation function
  robustness.py           Ties and stability notes
  robustness_data/        Files read by the Robustness page
  streamlit_app.py        Streamlit front end
review/                   Scripts that regenerate the Appendix H tables
tests/                    102 automated tests
results/                  Results database, validation and analysis outputs
run.py                    Benchmark command-line entry point
RUN_DASHBOARD.py          Launches the Flask dashboard
```

## Reproduction

Commands in the order used for the thesis campaign (Appendix A, Table 25):

| Step | Command | Produces |
|---|---|---|
| 1 | `python run.py check` | Environment and capability report; which backends are reachable |
| 2 | `python run.py validate` | Cross-backend equivalence check → `results/validate.txt` |
| 3 | `python run.py bench --tasks inference,scalability --warmup 5 --measured 5` | Experiments 1 and 3 for every available backend at all five sizes |
| 4 | `python run.py bench --tasks training --preset paper` | Experiment 2 at the fixed budget (6,000 / 1,000 images, three epochs, 256 hidden units) |
| 5 | `python run.py bench --only brian2` | Partial re-run of one simulator (rows are appended, so interrupted runs resume) |
| 6 | `python run.py analyse` | Chapter 4 statistics → `results/ANALYSIS.md`, `results/analysis.json` |
| 7 | `python RUN_DASHBOARD.py` | Dashboard at http://127.0.0.1:5000 (or next free port) |
| 8 | `streamlit run dashboard/streamlit_app.py` | Streamlit alternative (see `dashboard/requirements-streamlit.txt`) |
| 9 | `python -m pytest tests` | The 102 automated tests |

A simulator with no working backend on the requested device writes no row and prints an explicit skip; it is never recorded as zero.

## Running the dashboard on your own computer

```
pip install -r dashboard/requirements.txt
python RUN_DASHBOARD.py                      # Flask version → http://127.0.0.1:5000
streamlit run dashboard/streamlit_app.py     # Streamlit version → http://localhost:8501
```

`127.0.0.1` addresses only work on the computer where the dashboard is running; use the online link above to view it anywhere.

## Dashboard pages

Dashboard (`/`), All Simulators, Optimisation, Inference, Scalability, Memory, Training, Sensitivity, Robustness, Equivalence and provenance, Methods and limitations. Every table has a CSV export, and read-only JSON routes expose the same data.

## Scope and limitations

- All measurements come from one CPU-only platform; results compare the implemented simulator-backend configurations under the stated protocol.
- The energy figure is a processor-time-based estimate, not a measurement of electrical power.
- Accuracy is reported for context and used only in explicitly exploratory selection scenarios.
- The selection feature ranks only the measured backends at the measured network sizes.

## Citation

> L. Tshering, "Building a Benchmarking Dashboard for SNN Methods," Master of ICT Research thesis, School of Information Technology and Engineering, Melbourne Institute of Technology, 2026.

## License

MIT — see [LICENSE](LICENSE).
