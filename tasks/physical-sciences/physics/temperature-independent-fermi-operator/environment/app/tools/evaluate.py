"""Practice evaluator for /app/solver/fermi_operator.py.

    python /app/tools/evaluate.py accuracy            # small systems vs dense eigh
    python /app/tools/evaluate.py timing [names...]   # graded-size public instances
    python /app/tools/evaluate.py scaling [families]  # ribbon / square / cubic sweeps at kT = 0

Every call runs in a fresh single-threaded interpreter, like the grader, and
reports cost = max(wall, CPU) minus the cost of the same process without your
solver.  There is no reference timing here; the grader compares against a
reference implementation it does not ship.
"""
import json
import os
import resource
import subprocess
import sys
import tempfile
import time

import numpy as np
import scipy.linalg as sla

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hamiltonians as hm  # noqa: E402

SOLVER = os.environ.get("FERMI_SOLVER_DIR", "/app/solver")
TOL = 1e-6
THREADS = {k: "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                            "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")}
CHILD = r"""
import json, sys, numpy as np, scipy.sparse as sp, scipy.sparse.linalg
p = json.load(open("params.json")); d = np.load("instance.npz")
H = sp.csr_matrix((d["data"], d["indices"], d["indptr"]), shape=tuple(d["shape"]))
X = d["X"]
if p["null"]:
    Y = X.copy()
else:
    sys.path.insert(0, p["solver"])
    import fermi_operator
    Y = np.asarray(fermi_operator.fermi_dirac_operator(H, p["kT"], p["mu"]) @ X)
np.save("out.npy", Y)
"""


def timed_call(H, kT, mu, X, null=False, timeout=None):
    with tempfile.TemporaryDirectory() as tmp:
        np.savez(os.path.join(tmp, "instance.npz"), data=H.data, indices=H.indices,
                 indptr=H.indptr, shape=np.array(H.shape), X=X)
        with open(os.path.join(tmp, "params.json"), "w") as fh:
            json.dump({"null": null, "solver": SOLVER, "kT": kT, "mu": mu}, fh)
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        t0 = time.perf_counter()
        proc = subprocess.run([sys.executable, "-c", CHILD], cwd=tmp, timeout=timeout,
                              env={**os.environ, **THREADS}, capture_output=True, text=True)
        wall = time.perf_counter() - t0
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        if proc.returncode:
            raise RuntimeError(proc.stderr[-2000:])
        cpu = after.ru_utime - before.ru_utime + after.ru_stime - before.ru_stime
        return max(wall, cpu), np.load(os.path.join(tmp, "out.npy"))


def _last_line(exc):
    lines = [ln for ln in str(exc).strip().splitlines() if ln.strip()]
    return lines[-1][-200:] if lines else repr(exc)


def accuracy():
    cases = (("ribbon", hm.anderson((300, 6), 1.5, 11), -0.7, False),
             ("square", hm.anderson((40, 40), 1.5, 12), 0.35, False),
             ("cubic", hm.anderson((12, 12, 12), 3.0, 13), -1.2, False),
             ("ionic", hm.anderson((40, 40), 0.5, 14, stagger=0.6), 0.0, True),
             ("amorphous", hm.amorphous(800, 15), -1.0, False))
    ok = True
    for name, H, target, insulator in cases:
        mu = hm.choose_mu(H, target, insulator)
        X = hm.probe_block(H.shape[0], 5)
        w, Q = sla.eigh(H.toarray())
        QX = Q.T @ X
        for kT in hm.TEMPERATURES:
            fw = (w < mu).astype(float) if kT == 0 else 0.5 * (1 - np.tanh(0.5 * (w - mu) / kT))
            exact = Q @ (fw[:, None] * QX)
            try:
                cost, Y = timed_call(H, kT, mu, X)
                err = (np.linalg.norm(Y - exact, axis=0) / np.linalg.norm(exact, axis=0)).max()
                flag = "ok" if err <= TOL else "FAIL"
                ok &= err <= TOL
                print(f"{name:10s} N={H.shape[0]:5d} kT={kT:8.1e}  err={err:.2e}  {flag}", flush=True)
            except Exception as exc:  # noqa: BLE001
                ok = False
                print(f"{name:10s} N={H.shape[0]:5d} kT={kT:8.1e}  ERROR {_last_line(exc)}", flush=True)
    print("all within 1e-6" if ok else "some cases failed")


def timing(names):
    names = names or [n for n, *_ in hm.PUBLIC_INSTANCES]
    for name in names:
        H, mu = hm.public_instance(name)
        X = hm.probe_block(H.shape[0], 5)
        null, _ = timed_call(H, 0.0, mu, X, null=True)
        costs = []
        for kT in hm.TEMPERATURES:
            try:
                cost, _ = timed_call(H, kT, mu, X, timeout=900)
                costs.append(cost - null)
                print(f"{name:10s} N={H.shape[0]:6d} kT={kT:8.1e}  cost={cost - null:8.3f}s", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"{name:10s} N={H.shape[0]:6d} kT={kT:8.1e}  ERROR {_last_line(exc)}", flush=True)
        if costs:
            print(f"{name:10s} worst / kT=0 cost ratio: {max(costs) / max(costs[-1], 1e-3):.2f}")


def scaling(families):
    targets = {"ribbon": -0.7, "square": 0.35, "cubic": -1.2}
    for family in families or list(hm.SWEEPS):
        ns, costs = [], []
        for i, size in enumerate(hm.SWEEPS[family]):
            H = hm.build(family, 2000 + i, size)
            mu = hm.choose_mu(H, targets[family])
            X = hm.probe_block(H.shape[0], 5)
            null, _ = timed_call(H, 0.0, mu, X, null=True)
            try:
                cost, _ = timed_call(H, 0.0, mu, X, timeout=1800)
            except Exception as exc:  # noqa: BLE001
                print(f"{family:6s} N={H.shape[0]:7d} kT=0  ERROR {_last_line(exc)}", flush=True)
                break
            ns.append(H.shape[0])
            costs.append(max(cost - null, 1e-2))
            print(f"{family:6s} N={H.shape[0]:7d} kT=0  cost={costs[-1]:8.3f}s", flush=True)
        if len(ns) > 1:
            slope = np.polyfit(np.log(ns), np.log(costs), 1)[0]
            print(f"{family:6s} fitted exponent d log(cost) / d log(N) = {slope:.2f}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "accuracy"
    {"accuracy": lambda: accuracy(), "timing": lambda: timing(sys.argv[2:]),
     "scaling": lambda: scaling(sys.argv[2:])}[mode]()
