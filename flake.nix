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
      checks = forAllSystems (pkgs: {
        ansible = pkgs.runCommand "ansible-checks" {
          src = ./.;
          nativeBuildInputs = [
            pkgs.ansible
            pkgs.ansible-lint
            pkgs.bash
            pkgs.coreutils
            pkgs.findutils
            pkgs.gnumake
            pkgs.git
            pkgs.python3
            (pkgs.ruby.withPackages (ps: [ ps.minitest ]))
          ];
        } ''
          cp -r "$src" source
          chmod -R u+w source
          cd source
          patchShebangs ansible/files
          export ANSIBLE_HOME="$TMPDIR/ansible"
          export XDG_CACHE_HOME="$TMPDIR/cache"
          mkdir -p "$ANSIBLE_HOME" "$XDG_CACHE_HOME"
          make test
          make lint
          touch "$out"
        '';
      });

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
            # デプロイ前に手元で app/go のコンパイルエラーを見つけるため
            pkgs.go
            pkgs.gopls
          ];
        };
      });
    };
}
