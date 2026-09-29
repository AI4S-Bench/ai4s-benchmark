import json
import subprocess

from bench import run_matrix


def test_harbor_command_never_falls_back_to_source(monkeypatch):
    monkeypatch.setattr(run_matrix.shutil, "which", lambda _: None)

    assert run_matrix.harbor_command() is None


def test_nft_fib_inet_kernel_config_detection():
    assert run_matrix.nft_fib_inet_enabled("CONFIG_NFT_FIB_INET=y\n")
    assert run_matrix.nft_fib_inet_enabled("CONFIG_NFT_FIB_INET=m\n")
    assert not run_matrix.nft_fib_inet_enabled("CONFIG_NFT_FIB=m\nCONFIG_NFT_FIB_IPV4=m\n")


def test_linux_container_shell_scripts_reject_crlf():
    assert run_matrix.contains_crlf(b"#!/bin/bash\r\necho test\r\n")
    assert not run_matrix.contains_crlf(b"#!/bin/bash\necho test\n")


def test_submodule_gitlink_matches_manifest_pin():
    manifest = run_matrix.load_manifest()
    pinned = manifest["upstreams"][manifest["tasks"][0]["source"]]["commit"]
    entry = subprocess.run(
        ["git", "-C", str(run_matrix.ROOT), "ls-files", "-s", "references/terminal-bench-science"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()

    assert entry[:2] == ["160000", pinned]


def test_checkout_commit_ignores_uninitialized_submodule(tmp_path):
    assert run_matrix.checkout_commit(tmp_path) is None

    git = ["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@example.test"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "commit", "-q", "--allow-empty", "--no-gpg-sign", "-m", "pin"], check=True)
    head = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()

    assert run_matrix.checkout_commit(tmp_path) == head


def write_trial(job_dir, name, reward=None, exception=None):
    (job_dir / name).mkdir(parents=True)
    result = {
        "verifier_result": None if reward is None else {"rewards": {"reward": reward}},
        "exception_info": None if exception is None else {"exception_type": exception},
    }
    (job_dir / name / "result.json").write_text(json.dumps(result), encoding="utf-8")


def test_matrix_gates_on_trial_rewards_not_harbor_exit_code(tmp_path):
    write_trial(tmp_path, "oracle__a", reward=1.0)
    write_trial(tmp_path, "oracle__b", reward=0.0)
    (tmp_path / "result.json").write_text("{}", encoding="utf-8")

    trials = run_matrix.trial_outcomes(tmp_path)

    assert [trial["reward"] for trial in trials] == [1.0, 0.0]
    assert not run_matrix.meets_expectation({"attempts": 2, "expected_reward": 1.0}, trials)
    assert run_matrix.meets_expectation({"attempts": 2}, trials)


def test_errored_or_missing_trials_miss_the_expectation(tmp_path):
    write_trial(tmp_path, "nop__a", reward=0.0, exception="VerifierTimeoutError")
    negative_control = {"attempts": 1, "expected_reward": 0.0}

    assert not run_matrix.meets_expectation(negative_control, run_matrix.trial_outcomes(tmp_path))
    assert not run_matrix.meets_expectation(negative_control, [])
