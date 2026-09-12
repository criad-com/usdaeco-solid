{
  description = "Exact bodies, measurements and proxy twins";
  inputs = {
    toolchain.url = "github:criad-com/usdaeco-toolchain?ref=v0.3.10";
    core.url = "github:criad-com/usdaeco-core?ref=v0.9.4";
    core.flake = false;
    axis.url = "github:criad-com/usdaeco-axis?ref=v0.1.4";
    axis.flake = false;
    datacentre.url = "github:criad-com/usdaeco-datacentre?ref=v0.4.8";
    datacentre.flake = false;
    ifc.url = "github:criad-com/usdaeco-ifc?ref=v0.2.2";
    ifc.flake = false;
    # The native runtime consumes both kits' package outputs. Share the
    # selected family releases instead of resolving their older nested pins.
    usdSolid.url = "github:criad-com/usdSolid?ref=v0.1.4";
    usdSolid.inputs.aeco-toolchain.follows = "toolchain/aeco-toolchain";
    usdSolid.inputs.usdaeco-toolchain.follows = "toolchain";
    usdSolidOcct.url = "github:criad-com/usdSolidOcct?ref=v0.1.3";
    usdSolidOcct.inputs.aeco-toolchain.follows = "toolchain/aeco-toolchain";
    usdSolidOcct.inputs.usdaeco-toolchain.follows = "toolchain";
    usdSolidOcct.inputs.usdSolid.follows = "usdSolid";
    nixpkgs.follows = "toolchain/nixpkgs";
  };
  outputs = { self, nixpkgs, toolchain, core, axis, datacentre, ifc, usdSolid, usdSolidOcct }:
    let
      each = nixpkgs.lib.genAttrs [ "aarch64-darwin" "x86_64-linux" ];
      make = system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          kit = toolchain.lib.forSystem system;
          corePlugin = kit.buildCodelessSchema { name = "usdAeco"; src = core; };
          setup = ''
            export TOOLCHAIN_DIR=${toolchain}
            export AECO_CORE_ROOT=${core}
            export AECO_AXIS_ROOT=${axis}
            export AECO_IFC_ROOT=${ifc}
            export AECO_DATACENTRE_ROOT=${datacentre}
            export CORE_PLUGIN_DIR=${corePlugin}/plugins/usdAeco/resources
            export PXR_PLUGINPATH_NAME=$CORE_PLUGIN_DIR
            export USD_SOLID_OCCT_RUNTIME=${usdSolidOcct.packages.${system}.runtime}
          '';
          command = name: script: pkgs.writeShellApplication {
            inherit name;
            runtimeInputs = [ kit.pythonEnv kit.usd-dev pkgs.clang ];
            text = setup + ''
              cp -R ${self} source
              chmod -R u+w source
              cd source
              export AECO_EXACT_CACHE=$PWD/.work/native
              env -u PYTHONPATH python ${script} "$@"
            '';
          };
        in { inherit pkgs kit setup command; };
    in {
      packages = each (system: let p = make system; in {
        default = p.pkgs.runCommand "usdaeco-solid-source" {} ''mkdir -p "$out"; cp -R ${self}/. "$out/"'';
      });
      checks = each (system: let p = make system; in {
        library = p.pkgs.runCommand "usdaeco-solid-check" {
          nativeBuildInputs = [ p.kit.pythonEnv p.kit.usd-dev p.pkgs.clang ];
        } (p.setup + ''
          cp -R ${self} source
          chmod -R u+w source
          cd source
          export AECO_EXACT_CACHE=$PWD/.work/native
          env -u PYTHONPATH PYTHONPATH=$AECO_CORE_ROOT:$PWD python check.py
          mkdir -p "$out"
        '');
      });
      devShells = each (system: let p = make system; in {
        default = p.pkgs.mkShell { packages = [ p.kit.pythonEnv p.kit.usd-dev p.pkgs.clang ]; shellHook = p.setup; };
      });
      apps = each (system: let p = make system; in {
        example = { type = "app"; program = "${p.command "example" "examples/datacentre/run.py"}/bin/example"; };
      });
    };
}
