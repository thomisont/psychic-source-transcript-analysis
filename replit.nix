{ pkgs }: {
  deps = [
    pkgs.nano
    pkgs.python311Packages.pytest
    pkgs.python311Packages.uvicorn
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
  ];
}
## New comment
