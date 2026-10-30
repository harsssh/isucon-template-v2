{
  description = "ISUCON の競技サーバーをセットアップするためのツール";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      systems = [
        "aarch64-darwin"
        "x86_64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.ansible
            pkgs.ansible-lint
            # Makefile と ansible/files のスクリプト、テスト用
            pkgs.bash
            pkgs.coreutils
            pkgs.gnumake
            pkgs.python3
            pkgs.ruby
          ];
        };
      });
    };
}
