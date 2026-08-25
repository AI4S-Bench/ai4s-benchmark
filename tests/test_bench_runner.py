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
