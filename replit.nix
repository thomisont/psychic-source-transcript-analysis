{ pkgs }: {
  deps = [
    pkgs.nano
    pkgs.python310Packages.pytest
    pkgs.python310Packages.uvicorn
    pkgs.python310
    pkgs.gcc
    pkgs.glibc
    pkgs.python310Packages.pip
    pkgs.python310Packages.setuptools
    pkgs.python310Packages.wheel
    pkgs.curl
    pkgs.git
    pkgs.openssl
    pkgs.zlib
    pkgs.stdenv
    pkgs.libstdcxx5
  ];
}
## New comment
